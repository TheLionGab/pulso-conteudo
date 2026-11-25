import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def carregar(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, ROOT / caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


gate = carregar('g_conteudo_pro', 'gates/g_conteudo_pro.py')
conferir = carregar('conferir_episodio', 'diario/conferir_episodio.py')
EXEMPLO = ROOT / 'exemplos/2026-11-24-dolar-soja'


def exemplo():
    return (json.loads((EXEMPLO / 'episodio.json').read_text()), json.loads((EXEMPLO / 'dossie.json').read_text()))


def linha(id_, arquivo, caminho, **extra):
    return {'id': id_, 'numero': 3, 'json_campo': {'arquivo': arquivo, 'caminho': caminho}, **extra}


class ConteudoPro(unittest.TestCase):
    def test_libera_o_exemplo_e_os_modelos_do_repo(self):
        episodio, dossie = exemplo()
        self.assertEqual(gate.falhas_de(episodio, dossie), [])
        for arquivo in sorted((ROOT / 'exemplos').glob('*.json')):
            self.assertEqual(gate.falhas_de(json.loads(arquivo.read_text()), {}), [], arquivo.name)

    def test_libera_o_fecho_pro_e_preco_de_mercado(self):
        episodio, dossie = exemplo()
        episodio['cta_final'] = 'No Pulso Pro, compare compradores pelo valor que sobra após o frete.'
        episodio['roteiro'][1][1] = 'A soja foi a *{R$ 145,50|cento e quarenta e cinco e cinquenta}* em Rondonópolis.'
        episodio['legenda_instagram'] += '\nO plano de safra e a chuva não mudam a conta. Manter o preço da saca é o ponto.'
        dossie['linhas'].append(linha('deral', 'fontes/pulso-referencias.json', ['referencias', 'feijao', 'Curitiba/PR', 'deral|Carioca|R$/sc', 'valor']))
        self.assertEqual(gate.falhas_de(episodio, dossie), [])

    def test_barra_oferta_de_compra_no_dossie(self):
        episodio, dossie = exemplo()
        for caminho in (['ofertas_compra', 'soja', 'Sorriso/MT', 'valor_min'], ['ofertas_compra', 'soja', 'Sorriso/MT', 'n_ofertas'],
                        ['x', 'valor_max']):
            ruim = copy.deepcopy(dossie)
            ruim['linhas'].append(linha('oferta', 'fontes/pulso-referencias.json', caminho))
            achados = gate.falhas_de(episodio, ruim)
            self.assertEqual(len(achados), 1, caminho)
            self.assertIn("linha 'oferta'", achados[0])

    def test_barra_derivado_de_linha_de_oferta_em_cadeia(self):
        episodio, dossie = exemplo()
        dossie['linhas'].append(linha('oferta', 'fontes/pulso-referencias.json', ['ofertas_compra', 'soja', 'Sorriso/MT', 'valor_max']))
        dossie['derivados'] += [{'id': 'dif', 'de': ['oferta', 'ptax_16'], 'formula': 'A / B', 'valor': 1.0},
                                {'id': 'dif2', 'de': ['dif', 'ptax_16'], 'formula': 'A / B', 'valor': 1.0}]
        achados = gate.falhas_de(episodio, dossie)
        self.assertEqual(sorted(a.split("'")[1] for a in achados), ['dif', 'dif2', 'oferta'])

    def test_barra_gratuidade_em_cada_campo_de_texto(self):
        for texto in ('grátis', 'GRÁTIS', 'gratis', 'baixe grátis', 'de graça', 'De Graça no app', 'teste gratuito', 'gratuita'):
            for onde in ('roteiro', 'cena', 'legenda_instagram', 'selo', 'cta_final'):
                episodio, dossie = exemplo()
                if onde == 'roteiro':
                    episodio['roteiro'][-1][1] = f'No Pulso Pro, veja a praça, {texto}.'
                elif onde == 'cena':
                    episodio['cenas'][0]['apoio'] = texto
                elif onde == 'selo':
                    episodio['cenas'][-1]['selo'] = f'PULSO DO CAMPO · {texto}'
                else:
                    episodio[onde] += f' {texto}'
                achados = gate.falhas_de(episodio, dossie)
                self.assertTrue(any('gratuidade' in a for a in achados), (texto, onde, achados))

    def test_barra_preco_ligado_ao_pro_mas_libera_preco_de_mercado(self):
        for ruim in ('No Pulso Pro, por R$ 29,90 por mês.', 'Assine o Pulso Pro por 30 reais.', 'Pulso Pro com desconto de lançamento.',
                     'Pulso Pro: teste por 7 dias.', 'A assinatura custa R$ 19.'):
            episodio, dossie = exemplo()
            episodio['legenda_instagram'] += f'\n{ruim}'
            achados = gate.falhas_de(episodio, dossie)
            self.assertTrue(any('ligado ao Pro' in a for a in achados), (ruim, achados))
        episodio, dossie = exemplo()
        episodio['legenda_instagram'] += '\nA soja foi a R$ 145,50. No Pulso Pro, veja a cotação da sua praça.'
        self.assertEqual(gate.falhas_de(episodio, dossie), [])

    def test_barra_promessa_de_resultado(self):
        for ruim in ('Ganhe mais com o Pulso Pro.', 'Você vai lucrar.', 'Lucre na safra.', 'Você vai ganhar na venda.', 'lucro garantido',
                     'Aumente seu lucro.'):
            episodio, dossie = exemplo()
            episodio['cta_final'] = ruim
            self.assertTrue(any('promessa de resultado' in a for a in gate.falhas_de(episodio, dossie)), ruim)

    def test_barra_a_fala_marcada_com_exibe_e_fala(self):
        episodio, dossie = exemplo()
        episodio['roteiro'][1][1] = 'Veja *{agora|de graça}* no app.'
        self.assertTrue(any('gratuidade' in a for a in gate.falhas_de(episodio, dossie)))

    def test_cli_sai_1_e_diz_o_campo(self):
        episodio, dossie = exemplo()
        episodio['cenas'][-1]['selo'] = 'PULSO DO CAMPO · BAIXE GRÁTIS'
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'episodio.json').write_text(json.dumps(episodio))
            (Path(tmp) / 'dossie.json').write_text(json.dumps(dossie))
            r = subprocess.run([sys.executable, '-I', str(ROOT / 'gates/g_conteudo_pro.py'), tmp], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn('cenas[', r.stderr)
            self.assertIn('selo', r.stderr)
            episodio['cenas'][-1]['selo'] = 'PULSO DO CAMPO · PULSO PRO'
            (Path(tmp) / 'episodio.json').write_text(json.dumps(episodio))
            r = subprocess.run([sys.executable, '-I', str(ROOT / 'gates/g_conteudo_pro.py'), tmp], capture_output=True, text=True)
            self.assertEqual((r.returncode, r.stderr), (0, ''))

    def test_conferir_episodio_aplica_o_gate_e_aceita_o_exemplo(self):
        self.assertEqual(conferir.conferir('2026-11-24', EXEMPLO), 'pulso-brasil-2026-11-24-dolar-soja')
        episodio, dossie = exemplo()
        episodio['cta_final'] = 'Baixe grátis'
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'episodio.json').write_text(json.dumps(episodio))
            (Path(tmp) / 'dossie.json').write_text(json.dumps(dossie))
            with self.assertRaisesRegex(ValueError, 'gratuidade'):
                conferir.conferir('2026-11-24', tmp)

    def test_pipeline_roda_o_gate_antes_de_qualquer_render(self):
        script = (ROOT / 'pulso-brasil.sh').read_text()
        gate_pos = script.index('gates/g_conteudo_pro.py')
        self.assertLess(gate_pos, script.index('audio.voz'))
        self.assertLess(gate_pos, script.index('remotion" render'))


if __name__ == '__main__':
    unittest.main()
