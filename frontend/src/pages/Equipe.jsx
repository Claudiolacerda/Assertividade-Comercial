import { useEffect, useState } from "react";

import { api } from "../api";
import { useAuth } from "../auth";

export default function Equipe() {
  const { ehAdmin } = useAuth();
  const [usuarios, setUsuarios] = useState(null);
  const [novo, setNovo] = useState({ nome: "", email: "", senha: "", papel: "membro" });
  const [erro, setErro] = useState("");
  const [salvo, setSalvo] = useState("");

  async function carregar() {
    try {
      setUsuarios(await api.usuarios());
    } catch (e) {
      setErro(e.message);
    }
  }

  useEffect(() => {
    if (ehAdmin) carregar();
  }, [ehAdmin]);

  if (!ehAdmin) {
    return (
      <div className="aviso">
        Só o administrador da empresa pode gerenciar usuários.
      </div>
    );
  }

  async function criar(e) {
    e.preventDefault();
    setErro("");
    setSalvo("");
    try {
      await api.criarUsuario(novo);
      setSalvo(`${novo.nome} já pode entrar com o e-mail ${novo.email}.`);
      setNovo({ nome: "", email: "", senha: "", papel: "membro" });
      await carregar();
    } catch (err) {
      setErro(err.message);
    }
  }

  const campo = (k) => (e) => setNovo((n) => ({ ...n, [k]: e.target.value }));

  return (
    <>
      <div className="cabecalho-pagina">
        <div>
          <h1>Equipe</h1>
          <p>Quem tem acesso ao painel da sua empresa.</p>
        </div>
      </div>

      <div className="grade dois">
        <section className="cartao">
          <h2>Usuários</h2>
          {!usuarios ? (
            <p style={{ color: "var(--ink-2)" }}>Carregando…</p>
          ) : (
            <div className="rolagem" style={{ marginTop: 10 }}>
              <table>
                <thead>
                  <tr>
                    <th>Nome</th>
                    <th>E-mail</th>
                    <th>Papel</th>
                  </tr>
                </thead>
                <tbody>
                  {usuarios.map((u) => (
                    <tr key={u.id}>
                      <td>{u.nome}</td>
                      <td>{u.email}</td>
                      <td>{u.papel === "admin" ? "Administrador" : "Membro"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="cartao">
          <h2>Adicionar usuário</h2>
          <form onSubmit={criar}>
            <div className="campos">
              <div>
                <label htmlFor="n-nome">Nome</label>
                <input id="n-nome" value={novo.nome} onChange={campo("nome")} required minLength={2} />
              </div>
              <div>
                <label htmlFor="n-email">E-mail</label>
                <input id="n-email" type="email" value={novo.email} onChange={campo("email")} required />
              </div>
              <div>
                <label htmlFor="n-senha">Senha provisória</label>
                <input
                  id="n-senha"
                  type="password"
                  value={novo.senha}
                  onChange={campo("senha")}
                  required
                  minLength={8}
                  autoComplete="new-password"
                />
              </div>
              <div>
                <label htmlFor="n-papel">Papel</label>
                <select id="n-papel" value={novo.papel} onChange={campo("papel")}>
                  <option value="membro">Membro — vê os painéis</option>
                  <option value="admin">Administrador — também edita metas e exclui análises</option>
                </select>
              </div>
            </div>
            {salvo && <div className="aviso ok" style={{ marginBottom: 12 }}>{salvo}</div>}
            {erro && (
              <div className="aviso erro" style={{ marginBottom: 12 }} role="alert">
                {erro}
              </div>
            )}
            <button className="primario" type="submit">
              Adicionar
            </button>
          </form>
        </section>
      </div>
    </>
  );
}
