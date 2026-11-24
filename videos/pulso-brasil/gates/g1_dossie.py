"""G1: confere cada número do dossie.json contra a cópia local da fonte (fontes/), sem rede.

Uso: python3 -I g1_dossie.py <pasta_episodio> [--travar]
Sem --travar (o pipeline), toda cópia usada já tem de estar em fontes_sha256: a trava vem do
dossiê de origem e não é criada numa cópia descartável. --travar grava as travas que faltam.
Cada linha declara como se prova, e a primeira regra que casar vale:
- "json_campo": {"arquivo", "caminho": [chaves]} -> o valor no JSON é igual a "numero".
- "json_moda": {"arquivo", "campo", "contagem": "k/n"} -> o valor mais comum de "campo" entre as
  entradas do JSON tem dia igual a "numero" e aparece k vezes em n.
- "snapshot": "fontes/<arquivo>" -> "trecho_literal" está no texto da cópia e "numero" está no trecho.
O sha256 de cada cópia fica em dossie["fontes_sha256"] (gravado com --travar); cópia alterada
depois reprova. Os "derivados" são recalculados, duas casas: "A / B - 1" (em %) ou "A / B" (razão, que
pode ser usada por um derivado seguinte).
Falha fecha: qualquer linha sem prova sai com código 1 e não grava nada.
"""
import collections, hashlib, html, json, os, re, sys

TRAVAR = "--travar" in sys.argv[2:]
EP = os.path.realpath(sys.argv[1])
CAMINHO = os.path.join(EP, "dossie.json")
dossie = json.load(open(CAMINHO, encoding="utf-8"))
falhas, travas = [], dict(dossie.get("fontes_sha256", {}))


def arquivo(rel):
    p = os.path.realpath(os.path.join(EP, rel))
    if not p.startswith(os.path.join(EP, "fontes") + os.sep) or not os.path.isfile(p):
        raise ValueError(f"cópia ausente ou fora de fontes/: {rel}")
    dado = open(p, "rb").read()
    sha = hashlib.sha256(dado).hexdigest()
    if rel not in travas and not TRAVAR:
        raise ValueError(f"{rel} sem trava em fontes_sha256; trave na pasta do episódio com --travar")
    if travas.setdefault(rel, sha) != sha:
        raise ValueError(f"{rel} mudou depois de travado (sha256 {sha[:12]} != {travas[rel][:12]})")
    return dado.decode("utf-8", errors="ignore"), p


def texto(rel):
    t, p = arquivo(rel)
    if p.endswith((".html", ".htm")):
        t = re.sub(r"(?s)<(script|style|noscript|svg)\b.*?</\1>", " ", t)
        t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return " ".join(t.split())


def formas(n):
    """Formas escritas aceitas de um número: 135.2 -> 135,2 / 135,20 / 135.20; -0.37 -> -0,37."""
    base = {repr(n), str(n)}
    if isinstance(n, float):
        for casas in (1, 2, 3, 4):
            base.add(f"{n:.{casas}f}")
    if isinstance(n, int) or (isinstance(n, float) and n.is_integer()):
        base.add(str(int(n)))
    # milhar no padrão brasileiro: 5508.23 -> 5.508,23
    milhar = {f"{n:,.{c}f}".replace(",", "_").replace(".", ",").replace("_", ".") for c in (0, 1, 2) if abs(n) >= 1000}
    return {b.replace(".", ",") for b in base} | base | milhar


def confere(l):
    n = l["numero"]
    if "json_campo" in l:
        c = l["json_campo"]
        v = json.loads(arquivo(c["arquivo"])[0])
        for k in c["caminho"]:
            v = v[k]
        if v != n:
            raise ValueError(f"json_campo {c['caminho']} = {v!r}, dossiê diz {n!r}")
        return "json_campo"
    if "json_moda" in l:
        c = l["json_moda"]
        v = json.loads(arquivo(c["arquivo"])[0])
        valores = [e[c["campo"]] for e in v.values()]
        moda, k = collections.Counter(valores).most_common(1)[0]
        if int(str(moda)[-2:]) != n or f"{k}/{len(valores)}" != c["contagem"]:
            raise ValueError(f"json_moda: moda {moda} em {k}/{len(valores)}, dossiê diz dia {n} em {c['contagem']}")
        return "json_moda"
    if "snapshot" in l:
        t, trecho = texto(l["snapshot"]), " ".join(l["trecho_literal"].split())
        if trecho not in t:
            raise ValueError(f"trecho_literal não está em {l['snapshot']}: {trecho[:70]!r}")
        if not any(re.search(r"(?<![\d.,])" + re.escape(f) + r"0*(?!\d)", trecho) for f in formas(n)):
            raise ValueError(f"número {n} não aparece no trecho")
        return "snapshot"
    raise ValueError("sem regra de prova (json_campo, json_moda ou snapshot)")


