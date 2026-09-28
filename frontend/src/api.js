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

export function guardarToken(token) {
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

export function guardarEmpresa(id) {
  try {
    if (id) localStorage.setItem(CHAVE_EMPRESA, String(id));
    else localStorage.removeItem(CHAVE_EMPRESA);
  } catch {
    /* idem */
  }
}

export class ErroApi extends Error {
  constructor(mensagem, status) {
    super(mensagem);
    this.status = status;
  }
}

async function mensagemDeErro(resposta) {
  try {
    const corpo = await resposta.json();
    const d = corpo?.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return d.map((e) => e.msg || String(e)).join(" ");
  } catch {
    /* resposta sem JSON */
  }
  if (resposta.status === 401) return "Sessão expirada. Faça login novamente.";
  return `Falha na requisição (${resposta.status}).`;
}

function cabecalhos(extra = {}, comCorpo = false) {
  const h = { ...extra };
  const token = lerToken();
  if (token) h.Authorization = `Bearer ${token}`;
  const empresa = lerEmpresa();
  if (empresa) h["X-Empresa"] = String(empresa);
  if (comCorpo) h["Content-Type"] = "application/json";
  return h;
}

async function requisitar(caminho, opcoes = {}) {
  const temCorpoJson = opcoes.body && !(opcoes.body instanceof FormData);
  let resposta;
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
  if (resposta.status === 204) return null;
  return resposta.json();
}

async function baixar(caminho, nome) {
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
  login: (email, senha) =>
    requisitar("/auth/login", { method: "POST", body: JSON.stringify({ email, senha }) }),

  cadastrar: (dados) => requisitar("/auth/cadastro", { method: "POST", body: JSON.stringify(dados) }),

  eu: () => requisitar("/auth/eu"),

  usuarios: () => requisitar("/auth/usuarios"),

  criarUsuario: (dados) => requisitar("/auth/usuarios", { method: "POST", body: JSON.stringify(dados) }),

  // ---- organização ----
  organizacao: () => requisitar("/organizacao"),

  mudarTipoOrganizacao: (tipo) =>
    requisitar("/organizacao/tipo", { method: "PUT", body: JSON.stringify({ tipo }) }),

  // ---- carteira ----
  empresas: () => requisitar("/empresas"),

  carteira: () => requisitar("/empresas/carteira"),

  criarEmpresa: (dados) => requisitar("/empresas", { method: "POST", body: JSON.stringify(dados) }),

  arquivarEmpresa: (id) => requisitar(`/empresas/${id}`, { method: "DELETE" }),

  // ---- análises ----
  analises: () => requisitar("/analises"),

  analise: (id) => requisitar(`/analises/${id}`),

  evolucao: () => requisitar("/analises/evolucao"),

  excluirAnalise: (id) => requisitar(`/analises/${id}`, { method: "DELETE" }),

  configuracao: () => requisitar("/configuracao"),

  salvarConfiguracao: (dados) =>
    requisitar("/configuracao", { method: "PUT", body: JSON.stringify(dados) }),

  enviarAnalise: ({ arquivosMeta, arquivosReunioes, mesReferencia }) => {
    const form = new FormData();
    arquivosMeta.forEach((a) => form.append("arquivos_meta", a));
    arquivosReunioes.forEach((a) => form.append("arquivos_reunioes", a));
    if (mesReferencia) form.append("mes_referencia", mesReferencia);
    return requisitar("/analises", { method: "POST", body: form });
  },

  baixarExcel: (id, nome) => baixar(`/analises/${id}/excel`, nome),

  // ---- planilha-modelo (público) ----
  baixarModelo: () => baixar("/modelo/planilha-comercial.xlsx", "Modelo_Comercial_Neriah.xlsx"),

  urlModelo: "/api/modelo/planilha-comercial.xlsx",
};
