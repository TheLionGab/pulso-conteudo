import React from 'react';
import { AbsoluteFill } from 'remotion';
import { C, FONT, fontFaces } from './lib';

// Pergunta do story (PNG transparente sobreposto no ffmpeg). Zona segura: entre 250 e 1580 px.
export const Pergunta: React.FC = () => (
  <AbsoluteFill style={{ background: 'transparent' }}>
    <style>{fontFaces}</style>
    <div style={{ position: 'absolute', left: 56, right: 56, top: 1040, textAlign: 'center' }}>
      <div style={{ display: 'inline-block', background: 'linear-gradient(90deg, #FBBF24, #D97706)', borderRadius: 32, padding: '22px 36px', boxShadow: '0 0 50px rgba(251,191,36,0.5)' }}>
        <div style={{ fontFamily: FONT, fontWeight: 900, fontSize: 54, color: '#05070A', letterSpacing: -0.5 }}>VOCÊ JÁ PLANTOU A SOJA?</div>
      </div>
    </div>
  </AbsoluteFill>
);
