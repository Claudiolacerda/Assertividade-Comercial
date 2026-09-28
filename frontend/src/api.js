/* Cliente HTTP: guarda o token e traduz erro da API em mensagem legível. */

const CHAVE_TOKEN = "assertividade_token";

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
    // Erro de validação do FastAPI vem como lista
    if (Array.isArray(d)) return d.map((e) => e.msg || String(e)).join(" ");
  } catch {
    /* resposta sem JSON */
  }
  if (resposta.status === 401) return "Sessão expirada. Faça login novamente.";
  return `Falha na requisição (${resposta.status}).`;
}

async function requisitar(caminho, opcoes = {}) {
  const token = lerToken();
  const cabecalhos = { ...(opcoes.headers || {}) };
  if (token) cabecalhos.Authorization = `Bearer ${token}`;
  if (opcoes.body && !(opcoes.body instanceof FormData)) {
    cabecalhos["Content-Type"] = "application/json";
  }

  let resposta;
  try {
    resposta = await fetch(`/api${caminho}`, { ...opcoes, headers: cabecalhos });
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

export const api = {
  login: (email, senha) =>
    requisitar("/auth/login", { method: "POST", body: JSON.stringify({ email, senha }) }),

  cadastrar: (dados) => requisitar("/auth/cadastro", { method: "POST", body: JSON.stringify(dados) }),

  eu: () => requisitar("/auth/eu"),

  usuarios: () => requisitar("/auth/usuarios"),

  criarUsuario: (dados) =>
    requisitar("/auth/usuarios", { method: "POST", body: JSON.stringify(dados) }),

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

  async baixarExcel(id, nome) {
    const token = lerToken();
    const resposta = await fetch(`/api/analises/${id}/excel`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
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
  },
};
