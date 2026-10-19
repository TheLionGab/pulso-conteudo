# Carrossel — janela de pulverização

Pilar **"Como se calcula"** (ver `docs/PLANO-FUNIL.md`, seção 1). Trabalho da peça:
**salvamento**, não curtida. Se em 3 peças deste pilar o salvamento não subir, o pilar cai.

Formato: 7 slides, 1080×1350 (4:5). `out/slide-1.png` … `out/slide-7.png`.

## Por que esta peça existe

O app calcula a janela de pulverização com pesos explícitos em
`apps/meu-talhao/lib/operationWindow.ts`. Isso é conteúdo que **só quem tem o produto consegue
publicar** — não é dica genérica de internet, é a régua real, com o número que ela produz.

O gancho é uma comparação contraintuitiva, e os dois lados foram conferidos executando a função:

| Cenário (os outros dois fatores perfeitos) | Nota | Status |
| ------------------------------------------ | ---- | ------ |
| Vento no limiar — 10 km/h | **55** | Atenção |
| Temperatura no limiar — 30 °C | **75** | Aberta |
| Umidade no limiar — 55% | **70** | Aberta (no corte) |

Mesmo "no limite", resultados opostos. Isso é a peça inteira.

## Integridade dos números

Todo número saiu de executar o código, não de estimativa. Reproduzir:

```bash
cd apps/meu-talhao
node --experimental-strip-types -e "
import('./lib/operationWindow.ts').then((m) =>
  console.log(m.evaluateOperationWindows({ temperatura: 20, umidade: 80, vento: 10, probabilidadeChuva: 0 })))"
```

**Se `operationWindow.ts` mudar peso ou limiar, esta peça vira desinformação.** Re-executar e
re-renderizar antes de republicar. O arquivo está na lista de `coverage.include` do
`vitest.config.ts`, então mudança ali passa por teste — mas o teste não sabe que existe um
carrossel publicado dependendo dos mesmos valores.

## Duas ressalvas que ficam na arte

Ambas no slide 7, não em letra miúda:

- **Os limiares são calibrados para Mato Grosso.** Está escrito no cabeçalho de
  `operationWindow.ts` ("Limiares agronômicos para a região de MT"). Publicar como se fosse
  régua nacional seria overclaim.
- **Recomendação agronômica é do técnico.** O app organiza sinal; não assina decisão. Mesma
  postura do aviso da ficha na loja (`store-assets/play/metadata/pt-BR/full_description.txt`).

## Legenda

> Vento de 10 km/h e temperatura de 30 °C estão os dois no limite. Só um tira sua janela de
> pulverização do verde.
>
> No cálculo do Pulso do Campo o vento pesa 45%, a umidade 30% e a temperatura 25%. Por isso o
> vento no limiar derruba a nota para 55 (atenção) enquanto a temperatura no limiar ainda deixa
> 75 (aberta).
>
> Arrasta pra ver a conta dos três fatores. Limiares calibrados para MT.
>
> #pulverizacao #agro #matogrosso #sojabrasil #agronomia

Cinco hashtags, todas de assunto. Sem `#agro2026`, sem `#instaagro`, sem bloco de trinta — não
adianta alcance de quem não pulveriza.

**Primeiro comentário** (não na legenda, para não competir com o gancho):

> A janela também depende de plantio e colheita, que têm pesos próprios. Se quiser que eu abra
> essas duas contas, comenta aí.

Isso é uma sonda de próxima peça, não enfeite: se ninguém pedir, o pilar não vira série.

## Antes de publicar

1. Marcar o link da bio com `campaign_id` / `creator_id` — o app já atribui compra a campanha
   (`lib/paywall.ts:226`), e link sem marcação joga essa atribuição fora de forma irrecuperável.
   Ver `docs/PLANO-FUNIL.md`, passo 3.
2. Subir os 7 PNGs **na ordem**. Carrossel fora de ordem quebra a narrativa do gancho.
3. Não recortar: a arte já é 4:5, a proporção que o Instagram entrega inteira no feed.

## Regenerar

```bash
node marketing/pieces/2026-08-20-janela-pulverizacao/render.mjs
```

`assertFits()` derruba o render se um slide transbordar o quadro ou se o navegador quebrar uma
linha do título por conta própria. Num carrossel isso importa mais que numa peça única: só um
dos sete quebra, e é o que passa despercebido na revisão.
