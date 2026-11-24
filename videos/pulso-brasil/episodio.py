"""Valida o subconjunto de JSON Schema usado no contrato local, sem instalação."""
from datetime import date
import json
import math
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

from audio.roteiro import parse_validado

ROOT = Path(__file__).resolve().parent
SCHEMA = json.loads((ROOT / "episodio.schema.json").read_text())


def validar_campo(valor, regra, caminho):
    def erro(mensagem):
        raise ValueError(f"{caminho}: {mensagem}")

    variantes = regra.get("oneOf", regra.get("anyOf"))
    if variantes is not None:
        selecionada = [r for r in variantes if r.get("properties", {}).get("tipo", {}).get("const") ==
                        (valor.get("tipo") if isinstance(valor, dict) else None)]
        if isinstance(valor, dict) and "tipo" in valor and len(selecionada) == 1:
            validar_campo(valor, selecionada[0], caminho)
            return
        for variante in variantes:
            try:
                validar_campo(valor, variante, caminho)
            except ValueError:
                continue
            return
        erro("valor ou tipo de cena não previsto no schema")
    tipo = regra.get("type")
    tipos = {"object": dict, "array": list, "string": str}
    if tipo in tipos and not isinstance(valor, tipos[tipo]):
        erro(f"esperado {tipo}")
    if tipo == "number" and not (type(valor) is int or type(valor) is float and math.isfinite(valor)):
        erro("esperado número finito")
    if "const" in regra and valor != regra["const"]:
        erro(f"esperado {regra['const']!r}")
    if "enum" in regra and valor not in regra["enum"]:
        erro(f"esperado um de {regra['enum']}")
    if tipo == "object":
        propriedades = regra["properties"]
        for chave in regra.get("required", ()):
            if chave not in valor:
                raise ValueError(f"{caminho}.{chave}: obrigatório")
        for chave, dado in valor.items():
            if chave in propriedades:
                validar_campo(dado, propriedades[chave], f"{caminho}.{chave}")
            elif regra.get("additionalProperties") is False:
                erro(f"campo desconhecido: {chave}")
    if tipo == "array":
        if not regra.get("minItems", 0) <= len(valor) <= regra.get("maxItems", math.inf):
            erro("quantidade de itens inválida")
        for i, item in enumerate(valor):
            validar_campo(item, regra["prefixItems"][i] if "prefixItems" in regra else regra["items"],
                          f"{caminho}[{i}]")
    if tipo == "string":
        if not re.search(regra["pattern"], valor) or len(valor) > regra.get("maxLength", math.inf):
            erro("texto vazio ou formato/tamanho inválido")
        if regra.get("format") == "date":
            try:
                if date.fromisoformat(valor).isoformat() != valor:
                    erro("use data AAAA-MM-DD")
            except ValueError:
                erro("use uma data válida AAAA-MM-DD")
        if regra.get("format") == "uri" and not urlsplit(valor).hostname:
            erro("URL sem domínio")
    if tipo == "number" and not regra.get("minimum", -math.inf) <= valor <= regra.get("maximum", math.inf):
        erro("número fora da faixa")


def validar(episodio):
    validar_campo(episodio, SCHEMA, "episodio")
    cenas = episodio["cenas"]
    if cenas[-1]["tipo"] != "fecho_app" or any(c["tipo"] == "fecho_app" for c in cenas[:-1]):
        raise ValueError("cenas: fecho_app deve aparecer apenas no fim")
    ids = [c["id"] for c in cenas]
    if any(not re.fullmatch(r"[a-z][a-z0-9_-]*", id_cena) for id_cena in ids):
        raise ValueError("cenas: IDs devem ser identificadores ASCII em minúsculas")
    if len(set(ids)) != len(ids):
        raise ValueError("cenas: IDs duplicados")
    ordem = []
    for cena, texto, _ in episodio["roteiro"]:
        parse_validado(texto)
        if not ordem or ordem[-1] != cena:
            ordem.append(cena)
    if ordem != ids:
        raise ValueError("roteiro: as cenas devem aparecer uma vez em blocos, na ordem declarada")
    clipes = json.loads((ROOT / "assets/manifest.json").read_text())
    for cena in cenas:
        if "clipe" in cena and not clipes.get(cena["clipe"], {}).get("destino", "").startswith("cenas/"):
            raise ValueError(f"cenas: clipe não canônico: {cena['clipe']}")
    return episodio


if __name__ == "__main__":
    try:
        validar(json.loads(Path(sys.argv[1]).read_text()))
    except (ValueError, OSError) as erro:
        sys.exit(f"Schema: {erro}")
    print("Schema aprovado")
