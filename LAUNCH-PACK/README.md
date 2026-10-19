# Pulso do Campo — Launch Pack (08/09/2026)

Pacote de vídeos verticais 1080×1920 para lançamento e aquisição.

## Branding aplicado

| Token | Valor | Fonte |
|-------|-------|-------|
| Shell | `#05070a` | `marketing/engine/tokens.css` |
| Primary | `#10b981` | `theme/foundation.ts` |
| Tipografia | Inter 500/700/900 | App + HyperFrames |
| Logo | Gradiente `#6EE7B7` → `#047857` | `LogoPulsoDoCampo.tsx` |

**Honestidade:** sem “Brasil inteiro”, sem Google Play (404), números de `mercado-fisico-mt` onde aplicável.

## Peças

| # | Arquivo | Duração | Uso |
|---|---------|---------|-----|
| 01 | `01-cotacoes-hero_*` | 22s | Hero App Store / Reels / afiliados |
| 02 | `02-engenharia-escada_*` | 25,5s | Credibilidade do motor de preço |
| 03 | `03-engenharia-cvale_*` | 21,7s | Caso C.Vale — mesmo comprador |
| 04 | `04-engenharia-dados_*` | 22,4s | Como o dado entra |
| 05 | `05-diagnostico-praga_*` | 20s | AgroIA diagnóstico |
| 06 | `06-comunidade_*` | 18s | Aba Comunidade (cold start) |

## Áudio

- **Cotações:** HeyGen BGM + SFX + VO Guilherme-Mello (ElevenLabs, clips 07/09)
- **Engenharia reel 1:** José Arnelas VO + BGM orgânica
- **Engenharia reels 2–3:** BGM minimal + SFX
- **Diagnóstico:** VO 4 clipes + SFX (CTA App Store only)
- **Comunidade:** HeyGen bed + SFX (mudo — premium visual)

## Render

```bash
export CHROMIUM_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
# Ver scripts em ../videos/*/package.json
```

## Bloqueios conhecidos

- ElevenLabs TTS quota esgotada → VO premium Andrea Lot pendente
- Captura device real na promo Cotações → mock UI com dados reais
- `pulso-android-lancamento` — **não publicar** (Play 404)
