"""Coleta determinística dos dados do episódio diário: o modelo não busca nem transcreve dado.

Uso:
  python3 -I coletar_dados.py <pasta_do_dia> <AAAA-MM-DD> --trava <arquivo>   grava fontes/ e a trava
  python3 -I coletar_dados.py --conferir <pasta_do_dia> --trava <arquivo>     confere depois do modelo

Grava em <pasta_do_dia>/fontes/:
  bcb-ptax.json     PTAX venda dos 15 dias até o dia (Banco Central, Olinda), bytes da resposta.
  pulso-imea.json   IMEA soja e milho de MT na semana do último pregão, e as praças da soja nesse dia
                    (public.mercado_quotes do Supabase do Pulso, REST só leitura, service role).
  pulso-imea.sql    A mesma leitura em SQL e as URLs REST usadas, para quem revisar refazer.
Fontes OPCIONAIS (mesmo banco do app e INMET), cada uma com o JSON e a consulta registrada ao lado. Ausente,
vazia ou com erro, a fonte é pulada e a coleta segue; só PTAX e IMEA derrubam a coleta:
  pulso-mercado.json/.sql      public.mercado_quotes do último pregão: todas as culturas e papéis (imea, praça),
                               com o pregão anterior e o resumo das praças (média, maior, menor, distância à média).
  pulso-referencias.json/.sql  mercado.market_observations PUBLIC_PRICE: referências (DERAL e afins) e a faixa
                               agregada das ofertas de compra (sem nome de comprador nem id de oferta).
  pulso-insumos.json/.sql      cotacoes.v_insumos_precos_vigentes (insumos, Conab MT) com a variação.
  pulso-noticias.json/.sql     noticias.artigos das últimas 72 h (manchetes).
  inmet-avisos.json/.consulta.txt  avisos ativos do INMET com município de MT (API pública do INMET).
E a trava (--trava, FORA da pasta do dia, onde o modelo não escreve): sha256 dos arquivos obrigatórios e dos
opcionais que foram gravados. O --conferir reprova se algum mudou ou sumiu, ou se fontes/ ganhou qualquer
arquivo (nem link simbólico).

Ambiente: SUPABASE_SERVICE_ROLE_KEY (obrigatória; nunca impressa nem gravada) e SUPABASE_URL
(padrão: projeto do Pulso). Mac (agendado.sh) e nuvem (pulso-brasil-diario.yml) usam este mesmo caminho.
Saída: 0 coletou; 3 sem dado novo para episódio (grava sem-episodio.txt com o motivo); 1 erro.
"""
import datetime as dt
import hashlib
import json
import os
import re
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
# Fonte opcional: nome -> (dados, consulta registrada). Os dois arquivos existem juntos ou nenhum existe.
OPCIONAIS = {
    "mercado": ("fontes/pulso-mercado.json", "fontes/pulso-mercado.sql"),
    "referencias": ("fontes/pulso-referencias.json", "fontes/pulso-referencias.sql"),
    "insumos": ("fontes/pulso-insumos.json", "fontes/pulso-insumos.sql"),
    "noticias": ("fontes/pulso-noticias.json", "fontes/pulso-noticias.sql"),
    "inmet": ("fontes/inmet-avisos.json", "fontes/inmet-avisos.consulta.txt"),
}
ARQUIVOS_OPCIONAIS = tuple(a for par in OPCIONAIS.values() for a in par)
CONHECIDOS = frozenset(ARQUIVOS) | frozenset(ARQUIVOS_OPCIONAIS)
LIMITE_LINHAS = 1000  # teto padrão do PostgREST do Supabase: resposta no teto pode estar cortada
URL_INMET = "https://apiprevmet3.inmet.gov.br/avisos/ativos"
TOTAL_MUNICIPIOS_MT = 142
SEVERIDADE_INMET = {6: "Perigo potencial", 7: "Perigo", 8: "Grande perigo"}


class SemEpisodio(Exception):
    pass


class SemFonte(Exception):
    """Fonte opcional sem dado utilizável: a coleta segue sem ela."""


