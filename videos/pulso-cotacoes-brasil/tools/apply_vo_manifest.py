#!/usr/bin/env python3
"""Aplica manifest VO v24 no index.html (durações + paths)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

# timeline 22s — offsets fixos V2.3
STARTS = {
    "vo-01-abertura.mp3": 0.4,
    "vo-02-busca.mp3": 3.6,
    "vo-03-preco.mp3": 8.6,
    "vo-04-carrossel.mp3": 13.6,
    "vo-05-contraste.mp3": 17.6,
    "vo-06-cta.mp3": 20.3,
}
ORDER = list(STARTS.keys())


def main() -> None:
    manifest_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if not manifest_path:
        sys.exit("uso: python3 apply_vo_manifest.py assets/vo/v24-andrea-lot/manifest.json")
    items = json.loads(manifest_path.read_text())
    by_file = {Path(x["file"]).name: x for x in items if "file" in x}
    html = INDEX.read_text()
    blocks: list[str] = []
    for i, fname in enumerate(ORDER, 1):
        if fname not in by_file:
            continue
        rel = by_file[fname]["file"]
        dur = by_file[fname]["duration_s"]
        start = STARTS[fname]
        id_ = f"el-vo-{i:02d}"
        blocks.append(
            f'      <audio id="{id_}" src="{rel}" data-start="{start}" '
            f'data-duration="{dur:.2f}" data-track-index="10" data-volume="1.0"></audio>'
        )
    block = "\n".join(blocks)
    html, n = re.subn(
        r"      <!-- VO.*?-->\n(?:      <audio id=\"el-vo-\d+\".*?</audio>\n)+",
        f"      <!-- VO — ElevenLabs v24 ({manifest_path.parent.name}) -->\n{block}\n",
        html,
        count=1,
        flags=re.DOTALL,
    )
    if n != 1:
        sys.exit("BLOCKED: bloco VO não encontrado em index.html")
    INDEX.write_text(html)
    print("OK", INDEX)


if __name__ == "__main__":
    main()
