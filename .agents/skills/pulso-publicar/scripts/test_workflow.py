import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('workflow', Path(__file__).with_name('workflow.py'))
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


class PublicationTests(unittest.TestCase):
    def test_legenda_unica_e_com_quebras(self):
        text = 'Frete em MT.\n\nBaixe grátis.'
        self.assertEqual(w.caption_check(text, text), {'exact': True, 'once': True})
        self.assertEqual(w.caption_check(text + text, text), {'exact': False, 'once': False})

    def test_estado_instagram_incerto_nunca_reenvia(self):
        self.assertEqual(w.pending({'instagram': {'phase': 'sharing'}, 'app': {}}),
                         ['reconcile_instagram', 'verify_app'])
        self.assertEqual(w.pending({'instagram': {'phase': 'verified'}, 'app': {'phase': 'verified'}}), [])

    def test_sql_idempotente_e_escape_sem_sobrescrever(self):
        meta = {'id': 'pulso-news-2026-11-06', 'titulo': "Preço d'água", 'resumo': 'Histórico.',
                'publicado_em': '2026-11-06', 'duracao_seg': 43, 'culturas': [],
                'push_titulo': 'Frete', 'push_corpo': 'Confira.', 'fontes': [
                    {'nome': 'Conab', 'url': 'https://www.gov.br/conab', 'data': '2026-10-27'}]}
        sql = w.insert_sql(meta, 'a' * 32 + '/video-123.mp4', 'a' * 32 + '/capa-123.jpg')
        self.assertIn("Preço d''água", sql)
        self.assertIn('on conflict(id) do nothing', sql.lower())
        self.assertNotIn('do update', sql.lower())
        self.assertIn("'publicado'", sql)

    def test_caminhos_fora_episodio_e_symlinks_recusados(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'ep'; root.mkdir()
            outside = Path(td) / 'secret'; outside.write_text('not a credential')
            (root / 'link').symlink_to(outside)
            for value in ('../secret', 'link', '/etc/passwd'):
                with self.assertRaises(ValueError): w.inside(root, value)

    def test_hash_midia_alterada_recusa(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / 'out').mkdir()
            (root / 'out/video.mp4').write_bytes(b'original')
            manifest = {'video': {'arquivo': 'out/video.mp4', 'sha256': hashlib.sha256(b'original').hexdigest()},
                        'entradas_sha256': {}}
            w.check_manifest(root, manifest)
            (root / 'out/video.mp4').write_bytes(b'changed')
            with self.assertRaises(ValueError): w.check_manifest(root, manifest)

    def test_registro_sem_hash_correto_nao_e_aprovacao(self):
        h = 'a' * 64
        self.assertTrue(w.review_check('SHA ' + h + '\nAPROVADO\n', h))
        self.assertFalse(w.review_check('SHA ' + h + '\nREPROVADO\n', h))
        self.assertFalse(w.review_check('SHA ' + 'b' * 64 + '\nAPROVADO\n', h))

    def test_recibo_outro_video_nao_confirma_publicacao(self):
        with self.assertRaises(ValueError):
            w.receipt_check({'video_sha256': 'b' * 64}, 'a' * 64)

    def test_legenda_vazia_e_quebras_reais(self):
        self.assertEqual(w.caption_check('', ''), {'exact': False, 'once': False})
        self.assertEqual(w.caption_check('A\n\nB', 'A\n\nB'), {'exact': True, 'once': True})
        self.assertFalse(w.caption_check('A B', 'A\n\nB')['exact'])

    def test_recibo_mesmo_hash_exige_conta_e_permalink_corretos(self):
        receipt = {'video_sha256': 'a' * 64, 'conta': 'pulsodocampo',
                   'reel': 'https://www.instagram.com/pulsodocampo/reel/ABC/',
                   'verificado_em': '2026-11-06T13:34:50Z'}
        self.assertTrue(w.receipt_check(receipt, 'a' * 64))
        for patch in ({'conta': 'outra'}, {'reel': 'https://evil.test/pulsodocampo/reel/ABC/'},
                      {'verificado_em': ''}):
            with self.assertRaises(ValueError): w.receipt_check(receipt | patch, 'a' * 64)

    def test_capa_e_entradas_alteradas_recusadas(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name in ('video.mp4', 'capa.jpg', 'roteiro.md'):
                (root / name).write_bytes(b'original')
            h = hashlib.sha256(b'original').hexdigest()
            manifest = {'video': {'arquivo': 'video.mp4', 'sha256': h},
                        'capa': {'arquivo': 'capa.jpg', 'sha256': h},
                        'entradas_sha256': {'roteiro.md': h}}
            for name in ('capa.jpg', 'roteiro.md'):
                (root / name).write_bytes(b'changed')
                with self.assertRaises(ValueError): w.check_manifest(root, manifest)
                (root / name).write_bytes(b'original')

    def test_journal_nunca_e_promovido_a_recibo(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'out/publicacao').mkdir(parents=True)
            (root / 'qa').mkdir()
            (root / 'out/v.mp4').write_bytes(b'v')
            h = hashlib.sha256(b'v').hexdigest()
            files = {'out/manifesto.json': {'video': {'arquivo': 'out/v.mp4', 'sha256': h},
                                           'entradas_sha256': {}},
                     'out/meta-app.json': {'id': 'pulso-news-2026-11-06'},
                     'out/publicacao/estado.json': {'video_sha256': h,
                                                   'instagram': {'phase': 'verified'},
                                                   'app': {'phase': 'submitted'}}}
            for name, value in files.items(): (root / name).write_text(json.dumps(value))
            (root / 'qa/recibo-critico-publicacao.txt').write_text(h + '\nAPROVADO')
            self.assertEqual(w.plan(root)['pending'], ['reconcile_instagram', 'reconcile_app'])
            files['out/publicacao/estado.json']['video_sha256'] = 'b' * 64
            (root / 'out/publicacao/estado.json').write_text(json.dumps(files['out/publicacao/estado.json']))
            with self.assertRaises(ValueError): w.plan(root)

    def test_nega_aprovacao_negada_e_hash_substring(self):
        h = 'a' * 64
        self.assertFalse(w.review_check(h + '\nNÃO APROVADO', h))
        self.assertFalse(w.review_check('a' + h + '\nAPROVADO', h))

    def test_revisao_legada_e_negacao_multilinha(self):
        h = 'a' * 64
        self.assertTrue(w.review_check('SHA256' + h + '\nAPROVADO', h))
        for negation in ('NÃO\nAPROVADO', 'NAO  APROVADO', 'NÃO\tAPROVADO'):
            self.assertFalse(w.review_check(h + '\n' + negation, h))
        self.assertFalse(w.review_check('SHA256a' + h + '\nAPROVADO', h))

    def test_sql_preserva_barras_e_aspas(self):
        self.assertEqual(w.sql_literal("d'água\\x"), "E'd''água\\\\x'")
        with self.assertRaises(ValueError): w.sql_literal('nulo\x00')


if __name__ == '__main__': unittest.main()
