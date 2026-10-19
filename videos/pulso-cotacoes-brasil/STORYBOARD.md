---
format: 1080x1920
duration: 30.7s
message: "Cotação de comprador real, na sua cidade — em qualquer cidade do Brasil"
arc: Abertura silenciosa → Busca → Preço real revelado → Carrossel nacional → Cobertura no mapa → Contraste → CTA
audience: produtores rurais brasileiros (soja/milho), usuários e leads do Pulso do Campo
mode: autonomous
music: none — sem trilha melódica; SFX pulsado como underscore rítmico (impact-bass em beats fortes, whoosh nos cortes, click/pop/typing nas interações de UI)
voiceover: none — vídeo mudo por decisão de direção; o app é o narrador
---

## Video direction

- **Pivot de direção (26/08):** vídeo silencioso, estilo preview de App Store —
  "onde eu nem preciso falar, o próprio app fala". Nenhum frame tem VO. Texto
  em tela é só rótulo funcional de UI (nome de tela, badge, valor), nunca
  legenda de fala. O produto (mock-UI do app) é o herói em 4 dos 7 frames.
- **Palette (frame.md por papel):** canvas escuro `ink-black` em todos os frames
  (registro DARK do broadside); `fire-orange` (= verde-marca #10b981) é o único
  acento — reservado para o payoff de cada frame (preço real, badge, lockup).
  Texto em `cream`; apoio em `cream-muted`; hairlines `border-dark`. O device
  (celular) é o único elemento com cantos arredondados — broadside = cantos
  retos em todo o resto.
- **Motion grammar:** sem VO para ancorar reveals, o ritmo agora é por
  **beat de SFX** — cada elemento chega no cue do SFX, não de uma fala. Cursor
  oversized (house style) conduz toda interação de UI: tap, swipe, digitação —
  é ele quem "fala" pelo produto. `power3` long-tail decel como default, settle
  liso, zero overshoot/bounce.
- **Ritmo / frames segurados:** Frame 6 (contraste) e Frame 7 (lockup) terminam
  em held read — a calma é o clímax, igual antes. Frames 1 e 4 (abertura e
  carrossel) são os de tempo mais agressivo — motion pura, sem texto para ler.
- **Negative list:** sem gradientes roxo-azul "IA", sem bokeh flutuante, sem
  chrome de browser/cursor real fora do mock-UI, sem bordas arredondadas fora
  do device, sem slideshow (front-load + freeze), sem legenda de fala (não há
  fala). Números sempre `tabular-nums`. Conteúdo importante no topo ~83%.

## Frame 1 — Abertura: o app acorda

- type: hook
- blueprint: device-surface-showcase + oversized-cursor
- scene: Palco escuro; ícone do app pulsa sozinho; cursor oversized entra e toca; ripple de toque; tela abre em wipe vertical revelando o header "Cotações"
- duration: 2.6s
- transition_in: cut
- status: pending
- src: compositions/frames/01-abertura.html
- voiceover: none
- asset_candidates:

Sem tipografia falada — a primeira coisa que o espectador vê é o produto
sendo tocado, não uma frase. O cursor gigante é o único "personagem" fora
da tela do app; ele entra de fora do frame (house style oversized-cursor),
mira o ícone, clica, e o clique é o gatilho de tudo que segue.

- blueprint: device-surface-showcase (Adapt) + oversized-cursor (Reproduce)
- focal: ícone do app "Pulso do Campo" (construído — wordmark do preset + ponto verde, mesma assinatura do Frame 7 antigo)
- roles: (nenhum candidate)
- sfx: whoosh-short (entrada do cursor), click-soft (toque no ícone), pop (wipe de abertura)

Scene 1 (0.0–0.9s): canvas escuro vazio; ícone do app (quadrado stone escuro, cantos levemente arredondados, ponto verde pulsante + "P" do wordmark) aparece centrado, ~18% da largura, pulso sutil de glow em loop (2 ciclos) sinalizando "toque aqui".
Scene 2 (0.9–1.7s): cursor oversized entra de fora do frame (canto inferior direito, offscreen law), percorre a diagonal até o ícone com ease de aproximação, mira a ponta exatamente no centro do ícone.
Scene 3 (1.7–2.6s): tap — cursor comprime (squash sutil), ripple verde se expande do ponto de toque; no pico do ripple, wipe vertical (bottom→top) revela a tela do app por trás: header "Cotações" já visível no topo; hold de 2 frames até o corte.

## Frame 2 — Busca: qualquer cidade do Brasil

- type: pain_point→feature (invertido: mostra a solução buscando, não o problema falado)
- blueprint: device-surface-showcase
- scene: Tela de busca do app; campo de busca com cursor piscando; nomes de cidades reais digitam e apagam em sequência rápida; cursor oversized toca "usar minha localização" ou digita "Sorriso"
- duration: 5.0s
- transition_in: crossfade
- status: pending
- src: compositions/frames/02-busca.html
- voiceover: none
- asset_candidates:

A ausência de fala aqui é o ponto: em vez de dizer "cotação em qualquer
cidade", o campo de busca literalmente digita e troca nomes de cidades reais
— a UI prova a abrangência sozinha. Termina com o cursor tocando "Sorriso,
MT" na lista de sugestões, confirmando a seleção.

- blueprint: device-surface-showcase (Adapt)
- focal: campo de busca + lista de sugestões (construído)
- roles: (nenhum candidate)
- sfx: typing (loop curto por nome), click-soft (seleção final)

Scene 1 (0.0–1.0s): device já em tela (continuidade do Frame 1, sem reabrir), header "Cotações" com campo de busca vazio abaixo, placeholder "Buscar cidade…" com cursor piscando (caret verde).
Scene 2 (1.0–3.4s): digitação sintética em rajada — "Sorriso" digita letra a letra (typewriter, ~60ms/char), pausa 0.3s, apaga, "Rio Verde" digita, pausa, apaga, "Cascavel" digita — 3 ciclos rápidos, cada um revela 2-3 linhas de sugestão abaixo do campo (cidade + estado, mono pequeno).
Scene 3 (3.4–5.0s): na última rajada, "Sorriso" digita de novo e PARA (não apaga); lista de sugestões mostra "Sorriso, MT" destacado; cursor oversized entra e toca a sugestão — highlight verde no tap, hold curto até o corte.

## Frame 3 — Preço real revelado

- type: feature_showcase (herói do vídeo)
- blueprint: device-surface-showcase
- scene: Card de cotação se monta por partes: "Oferta de compra — Soja", valor R$ 129,50/sc em count-up, selo "comprador verificado", linha de procedência "coletado do site do comprador"
- duration: 6.5s
- transition_in: push-slide LEFT
- status: pending
- src: compositions/frames/03-comprador.html
- voiceover: none
- asset_candidates:

O clímax de produto do vídeo — mesmo conteúdo do antigo Frame 5, mas agora
sem VO ancorando o ritmo: cada peça do card chega no beat de um SFX (não de
uma fala), então o timing fica mais curto e mais percussivo. É o frame que
mais precisa ficar "impecável" — é o que vende sozinho.

- blueprint: device-surface-showcase (Reproduce, ritmo adaptado para SFX-only)
- focal: card de cotação completo (construído)
- roles: (nenhum candidate)
- sfx: click-soft (troca de tela), pop (badge), impact-bass-2 (valor bate), typing (linha de procedência)

Scene 1 (0.0–1.3s): tela troca (push-slide left, continuidade da seleção do Frame 2); header "Cotações · Sorriso, MT" com timestamp; card vazio (skeleton) já no lugar, ~70% da largura.
Scene 2 (1.3–3.6s): card preenche: título "Oferta de compra" + "Soja" entra primeiro (stagger curto); no beat do impact-bass-2, valor "R$ 129,50" sobe em count-up (tabular-nums, verde, display grande) com "/sc" fixo ao lado; cidade e distância ("Sorriso, MT · 12 km") entram por baixo.
Scene 3 (3.6–6.5s): badge "comprador verificado" pop (spring-pop, sem overshoot) com ícone de check; linha de procedência "coletado do site do comprador · hoje" entra por último em mono pequeno com keyword glow em "direto na fonte"; um segundo card parcial (Milho R$ 62,80/sc) desliza atrás sugerindo lista; hold até o corte.

## Frame 4 — Carrossel: cidade após cidade

- type: feature_showcase (prova de abrangência via UI, não texto)
- blueprint: device-surface-showcase + oversized-cursor
- scene: Cursor oversized faz swipe rápido no card, trocando por 4 cidades diferentes com preço real cada uma — puro gesto, zero texto de cabeçalho novo
- duration: 4.0s
- transition_in: cut
- status: pending
- src: compositions/frames/04-carrossel.html
- voiceover: none
- asset_candidates:

Frame novo (não existia na versão narrada). É a resposta visual direta ao
pedido "o app fala por mim": em vez de um mapa ou uma frase dizendo "todas as
cidades", o dedo (cursor) literalmente passa o dedo por 4 cidades reais e
cada card muda de valor e de nome — a repetição RÁPIDA é o argumento.

- blueprint: device-surface-showcase (Adapt) + oversized-cursor (Reproduce)
- focal: sequência de 4 cards de cotação (construído)
- roles: (nenhum candidate)
- sfx: click-soft (cada swipe), whoosh-short (transição final pro mapa)

Scene 1 (0.0–0.3s): continuidade do card de Sorriso (fim do Frame 3), cursor oversized já em posição sobre o card.
Scene 2 (0.3–3.4s): 4 swipes rápidos e idênticos em cadência (~0.75s cada): cursor arrasta o card para a esquerda (drag real, não fade), card sai, próximo entra da direita — "Rio Verde, GO · R$ 131,20/sc" → "Cascavel, PR · R$ 127,90/sc" → "Dourados, MS · R$ 130,10/sc" → "Luís Eduardo Magalhães, BA · R$ 128,40/sc"; cada card mantém o mesmo layout do Frame 3 (nome, valor tabular-nums verde, badge verificado pequeno) — só o conteúdo muda, a estrutura é idêntica (repetição = argumento).
Scene 3 (3.4–4.0s): no último card, tudo mais congela e some (fade rápido) deixando só o device na tela, pronto pro corte para o mapa; whoosh-short marca a saída.

## Frame 5 — Cobertura: todas as cidades do Brasil

- type: feature_showcase
- blueprint: compose
- scene: Mapa do Brasil em SVG no escuro; pontos de cidades acendem em cascata (centenas), contador de cidades sobe junto; headline "+ DE 5.000 MUNICÍPIOS"
- duration: 3.6s
- transition_in: crossfade
- status: pending
- src: compositions/frames/05-mapa.html
- voiceover: none
- asset_candidates:

Reaproveita a assinatura do mapa da versão anterior (silhueta do Brasil como
herói, cascata de pontos verdes, count-up de municípios) — já validado
visualmente — mas sem cue de VO: o ritmo agora é auto-timed, mais curto.

- blueprint: compose
- focal: mapa do Brasil em SVG (construído)
- roles: (nenhum candidate)
- sfx: typing (count-up), pop (headline)

Scene 1 (0.0–1.0s): silhueta do Brasil em SVG self-draw (stroke hairline cream sobre canvas escuro), centrada ~60% da largura, terço superior/médio.
Scene 2 (1.0–2.6s): cluster→outward expansion de pontos verdes acendendo em cascata do Centro-Oeste para as bordas (dezenas por segundo); counter mono em value-scaled count-up no canto superior direito ("+ de 5.000 municípios").
Scene 3 (2.6–3.6s): headline "TODAS." entra sozinha abaixo do mapa em spring-pop verde com keyword glow; hold parado (subtle jitter só no glow) até o corte.

## Frame 6 — Contraste: média vs preço que fecha negócio

- type: benefit_highlight
- blueprint: comparison-split
- scene: Split vertical: em cima "ÍNDICE" com faixa borrada R$ 118–142 (cinza); embaixo "COMPRADOR REAL" com R$ 129,50 nítido (verde); badges pop nos dois lados
- duration: 5.0s
- transition_in: crossfade
- status: pending
- src: compositions/frames/06-contraste.html
- voiceover: none
- asset_candidates:

Reaproveita a assinatura da versão anterior (vago vs acionável, split
empilhado no 9:16) sem cue de VO — os dois cards entram em sequência rápida
por beat de SFX, não por fala. É o frame que o produtor manda no grupo do
WhatsApp.

- blueprint: comparison-split (Reproduce, ritmo SFX-only)
- focal: par de cards índice × comprador real (construído)
- roles: (nenhum candidate)
- sfx: whoosh-short (card 1), impact-bass-2 (card 2), pop (badges)

Scene 1 (0.0–1.8s): split-screen vertical (empilhado); card ÍNDICE entra de cima com split-tilt leve: rótulo mono "ÍNDICE REGIONAL", faixa borrada "R$ 118–142", tudo em cinza cream-muted.
Scene 2 (1.8–3.4s): card COMPRADOR REAL entra de baixo em split-tilt espelhado: rótulo "OFERTA DE COMPRADOR", "R$ 129,50/sc" nítido em verde-marca, cidade "Sorriso, MT".
Scene 3 (3.4–5.0s): badges pop na borda interna de cada card ("média" cinza · "preço que fecha negócio" verde); held read absoluto até o corte — frame segurado da direção.

## Frame 7 — CTA: já disponível

- type: cta
- blueprint: logo-assemble-lockup
- scene: Palco limpa, o lockup "Pulso do Campo" se monta ao centro, sub-linha "O preço real do seu grão." e chip "Já disponível no app"
- duration: 4.0s
- transition_in: zoom-through
- status: pending
- src: compositions/frames/07-cta.html
- voiceover: none
- asset_candidates:

Fechamento calmo: a marca se monta, o CTA respira e o frame segura no
lockup final — igual à versão anterior, timing auto-conduzido em vez de
seguir cue de fala.

- blueprint: logo-assemble-lockup (Reproduce, timing auto-conduzido)
- focal: lockup tipográfico "Pulso do Campo" (construído — mesmo wordmark do ícone do Frame 1, fecha o círculo visual)
- roles: (nenhum candidate)
- sfx: riser, impact-bass-1

Scene 1 (0.0–1.4s): palco limpa (canvas escuro vazio); wordmark "Pulso do Campo" monta-se por cascata de palavras ao centro (per-word staggered, settle liso), ponto verde aceso ao lado — mesmo ponto do ícone do Frame 1, fechando o círculo visual do vídeo.
Scene 2 (1.4–2.6s): sub-linha "O preço real do seu grão." em cream-muted entra abaixo, uma linha só; o ponto verde emite UM pulso de anel (SVG ring, self-draw + fade).
Scene 3 (2.6–4.0s): chip mono "JÁ DISPONÍVEL NO APP" surge sob a sub-linha com spring-pop discreto; held read total até o fim (subtle jitter apenas no glow do ponto).
