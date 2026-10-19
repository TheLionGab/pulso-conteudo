# Reels — o fator que fecha a janela

Par do carrossel `2026-08-20-janela-pulverizacao`, mesmo pilar ("Como se calcula") e mesmos
números. Trabalho da peça: **alcance**. O carrossel é o que fica salvo; o Reels é o que traz
gente nova.

`out/reels-vento.mp4` — 18,2 s · 1080×1920 · H.264 High · yuv420p · 30 fps · sem áudio ·
faststart · 546 quadros. `out/capa.png` é o quadro de capa em PNG.

## Roteiro (5 cenas)

| Início | Cena | O que aparece |
| ------ | ---- | ------------- |
| 0,0 s | Gancho | Vento 10 km/h e 30 °C estão os dois no limite — só um tira do verde |
| 4,2 s | Os pesos | Barras: vento 45% · umidade 30% · temperatura 25% |
| 8,2 s | Vento no limiar | **55 · atenção** |
| 12,2 s | Temperatura no limiar | **75 · aberta** |
| 16,2 s | Fecho | "Olhe o vento primeiro" + as duas ressalvas |

O gancho inteiro cabe nos primeiros 4 s — é o que decide se o Reels é assistido. As duas
ressalvas (limiares de MT, recomendação é do técnico) ficam na arte, não na legenda.

## Sem áudio, de propósito

O MP4 não tem faixa de áudio, e o `validateMp4()` reprova se aparecer uma. Escolha:

- Muito Reels do agro é assistido no mudo, e o vídeo é legível sem som.
- Trilha entra no próprio Instagram, com áudio da biblioteca dele — que é o que o algoritmo
  distribui. Áudio embutido aqui não ganharia isso e ainda arriscaria direito autoral.

## Números

Idênticos aos do carrossel, pela mesma fonte: executar
`apps/meu-talhao/lib/operationWindow.ts`. O comando está no README do carrossel. **Peso ou
limiar que mude ali invalida as duas peças ao mesmo tempo** — re-executar e re-renderizar as
duas antes de republicar qualquer uma.

## Legenda

> O vento pesa 45% no cálculo da janela de pulverização. A temperatura, 25%.
>
> Por isso vento no limiar (10 km/h) derruba a nota para 55 — atenção — enquanto temperatura no
> limiar (30 °C) ainda deixa 75, aberta. Mesmo "no limite", resultados opostos.
>
> Limiares calibrados para MT.
>
> #pulverizacao #agro #matogrosso #agronomia

## Antes de publicar

1. Link da bio marcado com `campaign_id` / `creator_id` (ver `docs/PLANO-FUNIL.md`, passo 3).
2. Publicar o Reels **antes** do carrossel, com alguns dias de intervalo: o Reels traz gente
   nova, o carrossel converte quem já chegou. Ordem inversa desperdiça o alcance.
3. Escolher a capa no Instagram apontando para o gancho (≈2 s) ou subir `capa.png`.

## Regenerar

```bash
node marketing/pieces/2026-08-20-reels-vento/render.mjs
```

Dois gates antes de qualquer arquivo sair: `assertScenesFit()` reprova cena mais alta que a safe
area do Reels ou elemento vazando à direita (onde fica a coluna de ações do app), e
`validateMp4()` decodifica o arquivo inteiro conferindo codec, pix_fmt, dimensão, fps, ausência
de áudio, contagem de quadros e faststart.
