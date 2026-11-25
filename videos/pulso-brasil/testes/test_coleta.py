import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]


def carregar(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, ROOT / caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


coleta = carregar('coletar_dados', 'diario/coletar_dados.py')
acervo = carregar('baixar_acervo', 'assets/baixar_acervo.py')
publicado = carregar('ja_publicado', 'diario/ja_publicado.py')
historico = carregar('registrar_historico', 'diario/registrar_historico.py')
conferir = carregar('conferir_episodio', 'diario/conferir_episodio.py')

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
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        # A pasta do dia (onde o modelo escreve) e a trava (fora dela) são irmãs, nunca pai e filha.
        self.pasta, self.trava = Path(tmp.name) / 'dia', Path(tmp.name) / 'trava' / 'coleta.sha256'
        self.pasta.mkdir()
        env = mock.patch.dict('os.environ', {'SUPABASE_SERVICE_ROLE_KEY': 'chave-falsa'})
        env.start()
        self.addCleanup(env.stop)

    def coletar(self, dia='2026-11-24', **kw):
        with mock.patch.object(coleta, 'baixar', falso(**kw)):
            return coleta.main([str(self.pasta), dia, '--trava', str(self.trava)])

    def conferir(self):
        return coleta.main(['--conferir', str(self.pasta), '--trava', str(self.trava)])

    def test_grava_fontes_no_formato_do_molde_e_a_trava_fora_da_pasta(self):
        self.assertEqual(self.coletar(), 0)
        imea = json.loads((self.pasta / 'fontes/pulso-imea.json').read_text())
        self.assertEqual(imea['imea_mt']['soja'], {'2026-11-16': 136.51, '2026-11-23': 138.66})
        self.assertEqual(imea['pracas_soja_2026-11-23'], {'Rondonópolis': 145.5})
        self.assertEqual(len(imea['sql']), 2)
        self.assertIn('public.mercado_quotes', (self.pasta / 'fontes/pulso-imea.sql').read_text())
        self.assertEqual(len(self.trava.read_text().splitlines()), 3)
        self.assertFalse(any('coleta.sha256' in p.name for p in self.pasta.rglob('*')))
        todo = ''.join(p.read_text() for p in list(self.pasta.rglob('*.json')) + [self.trava])
        self.assertNotIn('chave-falsa', todo)

    def test_conferir_aceita_o_que_a_coleta_gravou(self):
        self.coletar()
        self.assertEqual(self.conferir(), 0)

    def test_conferir_pega_fonte_alterada_ou_removida(self):
        self.coletar()
        alvo = self.pasta / 'fontes/pulso-imea.json'
        original = alvo.read_text()
        alvo.write_text('{}')
        with self.assertRaisesRegex(RuntimeError, 'mudou depois da coleta'):
            self.conferir()
        alvo.unlink()
        with self.assertRaisesRegex(RuntimeError, 'sumiu depois da coleta'):
            self.conferir()
        alvo.write_text(original)
        self.assertEqual(self.conferir(), 0)

    def test_conferir_pega_arquivo_novo_do_modelo_em_fontes(self):
        self.coletar()
        (self.pasta / 'fontes/snapshot-inventado.html').write_text('<p>5,99</p>')
        with self.assertRaisesRegex(RuntimeError, 'arquivo novo em fontes/.*snapshot-inventado'):
            self.conferir()

    def test_conferir_pega_arquivo_novo_em_subpasta_e_link_simbolico(self):
        self.coletar()
        (self.pasta / 'fontes/extra').mkdir()
        (self.pasta / 'fontes/extra/a.json').write_text('{}')
        with self.assertRaisesRegex(RuntimeError, 'arquivo novo em fontes/'):
            self.conferir()
        (self.pasta / 'fontes/extra/a.json').unlink()
        (self.pasta / 'fontes/ptax-link.json').symlink_to(self.pasta / 'fontes/bcb-ptax.json')
        with self.assertRaisesRegex(RuntimeError, 'link simbólico'):
            self.conferir()

    def test_modelo_nao_consegue_refazer_a_trava_dentro_da_pasta(self):
        with self.assertRaisesRegex(RuntimeError, 'fora da pasta do dia'):
            coleta.main([str(self.pasta), '2026-11-24', '--trava', str(self.pasta / 'coleta.sha256')])
        with self.assertRaisesRegex(RuntimeError, 'falta --trava'):
            coleta.main([str(self.pasta), '2026-11-24'])

    def test_coleta_nova_recusa_sobra_de_execucao_anterior_em_fontes(self):
        (self.pasta / 'fontes').mkdir()
        (self.pasta / 'fontes/sobra.json').write_text('{}')
        with self.assertRaisesRegex(RuntimeError, 'fontes/ já tem arquivo que não é da coleta'):
            self.coletar()

    def test_imea_velho_ou_ausente_vira_sem_episodio_codigo_3(self):
        for imea_ate in ('2026-11-18', None):
            self.assertEqual(self.coletar(imea_ate=imea_ate), 3)
            self.assertTrue((self.pasta / 'sem-episodio.txt').is_file())
            (self.pasta / 'sem-episodio.txt').unlink()
        self.assertFalse(self.trava.exists())

    def test_sem_chave_falha(self):
        with mock.patch.dict('os.environ', {'SUPABASE_SERVICE_ROLE_KEY': ''}):
            self.assertEqual(coleta.main([str(self.pasta), '2026-11-24', '--trava', str(self.trava)]), 1)


class Resposta:
    def __init__(self, dados):
        self.dados = dados

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, _n=-1):
        dados, self.dados = self.dados, b''
        return dados


