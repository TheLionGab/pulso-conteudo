"""Nova tentativa do G3: só a lógica de qual cache invalidar, sem ElevenLabs, sem G3 e sem ffmpeg."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import wave

from audio import regerar, voz
from audio.roteiro import parse

ROOT = Path(__file__).resolve().parents[1]
EPISODIO = json.loads((ROOT / 'exemplos/2026-11-24-dolar-soja/episodio.json').read_text())


def falas_cruas():
    return [' '.join(u['fala'] for u in parse(texto)) for _, texto, _ in EPISODIO['roteiro']]


def gravar_wav(destino):
    """WAV mínimo que o cache da voz aceita (mono, 16 bits, 24 kHz)."""
    with wave.open(str(destino), 'wb') as w:
        w.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
        w.writeframes(b'\0\0' * 240)


def asr(reprovados, falas=None):
    falas = falas or falas_cruas()
    segs = [{'seg': i, 'escuta': escuta, 'wer': 0.9 if i in reprovados else 0.1, 'fala': f, 'ouvido': 'x'}
            for escuta in ('cru', 'ar x1.1') for i, f in enumerate(falas)]
    return {'voz': 'v', 'teto_wer': 0.35, 'reprovados': sorted(reprovados), 'segmentos': segs}


class Regerar(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.cache = Path(tmp.name) / 'cache'
        self.cache.mkdir()
        _, self.arquivos = voz.arquivos_do_cache(EPISODIO['roteiro'], self.cache)
        for arquivo in set(self.arquivos):
            gravar_wav(arquivo)
        # Nenhum teste aqui pode chegar à voz paga.
        parar = mock.patch.object(voz, 'sintetizar', side_effect=AssertionError('ElevenLabs chamada'))
        parar.start()
        self.addCleanup(parar.stop)
        self.tmp = Path(tmp.name)

    def restantes(self):
        return {i for i, a in enumerate(self.arquivos) if a.exists()}

    def test_apaga_do_cache_so_os_segmentos_reprovados(self):
        n = len(self.arquivos)
        reprovados = {1, n - 2}
        self.assertEqual(len(set(self.arquivos)), n, 'o exemplo tem fala repetida; o teste supõe falas distintas')
        self.assertEqual(regerar.invalidar(EPISODIO, asr(reprovados), self.cache), sorted(reprovados))
        self.assertEqual(self.restantes(), set(range(n)) - reprovados)

    def test_sem_reprovado_nada_e_apagado_e_o_pipeline_para_como_antes(self):
        with self.assertRaisesRegex(ValueError, 'nada a regerar'):
            regerar.invalidar(EPISODIO, asr(set()), self.cache)
        self.assertEqual(self.restantes(), set(range(len(self.arquivos))))

    def test_asr_de_outro_episodio_ou_fora_do_roteiro_nao_apaga_nada(self):
        falas = falas_cruas()
        falas[2] = 'outra fala'
        with self.assertRaisesRegex(ValueError, 'não é deste episódio'):
            regerar.invalidar(EPISODIO, asr({2}, falas), self.cache)
        with self.assertRaisesRegex(ValueError, 'fora do roteiro'):
            regerar.invalidar(EPISODIO, asr({len(self.arquivos)}, falas_cruas() + ['x']), self.cache)
        self.assertEqual(self.restantes(), set(range(len(self.arquivos))))

    def test_o_cache_invalidado_e_o_mesmo_que_o_gerar_usa(self):
        # Só os reprovados faltam: o gerar tentaria sintetizar exatamente esses, e mais nenhum.
        regerar.invalidar(EPISODIO, asr({0, 3}), self.cache)
        with mock.patch.object(voz, 'sintetizar', side_effect=lambda fala, chave, destino, anteriores: gravar_wav(destino)) as sintetizar, \
                mock.patch.dict('os.environ', {'ELEVENLABS_API_KEY': 'falsa'}), \
                mock.patch.object(voz, 'checar'):
            voz.gerar(EPISODIO, self.tmp / 'audio', self.cache)
        enviados = [chamada.args[0] for chamada in sintetizar.call_args_list]
        falas, _ = voz.arquivos_do_cache(EPISODIO['roteiro'], self.cache)
        self.assertEqual(enviados, [falas[0], falas[3]])

    def test_linha_de_comando_sai_1_sem_asr_e_nao_apaga(self):
        r = subprocess.run([sys.executable, '-m', 'audio.regerar', str(ROOT / 'exemplos/2026-11-24-dolar-soja/episodio.json'),
                            str(self.tmp / 'nao-existe.json'), str(self.cache)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn('Regerar:', r.stderr)
        self.assertEqual(self.restantes(), set(range(len(self.arquivos))))

    def test_linha_de_comando_lista_os_segmentos_regerados(self):
        caminho = self.tmp / 'asr.json'
        caminho.write_text(json.dumps(asr({2})))
        r = subprocess.run([sys.executable, '-m', 'audio.regerar', str(ROOT / 'exemplos/2026-11-24-dolar-soja/episodio.json'),
                            str(caminho), str(self.cache)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, 'G3: regerando só os segmentos 002'))
        self.assertNotIn(2, self.restantes())


class PipelineChamaARegeracaoUmaVez(unittest.TestCase):
    """O pulso-brasil.sh precisa de ffmpeg, Node e modelos; aqui só a ordem dos passos do G3."""

    def setUp(self):
        self.texto = (ROOT / 'pulso-brasil.sh').read_text()

    def test_sintaxe_do_shell(self):
        self.assertEqual(subprocess.run(['bash', '-n', str(ROOT / 'pulso-brasil.sh')], capture_output=True).returncode, 0)

    def test_g3_roda_no_maximo_duas_vezes_e_a_regeracao_fica_entre_elas(self):
        chamadas = [i for i in range(len(self.texto)) if self.texto.startswith('gates/g3_asr.py', i)]
        self.assertEqual(len(chamadas), 2)
        regeracao = self.texto.index('audio.regerar')
        self.assertTrue(chamadas[0] < regeracao < chamadas[1])
        # A 1ª chamada não derruba o shell antes da regeração; a 2ª derruba (sem `||`), como o G3 sempre fez.
        primeira = self.texto[self.texto.rindex('\n', 0, chamadas[0]):self.texto.index('\n', chamadas[0])]
        segunda = self.texto[self.texto.rindex('\n', 0, chamadas[1]):self.texto.index('\n', chamadas[1])]
        self.assertIn('|| g3=$?', primeira)
        self.assertNotIn('||', segunda)
        self.assertEqual(self.texto.count('voz_e_montagem'), 3)  # definição, 1ª passagem e retry


if __name__ == '__main__':
    unittest.main()
