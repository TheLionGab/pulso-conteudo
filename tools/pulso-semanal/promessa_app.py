#!/usr/bin/env python3
"""Reprova roteiro do Pulso News que prometa tela ou função que o app não tem.

Regra: frase que mande o produtor ver/conferir/abrir/acompanhar algo "no Pulso do
Campo" ou "no app" precisa casar com um recurso cuja tela exista no snapshot
telas-app.json (lista de apps/meu-talhao/app/(tabs) na origin/main do app). Promessas
proibidas conhecidas (ex.: aviso do município no app) reprovam sempre.
Entradas: pauta.json, JSON de linhas do catálogo (titulo/resumo/push_*), lista de
falas do roteiro, ou --texto. Saída: achados e exit 1 se reprovar.
--atualizar-telas regenera o snapshot (só leitura no repo do app).
Limite: checa TEMA, não função exata. "clima" casa clima.tsx, mas não prova que a
tela tenha aquele dado ou botão; a lista de recursos e de promessas proibidas é
curada à mão. Frase sem o app como lugar ("o Pulso do Campo apurou", "consultam o
Pulso do Campo") não passa pela regra de recurso; só pelas promessas proibidas.
"""
import argparse
from datetime import date
import json
from pathlib import Path
import re
import subprocess
import sys

TELAS = Path(__file__).with_name('telas-app.json')
REPO_APP = Path.home() / 'Developer/Pulso-Do-Campo'
PREFIXO = 'apps/meu-talhao/app/(tabs)/'

# Recurso citável (regex sobre a frase) -> tela exigida, relativa a (tabs)/.
RECURSOS = (
    (r'previs|chuva|clima|tempo\b|temperatura|umidade|radar', 'clima.tsx'),
    (r'cota[çc]|pre[çc]o|pra[çc]a|saca\b|arroba|mercado', 'cotacoes.tsx'),
    (r'not[ií]cia|manchete', 'noticias.tsx'),
    (r'alertas?\b|notifica[çc]', 'alertas.tsx'),
    (r'assistente|\bia\b|intelig[êe]ncia artificial', 'assistente.tsx'),
    (r'diagn[óo]stic', 'diagnostico.tsx'),
    (r'comunidade', 'comunidade/index.tsx'),
    (r'frete', 'ferramentas/calculadora-frete.tsx'),
    (r'custo de produ[çc]', 'ferramentas/custo-producao.tsx'),
    (r'rela[çc][ãa]o de troca', 'ferramentas/relacao-troca.tsx'),
    (r'simulador de safra', 'ferramentas/simulador-safra.tsx'),
    (r'simulador de venda', 'ferramentas/simulador-venda.tsx'),
    (r'manejo de pragas|pragas', 'ferramentas/manejo-pragas.tsx'),
)
# Promessas que o app não cumpre. aviso_inmet saiu da UI em 08/11/2026
# (apps/meu-talhao/lib/push/channels.ts, ALERTAS_UI_CHANNELS): sem aviso oficial no app.
PROIBIDAS = (
    (r'(?:avisos?|alertas?)\s+(?:d[oa]s?|de|para|pra)\s+(?:seu\s+|sua\s+|a\s+|o\s+)?'
     r'(?:munic[ií]pios?|cidades?|regi[ãa]o|propriedade|talh[ãa]o)',
     'aviso/alerta por município, cidade ou região: o app não tem'),
    (r'(?:avisos?|alertas?)\s+(?:do\s+|da\s+)?(?:inmet|defesa civil)',
     'aviso do Inmet ou da Defesa Civil: saiu do app em 08/11/2026'),
    (r'(?:avisos?|alertas?)\s+(?:de|d[oa]s?)\s+(?:geadas?|tempestades?|temporais|temporal|granizo|vendaval)',
     'aviso/alerta de evento climático: o app não tem'),
    (r'(?:avisos?|alertas?)\s+oficia(?:l|is)', 'avisos oficiais: o app não tem'),
)
VERBO = re.compile(r'\b(?:ver|veja|vejam|confir[ae]\w*|conferir|abr[ae]\w*|abrir|acompanh\w+|'
                   r'consult\w+|olh\w+|cheque|checar|receb\w+|chega\w*|notifica\w*|avisa\w*)\b', re.I)
APP = re.compile(r'pulso do campo|\bapp\b|aplicativo', re.I)
# O app como LUGAR ("no app", "pelo Pulso do Campo", "abra o app"), não como sujeito
# ("o Pulso do Campo apurou") nem objeto de outro verbo ("consultam o Pulso do Campo").
LUGAR = re.compile(r'\b(?:no|na|nos|nas|pelo|pela|do|da|dentro d[oa]|via|em)\s+(?:seu\s+|nosso\s+)?'
                   r'(?:app|aplicativo|pulso do campo)\b|\babr[ae]\w*\s+o\s+(?:app|aplicativo|pulso do campo)\b',
                   re.I)
FRASES = re.compile(r'(?<=[.!?])\s+')


def carregar_telas(caminho=TELAS):
    return set(json.loads(Path(caminho).read_text(encoding='utf-8'))['telas'])


