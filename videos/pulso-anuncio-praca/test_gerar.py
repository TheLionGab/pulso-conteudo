import json
import unittest
from pathlib import Path

import gerar

BASE = json.loads((Path(__file__).parent / "testes" / "fixture-imea.json").read_text(encoding="utf-8"))


class TestGerar(unittest.TestCase):
    def test_cidade_abaixo_do_topo_compara_com_quem_paga_mais(self):
        d = gerar.montar_dados(BASE, "soja", "Sorriso")
        self.assertEqual(d["preco"], 138.20)
        self.assertEqual(d["comparacao"]["diferenca"], 5.80)
        self.assertEqual(d["comparacao"]["total"], 58000)
        self.assertEqual(d["comparacao"]["titulo"], "Rondonópolis paga mais")
        self.assertEqual(d["data"], "19/11/2026")

    def test_cidade_no_topo_compara_com_o_piso(self):
        d = gerar.montar_dados(BASE, "soja", "Rondonópolis")
        self.assertEqual(d["comparacao"]["titulo"], "Rondonópolis lidera hoje")
        self.assertEqual(d["comparacao"]["diferenca"], 8.65)
        self.assertIn("Querência", d["comparacao"]["subtitulo"])

    def test_ranking_tem_a_cidade_no_maximo_6_linhas_e_ordem_decrescente(self):
        for cidade in BASE["produtos"]["soja"]:
            r = gerar.montar_ranking(BASE["produtos"]["soja"], cidade)
            self.assertLessEqual(len(r), 6)
            self.assertEqual(sum(1 for x in r if x["eu"]), 1)
            valores = [x["valor"] for x in r]
            self.assertEqual(valores, sorted(valores, reverse=True))
            self.assertTrue(all(0 < x["largura"] <= 1 for x in r))

    def test_cidade_inexistente_para(self):
        with self.assertRaises(SystemExit):
            gerar.montar_dados(BASE, "soja", "Cuiabá")

    def test_index_recebe_os_dados(self):
        d = gerar.montar_dados(BASE, "milho", "Sinop")
        html = gerar.escrever_index(d).read_text(encoding="utf-8")
        self.assertNotIn("/*__DADOS__*/ null", html)
        self.assertIn('"cidade": "Sinop"', html)


if __name__ == "__main__":
    unittest.main()
