"""G3 (ASR): transcreve cada segmento da voz com Whisper local (sherpa-onnx) e compara com a fala.

Uso: <python com sherpa_onnx> g3_asr.py <pasta_episodio> <pasta_modelos> [teto_wer] [--so-cru]
Números não entram no WER (ver NUMERAIS). Não está no montar-e-renderizar.sh: roda depois da
voz final, no venv que tem sherpa_onnx (pulso-news-2026-10-14/venv).
<pasta_modelos> contém sherpa-onnx-whisper-base/ (já baixado; este script não baixa nada).
WER por segmento, em palavras normalizadas (minúsculas, sem acento e sem pontuação), em duas
escutas: o trecho cru (audio/segs) e, sem --so-cru, o trecho como vai ao ar (video/public/voz.wav,
com pausas encurtadas e atempo do montar.py; a timeline tem de ser da mesma voz do sintese.json).
Reprova (código 1) se algum segmento passar do teto (padrão 0,35) em qualquer escuta. Grava
audio/asr.json com o resultado e a lista "reprovados" (o gerar_voz_gemini.sh regera só esses).
O teto mede "a voz leu outra coisa", não sotaque: Whisper base erra nome próprio sozinho.
"""
import json, os, sys, unicodedata

import numpy as np
import sherpa_onnx
import soundfile as sf

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
SO_CRU = "--so-cru" in sys.argv
EP, MOD = os.path.abspath(ARGS[0]), os.path.abspath(ARGS[1])
TETO = float(ARGS[2]) if len(ARGS) > 2 else 0.35
sys.path.insert(0, os.path.join(EP, "audio"))
from roteiro import ROTEIRO, parse  # noqa: E402

M = os.path.join(MOD, "sherpa-onnx-whisper-base")
rec = sherpa_onnx.OfflineRecognizer.from_whisper(
    encoder=f"{M}/base-encoder.onnx", decoder=f"{M}/base-decoder.onnx", tokens=f"{M}/base-tokens.txt",
    language="pt", num_threads=4)


# Números saem dos dois lados: o Whisper escreve "16" onde a fala diz "dezesseis", e o valor de cada
# número já é conferido por G1 (fonte) e G2 (fala sem dígito). Aqui só as outras palavras contam.
NUMERAIS = set("""zero um uma dois duas tres quatro cinco seis sete oito nove dez onze doze treze
catorze quatorze quinze dezesseis dezessete dezoito dezenove vinte trinta quarenta cinquenta sessenta
setenta oitenta noventa cem cento duzentos trezentos quatrocentos quinhentos seiscentos setecentos
oitocentos novecentos mil milhao milhoes virgula meio e por""".split())


def palavras(t):
    t = unicodedata.normalize("NFKD", t.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return [w for w in "".join(c if c.isalnum() else " " for c in t).split()
            if w not in NUMERAIS and not any(c.isdigit() for c in w)]


def wer(ref, hip):
    d = list(range(len(hip) + 1))
    for i, r in enumerate(ref, 1):
        ant, d[0] = d[0], i
        for j, h in enumerate(hip, 1):
            ant, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, ant + (r != h))
    return d[-1] / max(1, len(ref))


def ouve(a, sr):
    if a.ndim > 1:
        a = a.mean(1)
    n = int(len(a) * 16000 / sr)
    x = np.interp(np.linspace(0, len(a) - 1, n), np.arange(len(a)), a).astype(np.float32)
    st = rec.create_stream()
    st.accept_waveform(16000, x)
    rec.decode_stream(st)
    return st.result.text.strip()


sintese = json.load(open(os.path.join(EP, "audio", "sintese.json")))
falas = [" ".join(u["fala"] for u in parse(texto)) for _, texto, _ in ROTEIRO]
escutas = [("cru", [sf.read(os.path.join(EP, "audio", "segs", f"seg_{i:03d}.wav"), dtype="float32") for i in range(len(ROTEIRO))])]
if not SO_CRU:
    tl = json.load(open(os.path.join(EP, "video", "public", "timeline.json")))
    if tl.get("voz") != f"{sintese['modelo']}/{sintese['voz']}":
        sys.exit(f"G3 reprovado: timeline montada com {tl.get('voz')}, síntese é {sintese['modelo']}/{sintese['voz']}; rode o montar-e-renderizar.sh")
    v, vsr = sf.read(os.path.join(EP, "video", "public", "voz.wav"), dtype="float32")
    escutas.append((f"ar x{tl.get('velocidade')}", [(v[int(s["s"] * vsr):int(s["e"] * vsr)], vsr) for s in tl["segmentos"]]))

res, ruins = [], set()
for nome, trechos in escutas:
    for i, (a, sr) in enumerate(trechos):
        ouvido = ouve(a, sr)
        w = round(wer(palavras(falas[i]), palavras(ouvido)), 3)
        res.append({"seg": i, "escuta": nome, "wer": w, "fala": falas[i], "ouvido": ouvido})
        marca = "FALHA" if w > TETO else "ok   "
        print(f"{marca} {nome:>8} seg {i:03d} WER {w:.2f} | {ouvido[:64]}")
        if w > TETO:
            ruins.add(i)

json.dump({"voz": sintese.get("voz"), "modelo_asr": "sherpa-onnx-whisper-base", "teto_wer": TETO,
           "reprovados": sorted(ruins), "segmentos": res},
          open(os.path.join(EP, "audio", "asr.json"), "w"), ensure_ascii=False, indent=1)
media = sum(r["wer"] for r in res) / len(res)
if ruins:
    sys.exit(f"G3 reprovado: segmentos {sorted(ruins)} acima de WER {TETO} (média {media:.2f}); regerar só esses")
print(f"G3 aprovado: {len(ROTEIRO)} segmentos em {len(escutas)} escuta(s), WER médio {media:.2f}, máximo {max(r['wer'] for r in res):.2f}")
