#!/usr/bin/env python3
"""Render a sourced Sunday briefing into a reviewable vertical package."""
import argparse
from datetime import date, timedelta
from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageFont

HOME = Path.home()
STUDIO = HOME / 'Studio/pulso-videos'
ASSETS = STUDIO / 'assets/semanal'
VOZ = STUDIO / 'pulso-news-2026-10-14'
AUDIO = HOME / 'Developer/Pulso-Do-Campo/scripts/pulso-news/remotion/audio'
W, H, FPS = 720, 1280, 30
INK, PAPER, MUTED = '#0A1614', '#F5F7ED', '#A3BBB1'
LIME, BLUE, GOLD = '#C7FD73', '#A7DCFF', '#FFD092'
FONTES_PRIMARIAS = (
    'gov.br', 'usda.gov', 'embrapa.br', 'cepea.esalq.usp.br', 'imea.com.br',
    'b3.com.br', 'aprosoja.com.br', 'senar.org.br', 'famato.org.br',
)
ACCENTS = {'gancho': LIME, 'mapa': BLUE, 'barras': LIME, 'decisao': GOLD, 'fecho': LIME}


def verificar(pauta, esperada):
    dia = date.fromisoformat(pauta['data'])
    cenas = pauta['cenas']
    if dia != esperada or dia.weekday() != 6:
        raise ValueError('Pauta não corresponde ao domingo solicitado')
    if not 5 <= len(cenas) <= 7 or cenas[0]['tipo'] != 'gancho' or cenas[-1]['tipo'] != 'fecho':
        raise ValueError('Informe entre cinco e sete cenas, com gancho e fecho')
    fontes = set()
    for i, cena in enumerate(cenas):
        tipo = cena['tipo']
        linhas, falas = cena['linhas'], cena['falas']
        minimo_linhas = 0 if tipo == 'gancho' else 1
        if tipo not in ACCENTS or not minimo_linhas <= len(linhas) <= 3 or not 1 <= len(falas) <= 3:
            raise ValueError(f'Estrutura inválida na cena {i + 1}')
        campos = [('seção', cena['secao'], 42), ('título', cena['titulo'], 65)]
        if cena['nota']:
            campos.append(('nota', cena['nota'], 104))
        campos += [('fala', fala, 110) for fala in falas]
        for linha in linhas:
            campos.extend([('rótulo', linha['rotulo'], 38), ('valor', linha['valor'], 42)])
        if cena.get('virada'):
            campos.append(('virada', cena['virada'], 48))
        for nome, valor, limite in campos:
            if not valor.strip() or len(valor) > limite or '\n' in valor:
                raise ValueError(f'Campo {nome} vazio ou longo na cena {i + 1} ({len(valor)}/{limite})')
        if tipo in ('gancho', 'fecho'):
            if i not in (0, len(cenas) - 1):
                raise ValueError('Gancho e fecho não são provas')
        else:
            url = urlparse(cena['url'])
            entidade = url.hostname or ''
            reconhecida = any(entidade == raiz or entidade.endswith('.' + raiz)
                               for raiz in FONTES_PRIMARIAS)
            data_fonte = date.fromisoformat(cena['data_fonte'])
            if (url.scheme != 'https' or not reconhecida or url.username or not cena['fonte'].strip()
                    or not dia - timedelta(days=6) <= data_fonte <= dia):
                raise ValueError(f'Fonte primária ou data inválida na cena {i + 1}')
            # Órgãos como Conab e MAPA compartilham o portal gov.br.
            caminho = url.path.strip('/').split('/', 1)[0]
            autoridade = (entidade.removeprefix('www.'), caminho if entidade in ('gov.br', 'www.gov.br') else '')
            fontes.add(autoridade)
        if tipo == 'barras':
            nums = [linha['quantidade'] for linha in linhas]
            if len(nums) < 2 or any(type(n) not in (int, float) or not math.isfinite(n) or n <= 0 for n in nums):
                raise ValueError('Barras precisam de pelo menos duas quantidades positivas')
        elif any(linha['quantidade'] is not None for linha in linhas):
            raise ValueError('Quantidade é exclusiva do gráfico de barras')
    palavras = sum(len(fala.split()) for cena in cenas for fala in cena['falas'])
    if len(fontes) < 2:
        raise ValueError(f'Pauta com {len(fontes)} autoridade(s); mínimo de duas independentes')
    if not 68 <= palavras <= 175:
        raise ValueError(f'Narração com {palavras} palavras; faixa admitida de 68 a 175')
    return cenas


