# pulso-conteudo

Conteúdo do **Pulso do Campo** que não é o app: vídeos, peças de marketing e o material de
lançamento. Saiu do repositório do app (`TheLionGab/Pulso-Do-Campo`) em 19/10/2026 para o app
ficar só com código. Decisão do dono, já registrada lá em 21/09/2026: "sem vídeos no Pulso".

## O que tem aqui

| Pasta | O que é | Como roda |
|---|---|---|
| `videos/` | 7 projetos HyperFrames (composições HTML → MP4) | `cd videos/<projeto> && npm install && npm run check && npm run render` |
| `marketing/` | engine de stories, carrossel e reels (`engine/`) e as peças (`stories/`) | `node marketing/stories/<peça>/render.mjs` (precisa de Chromium e ffmpeg) |
| `INSTITUCIONAL/` | roteiro e post dos vídeos institucionais | os masters saem de `tools/export-institucional.sh` |
| `LAUNCH-PACK/` | manifesto do pacote de lançamento (o lançamento não aconteceu) | `tools/render-top3-cta-fix.sh` refaz os 3 masters |
| `tools/` | scripts que empacotam e re-renderizam os masters | rodar da raiz do repo |

- `videos/CLAUDE.md` vale para todos os projetos de vídeo (antes eram 4 cópias idênticas).
- Saída de render não entra no Git (`.gitignore`); ela é refeita a partir das composições.
- Caminhos de binário opcionais: `.env.example`.

## De onde veio

Importado da `main` do Pulso-Do-Campo em `bd08277`. O histórico anterior dessas pastas continua
lá, por exemplo `git log -- videos marketing INSTITUCIONAL LAUNCH-PACK`:

- `b746edad` 10/09/2026: higiene do repo, lint, CI e limpeza de branches (#198)
- `4e6f4114` 10/09/2026: promo com marca real do app + 5 projetos novos, render fora do Git (#191)
- `6e9faff4` 10/09/2026: promo mudo, o app vende sozinho (#110)
- `35d53855` 20/08/2026: stories, carrossel e reels (#98)

## O que não mora aqui

- Código, telas e lojas do app: `Pulso-Do-Campo`.
- Pipeline do Pulso News (`scripts/pulso-news/` no app) e os episódios em `~/Studio/pulso-videos/`.
