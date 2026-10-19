#!/usr/bin/env python3
"""Gera BGM + SFX do promo V2.1 via ElevenLabs (vozes + sons auditados).

Canon voz Pulso agro: Guilherme-Mello A0vayB3pXPiiEvllfYw5
(cooperfibra-boletim-audio-canon-20260904.md)

Uso:
  python3 tools/gerar_audio_elevenlabs_v21.py bgm
  python3 tools/gerar_audio_elevenlabs_v21.py sfx
  python3 tools/gerar_audio_elevenlabs_v21.py all
"""

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
BGM_OUT = ROOT / "assets" / "bgm" / "bed-pulso-elevenlabs-v21.mp3"
SFX_DIR = ROOT / "assets" / "sfx" / "elevenlabs"
MANIFEST = SFX_DIR / "manifest.json"

BGM_PROMPT = (
    "Instrumental background bed for a premium fintech agriculture app promo, "
    "22 seconds, subtle pulsing bass, warm analog synth pads, confident minimal, "
    "no vocals, no dramatic drop, sits under UI sound design, modern Brazilian agtech, "
    "clean mix, loop-friendly ending"
)

SFX_CUES: list[dict[str, object]] = [
    {
        "name": "whoosh-short",
        "text": "short smooth UI whoosh transition, airy, modern app",
        "duration_seconds": 0.6,
        "out": "whoosh-short.mp3",
    },
    {
        "name": "click-soft",
        "text": "soft premium mobile UI tap click, subtle, not harsh",
        "duration_seconds": 0.5,
        "out": "click-soft.mp3",
    },
    {
        "name": "impact-bass-2",
        "text": "deep soft bass impact for price reveal, controlled, not cinematic",
        "duration_seconds": 1.2,
        "out": "impact-bass-2.mp3",
    },
    {
        "name": "riser",
        "text": "short subtle riser for app store CTA lockup, 1.5 seconds",
        "duration_seconds": 1.5,
        "out": "riser.mp3",
    },
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


def post_audio(url: str, key: str, body: dict, dest: Path) -> None:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        method="POST",
        headers={
            "xi-api-key": key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(r.read())
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"BLOCKED: ElevenLabs HTTP {e.code} — {err[:500]}") from e


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(out.stdout.strip())


def gerar_bgm_ambient(key: str) -> None:
    """Fallback quando Music API sem crédito: bed longo via sound-generation."""
    print(f"BGM (sound-generation) → {BGM_OUT}")
    post_audio(
        "https://api.elevenlabs.io/v1/sound-generation?output_format=mp3_44100_128",
        key,
        {
            "text": BGM_PROMPT,
            "duration_seconds": 22.0,
            "prompt_influence": 0.45,
        },
        BGM_OUT,
    )
    dur = probe_duration(BGM_OUT)
    print(f"OK BGM ambient {dur:.2f}s")


def gerar_bgm(key: str) -> None:
    print(f"BGM (music v2) → {BGM_OUT}")
    try:
        post_audio(
            "https://api.elevenlabs.io/v1/music?output_format=mp3_44100_128",
            key,
            {
                "prompt": BGM_PROMPT,
                "music_length_ms": 22000,
                "model_id": "music_v2",
                "force_instrumental": True,
            },
            BGM_OUT,
        )
        dur = probe_duration(BGM_OUT)
        print(f"OK BGM music {dur:.2f}s")
    except SystemExit as e:
        msg = str(e)
        if "insufficient_credits" in msg or "payment_required" in msg:
            print("Music API sem crédito — fallback sound-generation")
            gerar_bgm_ambient(key)
        else:
            raise


def gerar_sfx(key: str) -> None:
    SFX_DIR.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {"provider": "elevenlabs", "cues": []}
    for cue in SFX_CUES:
        dest = SFX_DIR / str(cue["out"])
        print(f"SFX {cue['name']} → {dest.name}")
        post_audio(
            "https://api.elevenlabs.io/v1/sound-generation",
            key,
            {
                "text": cue["text"],
                "duration_seconds": cue["duration_seconds"],
            },
            dest,
        )
        dur = probe_duration(dest)
        manifest["cues"].append(
            {
                "name": cue["name"],
                "file": f"assets/sfx/elevenlabs/{cue['out']}",
                "duration_s": dur,
                "prompt": cue["text"],
            }
        )
        print(f"  OK {dur:.2f}s")
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(f"manifest → {MANIFEST}")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    key = chave()
    if mode in ("bgm", "all"):
        gerar_bgm(key)
    if mode in ("sfx", "all"):
        gerar_sfx(key)
    if mode not in ("bgm", "sfx", "all"):
        sys.exit("uso: bgm | sfx | all")


if __name__ == "__main__":
    main()
