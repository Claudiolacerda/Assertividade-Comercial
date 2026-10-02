import type {
  Analise,
  AnaliseResumo,
  Cadencia,
  Empresa,
  Organizacao,
  PreviaZap,
  RespostaToken,
  TipoOrganizacao,
  Usuario,
} from "./tipos";

/* Cliente HTTP: guarda o token, diz qual cliente da carteira está em foco e
   traduz erro da API em mensagem legível. */

const CHAVE_TOKEN = "neriah_token";
const CHAVE_EMPRESA = "neriah_empresa";

export function lerToken() {
  try {
    return localStorage.getItem(CHAVE_TOKEN);
  } catch {
    return null;
  }
}

export function guardarToken(token: string | null) {
  try {
    if (token) localStorage.setItem(CHAVE_TOKEN, token);
    else localStorage.removeItem(CHAVE_TOKEN);
  } catch {
    /* navegação privada: a sessão vale só para esta aba */
  }
}

/* Cliente em foco: vai no cabeçalho X-Empresa de toda requisição. O backend
   ainda confere se ele pertence à organização — isto aqui é conveniência, não
   controle de acesso. */
export function lerEmpresa() {
  try {
    const v = localStorage.getItem(CHAVE_EMPRESA);
    return v ? Number(v) : null;
  } catch {
    return null;
  }
}

export function guardarEmpresa(id: number | null) {
  try {
    if (id) localStorage.setItem(CHAVE_EMPRESA, String(id));
    else localStorage.removeItem(CHAVE_EMPRESA);
  } catch {
    /* idem */
  }
}

export class ErroApi extends Error {
  readonly status: number;

  constructor(mensagem: string, status: number) {
    super(mensagem);
    this.name = "ErroApi";
    this.status = status;
  }
}

async function mensagemDeErro(resposta: Response): Promise<string> {
  try {
    const corpo = await resposta.json();
    const d = corpo?.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return d.map((e: { msg?: string }) => e.msg || String(e)).join(" ");
  } catch {
    /* resposta sem JSON */
  }
  if (resposta.status === 401) return "Sessão expirada. Faça login novamente.";
  return `Falha na requisição (${resposta.status}).`;
}

function cabecalhos(extra: HeadersInit = {}, comCorpo = false): Record<string, string> {
  const h: Record<string, string> = { ...(extra as Record<string, string>) };
  const token = lerToken();
  if (token) h.Authorization = `Bearer ${token}`;
  const empresa = lerEmpresa();
  if (empresa) h["X-Empresa"] = String(empresa);
  if (comCorpo) h["Content-Type"] = "application/json";
  return h;
}

async function requisitar<T = unknown>(caminho: string, opcoes: RequestInit = {}): Promise<T> {
  const temCorpoJson = Boolean(opcoes.body) && !(opcoes.body instanceof FormData);
  let resposta: Response;
  try {
    resposta = await fetch(`/api${caminho}`, {
      ...opcoes,
      headers: cabecalhos(opcoes.headers, temCorpoJson),
    });
  } catch {
    throw new ErroApi("Não consegui falar com o servidor. Verifique sua conexão.", 0);
  }
  if (resposta.status === 401) {
    guardarToken(null);
    throw new ErroApi(await mensagemDeErro(resposta), 401);
  }
  if (!resposta.ok) throw new ErroApi(await mensagemDeErro(resposta), resposta.status);
  if (resposta.status === 204) return null as T;
  return resposta.json() as Promise<T>;
}