class Acervo(unittest.TestCase):
    ITEM = {'origem': 'a/b/clipe.mp4', 'sha256': hashlib.sha256(b'clipe').hexdigest()}

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


class JaPublicado(unittest.TestCase):
    def test_consulta_so_o_dia_e_o_status_publicado_e_devolve_os_ids(self):
        pedidos = []

        def abrir(pedido, timeout):
            pedidos.append(pedido)
            return Resposta(json.dumps([{'id': 'pulso-news-2026-11-24', 'status': 'publicado'}]).encode())

        ids = publicado.publicados_no_dia('2026-11-24', 'https://x.test', 'chave-falsa', abrir)
        self.assertEqual(ids, ['pulso-news-2026-11-24'])
        self.assertIn('publicado_em=eq.2026-11-24', pedidos[0].full_url)
        self.assertIn('status=eq.publicado', pedidos[0].full_url)

    def test_codigos_de_saida_0_10_e_erro(self):
        env = {'SUPABASE_SERVICE_ROLE_KEY': 'k', 'SUPABASE_URL': 'https://x.test'}
        with mock.patch.dict('os.environ', env):
            with mock.patch.object(publicado, 'publicados_no_dia', return_value=[]):
                self.assertEqual(publicado.main(['2026-11-24']), 0)
            with mock.patch.object(publicado, 'publicados_no_dia', return_value=['x']):
                self.assertEqual(publicado.main(['2026-11-24']), 10)
        with mock.patch.dict('os.environ', {'SUPABASE_SERVICE_ROLE_KEY': ''}), self.assertRaises(RuntimeError):
            publicado.main(['2026-11-24'])

    def test_id_que_ja_existe_em_qualquer_status_e_recusado_com_codigo_11(self):
        env = {'SUPABASE_SERVICE_ROLE_KEY': 'k', 'SUPABASE_URL': 'https://x.test'}
        with mock.patch.dict('os.environ', env), mock.patch.object(publicado, 'publicados_no_dia', return_value=[]):
            with mock.patch.object(publicado, 'status_do_id', return_value='rascunho') as consulta:
                self.assertEqual(publicado.main(['2026-11-24', 'pulso-brasil-2026-11-24-x']), 11)
                consulta.assert_called_once()
            with mock.patch.object(publicado, 'status_do_id', return_value=None):
                self.assertEqual(publicado.main(['2026-11-24', 'pulso-brasil-2026-11-24-x']), 0)
            # dia já publicado vence: pula sem olhar o id
            with mock.patch.object(publicado, 'publicados_no_dia', return_value=['a']), \
                    mock.patch.object(publicado, 'status_do_id') as consulta:
                self.assertEqual(publicado.main(['2026-11-24', 'pulso-brasil-2026-11-24-x']), 10)
                consulta.assert_not_called()

    def test_consulta_por_id_filtra_pelo_id_e_recusa_id_com_lixo(self):
        pedidos = []

        def abrir(pedido, timeout):
            pedidos.append(pedido.full_url)
            return Resposta(json.dumps([{'id': 'pulso-brasil-2026-11-24-x', 'status': 'retirado'}]).encode())

        self.assertEqual(publicado.status_do_id('pulso-brasil-2026-11-24-x', 'https://x.test', 'k', abrir), 'retirado')
        self.assertIn('id=eq.pulso-brasil-2026-11-24-x', pedidos[0])
        for ruim in ('x&status=eq.publicado', 'A B', '', 'a' * 81, 'pulso-brasil-2026-11-24-x\n'):
            with self.assertRaisesRegex(ValueError, 'id inválido'):
                publicado.status_do_id(ruim, 'https://x.test', 'k', abrir)
        self.assertEqual(len(pedidos), 1)

    def test_erro_do_catalogo_nao_vaza_cabecalho_e_nao_autoriza_publicar(self):
        def abrir(pedido, timeout):
            raise HTTPError(pedido.full_url, 401, 'sem acesso', {}, None)

        with self.assertRaisesRegex(RuntimeError, 'HTTP 401') as ctx:
            publicado.publicados_no_dia('2026-11-24', 'https://x.test', 'chave-falsa', abrir)
        self.assertNotIn('chave-falsa', str(ctx.exception))