ids = {}
for l in dossie.get("linhas", []):
    try:
        modo = confere(l)
        ids[l["id"]] = l["numero"]
        print(f"ok   {l['id']}: {l['numero']} ({modo})")
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
        falhas.append(f"{l.get('id', '?')}: {e}")
        print(f"FALHA {l.get('id', '?')}: {e}")

for dv in dossie.get("derivados", []):
    try:
        a, b = (ids[i] for i in dv["de"])
        f = dv["formula"].replace(" ", "")
        if re.fullmatch(r"[^/]+/[^/]+-1", f):
            calc = round((a / b - 1) * 100, 2)
        elif re.fullmatch(r"[^/\-]+-[^/\-]+", f):
            calc = round(a - b, 2)  # diferença na mesma unidade (ex.: R$/sc entre praças), 28/10
        elif re.fullmatch(r"[^/\-]+/[^/\-]+", f):
            calc = round(a / b, 2)  # razão (ex.: R$/ha ÷ sc/ha = R$/sc); vira id para derivados seguintes
            ids[dv["id"]] = calc
        else:
            raise ValueError(f"fórmula não suportada: {dv['formula']}")
        if calc != dv["valor"]:
            raise ValueError(f"recalculado {calc}, dossiê diz {dv['valor']}")
        print(f"ok   {dv['id']}: {dv['valor']} (derivado)")
    except (ValueError, KeyError, ZeroDivisionError) as e:
        falhas.append(f"{dv.get('id', '?')}: {e}")
        print(f"FALHA {dv.get('id', '?')}: {e}")

for af in dossie.get("afirmacoes", []):  # Pulso Brasil 28/10: frase sem número, provada por trecho literal da fonte
    try:
        if " ".join(af["trecho_literal"].split()) not in texto(af["snapshot"]):
            raise ValueError(f"trecho_literal não está em {af['snapshot']}: {af['trecho_literal'][:70]!r}")
        print(f"ok   {af['id']}: afirmação (snapshot)")
    except (ValueError, KeyError) as e:
        falhas.append(f"{af.get('id', '?')}: {e}")
        print(f"FALHA {af.get('id', '?')}: {e}")

if not dossie.get("linhas"):
    falhas.append("dossiê sem linhas")

# numeros_chave alimentam o g_repeticao: cada um tem de ser número provado aqui (linha ou derivado),
# senão o autor declara qualquer valor e o anti-repetição vira enfeite.
caminho_ep = os.path.join(EP, "episodio.json")
if os.path.isfile(caminho_ep):
    provados = {round(float(v), 4) for v in ids.values()}
    provados |= {round(float(dv["valor"]), 4) for dv in dossie.get("derivados", []) if "valor" in dv}
    chave = json.load(open(caminho_ep, encoding="utf-8")).get("numeros_chave") or []
    if not chave:
        falhas.append("episodio.json sem numeros_chave")
    for item in chave:
        if round(float(item.get("numero", "nan")), 4) not in provados:
            falhas.append(f"numeros_chave {item.get('numero')!r} não é linha nem derivado provado do dossiê")
            print(f"FALHA numeros_chave {item.get('numero')!r}: fora do dossiê")
if falhas:
    print(f"G1 reprovado: {len(falhas)} falha(s)", file=sys.stderr)
    sys.exit(1)
if TRAVAR and travas != dossie.get("fontes_sha256"):
    dossie["fontes_sha256"] = travas
    json.dump(dossie, open(CAMINHO, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"G1 aprovado: {len(ids)} linhas e {len(dossie.get('derivados', []))} derivado(s), {len(travas)} cópias travadas")
