#!/usr/bin/env python3
"""Baixa previews de vozes ElevenLabs (shared-voices) — zero quota TTS."""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRETS = Path.home() / ".config" / "lion-secrets.env"
PICKS = {
    "andrea-lot": "HOfBIVLhom4mc9WvXfyH",
    "rafha": "Lag2bmI1gPov7LCIcc2E",
    "adilson": "A26KfvFuSKaMzhhYkSlQ",
    "carlos": "NFmEzNOony1UsEJGXLth",
    "sergio": "rnJZLKxtlBZt77uIED10",
}


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


def meta(key: str, voice_id: str) -> dict:
    params = urllib.parse.urlencode({"search": voice_id, "page_size": 5})
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/shared-voices?{params}",
        headers={"xi-api-key": key},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read())
    for v in data.get("voices") or []:
        if v.get("voice_id") == voice_id:
            return v
    req2 = urllib.request.Request(
        "https://api.elevenlabs.io/v1/voices",
        headers={"xi-api-key": key},
    )
    with urllib.request.urlopen(req2, timeout=60) as r:
        owned = json.loads(r.read()).get("voices") or []
    for v in owned:
        if v.get("voice_id") == voice_id:
            return v
    sys.exit(f"BLOCKED: meta ausente para {voice_id}")


def main() -> None:
    key = chave()
    out = ROOT / "assets" / "vo" / "previews"
    out.mkdir(parents=True, exist_ok=True)
    for slug, vid in PICKS.items():
        m = meta(key, vid)
        url = m.get("preview_url")
        if not url:
            print(f"SKIP {slug}: sem preview_url")
            continue
        dest = out / f"{slug}.mp3"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=60) as r:
            dest.write_bytes(r.read())
        print(f"OK {dest} — {m.get('name')}")


if __name__ == "__main__":
    main()
