import React from 'react';
import { AbsoluteFill, Sequence, getInputProps, useCurrentFrame } from 'remotion';
import { Fundo, LogoMarca } from './chrome';
import { CenasReais } from './cenas-reais';
import { AlertaBR, GanchoBR, OniBR } from './scenesBR';
import { C, FONT, FPS, Pill, cena, clamp01, fontFaces, pop, prog } from './lib';

// Stories do Pulso Brasil 02/11: trechos do Reels sem legenda nem voz (a trilha entra no mux).
// Zona segura do Stories: nada importante acima de 250 px nem abaixo de 1580 px.
// Números iguais aos do dossiê (G1 aprovado). Tempos saem das cenas da timeline (voz Gemini).

const trecho = (nome: string, folga = 0.6) => {
  const c = cena(nome);
  return { de: Math.max(0, c.s - 0.3), dur: Math.min(15, c.e - c.s + 0.3 + folga) };
};
export const STORIES: Record<number, { de: number; dur: number }> = {
  1: { de: 0, dur: Math.min(15, cena('intro').e + 1.5) },
  2: trecho('oni', -0.1), // sem folga: a cena sai antes do fim e o story terminava vazio
  3: trecho('alerta'),
  4: { de: cena('fecho').s, dur: 8 },
};

const OURO = '#FBBF24';

const ChuvaDesigual: React.FC<{ t: number }> = ({ t }) => {
  const k = pop(t, cena('intro').e - 0.2, { damping: 13, stiffness: 170 });
  return (
    <div style={{ position: 'absolute', left: 56, right: 56, top: 1365, textAlign: 'center', opacity: clamp01(k * 2), transform: `scale(${0.85 + 0.15 * k})` }}>
      <div style={{ display: 'inline-block', background: 'linear-gradient(90deg, #FBBF24, #D97706)', borderRadius: 28, padding: '18px 40px', boxShadow: '0 0 50px rgba(251,191,36,0.5)' }}>
        <div style={{ fontFamily: FONT, fontWeight: 900, fontSize: 64, color: '#05070A', letterSpacing: -0.5 }}>A CHUVA NÃO CHEGA IGUAL</div>
      </div>
      <div style={{ marginTop: 18, fontFamily: FONT, fontWeight: 700, fontSize: 30, color: C.text }}>
        Até domingo: <span style={{ color: OURO }}>1.189 de 1.191 no Sul, 1 de 1.794 no Nordeste</span>
      </div>
      <div style={{ marginTop: 8, fontFamily: FONT, fontWeight: 600, fontSize: 22, color: C.muted }}>ECMWF, 50 cenários, rodada de 02/11/2026, CC BY 4.0. Previsão, não é certeza.</div>
    </div>
  );
};

const Marca: React.FC<{ t: number }> = ({ t }) => (
  <div style={{ position: 'absolute', left: 0, right: 0, top: 1440, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 16, opacity: prog(t, 0.6, 0.6) }}>
    <LogoMarca size={64} id="storyMarca" brilho={0.3} />
    <div style={{ fontFamily: FONT, fontWeight: 900, fontSize: 34, color: C.text, letterSpacing: 2.5 }}>
      PULSO <span style={{ color: C.greenLight }}>BRASIL</span>
      <span style={{ color: C.muted, fontWeight: 700, fontSize: 26, letterSpacing: 1 }}> · 02/11/2026</span>
    </div>
  </div>
);

const Cta: React.FC<{ t: number }> = ({ t }) => {
  const kL = prog(t, 0.1, 1.2);
  const k1 = pop(t, 0.3);
  const k2 = pop(t, 1.0);
  const k3 = pop(t, 1.6);
  return (
    <div style={{ position: 'absolute', left: 56, right: 56, top: 290, textAlign: 'center' }}>
      <div style={{ opacity: clamp01(k1 * 2), transform: `scale(${0.85 + 0.15 * k1})` }}>
        <Pill cor={OURO} fundo="rgba(5,7,10,0.85)" size={36}>▶ Veja o vídeo completo no Reels</Pill>
      </div>
      <div style={{ display: 'flex', justifyContent: 'center', marginTop: 40 }}>
        <LogoMarca size={170} k={kL} id="storyCta" brilho={0.4} />
      </div>
      <div style={{ marginTop: 22, fontFamily: FONT, fontWeight: 900, fontSize: 62, color: C.text, lineHeight: 1.08, opacity: clamp01(k2 * 2) }}>
        CHANCE DE CHUVA DA SUA CIDADE
        <div style={{ color: OURO }}>DIA A DIA, GRÁTIS.</div>
      </div>
      <div style={{ marginTop: 32, display: 'inline-block', background: 'linear-gradient(90deg, #10B981, #059669)', color: '#05070A', borderRadius: 40, padding: '24px 48px', boxShadow: `0 0 ${40 + 30 * k3}px rgba(16,185,129,0.55)`, transform: `scale(${0.9 + 0.1 * k3})`, opacity: clamp01(k3 * 2) }}>
        <div style={{ fontFamily: FONT, fontWeight: 900, fontSize: 52, letterSpacing: 1.5 }}>APP PULSO DO CAMPO</div>
        <div style={{ fontFamily: FONT, fontWeight: 800, fontSize: 28, marginTop: 4, letterSpacing: 2 }}>GRÁTIS · iPHONE E ANDROID</div>
      </div>
      <div style={{ marginTop: 22, fontFamily: FONT, fontWeight: 600, fontSize: 22, color: C.muted, lineHeight: 1.4 }}>
        Fontes: ECMWF (rodada de 02/11/2026, CC BY 4.0) e Conab (soja até 23/10/2026). Previsão não é certeza. Não é recomendação.
      </div>
    </div>
  );
};

export const StoryBR: React.FC = () => {
  const n = Number(getInputProps().n ?? 1);
  const { de } = STORIES[n];
  const f = useCurrentFrame();
  const local = f / FPS;
  const t = de + local;
  const qa = getInputProps().qa === true;
  return (
    <AbsoluteFill style={{ backgroundColor: C.bg }}>
      <style>{fontFaces}</style>
      <Fundo t={t} />
      <Sequence from={-Math.round(de * FPS)} layout="none">
        <CenasReais t={t} />
      </Sequence>
      {/* cenas do Reels começam em 250 px: 40 px abaixo para sair da barra de perfil do Stories */}
      <AbsoluteFill style={{ transform: 'translateY(40px)' }}>
        {n === 1 && <GanchoBR t={t} />}
        {n === 2 && <OniBR t={t} />}
        {n === 3 && <AlertaBR t={t} />}
      </AbsoluteFill>
      {n === 1 && <ChuvaDesigual t={t} />}
      {(n === 2 || n === 3) && <Marca t={local} />}
      {n === 4 && <Cta t={local} />}
      {/* fade de entrada para o story não começar no meio de um movimento */}
      <AbsoluteFill style={{ background: C.bg, opacity: 1 - prog(local, 0, 0.35), pointerEvents: 'none' }} />
      {qa && (
        <>
          <div style={{ position: 'absolute', left: 0, right: 0, top: 0, height: 250, background: 'rgba(255,0,0,0.25)' }} />
          <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: 340, background: 'rgba(255,0,0,0.25)' }} />
          {n === 4 && <div style={{ position: 'absolute', left: 140, right: 140, top: 1180, height: 300, border: '6px dashed #22D3EE', borderRadius: 30 }} />}
        </>
      )}
    </AbsoluteFill>
  );
};
