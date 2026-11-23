#!/usr/bin/env python3
"""Gera o anúncio "Preço da sua praça" para uma cidade e um produto.

Fluxo:
  1. Lê os preços de um JSON (offline) ou baixa do Supabase (--baixar).
  2. Monta os dados do vídeo (ranking, diferença, total em 10 mil sacas).
  3. Escreve index.html a partir de template.html.
  4. Com --render, chama o HyperFrames e grava out/<produto>-<cidade>-<data>.mp4.

Exemplos:
  python3 gerar.py --dados dados/imea-2026-11-19.json --produto soja --cidade Sorriso --render
  python3 gerar.py --baixar --produto milho --todas --render
     (--baixar lê SUPABASE_URL e SUPABASE_ANON_KEY do ambiente; só faz GET)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import unicodedata
import urllib.request
from datetime import date
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SACAS_REFERENCIA = 10_000
RANKING_MAX = 6
HYPERFRAMES = os.environ.get("HYPERFRAMES_VERSION", "0.9.86")

ROTULOS = {"soja": "Soja", "milho": "Milho"}


def slug(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return "-".join(sem_acento.lower().split())


def data_br(iso: str) -> str:
    a, m, d = iso[:10].split("-")
    return f"{d}/{m}/{a}"


def milhar(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def montar_ranking(precos: dict[str, float], cidade: str) -> list[dict]:
    """Topo 3 + a cidade + os 2 mais baixos, sem repetir, do maior para o menor."""
    ordem = sorted(precos.items(), key=lambda kv: (-kv[1], kv[0]))
    escolhidas: list[str] = []
    for nome, _ in ordem[:3] + [(cidade, precos[cidade])] + ordem[-2:]:
        if nome not in escolhidas:
            escolhidas.append(nome)
    # topo 3 + cidade + piso 2 nunca passa de RANKING_MAX (6)
    linhas = sorted(((n, precos[n]) for n in escolhidas), key=lambda kv: (-kv[1], kv[0]))
    maior = linhas[0][1]
    menor = linhas[-1][1]
    base = menor - max((maior - menor) * 0.6, 1.0)
    return [
        {
            "cidade": n,
            "valor": round(v, 2),
            "largura": round((v - base) / (maior - base), 4),
            "eu": n == cidade,
            "topo": i == 0 and n != cidade,
        }
        for i, (n, v) in enumerate(linhas)
    ]


def montar_comparacao(precos: dict[str, float], cidade: str) -> dict:
    """Se a cidade não é a que paga mais, compara com a que paga mais.
    Se é a que paga mais, compara com a que paga menos (mensagem positiva)."""
    meu = precos[cidade]
    topo_nome, topo = max(precos.items(), key=lambda kv: (kv[1], kv[0]))
    piso_nome, piso = min(precos.items(), key=lambda kv: (kv[1], kv[0]))
    if topo_nome != cidade and topo > meu:
        diferenca = round(topo - meu, 2)
        titulo = f"{topo_nome} paga mais"
        subtitulo = f"por saca do que {cidade}"
    else:
        diferenca = round(meu - piso, 2)
        titulo = f"{cidade} lidera hoje"
        subtitulo = f"por saca acima de {piso_nome}"
    return {
        "diferenca": diferenca,
        "titulo": titulo,
        "subtitulo": subtitulo,
        "total": round(diferenca * SACAS_REFERENCIA),
        "sacas_rotulo": milhar(SACAS_REFERENCIA),
    }


def montar_dados(base: dict, produto: str, cidade: str) -> dict:
    precos = base["produtos"][produto]
    if cidade not in precos:
        raise SystemExit(f"Cidade sem preço de {produto}: {cidade}. Opções: {', '.join(sorted(precos))}")
    return {
        "produto": produto,
        "produto_rotulo": ROTULOS.get(produto, produto.capitalize()),
        "cidade": cidade,
        "preco": round(precos[cidade], 2),
        "fonte": base["fonte"],
        "data": data_br(base["data_publicacao"]),
        "ranking": montar_ranking(precos, cidade),
        "comparacao": montar_comparacao(precos, cidade),
    }


def escrever_index(dados: dict) -> Path:
    template = (AQUI / "molde" / "template.html").read_text(encoding="utf-8")
    marcador = "/*__DADOS__*/ null"
    if marcador not in template:
        raise SystemExit("molde/template.html sem o marcador /*__DADOS__*/ null")
    html = template.replace(marcador, json.dumps(dados, ensure_ascii=False))
    destino = AQUI / "index.html"
    destino.write_text(html, encoding="utf-8")
    return destino


def renderizar(dados: dict, data_iso: str) -> Path:
    saida = AQUI / "out" / f"{dados['produto']}-{slug(dados['cidade'])}-{data_iso}.mp4"
    saida.parent.mkdir(exist_ok=True)
    temp = saida.with_name(saida.stem + ".parcial.mp4")
    cmd = ["npx", "--yes", f"hyperframes@{HYPERFRAMES}", "render", str(AQUI), "-o", str(temp), "-q", "delivery", "--quiet"]
    subprocess.run(cmd, check=True)
    temp.replace(saida)
    return saida


def baixar() -> dict:
    url = os.environ["SUPABASE_URL"].rstrip("/")
    chave = os.environ["SUPABASE_ANON_KEY"]
    cab = {"apikey": chave, "Authorization": f"Bearer {chave}", "Accept-Profile": "cotacoes"}

    def get(caminho: str) -> list:
        req = urllib.request.Request(f"{url}/rest/v1/{caminho}", headers=cab)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)

    comms = {c["id"]: c["slug"] for c in get("commodities?select=id,slug&slug=in.(soja,milho)")}
    ids = ",".join(str(i) for i in comms)
    principais = get(f"indicadores_imea?select=indicador_final_id,commodity_id&principal=eq.true&commodity_id=in.({ids})")
    por_indicador = {p["indicador_final_id"]: comms[p["commodity_id"]] for p in principais}
    inds = ",".join(str(i) for i in por_indicador)
    linhas = get(f"precos?select=indicador_final_id,localidade,valor,data_publicacao&indicador_final_id=in.({inds})")
    produtos: dict[str, dict[str, float]] = {}
    datas = []
    for l in linhas:
        if l["localidade"] == "Mato Grosso":
            continue
        produtos.setdefault(por_indicador[l["indicador_final_id"]], {})[l["localidade"]] = float(l["valor"])
        datas.append(l["data_publicacao"][:10])
    return {
        "fonte": "IMEA",
        "data_publicacao": max(datas),
        "consultado_em": date.today().isoformat(),
        "origem": "REST anon em cotacoes.precos (indicador principal)",
        "produtos": produtos,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    fonte = ap.add_mutually_exclusive_group(required=True)
    fonte.add_argument("--dados", type=Path, help="JSON de preços (ex.: dados/imea-2026-11-19.json)")
    fonte.add_argument("--baixar", action="store_true", help="baixa do Supabase e salva em dados/")
    ap.add_argument("--produto", default="soja", choices=["soja", "milho"])
    alvo = ap.add_mutually_exclusive_group(required=True)
    alvo.add_argument("--cidade")
    alvo.add_argument("--todas", action="store_true", help="um vídeo por cidade")
    ap.add_argument("--render", action="store_true", help="renderiza o MP4 (senão só escreve index.html)")
    a = ap.parse_args(argv)

    if a.baixar:
        base = baixar()
        arq = AQUI / "dados" / f"imea-{base['data_publicacao']}.json"
        arq.write_text(json.dumps(base, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"dados salvos: {arq}")
    else:
        base = json.loads(a.dados.read_text(encoding="utf-8"))

    cidades = sorted(base["produtos"][a.produto]) if a.todas else [a.cidade]
    for cidade in cidades:
        dados = montar_dados(base, a.produto, cidade)
        escrever_index(dados)
        if a.render:
            print(f"ok: {renderizar(dados, base['data_publicacao'])}")
        else:
            print(f"index.html pronto: {a.produto} · {cidade}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
