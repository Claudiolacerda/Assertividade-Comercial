import { useEffect, useState } from "react";

import { api } from "../api";
import { useAuth } from "../auth";
import { mensagemDoErro } from "../erros";

const PAPEIS = {
  admin: "Administrador — gerencia clientes, metas e usuários",
  membro: "Membro — analisa toda a carteira, não gerencia",
  cliente: "Cliente — vê apenas os clientes liberados, sem alterar nada",
};

export default function Equipe() {
  const { ehAdmin, empresas } = useAuth();
  const [usuarios, setUsuarios] = useState<any>(null);
  const [novo, setNovo] = useState<{
    nome: string;
    email: string;
    senha: string;
    papel: string;
    empresas: number[];
  }>({ nome: "", email: "", senha: "", papel: "membro", empresas: [] });
  const [erro, setErro] = useState("");
  const [salvo, setSalvo] = useState("");

  async function carregar() {
    try {
      setUsuarios(await api.usuarios());
    } catch (e) {
      setErro(mensagemDoErro(e));
    }
  }

  useEffect(() => {
    if (ehAdmin) carregar();
  }, [ehAdmin]);

  if (!ehAdmin) {
    return <div className="aviso">Só o administrador da organização pode gerenciar usuários.</div>;
  }

  async function criar(e) {
    e.preventDefault();
    setErro("");
    setSalvo("");
    try {
      await api.criarUsuario(novo);
      setSalvo(`${novo.nome} já pode entrar com o e-mail ${novo.email}.`);
      setNovo({ nome: "", email: "", senha: "", papel: "membro", empresas: [] });
      await carregar();
    } catch (err) {
      setErro(mensagemDoErro(err));
    }
  }

  const campo = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setNovo((n) => ({ ...n, [k]: e.target.value }));

  function alternarEmpresa(id: number) {
    setNovo((n) => ({
      ...n,
      empresas: n.empresas.includes(id) ? n.empresas.filter((x) => x !== id) : [...n.empresas, id],
    }));
  }

  return (
    <>
      <div className="cabecalho-pagina">
        <div>
          <h1>Equipe</h1>
          <p>
            Quem acessa a sua organização. Use o papel <strong>Cliente</strong> para liberar o painel
            ao cliente final, restrito ao que é dele.
          </p>
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
                    <th>Enxerga</th>
                  </tr>
                </thead>
                <tbody>
                  {usuarios.map((u) => (
                    <tr key={u.id}>
                      <td>{u.nome}</td>
                      <td>{u.email}</td>
                      <td style={{ textTransform: "capitalize" }}>{u.papel}</td>
                      <td className="texto">
                        {u.papel === "cliente"
                          ? u.empresas.map((e) => e.nome).join(", ") || "—"
                          : `toda a carteira (${u.empresas.length})`}
                      </td>
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
                  {Object.entries(PAPEIS).map(([v, rotulo]) => (
                    <option key={v} value={v}>
                      {rotulo}
                    </option>
                  ))}
                </select>
              </div>

              {novo.papel === "cliente" && (
                <div>
                  <label>Clientes que ele pode ver</label>
                  <div
                    style={{
                      border: "1px solid var(--borda)",
                      borderRadius: 9,
                      padding: 10,
                      maxHeight: 180,
                      overflowY: "auto",
                      display: "grid",
                      gap: 8,
                    }}
                  >
                    {empresas.map((e) => (
                      <label
                        key={e.id}
                        style={{ display: "flex", gap: 9, alignItems: "center", fontWeight: 500, margin: 0 }}
                      >
                        <input
                          type="checkbox"
                          
                          checked={novo.empresas.includes(e.id)}
                          onChange={() => alternarEmpresa(e.id)}
                        />
                        <span style={{ color: "var(--ink)" }}>{e.nome}</span>
                      </label>
                    ))}
                  </div>
                  <p style={{ fontSize: 12, color: "var(--ink-muted)", margin: "6px 0 0" }}>
                    Escolha pelo menos um — é o que ele vai enxergar ao entrar.
                  </p>
                </div>
              )}
            </div>

            {salvo && (
              <div className="aviso ok" style={{ marginBottom: 12 }}>
                {salvo}
              </div>
            )}
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
