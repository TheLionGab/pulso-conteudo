import React from 'react';
import { C, Camada, FONT, ate, clamp01, pathDe, pop, prog } from './lib';
import { MapaBR } from './MapaBR';
import { BEAT, LogoMarca, TOPO_CENA } from './chrome';
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

/** Valor de um número exibido em pt-BR ("−2,48%", "R$ 145,50", "+4,2%"); null se não for número. */
// Mesma regra de episodio.py (valor_exibido): 1º número do texto; ponto é milhar, vírgula é decimal.
export const valorDe = (s: string): number | null => {
  const m = s.match(/([+\-−]?)\s*(?:R\$|US\$)?\s*(\d[\d.]*(?:,\d+)?)/);
  if (!m) return null;
  const v = Number(m[2].replace(/\./g, '').replace(',', '.'));
  return m[1] === '-' || m[1] === '−' ? -v : v;
};

/** Barras a partir do zero. Parte de um todo (o número é o próprio percentual, ex.: 90,8% da área):
 * escala fixa de 0 a 100%. Senão, proporcionais entre si: largura = |valor| ÷ maior |valor|;
 * com sinais misturados, o zero fica no meio (positivo à direita, negativo à esquerda). */
const larguras = (itens: { numero: string; percentual: number }[]) => {
  const vs = itens.map((i) => valorDe(i.numero));
  // (episodio.py garante número em todo item de barras; o null aqui é só defesa)
  if (vs.some((v) => v === null) || vs.every((v, i) => (v as number) >= 0 && Math.abs((v as number) - itens[i].percentual) <= 0.5)) {
    return { zero: 0, w: itens.map((i) => i.percentual) };
  }
  const num = vs as number[];
  const max = Math.max(...num.map(Math.abs)) || 1;
  const misto = num.some((v) => v < 0) && num.some((v) => v > 0);
  return { zero: misto ? 50 : num.every((v) => v <= 0) ? 100 : 0, w: num.map((v) => (v / max) * (misto ? 50 : 100)) };
};

