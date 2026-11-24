"""Candidato sonoro: reutiliza a trilha própria do primeiro Pulso News, sem voz.
Não usa a faixa nova de telejornal reprovada. Não chama API nem compra música.
"""
import json,sys
from pathlib import Path
import numpy as np
import soundfile as sf
p=Path(sys.argv[1]);tl=json.loads((p/'timeline.json').read_text())
origem=Path('/Users/mac/Studio/pulso-videos/pulso-news-queda-do-milho/video/public/musica.wav')
x,sr=sf.read(origem,dtype='float32',always_2d=True)
n=round(tl['duracao']*sr)
if len(x)<n:raise SystemExit('Trilha de referência curta; não repetir automaticamente.')
y=x[:n].copy()
fade=min(round(sr*.25),n);y[:fade]*=np.linspace(.35,1,fade)[:,None]
fade=min(round(sr*1.2),n);y[-fade:]*=np.linspace(1,0,fade)[:,None]
y*=0.085/(np.sqrt(np.mean(y*y))+1e-9)
sf.write(p/'musica.wav',y,sr)
# A trilha original já contém sua assinatura; evitar empilhar novos impactos.
sf.write(p/'efeitos.wav',np.zeros((n,2),dtype=np.float32),sr)
(p/'trilha-proveniencia.json').write_text(json.dumps({'origem':str(origem),'uso':'candidato; trilha própria do primeiro News, sem adoção definitiva','duracao_s':tl['duracao'],'normalizacao_rms':0.085},ensure_ascii=False,indent=2))
print('Trilha própria original reutilizada; fade final aplicado; sem chamada paga.')
