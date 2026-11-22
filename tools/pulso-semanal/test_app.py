import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import app

PAUTA = json.loads((Path(__file__).with_name('pauta.exemplo.json')).read_text(encoding='utf-8'))
MANIFESTO = {'duracao_seg': 50.87}


class MetaTest(unittest.TestCase):
    def test_meta_respeita_tetos_e_contrato(self):
        meta = app.meta_da_pauta(PAUTA, MANIFESTO)
        self.assertEqual(meta['id'], 'pulso-news-2026-11-22')
        self.assertEqual(meta['duracao_seg'], 51)
        for campo, teto in app.TETOS.items():
            self.assertLessEqual(len(meta[campo]), teto, campo)
        self.assertIn('trigo', meta['culturas'])
        self.assertEqual(len(meta['fontes']), 4)
        self.assertTrue(all(f['url'].startswith('https://') for f in meta['fontes']))

    def test_push_nao_corta_tema_no_meio(self):
        corpo = app.lista('Especial: ', ['um tema bem comprido'] * 9, 60)
        self.assertTrue(corpo.endswith('.'))
        self.assertNotIn('…', corpo)
        self.assertLessEqual(len(corpo), 60)

    def test_sql_escapa_aspas_e_recusa_dia_publicado(self):
        meta = app.meta_da_pauta(PAUTA, MANIFESTO)
        meta['titulo'] = "D'água"
        sql = app.sql_insert(meta, {'video_path': 'a' * 32 + '/video-x.mp4',
                                    'capa_path': 'a' * 32 + '/capa-x.jpg'})
        self.assertIn("'D''água'", sql)
        self.assertIn("where not exists", sql)
        self.assertIn("status='publicado'", sql)


class CliTest(unittest.TestCase):
    def test_formato_inesperado_vira_runtime_error(self):
        saida = mock.Mock(returncode=0, stdout='{"error": "x"}')
        with mock.patch.object(app.subprocess, 'run', return_value=saida):
            with self.assertRaisesRegex(RuntimeError, 'formato inesperado'):
                app.cli(sql='select 1')

    def test_semana_no_app_engole_falha_opcional(self):
        import domingo
        from datetime import date
        with mock.patch.object(domingo, 'cli', side_effect=KeyError('rows')):
            self.assertEqual(domingo.semana_no_app(date(2026, 11, 22)), '')


class PublicarTest(unittest.TestCase):
    def test_recibo_existente_bloqueia_antes_de_rede(self):
        with tempfile.TemporaryDirectory() as pasta:
            ep = Path(pasta)
            (ep / 'publicado.json').write_text('{}')
            with mock.patch.object(app, 'cli') as cli:
                with self.assertRaisesRegex(ValueError, 'Recibo existente'):
                    app.publicar(ep)
                cli.assert_not_called()

    def test_dia_ocupado_nao_envia_midia(self):
        with tempfile.TemporaryDirectory() as pasta:
            ep = Path(pasta)
            meta = app.meta_da_pauta(PAUTA, MANIFESTO)
            with mock.patch.object(app, 'pacote_integro', return_value=({'sha256': 'f' * 64}, PAUTA)), \
                    mock.patch.object(app, 'preparar', return_value=meta), \
                    mock.patch.object(app, 'cli', return_value=[{'id': 'outra', 'status': 'publicado'}]) as cli:
                with self.assertRaisesRegex(ValueError, 'Dia já tem'):
                    app.publicar(ep)
                self.assertEqual(cli.call_count, 1)
            self.assertFalse((ep / 'publicado.json').exists())


if __name__ == '__main__':
    unittest.main()
