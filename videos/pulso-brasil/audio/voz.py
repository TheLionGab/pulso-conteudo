"""Gera (ou restaura do cache) WAVs Gemini PCM mono 24 kHz."""
import base64
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


def cache_valido(arquivo):
    try:
        with wave.open(str(arquivo), "rb") as wav:
            return ((wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 2, 24000)
                    and wav.getnframes() > 0 and len(wav.readframes(wav.getnframes())) == 2 * wav.getnframes())
    except (OSError, EOFError, wave.Error):
        return False


def sintetizar(fala, estilo, chave, destino):
    corpo = {
        "contents": [{"parts": [{"text": f"{estilo}\n\nTexto a narrar:\n{fala}"}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": CANON["voz"]}}},
        },
    }
    pedido = Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{CANON['modelo']}:generateContent",
        json.dumps(corpo).encode(), {"Content-Type": "application/json", "x-goog-api-key": chave},
    )
    try:
        with urlopen(pedido, timeout=120) as resposta:
            candidato = json.load(resposta)["candidates"][0]
        if candidato.get("finishReason") != "STOP":
            raise ValueError("Gemini TTS: áudio incompleto")
        blob = next(p["inlineData"] for p in candidato["content"]["parts"] if "inlineData" in p)
        mime = blob["mimeType"].lower().replace(" ", "")
        if not mime.startswith("audio/l16;") or "rate=24000" not in mime.split(";"):
            raise ValueError("Gemini TTS: formato de áudio diferente de PCM 24 kHz")
        pcm = base64.b64decode(blob["data"], validate=True)
        if not pcm or len(pcm) % 2:
            raise ValueError("Gemini TTS: PCM vazio ou truncado")
    except HTTPError as erro:
        raise ValueError(f"Gemini TTS: HTTP {erro.code}") from None
    except (URLError, TimeoutError, KeyError, IndexError, StopIteration, TypeError):
        raise ValueError("Gemini TTS: resposta indisponível ou sem áudio") from None

    with tempfile.NamedTemporaryFile(dir=destino.parent, delete=False) as tmp:
        temporario = Path(tmp.name)
    try:
        with wave.open(str(temporario), "wb") as wav:
            wav.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
            wav.writeframes(pcm)
        temporario.replace(destino)
    finally:
        temporario.unlink(missing_ok=True)


def gerar(episodio, destino, cache):
    roteiro = validar(episodio)["roteiro"]
    estilo = Path(__file__).with_name("estilo.txt").read_text().strip()
    prefixo = json.dumps(CANON, sort_keys=True) + "\n" + estilo + "\n"
    falas = [" ".join(u["fala"] for u in parse(texto)) for _, texto, _ in roteiro]
    arquivos = [cache / (hashlib.sha256((prefixo + fala).encode()).hexdigest() + ".wav") for fala in falas]
    faltam = {arq: fala for arq, fala in zip(arquivos, falas) if not cache_valido(arq)}
    if faltam:
        chave = os.environ.get("GEMINI_API_KEY")
        if not chave:
            raise ValueError(f"Cache incompleto ({len(faltam)} trecho(s)) e GEMINI_API_KEY ausente")
        cache.mkdir(parents=True, exist_ok=True)
        for arquivo, fala in faltam.items():
            sintetizar(fala, estilo, chave, arquivo)

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
