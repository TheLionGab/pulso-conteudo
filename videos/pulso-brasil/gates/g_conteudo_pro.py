"""G conteúdo Pro: o episódio não entrega conteúdo do Pulso Pro nem promete o que o Pro não pode prometer.

Uso: python3 -I g_conteudo_pro.py <pasta_episodio>   (lê episodio.json e dossie.json)
Também é chamado pelo conferir_episodio.py (agendador e CI). Falha fecha: qualquer achado sai com código 1.

Reprova se:
 a) uma linha do dossiê (ou derivado) usa `ofertas_compra` de pulso-referencias.json ou os campos
    n_ofertas / valor_min / valor_max (oferta de compra é conteúdo do Pro, em qualquer caminho de prova);
 b) algum texto do episódio (roteiro, cenas, legenda, legenda_instagram, selo, cta_final, título etc.) diz
    "grátis", "de graça" e afins, liga preço, desconto, teste ou prazo ao Pro/assinatura, ou promete
    resultado ("ganhe mais", "lucre", "lucro garantido").
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

CAMPOS_OFERTA = {"n_ofertas", "valor_min", "valor_max"}

# Sempre reprova: gratuidade explícita em qualquer texto do episódio.
GRATIS = re.compile(r"\b(gratis|gratuit[oa]s?|de graca)\b")
# Reprova só na frase que fala do app ou do Pro: "sem custo de frete" e "free on board" são fato de mercado.
GRATIS_APP = re.compile(r"\b(free|sem (?:custo|pagar|cobranca|mensalidade|pagamento)|custo zero|nada a pagar|nao paga)\b")
APP = re.compile(r"\b(pulso|app|aplicativo|assin\w*|baix[ea]\w*|plano|premium|mensalidade)\b")
# Sempre reprova: promessa direta ao espectador.
PROMESSA = re.compile(
    r"\bganhe mais\b|\b(?:voce vai|voce pode|vai|ira) (?:ganhar|lucrar)\b|\blucre\b|\blucro garantido\b|"
    r"\baumente (?:seu|sua|o|a|os|as) (?:lucro|renda|margem|ganho)s?\b"
)
# Reprova só na frase do app/Pro: "ganhando mais de dois reais por saca em Sorriso" é fato.
PROMESSA_APP = re.compile(r"\bganh(?:ar|ando)\b(?:\s+\w+){0,2}\s+mais\b|\blucr(?:ar|ando|aria)\b|\bmais lucros?\b|\bmaior lucro\b")
# "pro" sozinho é "para o" ("vale pro produtor"): só nomes do plano contam.
PRO = re.compile(r"\b(pulso pro|plano pro|versao pro|assinatura|assinaturas|assinar|assine|assinante|mensalidade|premium)\b")
PRECO_PRO = re.compile(
    r"r\$\s*\d|\b\d+(?:[.,]\d+)?\s*reais\b|\bpor mes\b|\bao mes\b|\bdesconto\b|\bpromocao\b|\bpromocional\b|"
    r"\btempo limitado\b|\b\d+\s*dias\s+(?:gratis|de teste|de acesso|liberados?)\b|\bteste\b"
)


def norm(texto):
    """Minúsculas, sem acento, espaços colapsados: 'De GRAÇA' -> 'de graca'."""
    base = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return " ".join(base.lower().split())


def textos(valor, caminho="episodio"):
    """Todo texto do JSON com o caminho dele, para a mensagem apontar o campo."""
    if isinstance(valor, str):
        yield caminho, valor
    elif isinstance(valor, dict):
        for k, v in valor.items():
            yield from textos(v, f"{caminho}.{k}")
    elif isinstance(valor, (list, tuple)):
        for i, v in enumerate(valor):
            yield from textos(v, f"{caminho}[{i}]")


def falhas_de_texto(episodio):
    falhas = []
    for onde, bruto in textos(episodio):
        # *{exibe|fala}*: as duas formas contam
        texto = norm(re.sub(r"\*\{([^|}]*)\|([^}]*)\}\*", r"\1 \2", bruto))
        if m := GRATIS.search(texto):
            falhas.append(f"{onde}: promessa de gratuidade ({m.group(0)!r})")
        if m := PROMESSA.search(texto):
            falhas.append(f"{onde}: promessa de resultado ({m.group(0)!r})")
        for frase in re.split(r"[.!?;\n]+", texto):
            if APP.search(frase) and (m := GRATIS_APP.search(frase)):
                falhas.append(f"{onde}: promessa de gratuidade do app ({m.group(0)!r})")
            if APP.search(frase) and (m := PROMESSA_APP.search(frase)):
                falhas.append(f"{onde}: promessa de resultado ligada ao app ({m.group(0)!r})")
            if PRO.search(frase) and (m := PRECO_PRO.search(frase)):
                falhas.append(f"{onde}: preço, desconto, teste ou prazo ligado ao Pro ({m.group(0)!r})")
        if re.search(r"ofertas?_compra|n_ofertas|valor_min|valor_max", texto):
            falhas.append(f"{onde}: campo de oferta de compra (conteúdo do Pro) no texto")
    return falhas


def usa_oferta(linha):
    """True se a prova da linha passa por ofertas_compra ou por n_ofertas / valor_min / valor_max."""
    for chave in ("json_campo", "json_moda", "snapshot"):
        prova = linha.get(chave)
        if prova is None:
            continue
        pedacos = [str(p) for p in (prova.get("caminho") or [])] if isinstance(prova, dict) else []
        if isinstance(prova, dict) and prova.get("campo") is not None:
            pedacos.append(str(prova["campo"]))
        if "ofertas_compra" in pedacos or CAMPOS_OFERTA & set(pedacos):
            return True
        if "ofertas_compra" in json.dumps(prova, ensure_ascii=False):
            return True
    return False


def falhas_de_dossie(dossie):
    ruins = {l.get("id") for l in dossie.get("linhas", []) if isinstance(l, dict) and usa_oferta(l)}
    derivados = [d for d in dossie.get("derivados", []) if isinstance(d, dict)]
    mudou = True
    while mudou:  # derivado de linha de oferta também é oferta
        mudou = False
        for d in derivados:
            if d.get("id") not in ruins and (set(d.get("de") or []) & ruins or usa_oferta(d)):
                ruins.add(d.get("id"))
                mudou = True
    return [f"dossie: linha {i!r} usa oferta de compra (ofertas_compra, n_ofertas, valor_min, valor_max) — conteúdo do Pro"
            for i in sorted(ruins, key=str)]


def falhas_de(episodio, dossie):
    return falhas_de_dossie(dossie or {}) + falhas_de_texto(episodio or {})


def checar(pasta):
    pasta = Path(pasta)
    ler = lambda nome: json.loads((pasta / nome).read_text(encoding="utf-8"))
    return falhas_de(ler("episodio.json"), ler("dossie.json") if (pasta / "dossie.json").is_file() else {})


if __name__ == "__main__":
    achados = checar(sys.argv[1])
    for f in achados:
        print(f"FALHA {f}", file=sys.stderr)
    if achados:
        sys.exit(f"G conteúdo Pro reprovado: {len(achados)} falha(s)")
    print("G conteúdo Pro aprovado: sem oferta de compra, gratuidade, preço do Pro nem promessa de resultado")
