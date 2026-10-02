import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import type { ReactNode } from "react";

import { api, guardarEmpresa, guardarToken, lerEmpresa, lerToken } from "./api";
import type { Empresa, Usuario } from "./tipos";

/** O que o resto do app pode pedir ao contexto de autenticação. */
export interface Auth {
  usuario: Usuario | null;
  carregando: boolean;
  entrar: (email: string, senha: string) => Promise<void>;
  cadastrar: (payload: Record<string, unknown>) => Promise<void>;
  sair: () => void;
  empresas: Empresa[];
  empresaId: number | null;
  empresa: Empresa | null;
  trocarEmpresa: (id: number) => void;
  recarregarEmpresas: () => Promise<unknown>;
  ehAdmin: boolean;
  ehCliente: boolean;
  ehAgencia: boolean;
  temCarteira: boolean;
}

const Contexto = createContext<Auth | null>(null);

/** Escolhe qual cliente da carteira abrir: o último usado, se ainda existir. */
function empresaInicial(empresas: Empresa[] | undefined): number | null {
  if (!empresas?.length) return null;
  const salva = lerEmpresa();
  const achou = empresas.find((e) => e.id === salva);
  return (achou || empresas[0]).id;
}

export function ProvedorAuth({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [empresaId, setEmpresaId] = useState(lerEmpresa());
  const [carregando, setCarregando] = useState(Boolean(lerToken()));

  const aplicar = useCallback((u: Usuario | null) => {
    setUsuario(u);
    const id = empresaInicial(u?.empresas);
    guardarEmpresa(id);
    setEmpresaId(id);
  }, []);

  useEffect(() => {
    if (!lerToken()) return;
    let ativo = true;
    api
      .eu()
      .then((u) => ativo && aplicar(u))
      .catch(() => {
        guardarToken(null);
        guardarEmpresa(null);
      })
      .finally(() => ativo && setCarregando(false));
    return () => {
      ativo = false;
    };
  }, [aplicar]);

  const entrar = useCallback(
    async (email, senha) => {
      const dados = await api.login(email, senha);
      guardarToken(dados.access_token);
      aplicar(dados.usuario);
    },
    [aplicar],
  );

  const cadastrar = useCallback(
    async (payload) => {
      const dados = await api.cadastrar(payload);
      guardarToken(dados.access_token);
      aplicar(dados.usuario);
    },
    [aplicar],
  );

  const sair = useCallback(() => {
    guardarToken(null);
    guardarEmpresa(null);
    setUsuario(null);
    setEmpresaId(null);
  }, []);

  /** Troca o cliente em foco. Todas as telas recarregam a partir disso. */
  const trocarEmpresa = useCallback((id) => {
    guardarEmpresa(id);
    setEmpresaId(id);
  }, []);

  /** Depois de criar um cliente novo, a lista da sessão precisa acompanhar. */
  const recarregarEmpresas = useCallback(
    async (focarId = null) => {
      const empresas = await api.empresas();
      setUsuario((u) => (u ? { ...u, empresas } : u));
      const id = focarId ?? empresaInicial(empresas);
      guardarEmpresa(id);
      setEmpresaId(id);
      return empresas;
    },
    [],
  );

  const valor = useMemo<Auth>(() => {
    const empresas: Empresa[] = usuario?.empresas || [];
    return {
      usuario,
      carregando,
      entrar,
      cadastrar,
      sair,
      empresas,
      empresaId,
      empresa: empresas.find((e) => e.id === empresaId) || null,
      trocarEmpresa,
      recarregarEmpresas,
      ehAdmin: usuario?.papel === "admin",
      ehCliente: usuario?.papel === "cliente",
      // A carteira só existe para quem se declarou agência no cadastro. Quem
      // analisa o próprio comercial não vê nada disso — e liga depois, na
      // Configuração, se passar a atender outros clientes.
      ehAgencia: usuario?.organizacao?.tipo === "agencia",
      temCarteira: usuario?.organizacao?.tipo === "agencia" && usuario?.papel !== "cliente",
    };
  }, [usuario, carregando, entrar, cadastrar, sair, empresaId, trocarEmpresa, recarregarEmpresas]);

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useAuth() {
  const ctx = useContext(Contexto);
  if (!ctx) throw new Error("useAuth precisa estar dentro de ProvedorAuth");
  return ctx;
}
