#!/usr/bin/env python3
"""Distribui um episódio aprovado no catálogo Pulso. Sem TTS, agenda ou chaves novas.

prepare gera um plano local; publish usa a sessão existente do Supabase CLI.
Uma tentativa incerta exige reconciliação, nunca repetição automática.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
from urllib.request import urlopen
import uuid

PROJECT = 'jgsmgvplwhisapvuqcji'
ORIGIN = f'https://{PROJECT}.supabase.co'
GATES = {'G-PESQUISA', 'G0', 'G1', 'G2', 'G3', 'G4', 'G3-mix', 'visual', 'editorial'}
HELPER = Path(__file__).resolve().parents[1] / '.agents/skills/pulso-publicar/scripts/workflow.py'
spec = importlib.util.spec_from_file_location('pulso_workflow', HELPER)
wf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wf)


def now():
    return datetime.now(timezone.utc).isoformat()


def load(ep, name):
    return json.loads(wf.inside(ep, name).read_text())


def atomic(ep, name, value):
    """Saídas locais não podem escapar do episódio nem seguir symlinks."""
    ep = ep.resolve(strict=True)
    rel = Path(name)
    if rel.is_absolute() or '..' in rel.parts:
        raise ValueError('Saída fora do episódio')
    cursor = ep
    for part in rel.parts:
        cursor /= part
        if cursor.is_symlink():
            raise ValueError('Saída symlink recusada')
    target = ep / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    # Nome exclusivo: não seguir um temporário plantado por outra execução.
    temp = target.with_name(target.name + '.' + uuid.uuid4().hex + '.tmp')
    with temp.open('x') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2))
    temp.replace(target)


def candidate(ep):
    manifest = load(ep, 'out/manifesto.json')
    wf.check_manifest(ep, manifest)
    sha = manifest['video']['sha256']
    if not wf.review_check(wf.inside(ep, 'qa/recibo-critico-publicacao.txt').read_text(), sha):
        raise ValueError('Crítico não aprovou este vídeo')
    ready = load(ep, 'out/pronto-app.json')
    if ready['video_sha256'] != sha or set(ready['gates']) != GATES:
        raise ValueError('Gates ausentes ou de outro candidato')
    for gate in ready['gates'].values():
        if gate['resultado'] != 'aprovado' or not gate['evidencias']:
            raise ValueError('Gate não aprovado')
        for proof in gate['evidencias']:
            if wf.digest(wf.inside(ep, proof['arquivo'])) != proof['sha256']:
                raise ValueError('Prova alterada: ' + proof['arquivo'])
    if 'capa' not in manifest:
        raise ValueError('Capa obrigatória')
    meta = load(ep, 'out/meta-app.json')
    # Validação completa do contrato segue no publicador canônico do app.
    if not re.fullmatch(r'pulso-news-\d{4}-\d{2}-\d{2}(?:-[a-z0-9]+)*', meta['id']):
        raise ValueError('ID inválido')
    if meta['id'][11:21] != meta['publicado_em'] or len(meta['id']) > 80:
        raise ValueError('Data ou tamanho do ID divergente')
    return manifest, meta


def sql_for(meta, paths, previous):
    q = wf.sql_literal
    columns = ['id', 'titulo', 'resumo', 'publicado_em', 'duracao_seg', 'culturas',
               'video_path', 'capa_path', 'push_titulo', 'push_corpo', 'fontes', 'status', 'aprovado_em']
    values = [q(meta[key]) for key in columns[:4]] + [str(meta['duracao_seg']),
              'ARRAY[' + ','.join(q(c) for c in meta['culturas']) + ']::text[]',
              q(paths['video_path']), q(paths['capa_path']), q(meta['push_titulo']),
              q(meta['push_corpo']), q(json.dumps(meta['fontes'], ensure_ascii=False)) + '::jsonb',
              "'publicado'", 'now()']
    statements = []
    if previous:
        # Compare o snapshot inteiro: alteração concorrente de metadados também bloqueia.
        statements += [f"PERFORM 1 FROM public.pulso_news_episodios e WHERE id={q(previous['id'])} "
                       f"AND to_jsonb(e)={q(json.dumps(previous, ensure_ascii=False))}::jsonb FOR UPDATE;",
                       "IF NOT FOUND THEN RAISE EXCEPTION 'Edição anterior mudou; reconciliar'; END IF;",
                       f"UPDATE public.pulso_news_episodios SET status='rascunho',atualizado_em=now() WHERE id={q(previous['id'])};"]
    statements += [f"INSERT INTO public.pulso_news_episodios ({','.join(columns)}) VALUES ({','.join(values)});"]
    return ('DO $publicacao$ BEGIN\n' + '\n'.join(statements) + '\nEND $publicacao$;\n'
            f"SELECT id,status,video_path,capa_path,aprovado_em FROM public.pulso_news_episodios WHERE id={q(meta['id'])};\n")


def prepare(ep, snapshot, replace_id=None):
    manifest, meta = candidate(ep)
    rows = snapshot if isinstance(snapshot, list) else snapshot['rows']
    if any(row['id'] == meta['id'] for row in rows):
        raise ValueError('ID já existe; reconciliar antes de planejar')
    published = [r for r in rows if r['publicado_em'] == meta['publicado_em'] and r['status'] == 'publicado']
    if len(published) > 1 or (published and published[0]['id'] != replace_id):
        raise ValueError('Dia já publicado; troca exige ID explícito e autorização do chat')
    if replace_id and (not published or published[0]['id'] != replace_id):
        raise ValueError('Edição a substituir não corresponde ao snapshot')
    token = uuid.uuid4().hex
    paths = {'video_path': f"{token}/video-{manifest['video']['sha256'][:12]}.mp4",
             'capa_path': f"{token}/capa-{manifest['capa']['sha256'][:12]}.jpg"}
    plan = {'project': PROJECT, 'id': meta['id'], 'video_sha256': manifest['video']['sha256'],
            'capa_sha256': manifest['capa']['sha256'], 'meta_sha256': wf.digest(wf.inside(ep, 'out/meta-app.json')),
            'previous': published[0] if published else None, **paths}
    sql = sql_for(meta, paths, plan['previous'])
    plan['sql_sha256'] = hashlib.sha256(sql.encode()).hexdigest()
    return plan, sql


def cli(query):
    result = subprocess.run(['supabase', 'db', 'query', '--linked', '--project-ref', PROJECT,
                             '--output', 'json', query], capture_output=True, text=True, timeout=90)
    if result.returncode:
        raise RuntimeError('Supabase CLI recusou consulta; nenhum retry automático')
    data = json.loads(result.stdout)
    return data if isinstance(data, list) else data['rows']


def public_media(ep, manifest, plan):
    for kind, field in (('video', 'video_path'), ('capa', 'capa_path')):
        url = ORIGIN + '/storage/v1/object/public/pulso-news/' + plan[field]
        with urlopen(url, timeout=60) as response:
            data = response.read(50 * 1024 * 1024 + 1)
            if response.status != 200 or len(data) != manifest[kind]['bytes']:
                raise ValueError('Mídia pública incompleta')
            if hashlib.sha256(data).hexdigest() != manifest[kind]['sha256']:
                raise ValueError('Mídia pública de outro candidato')


def publish(ep, plan, publisher, g6_authorization=None):
    manifest, meta = candidate(ep)
    if (plan['project'] != PROJECT or plan['id'] != meta['id']
            or plan['video_sha256'] != manifest['video']['sha256']
            or plan['capa_sha256'] != manifest['capa']['sha256']
            or plan['meta_sha256'] != wf.digest(wf.inside(ep, 'out/meta-app.json'))):
        raise ValueError('Plano de outro candidato')
    sql = wf.inside(ep, 'qa/publicar-app.sql')
    expected_sql = sql_for(meta, plan, plan['previous'])
    if wf.digest(sql) != plan['sql_sha256'] or sql.read_text() != expected_sql:
        raise ValueError('SQL alterado após planejamento/revisão')
    review = load(ep, 'qa/revisao-sql.json')
    if review.get('aprovado') is not True or review.get('sql_sha256') != plan['sql_sha256']:
        raise ValueError('Crítico não aprovou este SQL')
    for kind, field, ext in (('video','video_path','mp4'),('capa','capa_path','jpg')):
        if not re.fullmatch(r'[a-f0-9]{32}/'+kind+'-'+manifest[kind]['sha256'][:12]+r'\.'+ext, plan[field]):
            raise ValueError('Caminho de mídia não é imutável e vinculado ao candidato')
    receipt = load(ep, 'out/publicado.json') if (ep/'out/publicado.json').exists() else {}
    if receipt and receipt.get('video_sha256') != plan['video_sha256']:
        raise ValueError('Recibo existente de outro candidato; preservar e reconciliar')
    if g6_authorization:
        auth = load(ep, g6_authorization)
        if (auth.get('confirmacao_inequivoca_da_dispensa') is not True
                or auth.get('id') != meta['id'] or auth.get('video_sha256') != plan['video_sha256']
                or auth.get('reutilizavel') is not False or not auth.get('motivo')):
            raise ValueError('Exceção G6 não corresponde à autorização específica do chat')
    else:
        # O G6 canônico consulta o banco. Não carrega .env ou credenciais do disco.
        gate = publisher.with_name('frescor.mjs')
        if subprocess.run(['node', str(gate), '--dossie', str(wf.inside(ep, 'dossie.json'))],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
            raise ValueError('G6 reprovou; sem envio ou dispensa automática')
    journal = load(ep, 'out/publicacao/estado.json') if (ep/'out/publicacao/estado.json').exists() else {}
    if journal and journal.get('video_sha256') != plan['video_sha256']:
        raise ValueError('Journal de outro candidato')
    if journal.get('app'):
        raise ValueError('App já teve tentativa; reconciliar, não reenviar')
    q = wf.sql_literal
    # Backup imediatamente antes da primeira escrita, com schema conferido no projeto alvo.
    columns = cli("select column_name from information_schema.columns where table_schema='public' and table_name='pulso_news_episodios'")
    if not set(meta).issubset({row['column_name'] for row in columns}):
        raise ValueError('Schema incompatível; sem mutação')
    current = cli(f"select * from public.pulso_news_episodios where publicado_em={q(meta['publicado_em'])}")
    if any(row['id'] == meta['id'] for row in current):
        raise ValueError('Candidato já existe; reconciliar')
    published = [r for r in current if r['status'] == 'publicado']
    expected = [plan['previous']] if plan['previous'] else []
    if published != expected:
        raise ValueError('Catálogo mudou após o plano; reconciliar')
    atomic(ep, 'qa/backup-app-antes-publicacao.json', current)
    journal.update(video_sha256=plan['video_sha256'], app={'phase':'submitted','em':now(),'id':meta['id']})
    atomic(ep, 'out/publicacao/estado.json', journal)
    try:
        for kind, field in (('video', 'video_path'), ('capa', 'capa_path')):
            media = wf.inside(ep, manifest[kind]['arquivo'])
            result = subprocess.run(['supabase','storage','cp',str(media), 'ss:///pulso-news/'+plan[field],
                                     '--project-ref',PROJECT,'--linked'], capture_output=True, timeout=300)
            if result.returncode:
                raise RuntimeError('Upload não confirmado; reconciliar')
        public_media(ep, manifest, plan)
        result = subprocess.run(['supabase','db','query','--linked','--project-ref',PROJECT,
                                 '--file',str(sql),'--output','json'], capture_output=True, timeout=90)
        if result.returncode:
            raise RuntimeError('Publicação não confirmada; reconciliar')
        # Leitura como anon, sem presumir que a escrita administrativa é visível ao usuário.
        rows = cli(f"begin; set local role anon; select id,status,video_path,capa_path,aprovado_em from public.pulso_news_episodios where id={q(meta['id'])}; commit;")
        if (len(rows) != 1 or rows[0]['status'] != 'publicado'
                or any(rows[0][k] != plan[k] for k in ('video_path','capa_path'))):
            raise ValueError('Leitura anon não confirmou o candidato')
        public_media(ep, manifest, plan)
        atomic(ep, 'qa/verificacao-app-anon.json', {'em':now(),'rows':rows,'video_sha256':plan['video_sha256'],'midias_http_hash':True})
        # Releia: o canal Instagram pode ter sido confirmado durante a transferência.
        receipt = load(ep, 'out/publicado.json') if (ep/'out/publicado.json').exists() else {}
        if receipt and receipt.get('video_sha256') != plan['video_sha256']:
            raise ValueError('Recibo mudou de candidato durante publicação; reconciliar')
        app = {'id':meta['id'],'status':'publicado','aprovado_em':rows[0]['aprovado_em'],
               'verificado_em':now(),'verificacao':'qa/verificacao-app-anon.json',
               'video_path':plan['video_path'],'capa_path':plan['capa_path']}
        receipt.update(video_sha256=plan['video_sha256'], app=app)
        atomic(ep, 'out/publicado.json', receipt)
        journal['app'] = dict(app, phase='verified')
        atomic(ep, 'out/publicacao/estado.json', journal)
        return app
    except Exception:
        journal['app']['phase'] = 'uncertain'
        atomic(ep, 'out/publicacao/estado.json', journal)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare','publish'))
    parser.add_argument('episode', type=Path)
    parser.add_argument('--snapshot', help='Backup JSON completo obtido pelo Supabase CLI')
    parser.add_argument('--replace-id')
    parser.add_argument('--publisher', type=Path, default=Path('/Users/mac/Developer/Pulso-Do-Campo/scripts/pulso-news/publicar.mjs'))
    parser.add_argument('--g6-authorization', help='Caminho relativo; requer exceção expressa do dono no chat')
    args = parser.parse_args()
    ep = args.episode.resolve(strict=True)
    try:
        if args.action == 'prepare':
            if not args.snapshot:
                raise ValueError('--snapshot obrigatório; prepare não faz rede')
            if (ep/'out/plano-app.json').exists():
                raise ValueError('Plano existente: preservar candidato/revisão, não regenerar caminhos')
            plan, sql = prepare(ep, load(ep, args.snapshot), args.replace_id)
            # Valida meta/mídia pelo publicador existente, sem rede nem G6 dispensado.
            manifest, meta = candidate(ep)
            command = ['node',str(args.publisher),'rascunho','--meta',str(wf.inside(ep,'out/meta-app.json')),
                       '--video',str(wf.inside(ep,manifest['video']['arquivo'])),
                       '--capa',str(wf.inside(ep,manifest['capa']['arquivo'])),'--dry-run']
            if subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
                raise ValueError('Publicador canônico reprovou o pacote')
            atomic(ep, 'out/plano-app.json', plan)
            sql_path = ep/'qa/publicar-app.sql'
            if sql_path.is_symlink():
                raise ValueError('SQL symlink recusado')
            # Diretório qa foi validado em candidate pelas provas locais.
            sql_path.write_text(sql)
            print('Plano preparado; G6, autorização e revisão do SQL ainda obrigatórios. Sem mutações remotas.')
        else:
            print(json.dumps(publish(ep, load(ep,'out/plano-app.json'), args.publisher,
                                     args.g6_authorization), ensure_ascii=False))
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(1, 'Pipeline interrompido: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
