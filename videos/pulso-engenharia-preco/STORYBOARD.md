---
format: 1080x1920
duration: 25.5s
message: "O motor prefere dizer não sei a inventar um número"
arc: Spread → Vazio de cobertura → Degraus 1-2 → Degrau 3-4 → Degrau 5 → Marca
audience: produtores rurais de MT, e quem julga se o Pulso é sério
voiceover: none — a aritmética na tela é o argumento
music: bed-confident-minimal + SFX nos beats
---

## Por que este reel existe

O promo anterior vende o resultado ("cotação de comprador real"). Este
vende a **engenharia**: por que o número do Pulso merece confiança. É o
conteúdo que converte quem desconfia, não quem já quer comprar.

## Regra de honestidade deste vídeo

**Todo número vem de código, não de copy.** Fonte primária:
`~/Developer/mercado-fisico-mt/worker/ingest/resolver.py`.

- `POLO_ANCHORS` — Rondonópolis soja 141,00 · Porto dos Gaúchos 113,00 ·
  Sinop 129,00 · Campo Novo do Parecis 127,00 · Querência 122,00.
- `DISTANCE_OVERRIDES["Tabaporã"]` — polo Porto dos Gaúchos, frete 4,00,
  retenção 2,00. Daí 113,00 − 4,00 − 2,00 = **107,00**.
- `RESOLUTION_FLAGS` — os cinco degraus, na ordem exata do arquivo.
- Comentário da linha 122 do resolver — o caso C.Vale 113 vs 118.
- 142 municípios e 6 commodities: docstring do módulo e `COMMODITIES`.
  142 × 6 = 852 é aritmética, não estimativa.

O que **não** entrou por não estar no código desta máquina: desconto de
prazo por Selic, robô de WhatsApp lendo 19 compradores, barreira
anti-arbitragem, boletim das 06h35. Tudo isso aparece no notebook
"Improve", mas as fontes citadas lá (`normalizador_prazo.py`,
`intake_balcao.py`, `card_generator.py`, `audio_processor.py`) não
existem em `mercado-fisico-mt`. Ficou de fora até alguém apontar onde
esse código mora. Ver "Reels 2 e 3" abaixo.

## Frames

### 01 — spread · 0.0→4.0s
Duas praças de MT, mesma soja, mesmo dia. Count-up 141,00 e 113,00, e a
diferença de 28,00 chega como terceiro card. Fecha em "1.000 sacas =
R$ 28.000". O gancho é o dinheiro, não a tecnologia.

### 02 — vazio · 3.5→7.6s (crossfade)
Grade de 142 células; poucas acesas. 142 × 6 = 852 preços que precisam
existir todo dia, quase nenhum publicado. Estabelece o problema que a
escada resolve.

### 03 — degraus 1 e 2 · 7.1→12.1s (push-slide)
MEDIANA_PULSO (3+ mesas → mediana) e VERIFICADO (1-2 mesas → a mais
baixa; coop na frente de trading). Fecha com "errar para menos é
decepção, errar para mais é prejuízo".

### 04 — degraus 3 e 4 · 12.1→17.1s (hard cut)
A subtração de Tabaporã aparece linha a linha e o total conta de 113,00 até
107,00 — o espectador vê o frete sair. Depois REFERENCIA_POLO, o degrau
fraco que ainda devolve número.

### 05 — degrau 5 · 16.6→21.5s (crossfade)
Card vazio, tracejado, com um traço no lugar do preço.
SEM_REFERENCIA_LOCAL, "vácuo de liquidez". A tese: o motor prefere dizer
não sei a inventar um número. É o frame que separa o Pulso de um
agregador.

### 06 — marca · 21.0→25.5s (zoom-through)
Os cinco degraus recapitulados, recuam, e o lockup monta.

## Reels 2 e 3 — roteirizados, não produzidos

**Reel 2 · "O preço a prazo que custa dinheiro"** — os R$ 142,00 para 30
dias que valem menos que R$ 141,00 à vista. Bloqueado: a lógica de
desconto por Selic não está no código desta máquina. Antes de produzir,
achar onde `normalizador_prazo.py` mora e usar a fórmula real.

**Reel 3 · "Como o dado entra"** — coleta, validação, resolução,
publicação. Bloqueado pelo mesmo motivo: `intake_balcao.py`,
`validator.py` e `store.py` são fontes do notebook e não estão em
`mercado-fisico-mt`.

Não produzir esses dois com número inventado. O reel 1 vale justamente
porque cada número tem `arquivo:linha`.
