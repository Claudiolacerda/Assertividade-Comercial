import { useEffect, useState } from "react";

import { api } from "../api";
import { mensagemDoErro } from "../erros";
import type { Conexao, Provedores, TesteConexao } from "../tipos";

/* O formulário do conector genérico é o que faz um CRM sem documentação
   pública funcionar. Ele é longo de propósito: cada campo aqui é uma pergunta
   que o suporte do CRM responde em um minuto, e preenchê-las é mais rápido do
   que esperar alguém escrever um conector dedicado. */
const EXEMPLO = {
  url: "https://api.seucrm.com.br/v1/negocios",
  auth: { tipo: "bearer", nome: "", prefixo: "" },
  itens: "data",
  paginacao: { tipo: "deslocamento", param: "offset", param_tamanho: "limit", tamanho: 100 },
  periodo: { param_de: "data_inicio", param_ate: "data_fim", formato: "%Y-%m-%d" },
  campos: {
    Cliente: "nome",
    Status: "situacao",
    "Data do lead": "criado_em",
    "Data de fechamento": "fechado_em",
    Valor: "valor",
    Responsável: "vendedor.nome",
  },
};

function Estado({ conexao }: { conexao: Conexao }) {
  if (!conexao.ativa) return <span className="selo incerto">desligada</span>;
  if (conexao.ultimo_erro) return <span className="selo fora">com erro</span>;
  if (conexao.ultima_importacao) return <span className="selo ok">funcionando</span>;
  return <span className="selo incerto">nunca usada</span>;
}

