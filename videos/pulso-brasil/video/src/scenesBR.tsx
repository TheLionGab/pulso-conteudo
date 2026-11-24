import React from 'react';
import { C, Camada, FONT, cena, clamp01, pop } from './lib';
import { MapaBR } from './MapaBR';
import { LogoMarca } from './chrome';

const GREEN = '#34D399';
const GOLD = '#FBBF24';
const BLUE = '#60A5FA';
const box: React.CSSProperties = { background: 'linear-gradient(150deg,rgba(15,27,25,.96),rgba(7,14,18,.95))', border: '2px solid rgba(148,163,184,.35)', borderRadius: 32, padding: '26px 32px', boxShadow: '0 22px 70px rgba(0,0,0,.4)' };
const label: React.CSSProperties = { fontFamily: FONT, fontWeight: 800, fontSize: 28, letterSpacing: 2, color: C.muted, textTransform: 'uppercase' };
const headline: React.CSSProperties = { fontFamily: FONT, fontWeight: 900, fontSize: 72, lineHeight: 1.07, letterSpacing: -1.5, color: C.text };
const note: React.CSSProperties = { fontFamily: FONT, fontWeight: 600, fontSize: 26, lineHeight: 1.35, color: '#B7C6D3', textAlign: 'center' };
const Source: React.FC<{ children?: React.ReactNode }> = ({ children }) => <div style={{ ...note, marginTop: 24 }}>{children ?? 'CONAB · soja 2026/27 · até 30/10/2026'}</div>;
const Page: React.FC<{ name: string; t: number; children: React.ReactNode; first?: boolean }> = ({ name, t, children, first = false }) => {
  const c = cena(name);
  return <Camada t={t} de={first ? -0.5 : c.s - 0.15} ate={c.e} fin={first ? 0.2 : 0.25} fout={0.2} dy={first ? 0 : 24}>
    <div style={{ position: 'absolute', left: 58, right: 58, top: 248, color: C.text }}>{children}</div>
  </Camada>;
};
const Bar: React.FC<{ value: number; color: string }> = ({ value, color }) => <div style={{ width: '100%', height: 38, borderRadius: 12, background: 'rgba(148,163,184,.2)', overflow: 'hidden' }}>
  <div style={{ width: `${value}%`, height: '100%', background: color, borderRadius: 12 }} />
</div>;

export const GanchoBR: React.FC<{ t: number }> = ({ t }) => <Page name="intro" t={t} first>
  <div style={{ ...label, color: GREEN }}>SOJA · MATO GROSSO</div>
  <div style={{ ...headline, marginTop: 16, fontSize: 68 }}>O plantio avançou.</div>
  <div style={{ fontFamily: FONT, fontSize: 182, fontWeight: 900, color: GREEN, letterSpacing: -8, lineHeight: 1.05, marginTop: 12 }}>90,8%</div>
  <div style={{ ...label, fontSize: 32, color: C.text, letterSpacing: 1 }}>DA ÁREA PREVISTA SEMEADA</div>
  <div style={{ marginTop: 12 }}><Bar value={90.8} color={GREEN} /></div>
  <div style={{ marginTop: 22 }}><MapaBR altura={440} fracao={{}} rotuloMT="90,8%" /></div>
  <div style={{ ...box, marginTop: 8, borderColor: GREEN, fontFamily: FONT, fontWeight: 800, fontSize: 42, lineHeight: 1.2 }}>Como estão essas lavouras?</div>
  <Source />
</Page>;

export const OniBR: React.FC<{ t: number }> = ({ t }) => <Page name="oni" t={t}>
  <div style={{ ...label, color: BLUE }}>O CONTEXTO NO BRASIL</div>
  <div style={{ ...headline, marginTop: 18 }}>Na mesma série,<br />o retrato é este:</div>
  <div style={{ ...box, marginTop: 30, borderColor: BLUE }}>
    <div style={{ fontFamily: FONT, fontSize: 180, fontWeight: 900, color: BLUE, letterSpacing: -7, lineHeight: 1.1 }}>54,3%</div>
    <div style={{ ...label, color: C.text, margin: '12px 0 24px' }}>DA ÁREA SEMEADA</div>
    <Bar value={54.3} color={BLUE} />
    <div style={{ fontFamily: FONT, fontSize: 34, fontWeight: 700, color: '#D8E3ED', lineHeight: 1.4, marginTop: 26 }}>Agregado dos 12 estados<br />acompanhados pela Conab.</div>
  </div>
  <div style={{ ...box, marginTop: 24, fontFamily: FONT, fontSize: 34, fontWeight: 700, lineHeight: 1.3 }}>Esses estados correspondem<br />a <span style={{ color: BLUE }}>95% da área cultivada.</span></div>
  <Source>CONAB · até 30/10/2026<br />Não é média simples dos estados.</Source>
</Page>;