class ErroFonte(RuntimeError):
    """Falha de leitura. A mensagem pode levar URL e corpo da resposta; só `categoria` (HTTP 404, URLError,
    resposta no teto) é segura para log público."""

    def __init__(self, mensagem, categoria):
        super().__init__(mensagem)
        self.categoria = categoria


def sha256(caminho):
    return hashlib.sha256(Path(caminho).read_bytes()).hexdigest()


def baixar(url, cabecalhos=None, tentativas=3, espera=30):
    """GET com nova tentativa; o erro nunca leva cabeçalho (a chave não vaza em log)."""
    ultimo = categoria = "sem resposta"
    for n in range(tentativas):
        try:
            with urlopen(Request(url, headers=cabecalhos or {}), timeout=60) as r:
                return r.read()
        except HTTPError as e:
            categoria = f"HTTP {e.code}"
            ultimo = f"{categoria} {e.read().decode(errors='replace')[:200]}"
            if 400 <= e.code < 500 and e.code != 429:
                break
        except (URLError, TimeoutError, OSError) as e:
            ultimo = categoria = type(e).__name__
        if n + 1 < tentativas:
            time.sleep(espera)
    raise ErroFonte(f"{url.split('?')[0]}: {ultimo}", categoria)


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


class Contexto:
    """O que cada fonte opcional precisa: o dia, a base do Supabase e a chave (que nunca sai daqui)."""

    def __init__(self, dia, base, chave):
        self.dia, self.base, self.chave = dia, base, chave

    def dias_antes(self, n):
        return (dt.date.fromisoformat(self.dia) - dt.timedelta(days=n)).isoformat()

    def ler(self, consulta, schema=None):
        """GET REST (PostgREST) só leitura; schema diferente de public vai em Accept-Profile."""
        cab = {"apikey": self.chave, "Authorization": f"Bearer {self.chave}", "Accept": "application/json"}
        if schema:
            cab["Accept-Profile"] = schema
        # Fonte opcional não merece 3 tentativas de 30 s: 2 de 5 s.
        linhas = json.loads(baixar(f"{self.base}/rest/v1/{consulta}", cab, tentativas=2, espera=5), parse_float=float)
        if not isinstance(linhas, list):
            raise ErroFonte(f"resposta inesperada em {consulta.split('?')[0]}", "resposta fora do formato")
        return linhas

    def ler_completo(self, consulta, schema=None):
        """Como ler(), mas resposta no teto de linhas é recusada (pode estar cortada)."""
        linhas = self.ler(consulta, schema)
        if len(linhas) >= LIMITE_LINHAS:
            raise ErroFonte(f"{consulta.split('?')[0]}: {len(linhas)} linhas, no teto do PostgREST; pode estar cortada",
                            "resposta no teto de linhas (pode estar cortada)")
        return linhas


def texto_consulta(titulo, sqls, rests):
    corpo = f"-- {titulo} (coletar_dados.py, só leitura). Refazer = rodar as consultas.\n" + ";\n".join(sqls) + ";\n"
    return corpo + "\n-- Mesma leitura por REST (PostgREST):\n" + "\n".join(f"-- {r}" for r in rests) + "\n"


def agora_utc():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S+00")


