import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { api, guardarToken, lerToken } from "./api";

const Contexto = createContext(null);

export function ProvedorAuth({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [carregando, setCarregando] = useState(Boolean(lerToken()));

  useEffect(() => {
    if (!lerToken()) return;
    let ativo = true;
    api
      .eu()
      .then((u) => ativo && setUsuario(u))
      .catch(() => guardarToken(null))
      .finally(() => ativo && setCarregando(false));
    return () => {
      ativo = false;
    };
  }, []);

  const entrar = useCallback(async (email, senha) => {
    const dados = await api.login(email, senha);
    guardarToken(dados.access_token);
    setUsuario(dados.usuario);
  }, []);

  const cadastrar = useCallback(async (payload) => {
    const dados = await api.cadastrar(payload);
    guardarToken(dados.access_token);
    setUsuario(dados.usuario);
  }, []);

  const sair = useCallback(() => {
    guardarToken(null);
    setUsuario(null);
  }, []);

  const valor = useMemo(
    () => ({ usuario, carregando, entrar, cadastrar, sair, ehAdmin: usuario?.papel === "admin" }),
    [usuario, carregando, entrar, cadastrar, sair],
  );

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useAuth() {
  const ctx = useContext(Contexto);
  if (!ctx) throw new Error("useAuth precisa estar dentro de ProvedorAuth");
  return ctx;
}
