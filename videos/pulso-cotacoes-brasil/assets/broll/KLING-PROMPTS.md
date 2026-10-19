# B-roll Kling — frames 01 e 07

Destino: fundo (full-bleed, atrás do palco escuro) dos frames
`01-abertura.html` e `07-cta.html`. Formato 9:16, 5s, sem áudio.

## Restrições que os prompts têm de respeitar

Vêm do STORYBOARD e do frame.md, não são gosto:

- Registro DARK (`ink-black` #05070a). O b-roll é fundo, não assunto:
  entra rebaixado, nunca compete com o ícone nem com o lockup.
- Verde-marca #10b981 é o ÚNICO acento. Amanhecer laranja saturado
  briga com ele. Luz tem de ser rasante, contida, fria nas sombras.
- Centro do quadro fica ocupado: ícone 194px no frame 01, lockup
  tipográfico no frame 07. A composição precisa de centro calmo e
  escuro.
- Zero texto, zero placa, zero logo, zero pessoa. Texto generativo
  sai deformado — já medido em 31/07/2026 nos 3 clipes de teste.
- Movimento contínuo, um único plano, sem corte. Corte dentro do
  b-roll compete com o corte do vídeo.
- Mato Grosso: latossolo vermelho, planalto, céu amplo, soja em
  enchimento de grão.

## Prompt 1 — frame 01 (abertura, "o app acorda")

Energia: despertar. Câmera baixa, entre as linhas.

```
Ultra-low tracking shot gliding forward between two rows of soybean
plants at first light on a Mato Grosso plateau farm, camera 20 cm
above red latosol soil, lens skimming the leaves so they brush past
the frame edges in soft foreground blur. Dew beads on the trifoliate
leaves catch the first rays as thin specular glints. Low ground mist
drifts between the rows. The sun is still below the horizon line:
light is raking and restrained, cool blue-green shadow filling most
of the frame, a narrow warm rim only on the topmost leaves. Deep
shadow occupies the centre of the frame. Slow continuous dolly, no
cut, constant speed, subtle natural parallax between near and far
rows. Cinematic anamorphic look, 35mm, shallow depth of field,
low-key exposure, muted desaturated palette leaning cool green and
near-black, fine film grain. Vertical 9:16 composition, negative
space in the upper two thirds.
```

Negative prompt:

```
text, letters, numbers, watermark, logo, signage, people, farmers,
hands, animals, machinery, tractor, buildings, roads, orange
saturated sunset, golden hour glow, purple blue gradient, lens
flare, bokeh balls, floating particles, fast motion, camera shake,
zoom, cuts, split screen, high key, oversaturated, HDR, cartoon,
illustration, 3d render
```

## Prompt 2 — frame 07 (CTA, "o preço real do seu grão")

Energia: fechamento calmo. Câmera alta, horizonte, respiro.

```
Slow aerial rise over an endless soybean field on a Mato Grosso
plateau at dawn, camera lifting vertically and drifting forward at
a constant speed, revealing the crop rows converging toward a low
flat horizon. Thin layer of ground fog sits in the field furrows.
The sky holds a narrow band of cold pre-sunrise light near the
horizon and fades to deep near-black at the top of the frame. Crop
canopy reads as dark textured green, not lush; red latosol soil
shows faintly between the rows. Light is soft and directional, no
sun disc visible. Single continuous take, no cut, slow constant
motion, gentle atmospheric haze depth. Cinematic wide lens, high
dynamic range compressed to a low-key grade, muted desaturated
palette of deep green and charcoal, fine film grain. Vertical 9:16
composition with a large calm dark area across the middle of the
frame.
```

Negative prompt:

```
text, letters, numbers, watermark, logo, signage, people, animals,
machinery, tractor, silo, buildings, power lines, roads, orange
saturated sunrise, golden hour glow, sun disc, purple blue gradient,
lens flare, bokeh balls, floating particles, fast motion, camera
shake, whip pan, cuts, high key, oversaturated, HDR, cartoon,
illustration, 3d render
```

## Como entram na composição

Camada de fundo, abaixo de tudo, com o preto do palco por cima:

- frame 01: substitui `.a01-bg` (hoje `background: #05070a`) por
  `<video>` em `object-fit: cover` mais um overlay
  `rgba(5,7,10,0.72)`. O ícone continua sendo o elemento mais claro
  do quadro.
- frame 07: mesma camada; overlay um pouco mais forte
  (`0.78`) porque o lockup é tipografia fina e precisa de contraste.

Vídeo entra `muted`, `playsinline`, e o seek é por quadro — o
motor de captura controla o tempo, então o clipe tem de ser mais
longo que o frame (5s > 3,1s do frame 01 e > 4,0s do frame 07).
