#!/usr/bin/env python3
"""Leva o especial de domingo ao catálogo do app Pulso.

preparar: gera meta-app.json a partir da pauta e valida no publicador canônico
(dry-run, sem rede). publicar: backup do catálogo, upload imutável, conferência
do hash público, INSERT que recusa dia já publicado e leitura como anon.
Usa a sessão existente do Supabase CLI; nenhuma chave é lida do disco.
Falha depois do upload deixa estado 'incerto': reconciliar, nunca reenviar às cegas.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import sys
from urllib.request import urlopen

from render import hash_arquivo, hash_pauta

PROJETO = 'jgsmgvplwhisapvuqcji'
ORIGEM = f'https://{PROJETO}.supabase.co/storage/v1/object/public/pulso-news/'
PUBLICADOR = Path.home() / 'Developer/Pulso-Do-Campo/scripts/pulso-news/publicar.mjs'
CULTURAS = {'soja': 'soja', 'milho': 'milho', 'algod': 'algodao', 'trigo': 'trigo',
            'boi': 'pecuaria', 'gado': 'pecuaria', 'arroba': 'pecuaria', 'feij': 'feijao',
            'arroz': 'arroz', 'sorgo': 'sorgo'}
# Mesmos tetos do publicar.mjs (TETOS) e dos CHECKs da tabela.
TETOS = {'titulo': 80, 'resumo': 240, 'push_titulo': 45, 'push_corpo': 130}


def agora():
    return datetime.now(timezone.utc).isoformat()


def ler(caminho):
    return json.loads(caminho.read_text(encoding='utf-8'))


def gravar(caminho, valor):
    temp = caminho.with_name(caminho.name + '.tmp')
    temp.write_text(json.dumps(valor, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(caminho)


def cortar(texto, teto):
    if len(texto) <= teto:
        return texto
    return texto[:teto - 1].rsplit(' ', 1)[0].rstrip(',;:·') + '…'


def lista(prefixo, itens, teto):
    """Só itens inteiros cabem: notificação cortada no meio de um tema confunde."""
    texto = prefixo + itens[0] + '.'
    for n in range(2, len(itens) + 1):
        candidato = prefixo + ', '.join(itens[:n - 1]) + ' e ' + itens[n - 1] + '.'
        if len(candidato) > teto:
            break
        texto = candidato
    return cortar(texto, teto)


def pacote_integro(ep):
    """Manifesto, vídeo, capa e pauta precisam ser os mesmos do render."""
    manifesto, pauta = ler(ep / 'manifesto.json'), ler(ep / 'pauta.json')
    if (manifesto['sha256'] != hash_arquivo(ep / 'pulso-semanal.mp4')
            or manifesto['capa_sha256'] != hash_arquivo(ep / 'capa.jpg')
            or manifesto['pauta_sha256'] != hash_pauta(pauta)):
        raise ValueError('Pacote alterado depois do render')
    return manifesto, pauta


def meta_da_pauta(pauta, manifesto):
    cenas = pauta['cenas']
    meio = cenas[1:-1]
    texto = ' '.join([pauta['titulo']] + [c['titulo'] + ' ' + ' '.join(c['falas']) for c in cenas]).lower()
    culturas = sorted({v for k, v in CULTURAS.items() if k in texto}) or ['soja']
    temas = [c['titulo'] for c in meio]
    fontes, vistas = [], set()
    for c in meio:
        if c['url'] not in vistas:
            vistas.add(c['url'])
            fontes.append({'nome': c['fonte'], 'url': c['url'], 'data': c['data_fonte']})
    return {
        'id': f"pulso-news-{pauta['data']}",
        'titulo': cortar('Especial de domingo: ' + pauta['titulo'].split(':', 1)[-1].strip(), TETOS['titulo']),
        'resumo': lista('O melhor da semana para MT: ', temas, TETOS['resumo']),
        'publicado_em': pauta['data'],
        'duracao_seg': max(1, round(manifesto['duracao_seg'])),
        'culturas': culturas,
        'push_titulo': cortar(cenas[0]['titulo'], TETOS['push_titulo']),
        'push_corpo': lista('Especial de domingo: ', [t[0].lower() + t[1:] for t in temas],
                            TETOS['push_corpo']),
        'fontes': fontes,
    }


def preparar(ep):
    manifesto, pauta = pacote_integro(ep)
    meta = meta_da_pauta(pauta, manifesto)
    gravar(ep / 'meta-app.json', meta)
    cmd = ['node', str(PUBLICADOR), 'rascunho', '--meta', str(ep / 'meta-app.json'),
           '--video', str(ep / 'pulso-semanal.mp4'), '--capa', str(ep / 'capa.jpg'),
           '--sem-frescor', 'edição semanal sem cotação ancorada no banco', '--dry-run']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    if ret.returncode:
        raise ValueError('Publicador canônico reprovou o meta: ' + ret.stderr.strip()[-300:])
    return meta


def cli(*args, sql=None, arquivo=None):
    cmd = ['supabase', *args, '--project-ref', PROJETO, '--linked']
    if sql is not None or arquivo is not None:
        cmd = ['supabase', 'db', 'query', '--linked', '--project-ref', PROJETO, '--output', 'json']
        cmd += ['--file', str(arquivo)] if arquivo else [sql]
    ret = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if ret.returncode:
        raise RuntimeError(f'Supabase CLI recusou {args[:2] or "consulta"}; sem retry automático')
    if sql is None and arquivo is None:
        return ret.stdout
    dados = json.loads(ret.stdout)
    linhas = dados.get('rows') if isinstance(dados, dict) else dados
    if not isinstance(linhas, list):
        raise RuntimeError('Supabase CLI devolveu formato inesperado')
    return linhas


def q(valor):
    return "'" + str(valor).replace("'", "''") + "'"


def sql_insert(meta, caminhos):
    colunas = ['id', 'titulo', 'resumo', 'publicado_em', 'duracao_seg', 'culturas', 'video_path',
               'capa_path', 'push_titulo', 'push_corpo', 'fontes', 'status', 'aprovado_em']
    valores = [q(meta['id']), q(meta['titulo']), q(meta['resumo']), q(meta['publicado_em']) + '::date',
               str(int(meta['duracao_seg'])), 'ARRAY[' + ','.join(q(c) for c in meta['culturas']) + ']::text[]',
               q(caminhos['video_path']), q(caminhos['capa_path']), q(meta['push_titulo']),
               q(meta['push_corpo']), q(json.dumps(meta['fontes'], ensure_ascii=False)) + '::jsonb',
               "'publicado'", 'now()']
    # O NOT EXISTS impede trocar silenciosamente a edição de um dia já publicado.
    return (f"insert into public.pulso_news_episodios ({','.join(colunas)})\nselect "
            + ',\n  '.join(valores)
            + f"\nwhere not exists (select 1 from public.pulso_news_episodios where publicado_em="
              f"{q(meta['publicado_em'])} and status='publicado')\nreturning id,status,aprovado_em;\n")


def conferir_midia(caminho, local):
    with urlopen(ORIGEM + caminho, timeout=90) as resposta:
        dados = resposta.read(60 * 1024 * 1024)
    if resposta.status != 200 or hashlib.sha256(dados).hexdigest() != hash_arquivo(local):
        raise ValueError('Mídia pública diverge do pacote')


def publicar(ep):
    recibo = ep / 'publicado.json'
    if recibo.exists():
        raise ValueError('Recibo existente: edição já publicada ou incerta; reconciliar')
    manifesto, _ = pacote_integro(ep)
    meta = preparar(ep)
    qa = ep / 'qa'
    qa.mkdir(exist_ok=True)
    atuais = cli(sql=f"select * from public.pulso_news_episodios where publicado_em={q(meta['publicado_em'])}")
    if any(r['status'] == 'publicado' or r['id'] == meta['id'] for r in atuais):
        raise ValueError('Dia já tem edição publicada ou este ID existe; troca só com decisão do dono')
    gravar(qa / 'backup-dia-antes.json', atuais)
    token = secrets.token_hex(16)
    caminhos = {'video_path': f"{token}/video-{manifesto['sha256'][:12]}.mp4",
                'capa_path': f"{token}/capa-{manifesto['capa_sha256'][:12]}.jpg"}
    estado = {'video_sha256': manifesto['sha256'], 'fase': 'enviando', 'em': agora(), **caminhos}
    gravar(recibo, estado)
    try:
        for arq, campo, tipo in (('pulso-semanal.mp4', 'video_path', 'video/mp4'),
                                 ('capa.jpg', 'capa_path', 'image/jpeg')):
            cli('storage', 'cp', str(ep / arq), 'ss:///pulso-news/' + caminhos[campo],
                '--content-type', tipo, '--experimental')
            conferir_midia(caminhos[campo], ep / arq)
        sql = qa / 'publicar-app.sql'
        sql.write_text(sql_insert(meta, caminhos), encoding='utf-8')
        linhas = cli(arquivo=sql)
        if len(linhas) != 1 or linhas[0]['status'] != 'publicado':
            raise ValueError('INSERT não confirmou a publicação')
        anon = cli(sql=f"begin; set local role anon; select id,status,video_path,capa_path from "
                       f"public.pulso_news_episodios where id={q(meta['id'])}; commit;")
        if len(anon) != 1 or anon[0]['video_path'] != caminhos['video_path']:
            raise ValueError('Leitura anon não confirmou a edição')
        estado.update(fase='publicado', id=meta['id'], aprovado_em=linhas[0]['aprovado_em'],
                      verificado_anon_em=agora())
        gravar(recibo, estado)
        return estado
    except Exception:
        estado['fase'] = 'incerto'
        gravar(recibo, estado)
        raise


def main():
    cli_ = argparse.ArgumentParser(description=__doc__)
    cli_.add_argument('acao', choices=('preparar', 'publicar'))
    cli_.add_argument('episodio', type=Path)
    args = cli_.parse_args()
    ep = args.episodio.resolve(strict=True)
    try:
        resultado = preparar(ep) if args.acao == 'preparar' else publicar(ep)
    except (ValueError, KeyError, OSError, RuntimeError, subprocess.SubprocessError) as erro:
        print(f'FALHA app: {erro}', file=sys.stderr)
        sys.exit(1)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
