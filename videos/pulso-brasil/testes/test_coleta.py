import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('coletar_dados', ROOT / 'diario/coletar_dados.py')
coleta = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coleta)

PTAX = json.dumps({'value': [{'cotacaoVenda': 5.7324, 'dataHoraCotacao': '2026-11-16 13:06:32.5'}]}).encode()


def falso(imea_ate='2026-11-23', pracas=True):
    """Responde como o PostgREST: pregão mais recente, semana de soja e milho, praças."""
    def baixar(url, cabecalhos=None, **_):
        if 'olinda.bcb.gov.br' in url:
            return PTAX
        if 'select=data_publicacao&' in url:
            return json.dumps([{'data_publicacao': imea_ate}] if imea_ate else []).encode()
        if 'cultura=in.' in url:
            return json.dumps([
                {'data_publicacao': '2026-11-16', 'cultura': 'milho', 'valor': 45.5},
                {'data_publicacao': '2026-11-16', 'cultura': 'soja', 'valor': 136.51},
                {'data_publicacao': '2026-11-23', 'cultura': 'soja', 'valor': 138.66},
            ]).encode()
        return json.dumps([{'localidade': 'Rondonópolis', 'valor': 145.5}] if pracas else []).encode()
    return baixar


class Coleta(unittest.TestCase):
    def rodar(self, dia='2026-11-24', **kw):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(coleta, 'baixar', falso(**kw)), \
                mock.patch.dict('os.environ', {'SUPABASE_SERVICE_ROLE_KEY': 'chave-falsa'}):
            pasta = Path(tmp)
            codigo = coleta.main([str(pasta), dia])
            return codigo, pasta, {p.name: p.read_text() for p in pasta.rglob('*') if p.is_file()}

    def test_grava_fontes_no_formato_do_molde_e_a_trava(self):
        codigo, _, arquivos = self.rodar()
        self.assertEqual(codigo, 0)
        imea = json.loads(arquivos['pulso-imea.json'])
        self.assertEqual(imea['imea_mt']['soja'], {'2026-11-16': 136.51, '2026-11-23': 138.66})
        self.assertEqual(imea['pracas_soja_2026-11-23'], {'Rondonópolis': 145.5})
        self.assertEqual(len(imea['sql']), 2)
        self.assertIn('public.mercado_quotes', arquivos['pulso-imea.sql'])
        self.assertNotIn('chave-falsa', ''.join(arquivos.values()))
        self.assertEqual(len(arquivos['coleta.sha256'].splitlines()), 3)

    def test_conferir_pega_fonte_alterada(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(coleta, 'baixar', falso()), \
                mock.patch.dict('os.environ', {'SUPABASE_SERVICE_ROLE_KEY': 'k'}):
            pasta = Path(tmp)
            coleta.main([tmp, '2026-11-24'])
            coleta.conferir(pasta)
            (pasta / 'fontes/pulso-imea.json').write_text('{}')
            with self.assertRaisesRegex(RuntimeError, 'mudou depois da coleta'):
                coleta.conferir(pasta)

    def test_imea_velho_ou_ausente_vira_sem_episodio(self):
        for imea_ate in ('2026-11-18', None):
            codigo, _, arquivos = self.rodar(imea_ate=imea_ate)
            self.assertEqual(codigo, 3)
            self.assertIn('sem-episodio.txt', arquivos)

    def test_sem_chave_falha(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict('os.environ', {'SUPABASE_SERVICE_ROLE_KEY': ''}):
            self.assertEqual(coleta.main([tmp, '2026-11-24']), 1)


spec_acervo = importlib.util.spec_from_file_location('baixar_acervo', ROOT / 'assets/baixar_acervo.py')
acervo = importlib.util.module_from_spec(spec_acervo)
spec_acervo.loader.exec_module(acervo)


class Resposta:
    def __init__(self, dados):
        self.dados, self.lido = dados, False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, _n):
        dados, self.dados = self.dados, b''
        return dados


class Acervo(unittest.TestCase):
    ITEM = {'origem': 'a/b/clipe.mp4', 'sha256': __import__('hashlib').sha256(b'clipe').hexdigest()}

    def test_baixa_confere_sha_e_pula_o_que_ja_esta_integro(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(acervo, 'urlopen', return_value=Resposta(b'clipe')) as aberto:
            pasta = Path(tmp)
            self.assertEqual(acervo.baixar_item('https://x.test', 'k', pasta, self.ITEM), 'baixado')
            self.assertEqual((pasta / 'a/b/clipe.mp4').read_bytes(), b'clipe')
            self.assertEqual(acervo.baixar_item('https://x.test', 'k', pasta, self.ITEM), 'cache')
            self.assertEqual(aberto.call_count, 1)
            self.assertEqual(sorted(p.name for p in (pasta / 'a/b').iterdir()), ['clipe.mp4'])

    def test_sha_errado_nao_fica_no_acervo(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(acervo, 'urlopen', side_effect=lambda *a, **k: Resposta(b'outro')), \
                mock.patch.object(acervo.time, 'sleep'):
            with self.assertRaisesRegex(RuntimeError, 'sha256 diferente'):
                acervo.baixar_item('https://x.test', 'k', Path(tmp), self.ITEM)
            self.assertEqual([p for p in Path(tmp).rglob('*') if p.is_file()], [])

    def test_origem_fora_do_acervo_e_recusada(self):
        for origem in ('../fora.mp4', '/etc/x'):
            with self.assertRaisesRegex(ValueError, 'fora do acervo'):
                acervo.destino_seguro(Path('/tmp/a'), origem)


if __name__ == '__main__':
    unittest.main()
