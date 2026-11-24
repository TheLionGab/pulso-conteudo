#!/bin/zsh
# Pulso Brasil 02/11 (ECMWF, rodada 02/11; Conab até 23/10; chuva da semana e soja; fecho freemium). Depois da voz (audio/segs): G1, timeline (G2 dentro),
# trilha, mix (-14 LUFS), render 1080x1920, faststart, capa e G4. Sem chaves, sem envio.
set -e
R=/Users/mac/Studio/pulso-videos/_previas/pulso-brasil-2026-11-04-soja
PY=/Users/mac/Studio/pulso-videos/pulso-news-2026-10-14/venv/bin/python
PUB=$R/video/public
COMP=PulsoBrasil0411Soja
python3 -I $R/gates/g1_dossie.py $R
cd $R/audio
$PY montar.py . $PUB ${1:-auto}
$PY trilha.py $PUB
./mix.sh $PUB $PUB/mix.m4a
cd $R/video
npx tsc --noEmit -p .
npx remotion render $COMP out/bruto.mp4 --crf 23 --concurrency=2 --log=error
mkdir -p $R/out
ffmpeg -v error -y -i out/bruto.mp4 -c copy -movflags +faststart $R/out/pulso-brasil-0411-soja.mp4
QUADRO=15  # quadro 0,5s: número do gancho já visível, sem legenda
npx remotion still $COMP $R/out/capa.jpg --frame=$QUADRO --props='{"capa":true}' --image-format=jpeg --jpeg-quality=90 --log=error
python3 -I $R/gates/g4_manifesto.py $R $R/out/pulso-brasil-0411-soja.mp4 $R/out/capa.jpg
echo "pronto: $R/out/pulso-brasil-0411-soja.mp4"
