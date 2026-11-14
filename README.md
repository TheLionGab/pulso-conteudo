# pulso-conteudo

Conteúdo do **Pulso do Campo** que não é o app: vídeos, peças de marketing e o material de
lançamento. Saiu do repositório do app (`TheLionGab/Pulso-Do-Campo`) em 19/10/2026 para o app
ficar só com código. Decisão do dono, já registrada lá em 21/09/2026: "sem vídeos no Pulso".

## O que tem aqui

Este checkout usa `sparse-checkout`: só `tools/`, este README e `.gitignore`
foram materializados inicialmente. As pastas abaixo descrevem o repositório,
não garantem presença local. Confira `git sparse-checkout list` antes de renderizar;
materialize apenas a pasta necessária, preservando alterações locais.

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

## Distribuição do Pulso News

A skill Codex `.agents/skills/pulso-publicar/` reúne o procedimento assistido de
publicação no Instagram e catálogo do app. O helper `scripts/workflow.py` dessa
skill executa somente preflight e plano de retomada, sem rede ou escrita no episódio.
Não é um publicador autônomo nem uma agenda; os canais são operados pelo agente
com a autorização vigente e os gates do pipeline. Recibos existentes impedem
republicar por engano. Leia o `SKILL.md` antes de usar.

### Pacote aprovado → catálogo do app

`tools/pulso_news_app.py` integra o pacote do Studio ao catálogo existente, sem
criar outro gerador, agenda, chave ou SDK. `prepare` é offline; `publish` usa a
sessão já autenticada do Supabase CLI no projeto fixo do Pulso. Não altera código
do app, schema, RLS nem dispara push manual. O app já lê o catálogo remoto: não
precisa de novo binário para cada episódio.

```sh
python3 tools/pulso_news_app.py prepare /caminho/episodio \
  --snapshot qa/backup-app-completo.json --replace-id ID_ANTERIOR
python3 -m unittest discover -s tools -p 'test_pulso_news_app.py'
```

O snapshot completo é obtido por SELECT no projeto confirmado. O pacote exige
manifesto, capa, metadados, crítico no hash do vídeo e `out/pronto-app.json` com
G-PESQUISA/G0/G1/G2/G3/G4/G3-mix/visual/editorial e hashes das provas. Plano e SQL
ficam no episódio, fora deste repo. O SQL exige parecer independente no próprio
hash em `qa/revisao-sql.json` (`aprovado: true`, `sql_sha256`). Antes de publicar,
confira autorizações e ownership vigentes; arquivo de parecer não concede acesso.

```sh
python3 tools/pulso_news_app.py publish /caminho/episodio
```

O G6 canônico continua obrigatório. Exceção só com autorização **específica** do
dono no chat e recibo vinculado ao ID/hash desta edição, não reutilizável, passado
por `--g6-authorization qa/autorizacao-g6-app.json`. Falha não vira dispensa
automática. Não replique credenciais para fazer o G6 funcionar.

Dia ocupado não é substituído implicitamente. Troca autorizada preserva a edição
anterior como rascunho, sem apagar mídia; compara e trava o snapshot completo na
mesma transação do INSERT. A publicação grava backup, journal antes de enviar,
confere bytes/hashes públicos e leitura como `anon`, então combina os recibos dos
canais atomicamente. Falha deixa `uncertain`: reconciliar, nunca reenviar às cegas.
Não usar `retirar` para esta troca: esse comando apaga mídia.

Os dois produtores atuais (diário do app e Studio) continuam separados. Antes de
gastar voz no Studio, consulte o catálogo do dia para decidir qual edição distribuir.
Uma rotina instalada não prova que a edição futura passou nos gates ou foi publicada.
