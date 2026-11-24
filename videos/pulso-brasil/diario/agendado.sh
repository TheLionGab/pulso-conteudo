#!/usr/bin/env bash
# Episódio diário do Pulso Brasil, chamado pelo launchd (diario/com.pulso.video-diario.plist).
# Baixa a PTAX, pede ao Claude o episódio e o dossiê (diario/pauta.md), trava as fontes e
# renderiza com ~/bin/pulso-video. Não publica: o dono aprova e publica depois.
set -euo pipefail
export PATH="$HOME/.local/bin:$HOME/bin:/opt/homebrew/bin:/usr/bin:/bin"
raiz="$(cd "$(dirname "$0")/.." && pwd -P)"
dia="${1:-$(TZ=America/Cuiaba date +%F)}"
base="$HOME/Studio/pulso-videos/diario"
pasta="$base/$dia-instagram"
mkdir -p "$pasta/fontes"
exec >>"$base/agendado.log" 2>&1
echo "== $(date '+%F %T') episódio $dia"
if [ -f "$pasta/episodio.json" ] || [ -f "$pasta/sem-episodio.txt" ]; then
  echo "Já tratado; nada a fazer."; exit 0
fi

inicio="$(date -j -v-15d -f %F "$dia" +%m-%d-%Y)"
fim="$(date -j -f %F "$dia" +%m-%d-%Y)"
curl -fsS --max-time 60 -o "$pasta/fontes/bcb-ptax.json" \
  "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo(dataInicial=@i,dataFinalCotacao=@f)?@i='$inicio'&@f='$fim'&\$select=cotacaoVenda,dataHoraCotacao&\$format=json"

cd "$pasta"
claude -p "$(cat "$raiz/diario/pauta.md")

Dia: $dia
Pasta: $pasta
Molde: $raiz" \
  --add-dir "$raiz" --add-dir "$base/2026-11-24-instagram" \
  --allowedTools "Read" "Glob" "Grep" "Write(/$pasta/**)" "Edit(/$pasta/**)" \
    "Bash(python3 $raiz/episodio.py:*)" "mcp__supabase-pulso-ro__execute_sql"

if [ -f sem-episodio.txt ]; then echo "Sem episódio: $(cat sem-episodio.txt)"; exit 0; fi
test -f episodio.json && test -f dossie.json || { echo "Claude não gerou episodio.json e dossie.json"; exit 1; }
python3 -I "$raiz/gates/g1_dossie.py" "$pasta" --travar
pulso-video "$dia"
echo "Pronto para revisão: $pasta (vídeo no render.log)"
