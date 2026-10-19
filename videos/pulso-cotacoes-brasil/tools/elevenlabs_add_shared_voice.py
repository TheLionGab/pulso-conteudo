#!/usr/bin/env python3
"""Adiciona voz compartilhada ElevenLabs à biblioteca da conta."""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

SECRETS = Path.home() / ".config" / "lion-secrets.env"

# Promo agro — curadoria (shared + owned)
CURATED = {
    "andrea-lot": ("HOfBIVLhom4mc9WvXfyH", None, "Andrea Lot — authoritative BR (67M uses)"),
    "rafha": ("Lag2bmI1gPov7LCIcc2E", None, "Rafha — Intense & Motivational"),
    "adilson": ("A26KfvFuSKaMzhhYkSlQ", None, "Adilson — Neutral Male (7.9M uses)"),
    "carlos": ("NFmEzNOony1UsEJGXLth", None, "Carlos — Resonant & Majestic (owned)"),
    "sergio": ("rnJZLKxtlBZt77uIED10", None, "Sergio — Deep, Resonant (owned)"),
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


def fetch_shared(key: str, voice_id: str) -> dict | None:
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
    return None


def add_voice(key: str, public_owner_id: str, voice_id: str, name: str) -> None:
    body = json.dumps({"new_name": name}).encode()
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/voices/add/{public_owner_id}/{voice_id}",
        data=body,
        method="POST",
        headers={"xi-api-key": key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        print(json.loads(r.read()))


def main() -> None:
    slug = sys.argv[1] if len(sys.argv) > 1 else "andrea-lot"
    if slug not in CURATED:
        print("slugs:", ", ".join(CURATED))
        sys.exit(f"uso: python3 elevenlabs_add_shared_voice.py [{ '|'.join(CURATED) }]")
    voice_id, _, label = CURATED[slug]
    key = chave()
    if slug in ("carlos", "sergio"):
        print(f"SKIP add — {label} já na biblioteca ({voice_id})")
        return
    meta = fetch_shared(key, voice_id)
    if not meta:
        sys.exit(f"BLOCKED: voice_id {voice_id} não encontrada em shared-voices")
    owner = meta.get("public_owner_id")
    if not owner:
        sys.exit("BLOCKED: public_owner_id ausente")
    print(f"ADD {label} owner={owner[:12]}… voice={voice_id}")
    add_voice(key, owner, voice_id, meta.get("name") or slug)


if __name__ == "__main__":
    main()
