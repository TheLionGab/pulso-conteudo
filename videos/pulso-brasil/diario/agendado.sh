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
# .pronto só é gravado no fim: se a voz ou um gate falhou, a próxima rodada tenta de novo.
if [ -f "$pasta/.pronto" ] || [ -f "$pasta/sem-episodio.txt" ]; then
  echo "Já tratado; nada a fazer."; exit 0
fi
cd "$pasta"
modelo="$base/2026-11-24-instagram"

if [ ! -f episodio.json ]; then
  inicio="$(date -j -v-15d -f %F "$dia" +%m-%d-%Y)"
  fim="$(date -j -f %F "$dia" +%m-%d-%Y)"
  curl -fsS --retry 3 --retry-delay 30 --max-time 60 -o fontes/bcb-ptax.json \
    "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo(dataInicial=@i,dataFinalCotacao=@f)?@i='$inicio'&@f='$fim'&\$select=cotacaoVenda,dataHoraCotacao&\$format=json"
  python3 -I -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1])).get("value") else 1)' fontes/bcb-ptax.json ||
    { echo "PTAX vazia no Banco Central" > sem-episodio.txt; echo "Sem episódio: PTAX vazia"; exit 0; }
  ptax_sha="$(shasum -a 256 fontes/bcb-ptax.json)"

  # Leitura e escrita só nas pastas do molde, do dia e do episódio modelo.
  claude -p "$(cat "$raiz/diario/pauta.md")

Dia: $dia
Pasta: $pasta
Molde: $raiz" \
    --add-dir "$raiz" --add-dir "$modelo" \
    --allowedTools "Read(/$raiz/**)" "Read(/$pasta/**)" "Read(/$modelo/**)" \
      "Glob(/$raiz/**)" "Glob(/$pasta/**)" "Grep(/$raiz/**)" "Grep(/$pasta/**)" \
      "Write(/$pasta/**)" "Edit(/$pasta/**)" \
      "Bash(python3 $raiz/episodio.py:*)" "mcp__supabase-pulso-ro__execute_sql"

  # A PTAX baixada pelo script não pode ter sido mexida pelo modelo.
  [ "$(shasum -a 256 fontes/bcb-ptax.json)" = "$ptax_sha" ] ||
    { echo "fontes/bcb-ptax.json mudou durante o claude; episódio descartado"; mv episodio.json episodio.rejeitado.json 2>/dev/null; exit 1; }
  if [ -f sem-episodio.txt ]; then echo "Sem episódio: $(cat sem-episodio.txt)"; exit 0; fi
fi

test -f episodio.json && test -f dossie.json || { echo "Claude não gerou episodio.json e dossie.json"; exit 1; }
grep -q fontes_sha256 dossie.json || python3 -I "$raiz/gates/g1_dossie.py" "$pasta" --travar
pulso-video "$dia"
touch .pronto
echo "Pronto para revisão: $pasta (vídeo no render.log)"
