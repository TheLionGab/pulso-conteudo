#!/usr/bin/env bash
set -euo pipefail
raiz="$(cd "$(dirname "$0")" && pwd -P)"
python="${PULSO_PYTHON:-python3}"
entrada="$("$python" -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve(strict=True))' "${1:?Uso: ./pulso-brasil.sh episodio.json}")"
video="$raiz/video"
cd "$raiz"
"$python" episodio.py "$entrada"
"$python" gates/g_repeticao.py "$entrada" "${PULSO_HISTORICO:-$raiz/historico.jsonl}"

# Um diretório novo por tentativa: resultados e intermediários de episódios não se misturam.
trabalho="$(mktemp -d "${TMPDIR:-/tmp}/pulso-brasil.XXXXXXXX")"
echo "Trabalho: $trabalho"
origem="$(dirname "$entrada")"
public="$trabalho/video/public"
out="$trabalho/out"
mkdir -p "$public" "$out" "$trabalho/audio"
cp "$entrada" "$trabalho/episodio.json"
cp "${PULSO_DOSSIE:-$origem/dossie.json}" "$trabalho/dossie.json"
cp -R "${PULSO_FONTES:-$origem/fontes}" "$trabalho/fontes"
"$python" -I gates/g1_dossie.py "$trabalho"
"$python" -I gates/g2_fala.py "$trabalho"
"$python" -c 'import numpy, soundfile'
for ferramenta in ffmpeg ffprobe node git; do
  command -v "$ferramenta" >/dev/null || { echo "Instale $ferramenta" >&2; exit 1; }
done
# G3: sherpa-onnx (pasta de modelos) se houver; senão whisper.cpp com um ggml-*.bin local.
modelos="${PULSO_MODELOS:-${PULSO_ACERVO:-$HOME/Library/Mobile Documents/com~apple~CloudDocs/Pulso-Videos-Arquivo}/modelos}"
if ! { "$python" -c 'import sherpa_onnx' 2>/dev/null && { test -s "$modelos/sherpa-onnx-whisper-small/small-encoder.onnx" || test -s "$modelos/sherpa-onnx-whisper-base/base-encoder.onnx"; }; }; then
  modelos="${PULSO_WHISPER_MODELO:-$HOME/Library/Application Support/superwhisper/ggml-small.bin}"
  test -s "$modelos" || { echo "G3: sem sherpa-onnx e sem modelo whisper.cpp (PULSO_WHISPER_MODELO)" >&2; exit 1; }
  command -v "${PULSO_WHISPER_CLI:-whisper-cli}" >/dev/null || { echo "G3: instale whisper-cpp (whisper-cli)" >&2; exit 1; }
fi
echo "G3 com: $modelos"
remotion="$video/node_modules/.bin/remotion"
test -x "$remotion" || { echo "Instale as dependências npm em video/" >&2; exit 1; }
# Navegador já baixado (PULSO_CHROME) evita o download do headless shell a cada máquina nova.
navegador=()
if [ -n "${PULSO_CHROME:-}" ]; then navegador=(--browser-executable="$PULSO_CHROME"); fi
app="${PULSO_APP_REPO:-$HOME/Developer/Pulso-Do-Campo}"
app="$(cd "$app" && pwd -P)"
for arquivo in publicar.mjs frescor.mjs; do
  git -C "$app" cat-file -e "origin/main:scripts/pulso-news/$arquivo" ||
    { echo "G5: $arquivo ausente na origin/main local (PULSO_APP_REPO)" >&2; exit 1; }
done
export PULSO_APP_REPO="$app"
PULSO_PYTHON="$python" assets/obter.sh "$public"
"$python" -c 'import json, sys; from pathlib import Path; p = Path(sys.argv[1]); (p/"audio/roteiro.json").write_text(json.dumps(json.loads((p/"episodio.json").read_text())["roteiro"], ensure_ascii=False))' "$trabalho"
"$python" -m audio.voz "$trabalho/episodio.json" "$trabalho/audio" "${PULSO_CACHE_VOZ:-$HOME/Library/Caches/Pulso-Brasil/voz}"
"$python" gates/g_voz.py "$trabalho/audio/sintese.json"
"$python" audio/montar.py "$trabalho/audio" "$public" auto "$trabalho/audio/roteiro.json"
"$python" -I gates/g3_asr.py "$trabalho" "$modelos"
"$python" -m audio.trilha "$public"
bash audio/mix.sh "$public" "$public/mix.m4a"

"$python" - "$trabalho" <<'PY'
import json
import math
from pathlib import Path
import sys

p = Path(sys.argv[1])
ep = json.loads((p / "episodio.json").read_text())
timeline = json.loads((p / "video/public/timeline.json").read_text())
duracao = math.ceil(timeline["duracao"] * 30) / 30
if not 30 <= duracao <= 60:
    sys.exit(f"Duração calculada {duracao:.2f} s fora de 30–60 s")
for capa, arquivo in [(False, "props.json"), (True, "props-capa.json")]:
    (p / arquivo).write_text(json.dumps(dict(episodio=ep, timeline=timeline, capa=capa), ensure_ascii=False))
PY

cd "$video"
"$python" "$raiz/assets/integridade.py" verificar "$public"
"$remotion" render src/index.ts PulsoBrasil "$trabalho/bruto.mp4" --props="$trabalho/props.json" \
  --public-dir="$public" --codec=h264 --audio-codec=aac --crf=23 --concurrency=2 ${navegador[@]+"${navegador[@]}"}
ffmpeg -v error -i "$trabalho/bruto.mp4" -c copy -movflags +faststart "$out/pulso-brasil.mp4"
"$remotion" still src/index.ts PulsoBrasil "$out/capa.jpg" --frame=15 --props="$trabalho/props-capa.json" \
  --public-dir="$public" --image-format=jpeg --jpeg-quality=90 ${navegador[@]+"${navegador[@]}"}
"$python" -I "$raiz/gates/g4_manifesto.py" "$trabalho" "$out/pulso-brasil.mp4" "$out/capa.jpg"
"$python" -I "$raiz/gates/g5_ep_json.py" "$trabalho" "$out/pulso-brasil.mp4" "$out/capa.jpg"
echo "Pronto: $out/pulso-brasil.mp4"
