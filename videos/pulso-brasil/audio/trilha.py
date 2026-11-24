"""Trilha canônica: reutiliza a faixa do episódio de 04/11, sem voz.
Não usa a faixa nova de telejornal reprovada. Não chama API nem compra música.
"""
import json,sys
from pathlib import Path
from assets.integridade import caminhos
import numpy as np
import soundfile as sf
p=Path(sys.argv[1]);tl=json.loads((p/'timeline.json').read_text())
origem=caminhos(p)['trilha']
x,sr=sf.read(origem,dtype='float32',always_2d=True)
n=round(tl['duracao']*sr)
if len(x) < n:
    # A cópia publicada já tem fade; repete a abertura com crossfade, sem trocar de faixa.
    sobreposicao = min(round(sr * 1.2), len(x) // 2)
    rampa = np.linspace(0, 1, sobreposicao)[:, None]
    x = np.concatenate((x[:-sobreposicao], x[-sobreposicao:] * (1-rampa)
                        + x[:sobreposicao] * rampa, x[sobreposicao:]))
y=x[:n].copy()
fade=min(round(sr*.25),n);y[:fade]*=np.linspace(.35,1,fade)[:,None]
fade=min(round(sr*1.2),n);y[-fade:]*=np.linspace(1,0,fade)[:,None]
y*=0.085/(np.sqrt(np.mean(y*y))+1e-9)
sf.write(p/'musica.wav',y,sr)
# A trilha original já contém sua assinatura; evitar empilhar novos impactos.
sf.write(p/'efeitos.wav',np.zeros((n,2),dtype=np.float32),sr)
(p/'trilha-proveniencia.json').write_text(json.dumps({'origem':str(origem.relative_to(p)),'uso':'trilha canônica do Pulso Brasil','duracao_s':tl['duracao'],'normalizacao_rms':0.085},ensure_ascii=False,indent=2))
print('Trilha canônica de 04/11 verificada; fade final aplicado.')
