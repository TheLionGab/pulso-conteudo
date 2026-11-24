"""Monta voz.wav + timeline.json a partir dos trechos da voz oficial (audio/segs/).

Uso: montar.py <pasta_audio> <pasta_saida> [atempo] [roteiro.json]
Mesma lógica de tempo do narracao.py original (Kokoro), trocando só a origem do áudio.
"""
import hashlib, json, os, re, subprocess, sys
import numpy as np
import soundfile as sf
from roteiro import ROTEIRO, parse

A = sys.argv[1]
OUT = sys.argv[2]
# "auto" (padrão): encurta pausas internas e acelera até caber em ALVO s, sem passar de ATEMPO_MAX
ATEMPO_ARG = sys.argv[3] if len(sys.argv) > 3 else "auto"
ALVO, ATEMPO_MAX, PAUSA_MAX = 49.0, 1.25, 0.2  # Pulso Brasil 28–29/10: 35–50 s
CAUDA = 1.0  # segundo extra depois da voz para o acorde final da trilha respirar (dono, 02/11/2026)
VOICE = None
if len(sys.argv) > 4:
    with open(sys.argv[4]) as entrada:
        ROTEIRO = json.load(entrada)
# G2 antes de escrever qualquer saída: fala sem dígito e comparativo com id do dossiê.
EP = os.path.dirname(os.path.abspath(A))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "gates"))
from g2_fala import checar  # noqa: E402
from g_voz import checar as checar_voz  # noqa: E402

checar(ROTEIRO, parse, os.path.join(EP, "dossie.json"))
registro = os.path.join(A, "sintese.json")
if os.path.isfile(registro):
    with open(registro) as entrada:
        sintese = json.load(entrada)
    checar_voz(sintese)
    faltam = [k for k in ("segmentos_sha256", "roteiro_sha256", "segmentos") if k not in sintese]
    if faltam:
        sys.exit(f"sintese.json sem {', '.join(faltam)}: gere a voz pelo audio.voz.")
    from pathlib import Path
    reais = [hashlib.sha256((Path(A) / "segs" / f"seg_{i:03d}.wav").read_bytes()).hexdigest()
             for i in range(len(ROTEIRO))]
    if reais != sintese["segmentos_sha256"]:
        sys.exit("WAVs não correspondem à síntese canônica.")
    atual = hashlib.sha256(json.dumps(ROTEIRO, ensure_ascii=False).encode()).hexdigest()
    if sintese["roteiro_sha256"] != atual or sintese["segmentos"] != len(ROTEIRO):
        sys.exit("Roteiro não corresponde à síntese: montagem cancelada antes de escrever saídas.")
    VOICE = f"{sintese['modelo']}/{sintese['voz']}"
if VOICE is None:
    sys.exit("sintese.json canônico não encontrado.")
SR = 24000
LIGA = {"de", "do", "da", "o", "a", "os", "as", "um", "uma", "por", "em", "na", "no", "e", "que", "com", "se", "é"}


def encurta_pausas(a, sr):
    """Pausa interna maior que PAUSA_MAX vira PAUSA_MAX (o TTS pago arrasta pausas; 27/10: 18 s de 74)."""
    regs = regioes_voz(a, sr, limiar_db=-36)  # -46 dB tratava a respiração do Gemini como voz
    if len(regs) < 2:
        return a
    partes, fim = [a[:int(regs[0][1] * sr)]], regs[0][1]
    for r0, r1 in regs[1:]:
        # corta o meio do silêncio, não as bordas: a -36 dB o ataque fraco ("M" de "Mas") fica fora
        # da região e sumia ("Mas também" virou "Pás também" no G3 do v3, 27/10)
        meia = min(r0 - fim, PAUSA_MAX) / 2
        partes.append(a[int(fim * sr):int((fim + meia) * sr)])
        partes.append(a[int((r0 - meia) * sr):int(r1 * sr)])
        fim = r1
    partes.append(a[int(fim * sr):])
    return np.concatenate(partes)


def bruto(idx):
    a, sr = sf.read(f"{A}/segs/seg_{idx:03d}.wav", dtype="float32")
    return encurta_pausas(a.astype(np.float32), sr), sr


def define_atempo():
    global ATEMPO, SPEED
    if ATEMPO_ARG == "auto":
        total = 0.12
        for i, (_, _, pausa) in enumerate(ROTEIRO):
            a, sr = bruto(i)
            total += len(a) / sr + pausa
        ATEMPO = round(min(ATEMPO_MAX, max(1.0, total / ALVO)), 3)
        print(f"atempo auto: {total:.1f} s com pausas curtas -> x{ATEMPO}")
    else:
        ATEMPO = float(ATEMPO_ARG)
    SPEED = ATEMPO


