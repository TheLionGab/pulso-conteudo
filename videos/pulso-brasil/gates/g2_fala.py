"""G2: o texto falado não tem dígito, e todo comparativo tem linha de comparação no dossiê.

Uso: python3 -I g2_fala.py <pasta_episodio>   (lê audio/roteiro.py e dossie.json)
Também é chamado pelo montar.py antes de escrever qualquer saída (checar()).
Comparativo é palavra de COMPARATIVOS. Cada ocorrência precisa de uma entrada em
dossie["comparativos"]: {"trecho": pedaço da fala que contém a palavra, "ids": [linhas do dossiê]},
com todos os ids existentes em "linhas" ou "derivados". Falha fecha (código 1).
"""
import json, os, re, sys

COMPARATIVOS = re.compile(
    r"\b(recordes?|maior(?:es)?|menor(?:es)?|mínim[oa]s?|máxim[oa]s?|pior(?:es)?|melhor(?:es)?|"
    r"lidera\w*|líder(?:es)?|mais alt[oa]s?|mais baix[oa]s?|inédit[oa]s?)\b",
    re.IGNORECASE,
)


def falhas_de(roteiro, parse, dossie):
    ids = {l["id"] for l in dossie.get("linhas", [])} | {d["id"] for d in dossie.get("derivados", [])}
    cobertos = dossie.get("comparativos", [])
    falhas = []
    for c in cobertos:
        sem = [i for i in c.get("ids", []) if i not in ids]
        if not c.get("ids") or sem:
            falhas.append(f"comparativo {c.get('trecho')!r}: ids ausentes no dossiê {sem or '(lista vazia)'}")
    for i, (_, texto, _) in enumerate(roteiro):
        fala = " ".join(u["fala"] for u in parse(texto))
        for d in re.finditer(r"\d+", fala):
            falhas.append(f"seg {i:03d}: dígito na fala {fala[max(0, d.start() - 25):d.end() + 25]!r}")
        for m in COMPARATIVOS.finditer(fala):
            ok = any(m.group(0).lower() in c["trecho"].lower() and c["trecho"].lower() in fala.lower() for c in cobertos)
            if not ok:
                falhas.append(f"seg {i:03d}: comparativo {m.group(0)!r} sem entrada em dossie.comparativos")
    return falhas


def checar(roteiro, parse, dossie_path):
    falhas = falhas_de(roteiro, parse, json.load(open(dossie_path, encoding="utf-8")))
    if falhas:
        for f in falhas:
            print(f"FALHA {f}", file=sys.stderr)
        sys.exit(f"G2 reprovado: {len(falhas)} falha(s); nada foi escrito")
    print(f"G2 aprovado: {len(roteiro)} segmentos, fala sem dígito, comparativos com id")


if __name__ == "__main__":
    ep = os.path.abspath(sys.argv[1])
    sys.path.insert(0, os.path.join(ep, "audio"))
    from roteiro import ROTEIRO, parse

    checar(ROTEIRO, parse, os.path.join(ep, "dossie.json"))