def coletar_mercado(ctx):
    """Todas as culturas e papéis de public.mercado_quotes no último pregão, com o pregão anterior."""
    filtro = "papel=in.(imea,praca)"
    tab = "mercado_quotes"
    ultimo = ctx.ler(f"{tab}?select=data_publicacao&{filtro}&data_publicacao=lte.{ctx.dia}&order=data_publicacao.desc&limit=1")
    if not ultimo:
        raise SemFonte("mercado_quotes sem pregão até o dia")
    data = str(ultimo[0]["data_publicacao"])[:10]
    if (dt.date.fromisoformat(ctx.dia) - dt.date.fromisoformat(data)).days > IDADE_MAX_DIAS:
        raise SemFonte(f"mercado_quotes de {data} é velho demais para {ctx.dia}")
    colunas = "cultura,papel,localidade,source,valor,unidade,data_publicacao"
    q_dia = f"{tab}?select={colunas}&{filtro}&data_publicacao=eq.{data}&order=cultura.asc,papel.asc,localidade.asc"
    linhas = ctx.ler_completo(f"{q_dia}&limit={LIMITE_LINHAS}")
    q_ant = f"select=data_publicacao&{filtro}&data_publicacao=lt.{data}&order=data_publicacao.desc&limit=1"
    anterior = ctx.ler(f"{tab}?{q_ant}")
    data_ant, valores_ant = None, {}
    if anterior:
        data_ant = str(anterior[0]["data_publicacao"])[:10]
        for l in ctx.ler_completo(f"{tab}?select={colunas}&{filtro}&data_publicacao=eq.{data_ant}&limit={LIMITE_LINHAS}"):
            valores_ant[(l["cultura"], l["papel"], l["localidade"], l.get("source") or "sem-fonte")] = float(l["valor"])

    mercado = {}
    for l in linhas:
        cultura, papel, local, fonte = str(l["cultura"]), str(l["papel"]), str(l["localidade"]), str(l.get("source") or "sem-fonte")
        reg = {"valor": float(l["valor"]), "unidade": str(l["unidade"]), "data": data}
        ant = valores_ant.get((cultura, papel, local, fonte))
        if ant is not None:
            reg["anterior"] = {"data": data_ant, "valor": ant}
        mercado.setdefault(cultura, {}).setdefault(papel, {}).setdefault(local, {})[fonte] = reg
    if not mercado:
        raise SemFonte(f"mercado_quotes sem linhas em {data}")

    resumo = {}
    for cultura, papeis in mercado.items():
        grupos = {}
        for local, fontes in papeis.get("praca", {}).items():
            for fonte, reg in fontes.items():
                grupos.setdefault((reg["unidade"], fonte), []).append((local, reg))
        if not grupos:
            continue
        (unidade, fonte), membros = max(grupos.items(), key=lambda kv: (len(kv[1]), kv[0]))
        if len(membros) < 3:
            continue
        media = round(sum(r["valor"] for _, r in membros) / len(membros), 2)
        ordem = sorted(membros, key=lambda m: (-m[1]["valor"], m[0]))
        for local, reg in membros:
            reg["distancia_media"] = round(reg["valor"] - media, 2)
        resumo[cultura] = {
            "unidade": unidade, "fonte": fonte, "n_pracas": len(membros), "media": media,
            "maior": {"localidade": ordem[0][0], "valor": ordem[0][1]["valor"]},
            "menor": {"localidade": ordem[-1][0], "valor": ordem[-1][1]["valor"]},
            "amplitude": round(ordem[0][1]["valor"] - ordem[-1][1]["valor"], 2),
        }

    sql = [
        f"select cultura, papel, localidade, source, valor, unidade, data_publicacao from public.{tab} "
        f"where papel in ('imea','praca') and data_publicacao = date '{data}' order by cultura, papel, localidade",
    ]
    if data_ant:
        sql.append(f"select cultura, papel, localidade, source, valor from public.{tab} "
                   f"where papel in ('imea','praca') and data_publicacao = date '{data_ant}'")
    dados = {
        "consulta_em": agora_utc(),
        "origem": "Pulso do Campo, produção, leitura só leitura por REST (coletar_dados.py); dado primário IMEA e praças do app",
        "tabela": f"public.{tab}", "data": data, "data_anterior": data_ant,
        "mercado": mercado, "resumo_pracas": resumo, "sql": sql,
    }
    return dados, texto_consulta("public.mercado_quotes, último pregão", sql, [f"GET {ctx.base}/rest/v1/{q_dia}&limit={LIMITE_LINHAS}"])


