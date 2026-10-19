#!/usr/bin/env python3
"""Busca vozes compartilhadas ElevenLabs (PT-BR) — read-only."""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

SECRETS = Path.home() / ".config" / "lion-secrets.env"


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


def main() -> None:
    key = chave()
    q = sys.argv[1] if len(sys.argv) > 1 else "portuguese"
    params = urllib.parse.urlencode({
        "language": "pt",
        "page_size": 30,
        "search": q,
    })
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/shared-voices?{params}",
        headers={"xi-api-key": key},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read())
    voices = data.get("voices") or data.get("shared_voices") or []
    print(f"# shared-voices search={q!r} count={len(voices)}")
    for v in voices[:25]:
        labels = v.get("labels") or {}
        print(
            f"{v.get('voice_id')}\t{v.get('name')}\t"
            f"gender={labels.get('gender','?')} accent={labels.get('accent','?')} "
            f"age={labels.get('age','?')} use={v.get('usage_character_count_1y',0)}"
        )


if __name__ == "__main__":
    main()
