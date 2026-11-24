# Pulso Brasil

Da pasta deste molde: `./pulso-brasil.sh caminho/episodio.json`. No sucesso, o
comando imprime o MP4 em `$TMPDIR/pulso-brasil.*/out/`, junto com capa, manifesto,
`ep.json` e `legenda-instagram.txt`. Não publica nem agenda.

- Use os JSONs de `exemplos/` para montar a pauta. O roteiro é uma lista de
  `[id_da_cena, texto, pausa_em_segundos]`; `[cue]` marca o tempo e
  `*{42%|quarenta e dois por cento}*` separa a tela da fala. A última cena é
  `fecho_app`. Os exemplos reproduzem dados e texto do molde de soja (04/11) e
  reconstituem a pauta de chuva/soja (02/11) a partir do vídeo arquivado.
- Ao lado do JSON, deixe `dossie.json` e `fontes/` com as cópias que o G1
  exige (ou aponte `PULSO_DOSSIE` e `PULSO_FONTES`). O G5 também aplica o
  contrato de frescor da versão local do app ao dossiê. Os exemplos são fixtures
  editoriais; os snapshots e o cache de voz históricos não estão no Git.
- Mantenha `PULSO_HISTORICO` apontando para o JSONL de publicados, com data,
  pauta_id, tema, título e números-chave (mesmo formato do episódio). O
  `historico.jsonl` incluído é uma lista parcial de casos conhecidos, não uma
  sincronização do feed. O render não acrescenta registros: só entra o
  que tiver sido publicado.
- Instale FFmpeg, Node e as dependências em `video/` (`npm install` para gerar
  o lock se ausente; depois `npm ci`). Use Python ≥3.11 com `numpy`,
  `soundfile`; `PULSO_PYTHON` pode apontar ao ambiente virtual. O G3 usa
  `sherpa-onnx` com `PULSO_MODELOS` (pasta com `sherpa-onnx-whisper-base/`)
  ou, sem ele, `whisper-cli` com `PULSO_WHISPER_MODELO` (um `ggml-*.bin`).
  `PULSO_CHROME` aponta um chrome-headless-shell já baixado. O G5 usa a
  `origin/main` **local** do checkout `PULSO_APP_REPO` (padrão:
  `~/Developer/Pulso-Do-Campo`), em dry-run.
- Trave as fontes do dossiê uma vez, na pasta do episódio:
  `python3 -I gates/g1_dossie.py <pasta> --travar`. O pipeline reprova
  cópia sem trava, e `numeros_chave` fora do dossiê provado.
- `PULSO_ACERVO` altera a raiz do iCloud `Pulso-Videos-Arquivo`.
  `assets/obter.sh <public>` recupera a trilha e os clipes do manifesto.
  A síntese usa o cache em `PULSO_CACHE_VOZ` (padrão
  `~/Library/Caches/Pulso-Brasil/voz`). Voz oficial: ElevenLabs
  (`config/voz.json`, a mesma do app). Sem cache completo, só sintetiza com
  `ELEVENLABS_API_KEY` já no ambiente, até `PULSO_ELEVEN_TETO` caracteres
  novos (padrão 2500). Nunca troca de voz.

Verificação offline: `python3 -m unittest discover -s testes -v`.
Com as dependências Node instaladas: `cd video && npx tsc --noEmit`.
