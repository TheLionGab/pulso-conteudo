"""Coleta determinística dos dados do episódio diário: o modelo não busca nem transcreve dado.

Uso:
  python3 -I coletar_dados.py <pasta_do_dia> <AAAA-MM-DD> --trava <arquivo>   grava fontes/ e a trava
  python3 -I coletar_dados.py --conferir <pasta_do_dia> --trava <arquivo>     confere depois do modelo

Grava em <pasta_do_dia>/fontes/:
  bcb-ptax.json     PTAX venda dos 15 dias até o dia (Banco Central, Olinda), bytes da resposta.
  pulso-imea.json   IMEA soja e milho de MT na semana do último pregão, e as praças da soja nesse dia
                    (public.mercado_quotes do Supabase do Pulso, REST só leitura, service role).
  pulso-imea.sql    A mesma leitura em SQL e as URLs REST usadas, para quem revisar refazer.
E a trava (--trava, FORA da pasta do dia, onde o modelo não escreve): sha256 dos três arquivos. O
--conferir reprova se algum mudou ou sumiu, ou se fontes/ ganhou qualquer arquivo (nem link simbólico).

Ambiente: SUPABASE_SERVICE_ROLE_KEY (obrigatória; nunca impressa nem gravada) e SUPABASE_URL
(padrão: projeto do Pulso). Mac (agendado.sh) e nuvem (pulso-brasil-diario.yml) usam este mesmo caminho.
Saída: 0 coletou; 3 sem dado novo para episódio (grava sem-episodio.txt com o motivo); 1 erro.
"""
import datetime as dt
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

URL_PADRAO = "https://jgsmgvplwhisapvuqcji.supabase.co"
PTAX = ("https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
        "CotacaoDolarPeriodo(dataInicial=@i,dataFinalCotacao=@f)")
IDADE_MAX_DIAS = 4  # mesma janela do app (scripts/pulso-news/diario/constantes.mjs): sem dado velho
JANELA_DIAS = 7  # semana do último pregão, inclusive (ex.: 16 a 23/11)
ARQUIVOS = ("fontes/bcb-ptax.json", "fontes/pulso-imea.json", "fontes/pulso-imea.sql")


class SemEpisodio(Exception):
    pass


def sha256(caminho):
    return hashlib.sha256(Path(caminho).read_bytes()).hexdigest()


def baixar(url, cabecalhos=None, tentativas=3, espera=30):
    """GET com nova tentativa; o erro nunca leva cabeçalho (a chave não vaza em log)."""
    ultimo = "sem resposta"
    for n in range(tentativas):
        try:
            with urlopen(Request(url, headers=cabecalhos or {}), timeout=60) as r:
                return r.read()
        except HTTPError as e:
            ultimo = f"HTTP {e.code} {e.read().decode(errors='replace')[:200]}"
            if 400 <= e.code < 500 and e.code != 429:
                break
        except (URLError, TimeoutError, OSError) as e:
            ultimo = type(e).__name__
        if n + 1 < tentativas:
            time.sleep(espera)
    raise RuntimeError(f"{url.split('?')[0]}: {ultimo}")


def coletar_ptax(dia, destino):
    d = dt.date.fromisoformat(dia)
    ini, fim = (x.strftime("%m-%d-%Y") for x in (d - dt.timedelta(days=15), d))
    url = f"{PTAX}?@i='{ini}'&@f='{fim}'&$select=cotacaoVenda,dataHoraCotacao&$format=json"
    corpo = baixar(url)
    if not json.loads(corpo).get("value"):
        raise SemEpisodio("PTAX vazia no Banco Central")
    destino.write_bytes(corpo)


