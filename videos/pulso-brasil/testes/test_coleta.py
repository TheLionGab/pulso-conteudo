import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from urllib.error import HTTPError, URLError

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


FONTE_OK = {'source_name': 'Fonte', 'can_be_named': True, 'active': True, 'default_trust_class': 'BENCHMARK'}


def linha_oferta(oferta_id, valor, instante, **extra):
    meta = {'series': 'gd_oferta', 'ref_date': '2026-11-23'}
    if oferta_id:
        meta['oferta_id'] = oferta_id
    return {'commodity': 'soja', 'observed_at': f'2026-11-23T{instante}+00:00', 'received_at': f'2026-11-23T{instante}+00:00',
            'value': valor, 'unit': 'R$/sc', 'metadata': meta, 'market_sources': dict(FONTE_OK, **extra),
            'market_locations': {'municipality': 'Sorriso', 'uf': 'MT'}}


def completo(**kw):
    """Banco com todas as fontes opcionais. O que vier em kw vai para falso() (PTAX e IMEA)."""
    obrigatorias = falso(**kw)

    def baixar(url, cabecalhos=None, **resto):
        cab = cabecalhos or {}
        if 'apiprevmet3.inmet.gov.br' in url:
            return json.dumps({'hoje': [{'id': 77, 'descricao': 'Tempestade', 'id_severidade': 7, 'data_inicio': '2026-11-24',
                                         'data_fim': '2026-11-25', 'geocodes': '5102678,5107602,3550308'}],
                               'futuro': [{'id': 78, 'descricao': 'Onda de calor', 'id_severidade': 6, 'data_inicio': '2026-11-24',
                                           'data_fim': '2026-11-26', 'geocodes': '3550308'}]}).encode()
        if 'mercado_quotes?select=data_publicacao&papel=in.' in url:
            return json.dumps([{'data_publicacao': '2026-11-16' if 'data_publicacao=lt.' in url else '2026-11-23'}]).encode()
        if 'mercado_quotes?select=cultura,papel' in url:
            if 'data_publicacao=eq.2026-11-16' in url:
                return json.dumps([{'cultura': 'soja', 'papel': 'praca', 'localidade': 'Rondonópolis', 'source': 'imea',
                                    'valor': 143.0, 'unidade': 'R$/sc', 'data_publicacao': '2026-11-16'}]).encode()
            pracas = [('Rondonópolis', 145.5), ('Sorriso', 136.0), ('Sapezal', 139.0)]
            linhas = [{'cultura': 'soja', 'papel': 'praca', 'localidade': l, 'source': 'imea', 'valor': v, 'unidade': 'R$/sc',
                       'data_publicacao': '2026-11-23'} for l, v in pracas]
            linhas.append({'cultura': 'milho', 'papel': 'imea', 'localidade': 'Mato Grosso', 'source': 'imea', 'valor': 46.0,
                           'unidade': 'R$/sc', 'data_publicacao': '2026-11-23'})
            return json.dumps(linhas).encode()
        if 'market_observations' in url:
            assert cab.get('Accept-Profile') == 'mercado'
            if 'series=eq.gd_oferta' in url:
                return json.dumps([
                    linha_oferta('a', 141.0, '15:00:00'), linha_oferta('a', 140.0, '12:00:00'), linha_oferta('b', 143.0, '13:00:00'),
                    linha_oferta(None, 150.0, '14:00:00'),                      # sem oferta_id: não conta
                    linha_oferta('c', 160.0, '14:00:00', can_be_named=False),   # fonte não nomeável: fora
                ]).encode()
            return json.dumps([{'commodity': 'feijao', 'observed_at': '2026-11-21T10:00:00+00:00', 'received_at': '2026-11-21T10:00:00+00:00',
                                'value': 300.0, 'unit': 'R$/sc', 'metadata': {'series': 'deral', 'place': 'Curitiba/PR', 'ref_date': '2026-11-20',
                                                                              'source_label': 'DERAL/SEAB-PR', 'product': 'Carioca'},
                                'market_sources': FONTE_OK, 'market_locations': None}]).encode()
        if 'v_insumos_precos_vigentes' in url:
            assert cab.get('Accept-Profile') == 'cotacoes'
            return json.dumps([{'slug': 'ureia', 'nome': 'Ureia', 'categoria': 'fertilizante', 'localidade': 'MT', 'valor': 3500.0,
                                'unidade': 'R$/t', 'variacao_pct': 4.2, 'fonte': 'Conab', 'vigente_em': '2026-11-20'}]).encode()
        if 'artigos?select=' in url:
            assert cab.get('Accept-Profile') == 'noticias'
            return json.dumps([
                {'titulo': 'Soja sobe em Sorriso', 'fonte': 'Canal', 'url': 'https://x.test/a', 'publicado_em': '2026-11-24T10:00:00+00:00',
                 'commodities': ['soja'], 'regiao': 'mt'},
                {'titulo': 'Título com "aspas"', 'fonte': 'Canal', 'url': 'https://x.test/b', 'publicado_em': '2026-11-24T09:00:00+00:00'},
                {'titulo': 'Sem link', 'fonte': 'Canal', 'url': 'javascript:1', 'publicado_em': '2026-11-24T08:00:00+00:00'},
            ]).encode()
        return obrigatorias(url, cabecalhos, **resto)
    return baixar


