"""Trilha e efeitos do Pulso Brasil, a partir do acervo versionado (assets/manifest.json).

A música vem de config/trilha.json ("musica": chave do manifesto). Os efeitos seguem a timeline:
riser na abertura, whoosh em cada troca de cena, tick nos números em destaque e sting no fecho.
Não chama API: os sons foram gerados uma vez (assets/sons_elevenlabs.py) e conferidos por sha256.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

from assets.integridade import caminhos

CONFIG = json.loads((Path(__file__).resolve().parents[1] / "config/trilha.json").read_text())
# Nível RMS de cada efeito antes do mix (o mix.sh ainda aplica volume 0,5 na pista de efeitos).
NIVEL = {"riser_abertura": 0.10, "whoosh_transicao": 0.07, "tick_numero": 0.05, "sting_logo": 0.10}
TICK_INTERVALO = 1.2  # s mínimos entre dois ticks, para não virar metralhadora


def ler(arquivo, sr):
    x, sr_x = sf.read(arquivo, dtype="float32", always_2d=True)
    if sr_x != sr:
        raise ValueError(f"{arquivo.name}: {sr_x} Hz, esperado {sr} Hz")
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    return x[:, :2]


def musica(origem, n, sr):
    x = ler(origem, sr)
    if len(x) < 2:
        raise ValueError(f"{origem.name}: faixa com menos de 2 amostras")  # o laço abaixo não cresceria
    if len(x) < n:
        # Repete a abertura com crossfade, sem trocar de faixa.
        sobreposicao = min(round(sr * 1.2), len(x) // 2)
        rampa = np.linspace(0, 1, sobreposicao)[:, None]
        while len(x) < n:
            x = np.concatenate((x[:-sobreposicao], x[-sobreposicao:] * (1 - rampa)
                                + x[:sobreposicao] * rampa, x[sobreposicao:]))
    y = x[:n].copy()
    fade = min(round(sr * .25), n)
    y[:fade] *= np.linspace(.35, 1, fade)[:, None]
    fade = min(round(sr * 1.2), n)
    y[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return y * (0.085 / (np.sqrt(np.mean(y * y)) + 1e-9))


def marcas(tl):
    """Lista (efeito, instante em s, alinhamento) a partir da timeline."""
    cenas = sorted(tl["cenas"].items(), key=lambda c: c[1]["s"])
    saida = [("riser_abertura", 0.0, "inicio")]
    for nome, c in cenas[1:]:
        if nome == "fecho":
            saida.append(("sting_logo", c["s"], "inicio"))
        else:
            saida.append(("whoosh_transicao", c["s"], "meio"))
    ultimo = -TICK_INTERVALO
    anterior_hl = False
    for p in tl["palavras"]:
        if p["hl"] and not anterior_hl and p["s"] - ultimo >= TICK_INTERVALO:
            saida.append(("tick_numero", p["s"], "inicio"))
            ultimo = p["s"]
        anterior_hl = p["hl"]
    return saida


def efeitos(arquivos, tl, n, sr):
    pista = np.zeros((n, 2), dtype=np.float32)
    usados = []
    for nome, t, alinhamento in marcas(tl):
        x = ler(arquivos[nome], sr)
        x = x * (NIVEL[nome] / (np.sqrt(np.mean(x * x)) + 1e-9))
        inicio = round(t * sr) - (len(x) // 2 if alinhamento == "meio" else 0)
        if inicio >= n:
            continue  # marca depois do fim: n - inicio negativo viraria fatia do fim do efeito
        corte = max(0, -inicio)
        inicio = max(0, inicio)
        trecho = x[corte:corte + n - inicio]
        if len(trecho) == 0:
            continue
        fade = min(round(sr * .05), len(trecho))
        trecho = trecho.copy()
        trecho[-fade:] *= np.linspace(1, 0, fade)[:, None]
        pista[inicio:inicio + len(trecho)] += trecho
        usados.append({"efeito": nome, "s": round(inicio / sr, 3)})
    pico = np.abs(pista).max()
    if pico > 0.89:
        pista *= 0.89 / pico
    return pista, usados


def main(p):
    tl = json.loads((p / "timeline.json").read_text())
    arquivos = caminhos(p)
    chave = os.environ.get("PULSO_TRILHA") or CONFIG["musica"]  # PULSO_TRILHA: prévia de outra faixa
    if chave not in arquivos:
        raise ValueError(f"config/trilha.json: música {chave!r} fora do assets/manifest.json")
    sr = sf.info(arquivos[chave]).samplerate
    n = round(tl["duracao"] * sr)
    sf.write(p / "musica.wav", musica(arquivos[chave], n, sr), sr)
    if CONFIG.get("efeitos"):
        pista, usados = efeitos(arquivos, tl, n, sr)
    else:
        pista, usados = np.zeros((n, 2), dtype=np.float32), []
    sf.write(p / "efeitos.wav", pista, sr)
    (p / "trilha-proveniencia.json").write_text(json.dumps(
        {"musica": chave, "origem": str(arquivos[chave].relative_to(p)), "duracao_s": tl["duracao"],
         "normalizacao_rms": 0.085, "efeitos": usados}, ensure_ascii=False, indent=2))
    print(f"Trilha {chave}; {len(usados)} efeitos: "
          + ", ".join(f"{u['efeito'].split('_')[0]}@{u['s']}" for u in usados))


if __name__ == "__main__":
    try:
        main(Path(sys.argv[1]))
    except (ValueError, KeyError, OSError) as erro:
        sys.exit(f"Trilha: {erro}")