class Historico(unittest.TestCase):
    EP = {'data': '2026-11-24', 'pauta_id': 'dolar-soja', 'tema': 'Dólar e soja', 'titulo': 'T',
          'numeros_chave': [{'numero': 5.85, 'fonte': 'PTAX', 'data': '2026-11-24'}], 'outro': 'x'}

    def arquivos(self, tmp, conteudo):
        ep, h = Path(tmp) / 'ep.json', Path(tmp) / 'historico.jsonl'
        ep.write_text(json.dumps(self.EP))
        h.write_text(conteudo)
        return ep, h

    def test_anexa_uma_vez_e_so_os_campos_do_historico(self):
        with tempfile.TemporaryDirectory() as tmp:
            ep, h = self.arquivos(tmp, '{"data":"2026-11-23","pauta_id":"x","tema":"X"}')  # sem \n final
            self.assertTrue(historico.registrar(ep, h, '2026-11-24'))
            self.assertFalse(historico.registrar(ep, h, '2026-11-24'))
            linhas = h.read_text().splitlines()
            self.assertEqual(len(linhas), 2)
            self.assertNotIn('outro', json.loads(linhas[1]))
            self.assertEqual(json.loads(linhas[1])['data'], '2026-11-24')
            self.assertEqual(json.loads(linhas[1])['numeros_chave'][0]['numero'], 5.85)

    def test_episodio_de_outro_dia_nao_entra_no_historico(self):
        with tempfile.TemporaryDirectory() as tmp:
            ep, h = self.arquivos(tmp, '')
            with self.assertRaisesRegex(ValueError, 'não do dia 2026-11-25'):
                historico.registrar(ep, h, '2026-11-25')
            self.assertEqual(h.read_text(), '')

    def test_tem_o_dia(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, h = self.arquivos(tmp, '{"data":"2026-11-23","pauta_id":"x","tema":"X"}\n\n')
            self.assertTrue(historico.tem_o_dia('2026-11-23', h))
            self.assertFalse(historico.tem_o_dia('2026-11-24', h))


class ConferirEpisodio(unittest.TestCase):
    def pasta(self, tmp, episodio_data='2026-11-24', dossie_data='2026-11-24', dossie_ep='pulso-brasil-2026-11-24-dolar-soja',
              ep=None):
        p = Path(tmp)
        (p / 'episodio.json').write_text(json.dumps({'data': episodio_data}))
        (p / 'dossie.json').write_text(json.dumps({'data': dossie_data, 'episodio': dossie_ep}))
        if ep is not None:
            (p / 'out').mkdir()
            (p / 'out/ep.json').write_text(json.dumps(ep))
        return p

    EP_OK = {'id': 'pulso-brasil-2026-11-24-dolar-soja', 'publicado_em': '2026-11-24'}

    def test_aceita_episodio_do_dia_e_o_exemplo_do_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(conferir.conferir('2026-11-24', self.pasta(tmp, ep=self.EP_OK), exigir_ep=True),
                             'pulso-brasil-2026-11-24-dolar-soja')
        self.assertEqual(conferir.conferir('2026-11-24', ROOT / 'exemplos/2026-11-24-dolar-soja'),
                         'pulso-brasil-2026-11-24-dolar-soja')

    def test_reprova_data_de_outro_dia_no_episodio_ou_no_dossie(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, r'episodio.json data .2026-11-23. diferente'):
                conferir.conferir('2026-11-24', self.pasta(tmp, episodio_data='2026-11-23'))
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, r'dossie.json data'):
                conferir.conferir('2026-11-24', self.pasta(tmp, dossie_data='2026-11-25'))

    def test_reprova_id_do_dossie_de_outro_dia_ou_fora_do_formato(self):
        for ruim in ('pulso-brasil-2026-11-23-dolar', 'pulso-news-2026-11-24', 'pulso-brasil-2026-11-24-', 'Pulso-Brasil-2026-11-24',
                     'pulso-brasil-2026-11-24-' + 'a' * 60, 'pulso-brasil-2026-11-24-dolar\n', None):
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaisesRegex(ValueError, 'dossie.json episodio'):
                    conferir.conferir('2026-11-24', self.pasta(tmp, dossie_ep=ruim))

    def test_id_so_com_a_data_e_aceito(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(conferir.conferir('2026-11-24', self.pasta(tmp, dossie_ep='pulso-brasil-2026-11-24')),
                             'pulso-brasil-2026-11-24')

    def test_reprova_meta_do_publicar_que_diverge(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = self.pasta(tmp, ep={'id': 'pulso-brasil-2026-11-24-outro', 'publicado_em': '2026-11-24'})
            with self.assertRaisesRegex(ValueError, 'ep.json id .* diferente de dossie.json episodio'):
                conferir.conferir('2026-11-24', pasta, exigir_ep=True)
        with tempfile.TemporaryDirectory() as tmp:
            pasta = self.pasta(tmp, ep={**self.EP_OK, 'publicado_em': '2026-11-23'})
            with self.assertRaisesRegex(ValueError, 'ep.json publicado_em'):
                conferir.conferir('2026-11-24', pasta, exigir_ep=True)
        with tempfile.TemporaryDirectory() as tmp:  # --ep sem o arquivo = erro, não aprovação
            with self.assertRaises(OSError):
                conferir.conferir('2026-11-24', self.pasta(tmp), exigir_ep=True)


class Redigir(unittest.TestCase):
    def redigir(self, texto):
        import subprocess
        return subprocess.run(['bash', str(ROOT / 'diario/redigir.sh')], input=texto, capture_output=True, text=True, check=True).stdout

    def test_tira_o_que_tem_cara_de_chave_e_deixa_o_resto(self):
        falsos = ['eyJ' + 'a' * 40 + '.' + 'b' * 20, 'sk-ant-api03-' + 'c' * 30, 'sk_' + 'd' * 32, 'sb_secret_' + 'e' * 24,
                  'github_pat_' + 'f' * 30, 'ghs_' + 'g' * 30]
        saida = self.redigir('G3 aprovado: WER 0,07\n' + '\n'.join(f'chave {f} fim' for f in falsos) +
                             '\nAuthorization: Bearer ' + 'h' * 30 + '\nxi-api-key: ' + 'i' * 30 + '\napikey=' + 'j' * 30 + '\n')
        for f in falsos + ['h' * 30, 'i' * 30, 'j' * 30]:
            self.assertNotIn(f, saida)
        self.assertIn('G3 aprovado: WER 0,07', saida)
        self.assertGreaterEqual(saida.count('[redigido]'), 9)


if __name__ == '__main__':
    unittest.main()
