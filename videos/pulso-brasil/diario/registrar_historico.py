"""Anexa o episódio publicado ao historico.jsonl (idempotente: o mesmo dia e pauta não entra duas vezes).

Uso: python3 -I registrar_historico.py <episodio.json> <historico.jsonl>
     python3 -I registrar_historico.py --tem <AAAA-MM-DD> <historico.jsonl>   (imprime sim ou nao)
Saída: 0 (anexou, já estava ou respondeu); 1 erro. Só publicado entra: o render nunca grava histórico.
"""
import json
import sys
from pathlib import Path

CAMPOS = ("data", "pauta_id", "tema", "titulo", "numeros_chave")


def registrar(episodio, historico):
    ep = json.loads(Path(episodio).read_text(encoding="utf-8"))
    arquivo = Path(historico)
    texto = arquivo.read_text(encoding="utf-8")
    for linha in texto.splitlines():
        if not linha.strip():
            continue
        antigo = json.loads(linha)
        if antigo.get("data") == ep["data"] and antigo.get("pauta_id") == ep["pauta_id"]:
            return False
    registro = {campo: ep[campo] for campo in CAMPOS}
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
        print("histórico: linha anexada" if registrar(*sys.argv[1:3]) else "histórico: dia já registrado")
    except (OSError, ValueError, KeyError, TypeError) as erro:
        sys.exit(f"registrar_historico: {erro}")
