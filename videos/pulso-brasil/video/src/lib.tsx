import React from 'react';
import { Easing, random, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import '@fontsource/inter/latin-500.css';
import '@fontsource/inter/latin-600.css';
import '@fontsource/inter/latin-700.css';
import '@fontsource/inter/latin-800.css';
import '@fontsource/inter/latin-900.css';
export const FPS = 30;
export const W = 1080;
export const H = 1920;

export const C = {
  bg: '#05070A',
  bg2: '#080C12',
  surface: '#0F1419',
  surface2: '#161B22',
  line: '#222C38',
  text: '#FFFFFF',
  muted: '#94A3B8',
  dim: '#4B5563',
  amber: '#F59E0B',
  amberDeep: '#D97706',
  amberSoft: 'rgba(245,158,11,0.14)',
  red: '#EF4444',
  redSoft: 'rgba(239,68,68,0.14)',
  green: '#10B981',
  greenLight: '#34D399',
  mint: '#6EE7B7',
  greenSoft: 'rgba(16,185,129,0.14)',
  grey: '#717F94',
};

export const FONT = 'Inter, system-ui, sans-serif';

/** tempo atual em segundos */
export const useT = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return frame / fps;
};

export const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
export const lerp = (a: number, b: number, k: number) => a + (b - a) * k;

/** progresso 0..1 de `a` a `a+d` com easing */
export const prog = (t: number, a: number, d: number, ease: (x: number) => number = Easing.out(Easing.cubic)) =>
  ease(clamp01((t - a) / d));

export const pop = (t: number, a: number, cfg: Partial<{ damping: number; stiffness: number; mass: number }> = {}) =>
  t < a ? 0 : spring({ frame: (t - a) * FPS, fps: FPS, config: { damping: 13, stiffness: 170, mass: 0.7, ...cfg } });

/** opacidade de janela [a, b] com fades */
export const janela = (t: number, a: number, b: number, fin = 0.25, fout = 0.25) =>
  Math.min(prog(t, a, fin, Easing.out(Easing.quad)), 1 - prog(t, b - fout, fout, Easing.in(Easing.quad)));

export const shake = (t: number, a: number, dur = 0.45, amp = 22, seed = 'k') => {
  if (t < a || t > a + dur) return { x: 0, y: 0, r: 0 };
  const k = 1 - (t - a) / dur;
  const f = Math.floor(t * FPS);
  return {
    x: (random(`${seed}x${f}`) - 0.5) * 2 * amp * k,
    y: (random(`${seed}y${f}`) - 0.5) * 2 * amp * k,
    r: (random(`${seed}r${f}`) - 0.5) * 2 * 1.2 * k,
  };
};

export const contar = (t: number, a: number, d: number, de: number, ate: number) =>
  lerp(de, ate, prog(t, a, d, (x) => (1 - Math.pow(2, -10 * x)) / (1 - Math.pow(2, -10))));

export const fmt = (n: number, casas = 1) =>
  n.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });

/** Camada que entra/sai com fade + leve deslocamento */
export const Camada: React.FC<{
  t: number;
  de: number;
  ate: number;
  children: React.ReactNode;
  dy?: number;
  fin?: number;
  fout?: number;
  style?: React.CSSProperties;
}> = ({ t, de, ate, children, dy = 40, fin = 0.35, fout = 0.3, style }) => {
  if (t < de - 0.05 || t > ate + 0.05) return null;
  const o = janela(t, de, ate, fin, fout);
  const kin = prog(t, de, fin + 0.15, Easing.out(Easing.cubic));
  const kout = prog(t, ate - fout, fout, Easing.in(Easing.cubic));
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        opacity: o,
        transform: `translateY(${(1 - kin) * dy - kout * dy * 0.6}px) scale(${1 - kout * 0.03})`,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

export const Pill: React.FC<{
  children: React.ReactNode;
  cor?: string;
  fundo?: string;
  size?: number;
  style?: React.CSSProperties;
  solid?: boolean;
}> = ({ children, cor = C.amber, fundo, size = 28, style, solid }) => (
  <div
    style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 10,
      padding: `${size * 0.32}px ${size * 0.75}px`,
      borderRadius: 999,
      border: `2.5px solid ${cor}`,
      background: solid ? cor : fundo ?? 'rgba(5,7,10,0.72)',
      color: solid ? C.bg : cor,
      fontFamily: FONT,
      fontWeight: 800,
      fontSize: size,
      letterSpacing: 0.6,
      textTransform: 'uppercase',
      whiteSpace: 'nowrap',
      ...style,
    }}
  >
    {children}
  </div>
);

export const Check: React.FC<{ size?: number; cor?: string; k?: number }> = ({ size = 22, cor = C.greenLight, k = 1 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24">
    <path
      d="M4 12.5l5 5L20 6.5"
      fill="none"
      stroke={cor}
      strokeWidth={3.4}
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeDasharray={30}
      strokeDashoffset={30 * (1 - k)}
    />
  </svg>
);

export const Cadeado: React.FC<{ size?: number; cor?: string; aberto?: number }> = ({ size = 40, cor = C.grey, aberto = 0 }) => (
  <svg width={size} height={size} viewBox="0 0 40 40">
    <path
      d={`M12 18 V13 a8 8 0 0 1 16 0 V${lerp(18, 10, aberto)}`}
      fill="none"
      stroke={cor}
      strokeWidth={3.6}
      strokeLinecap="round"
      transform={`translate(${aberto * 10} ${-aberto * 4})`}
    />
    <rect x={8} y={18} width={24} height={17} rx={4} fill={cor} />
    <circle cx={20} cy={26} r={2.6} fill={C.bg} />
  </svg>
);

export const Seta: React.FC<{ size?: number; cor?: string }> = ({ size = 34, cor = C.muted }) => (
  <svg width={size} height={size} viewBox="0 0 24 24">
    <path d="M12 3v17M5 13l7 7 7-7" fill="none" stroke={cor} strokeWidth={2.6} strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

/** caminho de série com ruído determinístico */
export const serie = (n: number, f: (x: number) => number, seed: string, ruido = 0.012) =>
  Array.from({ length: n }, (_, i) => {
    const x = i / (n - 1);
    const r = (random(`${seed}${i}`) - 0.5) * 2 * ruido + (random(`${seed}b${Math.floor(i / 3)}`) - 0.5) * ruido;
    return [x, f(x) + r] as [number, number];
  });

export const pathDe = (pts: [number, number][], w: number, h: number) =>
  pts.map(([x, y], i) => `${i ? 'L' : 'M'}${(x * w).toFixed(1)} ${(y * h).toFixed(1)}`).join(' ');

/** recorta a série até a fração `p` de x (interpola o último ponto) */
export const ate = (pts: [number, number][], p: number) => {
  const out: [number, number][] = [];
  for (let i = 0; i < pts.length; i++) {
    if (pts[i][0] <= p) out.push(pts[i]);
    else {
      const a = pts[i - 1];
      const b = pts[i];
      if (a) {
        const k = (p - a[0]) / (b[0] - a[0]);
        out.push([p, lerp(a[1], b[1], k)]);
      }
      break;
    }
  }
  return out;
};