def atualizar_telas(caminho=TELAS):
    """Só leitura no repo do app: git ls-tree + rev-parse da origin/main."""
    def git(*a):
        ret = subprocess.run(['git', '-C', str(REPO_APP), *a], capture_output=True, text=True, check=True)
        return ret.stdout.strip()
    arquivos = git('ls-tree', '-r', '--name-only', 'origin/main', '--', PREFIXO.rstrip('/')).splitlines()
    telas = sorted(a[len(PREFIXO):] for a in arquivos if a.endswith('.tsx') and not a.endswith('_layout.tsx'))
    dados = {'origem': 'apps/meu-talhao/app/(tabs) em origin/main de Pulso-Do-Campo',
             'sha': git('rev-parse', 'origin/main'), 'data': date.today().isoformat(), 'telas': telas}
    Path(caminho).write_text(json.dumps(dados, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return dados


def checar_unidade(frase, campo, telas, app_no_contexto=False):
    """Achados de uma frase. app_no_contexto: a cena cita o app em outra linha."""
    achados = []
    tem_app = bool(APP.search(frase))
    for padrao, motivo in PROIBIDAS:
        if re.search(padrao, frase, re.I) and (tem_app or app_no_contexto):
            return [{'campo': campo, 'frase': frase, 'motivo': 'promessa proibida, ' + motivo}]
    if LUGAR.search(frase) and VERBO.search(frase):
        exigidas = [tela for padrao, tela in RECURSOS if re.search(padrao, frase, re.I)]
        if not exigidas:
            achados.append({'campo': campo, 'frase': frase,
                            'motivo': 'manda ver algo no app sem recurso conhecido'})
        for tela in exigidas:
            if tela not in telas:
                achados.append({'campo': campo, 'frase': frase, 'motivo': f'tela inexistente no app: {tela}'})
    return achados


def checar_unidades(unidades, telas):
    """unidades: [(campo, texto)] de um mesmo bloco (cena ou linha do catálogo)."""
    quebradas = [(campo, f.strip()) for campo, texto in unidades if isinstance(texto, str)
                 for f in FRASES.split(texto) if f.strip()]
    app_no_bloco = any(APP.search(f) for _, f in quebradas)
    achados = []
    for campo, frase in quebradas:
        achados += checar_unidade(frase, campo, telas, app_no_bloco)
    return achados


def checar_texto(texto, telas, campo='texto'):
    return checar_unidades([(campo, texto)], telas)


def unidades_da_cena(cena, prefixo):
    unidades = [(f'{prefixo}.titulo', cena.get('titulo')), (f'{prefixo}.nota', cena.get('nota'))]
    unidades += [(f'{prefixo}.falas[{i}]', f) for i, f in enumerate(cena.get('falas', []))]
    unidades += [(f'{prefixo}.linhas[{i}]', f"{l.get('rotulo', '')}: {l.get('valor', '')}")
                 for i, l in enumerate(cena.get('linhas', []))]
    return unidades


def checar_pauta(pauta, telas):
    achados = checar_unidades([('titulo', pauta.get('titulo'))], telas)
    for i, cena in enumerate(pauta.get('cenas', [])):
        achados += checar_unidades(unidades_da_cena(cena, f'cenas[{i}]'), telas)
    return achados


def checar_linhas(linhas, telas, prefixo='linhas'):
    achados = []
    for i, linha in enumerate(linhas):
        achados += checar_unidades([(f'{prefixo}[{i}].{c}', linha.get(c))
                                    for c in ('titulo', 'resumo', 'push_titulo', 'push_corpo')], telas)
    return achados


def checar_dados(dados, telas):
    """Detecta o formato: pauta, catálogo ({rows}), meta-app, lista de linhas ou de falas."""
    if isinstance(dados, dict) and 'cenas' in dados:
        return checar_pauta(dados, telas)
    if isinstance(dados, dict) and 'rows' in dados:
        return checar_linhas(dados['rows'], telas, 'rows')
    if isinstance(dados, dict):
        return checar_linhas([dados], telas, 'meta')
    if dados and all(isinstance(x, dict) for x in dados):
        return checar_linhas(dados, telas)
    return checar_unidades([(f'falas[{i}]', x[1] if isinstance(x, list) else x)
                            for i, x in enumerate(dados)], telas)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('arquivos', nargs='*', type=Path)
    cli.add_argument('--texto')
    cli.add_argument('--atualizar-telas', action='store_true')
    args = cli.parse_args()
    if args.atualizar_telas:
        dados = atualizar_telas()
        print(f"telas-app.json: {len(dados['telas'])} telas, origin/main {dados['sha'][:8]}")
    telas = carregar_telas()
    achados = checar_texto(args.texto, telas) if args.texto else []
    for arq in args.arquivos:
        achados += [{**a, 'arquivo': str(arq)}
                    for a in checar_dados(json.loads(arq.read_text(encoding='utf-8')), telas)]
    for a in achados:
        print(f"{a.get('arquivo', '-')}:{a['campo']}: {a['motivo']}: \"{a['frase']}\"")
    sys.exit(1 if achados else 0)


if __name__ == '__main__':
    main()
