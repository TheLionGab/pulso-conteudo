# Pulso do Campo — Vídeos Institucionais (FINAL)

**Owner:** pipeline HyperFrames · worktree `video-cotacoes`  
**Data:** 08/09/2026  
**Veredito:** VERIFIED (renders + device capture iPhone 13)

---

## Pacote entregue

Pasta canônica: **`INSTITUCIONAL/vertical/`**

| Arquivo | Duração | Uso institucional |
|---------|---------|-------------------|
| `01-hero-device-21s.mp4` | 21s | **MASTER** — 3 telas reais iPhone + CTA |
| `02-cotacoes-22s.mp4` | 22s | App Store preview · Reels · afiliados |
| `03-engenharia-escada-25s.mp4` | 25,5s | Credibilidade motor de preço |
| `04-engenharia-cvale-22s.mp4` | 21,7s | Caso C.Vale — mesmo comprador |
| `05-engenharia-dados-22s.mp4` | 22,4s | Como o dado entra no Pulso |
| `06-diagnostico-20s.mp4` | 20s | AgroIA diagnóstico + **VO HeyGen** |
| `07-comunidade-18s.mp4` | 18s | Comunidade cold-start |

App Store: `INSTITUCIONAL/app-store/preview-21s.mp4` (corte do hero)

---

## Ferramentas usadas

| Ferramenta | Papel |
|------------|-------|
| **HyperFrames 0.8.12** | Render HTML → MP4 (pipeline principal) |
| **iPhone 13 + agent-device** | Capturas reais integradas no hero |
| **HeyGen** | BGM (Astral bed) + SFX library + VO diagnóstico |
| **ElevenLabs** | VO cotações (Guilherme-Mello, clips 07/09) · SFX |
| **ffmpeg** | Empacote, QC frames, App Store cut |
| **CapCut** | *Opcional pós* — importar masters de `INSTITUCIONAL/vertical/` para legendas finais ou ajuste de ritmo |

> ElevenLabs TTS novo: **BLOCKED** (quota 12 chars). Andrea Lot pendente recarga.

---

## Branding

- Shell `#05070a` · Primary `#10b981` · Inter
- CTA por peça: **App Store only** (chip variado — sem Google Play, sem “entrar no Pulso” no vídeo)
- Sem Google Play (gate Play 404)
- Sem “Brasil inteiro” — honestidade MT/142 municípios

---

## Evidência device

`~/.config/lion-dev/evidence/pulso-launch-device-20260908/`
- Cotações Campo Verde · Soja R$ 141,40
- Diagnóstico AgroIA
- Comunidade feed real

---

## Re-render

```bash
export CHROMIUM_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
cd ~/.config/lion-dev/worktrees/pulso-do-campo/video-cotacoes
./tools/export-institucional.sh
```

Projetos fonte: `videos/pulso-*`

---

## Fora de escopo (não publicar)

- `pulso-android-lancamento` — Play 404
- Peças Cooperfibra / NM — outro produto

---

## Próximo (só se pedir)

- VO Andrea Lot (ElevenLabs) após recarga
- Captura device swipe carrossel cotações (substituir mock frames 02–04)
- Versão 16:9 pitch B2B (`lion-videos/arquitetura-preco-pulso`)
