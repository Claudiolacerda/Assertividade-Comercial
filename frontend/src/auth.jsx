import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { api, guardarEmpresa, guardarToken, lerEmpresa, lerToken } from "./api";

const Contexto = createContext(null);

/** Escolhe qual cliente da carteira abrir: o último usado, se ainda existir. */
function empresaInicial(empresas) {
  if (!empresas?.length) return null;
  const salva = lerEmpresa();
  const achou = empresas.find((e) => e.id === salva);
  return (achou || empresas[0]).id;
}

export function ProvedorAuth({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [empresaId, setEmpresaId] = useState(lerEmpresa());
  const [carregando, setCarregando] = useState(Boolean(lerToken()));

  const aplicar = useCallback((u) => {
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

  const valor = useMemo(() => {
    const empresas = usuario?.empresas || [];
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
      // A carteira só faz sentido para quem administra mais de um cliente
      temCarteira: empresas.length > 1 || usuario?.organizacao?.tipo === "agencia",
    };
  }, [usuario, carregando, entrar, cadastrar, sair, empresaId, trocarEmpresa, recarregarEmpresas]);

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useAuth() {
  const ctx = useContext(Contexto);
  if (!ctx) throw new Error("useAuth precisa estar dentro de ProvedorAuth");
  return ctx;
}
