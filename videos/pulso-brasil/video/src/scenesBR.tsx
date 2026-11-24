import React from 'react';
import { C, Camada, FONT, clamp01, pathDe, pop, prog } from './lib';
import { MapaBR } from './MapaBR';
import { LogoMarca } from './chrome';
import type { Cena, Janela, Tom } from './tipos';

const GREEN = '#34D399';
const GOLD = '#FBBF24';
const BLUE = '#60A5FA';
const cores: Record<Tom, string> = { verde: GREEN, ouro: GOLD, azul: BLUE, cinza: '#94A3B8' };
const box: React.CSSProperties = { background: 'linear-gradient(150deg,rgba(15,27,25,.96),rgba(7,14,18,.95))', border: '2px solid rgba(148,163,184,.35)', borderRadius: 32, padding: '26px 32px', boxShadow: '0 22px 70px rgba(0,0,0,.4)' };
const label: React.CSSProperties = { fontFamily: FONT, fontWeight: 800, fontSize: 28, letterSpacing: 2, color: C.muted, textTransform: 'uppercase' };
const headline: React.CSSProperties = { fontFamily: FONT, fontWeight: 900, fontSize: 72, lineHeight: 1.07, letterSpacing: -1.5, color: C.text };
const note: React.CSSProperties = { fontFamily: FONT, fontWeight: 600, fontSize: 26, lineHeight: 1.35, color: '#B7C6D3', textAlign: 'center' };
const linhas: React.CSSProperties = { whiteSpace: 'pre-line' };
const texto: React.CSSProperties = { fontFamily: FONT, lineHeight: 1.3, ...linhas };

const Bar: React.FC<{ value: number; color: string }> = ({ value, color }) => (
  <div style={{ width: '100%', height: 38, borderRadius: 12, background: 'rgba(148,163,184,.2)', overflow: 'hidden' }}>
    <div style={{ width: `${value}%`, height: '100%', background: color, borderRadius: 12 }} />
  </div>
);

const Numero: React.FC<{ valor: string; tamanho: number; cor: string; margem?: string }> = ({ valor, tamanho, cor, margem }) => (
  <div style={{ fontFamily: FONT, fontSize: tamanho, fontWeight: 900, color: cor, letterSpacing: tamanho >= 180 ? -8 : 0, lineHeight: 1.1, margin: margem }}>{valor}</div>
);

const Titulo: React.FC<{ chamada: string; titulo: string; cor: string; primeira?: boolean }> = ({ chamada, titulo, cor, primeira }) => (
  <>
    <div style={{ ...label, color: cor }}>{chamada}</div>
    <div style={{ ...headline, ...linhas, marginTop: primeira ? 16 : 18, fontSize: primeira ? 68 : 72 }}>{titulo}</div>
  </>
);

type ConteudoProps = { dados: Cena; t: number; inicio: number; cta: string };