def carrega(idx):
    a, sr = bruto(idx)
    if ATEMPO != 1.0:
        src = os.path.join(A, f"pn_in_{idx:03d}.wav")
        tmp = os.path.join(A, f"pn_seg_{idx:03d}.wav")
        sf.write(src, a, sr)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", f"atempo={ATEMPO}", "-ar", str(SR), tmp], check=True)
        a, sr = sf.read(tmp, dtype="float32")
    return a, sr


def regioes_voz(a, sr, limiar_db=-46, gap_min=0.12):
    """Regiões com voz (início, fim) em segundos, separadas por silêncios >= gap_min."""
    hop = int(sr * 0.01)
    n = len(a) // hop
    rms = np.array([np.sqrt(np.mean(a[i * hop:(i + 1) * hop] ** 2) + 1e-12) for i in range(n)])
    db = 20 * np.log10(rms / (rms.max() + 1e-12))
    voz = db > limiar_db
    regs, i = [], 0
    while i < n:
        if voz[i]:
            j = i
            while j < n and voz[j]:
                j += 1
            regs.append([i * 0.01, j * 0.01])
            i = j
        else:
            i += 1
    # funde buracos curtos
    out = []
    for r in regs:
        if out and r[0] - out[-1][1] < gap_min:
            out[-1][1] = r[1]
        else:
            out.append(r)
    return out


def tempos_reais(idx, us):
    """Início e fim falados de cada unidade, já no áudio com pausas encurtadas e atempo. None sem alinhamento válido."""
    caminho = os.path.join(A, "alinhamento.json")
    if not os.path.isfile(caminho):
        return None
    with open(caminho) as entrada:
        al = json.load(entrada)[idx]
    fala = " ".join(u["fala"] for u in us)
    if "".join(al["characters"]) != fala:
        print(f"seg {idx}: alinhamento não confere com a fala; tempo estimado")
        return None
    a, sr = sf.read(f"{A}/segs/seg_{idx:03d}.wav", dtype="float32")
    regs = regioes_voz(a.astype(np.float32), sr, limiar_db=-36)  # as mesmas regiões de encurta_pausas
    cortes = []
    for (_, fim), (r0, _) in zip(regs, regs[1:]):
        meia = min(r0 - fim, PAUSA_MAX) / 2
        cortes.append((fim + meia, r0 - meia))

    def mapa(x):
        return (x - sum(max(0.0, min(x, c1) - c0) for c0, c1 in cortes)) / ATEMPO

    tempos, pos = [], 0
    for u in us:
        fim_u = pos + len(u["fala"]) - 1
        tempos.append((mapa(al["character_start_times_seconds"][pos]), mapa(al["character_end_times_seconds"][fim_u])))
        pos = fim_u + 2
    return tempos


