#!/usr/bin/env python3
"""VO promo 22s — ElevenLabs vozes premium PT-BR."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRETS = Path.home() / ".config" / "lion-secrets.env"
MODEL = "eleven_multilingual_v2"
VOICE_DEFAULT = "HOfBIVLhom4mc9WvXfyH"  # Andrea Lot — authoritative BR (top usage)
VOICES_CANDIDATES = {
    # shared library — promo agro / autoridade
    "andrea-lot": ("HOfBIVLhom4mc9WvXfyH", "Andrea Lot — authoritative Brazilian Portuguese"),
    "rafha": ("Lag2bmI1gPov7LCIcc2E", "Rafha — Intense & Motivational"),
    "adilson": ("A26KfvFuSKaMzhhYkSlQ", "Adilson — Portuguese Neutral Male"),
    "fabi": ("e06XicPETIbfUaeHM9zH", "Fabi — Portuguese (BR)"),
    "pri": ("8EY2gK6oUxZCDZAlvUpZ", "Pri — Warm & Natural Brazilian Portuguese"),
    # owned library
    "carlos": ("NFmEzNOony1UsEJGXLth", "Carlos — Resonant & Majestic Storyteller"),
    "sergio": ("rnJZLKxtlBZt77uIED10", "Sergio — Deep, Resonant and Clear"),
    "pedro": ("UZ6DwZuYojB2xoXipTLo", "Pedro Martins"),
    "jose-arnelas": ("M6Jwe10uUuqfIwN7yf4V", "José Arnelas"),
    "arnold": ("ZYCQDYoXnl78dNdU6JeG", "Arnold — Br"),
    "guilherme-mello": ("A0vayB3pXPiiEvllfYw5", "Guilherme Mello — PT-BR (canon legado)"),
}
SETTINGS = {
    "stability": 0.52,
    "similarity_boost": 0.78,
    "style": 0.12,
    "use_speaker_boost": True,
    "speed": 1.06,
}

SEGMENTS = [
    ("vo-01-abertura.mp3", "No Pulso do Campo, cotação de comprador real — na sua praça."),
    ("vo-02-busca.mp3", "Busque a cidade. Campo Verde, Sorriso, Rondonópolis."),
    ("vo-03-preco.mp3", "Soja a cento e trinta e três reais e cinquenta. Preço de mesa, à vista."),
    ("vo-04-carrossel.mp3", "Deslize entre praças. Milho, soja — comprador verificado."),
    ("vo-05-contraste.mp3", "Índice é faixa. Comprador é o preço que fecha."),
    ("vo-06-cta.mp3", "Baixe o Pulso do Campo."),
]


def chave() -> str:
    env = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if env:
        return env
    if not SECRETS.exists():
        sys.exit(f"BLOCKED: ausente ELEVENLABS_API_KEY ou {SECRETS}")
    for line in SECRETS.read_text().splitlines():
        if line.strip().startswith("ELEVENLABS_API_KEY="):
            v = line.split("=", 1)[1].strip().strip("\"'")
            if v:
                return v
    sys.exit("BLOCKED: ELEVENLABS_API_KEY vazia")


def quota_restante(key: str) -> tuple[int, int]:
    req = urllib.request.Request(
        "https://api.elevenlabs.io/v1/user/subscription",
        headers={"xi-api-key": key},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        sub = json.loads(r.read())
    used = int(sub.get("character_count") or 0)
    limit = int(sub.get("character_limit") or 0)
    return limit - used, limit


def sintetizar(texto: str, key: str, dest: Path, voice_id: str) -> None:
    body = json.dumps({
        "text": texto,
        "model_id": MODEL,
        "voice_settings": SETTINGS,
    }).encode()
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        data=body,
        method="POST",
        headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(r.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:400]
        sys.exit(f"BLOCKED TTS HTTP {e.code}: {detail}")


def probe(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(out.stdout.strip())


def main() -> None:
    slug = sys.argv[1] if len(sys.argv) > 1 else "andrea-lot"
    if slug not in VOICES_CANDIDATES:
        print("vozes:", ", ".join(VOICES_CANDIDATES))
        sys.exit(f"uso: python3 gerar_vo_v23.py [{ '|'.join(VOICES_CANDIDATES) }]")
    voice_id, voice_name = VOICES_CANDIDATES[slug]
    out_dir = ROOT / "assets" / "vo" / f"v24-{slug}"
    key = chave()
    chars_needed = sum(len(t) for _, t in SEGMENTS)
    remaining, limit = quota_restante(key)
    print(f"# quota chars remaining={remaining}/{limit} need≈{chars_needed}")
    if remaining < chars_needed:
        sys.exit(
            f"BLOCKED: quota ElevenLabs insuficiente ({remaining} < {chars_needed}). "
            "Recarregue em elevenlabs.io → Subscription."
        )
    manifest: list[dict[str, object]] = [{"voice_id": voice_id, "voice_name": voice_name}]
    for fname, text in SEGMENTS:
        dest = out_dir / fname
        print(f"TTS [{voice_name}] {fname}…")
        sintetizar(text, key, dest, voice_id)
        dur = probe(dest)
        manifest.append({"file": f"assets/vo/v24-{slug}/{fname}", "text": text, "duration_s": dur})
        print(f"  OK {dur:.2f}s")
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print("DONE", out_dir)


if __name__ == "__main__":
    main()
