# EXECUTION V2 — Promo Cotações Brasil (22s, fora da curva)

**Owner:** Cursor / Claude Code (sessão ativa)  
**Projeto:** `pulso-cotacoes-brasil`  
**Baseline render:** `renders/pulso-cotacoes-brasil_2026-09-07_22-01-39.mp4` (30,7s — descartar como master)  
**Data lock:** 08/09/2026

---

## 0. Decisões travadas (não reabrir)

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| Duração | **22,0s** (±0,5s) | App Store preview — um argumento, não tour |
| Áudio | **Mudo** + SFX only | STORYBOARD original; VO IA mata o premium |
| UI | **Captura real iPhone 13** | Mock cinza = placeholder; produto é a prova |
| B-roll | Kling frame 01 existente + overlay 0,72 | Já em `assets/broll/frame01-lavoura-amanhecer.mp4` |
| Kling frame 07 | **Fase 2** (crédito) | 16 créditos insuficientes hoje |
| HeyGen avatar | **Proibido** | Política Pulso |
| NotebookLM | **Proibido** | Editorial separado (Aprenda) |
| Números | `mercado-fisico-mt/worker/ingest/scrapers/anchors.py` | arquivo:linha obrigatório |
| Mapa “5.000 municípios” | **Cortado** | Sem lastro honesto no app hoje |
| Watermark Kling | Aceitar ou crop | Não inpaint |

**Mensagem única:** *Preço de mesa, não de tela.*

---

## 1. Arquitetura do filme (4 blocos)

```
| Bloco | Tempo   | Fonte                    | Conteúdo                                      |
|-------|---------|--------------------------|-----------------------------------------------|
| A     | 0–4,0s  | Kling + HyperFrames 01   | Lavoura → ícone → tap → wipe                  |
| B     | 4–10s   | Captura device + HF 02-03| Busca cidade → card soja count-up + badge     |
| C     | 10–16s  | Captura device + HF 04   | Swipe 3 praças (preços reais, mesmo layout)  |
| D     | 16–22s  | HyperFrames 06 + 07      | Contraste índice vs mesa → lockup CTA         |
```

**Frames removidos do master:** 05-mapa (SVG genérico).

---

## 2. Dados na tela (fonte única)

Cidades e preços do swipe — `anchors.py`:

| Cidade | Commodity | Preço | Linha ref |
|--------|-----------|-------|-----------|
| Sorriso | Milho | R$ 43,00/sc | BR163 ~66 |
| Rondonópolis | Soja | R$ 140,00/sc | POLO_SUL ~57 |
| Campo Verde | Soja | R$ 133,50/sc | POLO_SUL ~53 |
| Porto dos Gaúchos | Soja | R$ 113,00/sc | FRONTEIRA ~80 |

Card hero (bloco B): **Campo Verde · Soja · R$ 133,50/sc · Cooperfibra · À vista D+1**

Contraste (bloco D): índice borrado “R$ 118–142” vs mesa “R$ 133,50/sc”.

---

## 3. Fases e gates (ordem obrigatória)

### Fase 1 — DATA GATE
- [ ] Listar 4 cidades acima com `anchors.py:linha`
- [ ] Confirmar que o app QA mostra ofertas equivalentes (device) OU usar captura com overlay HF alinhado aos anchors
- **Veredito:** STATICALLY VERIFIED ou BLOCKED

### Fase 2 — CAPTURE GATE (iPhone 13)
Device: `lion-device verify` → `00008110-0014385E0AB9801E`  
App: `com.pimentinhas.agro.dev` + Metro worktree `video-cotacoes`

| Clip | Ação | Duração alvo | Arquivo |
|------|------|--------------|---------|
| cap-01 | Abrir Cotações, buscar Campo Verde, card visível | 3s | `assets/capture/cap-busca-card.mp4` |
| cap-02 | Swipe/scroll 3 cards (ou 3 buscas rápidas) | 4s | `assets/capture/cap-swipe-pracas.mp4` |

