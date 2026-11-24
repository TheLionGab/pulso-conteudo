import React from 'react';
import { AbsoluteFill, OffthreadVideo, Sequence, staticFile } from 'remotion';
import lista from '../public/cenas/lista.json';
import { C, FPS, TL, janela } from './lib';

const CLIPE = 8;
const LENTO_MAX = 0.8;
const FADE = 0.5;
const EXISTE = new Set(lista as string[]);

type Trecho = { arquivo: string; de: number; ate: number };

const trechos = (): Trecho[] => {
  const fim = TL.duracao as number;
  const t = (arquivo: string, de: number, ate: number): Trecho => ({
    arquivo,
    de: Math.max(0, de - FADE / 2),
    ate: Math.min(ate + FADE / 2, fim),
  });

  const c = (n: string) => (n in TL.cenas ? (TL.cenas[n] as { s: number; e: number }).s : (TL.cues[n] as number));
  return [
    t('cena09_plantio_soja', 0, c('oni')),
    t('cena03_silos', c('oni'), c('regioes')),
    t('cena09_plantio_soja', c('regioes'), c('alerta')),
    t('cena_trator_preparo', c('alerta'), c('bolso')),
    t('cena09_plantio_soja', c('bolso'), c('fecho')),
    t('cena_ceu_nuvens_cerrado', c('fecho'), fim),
  ].filter((tr) => EXISTE.has(tr.arquivo));
};

const Clipe: React.FC<{ tr: Trecho; t: number }> = ({ tr, t }) => {
  const dur = tr.ate - tr.de;
  const rate = Math.min(1, Math.max(LENTO_MAX, CLIPE / dur));
  // primeiro clipe já entra visível: o quadro 0 é o que aparece no feed antes de a pessoa decidir parar
  const o = janela(t, tr.de === 0 ? -FADE : tr.de, tr.ate, FADE, FADE);
  const k = Math.max(0, Math.min(1, (t - tr.de) / dur));
  return (
    <Sequence from={Math.round(tr.de * FPS)} durationInFrames={Math.round(dur * FPS)} layout="none">
      <AbsoluteFill style={{ opacity: o * 0.62 }}>
        <OffthreadVideo
          src={staticFile(`cenas/${tr.arquivo}.mp4`)}
          muted
          playbackRate={rate}
          style={{ width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${1.04 + 0.05 * k})`, filter: 'saturate(0.88) brightness(0.85)' }}
        />
      </AbsoluteFill>
    </Sequence>
  );
};

export const CenasReais: React.FC<{ t: number }> = ({ t }) => {
  const lst = trechos();
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