const Bar: React.FC<{ value: number; color: string; zero?: number; k?: number }> = ({ value, color, zero = 0, k = 1 }) => {
  const w = Math.abs(value) * k;
  const esquerda = value < 0 ? zero - w : zero;
  return (
    <div style={{ position: 'relative', width: '100%', height: 38, borderRadius: 12, background: 'rgba(148,163,184,.2)', overflow: 'hidden' }}>
      <div style={{ position: 'absolute', left: `${esquerda}%`, width: `${w}%`, top: 0, bottom: 0, background: color, borderRadius: 12 }} />
      {zero > 0 && zero < 100 && <div style={{ position: 'absolute', left: `calc(${zero}% - 2px)`, width: 4, top: -6, bottom: -6, background: '#E2E8F0' }} />}
    </div>
  );
};

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
        {/* quadro 0 já mostra o número inteiro (é a capa no feed); o soco de escala só reforça */}
        <div style={{ transform: `scale(${1 + 0.06 * Math.exp(-4 * Math.max(0, t - inicio)) * Math.cos(9 * Math.max(0, t - inicio))})`, transformOrigin: '0% 50%' }}>
          <Numero valor={dados.numero} tamanho={182} cor={GREEN} margem="12px 0 0" />
        </div>
        <div style={{ ...label, fontSize: 32, color: C.text, letterSpacing: 1 }}>{dados.rotulo}</div>
        {dados.percentual !== undefined && <div style={{ marginTop: 12 }}><Bar value={dados.percentual} color={GREEN} k={prog(t, inicio + 0.2, 0.8)} /></div>}
        {dados.mapa_mt && <div style={{ marginTop: 22 }}><MapaBR altura={440} fracao={{}} rotuloMT={dados.mapa_mt} /></div>}
        {dados.pergunta && <div style={{ ...box, ...texto, marginTop: 8, borderColor: GREEN, fontWeight: 800, fontSize: 42 }}>{dados.pergunta}</div>}
      </>;
    case 'serie_linha': {
      const valores = dados.pontos.map((p) => p.valor);
      const baixo = Math.min(...valores);
      const alto = Math.max(...valores);
      const pontos: [number, number][] = dados.pontos.map((p, i) => [
        // y do SVG cresce para baixo: o maior valor fica em cima
        i / (valores.length - 1), alto === baixo ? 0.5 : (alto - p.valor) / (alto - baixo),
      ]);
      // Eixo explícito: a linha usa a faixa mínimo–máximo (não começa no zero), então as duas
      // guias mostram o valor de cada extremo e o pico leva data e valor.
      const iPico = valores.indexOf(alto);
      const casas = Math.min(4, Math.max(0, ...valores.map((v) => (String(v).split('.')[1] ?? '').length)));
      const num = (v: number) => v.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });
      const X = (x: number) => 30 + x * 640;
      const Y = (y: number) => 60 + y * 300;
      const [px, py] = pontos[iPico];
      const kLinha = prog(t, inicio, 1.2);
      const kPico = prog(t, inicio + 0.9, 0.4);
      return <>
        <Titulo {...dados} cor={BLUE} />
        <div style={{ ...box, borderColor: BLUE, marginTop: 32 }}>
          <svg width="100%" viewBox="0 0 820 420" style={{ opacity: prog(t, inicio, 0.5) }}>
            {/* guia do máximo (o valor vai no rótulo do pico) e do mínimo, com o valor à direita */}
            {[0, 1].map((y) => <line key={y} x1={30} x2={680} y1={Y(y)} y2={Y(y)} stroke="rgba(148,163,184,.35)" strokeWidth={2} strokeDasharray="8 10" />)}
            {alto !== baixo && <text x={790} y={Y(1) + 40} textAnchor="end" fill={C.muted} fontFamily={FONT} fontWeight={700} fontSize={26}>MÍN {num(baixo)}</text>}
            <path d={pathDe(ate(pontos, kLinha), 640, 300)} transform="translate(30 60)" stroke={BLUE} strokeWidth={9} fill="none" strokeLinejoin="round" strokeLinecap="round" />
            {kPico > 0 && <g opacity={kPico}>
              <circle cx={X(px)} cy={Y(py)} r={14} fill={GOLD} stroke="#05070A" strokeWidth={4} />
              <text x={Math.min(Math.max(X(px), 130), 560)} y={Y(py) - 26} textAnchor="middle" fill={GOLD} fontFamily={FONT} fontWeight={900} fontSize={30}>
                PICO {dados.pontos[iPico].rotulo} · {num(alto)}
              </text>
            </g>}
          </svg>
          <div style={{ ...label, display: 'flex', justifyContent: 'space-between' }}>
            <span>{dados.pontos[0].rotulo} · {num(valores[0])}</span>
            <span>{dados.pontos.at(-1)?.rotulo} · {num(valores[valores.length - 1])}</span>
          </div>
        </div>
      </>;
    }
    case 'barras': {
      const { zero, w } = larguras(dados.itens);
      return <>
        <Titulo {...dados} cor={GREEN} />
        <div style={{ ...box, marginTop: 32 }}>
          {dados.itens.map((item, i) => {
            const cor = cores[item.cor ?? (i === 0 ? 'cinza' : 'verde')];
            return <div key={i} style={i === 0 ? undefined : { borderTop: '2px solid rgba(148,163,184,.25)', marginTop: 34, paddingTop: 26 }}>
              <div style={{ ...label, fontSize: 30, color: cor }}>{item.rotulo}</div>
              <Numero valor={item.numero} tamanho={i === 0 ? 110 : 132} cor={cor} margem="12px 0 18px" />
              <Bar value={w[i]} zero={zero} color={cor} k={prog(t, inicio + 0.25 + 0.35 * i, 0.7)} />
            </div>;
          })}
          {zero === 50 && <div style={{ ...label, fontSize: 22, display: 'flex', justifyContent: 'space-between', marginTop: 12 }}><span>◀ CAIU</span><span>0</span><span>SUBIU ▶</span></div>}
        </div>
        <div style={{ ...texto, fontWeight: 800, fontSize: 40, color: GREEN, textAlign: 'center', marginTop: 26 }}>{dados.nota}</div>
      </>;
    }
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
        {/* CTA como botão: entra com mola depois do texto e pulsa na batida da trilha */}
        <div style={{ display: 'flex', justifyContent: 'center', marginTop: 44 }}>
          <div style={{
            transform: `scale(${(0.6 + 0.4 * clamp01(pop(t, inicio + 0.6))) * (1 + 0.035 * Math.exp(-((Math.max(0, t - inicio) % BEAT) / BEAT) * 5))})`,
            opacity: clamp01(pop(t, inicio + 0.6) * 1.5),
            background: `linear-gradient(90deg, ${GREEN}, #10B981)`, borderRadius: 999, padding: '26px 52px',
            boxShadow: '0 0 50px rgba(52,211,153,.45)', fontFamily: FONT, fontWeight: 900, fontSize: 40, letterSpacing: 1, color: '#04130D', textAlign: 'center',
          }}>{dados.selo}</div>
        </div>
      </>;
  }
};

export const CenaBR: React.FC<{ dados: Cena; t: number; janela: Janela; primeira: boolean; cta: string }> =
  ({ dados, t, janela, primeira, cta }) => (
    <Camada t={t} de={primeira ? -0.5 : janela.s - 0.15} ate={janela.e + (dados.tipo === 'fecho_app' ? 0.2 : 0)}
      fin={primeira ? 0.2 : 0.25} fout={0.2} dy={primeira ? 0 : 24}>
      <div style={{ position: 'absolute', left: 58, right: 58, top: TOPO_CENA, color: C.text }}>
        <Conteudo dados={dados} t={t} inicio={janela.s} cta={cta} />
        {dados.fonte && <div style={{ ...note, ...linhas, marginTop: 24 }}>{dados.fonte}</div>}
      </div>
    </Camada>
  );