@lru_cache(maxsize=48)
def fonte(tamanho, peso=700):
    return ImageFont.truetype(str(ASSETS / ('Inter_700Bold.ttf' if peso == 700 else 'Inter_900Black.ttf')), tamanho)


def texto(d, x, y, valor, tamanho, cor=PAPER, peso=700):
    d.text((x, y), valor, font=fonte(tamanho, peso), fill=cor, anchor='lt')


def quebrar(frase, tamanho, largura, peso=700):
    linhas = ['']
    for palavra in frase.split():
        nova = f'{linhas[-1]} {palavra}'.strip()
        if linhas[-1] and fonte(tamanho, peso).getlength(nova) > largura:
            linhas.append(palavra)
        else:
            linhas[-1] = nova
    return linhas


def bloco(d, x, y, frase, tamanho, largura, cor=PAPER, peso=700, limite=2):
    linhas = quebrar(frase, tamanho, largura, peso)
    while len(linhas) > limite or any(fonte(tamanho, peso).getlength(l) > largura for l in linhas):
        tamanho -= 2
        if tamanho < 19:
            raise ValueError(f'Texto excede área segura: {frase}')
        linhas = quebrar(frase, tamanho, largura, peso)
    for i, linha in enumerate(linhas):
        texto(d, x, y + i * int(tamanho * 1.07), linha, tamanho, cor, peso)


def caixa(d, xy, cor='#122523', borda='#3D5750', raio=15):
    d.rounded_rectangle(xy, raio, fill=cor, outline=borda, width=2)


def animar(seg, atraso=0, duracao=.48):
    return 1 - (1 - min(1, max(0, (seg - atraso) / duracao))) ** 3


@lru_cache(maxsize=1)
def fundo():
    img = Image.new('RGB', (W, H), INK)
    d = ImageDraw.Draw(img)
    for x in range(45, 673, 24):
        for y in range(146, 1020, 24):
            d.point((x, y), fill='#3F6358')
    return img


@lru_cache(maxsize=1)
def mapa():
    pts = json.loads((ASSETS / 'mt.json').read_text())['features'][0]['geometry']['coordinates'][0]
    x0, x1 = min(x for x, y in pts), max(x for x, y in pts)
    y0, y1 = min(y for x, y in pts), max(y for x, y in pts)
    escala = min(415 / (x1 - x0), 315 / (y1 - y0))
    return [(342 + (x-(x0+x1)/2)*escala, 517 + ((y0+y1)/2-y)*escala) for x, y in pts]


@lru_cache(maxsize=1)
def abertura():
    raw = subprocess.check_output([
        'ffmpeg', '-v', 'error', '-i', str(ASSETS / 'abertura.mp4'), '-an',
        '-vf', 'fps=8,scale=720:665:force_original_aspect_ratio=increase,crop=720:665',
        '-t', '7', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-',
    ])
    stride = 720 * 665 * 3
    escuro = Image.new('RGB', (720, 665), INK)
    return [Image.blend(Image.frombytes('RGB', escuro.size, raw[i:i+stride]), escuro, .42)
            for i in range(0, len(raw), stride)]


