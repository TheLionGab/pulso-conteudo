"""Gera, uma vez, as trilhas e os efeitos do assets/sons.json na ElevenLabs (Music e Sound Effects).

Uso: python -m assets.sons_elevenlabs <pasta do acervo>
A chave vem só de ELEVENLABS_API_KEY; nunca é impressa nem gravada. Arquivo que já existe no
acervo não é pedido de novo (sem gasto repetido). Saída: WAV 48 kHz estéreo em <acervo>/elevenlabs/
e, no fim, as linhas prontas para o assets/manifest.json com o sha256 de cada arquivo.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API = "https://api.elevenlabs.io/v1"
PLANO = json.loads((Path(__file__).with_name("sons.json")).read_text())


def pedir(rota, corpo, chave):
    pedido = Request(f"{API}/{rota}", json.dumps(corpo).encode(),
                     {"Content-Type": "application/json", "xi-api-key": chave})
    try:
        with urlopen(pedido, timeout=600) as resposta:
            dados = resposta.read()
    except HTTPError as erro:
        raise ValueError(f"ElevenLabs {rota.split('?')[0]}: HTTP {erro.code} {erro.read().decode(errors='replace')[:300]}") from None
    except (URLError, TimeoutError):
        raise ValueError(f"ElevenLabs {rota.split('?')[0]}: sem resposta") from None
    if len(dados) < 1000:
        raise ValueError(f"ElevenLabs {rota.split('?')[0]}: áudio vazio")
    return dados


def para_wav(mp3, destino):
    with tempfile.TemporaryDirectory() as tmp:
        bruto = Path(tmp) / "bruto.mp3"
        bruto.write_bytes(mp3)
        parcial = destino.with_suffix(".parcial.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(bruto), "-ar", "48000", "-ac", "2",
                        "-c:a", "pcm_s16le", str(parcial)], check=True)
        parcial.replace(destino)


def main(acervo):
    chave = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    pasta = acervo / "elevenlabs"
    pasta.mkdir(parents=True, exist_ok=True)
    pedidos = [(nome, "music?output_format=mp3_44100_192",
                {"prompt": texto, "music_length_ms": PLANO["duracao_musica_ms"], "model_id": "music_v1",
                 "force_instrumental": True})
               for nome, texto in PLANO["musica"].items()]
    pedidos += [(nome, "sound-generation?output_format=mp3_44100_192",
                 {"text": e["texto"], "duration_seconds": e["segundos"], "prompt_influence": 0.6})
                for nome, e in PLANO["efeitos"].items()]
    for nome, rota, corpo in pedidos:
        destino = pasta / f"{nome}.wav"
        if destino.exists():
            print(f"já existe: {destino.name}")
            continue
        if not chave:
            raise ValueError("ELEVENLABS_API_KEY ausente")
        print(f"pedindo {nome}...", flush=True)
        para_wav(pedir(rota, corpo, chave), destino)
    print("\nLinhas para o assets/manifest.json:")
    for nome, _, _ in pedidos:
        arquivo = pasta / f"{nome}.wav"
        sha = hashlib.sha256(arquivo.read_bytes()).hexdigest()
        print(f'  "{nome}": {{"origem": "elevenlabs/{nome}.wav", "destino": "sons/{nome}.wav", "sha256": "{sha}"}},')


if __name__ == "__main__":
    try:
        main(Path(sys.argv[1]).expanduser())
    except (ValueError, OSError, subprocess.CalledProcessError) as erro:
        sys.exit(f"Sons: {erro}")