async function baixar(caminho: string, nome: string) {
  const resposta = await fetch(`/api${caminho}`, { headers: cabecalhos() });
  if (!resposta.ok) throw new ErroApi(await mensagemDeErro(resposta), resposta.status);
  const blob = await resposta.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = nome;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export const api = {
  // ---- autenticação ----
  login: (email: string, senha: string) =>
    requisitar<RespostaToken>("/auth/login", { method: "POST", body: JSON.stringify({ email, senha }) }),

  cadastrar: (dados: Record<string, unknown>) => requisitar<RespostaToken>("/auth/cadastro", { method: "POST", body: JSON.stringify(dados) }),

  eu: () => requisitar<Usuario>("/auth/eu"),

  usuarios: () => requisitar<Usuario[]>("/auth/usuarios"),

  criarUsuario: (dados: Record<string, unknown>) => requisitar<Usuario>("/auth/usuarios", { method: "POST", body: JSON.stringify(dados) }),

  // ---- organização ----
  organizacao: () => requisitar<Organizacao>("/organizacao"),

  mudarTipoOrganizacao: (tipo: TipoOrganizacao) =>
    requisitar("/organizacao/tipo", { method: "PUT", body: JSON.stringify({ tipo }) }),

  // ---- carteira ----
  empresas: () => requisitar<Empresa[]>("/empresas"),

  carteira: () => requisitar<Empresa[]>("/empresas/carteira"),

  criarEmpresa: (dados: Record<string, unknown>) => requisitar<Empresa>("/empresas", { method: "POST", body: JSON.stringify(dados) }),

  arquivarEmpresa: (id: number) => requisitar(`/empresas/${id}`, { method: "DELETE" }),

  // ---- análises ----
  analises: () => requisitar<AnaliseResumo[]>("/analises"),

  analise: (id: number | string) => requisitar<Analise>(`/analises/${id}`),

  evolucao: () => requisitar<Record<string, unknown>[]>("/analises/evolucao"),

  excluirAnalise: (id: number) => requisitar(`/analises/${id}`, { method: "DELETE" }),

  configuracao: () => requisitar<Record<string, unknown>>("/configuracao"),

  salvarConfiguracao: (dados: Record<string, unknown>) =>
    requisitar("/configuracao", { method: "PUT", body: JSON.stringify(dados) }),

  enviarAnalise: ({
    arquivosMeta,
    arquivosReunioes,
    mesReferencia,
  }: {
    arquivosMeta: File[];
    arquivosReunioes: File[];
    mesReferencia?: string;
  }) => {
    const form = new FormData();
    arquivosMeta.forEach((a) => form.append("arquivos_meta", a));
    arquivosReunioes.forEach((a) => form.append("arquivos_reunioes", a));
    if (mesReferencia) form.append("mes_referencia", mesReferencia);
    return requisitar<Analise>("/analises", { method: "POST", body: form });
  },

  baixarExcel: (id: number, nome: string) => baixar(`/analises/${id}/excel`, nome),

  // ---- relatório de WhatsApp ----
  previaZap: (id: number | string, completo = false) =>
    requisitar<PreviaZap>(`/analises/${id}/whatsapp?completo=${completo}`),

  enviarZap: (id: number | string, dados: { numero?: string; texto: string }) =>
    requisitar(`/analises/${id}/whatsapp/enviar`, { method: "POST", body: JSON.stringify(dados) }),

  situacaoZap: () => requisitar<PreviaZap>("/whatsapp"),

  salvarZap: (numero: string) => requisitar("/whatsapp", { method: "PUT", body: JSON.stringify({ numero }) }),

  // ---- cadência ----
  cadencias: () => requisitar<Cadencia[]>("/cadencias"),

  modelosCadencia: () => requisitar<Record<string, unknown>[]>("/cadencias/modelos"),

  cadencia: (id: number) => requisitar<Cadencia>(`/cadencias/${id}`),

  criarCadencia: (dados: Record<string, unknown>) => requisitar<Cadencia>("/cadencias", { method: "POST", body: JSON.stringify(dados) }),

  salvarCadencia: (id: number, dados: Record<string, unknown>) =>
    requisitar(`/cadencias/${id}`, { method: "PUT", body: JSON.stringify(dados) }),

  excluirCadencia: (id: number) => requisitar(`/cadencias/${id}`, { method: "DELETE" }),

  // ---- planilha-modelo (público) ----
  baixarModelo: () => baixar("/modelo/planilha-comercial.xlsx", "Modelo_Comercial_Neriah.xlsx"),

  urlModelo: "/api/modelo/planilha-comercial.xlsx",
};