def coletar_imea(dia, base, chave, pasta):
    cab = {"apikey": chave, "Authorization": f"Bearer {chave}", "Accept": "application/json"}
    tabela = f"{base}/rest/v1/mercado_quotes"
    mt = "papel=eq.imea&localidade=eq." + quote("Mato Grosso")

    def ler(consulta):
        linhas = json.loads(baixar(f"{tabela}?{consulta}", cab), parse_float=float)
        if not isinstance(linhas, list):
            raise RuntimeError("resposta inesperada de mercado_quotes")
        return linhas

    ultimo = ler(f"select=data_publicacao&{mt}&cultura=eq.soja&data_publicacao=lte.{dia}"
                 "&order=data_publicacao.desc&limit=1")
    if not ultimo:
        raise SemEpisodio("IMEA sem nenhum pregão de soja até o dia")
    data = str(ultimo[0]["data_publicacao"])[:10]
    idade = (dt.date.fromisoformat(dia) - dt.date.fromisoformat(data)).days
    if idade > IDADE_MAX_DIAS:
        raise SemEpisodio(f"IMEA de {data} é velho demais para {dia} (mais de {IDADE_MAX_DIAS} dias)")
    inicio = (dt.date.fromisoformat(data) - dt.timedelta(days=JANELA_DIAS)).isoformat()

    q_serie = (f"select=data_publicacao,cultura,valor&{mt}&cultura=in.(soja,milho)"
               f"&data_publicacao=gte.{inicio}&data_publicacao=lte.{data}&order=cultura.asc,data_publicacao.asc")
    q_pracas = (f"select=localidade,valor&papel=eq.praca&cultura=eq.soja&data_publicacao=eq.{data}"
                "&order=valor.desc,localidade.asc")
    imea = {"soja": {}, "milho": {}}
    for l in ler(q_serie):
        imea[l["cultura"]][str(l["data_publicacao"])[:10]] = float(l["valor"])
    if len(imea["soja"]) < 2:
        raise RuntimeError(f"IMEA soja com {len(imea['soja'])} pregão(ões) em {inicio}..{data}")
    pracas = {l["localidade"]: float(l["valor"]) for l in ler(q_pracas)}

    sql = [
        "select now() as consulta_em, data_publicacao, cultura, valor from public.mercado_quotes "
        "where papel='imea' and localidade='Mato Grosso' and cultura in ('soja','milho') "
        f"and data_publicacao between date '{inicio}' and date '{data}' order by cultura, data_publicacao",
        "select localidade, valor from public.mercado_quotes where papel='praca' and cultura='soja' "
        f"and data_publicacao=date '{data}' order by valor desc, localidade",
    ]
    saida = {
        "consulta_em": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S+00"),
        "origem": "Pulso do Campo, produção, leitura só leitura por REST (coletar_dados.py); dado primário IMEA",
        "tabela": "public.mercado_quotes",
        "imea_mt": imea,
        f"pracas_soja_{data}": pracas,
        "sql": sql,
    }
    (pasta / "fontes/pulso-imea.json").write_text(json.dumps(saida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rest = [f"GET {tabela}?{q_serie}", f"GET {tabela}?{q_pracas}"]
    (pasta / "fontes/pulso-imea.sql").write_text(
        "-- Consulta usada por coletar_dados.py (service role, só leitura). Refazer = rodar as duas.\n"
        + ";\n".join(sql) + ";\n\n-- Mesma leitura por REST (schema public, PostgREST):\n"
        + "\n".join(f"-- {r}" for r in rest) + "\n", encoding="utf-8")


def fora_da_pasta(pasta, trava):
    """A trava fica fora da pasta onde o modelo escreve: senão ele refaz arquivo e trava juntos."""
    if trava == pasta or pasta in trava.parents:
        raise RuntimeError("--trava tem de ficar fora da pasta do dia (o modelo escreve nela)")


def arquivos_em_fontes(pasta):
    """Todo arquivo em fontes/ (relativo à pasta do dia). Link simbólico e pasta aninhada são recusados."""
    achados = []
    for caminho in sorted((pasta / "fontes").rglob("*")):
        if caminho.is_symlink():
            raise RuntimeError(f"link simbólico em fontes/: {caminho.relative_to(pasta)}")
        if caminho.is_file():
            achados.append(caminho.relative_to(pasta).as_posix())
    return achados


def gravar_trava(pasta, trava):
    extras = [a for a in arquivos_em_fontes(pasta) if a not in ARQUIVOS]
    if extras:
        raise RuntimeError(f"fontes/ tem arquivo que a coleta não gravou: {', '.join(extras)}")
    trava.parent.mkdir(parents=True, exist_ok=True)
    trava.write_text("".join(f"{sha256(pasta / rel)}  {rel}\n" for rel in ARQUIVOS))


def conferir(pasta, trava):
    """Falha se fonte mudou, sumiu ou se fontes/ ganhou qualquer arquivo depois da coleta."""
    fora_da_pasta(pasta, trava)
    travas = dict(reversed(linha.split("  ", 1)) for linha in trava.read_text().splitlines())
    if set(travas) != set(ARQUIVOS):
        raise RuntimeError("trava da coleta incompleta")
    atuais = arquivos_em_fontes(pasta)
    extras = [a for a in atuais if a not in travas]
    if extras:
        raise RuntimeError(f"arquivo novo em fontes/ depois da coleta (o modelo não pode criar fonte): {', '.join(extras)}")
    for rel, sha in travas.items():
        if rel not in atuais:
            raise RuntimeError(f"{rel} sumiu depois da coleta")
        if sha256(pasta / rel) != sha:
            raise RuntimeError(f"{rel} mudou depois da coleta (o modelo não pode alterar fonte)")
    print("fontes da coleta intactas:", ", ".join(ARQUIVOS))


def main(argv):
    argv = list(argv)
    trava = None
    if "--trava" in argv:
        i = argv.index("--trava")
        trava = Path(argv[i + 1]).resolve()
        del argv[i:i + 2]
    if trava is None:
        raise RuntimeError("falta --trava <arquivo> (fora da pasta do dia)")
    if argv[:1] == ["--conferir"]:
        conferir(Path(argv[1]).resolve(), trava)
        return 0
    pasta, dia = Path(argv[0]).resolve(), argv[1]
    fora_da_pasta(pasta, trava)
    dt.date.fromisoformat(dia)
    chave = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not chave:
        print("coletar_dados: falta SUPABASE_SERVICE_ROLE_KEY", file=sys.stderr)
        return 1
    base = os.environ.get("SUPABASE_URL", URL_PADRAO).strip().rstrip("/")
    if not base.startswith("https://"):
        print("coletar_dados: SUPABASE_URL tem de ser https", file=sys.stderr)
        return 1
    (pasta / "fontes").mkdir(parents=True, exist_ok=True)
    sobras = [a for a in arquivos_em_fontes(pasta) if a not in ARQUIVOS]
    if sobras:  # coleta nova não herda arquivo de execução anterior
        raise RuntimeError(f"fontes/ já tem arquivo que não é da coleta: {', '.join(sobras)}")
    try:
        coletar_ptax(dia, pasta / "fontes/bcb-ptax.json")
        coletar_imea(dia, base, chave, pasta)
    except SemEpisodio as motivo:
        (pasta / "sem-episodio.txt").write_text(f"{motivo}\n")
        print(f"Sem episódio: {motivo}")
        return 3
    gravar_trava(pasta, trava)
    imea = json.loads((pasta / "fontes/pulso-imea.json").read_text())
    print(f"coleta ok: {dia}; PTAX {len(json.loads((pasta / 'fontes/bcb-ptax.json').read_text())['value'])} dias; "
          f"IMEA soja {sorted(imea['imea_mt']['soja'])[-1]}, {len(imea['imea_mt']['soja'])} pregões; "
          f"{len(imea[[k for k in imea if k.startswith('pracas_soja_')][0]])} praças")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except (RuntimeError, ValueError, KeyError, IndexError, OSError) as erro:
        print(f"coletar_dados: {erro}", file=sys.stderr)
        sys.exit(1)
