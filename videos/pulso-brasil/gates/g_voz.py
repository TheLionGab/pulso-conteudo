import json
from pathlib import Path
import sys

CANON = json.loads((Path(__file__).resolve().parents[1] / "config/voz.json").read_text())


def checar(sintese):
    for campo, esperado in CANON.items():
        if sintese.get(campo) != esperado:
            raise ValueError(f"g_voz: {campo} esperado {esperado!r}; recebido {sintese.get(campo)!r}")
    return CANON


if __name__ == "__main__":
    try:
        checar(json.loads(Path(sys.argv[1]).read_text()))
    except (ValueError, OSError) as erro:
        sys.exit(str(erro))
    print("g_voz aprovado")
