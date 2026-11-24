import React from 'react';
import { AbsoluteFill, Loop, OffthreadVideo, Sequence, staticFile } from 'remotion';
import { FPS, janela } from './lib';
import type { Cena, Timeline } from './tipos';

const CLIPE = 8;
const LENTO_MAX = 0.8;
const FADE = 0.5;

type Trecho = { arquivo: string; de: number; ate: number };

const trechos = (cenas: Cena[], timeline: Timeline): Trecho[] => cenas.flatMap((cena, i) => {
  if (!cena.clipe) return [];
  const { s, e } = timeline.cenas[cena.id];
  return [{
    arquivo: cena.clipe,
    de: i === 0 ? 0 : Math.max(0, s - FADE / 2),
    ate: Math.min(e + FADE / 2, timeline.duracao),
  }];
});

const Clipe: React.FC<{ tr: Trecho; t: number }> = ({ tr, t }) => {
  const dur = tr.ate - tr.de;
  const rate = Math.min(1, Math.max(LENTO_MAX, CLIPE / dur));
  // primeiro clipe já entra visível: o quadro 0 é o que aparece no feed antes de a pessoa decidir parar
  const o = janela(t, tr.de === 0 ? -FADE : tr.de, tr.ate, FADE, FADE);
  const k = Math.max(0, Math.min(1, (t - tr.de) / dur));
  return (
    <Sequence from={Math.round(tr.de * FPS)} durationInFrames={Math.max(1, Math.round(tr.ate * FPS) - Math.round(tr.de * FPS))} layout="none">
      <AbsoluteFill style={{ opacity: o * 0.62 }}>
        <Loop layout="none" durationInFrames={Math.floor(CLIPE * FPS / rate)}>
          <OffthreadVideo
            src={staticFile(`cenas/${tr.arquivo}.mp4`)}
            muted
            playbackRate={rate}
            style={{ width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${1.04 + 0.05 * k})`, filter: 'saturate(0.88) brightness(0.85)' }}
          />
        </Loop>
      </AbsoluteFill>
    </Sequence>
  );
};

export const CenasReais: React.FC<{ t: number; cenas: Cena[]; timeline: Timeline }> = ({ t, cenas, timeline }) => {
  const lst = trechos(cenas, timeline);
  return (
    <AbsoluteFill style={{ pointerEvents: 'none' }}>
      {lst.map((tr, i) => (
        <Clipe key={`${tr.arquivo}-${i}`} tr={tr} t={t} />
      ))}
      {/* escurece onde ficam os cards e a legenda; deixa a imagem respirar no rodapé (zona do Reels) */}
      <AbsoluteFill style={{ background: 'linear-gradient(180deg, rgba(5,7,10,0.78) 0%, rgba(5,7,10,0.62) 45%, rgba(5,7,10,0.55) 72%, rgba(5,7,10,0.35) 88%, rgba(5,7,10,0.7) 100%)' }} />
    </AbsoluteFill>
  );
};
