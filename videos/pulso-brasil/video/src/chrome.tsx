import React from 'react';
import { C, FONT, H, W, clamp01, pop, prog } from './lib';
import type { Palavra, Timeline } from './tipos';

export const BEAT = 60 / 104;
/** Reels: topo ~120 px, base ~420 px, largura da legenda 840. */
export const REELS = { topo: 120, baseLegenda: 420, larguraLegenda: 840, fonte: 52 };

export const LogoMarca: React.FC<{ size: number; k?: number; brilho?: number; id?: string }> = ({ size, k = 1, brilho = 0, id = 'lg' }) => {
  const pulso = 'M220 462H350L405 405L467 536L548 310L618 462H804';
  const kp = clamp01(k / 0.6);
  const ks = clamp01((k - 0.45) / 0.55);
  const sw = (w: number, o = 1, extra: object = {}) => ({ stroke: `url(#${id})`, strokeWidth: w, strokeLinecap: 'round' as const, fill: 'none', opacity: o, ...extra });
  return (
    <svg width={size} height={size} viewBox="150 250 724 640" style={{ overflow: 'visible' }}>
      <defs>
        <linearGradient id={id} x1="220" y1="310" x2="804" y2="830" gradientUnits="userSpaceOnUse">
          <stop stopColor="#A7F3D0" />
          <stop offset="0.45" stopColor="#34D399" />
          <stop offset="1" stopColor="#059669" />
        </linearGradient>
        <filter id={`${id}g`} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="22" />
        </filter>
      </defs>
      {brilho > 0 && <path d={pulso} stroke="#34D399" strokeWidth={70} fill="none" strokeLinecap="round" strokeLinejoin="round" opacity={brilho * 0.55} filter={`url(#${id}g)`} />}
      <path d={pulso} {...sw(58, 1, { strokeLinejoin: 'round', strokeDasharray: 1400, strokeDashoffset: 1400 * (1 - kp) })} />
      <g opacity={ks}>
        <path d="M512 584V832" {...sw(58, 1, { strokeDasharray: 260, strokeDashoffset: 260 * (1 - ks) })} />
        <path d="M452 584C438 680 406 760 360 830" {...sw(48, 0.88, { strokeDasharray: 300, strokeDashoffset: 300 * (1 - ks) })} />
        <path d="M572 584C586 680 618 760 664 830" {...sw(48, 0.88, { strokeDasharray: 300, strokeDashoffset: 300 * (1 - ks) })} />
        <path d="M398 594C352 678 306 754 246 814" {...sw(38, 0.48, { strokeDasharray: 330, strokeDashoffset: 330 * (1 - ks) })} />
        <path d="M626 594C672 678 718 754 778 814" {...sw(38, 0.48, { strokeDasharray: 330, strokeDashoffset: 330 * (1 - ks) })} />
      </g>
    </svg>
  );
};

export const Fundo: React.FC<{ t: number }> = ({ t }) => {
  const fase = (t % BEAT) / BEAT;
  const batida = Math.exp(-fase * 6) * 0.25;
  return (
    <div style={{ position: 'absolute', inset: 0, background: C.bg, overflow: 'hidden' }}>
      <div style={{ position: 'absolute', inset: 0, background: `radial-gradient(1100px 900px at 50% 18%, rgba(16,185,129,${0.12 + batida * 0.05}) 0%, rgba(16,185,129,0.02) 55%, rgba(0,0,0,0) 75%)` }} />
      <svg width={W} height={H} style={{ position: 'absolute', inset: 0, opacity: 0.45 }}>
        {Array.from({ length: 13 }, (_, i) => <line key={`v${i}`} x1={i * 90} y1={0} x2={i * 90} y2={H} stroke="#0F1620" strokeWidth={1.5} />)}
        {Array.from({ length: 22 }, (_, i) => <line key={`h${i}`} x1={0} y1={i * 90 + ((t * 6) % 90)} x2={W} y2={i * 90 + ((t * 6) % 90)} stroke="#0F1620" strokeWidth={1.5} />)}
      </svg>
      <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(1400px 1900px at 50% 45%, rgba(0,0,0,0) 50%, rgba(0,0,0,0.72) 100%)' }} />
    </div>
  );
};

