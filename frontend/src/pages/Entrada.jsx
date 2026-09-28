import { useState } from "react";

import { useAuth } from "../auth";

export default function Entrada() {
  const { entrar, cadastrar } = useAuth();
  const [modo, setModo] = useState("login");
  const [dados, setDados] = useState({ empresa: "", nome: "", email: "", senha: "" });
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  const campo = (k) => (e) => setDados((d) => ({ ...d, [k]: e.target.value }));

  async function enviar(e) {
    e.preventDefault();
    setErro("");
    setEnviando(true);
    try {
      if (modo === "login") await entrar(dados.email, dados.senha);
      else await cadastrar(dados);
    } catch (err) {
      setErro(err.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="tela-entrada">
      <div className="caixa-entrada">
        <h1>Assertividade Comercial</h1>
        <p style={{ color: "var(--ink-2)", fontSize: 14, marginTop: 8 }}>
          Cruze o relatório de tráfego da Meta com a sua planilha comercial e veja o que os dois
          juntos dizem: CAC, ROAS, assertividade por vendedor e o que travou cada venda.
        </p>

        <div className="abas" style={{ marginTop: 20 }}>
          <button
            className={`aba${modo === "login" ? " ativa" : ""}`}
            onClick={() => {
              setModo("login");
              setErro("");
            }}
          >
            Entrar
          </button>
          <button
            className={`aba${modo === "cadastro" ? " ativa" : ""}`}
            onClick={() => {
              setModo("cadastro");
              setErro("");
            }}
          >
            Criar conta da empresa
          </button>
        </div>

        <form onSubmit={enviar}>
          <div className="campos">
            {modo === "cadastro" && (
              <>
                <div>
                  <label htmlFor="empresa">Nome da empresa</label>
                  <input
                    id="empresa"
                    value={dados.empresa}
                    onChange={campo("empresa")}
                    required
                    minLength={2}
                    autoComplete="organization"
                  />
                </div>
                <div>
                  <label htmlFor="nome">Seu nome</label>
                  <input
                    id="nome"
                    value={dados.nome}
                    onChange={campo("nome")}
                    required
                    minLength={2}
                    autoComplete="name"
                  />
                </div>
              </>
            )}
            <div>
              <label htmlFor="email">E-mail</label>
              <input
                id="email"
                type="email"
                value={dados.email}
                onChange={campo("email")}
                required
                autoComplete="email"
              />
            </div>
            <div>
              <label htmlFor="senha">Senha</label>
              <input
                id="senha"
                type="password"
                value={dados.senha}
                onChange={campo("senha")}
                required
                minLength={8}
                autoComplete={modo === "login" ? "current-password" : "new-password"}
              />
              {modo === "cadastro" && (
                <p style={{ fontSize: 12, color: "var(--ink-muted)", margin: "6px 0 0" }}>
                  Mínimo 8 caracteres, misturando letras e números.
                </p>
              )}
            </div>
          </div>

          {erro && (
            <div className="aviso erro" style={{ marginBottom: 14 }} role="alert">
              {erro}
            </div>
          )}

          <button className="primario" type="submit" disabled={enviando} style={{ width: "100%" }}>
            {enviando ? "Aguarde…" : modo === "login" ? "Entrar" : "Criar conta e começar"}
          </button>
        </form>

        {modo === "cadastro" && (
          <p style={{ fontSize: 12.5, color: "var(--ink-muted)", marginTop: 14, marginBottom: 0 }}>
            Os dados da sua empresa ficam em um espaço separado no banco, sem contato com os de
            outros clientes.
          </p>
        )}
      </div>
    </div>
  );
}
