import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

MANIFESTO = Path(__file__).with_name("manifest.json")
ACERVO_PADRAO = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/Pulso-Videos-Arquivo"


def verificar(arquivo, esperado):
    with arquivo.open("rb") as entrada:
        atual = hashlib.file_digest(entrada, "sha256").hexdigest()
    if atual != esperado:
        raise ValueError(f"SHA-256 divergente: {arquivo.name}")
    return arquivo


def caminhos(destino, acervo=None):
    saida = {}
    for nome, item in json.loads(MANIFESTO.read_text()).items():
        arquivo = destino / item["destino"]
        if acervo is not None:
            origem = verificar(acervo / item["origem"], item["sha256"])
            arquivo.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=arquivo.parent, delete=False) as copia:
                temporario = Path(copia.name)
            try:
                shutil.copyfile(origem, temporario)
                verificar(temporario, item["sha256"]).replace(arquivo)
            finally:
                temporario.unlink(missing_ok=True)
        saida[nome] = verificar(arquivo, item["sha256"])
    return saida


if __name__ == "__main__":
    try:
        modo, destino = sys.argv[1:]
        caminhos(Path(destino), Path(os.environ.get("PULSO_ACERVO", ACERVO_PADRAO)).expanduser()
                 if modo == "obter" else None)
    except (ValueError, OSError) as erro:
        sys.exit(f"Assets: {erro}")
    print("Assets canônicos conferidos")