def so_obrigatorias(**kw):
    """Opcionais fora do ar: 404 no banco, lista vazia onde o banco responde vazio, INMET sem rede."""
    obrigatorias = falso(**kw)

    def baixar(url, cabecalhos=None, **resto):
        if 'apiprevmet3.inmet.gov.br' in url:
            raise URLError('sem rede')
        if 'mercado_quotes?select=data_publicacao&papel=in.' in url or 'v_insumos_precos_vigentes' in url:
            raise RuntimeError(f"{url.split('?')[0]}: HTTP 404 relation does not exist")
        if 'market_observations' in url or 'artigos?select=' in url or 'mercado_quotes?select=cultura' in url:
            return b'[]'
        return obrigatorias(url, cabecalhos, **resto)
    return baixar


class FontesOpcionais(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.pasta, self.trava = Path(tmp.name) / 'dia', Path(tmp.name) / 'trava' / 'coleta.sha256'
        self.pasta.mkdir()
        env = mock.patch.dict('os.environ', {'SUPABASE_SERVICE_ROLE_KEY': 'chave-falsa'})
        env.start()
        self.addCleanup(env.stop)

    def coletar(self, banco, dia='2026-11-24'):
        with mock.patch.object(coleta, 'baixar', banco):
            return coleta.main([str(self.pasta), dia, '--trava', str(self.trava)])

    def conferir(self):
        return coleta.main(['--conferir', str(self.pasta), '--trava', str(self.trava)])

    def lido(self, rel):
        return json.loads((self.pasta / rel).read_text())

    def test_grava_cada_fonte_com_a_consulta_e_a_trava_cobre_todas(self):
        self.assertEqual(self.coletar(completo()), 0)
        for dados, consulta in coleta.OPCIONAIS.values():
            self.assertTrue((self.pasta / dados).is_file() and (self.pasta / consulta).is_file(), dados)
        self.assertEqual(len(self.trava.read_text().splitlines()), 3 + 2 * len(coleta.OPCIONAIS))
        self.assertEqual(self.conferir(), 0)
        todo = ''.join(p.read_text() for p in self.pasta.rglob('*') if p.is_file()) + self.trava.read_text()
        self.assertNotIn('chave-falsa', todo)

    def test_mercado_traz_todas_as_culturas_o_anterior_e_o_resumo_das_pracas(self):
        self.coletar(completo())
        m = self.lido('fontes/pulso-mercado.json')
        self.assertEqual(m['data'], '2026-11-23')
        self.assertEqual(m['mercado']['milho']['imea']['Mato Grosso']['imea']['valor'], 46.0)
        ron = m['mercado']['soja']['praca']['Rondonópolis']['imea']
        self.assertEqual(ron['anterior'], {'data': '2026-11-16', 'valor': 143.0})
        self.assertNotIn('anterior', m['mercado']['soja']['praca']['Sorriso']['imea'])
        r = m['resumo_pracas']['soja']
        self.assertEqual((r['n_pracas'], r['media'], r['amplitude']), (3, 140.17, 9.5))
        self.assertEqual((r['maior']['localidade'], r['menor']['localidade']), ('Rondonópolis', 'Sorriso'))
        self.assertEqual(ron['distancia_media'], 5.33)
        self.assertNotIn('resumo_pracas', m['mercado'])
        self.assertIn('public.mercado_quotes', (self.pasta / 'fontes/pulso-mercado.sql').read_text())

    def test_referencias_agregam_oferta_sem_comprador_e_respeitam_os_filtros(self):
        self.coletar(completo())
        r = self.lido('fontes/pulso-referencias.json')
        self.assertEqual(r['ofertas_compra']['soja']['Sorriso/MT'],
                         {'unidade': 'R$/sc', 'data': '2026-11-23', 'n_ofertas': 2, 'valor_min': 141.0, 'valor_max': 143.0, 'uf': 'MT'})
        self.assertEqual(r['referencias']['feijao']['Curitiba/PR']['deral|Carioca|R$/sc']['fonte'], 'DERAL/SEAB-PR')
        self.assertFalse(r['truncado'])
        texto = (self.pasta / 'fontes/pulso-referencias.json').read_text()
        self.assertNotIn('oferta_id', texto)
        self.assertIn('Accept-Profile: mercado', (self.pasta / 'fontes/pulso-referencias.sql').read_text())

    def test_insumos_noticias_e_inmet(self):
        self.coletar(completo())
        self.assertEqual(self.lido('fontes/pulso-insumos.json')['insumos']['ureia']['MT']['variacao_pct'], 4.2)
        titulos = [a['titulo'] for a in self.lido('fontes/pulso-noticias.json')['artigos']]
        self.assertEqual(titulos, ['Soja sobe em Sorriso'])  # aspas e link inválido ficam fora
        inmet = self.lido('fontes/inmet-avisos.json')
        self.assertEqual(list(inmet['avisos']), ['77'])  # o aviso 78 não cobre município de MT
        self.assertEqual((inmet['avisos']['77']['municipios_mt'], inmet['municipios_mt_com_aviso']), (2, 2))
        self.assertIn('apiprevmet3.inmet.gov.br', (self.pasta / 'fontes/inmet-avisos.consulta.txt').read_text())

    def test_fonte_opcional_ausente_ou_vazia_nao_derruba_a_coleta(self):
        self.assertEqual(self.coletar(so_obrigatorias()), 0)
        self.assertEqual([p.name for p in sorted((self.pasta / 'fontes').iterdir())], ['bcb-ptax.json', 'pulso-imea.json', 'pulso-imea.sql'])
        self.assertEqual(len(self.trava.read_text().splitlines()), 3)
        self.assertEqual(self.conferir(), 0)

    def test_so_a_fonte_que_falhou_some_e_o_resto_segue(self):
        def sem_insumos(url, cabecalhos=None, **resto):
            if 'v_insumos_precos_vigentes' in url:
                raise RuntimeError('HTTP 500')
            return completo()(url, cabecalhos, **resto)
        self.assertEqual(self.coletar(sem_insumos), 0)
        self.assertFalse((self.pasta / 'fontes/pulso-insumos.json').exists())
        self.assertFalse((self.pasta / 'fontes/pulso-insumos.sql').exists())
        self.assertTrue((self.pasta / 'fontes/pulso-mercado.json').is_file())
        self.assertEqual(len(self.trava.read_text().splitlines()), 3 + 2 * (len(coleta.OPCIONAIS) - 1))

    def test_resposta_no_teto_de_linhas_e_recusada_como_cortada(self):
        def cheia(url, cabecalhos=None, **resto):
            if 'v_insumos_precos_vigentes' in url:
                return json.dumps([{'slug': f'i{n}', 'nome': 'x', 'localidade': 'MT', 'valor': 1, 'unidade': 'R$/t', 'vigente_em': '2026-11-20'}
                                   for n in range(coleta.LIMITE_LINHAS)]).encode()
            return completo()(url, cabecalhos, **resto)
        self.assertEqual(self.coletar(cheia), 0)
        self.assertFalse((self.pasta / 'fontes/pulso-insumos.json').exists())

    def test_opcional_de_execucao_anterior_nao_vira_dado_do_dia(self):
        (self.pasta / 'fontes').mkdir()
        for rel in coleta.OPCIONAIS['insumos']:
            (self.pasta / rel).write_text('velho')
        self.assertEqual(self.coletar(so_obrigatorias()), 0)
        self.assertEqual(len(self.trava.read_text().splitlines()), 3)
        self.assertFalse((self.pasta / 'fontes/pulso-insumos.json').exists())

    def test_trava_pega_opcional_alterado_removido_ou_criado_pelo_modelo(self):
        self.coletar(completo())
        alvo = self.pasta / 'fontes/pulso-insumos.json'
        original = alvo.read_text()
        alvo.write_text('{"insumos": {"ureia": {"MT": {"valor": 1}}}}')
        with self.assertRaisesRegex(RuntimeError, r'pulso-insumos.json mudou depois da coleta'):
            self.conferir()
        alvo.unlink()
        with self.assertRaisesRegex(RuntimeError, r'pulso-insumos.json sumiu depois da coleta'):
            self.conferir()
        alvo.write_text(original)
        self.assertEqual(self.conferir(), 0)

    def test_modelo_nao_cria_fonte_opcional_que_a_coleta_nao_gravou(self):
        self.coletar(so_obrigatorias())
        (self.pasta / 'fontes/pulso-insumos.json').write_text('{"insumos": {}}')
        with self.assertRaisesRegex(RuntimeError, 'arquivo novo em fontes/.*pulso-insumos.json'):
            self.conferir()

    def test_trava_com_nome_desconhecido_ou_par_incompleto_e_recusada(self):
        self.coletar(completo())
        original = self.trava.read_text()
        self.trava.write_text(original + 'a' * 64 + '  fontes/inventado.json\n')
        with self.assertRaisesRegex(RuntimeError, 'trava da coleta incompleta'):
            self.conferir()
        sem_consulta = ''.join(l for l in original.splitlines(True) if 'pulso-insumos.sql' not in l)
        self.trava.write_text(sem_consulta)
        with self.assertRaisesRegex(RuntimeError, 'pela metade'):
            self.conferir()

    def test_ptax_e_imea_continuam_obrigatorios(self):
        self.assertEqual(self.coletar(completo(imea_ate=None)), 3)
        self.assertFalse(self.trava.exists())


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
