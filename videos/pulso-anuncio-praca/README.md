# Anúncio "Preço da sua praça"

Vídeo 9:16 de 20 s para Reels, Stories e Google App Campaign. Cada cidade recebe o seu vídeo,
feito com o preço real do IMEA do dia. Funciona sem som: o texto carrega a mensagem.

## Roteiro (20 s)

| Tempo | Cena | O que aparece |
|---|---|---|
| 0–3,6 s | Gancho | "Quanto vale a sua soja hoje?" + preço da cidade. O preço real já está no quadro 0 (miniatura). |
| 3,6–8,2 s | Ranking | 6 praças: topo 3, a cidade do anúncio ("← você") e as 2 mais baixas. |
| 8,2–11,9 s | Dinheiro | Diferença por saca e o total em 10 mil sacas. Aviso: "antes do frete". |
| 11,7–15,8 s | App | Celular com a tela real de cotações do app e 3 benefícios. |
| 15,8–20 s | CTA | Fecho da loja (`--loja ios` ou `android`), fonte e data dos preços. |

## Como gerar

```bash
cd videos/pulso-anuncio-praca
python3 -m unittest test_gerar
python3 gerar.py --dados dados/imea-2026-11-19.json --produto soja --cidade Sorriso --loja ios --render
bash rodar-diario.sh            # todas as cidades, soja e milho, iPhone e Android, dados do dia
```

- `--baixar` lê `SUPABASE_URL` e `SUPABASE_ANON_KEY` (chave pública do app; ver `.env.example`)
  e faz só GET em `cotacoes.precos`, indicador principal (preço disponível de compra).
- Os dados baixados ficam em `dados/imea-AAAA-MM-DD.json`: o vídeo pode ser refeito igual depois.
- Saída: `out/<produto>-<cidade>-<loja>-<data>.mp4` (fora do Git). Cerca de 1 min por vídeo.
- Um vídeo por loja: o anúncio do iPhone roda só para iOS e o do Android só para Android.
- `index.html` é gerado; edite `molde/template.html`.
- Render: HyperFrames 0.9.86 (`npm run check` antes de mudar o molde).

## Regras de texto (não quebrar)

- Todo número na tela vem do JSON do dia. Nada de preço inventado nem contagem a partir de número falso.
- A diferença entre praças é sempre marcada como "antes do frete".
- "14 dias grátis" só no vídeo do iPhone: plano anual, 6 trials de 14 dias medidos em produção
  até 04/11/2026. No Android nenhum trial foi registrado até 24/11/2026, então o vídeo diz
  "Baixe grátis" e não promete teste. Mudou a oferta? Mude `FECHO_POR_LOJA` em `gerar.py`.
- O celular da cena 4 mostra a tela real de cotações (`assets/device/cotacoes.png`, captura de
  30/09/2026, Alta Floresta), não uma tela de outro recurso. É a única exceção à regra do JSON:
  os números dela são os da captura, com praça e data visíveis na própria tela.