def quadro(cena, dia, indice, total_cenas, fala, tempo, progresso):
    tipo = cena['tipo']
    cor = ACCENTS[tipo]
    im = fundo().copy()
    if tipo == 'gancho':
        frames = abertura()
        if not frames:
            raise ValueError('Abertura ilustrativa sem quadros')
        im.paste(frames[min(len(frames) - 1, int(tempo * 8))], (0, 150))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 139), fill=INK)
    caixa(d, (47, 53, 82, 88), LIME, None, 8)
    d.line((52, 73, 58, 73, 62, 66, 67, 81, 75, 71), fill=INK, width=3)
    texto(d, 94, 58, 'PULSO NEWS', 26, PAPER, 900)
    texto(d, 464, 62, 'DOMINGO  /  ' + dia.strftime('%d.%m'), 20, MUTED)
    for i in range(total_cenas):
        x = 47 + i * (600 // total_cenas)
        d.rectangle((x, 114, x + 600 // total_cenas - 5, 118),
                    fill=cor if i <= indice else '#355048')

    if tipo == 'gancho':
        caixa(d, (44, 255, 647, 650), '#0B1A17', '#52786B', 20)
        bloco(d, 70, 287, cena['secao'], 23, 525, cor, limite=1)
        bloco(d, 66, 342, cena['titulo'], 76, 554, PAPER, 900, 3)
        texto(d, 70, 607, 'EDIÇÃO SEMANAL  ·  MATO GROSSO', 19, MUTED)
        texto(d, 47, 828, 'Imagem ilustrativa', 18, MUTED)
        if cena['linhas']:
            caixa(d, (44, 872, 648, 970), '#132922', cor)
            bloco(d, 67, 897, cena['linhas'][0]['valor'], 35, 550, cor, 900)
    else:
        bloco(d, 47, 169, cena['secao'], 24, 578, cor, limite=1)
        bloco(d, 45, 220, cena['titulo'], 62, 605, PAPER, 900)
        if tipo == 'mapa' and fala > 0:
            for j, linha in enumerate(cena['linhas']):
                y = 371 + j * 151
                caixa(d, (45, y, 622, y + 133), '#112C2D', cor)
                bloco(d, 67, y+18, linha['rotulo'], 23, 530, MUTED)
                bloco(d, 64, y+50, linha['valor'], 57, 530, cor, 900)
        elif tipo == 'mapa':
            caixa(d, (45, 368, 622, 692), '#102523')
            pts = mapa()
            d.polygon(pts, fill='#214440')
            d.line(pts + [pts[0]], fill=cor, width=2)
            for x in range(64, 635, 37):
                d.point((x, 522), fill='#587B70')
            texto(d, 65, 389, 'MATO GROSSO', 22, cor)
            texto(d, 65, 656, 'Contorno IBGE · sem recorte por município', 17, MUTED)
            largura = 576 // len(cena['linhas'])
            for j, linha in enumerate(cena['linhas']):
                x = 46 + j * largura
                caixa(d, (x, 718, x + largura - 8, 838), '#152E2E')
                bloco(d, x + 13, 741, linha['rotulo'], 20, largura - 32, MUTED)
                bloco(d, x + 13, 779, linha['valor'], 35, largura - 32, cor, 900)
        elif tipo == 'barras' and fala > 0 and fala == len(cena['falas']) - 1 and cena.get('virada'):
            caixa(d, (45, 382, 622, 725), '#102721', cor, 20)
            texto(d, 68, 421, 'NA SUA PRAÇA', 23, cor)
            bloco(d, 65, 480, cena['virada'], 70, 530, PAPER, 900, 3)
        elif tipo == 'barras':
            teto = max(l['quantidade'] for l in cena['linhas'])
            passo = 146 if len(cena['linhas']) == 3 else 184
            for j, linha in enumerate(cena['linhas']):
                y = 380 + passo * j
                caixa(d, (45, y, 647, y + passo - 14))
                bloco(d, 65, y + 19, linha['rotulo'], 23, 540, MUTED)
                bloco(d, 64, y + 53, linha['valor'], 49, 540, cor, 900)
                d.rectangle((65, y+113, 613, y+122), fill='#36544C')
                fim = 65 + int(548 * linha['quantidade']/teto * animar(tempo, .13*j, .85))
                d.rectangle((65, y+113, fim, y+122), fill=cor)
            texto(d, 48, 825, 'Barras com origem em zero', 18, MUTED)
        else:
            for j, linha in enumerate(cena['linhas']):
                n = animar(tempo, .23 * j)
                y = 382 + j * 147 + int(28 * (1 - n))
                caixa(d, (45, y, 647, y + 123), '#122523', cor if j == min(fala, len(cena['linhas'])-1) else '#3D5750')
                bloco(d, 66, y + 19, linha['rotulo'], 23, 540, cor)
                bloco(d, 65, y + 56, linha['valor'], 36, 540, PAPER, 900)
        bloco(d, 47, 886, cena['nota'], 24, 596, PAPER)
        if cena['fonte']:
            data = date.fromisoformat(cena['data_fonte']).strftime('%d/%m/%Y')
            bloco(d, 47, 940, f"{cena['fonte']}  ·  {data}", 20, 598, MUTED)
    caixa(d, (44, 997, 621, 1090), '#0A1714', '#39544C')
    legenda = cena['falas'][fala]
    bloco(d, 66, 1014, legenda, 28, 527, PAPER, 700, 2)
    d.rectangle((46, 1110, 621, 1114), fill='#39544C')
    d.rectangle((46, 1110, 46 + round(575 * progresso), 1114), fill=cor)
    return im


def rodar(cmd, **kwargs):
    return subprocess.run(cmd, check=True, **kwargs)


def segundos(arq):
    saida = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                     '-of', 'csv=p=0', str(arq)], text=True)
    return float(saida.strip())


