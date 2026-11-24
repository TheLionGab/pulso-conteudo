import React from 'react';
import { AbsoluteFill, Html5Audio, getInputProps, staticFile } from 'remotion';
import { Cabecalho, Fundo, Legendas, Progresso } from './chrome';
import { fontFaces, useT } from './lib';
import { CenasReais } from './cenas-reais';
import { AlertaBR, BolsoBR, FechoBR, GanchoBR, OniBR, RegioesBR } from './scenesBR';

export const PulsoBrasil0211: React.FC = () => {
  const t = useT();
  const capa = getInputProps().capa === true;
  return (
    <AbsoluteFill style={{ backgroundColor: '#05070A' }}>
      <style>{fontFaces}</style>
      <Fundo t={t} />
      <CenasReais t={t} />
      <GanchoBR t={t} />
      <OniBR t={t} />
      <RegioesBR t={t} />
      <AlertaBR t={t} />
      <BolsoBR t={t} />
      <FechoBR t={t} />
      <Cabecalho t={t} />
      {!capa && <Legendas t={t} />}
      {!capa && <Progresso t={t} />}
      <Html5Audio src={staticFile('mix.m4a')} />
    </AbsoluteFill>
  );
};
