---
workflow: product-launch-video
flow: automation
storyboard: no
message: "Cotação de comprador real, na sua cidade — em qualquer cidade do Brasil"
destination: reels-whatsapp
aspect: 1080x1920
language: pt-BR
audience: produtores rurais brasileiros (soja/milho/boi), usuários e leads do Pulso do Campo
length: 30.7s
angle: silent-app-showcase
---

## Intent

Anúncio de "novidade MÁXIMA" do app Pulso do Campo: a aba de Cotações passa a
cobrir **todas as cidades do Brasil**, com preços de **compradores reais** —
ofertas de compra efetivamente publicadas por compradores e coletadas dos
sites — em vez de índices regionais de alta variância (tipo IMEA), que nunca
batem com o preço que o produtor recebe na porteira. Tom: energia de
lançamento, direto, orgulho de produto, zero corporativês. É promo (sell),
não tour: sem captura de site; as telas do app são mock-UI construída com o
design system real do produto.

## Assets

- Sem material fornecido pelo usuário. Cores/tipografia vêm do design system
  do repo (`apps/meu-talhao/theme/foundation.ts`): primária #10b981,
  secundária #16A34A, neutros stone (#1C1917 escuro), accent #3B82F6,
  warning #F59E0B. Tema escuro é a cara do app.

## Customizations

- Count-up/rolagem de preços nos valores de cotação (R$/saca).
- Mapa do Brasil animado com pontos de cidades acendendo (cobertura nacional).
- Contraste visual "índice com variância alta" vs "oferta de comprador real".
- Carrossel de UI real (não texto) provando cobertura nacional cidade a cidade.
- SEM narração — SFX rítmico + motion carregam o ritmo; sem trilha melódica
  (BGM segue indisponível offline, e agora nem faz falta).

## Notes — pivot (26/08): vídeo mudo, app-first

Pedido do usuário: "design típico de App que vai vender muito só com esse
vídeo. Onde eu nem preciso falar — o próprio app e o vídeo fala por mim."
Isso substitui o brief original de "feature-reveal narrado" por um **app
showcase silencioso, estilo preview de App Store**: sem voiceover em nenhum
frame, sem blocos de tipografia falada — o produto (mock-UI do app) é o
protagonista em quase todos os frames; texto em tela é mínimo e funcional
(rótulo de UI, não legenda de fala). Motion + SFX + cortes é que vendem.

- Nome do app na tela: "Pulso do Campo".
- Não inventar números absurdos: usar valores plausíveis de soja/milho
  (ex.: soja R$ 129,50/sc, milho R$ 62,80/sc) e nomes reais de cidades
  (Sorriso-MT, Rio Verde-GO, Cascavel-PR, Dourados-MS, Luís Eduardo
  Magalhães-BA…).
- Não prometer data de lançamento nem preço do app; CTA genérico
  ("Já disponível no Pulso do Campo").
- Modo autônomo: usuário pediu para gerar — render aprovado de antemão.
