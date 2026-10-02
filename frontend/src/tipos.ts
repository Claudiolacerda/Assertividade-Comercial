/* O contrato entre o frontend e a API em Python.
 *
 * Estes tipos descrevem o que o backend REALMENTE devolve, não o que seria
 * conveniente. Onde o Python é livre (as tabelas do resultado, que variam com a
 * planilha que o cliente subiu), o tipo também é livre, e dizer isso é mais
 * honesto que inventar uma forma que o backend não garante. */

export type Papel = "admin" | "analista" | "cliente";
export type TipoOrganizacao = "agencia" | "direta";

export interface Organizacao {
  id: number;
  nome: string;
  slug: string;
  tipo: TipoOrganizacao;
}

export interface Empresa {
  id: number;
  nome: string;
  slug: string;
  segmento?: string | null;
  whatsapp?: string | null;
}

export interface Usuario {
  id: number;
  nome: string;
  email: string;
  papel: Papel;
  organizacao: Organizacao;
  empresas: Empresa[];
}

export interface RespostaToken {
  access_token: string;
  usuario: Usuario;
}

/** Um número do painel, já formatado pelo backend e com a meta resolvida. */
export interface Kpi {
  rotulo: string;
  texto: string;
  valor: number | null;
  formato: "int" | "brl" | "pct" | "x";
  explicacao?: string;
  meta_tipo?: "min" | "max" | null;
  meta_valor?: number | null;
  dentro_da_meta?: boolean;
}

/** Uma linha do diagnóstico. O nível chega com emoji embutido pelo motor. */
export interface Apontamento {
  "Área": string;
  "Nível": string;
  "Diagnóstico": string;
}

/** Quanto da planilha comercial o motor conseguiu aproveitar. */
export interface Cobertura {
  encontrados: number;
  total: number;
  ausentes: {
    campo: string;
    rotulo: string;
    impacto: "alto" | "médio" | "complementar";
    destrava: string;
  }[];
}

/** Uma linha de tabela. As colunas variam com a planilha, então a chave é livre;
 *  a ORDEM das chaves é a ordem das colunas e precisa ser preservada. */
export type LinhaTabela = Record<string, string | number | null>;

/* ---------------------------------------------------------------------- JET
 * A nota do mês. Espelha `backend/app/core/jet.py`: três pilares com peso, um
 * indicador por linha da régua e os pontos de melhoria já ordenados por
 * quanto cada um custou de Score. */

export type FaixaJet = "excelente" | "bom" | "atencao" | "critico";

export interface PilarJet {
  chave: "resultado" | "eficiencia" | "assertividade";
  rotulo: string;
  peso: number;
  /** Null quando nenhum indicador do pilar pôde ser pontuado. */
  nota: number | null;
  pontuado: boolean;
  indicadores_dentro: number;
  /** Peso depois da renormalização entre os pilares vivos. */
  peso_efetivo?: number;
}

export interface IndicadorJet {
  chave: string;
  rotulo: string;
  pilar: PilarJet["chave"];
  peso: number;
  sentido: "min" | "max";
  valor: number;
  meta: number;
  formato: string;
  /** 0 a 100. */
  atingimento: number;
  pontuado: boolean;
  /** Por que ficou fora, quando ficou. */
  motivo_fora: string;
  /** Pontos de Score que este indicador deixou na mesa. */
  custo: number;
}

export interface CampanhaJet {
  campanha: string;
  investido: number;
  nota: number;
  faixa: FaixaJet;
  fechados: number | null;
  leads: number;
  porque: string;
  /** "venda" quando a planilha liga campanha a cliente; "midia" quando não. */
  base: "venda" | "midia";
}

export interface MelhoriaJet {
  /** "indicador" custa Score; "registro" é lacuna de preenchimento. */
  tipo: "indicador" | "registro";
  chave: string | null;
  titulo: string;
  custo: number;
  valor: number | null;
  meta: number | null;
  formato: string | null;
  sentido: "min" | "max" | null;
  atingimento: number | null;
  texto: string;
  acao: string;
}

export interface Jet {
  score: number;
  faixa: FaixaJet;
  leitura: string;
  pilares: PilarJet[];
  indicadores: IndicadorJet[];
  campanhas: CampanhaJet[];
  melhorias: MelhoriaJet[];
  metas_ausentes: string[];
}

export interface ResultadoAnalise {
  kpis: Record<string, Kpi>;
  diagnostico: Apontamento[];
  tabelas: Record<string, LinhaTabela[]>;
  cobertura?: Cobertura;
  jet?: Jet;
}

/** O que a listagem devolve (AnaliseResumo no backend): sem o resultado. */
export interface AnaliseResumo {
  id: number;
  mes_referencia: string;
  versao: number;
  /** "concluida" | "processando" | "erro" — string livre no backend. */
  status: string;
  erro?: string | null;
  criada_em: string;
  kpis_resumo?: Record<string, number | null> | null;
}

/** O que o detalhe devolve: o resumo mais o resultado inteiro. */
export interface Analise extends AnaliseResumo {
  resultado: ResultadoAnalise | null;
}

/* ----------------------------------------------------------------- cadência */

export type CanalCadencia =
  | "whatsapp"
  | "ligacao"
  | "email"
  | "reuniao"
  | "espera"
  | "condicao"
  | "nota";

export interface DadosEtapa {
  canal: CanalCadencia;
  titulo: string;
  texto?: string;
  dia?: number;
  [chave: string]: unknown;
}

export interface Cadencia {
  id: number;
  nome: string;
  atualizada_em: string;
  fluxo: { nos: unknown[]; ligacoes: unknown[] };
  origem?: { analise_id?: number; mes_referencia?: string } | null;
  total_etapas?: number;
}

/* ---------------------------------------------------------------- WhatsApp */

export interface PreviaZap {
  texto: string;
  link: string;
  numero?: string | null;
  envio_automatico: boolean;
}
