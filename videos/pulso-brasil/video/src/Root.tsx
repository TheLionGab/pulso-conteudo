import React from 'react';
import { Composition } from 'remotion';
import { FPS, H, W } from './lib';
import { PulsoBrasil } from './PulsoBrasil';
import type { Props } from './tipos';

const vazio: Props = {
  episodio: { cabecalho: '', cenas: [], cta_final: '' },
  timeline: { duracao: 1, cenas: {}, palavras: [], legendas: [] },
  capa: false,
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="PulsoBrasil"
    component={PulsoBrasil}
    defaultProps={vazio}
    calculateMetadata={({ props }) => ({ durationInFrames: Math.ceil(props.timeline.duracao * FPS) })}
    durationInFrames={FPS}
    fps={FPS}
    width={W}
    height={H}
  />
);