def main():
    define_atempo()
    # peso de duração por palavra: letras, com vogal valendo mais (proxy de sílaba)
    fonema = lambda t: len(re.sub(r"[^\wÀ-ÿ]", "", t)) + 0.6 * len(re.findall(r"[aeiouáéíóúâêôãõà]", t.lower()))

    trilha = [np.zeros(int(SR * 0.12), dtype=np.float32)]
    t = 0.12
    palavras, segmentos, cues = [], [], {}
    for idx, (cena, texto, pausa) in enumerate(ROTEIRO):
        us = parse(texto)
        fala = " ".join(u["fala"] for u in us)
        a, sr = carrega(idx)
        assert sr == SR
        a = a.astype(np.float32)
        regs = regioes_voz(a, sr)
        if not regs or not np.any(a):
            sys.exit(f"Segmento {idx:03d} sem voz detectável.")
        ini, fim = regs[0][0], regs[-1][1]
        # 0,07 s antes da voz cortava o "Chi" de Chicago (G3, 27/10)
        a0, a1 = max(0, int((ini - 0.12) * sr)), min(len(a), int((fim + 0.15) * sr))
        a = a[a0:a1]
        regs = [[r0 - a0 / sr, r1 - a0 / sr] for r0, r1 in regs]

        # grupos separados por pontuação interna -> tenta casar com as regiões de voz
        grupos, atual = [], []
        for u in us:
            atual.append(u)
            if re.search(r"[,.:;!?…]$", u["fala"]) and u is not us[-1]:
                grupos.append(atual)
                atual = []
        if atual:
            grupos.append(atual)
        # só confia no casamento grupo↔região se a velocidade de fala de cada grupo for plausível
        # (no 27/10 um estalo curto virou a região do 1º grupo e adiantou o número em 1,5 s)
        ritmo = lambda g, r: (r[1] - r[0]) / sum(max(1, fonema(u["fala"])) for u in g)
        if len(grupos) == len(regs) and all(
                0.4 < ritmo(g, r) / ((regs[-1][1] - regs[0][0]) / sum(max(1, fonema(u["fala"])) for u in us)) < 2.5
                for g, r in zip(grupos, regs)):
            janelas = regs
        else:
            janelas = [[regs[0][0], regs[-1][1]]]
            grupos = [us]
        reais = tempos_reais(idx, us)
        if reais:  # tempo medido pelo provedor vence a estimativa por letras
            trechos = [(u, max(0.0, r0 - a0 / sr), max(0.0, r1 - a0 / sr)) for u, (r0, r1) in zip(us, reais)]
        else:
            trechos = []
            for g, (g0, g1) in zip(grupos, janelas):
                pesos = np.array([max(1, fonema(u["fala"])) for u in g], dtype=float)
                bordas = g0 + (g1 - g0) * np.concatenate([[0], np.cumsum(pesos) / pesos.sum()])
                trechos += zip(g, bordas[:-1], bordas[1:])
        for u, s0, s1 in trechos:
            for c in u["cues"]:
                cues[c if c not in cues else f"{c}_{idx}"] = round(t + s0, 3)
            palavras.append({"d": u["exibe"], "s": round(t + s0, 3), "e": round(t + s1, 3),
                             "hl": u["hl"], "seg": idx})
            for c in u.get("cues_fim", []):
                cues[c] = round(t + s1, 3)
        segmentos.append({"i": idx, "cena": cena, "s": round(t, 3), "e": round(t + len(a) / sr, 3),
                          "texto": " ".join(u["exibe"] for u in us)})
        trilha.append(a)
        trilha.append(np.zeros(int(SR * pausa), dtype=np.float32))
        t += len(a) / sr + pausa

    voz = np.concatenate(trilha)
    voz = voz / (np.abs(voz).max() + 1e-9) * 0.89
    sf.write(f"{OUT}/voz.wav", voz, SR)

    cenas = {}
    for s in segmentos:
        c = cenas.setdefault(s["cena"], {"s": s["s"], "e": s["e"]})
        c["e"] = s["e"]
    nomes = list(cenas)
    for a_, b_ in zip(nomes, nomes[1:]):
        cenas[a_]["e"] = cenas[b_]["s"]
    cenas[nomes[-1]]["e"] = round(t + CAUDA, 3)

    # legendas: até 4 palavras / 24 caracteres, quebra em pontuação e fim de segmento
    legendas, atual = [], []
    for i, p in enumerate(palavras):
        atual.append(p)
        prox = palavras[i + 1] if i + 1 < len(palavras) else None
        chars = sum(len(x["d"]) + 1 for x in atual)
        # não termina legenda em palavra de ligação ("de um por" | "cento"): puxa a próxima junto
        ligacao = p["d"].lower() in LIGA and prox is not None and prox["seg"] == p["seg"]
        fim = (prox is None or prox["seg"] != p["seg"] or re.search(r"[.,:;!?…]$", p["d"])
               or (not ligacao and (len(atual) >= 4 or chars + (len(prox["d"]) if prox else 0) > 24)))
        if fim:
            legendas.append({"s": atual[0]["s"], "e": atual[-1]["e"], "w": [palavras.index(x) for x in atual]})
            atual = []
    for a_, b_ in zip(legendas, legendas[1:]):
        a_["e"] = round(min(b_["s"], a_["e"] + 0.45), 3)
    legendas[-1]["e"] = round(legendas[-1]["e"] + 0.5, 3)

    json.dump({"duracao": round(t + CAUDA, 3), "voz": VOICE, "velocidade": SPEED, "segmentos": segmentos,
               "palavras": palavras, "legendas": legendas, "cues": cues, "cenas": cenas},
              open(f"{OUT}/timeline.json", "w"), ensure_ascii=False, indent=1)
    print(f"duração {t:.1f}s, {len(palavras)} palavras, {len(legendas)} legendas, {len(cues)} cues")
    print({k_: (v["s"], v["e"]) for k_, v in cenas.items()})


if __name__ == "__main__":
    main()