def _ref_date(meta, observado):
    """metadata.ref_date (AAAA-MM-DD válida), como mercado.observation_ref_date; sem ela a linha não vale."""
    texto = meta.get("ref_date")
    if not isinstance(texto, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", texto):
        return None
    try:
        dia = dt.date.fromisoformat(texto)
        local = (dt.datetime.fromisoformat(observado) - dt.timedelta(hours=4)).date()  # Cuiabá, UTC-4
    except ValueError:
        return None
    if meta.get("observed_at_basis") == "collection" and dia > local:
        return None
    return texto


# O metadata inteiro (jsonb de coletor) não sai do banco: só estas chaves, como colunas m_<chave> (PostgREST: alias:coluna->>chave).
CHAVES_META = ("series", "place", "product", "source_label", "ref_date", "observed_at_basis", "oferta_id")
# `extra` vem como objeto (->), não texto (->>): assim `fob: null` continua distinto de `fob` ausente e é recusado.
COLUNAS_META = ",".join([f"m_{k}:metadata->>{k}" for k in CHAVES_META] + ["m_extra:metadata->extra"])


def com_metadata(linha):
    """Remonta o `metadata` que o resto do coletor lê a partir das colunas m_*, sem chave nula (como no jsonb)."""
    meta = {k: linha[f"m_{k}"] for k in CHAVES_META if linha.get(f"m_{k}") is not None}
    extra = linha.get("m_extra")
    if isinstance(extra, dict) and "fob" in extra:
        meta["extra"] = {"fob": extra["fob"]}
    return {k: v for k, v in linha.items() if not k.startswith("m_")} | {"metadata": meta}


def coletar_referencias(ctx):
    """DERAL e afins (referências) e a faixa das ofertas de compra, de mercado.market_observations."""
    colunas = ("commodity,observed_at,received_at,value,unit," + COLUNAS_META + ","
               "market_sources!inner(source_name,can_be_named,active,default_trust_class),market_locations(municipality,uf)")
    base = (f"market_observations?select={colunas}&kind=eq.PUBLIC_PRICE&evidence_id=not.is.null&value=gt.0"
            "&market_sources.active=is.true")
    q_ofertas = f"{base}&metadata->>series=eq.gd_oferta&observed_at=gte.{ctx.dias_antes(4)}T00:00:00Z&order=observed_at.desc&limit={LIMITE_LINHAS}"
    q_outras = f"{base}&metadata->>series=neq.gd_oferta&observed_at=gte.{ctx.dias_antes(21)}T00:00:00Z&order=observed_at.desc&limit={LIMITE_LINHAS}"
    ofertas_brutas = [com_metadata(l) for l in ctx.ler(q_ofertas, "mercado")]
    outras_brutas = [com_metadata(l) for l in ctx.ler(q_outras, "mercado")]
    truncado = len(ofertas_brutas) >= LIMITE_LINHAS or len(outras_brutas) >= LIMITE_LINHAS

    def valida(l):
        """Mesmos filtros de public.referencia_cultura_fora_mt: fonte ativa e nomeável, BENCHMARK ou DERIVED, sem FOB."""
        fonte, meta = l.get("market_sources") or {}, l.get("metadata") or {}
        extra = meta.get("extra") if isinstance(meta.get("extra"), dict) else {}
        return (fonte.get("active") is True and fonte.get("can_be_named") is True
                and fonte.get("default_trust_class") in ("BENCHMARK", "DERIVED")
                and ("fob" not in extra or str(extra["fob"]).lower() == "true")
                and l.get("commodity") and float(l["value"]) > 0)

    def praca(l, preferir_local):
        meta, loc = l.get("metadata") or {}, l.get("market_locations") or {}
        cidade = f"{loc['municipality']}/{loc['uf']}" if loc.get("municipality") and loc.get("uf") else None
        place = str(meta.get("place") or "").strip() or None
        return (cidade or place) if preferir_local else (place or cidade)

    ref, ofertas = {}, {}
    for l in sorted((x for x in outras_brutas if valida(x)), key=lambda x: (x["observed_at"], x["received_at"]), reverse=True):
        meta = l["metadata"]
        dia_ref, lugar = _ref_date(meta, l["observed_at"]), praca(l, False)
        if not dia_ref or not lugar:
            continue
        serie = str(meta.get("series") or "sem-serie")
        alvo = ref.setdefault(l["commodity"], {}).setdefault(lugar, {})
        chave = f"{serie}|{meta.get('product') or ''}|{l['unit']}"
        if chave in alvo and alvo[chave]["data"] >= dia_ref:
            continue
        alvo[chave] = {"serie": serie, "produto": meta.get("product") or None, "valor": float(l["value"]), "unidade": l["unit"],
                       "data": dia_ref, "fonte": str(meta.get("source_label") or l["market_sources"].get("source_name") or ""),
                       "uf": (l.get("market_locations") or {}).get("uf")}

    por_oferta = {}  # (commodity, praça, unidade) -> {dia: {oferta_id: (instante, valor)}}
    for l in (x for x in ofertas_brutas if valida(x)):
        meta = l["metadata"]
        dia_ref, lugar, oid = _ref_date(meta, l["observed_at"]), praca(l, True), str(meta.get("oferta_id") or "").strip()
        if not dia_ref or not lugar or not oid:
            continue  # sem oferta_id não dá para contar oferta, só linha repetida do coletor
        dias = por_oferta.setdefault((l["commodity"], lugar, l["unit"]), {})
        atual = dias.setdefault(dia_ref, {}).get(oid)
        if atual is None or (l["observed_at"], l["received_at"]) > atual[0]:
            dias[dia_ref][oid] = ((l["observed_at"], l["received_at"]), float(l["value"]))
    for (cultura, lugar, unidade), dias in sorted(por_oferta.items()):
        recente = max(dias)
        valores = [v for _, v in dias[recente].values()]
        uf = lugar.rsplit("/", 1)[-1] if re.fullmatch(r".+/[A-Z]{2}", lugar) else None
        ofertas.setdefault(cultura, {})[lugar] = {"unidade": unidade, "data": recente, "n_ofertas": len(valores),
                                                  "valor_min": min(valores), "valor_max": max(valores), "uf": uf}
    if not ref and not ofertas:
        raise SemFonte("mercado.market_observations sem referência nem oferta válida")
    sql = [
        "select o.commodity, o.observed_at, o.received_at, o.value, o.unit, "
        + ", ".join(f"o.metadata->>'{k}' as m_{k}" for k in CHAVES_META) + ", o.metadata->'extra' as m_extra, "
        "s.source_name, l.municipality, l.uf "
        "from mercado.market_observations o join mercado.market_sources s using (source_id) "
        "left join mercado.market_locations l on l.ibge_code = o.location_ibge "
        "where o.kind = 'PUBLIC_PRICE' and o.evidence_id is not null and o.value > 0 and s.active "
        f"and o.metadata->>'series' = 'gd_oferta' and o.observed_at >= date '{ctx.dias_antes(4)}'",
        "-- idem com o.metadata->>'series' <> 'gd_oferta' e janela desde " + ctx.dias_antes(21),
    ]
    dados = {
        "consulta_em": agora_utc(),
        "origem": "Pulso do Campo, produção, mercado.market_observations (PUBLIC_PRICE), leitura só leitura por REST",
        "tabela": "mercado.market_observations",
        "aviso": "ofertas_compra é oferta de compra de um comprador, não preço de mercado; sem nome de comprador",
        "truncado": truncado, "referencias": ref, "ofertas_compra": ofertas, "sql": sql,
    }
    return dados, texto_consulta("mercado.market_observations", sql, [f"GET (Accept-Profile: mercado) {ctx.base}/rest/v1/{q_ofertas}",
                                                                      f"GET (Accept-Profile: mercado) {ctx.base}/rest/v1/{q_outras}"])


def coletar_insumos(ctx):
    """Preço vigente de insumos (Conab MT e afins) com a variação já calculada pelo app."""
    colunas = "slug,nome,categoria,localidade,valor,unidade,variacao_pct,fonte,vigente_em"
    q = (f"v_insumos_precos_vigentes?select={colunas}&vigente_em=gte.{ctx.dias_antes(60)}"
         f"&order=vigente_em.desc,slug.asc&limit={LIMITE_LINHAS}")
    linhas = ctx.ler_completo(q, "cotacoes")
    insumos = {}
    for l in linhas:
        reg = {"nome": str(l["nome"]), "categoria": l.get("categoria"), "valor": float(l["valor"]), "unidade": str(l["unidade"]),
               "variacao_pct": None if l.get("variacao_pct") is None else float(l["variacao_pct"]),
               "fonte": l.get("fonte"), "vigente_em": str(l["vigente_em"])[:10]}
        insumos.setdefault(str(l["slug"]), {}).setdefault(str(l["localidade"]), reg)  # 1ª = a mais recente
    if not insumos:
        raise SemFonte("sem insumo vigente nos últimos 60 dias")
    sql = [f"select {colunas} from cotacoes.v_insumos_precos_vigentes where vigente_em >= date '{ctx.dias_antes(60)}' "
           "order by vigente_em desc, slug"]
    dados = {"consulta_em": agora_utc(), "origem": "Pulso do Campo, cotacoes.v_insumos_precos_vigentes (Conab MT e afins), só leitura por REST",
             "tabela": "cotacoes.v_insumos_precos_vigentes", "insumos": insumos, "sql": sql}
    return dados, texto_consulta("cotacoes.v_insumos_precos_vigentes", sql, [f"GET (Accept-Profile: cotacoes) {ctx.base}/rest/v1/{q}"])


VOCAB_COMMODITIES = frozenset({"soja", "milho", "algodão", "algodao", "boi", "boi gordo", "café", "cafe", "trigo", "cana", "arroz",
                               "feijão", "feijao", "sorgo", "leite", "suíno", "suino", "frango", "fertilizantes", "câmbio", "cambio"})
VOCAB_REGIOES = frozenset({"mt", "mato grosso", "brasil", "centro-oeste", "sul", "sudeste", "norte", "nordeste", "mundo", "global"})


def fonte_limpa(valor):
    """Nome do veículo: só letras, espaço e ponto, até 40 caracteres. Fora disso, None (a manchete não entra)."""
    texto = " ".join(str(valor or "").split())
    return texto if re.fullmatch(r"(?:[^\W\d_]|[ .]){1,40}", texto) else None


def url_so_host(valor):
    """Só `https://host`: até 300 caracteres, sem usuário, porta, caminho, consulta nem fragmento. Fora disso, None."""
    texto = str(valor or "")
    m = re.fullmatch(r"https://([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)(?::443)?(?:[/?#]\S*)?", texto)
    return f"https://{m.group(1).lower()}" if m and len(texto) <= 300 else None


def _vocabulo(valor, vocab):
    texto = " ".join(str(valor or "").split()).lower()
    return texto if texto in vocab else None


def commodities_limpas(valor):
    """Até 8 itens do vocabulário curto ou alfanuméricos de até 30 caracteres; o resto é descartado."""
    itens = valor if isinstance(valor, list) else []
    limpos = (_vocabulo(i, VOCAB_COMMODITIES) for i in itens[:8] if isinstance(i, str))
    return list(dict.fromkeys(i for i in limpos if i))


def regiao_limpa(valor):
    return _vocabulo(valor, VOCAB_REGIOES) if isinstance(valor, str) else None


def coletar_noticias(ctx):
    """Manchetes das últimas 72 h de noticias.artigos (só título, fonte, link e data)."""
    q = (f"artigos?select=titulo,fonte,url,publicado_em,commodities,regiao&publicado_em=gte.{ctx.dias_antes(3)}T00:00:00Z"
         f"&publicado_em=lte.{ctx.dia}T23:59:59Z&order=publicado_em.desc&limit=40")
    artigos = []
    for l in ctx.ler(q, "noticias"):
        titulo = str(l.get("titulo") or "").strip()
        # O campo `fonte` do banco é texto livre (pode carregar instrução); a origem passa a ser o host do link.
        url = url_so_host(l.get("url"))
        fonte = url.removeprefix("https://") if url else None
        if not titulo or len(titulo) > 140 or re.search(r'[<>"\\]', titulo) or not fonte or not url:
            continue  # aspas e barra quebrariam a citação literal no JSON; fonte ou link fora do padrão não viram fonte
        artigos.append({"titulo": titulo, "fonte": fonte, "url": url, "publicado_em": str(l["publicado_em"])[:10],
                        "commodities": commodities_limpas(l.get("commodities")), "regiao": regiao_limpa(l.get("regiao"))})
    if not artigos:
        raise SemFonte("sem manchete utilizável nas últimas 72 h")
    sql = [f"select titulo, fonte, url, publicado_em, commodities, regiao from noticias.artigos where publicado_em >= date '{ctx.dias_antes(3)}' "
           "order by publicado_em desc limit 40"]
    dados = {"consulta_em": agora_utc(), "origem": "Pulso do Campo, noticias.artigos, só leitura por REST",
             "tabela": "noticias.artigos", "artigos": artigos, "sql": sql}
    return dados, texto_consulta("noticias.artigos", sql, [f"GET (Accept-Profile: noticias) {ctx.base}/rest/v1/{q}"])


def coletar_inmet(ctx):
    """Avisos ativos do INMET que cobrem município de MT no dia ou nos 3 dias seguintes."""
    corpo = json.loads(baixar(URL_INMET, {"Accept": "application/json", "User-Agent": "Mozilla/5.0 (compatible; PulsoBrasil/1.0)"},
                              tentativas=2, espera=5))
    if not isinstance(corpo, dict):
        raise SemFonte("resposta do INMET fora do formato")
    fim_janela = (dt.date.fromisoformat(ctx.dia) + dt.timedelta(days=3)).isoformat()
    avisos, municipios = {}, set()
    for aviso in [*(corpo.get("hoje") or []), *(corpo.get("futuro") or [])]:
        if not isinstance(aviso, dict) or aviso.get("id") is None:
            continue
        mt = {g.strip() for g in str(aviso.get("geocodes") or "").split(",") if re.fullmatch(r"51\d{5}", g.strip())}
        inicio, fim = str(aviso.get("data_inicio") or "")[:10], str(aviso.get("data_fim") or aviso.get("data_inicio") or "")[:10]
        if not mt or not (inicio and fim) or fim < ctx.dia or inicio > fim_janela:
            continue
        tipo = str(aviso.get("descricao") or "").strip()
        try:
            sev = int(aviso.get("id_severidade"))
        except (TypeError, ValueError):
            sev = None
        avisos[str(aviso["id"])] = {
            "tipo": tipo if re.fullmatch(r"[^\W\d_]+(?: [^\W\d_]+)*", tipo) and len(tipo) <= 40 else "aviso meteorológico",
            "severidade": SEVERIDADE_INMET.get(sev, "não informada"), "inicio": inicio, "fim": fim, "municipios_mt": len(mt),
            "url": f"https://alertas2.inmet.gov.br/{aviso['id']}"}
        municipios |= mt
    if not avisos:
        raise SemFonte("sem aviso do INMET para Mato Grosso na janela")
    consulta = f"GET {URL_INMET}\n# Filtro: geocódigo IBGE de MT (51xxxxx), aviso que termina em {ctx.dia} ou depois e começa até {fim_janela}.\n"
    dados = {"consulta_em": agora_utc(), "origem": "INMET, avisos ativos (API pública)", "url": URL_INMET, "dia": ctx.dia,
             "total_municipios_mt": TOTAL_MUNICIPIOS_MT, "municipios_mt_com_aviso": len(municipios), "avisos": dict(sorted(avisos.items()))}
    return dados, consulta


COLETORES = (("mercado", coletar_mercado), ("referencias", coletar_referencias), ("insumos", coletar_insumos),
             ("noticias", coletar_noticias), ("inmet", coletar_inmet))


def gravar_opcional(pasta, nome, dados, consulta):
    arq_dados, arq_consulta = OPCIONAIS[nome]
    (pasta / arq_dados).write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (pasta / arq_consulta).write_text(consulta, encoding="utf-8")


def coletar_opcionais(ctx, pasta, coletores=COLETORES):
    """Roda cada fonte opcional; nenhuma falha aqui derruba a coleta. Devolve {nome: 'ok' | 'vazia: ..' | 'ausente: ..'}."""
    resultado = {}
    for nome, coletor in coletores:
        try:
            dados, consulta = coletor(ctx)
        except SemFonte as motivo:
            resultado[nome] = f"vazia: {motivo}"
        except Exception as erro:  # opcional nunca derruba. O estado vai a log público: só a categoria do erro
            # (código HTTP ou tipo), nunca corpo de resposta, URL ou mensagem livre.
            resultado[nome] = f"ausente: {erro.categoria if isinstance(erro, ErroFonte) else type(erro).__name__}"
        else:
            gravar_opcional(pasta, nome, dados, consulta)
            resultado[nome] = "ok"
    return resultado


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


def pares_completos(nomes):
    """Cada fonte opcional tem os dois arquivos (dados e consulta) ou nenhum."""
    for nome, (dados, consulta) in OPCIONAIS.items():
        if (dados in nomes) != (consulta in nomes):
            raise RuntimeError(f"fonte opcional {nome} pela metade (dados e consulta andam juntos)")


def gravar_trava(pasta, trava):
    presentes = arquivos_em_fontes(pasta)
    extras = [a for a in presentes if a not in CONHECIDOS]
    if extras:
        raise RuntimeError(f"fontes/ tem arquivo que a coleta não gravou: {', '.join(extras)}")
    pares_completos(presentes)
    arquivos = [*ARQUIVOS, *(a for a in ARQUIVOS_OPCIONAIS if a in presentes)]
    trava.parent.mkdir(parents=True, exist_ok=True)
    trava.write_text("".join(f"{sha256(pasta / rel)}  {rel}\n" for rel in arquivos))
    return arquivos


def conferir(pasta, trava):
    """Falha se fonte mudou, sumiu ou se fontes/ ganhou qualquer arquivo depois da coleta."""
    fora_da_pasta(pasta, trava)
    travas = dict(reversed(linha.split("  ", 1)) for linha in trava.read_text().splitlines())
    if not set(ARQUIVOS) <= set(travas) or not set(travas) <= CONHECIDOS:
        raise RuntimeError("trava da coleta incompleta")
    pares_completos(set(travas))
    atuais = arquivos_em_fontes(pasta)
    extras = [a for a in atuais if a not in travas]
    if extras:
        raise RuntimeError(f"arquivo novo em fontes/ depois da coleta (o modelo não pode criar fonte): {', '.join(extras)}")
    for rel, sha in travas.items():
        if rel not in atuais:
            raise RuntimeError(f"{rel} sumiu depois da coleta")
        if sha256(pasta / rel) != sha:
            raise RuntimeError(f"{rel} mudou depois da coleta (o modelo não pode alterar fonte)")
    print("fontes da coleta intactas:", ", ".join(travas))


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
    sobras = [a for a in arquivos_em_fontes(pasta) if a not in CONHECIDOS]
    if sobras:  # coleta nova não herda arquivo de execução anterior
        raise RuntimeError(f"fontes/ já tem arquivo que não é da coleta: {', '.join(sobras)}")
    for rel in ARQUIVOS_OPCIONAIS:  # opcional de execução anterior é velho: só entra o que esta coleta gravar
        (pasta / rel).unlink(missing_ok=True)
    try:
        coletar_ptax(dia, pasta / "fontes/bcb-ptax.json")
        coletar_imea(dia, base, chave, pasta)
    except SemEpisodio as motivo:
        (pasta / "sem-episodio.txt").write_text(f"{motivo}\n")
        print(f"Sem episódio: {motivo}")
        return 3
    opcionais = coletar_opcionais(Contexto(dia, base, chave), pasta)
    gravar_trava(pasta, trava)
    imea = json.loads((pasta / "fontes/pulso-imea.json").read_text())
    print(f"coleta ok: {dia}; PTAX {len(json.loads((pasta / 'fontes/bcb-ptax.json').read_text())['value'])} dias; "
          f"IMEA soja {sorted(imea['imea_mt']['soja'])[-1]}, {len(imea['imea_mt']['soja'])} pregões; "
          f"{len(imea[[k for k in imea if k.startswith('pracas_soja_')][0]])} praças")
    for nome, estado in opcionais.items():
        print(f"fonte opcional {nome}: {estado}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except (RuntimeError, ValueError, KeyError, IndexError, OSError) as erro:
        print(f"coletar_dados: {erro}", file=sys.stderr)
        sys.exit(1)
