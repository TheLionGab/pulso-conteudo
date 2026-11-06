"""Preflight e retomada locais. Não publica, não acessa rede nem executa SQL."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse


def inside(root, value):
    root = Path(root).resolve(strict=True)
    relative = Path(value)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Caminho fora do episódio')
    path = root / relative
    cursor = root
    for part in relative.parts:
        cursor /= part
        if cursor.is_symlink():
            raise ValueError('Symlink recusado')
    path = path.resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('Arquivo inválido')
    return path


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def valid_hash(value):
    return isinstance(value, str) and re.fullmatch(r'[a-f0-9]{64}', value) is not None


def check_manifest(root, manifest):
    media = [manifest['video']]
    if 'capa' in manifest:
        media.append(manifest['capa'])
    pairs = [(item['arquivo'], item['sha256']) for item in media]
    pairs.extend(manifest['entradas_sha256'].items())
    for name, expected in pairs:
        if not valid_hash(expected) or digest(inside(root, name)) != expected:
            raise ValueError('Hash divergente: ' + name)


def caption_check(actual, expected):
    return {'exact': bool(expected) and actual == expected,
            'once': bool(expected) and actual.count(expected) == 1}


def review_check(text, video_hash):
    # Recibos legados usam SHA256<hash> sem separador e \\n literais.
    text = text.replace('\\n', '\n')
    hashes = re.findall(r'(?:\bSHA256\s*:?\s*|(?<![a-f0-9]))([a-f0-9]{64})(?![a-f0-9])', text)
    return (valid_hash(video_hash) and video_hash in hashes
            and re.search(r'\bAPROVADO\b', text) is not None
            and re.search(r'\b(?:REPROVADO|NÃO\s+APROVADO|NAO\s+APROVADO)\b', text) is None)


def receipt_check(receipt, video_hash):
    if not valid_hash(video_hash) or receipt.get('video_sha256') != video_hash:
        raise ValueError('Recibo não corresponde ao vídeo')
    reel = urlparse(receipt.get('reel', ''))
    account = receipt.get('conta', '')
    if (account != 'pulsodocampo' or reel.scheme != 'https'
            or reel.netloc != 'www.instagram.com'
            or not re.fullmatch(r'/pulsodocampo/reel/[A-Za-z0-9_-]+/', reel.path)
            or reel.query or reel.fragment or not receipt.get('verificado_em')):
        raise ValueError('Recibo Instagram incompleto ou conta incorreta')
    return True


def pending(state):
    result = []
    for channel in ('instagram', 'app'):
        phase = state.get(channel, {}).get('phase')
        if phase == 'verified':
            continue
        if phase in ('sharing', 'submitted', 'uncertain'):
            result.append('reconcile_' + channel)
        else:
            result.append('verify_' + channel)
    return result


def sql_literal(value):
    if not isinstance(value, str) or '\x00' in value:
        raise ValueError('Texto SQL inválido')
    # E literal torna o escape independente de standard_conforming_strings.
    return "E'" + value.replace('\\', '\\\\').replace("'", "''") + "'"


def insert_sql(meta, video_path, cover_path):
    """Gera proposta, nunca executa. Conferir schema real antes de usar."""
    for path in (video_path, cover_path):
        if not re.fullmatch(r'[a-f0-9]{32}/(?:video|capa)-[a-f0-9]+\.(?:mp4|jpg)', path):
            raise ValueError('Objeto de mídia não imutável')
    if not re.fullmatch(r'pulso-news-\d{4}-\d{2}-\d{2}', meta['id']):
        raise ValueError('ID inválido')
    if type(meta['duracao_seg']) is not int or meta['duracao_seg'] <= 0:
        raise ValueError('Duração inválida')
    if not isinstance(meta['culturas'], list) or not isinstance(meta['fontes'], list):
        raise ValueError('Listas inválidas')
    columns = ['id', 'titulo', 'resumo', 'publicado_em', 'duracao_seg', 'culturas',
               'video_path', 'capa_path', 'push_titulo', 'push_corpo', 'fontes',
               'status', 'aprovado_em']
    values = [sql_literal(meta[key]) for key in columns[:4]]
    values += [str(meta['duracao_seg']),
               'ARRAY[' + ','.join(sql_literal(x) for x in meta['culturas']) + ']::text[]',
               sql_literal(video_path), sql_literal(cover_path),
               sql_literal(meta['push_titulo']), sql_literal(meta['push_corpo']),
               sql_literal(json.dumps(meta['fontes'], ensure_ascii=False)) + '::jsonb',
               "'publicado'", 'now()']
    return ('insert into public.pulso_news_episodios (' + ','.join(columns)
            + ') values (' + ','.join(values)
            + ') on conflict(id) do nothing returning id,status,video_path,capa_path;')


def load(root, name):
    return json.loads(inside(root, name).read_text())


def plan(root):
    manifest = load(root, 'out/manifesto.json')
    check_manifest(root, manifest)
    video_hash = manifest['video']['sha256']
    if not review_check(inside(root, 'qa/recibo-critico-publicacao.txt').read_text(), video_hash):
        raise ValueError('Revisão de publicação ausente ou reprovada no hash')
    meta = load(root, 'out/meta-app.json')
    state = {}
    receipt_path = Path(root) / 'out/publicado.json'
    if receipt_path.exists():
        receipt = load(root, 'out/publicado.json')
        receipt_check(receipt, video_hash)
        state['instagram'] = {'phase': 'verified'}
        app = receipt.get('app', {})
        if (app.get('id') == meta['id'] and app.get('status') == 'publicado'
                and app.get('aprovado_em') and app.get('verificacao')):
            state['app'] = {'phase': 'verified'}
    # Um journal é evidência de tentativa, nunca prova de sucesso por si só.
    journal_path = Path(root) / 'out/publicacao/estado.json'
    if journal_path.exists():
        journal = load(root, 'out/publicacao/estado.json')
        if journal.get('video_sha256') != video_hash:
            raise ValueError('Journal de outro candidato')
        for channel in ('instagram', 'app'):
            if channel not in state:
                phase = journal.get(channel, {}).get('phase')
                state[channel] = {'phase': phase if phase in ('sharing', 'submitted', 'uncertain')
                                  else 'uncertain'}
    return {'mode': 'dry-run', 'episode': meta['id'], 'video_sha256': video_hash,
            'evidence': 'recibos locais; sem reconferência online',
            'pending': pending(state), 'mutations': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('episode', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(plan(args.episode), ensure_ascii=False, indent=2))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(1, 'Preflight recusado: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
