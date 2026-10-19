---
workflow: general-video
flow: companion
storyboard: no
message: "Tira a foto. A resposta vem em segundos — com fonte, não achismo."
destination: reels-stories
aspect: 1080x1920
language: pt-BR
audience: produtores rurais brasileiros, usuários e leads do Pulso do Campo
length: 20s
angle: feature-reveal-diagnostico
---

## Intent

Peça 4 do calendário da semana. Mostra a feature de diagnóstico de praga/doença
por foto do Pulso do Campo: o produtor fotografa a folha, a IA identifica e
devolve um plano de manejo com fonte citável (Embrapa/base de conhecimento) —
nunca dose ou marca comercial, sempre com disclaimer de confirmar com
agrônomo. Mock-UI com o design system real do app, sem captura de site.

## Assets

- Fonte de verdade do contrato de dados:
  `~/Developer/Pulso-Do-Campo/apps/meu-talhao/lib/diagnosePest.ts`.
- Exemplo usado (citado no próprio código como caso real): "Ferrugem asiática
  da soja" — fonte "Embrapa", cultura soja, severidade média/alta.
- Mesma paleta/tipografia dos vídeos irmãos.

## Regra de honestidade

**Recomendação é sempre classe de manejo, nunca marca comercial nem dose** —
o próprio `Diagnosis.recomendacao`/`defensivos` do código proíbe isso. O card
final leva o disclaimer ("confirme com agrônomo, produto registrado MAPA").
Não inventar % de confiança específico do produto real — usar um valor
plausível (ex. 92%) rotulado como exemplo ilustrativo do fluxo, não uma
medição real.

## Beats (20s)

1. 0.0–4.0s — produtor aponta câmera pra folha, foto é tirada (app real, mock-UI).
2. 4.0–9.0s — tela de "analisando", scan visual sobre a foto.
3. 9.0–16.0s — card de resultado: "Ferrugem asiática da soja", confiança 92%,
   severidade, recomendação de manejo (classe, não marca), fonte "Embrapa".
4. 16.0–20.0s — CTA: "Pulso do Campo. Já na App Store e no Google Play."

## Locução (mesma voz Guilherme-Mello, ElevenLabs)

1. "Tira uma foto da folha."
2. "A IA analisa na hora."
3. "Resposta com fonte — não achismo. E sempre com aviso: confirme com seu agrônomo."
4. "Pulso do Campo. Já na App Store e no Google Play."