export const RegioesBR: React.FC<{ t: number }> = ({ t }) => <Page name="regioes" t={t}>
  <div style={{ ...label, color: GREEN }}>MATO GROSSO · UMA SEMANA</div>
  <div style={{ ...headline, marginTop: 18 }}>O avanço<br />na mesma base.</div>
  <div style={{ ...box, marginTop: 32 }}>
    <div style={{ ...label, fontSize: 30 }}>ATÉ 23/10</div>
    <div style={{ fontFamily: FONT, fontSize: 110, fontWeight: 900, color: '#B7C6D3', lineHeight: 1.15, margin: '12px 0 18px' }}>75,78%</div>
    <Bar value={75.78} color="#94A3B8" />
    <div style={{ borderTop: '2px solid rgba(148,163,184,.25)', margin: '34px 0 26px' }} />
    <div style={{ ...label, fontSize: 30, color: GREEN }}>ATÉ 30/10</div>
    <div style={{ fontFamily: FONT, fontSize: 132, fontWeight: 900, color: GREEN, lineHeight: 1.15, margin: '12px 0 18px' }}>90,8%</div>
    <Bar value={90.8} color={GREEN} />
  </div>
  <div style={{ fontFamily: FONT, fontWeight: 800, fontSize: 40, color: GREEN, textAlign: 'center', marginTop: 26 }}>+15,02 pontos percentuais</div>
  <Source>CONAB · MT · área prevista semeada<br />Barras na mesma escala de 0 a 100%.</Source>
</Page>;

export const AlertaBR: React.FC<{ t: number }> = ({ t }) => <Page name="alerta" t={t}>
  <div style={{ ...label, color: GREEN }}>A LEITURA DA CONAB</div>
  <div style={{ ...headline, marginTop: 20 }}>O quadro<br />é favorável.</div>
  <div style={{ ...box, marginTop: 34, borderColor: GREEN }}>
    <div style={{ fontFamily: FONT, fontSize: 48, fontWeight: 800, color: GREEN, lineHeight: 1.2 }}>Desenvolvimento<br />vegetativo favorável</div>
    <div style={{ fontFamily: FONT, fontSize: 35, fontWeight: 600, color: C.text, marginTop: 22 }}>Situação fitossanitária normal.</div>
  </div>
  <div style={{ ...box, marginTop: 28, borderColor: GOLD }}>
    <div style={{ ...label, color: GOLD }}>A RESSALVA É PONTUAL</div>
    <div style={{ fontFamily: FONT, fontSize: 43, fontWeight: 800, color: C.text, lineHeight: 1.25, marginTop: 18 }}>Há diferenças no<br />estabelecimento das lavouras.</div>
  </div>
  <Source>CONAB · Monitoramento de 03/11/2026<br />Não demonstra perda generalizada.</Source>
</Page>;

export const BolsoBR: React.FC<{ t: number }> = ({ t }) => <Page name="bolso" t={t}>
  <div style={{ ...label, color: GOLD }}>PARA QUEM JÁ PLANTOU</div>
  <div style={{ ...headline, marginTop: 20 }}>O próximo olhar<br />é no talhão.</div>
  <div style={{ ...box, marginTop: 36, borderColor: GOLD }}>
    <div style={{ fontFamily: FONT, fontSize: 46, fontWeight: 800, lineHeight: 1.25 }}>Área semeada<br /><span style={{ color: GOLD }}>não mede produtividade.</span></div>
  </div>
  <div style={{ ...box, marginTop: 28 }}>
    <div style={{ ...label, color: GREEN }}>O QUE CONFERIR</div>
    <div style={{ fontFamily: FONT, fontSize: 43, fontWeight: 800, lineHeight: 1.3, marginTop: 18 }}>Como as plantas<br />estão se estabelecendo.</div>
    <div style={{ fontFamily: FONT, fontSize: 34, fontWeight: 600, lineHeight: 1.35, color: '#D6E0EA', marginTop: 26 }}>Acompanhamento com<br />assistência técnica.</div>
  </div>
  <Source>Informação para acompanhamento.<br />Não é prescrição de manejo.</Source>
</Page>;

export const FechoBR: React.FC<{ t: number }> = ({ t }) => {
  const c = cena('fecho');
  return <Page name="fecho" t={t}>
    <div style={{ display: 'flex', justifyContent: 'center', marginTop: 40 }}><LogoMarca size={170} k={clamp01(pop(t, c.s))} id="fechoSoja" brilho={0.3} /></div>
    <div style={{ ...headline, marginTop: 42, textAlign: 'center', fontSize: 82 }}>PULSO <span style={{ color: GREEN }}>NEWS</span></div>
    <div style={{ fontFamily: FONT, fontSize: 34, fontWeight: 700, color: C.muted, textAlign: 'center', marginTop: 16 }}>DO PULSO DO CAMPO</div>
    <div style={{ ...box, marginTop: 46, borderColor: GREEN, textAlign: 'center' }}>
      <div style={{ fontFamily: FONT, fontSize: 49, fontWeight: 800, lineHeight: 1.2 }}>Informação para<br />a decisão no campo.</div>
    </div>
    <div style={{ ...label, textAlign: 'center', color: GOLD, marginTop: 46, fontSize: 32 }}>DADOS ATÉ 30/10/2026</div>
    <Source>Fonte: CONAB · safra 2026/27<br />Voz sintética · imagens ilustrativas.</Source>
  </Page>;
};
