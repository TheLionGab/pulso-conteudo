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
# Aviso na Central de Notificações do Mac. Texto vai por argv: aspas do motivo não quebram o AppleScript.
avisar() {
  osascript -e 'on run argv' -e 'display notification (item 2 of argv) with title (item 1 of argv) sound name "Glass"' \
    -e 'end run' "$1" "$2" >/dev/null 2>&1 || true
}
# .pronto só é gravado no fim: se a voz ou um gate falhou, a próxima rodada tenta de novo.
if [ -f "$pasta/.pronto" ] || [ -f "$pasta/sem-episodio.txt" ]; then
  echo "Já tratado; nada a fazer."; exit 0
fi
# A trava das fontes da coleta fica fora de $pasta (o modelo só escreve em $pasta).
trava="$(mktemp "${TMPDIR:-/tmp}/pulso-coleta.XXXXXXXX")" || { echo "mktemp falhou"; exit 1; }
trap 'codigo=$?; rm -f "$trava"; [ "$codigo" -eq 0 ] || avisar "Pulso: vídeo $dia falhou" "Saída $codigo. Detalhe no fim de Studio/pulso-videos/diario/agendado.log."' EXIT
sem_episodio() { echo "Sem episódio: $(cat sem-episodio.txt)"; avisar "Pulso: sem vídeo $dia" "$(cat sem-episodio.txt)"; exit 0; }
cd "$pasta"

if [ ! -f episodio.json ]; then
  # PTAX e IMEA vêm do script (mesmo da nuvem, .github/workflows/pulso-brasil-diario.yml): o modelo só lê.
  # A service role do app fica no Chaves e vai só ao script, nunca ao claude.
  chave_app="${SUPABASE_SERVICE_ROLE_KEY:-$(security find-generic-password -a "$USER" -s pulso-supabase-service -w 2>/dev/null)}" ||
    { echo "Chave do app não encontrada. Rode uma vez: pulso-video --guardar-chave-app"; exit 1; }
  coleta=0
  SUPABASE_SERVICE_ROLE_KEY="$chave_app" python3 -I "$raiz/diario/coletar_dados.py" "$pasta" "$dia" --trava "$trava" || coleta=$?
  unset chave_app
  [ "$coleta" -ne 3 ] || sem_episodio
  [ "$coleta" -eq 0 ] || { echo "Coleta de dados falhou (saída $coleta)"; exit 1; }

  # Leitura e escrita só nas pastas do molde e do dia (o episódio modelo está em $raiz/exemplos).
  env -u SUPABASE_SERVICE_ROLE_KEY claude -p "$(cat "$raiz/diario/pauta.md")

Dia: $dia
Pasta: $pasta
Molde: $raiz" \
    --add-dir "$raiz" \
    --allowedTools "Read(/$raiz/**)" "Read(/$pasta/**)" \
      "Glob(/$raiz/**)" "Glob(/$pasta/**)" "Grep(/$raiz/**)" "Grep(/$pasta/**)" \
      "Write(/$pasta/**)" "Edit(/$pasta/**)" \
      "Bash(python3 $raiz/episodio.py:*)"

  # PTAX e IMEA gravados pelo script não podem ter sido mexidos pelo modelo, e fontes/ não ganha arquivo novo.
  python3 -I "$raiz/diario/coletar_dados.py" --conferir "$pasta" --trava "$trava" ||
    { echo "fonte mudou durante o claude; episódio descartado"; mv episodio.json episodio.rejeitado.json 2>/dev/null; exit 1; }
  if [ -f sem-episodio.txt ]; then sem_episodio; fi
fi

test -f episodio.json && test -f dossie.json || { echo "Claude não gerou episodio.json e dossie.json"; exit 1; }
# O que o modelo escreveu tem de ser do dia pedido (data do episódio e do dossiê, id do dossiê).
python3 -I "$raiz/diario/conferir_episodio.py" "$dia" "$pasta"
grep -q fontes_sha256 dossie.json || python3 -I "$raiz/gates/g1_dossie.py" "$pasta" --travar
pulso-video "$dia"
touch .pronto
echo "Pronto para revisão: $pasta (vídeo no render.log)"
avisar "Pulso: vídeo $dia pronto" "Para revisar em Studio/pulso-videos/diario/$dia-instagram (caminho no render.log)."
