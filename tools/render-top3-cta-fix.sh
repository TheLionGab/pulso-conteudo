#!/usr/bin/env bash
# Re-render dos 3 masters institucionais após correção de CTA (09/09/2026).
set -euo pipefail
export CHROMIUM_PATH="${CHROMIUM_PATH:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PACK="$ROOT/LAUNCH-PACK/renders"
STAMP="2026-09-09_CTA-FIX"

render_one() {
  local dir="$1" out_name="$2"
  echo ">> [$out_name] check + render"
  (cd "$ROOT/videos/$dir" && npm run check && npm run render -- --output "renders/${out_name}.mp4")
  cp "$ROOT/videos/$dir/renders/${out_name}.mp4" "$PACK/${out_name}.mp4"
  ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$PACK/${out_name}.mp4"
  echo "  OK $out_name"
}

mkdir -p "$PACK"
render_one pulso-device-launch "00-device-hero_${STAMP}"
render_one pulso-cotacoes-brasil "01-cotacoes-hero_${STAMP}"
render_one pulso-comunidade "06-comunidade_${STAMP}"

# Symlink canônicos para export (mantém PERFECT como fallback se script falhar)
for base in 00-device-hero 01-cotacoes-hero 06-comunidade; do
  cp "$PACK/${base}_${STAMP}.mp4" "$PACK/${base}_2026-09-08_PERFECT.mp4"
done

echo ">> top3 CTA-FIX prontos em $PACK"
