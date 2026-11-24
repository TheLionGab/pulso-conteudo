import math


def checar(video, duracao, lufs, pico, episodio):
    falhas = []
    if (video.get("width"), video.get("height")) != (1080, 1920):
        falhas.append("vídeo não é 1080x1920")
    if any(video.get(campo) != "30/1" for campo in ("avg_frame_rate", "r_frame_rate")):
        falhas.append("vídeo não é 30 fps")
    if not 30 <= duracao <= 60:
        falhas.append(f"duração {duracao:.2f} s fora de 30–60 s")
    if lufs is None or not -15 <= lufs <= -13:
        falhas.append(f"loudness integrado {lufs} LUFS fora de -14 ± 1")
    if pico is None or not math.isfinite(pico) or pico > -1:
        falhas.append(f"pico {pico} dBTP acima de -1 ou inválido")
    cenas = episodio.get("cenas", [])
    if not cenas or cenas[-1].get("tipo") != "fecho_app":
        falhas.append("última cena deve ser fecho_app")
    if not episodio.get("legenda_instagram", "").strip():
        falhas.append("legenda_instagram vazia")
    return falhas
