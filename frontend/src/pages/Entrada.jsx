import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import Marca from "../components/Marca";
import { useAuth } from "../auth";

export default function Entrada() {
  const { entrar, cadastrar } = useAuth();
  const [params] = useSearchParams();
  const [modo, setModo] = useState(params.get("modo") === "cadastro" ? "cadastro" : "login");
  const [dados, setDados] = useState({
    organizacao: "",
    tipo: "direta",
    empresa: "",
    nome: "",
    email: "",
    senha: "",
  });
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  const campo = (k) => (e) => setDados((d) => ({ ...d, [k]: e.target.value }));
  const trocar = (m) => () => {
    setModo(m);
    setErro("");
  };

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
    <div className="entrada">
      {/* -------- painel de marca -------- */}
      <aside className="entrada-marca escuro sobre-escuro">
        <Link to="/" style={{ textDecoration: "none" }}>
          <Marca tamanho={19} />
        </Link>

        <div>
          <p className="frase">
            Luz sobre o que o seu tráfego <span className="luz">realmente vendeu</span>
          </p>
          <p className="apoio">
            Duas planilhas entram. Sai o CAC real por campanha, a assertividade de cada vendedor e o
            que travou cada venda — com as conclusões escritas, não só os gráficos.
          </p>

          <div className="prova">
            <div className="item">
              <b>25,7%</b> de assertividade — e o aviso de que, descontando quem ainda não decidiu,
              a real é <b>17,1%</b>.
            </div>
            <div className="item">
              <b>R$ 405,67</b> de CAC — ou <b>R$ 730,20</b>, se os fechamentos marcados como
              parceiro vierem de indicação.
            </div>
            <div className="item">
              <b>7 clientes quentes</b> para fechar agora, com nome e o que cada um disse.
            </div>
          </div>
        </div>

        <div className="rodape-marca">Neriah · luz — inteligência de dados comerciais.</div>
      </aside>

      {/* -------- formulário -------- */}
      <main className="entrada-form">
        <div className="caixa">
          <h1>{modo === "login" ? "Entrar na sua conta" : "Criar a conta da empresa"}</h1>
          <p className="sub">
            {modo === "login"
              ? "Bem-vindo de volta. Suas análises estão onde você deixou."
              : "Você será o administrador. Cada cliente ganha um espaço isolado no banco."}
          </p>

          <form onSubmit={enviar} style={{ marginTop: 26 }}>
            <div className="campos">
              {modo === "cadastro" && (
                <>
                  <div>
                    <label htmlFor="tipo">Você é…</label>
                    <select id="tipo" value={dados.tipo} onChange={campo("tipo")}>
                      <option value="direta">Uma empresa analisando o próprio comercial</option>
                      <option value="agencia">Uma agência ou gestor de tráfego com vários clientes</option>
                    </select>
                  </div>
                  <div>
                    <label htmlFor="organizacao">
                      {dados.tipo === "agencia" ? "Nome da sua agência" : "Nome da empresa"}
                    </label>
                    <input
                      id="organizacao"
                      value={dados.organizacao}
                      onChange={campo("organizacao")}
                      required
                      minLength={2}
                      autoComplete="organization"
                      placeholder={dados.tipo === "agencia" ? "Agência Ponto Verde" : "Contabilidade Horizonte"}
                    />
                  </div>
                  {dados.tipo === "agencia" && (
                    <div>
                      <label htmlFor="empresa">Primeiro cliente da carteira</label>
                      <input
                        id="empresa"
                        value={dados.empresa}
                        onChange={campo("empresa")}
                        required
                        minLength={2}
                        placeholder="Contabilidade Horizonte"
                      />
                      <p style={{ fontSize: 12, color: "var(--ink-muted)", margin: "7px 0 0" }}>
                        Você adiciona os outros depois, na tela Carteira.
                      </p>
                    </div>
                  )}
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
                  placeholder="voce@suaempresa.com.br"
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
                  <p style={{ fontSize: 12, color: "var(--ink-muted)", margin: "7px 0 0" }}>
                    Mínimo 8 caracteres, misturando letras e números.
                  </p>
                )}
              </div>
            </div>

            {erro && (
              <div className="aviso erro" style={{ marginBottom: 15 }} role="alert">
                {erro}
              </div>
            )}

            <button className="primario" type="submit" disabled={enviando} style={{ width: "100%", padding: "12px" }}>
              {enviando ? "Aguarde…" : modo === "login" ? "Entrar" : "Criar conta e começar"}
            </button>
          </form>

          <p style={{ fontSize: 14, color: "var(--ink-2)", marginTop: 22, textAlign: "center" }}>
            {modo === "login" ? (
              <>
                Ainda não tem conta?{" "}
                <button
                  type="button"
                  onClick={trocar("cadastro")}
                  style={{ border: 0, background: "none", color: "var(--verde)", fontWeight: 620, padding: 0, cursor: "pointer" }}
                >
                  Criar a conta da empresa
                </button>
              </>
            ) : (
              <>
                Já tem conta?{" "}
                <button
                  type="button"
                  onClick={trocar("login")}
                  style={{ border: 0, background: "none", color: "var(--verde)", fontWeight: 620, padding: 0, cursor: "pointer" }}
                >
                  Entrar
                </button>
              </>
            )}
          </p>

          <p style={{ fontSize: 12.5, color: "var(--ink-muted)", marginTop: 26, textAlign: "center" }}>
            <Link to="/" style={{ color: "var(--ink-muted)" }}>
              ← Voltar para o site
            </Link>
          </p>
        </div>
      </main>
    </div>
  );
}
