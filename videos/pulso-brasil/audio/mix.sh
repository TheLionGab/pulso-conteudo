#!/bin/zsh
# Mix final do Pulso Brasil: voz + trilha telejornal com ducking 3:1 + efeitos, -14 LUFS, true peak -1,5 dBTP.
# loudnorm em passada única não garante o teto e o AAC ainda sobe o pico; o alimiter a -3 dBFS segura o
# G4 (pico ≤ -1 dBTP) sem mexer no LUFS (só corta os picos). Run 45598231609: -0,9 dBTP reprovado.
# Também grava medida_voz.wav e medida_mus.wav (voz e música como entram na soma) para o G3-mix.
# Uso: mix.sh <pasta_public> <saida.m4a>
set -e
P=$1
OUT=$2
ffmpeg -v error -y \
  -i "$P/voz.wav" -i "$P/musica.wav" -i "$P/efeitos.wav" \
  -filter_complex "
    [0:a]aresample=48000,highpass=f=80,equalizer=f=250:t=q:w=1:g=-2,equalizer=f=3200:t=q:w=1.2:g=2.5,
         acompressor=threshold=-20dB:ratio=3:attack=5:release=90:makeup=3,
         aformat=channel_layouts=stereo,asplit=3[voz][chave][mvoz];
    [1:a]volume=0.8[mus];
    [mus][chave]sidechaincompress=threshold=0.07:ratio=3:attack=15:release=300,asplit=2[musduck][mmus];
    [2:a]volume=0.5[fx];
    [voz][musduck][fx]amix=inputs=3:normalize=0:duration=longest,
         loudnorm=I=-14:TP=-1.5:LRA=11,
         aresample=48000,alimiter=limit=0.708:level=disabled:attack=5:release=50[out]" \
  -map "[out]" -ar 48000 -c:a aac -b:a 192k "$OUT" \
  -map "[mvoz]" -ar 48000 "$P/medida_voz.wav" \
  -map "[mmus]" -ar 48000 "$P/medida_mus.wav"
echo "mix → $OUT"