export default function Conexoes() {
  const [lista, setLista] = useState<Conexao[]>([]);
  const [catalogo, setCatalogo] = useState<Provedores | null>(null);
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(true);

  const [abrindo, setAbrindo] = useState(false);
  const [nome, setNome] = useState("");
  const [provedor, setProvedor] = useState("pipedrive");
  const [token, setToken] = useState("");
  const [dominio, setDominio] = useState("");
  const [configTexto, setConfigTexto] = useState(JSON.stringify(EXEMPLO, null, 2));
  const [salvando, setSalvando] = useState(false);

  const [testando, setTestando] = useState<number | null>(null);
  const [teste, setTeste] = useState<Record<number, TesteConexao>>({});

  async function recarregar() {
    try {
      const [conexoes, provedores] = await Promise.all([api.conexoes(), api.provedoresCrm()]);
      setLista(conexoes);
      setCatalogo(provedores);
    } catch (e) {
      setErro(mensagemDoErro(e));
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    recarregar();
  }, []);

  async function salvar(e) {
    e.preventDefault();
    setErro("");
    let config: Record<string, any>;
    if (provedor === "pipedrive") {
      config = { dominio };
    } else {
      try {
        config = JSON.parse(configTexto);
      } catch {
        setErro("A configuração não é um JSON válido. Confira as vírgulas e as aspas.");
        return;
      }
    }
    setSalvando(true);
    try {
      await api.criarConexao({ nome, provedor, token, config });
      setAbrindo(false);
      setNome("");
      setToken("");
      setDominio("");
      await recarregar();
    } catch (err) {
      setErro(mensagemDoErro(err));
    } finally {
      setSalvando(false);
    }
  }

  async function testar(conexao: Conexao) {
    setErro("");
    setTestando(conexao.id);
    try {
      setTeste({ ...teste, [conexao.id]: await api.testarConexao(conexao.id) });
    } catch (e) {
      setErro(mensagemDoErro(e));
    } finally {
      setTestando(null);
      await recarregar();
    }
  }

  async function remover(conexao: Conexao) {
    if (!confirm(`Apagar a conexão "${conexao.nome}"? As análises já feitas continuam.`)) return;
    try {
      await api.excluirConexao(conexao.id);
      await recarregar();
    } catch (e) {
      setErro(mensagemDoErro(e));
    }
  }

  const ajuda = catalogo?.provedores.find((p) => p.nome === provedor)?.ajuda;

  return (
    <>
      <div className="cabecalho-pagina">
        <div>
          <h1>Conexões com CRM</h1>
          <p>
            Em vez de exportar planilha todo mês, o Neriah puxa os negócios direto do seu CRM. O
            que vier é gravado como planilha também — para você poder abrir e conferir de onde
            saiu cada número.
          </p>
        </div>
        {!abrindo && (
          <button className="primario" onClick={() => setAbrindo(true)}>
            Ligar um CRM
          </button>
        )}
      </div>

      {erro && (
        <div className="aviso erro" role="alert" style={{ marginBottom: 18 }}>
          {erro}
        </div>
      )}

      {abrindo && (
        <form onSubmit={salvar} className="cartao" style={{ maxWidth: 760, marginBottom: 20 }}>
          <div className="grade" style={{ gap: 16 }}>
            <div>
              <label htmlFor="conexao-nome">Nome desta conexão</label>
              <input
                id="conexao-nome"
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                placeholder="Ex.: Pipedrive da operação"
                required
              />
            </div>

            <div>
              <label htmlFor="conexao-provedor">Qual CRM</label>
              <select
                id="conexao-provedor"
                value={provedor}
                onChange={(e) => setProvedor(e.target.value)}
              >
                {(catalogo?.provedores || []).map((p) => (
                  <option key={p.nome} value={p.nome}>
                    {p.rotulo}
                  </option>
                ))}
              </select>
              {ajuda && (
                <p style={{ fontSize: 12, color: "var(--ink-muted)", margin: "6px 0 0" }}>{ajuda}</p>
              )}
            </div>

            {provedor === "pipedrive" && (
              <div>
                <label htmlFor="conexao-dominio">Domínio da sua conta</label>
                <input
                  id="conexao-dominio"
                  value={dominio}
                  onChange={(e) => setDominio(e.target.value)}
                  placeholder="suaempresa.pipedrive.com"
                  required
                />
              </div>
            )}

            <div>
              <label htmlFor="conexao-token">Token de acesso</label>
              <input
                id="conexao-token"
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                autoComplete="off"
                required
              />
              <p style={{ fontSize: 12, color: "var(--ink-muted)", margin: "6px 0 0" }}>
                Fica cifrado no banco e nunca mais é exibido — nem para você.
              </p>
            </div>

            {provedor === "generico" && (
              <div>
                <label htmlFor="conexao-config">Como é a API (JSON)</label>
                <textarea
                  id="conexao-config"
                  value={configTexto}
                  onChange={(e) => setConfigTexto(e.target.value)}
                  rows={18}
                  spellCheck={false}
                  style={{ fontFamily: "ui-monospace, monospace", fontSize: 12.5 }}
                />
                <p style={{ fontSize: 12, color: "var(--ink-muted)", margin: "6px 0 0" }}>
                  Em <code>campos</code>, a esquerda é a coluna do Neriah e a direita é o campo no
                  JSON do seu CRM. As colunas aceitas são:{" "}
                  {(catalogo?.colunas || []).join(", ")}.
                </p>
              </div>
            )}
          </div>

          <div style={{ display: "flex", gap: 10, marginTop: 20 }}>
            <button className="primario" type="submit" disabled={salvando}>
              {salvando ? "Salvando…" : "Salvar conexão"}
            </button>
            <button type="button" className="discreto" onClick={() => setAbrindo(false)}>
              Cancelar
            </button>
          </div>
        </form>
      )}

      {carregando ? (
        <p>Carregando…</p>
      ) : lista.length === 0 ? (
        <div className="cartao">
          <p style={{ margin: 0 }}>
            Nenhum CRM ligado ainda. Enquanto não houver, a análise continua pela planilha, como
            sempre.
          </p>
        </div>
      ) : (
        <div className="grade" style={{ gap: 14 }}>
          {lista.map((c) => (
            <div className="cartao" key={c.id}>
              {/* alignItems no topo: sem ele o flex esticava a coluna dos botões
                  até a altura do cartão, e "Testar agora" virava um bloco alto. */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
                <div>
                  {/* O selo fora do h2: ele tem margin-top própria no CSS e,
                      dentro do título, descia em relação ao texto. */}
                  <h2 style={{ margin: 0, fontSize: 16 }}>{c.nome}</h2>
                  <Estado conexao={c} />
                  <p style={{ margin: "4px 0 0", fontSize: 13, color: "var(--ink-2)" }}>
                    {catalogo?.provedores.find((p) => p.nome === c.provedor)?.rotulo || c.provedor}
                    {c.ultima_importacao &&
                      ` · última importação em ${new Date(c.ultima_importacao).toLocaleString("pt-BR")}`}
                  </p>
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <button onClick={() => testar(c)} disabled={testando === c.id}>
                    {testando === c.id ? "Testando…" : "Testar agora"}
                  </button>
                  <button
                    className="discreto"
                    onClick={() => api.editarConexao(c.id, { ativa: !c.ativa }).then(recarregar)}
                  >
                    {c.ativa ? "Desligar" : "Religar"}
                  </button>
                  <button className="discreto" onClick={() => remover(c)}>
                    Apagar
                  </button>
                </div>
              </div>

              {c.ultimo_erro && (
                <div className="aviso erro" style={{ marginTop: 12 }}>
                  {c.ultimo_erro}
                </div>
              )}

              {teste[c.id] && (
                <div style={{ marginTop: 12 }}>
                  <p style={{ margin: "0 0 6px", fontSize: 13 }}>
                    <strong>{teste[c.id].quantidade}</strong> negócio(s) no mês corrente.
                  </p>
                  {/* O que NÃO veio preenchido é a informação mais útil aqui: é
                      a coluna que vai faltar na análise, e é mais barato
                      descobrir agora do que pelo indicador sumido. */}
                  {teste[c.id].colunas_vazias.length > 0 && (
                    <p style={{ margin: 0, fontSize: 13, color: "var(--ink-2)" }}>
                      Sem dado nestas colunas: {teste[c.id].colunas_vazias.join(", ")}.
                    </p>
                  )}
                  {teste[c.id].avisos.map((a, i) => (
                    <div className="aviso" key={i} style={{ marginTop: 8 }}>
                      {a}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
