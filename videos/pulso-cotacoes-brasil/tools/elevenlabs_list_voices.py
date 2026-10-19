#!/usr/bin/env python3
"""Lista vozes ElevenLabs (pt-BR / portuguese) — read-only, sem imprimir key."""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

SECRETS = Path.home() / ".config" / "lion-secrets.env"


def chave() -> str:
    env = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if env:
        return env
    if not SECRETS.exists():
        sys.exit("BLOCKED: sem key")
    for line in SECRETS.read_text().splitlines():
        if line.strip().startswith("ELEVENLABS_API_KEY="):
            v = line.split("=", 1)[1].strip().strip("\"'")
            if v:
                return v
    sys.exit("BLOCKED: key vazia")


def main() -> None:
    key = chave()
    req = urllib.request.Request(
        "https://api.elevenlabs.io/v1/voices",
        headers={"xi-api-key": key},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:300]}")

    voices = data.get("voices", [])
    hits = []
    for v in voices:
        name = (v.get("name") or "").lower()
        labels = v.get("labels") or {}
        lang = str(labels.get("language", "")).lower()
        accent = str(labels.get("accent", "")).lower()
        desc = str(labels.get("description", "")).lower()
        blob = " ".join([name, lang, accent, desc, str(v.get("description", "")).lower()])
        if any(
            x in blob
            for x in (
                "portuguese",
                "portugu",
                "brazil",
                "brasile",
                "pt-br",
                "pt_br",
                "brazilian",
            )
        ):
            hits.append(v)

    print(f"total_voices={len(voices)} pt_hits={len(hits)}\n")
    for v in sorted(hits, key=lambda x: x.get("name", "")):
        labels = v.get("labels") or {}
        print(
            f"{v.get('voice_id')}\t{v.get('name')}\t"
            f"lang={labels.get('language','?')} accent={labels.get('accent','?')} "
            f"age={labels.get('age','?')} gender={labels.get('gender','?')}"
        )

    # curated picks often used for PT promo (public library names)
    curated = [
        "guilherme",
        "will",
        "brian",
        "adam",
        "daniel",
        "clyde",
        "james",
        "michael",
        "charlie",
        "eric",
        "jessica",
        "laura",
    ]
    print("\n# curated name scan")
    for v in voices:
        n = (v.get("name") or "").lower()
        if any(c in n for c in curated):
            labels = v.get("labels") or {}
            print(
                f"{v.get('voice_id')}\t{v.get('name')}\t"
                f"lang={labels.get('language','?')} gender={labels.get('gender','?')}"
            )

    try:
        req2 = urllib.request.Request(
            "https://api.elevenlabs.io/v1/user/subscription",
            headers={"xi-api-key": key},
        )
        with urllib.request.urlopen(req2, timeout=30) as r:
            sub = json.loads(r.read())
        print(
            f"\n# subscription tier={sub.get('tier')} "
            f"chars={sub.get('character_count')}/{sub.get('character_limit')} "
            f"remaining={sub.get('character_limit',0)-sub.get('character_count',0)}"
        )
    except urllib.error.HTTPError as e:
        print(f"\n# subscription ERR {e.code}")


if __name__ == "__main__":
    main()
