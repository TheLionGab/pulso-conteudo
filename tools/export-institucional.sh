#!/usr/bin/env bash
# Empacota vídeos institucionais Pulso do Campo — masters finais.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/LAUNCH-PACK/renders"
OUT="$ROOT/INSTITUCIONAL"
DIAG="$ROOT/videos/pulso-diagnostico-praga/renders"
export CHROMIUM_PATH="${CHROMIUM_PATH:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"

mkdir -p "$OUT/vertical" "$OUT/app-store" "$OUT/qc"

# Re-render diagnóstico com VO HeyGen (se ainda não existe FINAL)
if [ ! -f "$DIAG/pulso-diagnostico-praga_INSTITUCIONAL.mp4" ]; then
  echo ">> render diagnóstico + VO"
  (cd "$ROOT/videos/pulso-diagnostico-praga" && npm run check && npm run render -- --output renders/pulso-diagnostico-praga_INSTITUCIONAL.mp4)
fi

copy() {
  local src="$1" dest="$2"
  cp "$src" "$OUT/vertical/$dest"
  ffprobe -v error -show_entries format=duration,size -of csv=p=0 "$OUT/vertical/$dest"
  echo "  OK $dest"
}

echo ">> copiando masters"
copy "$SRC/00-device-hero_2026-09-08_PERFECT.mp4" "01-hero-device-21s.mp4"
copy "$SRC/01-cotacoes-hero_2026-09-08_PERFECT.mp4" "02-cotacoes-22s.mp4"
copy "$SRC/02-engenharia-escada_2026-09-08_PERFECT.mp4" "03-engenharia-escada-25s.mp4"
copy "$SRC/03-engenharia-cvale_2026-09-08_PERFECT.mp4" "04-engenharia-cvale-22s.mp4"
copy "$SRC/04-engenharia-dados_2026-09-08_PERFECT.mp4" "05-engenharia-dados-22s.mp4"
copy "$DIAG/pulso-diagnostico-praga_INSTITUCIONAL.mp4" "06-diagnostico-20s.mp4"
copy "$SRC/06-comunidade_2026-09-08_PERFECT.mp4" "07-comunidade-18s.mp4"

# App Store preview 30s (corte do hero device)
HERO="$OUT/vertical/01-hero-device-21s.mp4"
ffmpeg -y -i "$HERO" -t 30 -c copy "$OUT/app-store/preview-30s.mp4" 2>/dev/null || \
  ffmpeg -y -i "$HERO" -t 21 -c copy "$OUT/app-store/preview-21s.mp4"

# QC frames
ffmpeg -y -ss 6 -i "$HERO" -frames:v 1 "$OUT/qc/hero-cotacoes.jpg" 2>/dev/null

echo ">> INSTITUCIONAL pronto em $OUT"
ls -lh "$OUT/vertical/"