Protocolo:
1. `mac-guardian backup-guard`
2. `check-runner-exclusive.sh` — nenhum runner vivo
3. Gravar com Controle do iPhone **ou** `agent-device record` (sem WDA claim paralelo)
4. Modo escuro, sem notificações, 100% brilho
5. `ffprobe` + frame extraído em `evidence/promo-v2-capture/`

**Veredito:** DEVICE VERIFIED ou BLOCKED

### Fase 3 — COMPOSITION GATE
- [ ] Remover `<audio id="el-vo">` e trilha que briga com mudo
- [ ] `index.html`: duração total 22,0s; recortar frame 05; ajustar `data-start` dos clips
- [ ] Substituir mock UI nos frames 02–04 por `<video>` com captura (mask device)
- [ ] Grain 3% + LUT única (CSS filter ou pós ffmpeg)
- [ ] `npm run check` verde
- [ ] 4 contact sheets (1 por bloco) em `evidence/promo-v2-frames/`

**Veredito:** STATICALLY VERIFIED

### Fase 4 — SOUND GATE
- [ ] BGM bed ≤ 0,35 ou remover
- [ ] SFX nos beats: whoosh (cortes), click (tap), impact-bass (preço), riser (CTA)
- [ ] Assistir sem vídeo — ritmo legível em 10s

**Veredito:** STATICALLY VERIFIED (ouvido)

### Fase 5 — RENDER GATE
```bash
cd videos/pulso-cotacoes-brasil
CHROMIUM_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" npm run render
```
- Se SSD apertar: render em partes (padrão `moega-preco-trava/render-partes.sh`)
- Output: `renders/pulso-cotacoes-brasil_V2_YYYY-MM-DD.mp4`
- `ffprobe` duração + tamanho documentados

**Veredito:** STATICALLY VERIFIED

### Fase 6 — QC MATRIX (antes de entregar)

| # | Teste | Como |
|---|-------|------|
| 1 | Duração 21,5–22,5s | ffprobe |
| 2 | Bloco A: lavoura visível 0–4s | frame @2s |
| 3 | Bloco B: preço legível sem áudio | frame @7s mute |
| 4 | Bloco C: 3 praças distintas | frames @11,13,15s |
| 5 | Bloco D: contraste + CTA | frame @20s |
| 6 | Sem VO / sem música genérica alta | ouvir |
| 7 | Watermark Kling só no bloco A | inspeção visual |
| 8 | Números batem anchors.py | diff manual |

### Fase 7 — ENTREGA
- `renders/pulso-cotacoes-brasil_V2_*-720p.mp4` (segunda passada scale se necessário)
- `BRIEF-V2.md` one-pager
- Append `HANDOFF-ATIVO.md`
- **Não** publicar Instagram/YouTube sem pedido

---

## 4. Anti-erros (o que mata projeto sênior)

1. **Duas direções** — mudo + ElevenLabs no mesmo master  
2. **Inventar número** — qualquer preço fora de anchors.py  
3. **Render integral 22s de uma vez** com SSD cheio — usar partes  
4. **Pular check** — bug z-index vídeo preto já aconteceu (memória 07/09)  
5. **Commitar assets pesados** sem pedido do dono  
6. **Prometer “qualquer cidade”** no copy se captura mostra só MT  

---

## 5. Próximo comando (sessão seguinte)

```bash
# 1. Captura
open -a "QuickTime Player"  # ou agent-device após gates

# 2. Composição
cd ~/.config/lion-dev/worktrees/pulso-do-campo/video-cotacoes/videos/pulso-cotacoes-brasil
npm run check

# 3. Render
CHROMIUM_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" npm run render
```

---

## 6. Estado atual (08/09/2026 21:20)

| Item | Status |
|------|--------|
| Kling b-roll frame 01 | VERIFIED em disco |
| Captura device | NOT VERIFIED |
| index.html V2 (22s, mudo) | NOT VERIFIED |
| Render V2 | NOT VERIFIED |
| iPhone 13 | VERIFIED (`lion-device`) |
| Disco livre | ~217 GB — OK para render |