const Conteudo: React.FC<ConteudoProps> = ({ dados, t, inicio, cta }) => {
  switch (dados.tipo) {
    case 'gancho_numero':
      return <>
        <Titulo {...dados} cor={GREEN} primeira />
        <Numero valor={dados.numero} tamanho={182} cor={GREEN} margem="12px 0 0" />
        <div style={{ ...label, fontSize: 32, color: C.text, letterSpacing: 1 }}>{dados.rotulo}</div>
        {dados.percentual !== undefined && <div style={{ marginTop: 12 }}><Bar value={dados.percentual} color={GREEN} /></div>}
        {dados.mapa_mt && <div style={{ marginTop: 22 }}><MapaBR altura={440} fracao={{}} rotuloMT={dados.mapa_mt} /></div>}
        {dados.pergunta && <div style={{ ...box, ...texto, marginTop: 8, borderColor: GREEN, fontWeight: 800, fontSize: 42 }}>{dados.pergunta}</div>}
      </>;
    case 'serie_linha': {
      const valores = dados.pontos.map((p) => p.valor);
      const baixo = Math.min(...valores);
      const alto = Math.max(...valores);
      const pontos: [number, number][] = dados.pontos.map((p, i) => [
        i / (valores.length - 1), alto === baixo ? 0.5 : (p.valor - baixo) / (alto - baixo),
      ]);
      return <>
        <Titulo {...dados} cor={BLUE} />
        <div style={{ ...box, borderColor: BLUE, marginTop: 32 }}>
          <svg width="100%" viewBox="0 0 820 420" style={{ opacity: prog(t, inicio, 0.5) }}>
            <path d={pathDe(pontos, 760, 340)} transform="translate(30 30)" stroke={BLUE} strokeWidth={9} fill="none" strokeLinejoin="round" />
          </svg>
          <div style={{ ...label, display: 'flex', justifyContent: 'space-between' }}>
            <span>{dados.pontos[0].rotulo} · {valores[0].toLocaleString('pt-BR')}</span>
            <span>{dados.pontos.at(-1)?.rotulo} · {valores.at(-1)?.toLocaleString('pt-BR')}</span>
          </div>
        </div>
      </>;
    }
    case 'barras':
      return <>
        <Titulo {...dados} cor={GREEN} />
        <div style={{ ...box, marginTop: 32 }}>
          {dados.itens.map((item, i) => {
            const cor = cores[item.cor ?? (i === 0 ? 'cinza' : 'verde')];
            return <div key={i} style={i === 0 ? undefined : { borderTop: '2px solid rgba(148,163,184,.25)', marginTop: 34, paddingTop: 26 }}>
              <div style={{ ...label, fontSize: 30, color: cor }}>{item.rotulo}</div>
              <Numero valor={item.numero} tamanho={i === 0 ? 110 : 132} cor={cor} margem="12px 0 18px" />
              <Bar value={item.percentual} color={cor} />
            </div>;
          })}
        </div>
        <div style={{ ...texto, fontWeight: 800, fontSize: 40, color: GREEN, textAlign: 'center', marginTop: 26 }}>{dados.nota}</div>
      </>;
    case 'mapa_regioes':
      return <>
        <Titulo {...dados} cor={GREEN} />
        <div style={{ ...box, marginTop: 32 }}><MapaBR altura={720} fracao={dados.regioes} rotuloMT={dados.mapa_mt} /></div>
      </>;
    case 'cards':
      return <>
        <Titulo {...dados} cor={cores[dados.itens[0].cor ?? 'verde']} />
        {dados.itens.map((item, i) => {
          const cor = cores[item.cor ?? 'verde'];
          return <div key={i} style={{ ...box, borderColor: cor, marginTop: i === 0 ? 34 : 28 }}>
            {item.numero && <Numero valor={item.numero} tamanho={180} cor={cor} />}
            {item.rotulo && <div style={{ ...label, color: cor, marginBottom: 18 }}>{item.rotulo}</div>}
            {item.percentual !== undefined && <Bar value={item.percentual} color={cor} />}
            <div style={{ ...texto, marginTop: item.percentual !== undefined ? 26 : 0, fontSize: item.numero ? 34 : 48, fontWeight: 800, color: item.rotulo ? C.text : cor }}>{item.titulo}</div>
            {item.texto && <div style={{ ...texto, fontSize: 35, fontWeight: 600, marginTop: 22 }}>{item.texto}</div>}
          </div>;
        })}
      </>;
    case 'checklist_acao':
      return <>
        <Titulo {...dados} cor={GOLD} />
        <div style={{ ...box, ...texto, fontWeight: 800, fontSize: 46, borderColor: GOLD, marginTop: 36 }}>{dados.destaque}</div>
        <div style={{ ...box, marginTop: 28 }}>
          <div style={{ ...label, color: GREEN }}>O QUE CONFERIR</div>
          <div style={{ ...texto, fontSize: 43, fontWeight: 800, marginTop: 18 }}>{dados.acao}</div>
          <div style={{ ...texto, fontSize: 34, fontWeight: 600, color: '#D6E0EA', marginTop: 26 }}>{dados.apoio}</div>
        </div>
      </>;
    case 'fecho_app':
      return <>
        <div style={{ display: 'flex', justifyContent: 'center', marginTop: 40 }}><LogoMarca size={170} k={clamp01(pop(t, inicio))} id="fecho" brilho={0.3} /></div>
        <div style={{ ...headline, marginTop: 42, textAlign: 'center', fontSize: 82 }}>PULSO <span style={{ color: GREEN }}>NEWS</span></div>
        <div style={{ fontFamily: FONT, fontSize: 34, fontWeight: 700, color: C.muted, textAlign: 'center', marginTop: 16 }}>DO PULSO DO CAMPO</div>
        <div style={{ ...box, ...texto, marginTop: 46, borderColor: GREEN, textAlign: 'center', fontSize: 49, fontWeight: 800, lineHeight: 1.2 }}>{cta}</div>
        <div style={{ ...label, textAlign: 'center', color: GOLD, marginTop: 46, fontSize: 32 }}>{dados.selo}</div>
      </>;
  }
};

export const CenaBR: React.FC<{ dados: Cena; t: number; janela: Janela; primeira: boolean; cta: string }> =
  ({ dados, t, janela, primeira, cta }) => (
    <Camada t={t} de={primeira ? -0.5 : janela.s - 0.15} ate={janela.e + (dados.tipo === 'fecho_app' ? 0.2 : 0)}
      fin={primeira ? 0.2 : 0.25} fout={0.2} dy={primeira ? 0 : 24}>
      <div style={{ position: 'absolute', left: 58, right: 58, top: 248, color: C.text }}>
        <Conteudo dados={dados} t={t} inicio={janela.s} cta={cta} />
        {dados.fonte && <div style={{ ...note, ...linhas, marginTop: 24 }}>{dados.fonte}</div>}
      </div>
    </Camada>
  );
