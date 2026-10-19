#!/usr/bin/env python3
"""VO device-launch — HeyGen Starfish, alinhado às 5 cenas (21s)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "vo"
HEYGEN = Path("/Users/mac/.agents/skills/media-use/audio/scripts/heygen-tts.mjs")
DIAG_VO = ROOT.parent / "pulso-diagnostico-praga" / "assets" / "vo"

GENERATE = [
    ("vo-01.mp3", "Pulso do Campo."),
    ("vo-02.mp3", "Cotações da sua praça. Não é média nacional."),
    ("vo-05.mp3", "O campo falando. De verdade."),
]

COPY_FROM_DIAG = {
    "vo-03.mp3": "vo-01.mp3",
    "vo-04.mp3": "vo-02.mp3",
    "vo-06.mp3": "vo-04.mp3",
}


def probe(path: Path) -> float:
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(out.stdout.strip())


def synthesize(fname: str, text: str) -> None:
    dest_mp3 = OUT / fname
    dest_wav = OUT / fname.replace(".mp3", ".wav")
    print(f"TTS {fname}: {text}")
    subprocess.run(
        ["node", str(HEYGEN), text, "-o", str(dest_wav), "--lang", "pt-br"],
        check=True,
        cwd=str(ROOT),
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(dest_wav),
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "2",
            str(dest_mp3),
        ],
        check=True,
        capture_output=True,
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = [{"provider": "heygen-starfish"}]

    for fname, text in GENERATE:
        synthesize(fname, text)
        dur = probe(OUT / fname)
        manifest.append({"file": f"assets/vo/{fname}", "text": text, "duration_s": dur})
        print(f"  OK {dur:.2f}s")

    for dest, src in COPY_FROM_DIAG.items():
        shutil.copy2(DIAG_VO / src, OUT / dest)
        dur = probe(OUT / dest)
        manifest.append(
            {
                "file": f"assets/vo/{dest}",
                "text": f"(copy {src})",
                "duration_s": dur,
            }
        )
        print(f"COPY {dest} <- {src} ({dur:.2f}s)")

    (OUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    )
    print("DONE", OUT)


if __name__ == "__main__":
    main()
