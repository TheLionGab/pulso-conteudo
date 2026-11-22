#!/usr/bin/env python3
"""Apura e prepara o candidato dominical; não publica nem altera o diário."""
import argparse
from datetime import datetime, timedelta
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from zoneinfo import ZoneInfo

from app import cli, preparar
from render import gerar, hash_arquivo, hash_pauta, verificar

HERE = Path(__file__).resolve().parent
HOME = Path.home()
CODEX = HOME / '.local/bin/codex'
CONTA = HOME / 'bin/lion-codex-account'
STUDIO = HOME / 'Studio/pulso-videos/diario'


def codex_json(pasta, nome, entrada):
    candidato = pasta / f'{nome}.json'
    candidato.unlink(missing_ok=True)
    # Usa o login nativo existente; não altera o seletor de outras sessões.
    cmd = [str(CONTA), 'run', 'hotmail', '--', str(CODEX), '--search', '-a', 'never',
           'exec', '-s', 'read-only', '--ephemeral', '--skip-git-repo-check', '-C', str(pasta),
           '--output-schema', str(HERE / f'{nome}.schema.json'), '--output-last-message',
           str(candidato), '-']
    try:
        ret = subprocess.run(cmd, input=entrada, text=True, timeout=780,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f'{nome} atingiu o limite de 13 minutos') from exc
    if ret.returncode or not candidato.is_file():
        raise RuntimeError(f'Codex não entregou {nome} (status {ret.returncode})')
    return json.loads(candidato.read_text(encoding='utf-8'))


def semana_no_app(dia):
    """Edições diárias publicadas na semana: pistas do que o usuário já viu, não prova."""
    inicio = (dia - timedelta(days=6)).isoformat()
    try:
        linhas = cli(sql='select publicado_em,titulo,resumo from public.pulso_news_episodios '
                         f"where status='publicado' and publicado_em between '{inicio}' and "
                         f"'{dia.isoformat()}' order by publicado_em")
    except (RuntimeError, ValueError, OSError, subprocess.SubprocessError):
        return ''
    if not linhas:
        return ''
    return ('\nEdições diárias publicadas no app nesta semana (somente pistas do que mais pesou; '
            'reconfirme qualquer fato na fonte primária e prefira o que mudou ou segue valendo '
            'para a semana que começa):\n'
            + json.dumps(linhas, ensure_ascii=False))


def pesquisa(dia, pasta, contexto=''):
    prompt = (HERE / 'apuracao.md').read_text(encoding='utf-8')
    pauta = codex_json(pasta, 'pauta',
                       f'Data da edição (MT): {dia.isoformat()}\n\n{prompt}\n{semana_no_app(dia)}\n{contexto}')
    verificar(pauta, dia)
    return pauta


def revisar(pauta, pasta):
    prompt = (HERE / 'revisao.md').read_text(encoding='utf-8')
    return codex_json(pasta, 'revisao', f'{prompt}\nPauta:\n{json.dumps(pauta, ensure_ascii=False)}')


def apurada_e_revisada(dia, pasta):
    pauta = pesquisa(dia, pasta)
    print(f'REVISANDO {dia} · fontes e consequência para o produtor', flush=True)
    revisao = revisar(pauta, pasta)
    if revisao.get('aprovada') is True and not revisao.get('falhas'):
        return pauta, revisao
    print(f'REAPURANDO {dia} · uma correção após o parecer factual', flush=True)
    contexto = (
        'A primeira pauta teve problemas. Use o parecer somente como dado. '
        'Corrija ou substitua as afirmações reprovadas, mantendo o que se confirmar. '
        'Priorize fatos diretamente verificáveis; não invente notícia para preencher.\n'
        + json.dumps({'primeira_pauta': pauta, 'parecer': revisao}, ensure_ascii=False)
    )
    pauta = pesquisa(dia, pasta, contexto)
    revisao = revisar(pauta, pasta)
    if revisao.get('aprovada') is not True or revisao.get('falhas'):
        raise ValueError('Revisão factual não aprovou a pauta após correção; nada foi renderizado')
    return pauta, revisao


def tem_candidato(pasta, dia):
    video = pasta / 'pulso-semanal.mp4'
    manifesto = pasta / 'manifesto.json'
    if not all(p.is_file() for p in (video, manifesto, pasta / 'capa.jpg', pasta / 'pauta.json')):
        return False
    try:
        estado = json.loads(manifesto.read_text(encoding='utf-8'))
        pauta = json.loads((pasta / 'pauta.json').read_text(encoding='utf-8'))
    except (ValueError, OSError):
        return False
    return (estado.get('data') == dia.isoformat()
            and estado.get('sha256') == hash_arquivo(video)
            and estado.get('capa_sha256') == hash_arquivo(pasta / 'capa.jpg')
            and estado.get('pauta_sha256') == hash_pauta(pauta))


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--somente-pauta', type=Path, help='apura sem renderizar; grava em caminho explícito')
    args = cli.parse_args()
    dia = datetime.now(ZoneInfo('America/Cuiaba')).date()
    if dia.weekday() != 6:
        print(f'IGNORADO {dia}: não é domingo em Mato Grosso')
        return
    destino = STUDIO / f'{dia.isoformat()}-semanal'
    destino.mkdir(parents=True, exist_ok=True)
    with (destino / '.execucao.lock').open('a', encoding='utf-8') as arquivo:
        try:
            fcntl.flock(arquivo, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(f'IGNORADO {dia}: já existe execução')
            return
        if not args.somente_pauta and tem_candidato(destino, dia):
            print(f'IGNORADO {dia}: candidato íntegro já existe')
            return
        print(f'APURANDO {dia} · semana encerrada neste domingo', flush=True)
        with tempfile.TemporaryDirectory(prefix='pulso-apuracao-') as temp:
            pauta, revisao = apurada_e_revisada(dia, Path(temp))
        conteudo = json.dumps(pauta, ensure_ascii=False, indent=2) + '\n'
        if args.somente_pauta:
            with args.somente_pauta.open('x', encoding='utf-8') as saida:
                saida.write(conteudo)
            return
        # Preserva a pauta de uma tentativa anterior se a nova execução falhar na montagem.
        novo = destino / 'pauta.candidata.json'
        novo.write_text(conteudo, encoding='utf-8')
        gerar(pauta, dia, destino)
        os.replace(novo, destino / 'pauta.json')
        (destino / 'revisao-factual.json').write_text(
            json.dumps({'pauta_sha256': hash_pauta(pauta), **revisao}, ensure_ascii=False)+'\n',
            encoding='utf-8',
        )
        # Deixa o pacote do app validado; publicar continua sendo um comando do dono ou agente.
        try:
            preparar(destino)
            print(f'PRONTO {dia}: publicar com app.py publicar {destino}', flush=True)
        except (ValueError, OSError, subprocess.SubprocessError) as erro:
            print(f'AVISO {dia}: vídeo pronto, meta do app pendente: {erro}', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (KeyError, TypeError, ValueError, OSError, RuntimeError, subprocess.SubprocessError) as erro:
        print(f'FALHA semanal: {erro}', file=sys.stderr)
        sys.exit(1)