def sintetizar(cenas, tmp):
    roteiro = tmp / 'roteiro.json'
    roteiro.write_text(json.dumps([[c['titulo'], fala, {}] for c in cenas for fala in c['falas']],
                                  ensure_ascii=False), encoding='utf-8')
    audio = tmp / 'audio'
    env = {**os.environ, 'TMPDIR': str(tmp)}
    # O acesso oficial, quando já provisionado, fica no caminho canônico; sem nova credencial.
    modelo = 'kokoro-82m'
    if os.environ.get('ELEVENLABS_API_KEY'):
        oficial = subprocess.run([str(VOZ / 'venv/bin/python'), str(AUDIO / 'voz_elevenlabs.py'),
                                  str(audio), str(HOME / '.cache/pulso-news/elevenlabs'), str(roteiro)],
                                 env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if oficial.returncode == 0:
            modelo = 'ElevenLabs · voz oficial'
    if modelo == 'kokoro-82m':
        rodar([str(VOZ / 'venv/bin/python'), str(AUDIO / 'voz_kokoro.py'), str(audio),
               str(VOZ / 'modelo'), str(roteiro)], env=env)
    return sorted((audio / 'segs').glob('seg_*.wav')), modelo


def hash_pauta(pauta):
    canonica = json.dumps(pauta, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(canonica.encode()).hexdigest()


def hash_arquivo(caminho):
    with caminho.open('rb') as arq:
        return hashlib.file_digest(arq, 'sha256').hexdigest()


def gerar(pauta, dia, destino):
    cenas = verificar(pauta, dia)
    destino.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='render-', dir=destino) as nome:
        tmp = Path(nome)
        arquivos, voz = sintetizar(cenas, tmp)
        if len(arquivos) != sum(len(c['falas']) for c in cenas):
            raise ValueError('Número de segmentos de áudio divergente')
        # Leve aceleração apenas se o teto for excedido. Pausas iguais para legendas e áudio.
        medidas = [segundos(a) for a in arquivos]
        velocidade = max(1.0, sum(medidas) / (56 - .16*len(medidas)))
        if velocidade > 1.22 or sum(medidas) < 31:
            raise ValueError('A narração exige reescrita antes do render')
        duracoes = [math.ceil((s / velocidade + .16) * FPS) for s in medidas]
        total = sum(duracoes)
        lista = []
        for i, (arq, n) in enumerate(zip(arquivos, duracoes)):
            seg = tmp / f'a{i}.wav'
            rodar(['ffmpeg', '-v', 'error', '-i', str(arq), '-af',
                   f'atempo={velocidade:.6f},apad', '-t', str(n/FPS),
                   '-ar', '48000', '-ac', '1', str(seg)])
            lista.append(f"file '{seg.name}'")
        (tmp / 'concat.txt').write_text('\n'.join(lista) + '\n', encoding='utf-8')
        candidato = tmp / 'pulso-semanal.mp4'
        cmd = ['ffmpeg', '-v', 'error', '-f', 'rawvideo', '-pixel_format', 'rgb24', '-video_size',
               f'{W}x{H}', '-framerate', str(FPS), '-i', '-', '-f', 'concat', '-safe', '1',
               '-i', str(tmp / 'concat.txt'), '-vf', 'scale=1080:1920:flags=lanczos',
               '-af', 'loudnorm=I=-16:TP=-1.5:LRA=7', '-c:v', 'libx264', '-preset', 'veryfast',
               '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-ar', '48000', '-b:a', '128k',
               '-movflags', '+faststart', '-shortest', str(candidato)]
        indice = global_frame = 0
        with subprocess.Popen(cmd, stdin=subprocess.PIPE) as proc:
            for ci, cena in enumerate(cenas):
                local = 0
                for fi in range(len(cena['falas'])):
                    n = duracoes[indice]
                    for _ in range(n):
                        im = quadro(cena, dia, ci, len(cenas), fi, local/FPS, global_frame/total)
                        if global_frame == 15:
                            im.resize((1080, 1920), Image.Resampling.LANCZOS).save(tmp / 'capa.jpg', quality=94)
                        proc.stdin.write(im.tobytes())
                        global_frame += 1
                        local += 1
                    indice += 1
            proc.stdin.close()
            if proc.wait():
                raise RuntimeError('FFmpeg retornou erro ao renderizar')
        rodar(['ffmpeg', '-v', 'error', '-xerror', '-i', str(candidato), '-f', 'null', '-'])
        prova = json.loads(subprocess.check_output(
            ['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_name,width,height:format=duration',
             '-of', 'json', str(candidato)], text=True))
        formatos = [(s['codec_name'], s.get('width'), s.get('height')) for s in prova['streams']]
        duracao = float(prova['format']['duration'])
        if formatos != [('h264', 1080, 1920), ('aac', None, None)] or not 31 <= duracao <= 58:
            raise ValueError('Gates de formato ou duração falharam')
        sha = hash_arquivo(candidato)
        manifesto = {'data': dia.isoformat(), 'estado': 'candidato_nao_publicado',
                     'voz': voz, 'sha256': sha, 'duracao_seg': duracao,
                     'pauta_sha256': hash_pauta(pauta), 'capa_sha256': hash_arquivo(tmp / 'capa.jpg'),
                     'checagens': ['estrutura', 'datas de fonte', 'formato', 'decodificação integral']}
        (tmp / 'manifesto.json').write_text(json.dumps(manifesto, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        for nome in ['pulso-semanal.mp4', 'capa.jpg', 'manifesto.json']:
            (tmp / nome).replace(destino / nome)
        print(f'PRONTO {destino / "pulso-semanal.mp4"} ({duracao:.2f}s; {voz}; {sha})', flush=True)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('pauta', type=Path)
    cli.add_argument('--data', type=date.fromisoformat, required=True)
    cli.add_argument('--saida', type=Path, required=True)
    cli.add_argument('--validar', action='store_true')
    args = cli.parse_args()
    pauta = json.loads(args.pauta.read_text(encoding='utf-8'))
    if args.validar:
        verificar(pauta, args.data)
        print('Estrutura e datas verificadas')
    else:
        gerar(pauta, args.data, args.saida)


if __name__ == '__main__':
    main()
