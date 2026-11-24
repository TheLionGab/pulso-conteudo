import React from 'react';
import { C, FONT, clamp01 } from './lib';
import { PATHS, PATH_MT } from './mapa-paths';

// Mapa por região (malha IBGE). A cor é a fração real de municípios de cada região (dossiê G1, ECMWF):
// a região inteira recebe uma cor só, porque o dado é por região. Não desenha mancha de chuva nem área.
const ESCALA = 24.2;
const LARGURA = 968;
const ALTURA = 953;
const xy = (lon: number, lat: number) => ({ x: (lon + 74) * ESCALA, y: (5.4 - lat) * ESCALA });

const cor = (f: number) => {
  const a = [51, 60, 74];
  const b = [37, 130, 246];
  const m = a.map((v, i) => Math.round(v + (b[i] - v) * clamp01(f)));
  return `rgb(${m[0]},${m[1]},${m[2]})`;
};

const POS: Record<string, { lon: number; lat: number }> = {
  Norte: { lon: -60.5, lat: -4 },
  Nordeste: { lon: -41.5, lat: -8.5 },
  'Centro-Oeste': { lon: -54, lat: -15.5 },
  Sudeste: { lon: -45.5, lat: -20 },
  Sul: { lon: -52, lat: -28 },
};

export const MapaBR: React.FC<{
  altura: number;
  fracao: Record<string, number>;
  rotulos?: Record<string, string>;
  corForcada?: Record<string, string>;
  destaque?: string;
  rotuloMT?: string; // número do recorte: desenha o contorno de Mato Grosso por cima das regiões
}> = ({ altura, fracao, rotulos = {}, corForcada = {}, destaque, rotuloMT }) => (
  <svg viewBox={`0 0 ${LARGURA} ${ALTURA}`} height={altura} width={(altura * LARGURA) / ALTURA} style={{ display: 'block', margin: '0 auto', overflow: 'visible' }}>
    {Object.keys(PATHS).map((r) => (
      <path
        key={r}
        d={PATHS[r]}
        fill={corForcada[r] ?? cor(fracao[r] ?? 0)}
        stroke={destaque === r ? '#FBBF24' : '#0B1017'}
        strokeWidth={destaque === r ? 8 : 4}
        strokeLinejoin="round"
      />
    ))}
    {Object.entries(rotulos).map(([r, txt]) => {
      const q = xy(POS[r].lon, POS[r].lat);
      return (
        <g key={r} fontFamily={FONT} textAnchor="middle" fill={C.text} paintOrder="stroke" stroke="#05070A" strokeWidth={10} strokeLinejoin="round">
          <text x={q.x} y={q.y} fontSize={36} fontWeight={800} paintOrder="stroke">{r.toUpperCase()}</text>
          <text x={q.x} y={q.y + 62} fontSize={62} fontWeight={900} paintOrder="stroke">{txt}</text>
        </g>
      );
    })}
    {rotuloMT !== undefined && (
      <g fontFamily={FONT} textAnchor="middle" fill={C.text} paintOrder="stroke" stroke="#05070A" strokeWidth={10} strokeLinejoin="round">
        <path d={PATH_MT} fill="#FBBF24" fillOpacity={0.28} stroke="#FBBF24" strokeWidth={8} paintOrder="normal" />
        <text x={xy(-55.6, -12.2).x} y={xy(-55.6, -12.2).y} fontSize={36} fontWeight={800} paintOrder="stroke">MT</text>
        <text x={xy(-55.6, -12.2).x} y={xy(-55.6, -12.2).y + 62} fontSize={62} fontWeight={900} paintOrder="stroke">{rotuloMT}</text>
      </g>
    )}
  </svg>
);
