import copy
import json
from pathlib import Path
import unittest
from unittest import mock

import app
import promessa_app as pa

TELAS = pa.carregar_telas()
PAUTA = json.loads((Path(__file__).with_name('pauta.exemplo.json')).read_text(encoding='utf-8'))


class TextoTest(unittest.TestCase):
    def test_passa_previsao_com_tela_existente(self):
        self.assertEqual(pa.checar_texto(
            'Confira a previsão de chuva do seu município no Pulso do Campo.', TELAS), [])

    def test_reprova_aviso_do_municipio_no_app(self):
        achados = pa.checar_texto('Confira o aviso do seu município no Pulso do Campo.', TELAS)
        self.assertEqual(len(achados), 1)
        self.assertIn('promessa proibida', achados[0]['motivo'])
        self.assertIn('aviso do seu município', achados[0]['frase'])

    def test_reprova_aviso_inmet_e_avisos_oficiais(self):
        for frase in ('Veja o aviso do Inmet no app.', 'Abra o app e acompanhe os avisos oficiais.'):
            self.assertEqual(len(pa.checar_texto(frase, TELAS)), 1, frase)

    def test_reprova_aviso_por_cidade_ou_evento(self):
        for frase in ('Receba no app o aviso da sua cidade.',
                      'O Pulso do Campo te notifica com o alerta de geada.',
                      'No app, o aviso da Defesa Civil chega na hora.',
                      'Receba no Pulso do Campo o aviso de tempestade da sua região.'):
            self.assertEqual(len(pa.checar_texto(frase, TELAS)), 1, frase)

    def test_app_como_sujeito_ou_objeto_nao_reprova(self):
        for frase in ('Veja o que o Pulso do Campo apurou hoje.',
                      'Os produtores consultam o Pulso do Campo todo dia.'):
            self.assertEqual(pa.checar_texto(frase, TELAS), [], frase)

    def test_promessa_de_receber_sem_recurso_reprova(self):
        self.assertEqual(len(pa.checar_texto('Receba novidades no app.', TELAS)), 1)

    def test_reprova_tela_inexistente(self):
        sem_clima = TELAS - {'clima.tsx'}
        achados = pa.checar_texto('Veja a previsão de chuva no Pulso do Campo.', sem_clima)
        self.assertEqual(len(achados), 1)
        self.assertIn('tela inexistente', achados[0]['motivo'])
        self.assertIn('clima.tsx', achados[0]['motivo'])

    def test_reprova_recurso_desconhecido(self):
        achados = pa.checar_texto('Veja no Pulso do Campo.', TELAS)
        self.assertEqual(len(achados), 1)

    def test_sem_mencao_ao_app_nao_reprova(self):
        self.assertEqual(pa.checar_texto('Antes de operar, confira o aviso do município.', TELAS), [])

    def test_clima_e_praca_passam(self):
        self.assertEqual(pa.checar_texto(
            'Confira o clima e o preço da sua praça no Pulso do Campo.', TELAS), [])


class FormatosTest(unittest.TestCase):
    def test_pauta_exemplo_passa(self):
        self.assertEqual(pa.checar_pauta(PAUTA, TELAS), [])

    def test_pauta_aviso_em_linha_com_app_na_cena_reprova(self):
        pauta = copy.deepcopy(PAUTA)
        pauta['cenas'][-1]['linhas'] = [{'rotulo': 'CLIMA', 'valor': 'Confira o aviso do município',
                                         'quantidade': None},
                                        {'rotulo': 'ONDE', 'valor': 'Pulso do Campo', 'quantidade': None}]
        achados = pa.checar_pauta(pauta, TELAS)
        self.assertEqual(len(achados), 1)
        self.assertTrue(achados[0]['campo'].endswith('linhas[0]'))

    def test_catalogo_checa_campos_de_texto(self):
        linhas = [{'titulo': 'Ok', 'resumo': 'Soja em MT.',
                   'push_titulo': 'Soja', 'push_corpo': 'Veja o aviso do município no app.'}]
        achados = pa.checar_linhas(linhas, TELAS)
        self.assertEqual([a['campo'] for a in achados], ['linhas[0].push_corpo'])

    def test_detecta_formato_rows_e_lista_de_falas(self):
        self.assertEqual(pa.checar_dados({'rows': [{'resumo': 'Abra o app e veja o aviso do município.'}]},
                                         TELAS)[0]['campo'], 'rows[0].resumo')
        self.assertEqual(len(pa.checar_dados([['s0-0', 'Veja no app.', False]], TELAS)), 1)


class PrepararTest(unittest.TestCase):
    def test_preparar_recusa_roteiro_que_reprova_antes_do_dry_run(self):
        pauta = copy.deepcopy(PAUTA)
        pauta['cenas'][-1]['falas'] = ['Confira o aviso do seu município no Pulso do Campo.']
        with mock.patch.object(app, 'pacote_integro', return_value=({'duracao_seg': 50}, pauta)), \
                mock.patch.object(app.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'promete o que o app não tem'):
                app.preparar(Path('ep'))
        run.assert_not_called()


class TelasTest(unittest.TestCase):
    def test_snapshot_tem_sha_e_telas_mapeadas(self):
        dados = json.loads(pa.TELAS.read_text(encoding='utf-8'))
        self.assertEqual(len(dados['sha']), 40)
        for _, tela in pa.RECURSOS:
            self.assertIn(tela, TELAS)
        self.assertNotIn('alertas-inmet.tsx', TELAS)


if __name__ == '__main__':
    unittest.main()
