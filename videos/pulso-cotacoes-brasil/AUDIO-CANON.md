# Audio canon — Pulso promo / vídeos HyperFrames

**Provider:** ElevenLabs (`ELEVENLABS_API_KEY` em `~/.config/lion-secrets.env`)  
**Não usar:** Edge TTS / Antonio (proibido no produto agro).

## Voz (TTS)

| Papel | Nome | voice_id | Notas |
|-------|------|----------|-------|
| **Promo agro V2.4 (default)** | **Andrea Lot** | `HOfBIVLhom4mc9WvXfyH` | Shared library — authoritative BR (~67M chars/ano) |
| Promo energético | Rafha | `Lag2bmI1gPov7LCIcc2E` | Intense & Motivational |
| Neutro institucional | Adilson | `A26KfvFuSKaMzhhYkSlQ` | Neutral Male (~7.9M uses) |
| Storyteller owned | Carlos | `NFmEzNOony1UsEJGXLth` | Resonant & Majestic |
| Grave owned | Sergio | `rnJZLKxtlBZt77uIED10` | Deep, Resonant and Clear |
| Canon legado | Guilherme-Mello | `A0vayB3pXPiiEvllfYw5` | V2.3 atual (`vo-01`…`vo-07`) |

**Model:** `eleven_multilingual_v2` · stability 0.52, similarity 0.78, style 0.12, speed 1.06

Previews (sem gastar quota TTS): `assets/vo/previews/*.mp3` via `tools/elevenlabs_download_previews.py`

Fonte auditiva legado: `cooperfibra-boletim-audio-canon-20260904.md`

## Sons de fundo

| Tipo | Provider preferido | Fallback |
|------|-------------------|----------|
| **BGM** | **HeyGen** library (`searchSounds`, type=music) | MusicGen local / bed sintético |
| **SFX** | **HeyGen** library (type=sound_effects) | ElevenLabs sound-generation / Pixabay |
| **VO** | ElevenLabs Guilherme-Mello | — |

Scripts:
- `tools/fetch_heygen_audio_v22.mjs` — BGM + SFX HeyGen (Creator, OAuth)
- `tools/gerar_audio_elevenlabs_v21.py` — SFX/VO ElevenLabs

## Versões

| Render | Áudio |
|--------|-------|
| V2 | Pixabay + bed local |
| V2.1 | ElevenLabs SFX + bed loop (quota Music esgotada) |
| **V2.3** | **HeyGen BGM/SFX + VO Guilherme-Mello** (vo-01..07 remapeado 22s) |
| V2.4 (pendente quota) | HeyGen BGM/SFX + **Andrea Lot** (ou Rafha/Carlos) — `tools/gerar_vo_v23.py andrea-lot` |
