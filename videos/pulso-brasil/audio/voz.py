"""Gera (ou restaura do cache) WAVs PCM mono 24 kHz com a voz oficial ElevenLabs (config/voz.json).

A chave vem só de ELEVENLABS_API_KEY no ambiente; nunca é impressa nem gravada. Sem fallback de voz.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import wave

from episodio import validar
from audio.roteiro import parse
from gates.g_voz import CANON, checar

TETO = int(os.environ.get("PULSO_ELEVEN_TETO", "2500"))  # caracteres novos por execução; episódio ~700


def cache_valido(arquivo):
    try:
        with wave.open(str(arquivo), "rb") as wav:
            return ((wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 2, 24000)
                    and wav.getnframes() > 0 and len(wav.readframes(wav.getnframes())) == 2 * wav.getnframes())
    except (OSError, EOFError, wave.Error):
        return False


def sintetizar(fala, chave, destino, anteriores):
    """Voz oficial ElevenLabs, mesmos parâmetros do app (scripts/pulso-news/remotion/audio/voz_elevenlabs.py)."""
    corpo = {"text": fala, "model_id": CANON["modelo"], "language_code": "pt",
             "voice_settings": CANON["ajustes"], "seed": CANON["seed"]}
    if anteriores:
        corpo["previous_request_ids"] = anteriores[-3:]
    pedido = Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{CANON['voz']}?output_format=pcm_24000",
        json.dumps(corpo).encode(), {"Content-Type": "application/json", "xi-api-key": chave},
    )
    try:
        with urlopen(pedido, timeout=180) as resposta:
            pcm = resposta.read()
            id_pedido = resposta.headers.get("request-id")
        if not pcm or len(pcm) % 2:
            raise ValueError("ElevenLabs: PCM vazio ou truncado")
    except HTTPError as erro:
        detalhe = erro.read().decode(errors="replace")[:200]
        raise ValueError(f"ElevenLabs: HTTP {erro.code} {detalhe}") from None
    except (URLError, TimeoutError):
        raise ValueError("ElevenLabs: resposta indisponível") from None

    with tempfile.NamedTemporaryFile(dir=destino.parent, delete=False) as tmp:
        temporario = Path(tmp.name)
    try:
        with wave.open(str(temporario), "wb") as wav:
            wav.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
            wav.writeframes(pcm)
        temporario.replace(destino)
    finally:
        temporario.unlink(missing_ok=True)
    return id_pedido


def gerar(episodio, destino, cache):
    roteiro = validar(episodio)["roteiro"]
    prefixo = json.dumps(CANON, sort_keys=True) + "\n"
    falas = [" ".join(u["fala"] for u in parse(texto)) for _, texto, _ in roteiro]
    arquivos = [cache / (hashlib.sha256((prefixo + fala).encode()).hexdigest() + ".wav") for fala in falas]
    faltam = {arq: fala for arq, fala in zip(arquivos, falas) if not cache_valido(arq)}
    if faltam:
        novos = sum(len(f) for f in faltam.values())
        if novos > TETO:
            raise ValueError(f"{novos} caracteres novos passam do teto de {TETO} (PULSO_ELEVEN_TETO)")
        chave = os.environ.get("ELEVENLABS_API_KEY", "").strip()
        if not chave:
            raise ValueError(f"Cache incompleto ({len(faltam)} trecho(s)) e ELEVENLABS_API_KEY ausente")
        cache.mkdir(parents=True, exist_ok=True)
        anteriores = []
        for arquivo, fala in faltam.items():
            id_pedido = sintetizar(fala, chave, arquivo, anteriores)
            if id_pedido:
                anteriores.append(id_pedido)

    segs = destino / "segs"
    segs.mkdir(parents=True, exist_ok=True)
    hashes = []
    for i, arq in enumerate(arquivos):
        trecho = segs / f"seg_{i:03d}.wav"
        shutil.copyfile(arq, trecho)
        hashes.append(hashlib.sha256(trecho.read_bytes()).hexdigest())
    sintese = dict(CANON, segmentos=len(roteiro), segmentos_sha256=hashes,
                   roteiro_sha256=hashlib.sha256(json.dumps(roteiro, ensure_ascii=False).encode()).hexdigest())
    checar(sintese)
    (destino / "sintese.json").write_text(json.dumps(sintese, indent=2) + "\n")


if __name__ == "__main__":
    try:
        entrada, destino, cache = map(Path, sys.argv[1:])
        gerar(json.loads(entrada.read_text()), destino, cache)
    except (ValueError, OSError) as erro:
        sys.exit(f"Voz: {erro}")
