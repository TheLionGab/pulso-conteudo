"""Amarra o episódio ao dia pedido: o que o modelo escreveu tem de ser DO dia, senão nada sobe nem publica.

Uso: python3 -I conferir_episodio.py <AAAA-MM-DD> <pasta> [--ep]
<pasta> tem episodio.json e dossie.json; com --ep exige também out/ep.json (o meta que o publicar.mjs usa).
Reprova (código 1) se: episodio.data ou dossie.data forem diferentes do dia; dossie.episodio não casar
^pulso-brasil-AAAA-MM-DD(-slug)?$ com a data do dia (até 80 caracteres, mesmo contrato do app); ou, no ep.json,
id for diferente de dossie.episodio ou publicado_em diferente do dia.
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path

ID_RE = re.compile(r"^pulso-brasil-(\d{4}-\d{2}-\d{2})(?:-[a-z0-9]+)*$")


def checar_id(id_, dia, rotulo):
    if not isinstance(id_, str) or len(id_) > 80 or not (m := ID_RE.match(id_)):
        return [f"{rotulo} {id_!r} não casa pulso-brasil-AAAA-MM-DD(-slug) (até 80 caracteres)"]
    return [] if m.group(1) == dia else [f"{rotulo} {id_!r} é de {m.group(1)}, não do dia {dia}"]


def conferir(dia, pasta, exigir_ep=False):
    dt.date.fromisoformat(dia)
    pasta = Path(pasta)
    ler = lambda caminho: json.loads((pasta / caminho).read_text(encoding="utf-8"))
    episodio, dossie = ler("episodio.json"), ler("dossie.json")
    falhas = []
    for rotulo, valor in (("episodio.json data", episodio.get("data")), ("dossie.json data", dossie.get("data"))):
        if valor != dia:
            falhas.append(f"{rotulo} {valor!r} diferente do dia {dia}")
    falhas += checar_id(dossie.get("episodio"), dia, "dossie.json episodio")
    if exigir_ep or (pasta / "out/ep.json").is_file():
        ep = ler("out/ep.json")
        if ep.get("publicado_em") != dia:
            falhas.append(f"ep.json publicado_em {ep.get('publicado_em')!r} diferente do dia {dia}")
        if ep.get("id") != dossie.get("episodio"):
            falhas.append(f"ep.json id {ep.get('id')!r} diferente de dossie.json episodio {dossie.get('episodio')!r}")
        falhas += checar_id(ep.get("id"), dia, "ep.json id")
    if falhas:
        raise ValueError("; ".join(falhas))
    return dossie["episodio"]


if __name__ == "__main__":
    try:
        print("episódio do dia confere:", conferir(sys.argv[1], sys.argv[2], "--ep" in sys.argv[3:]))
    except (ValueError, KeyError, IndexError, TypeError, OSError) as erro:
        sys.exit(f"conferir_episodio: {erro}")
