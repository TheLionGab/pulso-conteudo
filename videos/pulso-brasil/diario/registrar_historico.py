"""Anexa o episódio publicado ao historico.jsonl (idempotente: o mesmo dia e pauta não entram duas vezes).

Uso: python3 -I registrar_historico.py <episodio.json> <historico.jsonl> --dia <AAAA-MM-DD>
     python3 -I registrar_historico.py --tem <AAAA-MM-DD> <historico.jsonl>   (imprime sim ou nao)
--dia é o dia que o workflow pediu: o episódio tem de ser desse dia, e é esse dia que fica gravado (o --tem do
contexto consulta o mesmo valor). Saída: 0 (anexou, já estava ou respondeu); 1 erro.
Só publicado entra: o render nunca grava histórico.
"""
import datetime as dt
import json
import sys
from pathlib import Path

CAMPOS = ("pauta_id", "tema", "titulo", "numeros_chave")


def registrar(episodio, historico, dia):
    dt.date.fromisoformat(dia)
    ep = json.loads(Path(episodio).read_text(encoding="utf-8"))
    if ep["data"] != dia:
        raise ValueError(f"episódio é de {ep['data']}, não do dia {dia}: não entra no histórico")
    arquivo = Path(historico)
    texto = arquivo.read_text(encoding="utf-8")
    for linha in texto.splitlines():
        if not linha.strip():
            continue
        antigo = json.loads(linha)
        if antigo.get("data") == dia and antigo.get("pauta_id") == ep["pauta_id"]:
            return False
    registro = {"data": dia, **{campo: ep[campo] for campo in CAMPOS}}
    if texto and not texto.endswith("\n"):
        texto += "\n"
    arquivo.write_text(texto + json.dumps(registro, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return True


def tem_o_dia(dia, historico):
    """Há registro desse dia? Se sim, o episódio já foi publicado: o agendado não refaz nada."""
    return any(json.loads(linha).get("data") == dia
               for linha in Path(historico).read_text(encoding="utf-8").splitlines() if linha.strip())


if __name__ == "__main__":
    try:
        if sys.argv[1:2] == ["--tem"]:  # --tem AAAA-MM-DD historico.jsonl -> imprime sim ou nao
            print("sim" if tem_o_dia(*sys.argv[2:4]) else "nao")
            sys.exit(0)
        if len(sys.argv) != 5 or sys.argv[3] != "--dia":
            raise ValueError("uso: registrar_historico.py <episodio.json> <historico.jsonl> --dia <AAAA-MM-DD>")
        print("histórico: linha anexada" if registrar(sys.argv[1], sys.argv[2], sys.argv[4]) else "histórico: dia já registrado")
    except (OSError, ValueError, KeyError, TypeError) as erro:
        sys.exit(f"registrar_historico: {erro}")
