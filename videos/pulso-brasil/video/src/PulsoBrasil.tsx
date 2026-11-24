import React from 'react';
import { AbsoluteFill, Html5Audio, staticFile } from 'remotion';
import { Cabecalho, Fundo, Legendas, Progresso } from './chrome';
import { useT } from './lib';
import { CenasReais } from './cenas-reais';
import { CenaBR } from './scenesBR';
import type { Props } from './tipos';

export const PulsoBrasil: React.FC<Props> = ({ episodio, timeline, capa }) => {
  const t = useT();
  const { cenas, cabecalho, cta_final } = episodio;
  const marcos = cenas.map((cena) => timeline.cenas[cena.id].s);
  return (
    <AbsoluteFill style={{ backgroundColor: '#05070A' }}>
      <Fundo t={t} />
      <CenasReais t={t} cenas={cenas} timeline={timeline} />
      {cenas.map((dados, i) => (
        <CenaBR key={dados.id} dados={dados} t={t} janela={timeline.cenas[dados.id]} primeira={i === 0} cta={cta_final} />
      ))}
      <Cabecalho t={t} texto={cabecalho} fechoS={marcos.at(-1) ?? timeline.duracao} />
      {!capa && <Legendas t={t} timeline={timeline} />}
      {!capa && <Progresso t={t} duracao={timeline.duracao} marcos={marcos.slice(1)} />}
      {cenas.length > 0 && !capa && <Html5Audio src={staticFile('mix.m4a')} />}
    </AbsoluteFill>
  );
};
