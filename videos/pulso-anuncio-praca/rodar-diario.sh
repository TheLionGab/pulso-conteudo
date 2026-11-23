#!/usr/bin/env bash
# Gera os anúncios do dia: um vídeo por cidade, soja e milho.
# Uso (da raiz do repo):  bash videos/pulso-anuncio-praca/rodar-diario.sh
# Precisa de SUPABASE_URL e SUPABASE_ANON_KEY no ambiente (ver .env.example). Só faz GET.
set -euo pipefail
cd "$(dirname "$0")"
python3 -m unittest test_gerar
python3 gerar.py --baixar --produto soja --todas --render
DADOS=$(ls -t dados/imea-*.json | head -1)
python3 gerar.py --dados "$DADOS" --produto milho --todas --render
echo "Vídeos em: $(pwd)/out"