export const Cabecalho: React.FC<{ t: number; texto: string; fechoS: number }> = ({ t, texto, fechoS }) => {
  const o = 1 - prog(t, fechoS - 0.2, 0.5);
  if (o <= 0) return null;
  return (
    <div style={{ position: 'absolute', left: 56, right: 56, top: REELS.topo, height: 96, opacity: o, display: 'flex', alignItems: 'center', gap: 16 }}>
      <div style={{ width: 74, height: 74, borderRadius: 20, background: 'radial-gradient(circle at 50% 40%, #134E3A 0%, #0A2A20 45%, #061510 80%)', border: '1.5px solid rgba(52,211,153,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 0 30px rgba(16,185,129,0.25)' }}>
        <LogoMarca size={54} id="hdr" brilho={0.4} />
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <div style={{ fontFamily: FONT, fontWeight: 900, fontSize: 31, color: C.text, letterSpacing: 2.5 }}>
          PULSO <span style={{ color: C.greenLight }}>NEWS</span>
        </div>
        <div style={{ fontFamily: FONT, fontWeight: 800, fontSize: 22, color: C.amber, letterSpacing: 1.2 }}>{texto}</div>
      </div>
    </div>
  );
};

const LIGA = new Set(['de', 'do', 'da', 'o', 'a', 'os', 'as', 'um', 'uma', 'por', 'em', 'na', 'no', 'e', 'que', 'com', 'se', 'é']);

const grupos = (ws: Palavra[]) => {
  const out: Palavra[][] = [];
  for (const w of ws) {
    const ult = out[out.length - 1];
    const prev = ult?.[ult.length - 1];
    // 28/10: unidade com espaço ("Chapada dos Guimarães") fica fora do grupo; junto, saía "emChapada"
    if (prev && !String(w.d).includes(' ') && LIGA.has(String(prev.d).toLowerCase().replace(/[^\p{L}]/gu, ''))) ult.push(w);
    else out.push([w]);
  }
  return out;
};

export const Legendas: React.FC<{ t: number; timeline: Timeline }> = ({ t, timeline }) => {
  const leg = timeline.legendas.find((l) => t >= l.s - 0.04 && t < l.e);
  if (!leg) return null;
  const ws = leg.w.map((i: number) => timeline.palavras[i]);
  const k = pop(t, leg.s - 0.04, { damping: 16, stiffness: 260 });
  return (
    <div style={{ position: 'absolute', left: 0, right: 0, bottom: REELS.baseLegenda, display: 'flex', justifyContent: 'center', alignItems: 'flex-end', zIndex: 10 }}>
      <div style={{ transform: `scale(${0.88 + 0.12 * k}) translateY(${(1 - k) * 12}px)`, transformOrigin: '50% 100%', opacity: clamp01(k * 1.6), background: 'rgba(5,7,10,0.85)', border: '1.5px solid rgba(255,255,255,0.08)', borderRadius: 24, padding: '16px 32px 18px', maxWidth: REELS.larguraLegenda, display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: '0 16px', boxShadow: '0 16px 45px rgba(0,0,0,0.6)' }}>
        {grupos(ws).map((g: Palavra[], gi: number) => (
          <span key={gi} style={{ display: 'inline-flex', gap: 16, whiteSpace: 'nowrap' }}>
            {g.map((w: Palavra, i: number) => {
              const falado = t >= w.s - 0.02;
              const ativo = falado && t < w.e + 0.05;
              const ka = ativo ? pop(t, w.s - 0.02, { damping: 12, stiffness: 300 }) : 1;
              return (
                <span key={i} style={{ fontFamily: FONT, fontWeight: 800, fontSize: REELS.fonte, lineHeight: 1.18, color: w.hl ? C.amber : C.text, opacity: falado ? 1 : 0.6 /* 24/11: 0,35 deixava a palavra futura ilegível no fundo escuro */, display: 'inline-block', transform: `scale(${ativo ? 1 + 0.06 * Math.min(1, 7 / String(w.d).length) * Math.sin(Math.PI * clamp01(ka)) : 1})` /* 28/10: palavra longa crescia 6% e comia o espaço ("emChapada") */, textShadow: w.hl && falado ? '0 0 24px rgba(245,158,11,0.55)' : 'none' }}>
                  {w.d}
                </span>
              );
            })}
          </span>
        ))}
      </div>
    </div>
  );
};

export const Progresso: React.FC<{ t: number; duracao: number; marcos: number[] }> = ({ t, duracao, marcos }) => {
  const p = clamp01(t / duracao);
  return (
    <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: 14, zIndex: 20 }}>
      <div style={{ position: 'absolute', inset: 0, background: 'rgba(255,255,255,0.07)' }} />
      <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${p * 100}%`, background: `linear-gradient(90deg, ${C.green}, ${C.greenLight} 55%, ${C.amber})`, boxShadow: '0 0 18px rgba(52,211,153,0.6)' }} />
      {marcos.map((segundo, i) => <div key={i} style={{ position: 'absolute', left: `${segundo / duracao * 100}%`, top: 0, bottom: 0, width: 4, background: t > segundo ? 'rgba(5,7,10,0.65)' : 'rgba(255,255,255,0.22)' }} />)}
    </div>
  );
};
