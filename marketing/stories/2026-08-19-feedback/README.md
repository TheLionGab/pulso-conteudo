# Stories de feedback — Pulso do Campo (19/08/2026)

Sequência de 3 stories pedindo a opinião de quem já usa o app. Objetivo declarado:
**coletar feedback qualificado o suficiente para priorizar backlog**, não juntar coração.

Por isso a sequência é um funil, não três posts soltos:

| # | Sticker | O que extrai | Atrito |
| - | ------- | ------------ | ------ |
| 1 | Caixinha de perguntas | Texto aberto — a única fonte de "o que falta" | Alto |
| 2 | Enquete (2 opções) | Sinal binário de utilidade do Radar | Baixo |
| 3 | Controle deslizante | Intensidade de recomendação (proxy de NPS) | Baixo |

Ordem proposital: quem responde a caixinha (2) e o slider (3) já engajou; postar os
fáceis primeiro derruba a taxa de resposta do difícil, que é justamente o que tem valor.
Se for postar só um, poste o **1**.

## Arquivos

| Arquivo | Para quê |
| ------- | -------- |
| `out/story-1.png` · `out/story-2.png` · `out/story-3.png` | Arte final, 1080×1920. É o que sobe. |
| `out/story-1-guia.jpg` · `-2-` · `-3-` | Mesma arte com a zona do sticker demarcada. **Não subir** — é referência de montagem. |
| `out/story-1.mp4` · `-2-` · `-3-` | Versão animada de 6s de cada peça (H.264 High, yuv420p, 1080×1920, 30fps, sem áudio, faststart). Pode subir vídeo nos três — o sticker funciona igual. |
| `out/MANIFEST.json` | Dimensões, sha256 e o resultado da validação de cada MP4. |
| `src/story.html` | Fonte da arte. Todo o texto vive no objeto `FRAMES` — editar lá, não no PNG. |
| `render.mjs` | Regenera tudo a partir do HTML. |

## Copy (fonte: `src/story.html`, objeto `FRAMES`)

**Story 1 — caixinha de perguntas**
Título: *O que você está achando do Pulso do Campo?*
Apoio: *Sem filtro. O que você responder aqui define o que a gente faz primeiro.*
Sticker: caixinha de perguntas, prompt sugerido → `Manda a real`
Rodapé: *Responde aí embaixo — a gente lê tudo*

**Story 2 — enquete**
Título: *O Radar de hoje te ajudou a decidir alguma coisa?*
Apoio: *Duas opções, dois segundos. Não tem resposta certa.*
Sticker: enquete → `Ajudou` / `Ainda não`

**Story 3 — controle deslizante**
Título: *Quanto você indicaria o Pulso pra outro produtor?*
Apoio: *Nota baixa com motivo vale mais que nota alta calada.*
Sticker: controle deslizante, emoji 🔥

## Como postar

1. Subir o PNG (ou o MP4 no story 1) sem cortar — a arte já é 1080×1920, o Instagram
   não deve reenquadrar.
2. Posicionar o sticker **dentro do retângulo do arquivo `-guia`**. A arte foi montada
   com esse espaço vazio de propósito; sticker em cima do título mata a leitura.
3. Não empilhar sticker extra (localização, música, hashtag). Cada sticker a mais divide
   o toque e derruba a taxa de resposta do que interessa.
4. Intervalo sugerido: os três no mesmo bloco, na ordem 1 → 2 → 3.
5. Responder as caixinhas no privado no mesmo dia. Quem respondeu e recebeu retorno
   responde de novo na próxima; quem não recebeu, não.

### Depois

O que voltar da caixinha (story 1) vira item em `docs/BACKLOG.md` — pedido de usuário é
entrada de backlog, não print no grupo.

## Regenerar

```bash
node marketing/stories/2026-08-19-feedback/render.mjs            # PNGs + MP4
node marketing/stories/2026-08-19-feedback/render.mjs --no-video # só PNGs (rápido)
```

Não precisa instalar nada no monorepo: o script fala CDP direto com o Chromium e chama o
`ffmpeg` do sistema. Dois pontos que travam:

- **`ffmpeg` sem libx264.** O script checa antes de renderar e falha explicando. A build
  que vem junto do Playwright (`/opt/pw-browsers/ffmpeg-*`) só encoda VP8/WebM, e o
  Instagram não aceita WebM. `brew install ffmpeg` resolve; ou aponte `FFMPEG_PATH`.
- **Texto que cresceu.** `assertFits()` derruba o render se o conteúdo vazar a safe area
  (250px em cima, 320px embaixo) ou se o título quebrar uma linha a mais. Isso é
  proposital: PNG torto só aparece depois de publicado.

O quadro renderizado é função pura de `?t=<ms>` — nenhuma animação roda sozinha, todas
ficam congeladas em `animation-play-state: paused` com delay negativo. Rodar duas vezes
produz o mesmo arquivo (verificado: os seis PNG/JPG saíram com sha256 idêntico em duas
execuções seguidas).

### Validação dos MP4

`validateMp4()` roda depois de cada encode e **decodifica o arquivo inteiro** — tamanho de
arquivo não prova nada, MP4 truncado abre no Finder e falha no upload. Reprova o render se:

- o codec não for H.264 ou o `pix_fmt` não for `yuv420p` (o Instagram recusa);
- a dimensão não for 1080×1920 ou a taxa não for 30fps;
- a contagem de quadros decodificados não bater com os 180 gerados;
- houver faixa de áudio;
- o átomo `moov` vier depois do `mdat` (sem faststart, o player espera o arquivo inteiro
  antes de começar — o que trava justamente em conexão de campo).

Estado atual dos três: `h264 (High) / yuv420p / 1080x1920 / DAR 9:16 / 180 quadros`.

## Kling — não usado, e por quê

A geração por Kling ficou de fora desta entrega por dois bloqueios concretos, nenhum
contornável de dentro desta sessão:

1. Não há credencial de Kling no ambiente (`KLING_ACCESS_KEY`/`KLING_SECRET_KEY` e
   variantes: todas vazias).
2. O proxy de egress bloqueia `app.klingai.com`, então nem a documentação da API dá para
   consultar — escrever o cliente de memória e chamar de "verificado" seria mentira.

O `story-1.mp4` entregue foi gerado localmente a partir da mesma arte, o que tem uma
vantagem que vídeo generativo não tem aqui: tipografia nítida e marca correta. Modelo de
vídeo não escreve "Pulso do Campo" sem errar a letra.

Se ainda quiser um plano de fundo gerado por Kling para trocar o gradiente, o prompt está
em `kling-prompt.md` — mas ele é para **fundo**, nunca para o texto.
