# Prompt Kling — plano de fundo do story (opcional)

Escopo: gerar **só o fundo em movimento**, para substituir o gradiente de
`src/story.html`. O texto e a marca continuam vindo do HTML, sobrepostos depois. Modelo de
vídeo generativo erra letra e erra logo — não peça o título para ele.

> **Não foi executado nesta sessão.** Não há credencial de Kling no ambiente e o proxy de
> egress bloqueia `app.klingai.com`, então nem a referência da API foi possível conferir.
> Os campos abaixo são os da interface web (text-to-video), que não dependem disso.

## Configuração

| Campo | Valor |
| ----- | ----- |
| Modo | Text to Video |
| Proporção | 9:16 |
| Duração | 5s (10s se for repetir a sequência inteira) |
| Movimento da câmera | fixo / estático |

## Prompt

```
Aerial drone shot at golden hour over a Brazilian cerrado soybean field, perfectly
straight crop rows converging toward the horizon, thin ground mist drifting between the
rows, deep dark green foliage, very dark underexposed scene lit only by low warm rim
light on the leaf tops, slow steady descent, no camera shake, cinematic, shallow depth of
field, 9:16 vertical framing with the upper two thirds nearly empty dark sky
```

O "upper two thirds nearly empty dark sky" não é enfeite: é o espaço onde o título e a
caixinha de perguntas caem. Fundo movimentado no meio do quadro compete com o texto e
perde.

## Negative prompt

```
text, letters, words, watermark, logo, signature, people, faces, hands, machinery,
tractor, oversaturated colors, orange sky, lens flare, fast camera movement, zoom,
distorted rows, warped horizon
```

## Depois de gerar

1. Salvar o MP4 em `src/bg-kling.mp4`.
2. No `story.html`, trocar `.bg`/`.glow` por um `<video>` cobrindo o palco, mantendo por
   cima um `linear-gradient(180deg, rgba(5,7,10,0.55), rgba(5,7,10,0.9))` — sem essa
   camada o texto branco não sustenta contraste sobre imagem real.
3. `render.mjs` captura vídeo dentro da página só se o quadro for avançado
   explicitamente (`video.currentTime = t/1000`); o congelamento por `--t` não alcança
   elemento `<video>`. Ajustar antes de rodar, senão os 180 quadros saem idênticos.
