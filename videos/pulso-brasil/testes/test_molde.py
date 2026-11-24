import json
from pathlib import Path
import tempfile
import unittest

from assets.integridade import verificar
from audio.roteiro import parse_validado
from episodio import validar
from gates.g_forma import checar as checar_formato
from gates.g_repeticao import checar as checar_repeticao
from gates.g_voz import checar as checar_voz

ROOT = Path(__file__).resolve().parents[1]


class Molde(unittest.TestCase):
    def test_schema_legenda(self):
        with self.assertRaisesRegex(ValueError, 'legenda_instagram'):
            exemplo = json.loads((ROOT / 'exemplos/2026-11-04-soja.json').read_text())
            validar(dict(exemplo, legenda_instagram='  '))

    def test_roteiro(self):
        self.assertEqual(parse_validado('[c] *{2,5%|dois vírgula cinco por cento}*.'), [
            {'exibe': '2,5%.', 'fala': 'dois vírgula cinco por cento.', 'hl': True, 'cues': ['c']},
        ])
        with self.assertRaisesRegex(ValueError, 'marcação'):
            parse_validado('texto {incompleto')

    def test_voz(self):
        canon = {'provedor': 'gemini', 'modelo': 'gemini-3.8-flash-tts', 'voz': 'Sadaltager'}
        self.assertEqual(checar_voz(canon), canon)
        for chave in ('modelo', 'voz'):
            with self.subTest(chave=chave), self.assertRaisesRegex(ValueError, chave):
                checar_voz(dict(canon, **{chave: 'alternativo'}))

    def test_repeticao(self):
        antigo = dict(data='2026-10-28', tema='El Niño', pauta_id='el-nino-out', titulo='Sinal no Pacífico')
        novo = dict(data='2026-11-15', tema=' EL NINO ', pauta_id='el-nino-nov', titulo='Risco de clima')
        self.assertIsNone(checar_repeticao(novo, [antigo]))
        numeros = [{'numero': '12,50', 'fonte': 'Conab', 'data': '2026-11-20'}]
        publicado = dict(data='2026-11-21', tema='Frete de grãos', pauta_id='a', titulo='Frete hoje', numeros_chave=numeros)
        candidato = dict(data='2026-11-23', tema='Custo rodoviário', pauta_id='b', titulo='Outro título',
                         numeros_chave=[dict(numeros[0], numero=12.5)])
        with self.assertRaisesRegex(ValueError, 'número'):
            checar_repeticao(candidato, [publicado])
        with self.assertRaisesRegex(ValueError, 'tema'):
            checar_repeticao(dict(candidato, tema='FRETE DE GRAOS!', numeros_chave=[]), [publicado])

    def test_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            arquivo = Path(tmp) / 'trilha.wav'
            arquivo.write_bytes(b'abc')
            sha = 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
            self.assertEqual(verificar(arquivo, sha), arquivo)
            arquivo.write_bytes(b'alterado')
            with self.assertRaisesRegex(ValueError, 'SHA-256'):
                verificar(arquivo, sha)

    def test_composicao(self):
        root = (ROOT / 'video/src/Root.tsx').read_text()
        self.assertIn('id="PulsoBrasil"', root)
        self.assertEqual(root.count('<Composition'), 1)
        exemplos = sorted((ROOT / 'exemplos').glob('*.json'))
        self.assertEqual(len(exemplos), 2)
        for arquivo in exemplos:
            validar(json.loads(arquivo.read_text()))

    def test_formato(self):
        video = dict(width=1080, height=1920, avg_frame_rate='30/1', r_frame_rate='30/1')
        ep = dict(legenda_instagram='Legenda', cenas=[{'tipo': 'fecho_app'}])
        self.assertEqual(checar_formato(video, 60, -14, -1, ep), [])
        self.assertEqual(len(checar_formato(dict(video, width=720, avg_frame_rate='24/1'), 61, -17, 0,
                                    dict(ep, legenda_instagram=' ', cenas=[]))), 7)
