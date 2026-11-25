from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import re
import sys
import unicodedata


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto.casefold())
    return " ".join(re.findall(r"\w+", "".join(c for c in texto if not unicodedata.combining(c))))


def chaves(episodio):
    return {
        (Decimal(str(item["numero"]).replace(",", ".")), normalizar(item["fonte"]), item["data"])
        for item in episodio.get("numeros_chave", [])
    }


ULTIMOS = 5  # o assunto de um dos últimos 5 episódios não volta, mesmo com título e id novos


def familia(pauta_id):
    """Assunto do pauta_id sem o sufixo de data (soja-pracas-mt-2511 -> soja-pracas-mt)."""
    return re.sub(r"-(?:\d{4}|\d{2}-\d{2})$", "", normalizar(str(pauta_id or "")).replace(" ", "-"))


def checar(episodio, publicados):
    data = date.fromisoformat(episodio["data"])
    publicados = list(publicados)
    recentes = sorted((p for p in publicados if date.fromisoformat(p["data"]) <= data), key=lambda p: p["data"], reverse=True)[:ULTIMOS]
    mia = familia(episodio.get("pauta_id"))
    for publicado in recentes:
        if mia and mia == familia(publicado.get("pauta_id")):
            raise ValueError(f"g_repeticao: assunto {mia!r} já saiu em {publicado['data']} (um dos últimos {ULTIMOS} episódios)")
    for publicado in publicados:
        dias = (data - date.fromisoformat(publicado["data"])).days
        if not 0 <= dias <= 7:
            continue
        for campo in ("pauta_id", "tema", "titulo"):
            if publicado.get(campo) and normalizar(episodio[campo]) == normalizar(publicado[campo]):
                raise ValueError(f"g_repeticao: {campo} já publicado em {publicado['data']}")
        if chaves(episodio) & chaves(publicado):
            raise ValueError(f"g_repeticao: mesmo número, fonte e data de {publicado['data']}")


if __name__ == "__main__":
    try:
        episodio = json.loads(Path(sys.argv[1]).read_text())
        with Path(sys.argv[2]).open() as historico:
            checar(episodio, (json.loads(linha) for linha in historico if linha.strip()))
    except (ValueError, KeyError, OSError, ArithmeticError) as erro:
        sys.exit(f"Histórico: {erro}")
    print("g_repeticao aprovado")
