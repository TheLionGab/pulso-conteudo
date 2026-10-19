#!/usr/bin/env python3
"""Gera VO diagnóstico via HeyGen Starfish TTS (fallback ElevenLabs quota)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "vo"
HEYGEN = Path("/Users/mac/.agents/skills/media-use/audio/scripts/heygen-tts.mjs")

SEGMENTS = [
    ("vo-01.mp3", "Tira uma foto da folha."),
    ("vo-02.mp3", "A IA analisa na hora."),
    ("vo-03.mp3", "Resposta com fonte — não achismo. Confirme com seu agrônomo."),
    ("vo-04.mp3", "Pulso do Campo. Baixe na App Store."),
]


def probe(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = [{"provider": "heygen-starfish"}]
    for fname, text in SEGMENTS:
        dest_mp3 = OUT / fname
        dest_wav = OUT / fname.replace(".mp3", ".wav")
        print(f"TTS {fname}: {text[:40]}…")
        subprocess.run(
            ["node", str(HEYGEN), text, "-o", str(dest_wav), "--lang", "pt-br"],
            check=True, cwd=str(ROOT),
        )
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(dest_wav), "-codec:a", "libmp3lame", "-q:a", "2", str(dest_mp3)],
            check=True, capture_output=True,
        )
        dur = probe(dest_mp3)
        manifest.append({"file": f"assets/vo/{fname}", "text": text, "duration_s": dur})
        print(f"  OK {dur:.2f}s")
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print("DONE", OUT)


if __name__ == "__main__":
    main()
