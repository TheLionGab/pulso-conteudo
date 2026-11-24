"""Pulso News: soja em MT; Conab até30/10/2026. Uma pauta, sem promoção forçada."""
import re

ROTEIRO = [('intro', '[gancho]O plantio da soja está perto do fim em Mato Grosso.', 0.15), ('intro', '[g97]Mas como estão essas lavouras?', 0.15), ('oni', '[oni]Nos *{12|doze}* estados acompanhados pela Conab, eram *{54,3%|cinquenta e quatro vírgula três por cento}*.', 0.15), ('regioes', '[regioes]Em Mato Grosso, uma semana antes, eram *{75,78%|quase setenta e seis por cento}*.', 0.15), ('alerta', '[alerta]A Conab descreve bom desenvolvimento das lavouras. Mas aponta diferenças pontuais no estabelecimento.', 0.15), ('bolso', '[bolso]O avanço do plantio não mede produtividade. [s_v]Confira como as plantas estão se estabelecendo, com assistência técnica.', 0.15), ('fecho', '[fecho]Dados até *{30/10|trinta de outubro}*. [tchau]*{Pulso News|Pulso News}*, informação para a decisão no campo.', 0.5)]

TOKEN = re.compile(r"\[(\w+)\]|\{([^|}]+)\|([^}]+)\}|(\S+)")


def parse(texto):
    """Devolve unidades: {exibe, fala, hl, cues}. Um {a|b} vira uma unidade só."""
    unidades, cues_pendentes = [], []
    texto = re.sub(r"\*\{([^}]*)\}\*", r"{*\1*}", texto)
    for m in TOKEN.finditer(texto):
        cue, ex, fa, palavra = m.groups()
        if cue:
            cues_pendentes.append(cue)
            continue
        if ex is not None:
            hl = ex.startswith("*")
            ex, fa = ex.strip("*"), fa.strip("*")
            unidades.append({"exibe": ex, "fala": fa, "hl": hl, "cues": cues_pendentes})
        else:
            tail_cues = re.findall(r"\[(\w+)\]", palavra)
            palavra = re.sub(r"\[\w+\]", "", palavra)
            if not palavra:
                cues_pendentes += tail_cues
                continue
            hl = "*" in palavra
            limpa = palavra.replace("*", "")
            if unidades and re.fullmatch(r"[.,:;!?…]+", limpa):
                unidades[-1]["exibe"] += limpa
                unidades[-1]["fala"] += limpa
                for c in tail_cues:
                    unidades[-1].setdefault("cues_fim", []).append(c)
                continue
            unidades.append({"exibe": limpa, "fala": limpa, "hl": hl, "cues": cues_pendentes})
            for c in tail_cues:
                unidades[-1].setdefault("cues_fim", []).append(c)
        cues_pendentes = []
    if cues_pendentes and unidades:
        unidades[-1].setdefault("cues_fim", []).extend(cues_pendentes)
    return unidades
