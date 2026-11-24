export type Tom = 'verde' | 'azul' | 'ouro' | 'cinza';
type Base = { id: string; clipe?: string; fonte?: string };
type Abertura = Base & { chamada: string; titulo: string };
type Item = { rotulo: string; numero: string; percentual: number; cor?: Tom };
type Card = { titulo: string; rotulo?: string; texto?: string; cor?: Tom; numero?: string; percentual?: number };

export type Cena =
  | (Abertura & { tipo: 'gancho_numero'; numero: string; rotulo: string; percentual?: number; mapa_mt?: string; pergunta?: string })
  | (Abertura & { tipo: 'serie_linha'; pontos: {rotulo: string; valor: number}[] })
  | (Abertura & { tipo: 'barras'; itens: Item[]; nota: string })
  | (Abertura & { tipo: 'mapa_regioes'; regioes: Record<string, number>; mapa_mt?: string })
  | (Abertura & { tipo: 'cards'; itens: Card[] })
  | (Abertura & { tipo: 'checklist_acao'; destaque: string; acao: string; apoio: string })
  | (Base & { tipo: 'fecho_app'; selo: string });

export type Janela = { s: number; e: number };
export type Palavra = Janela & { d: string; hl: boolean };
export type Timeline = {
  duracao: number;
  cenas: Record<string, Janela>;
  palavras: Palavra[];
  legendas: (Janela & { w: number[] })[];
};
export type Props = {
  episodio: { cabecalho: string; cenas: Cena[]; cta_final: string };
  timeline: Timeline;
  capa: boolean;
};
