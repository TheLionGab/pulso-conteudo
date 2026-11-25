"""Nova tentativa do G3: invalida o cache da voz só dos segmentos que o G3 reprovou.

Uso: python3 -m audio.regerar <episodio.json> <audio/asr.json> <pasta_cache_voz>
Lê "reprovados" do asr.json que o g3_asr.py gravou nesta execução, apaga do cache SÓ o WAV desses
segmentos e imprime os índices. O pulso-brasil.sh roda a voz de novo (que sintetiza apenas o que falta no
cache, sob o teto PULSO_ELEVEN_TETO), remonta e roda o G3 uma segunda e última vez. Este módulo não chama
a ElevenLabs nem mexe no G3.
Código 1 (e nada apagado) se não há segmento reprovado para regerar, ou se o asr.json não é deste episódio:
então o G3 falhou por outro motivo e o pipeline para como antes.
"""
import json
from pathlib import Path
import sys

from audio.roteiro import parse
from audio.voz import arquivos_do_cache
from episodio import validar


def reprovados(asr, falas_do_roteiro):
    """Índices reprovados no asr.json, conferidos contra a fala do roteiro (asr de outro episódio não vale)."""
    indices = sorted({int(i) for i in asr.get("reprovados", [])})
    if not indices:
        raise ValueError("G3 não reprovou segmento algum: nada a regerar")
    if any(not 0 <= i < len(falas_do_roteiro) for i in indices):
        raise ValueError("asr.json com segmento fora do roteiro")
    ouvidos = {(r["seg"], r["fala"]) for r in asr.get("segmentos", [])}
    for i in indices:
        if (i, falas_do_roteiro[i]) not in ouvidos:
            raise ValueError(f"asr.json não é deste episódio (segmento {i} com outra fala)")
    return indices


def invalidar(episodio, asr, cache):
    """Apaga do cache só o WAV dos segmentos reprovados. Devolve os índices."""
    roteiro = validar(episodio)["roteiro"]
    cru = [" ".join(u["fala"] for u in parse(texto)) for _, texto, _ in roteiro]
    indices = reprovados(asr, cru)
    _, arquivos = arquivos_do_cache(roteiro, Path(cache))
    # Dois segmentos com a mesma fala dividem o WAV: se um deles passou, o outro também será regerado, sem custo extra.
    for i in indices:
        arquivos[i].unlink(missing_ok=True)
    return indices


if __name__ == "__main__":
    try:
        episodio, asr, cache = sys.argv[1:4]
        indices = invalidar(json.loads(Path(episodio).read_text(encoding="utf-8")), json.loads(Path(asr).read_text(encoding="utf-8")), cache)
    except (ValueError, KeyError, TypeError, OSError) as erro:
        sys.exit(f"Regerar: {erro}")
    print("G3: regerando só os segmentos " + ", ".join(f"{i:03d}" for i in indices))
