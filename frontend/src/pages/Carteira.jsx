import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api";
import { useAuth } from "../auth";
import { formatar } from "../components/Charts";

/* Indicadores da carteira. `melhorQuando` diz para que lado a variação é boa —
   CAC subindo é ruim, assertividade subindo é boa. Sem isso a seta mente. */
const COLUNAS = [
  { chave: "assert", titulo: "Assertividade", formato: "pct", melhorQuando: "sobe" },
  { chave: "cac", titulo: "CAC", formato: "brl", melhorQuando: "desce" },
  { chave: "cpl", titulo: "Custo por lead", formato: "brl", melhorQuando: "desce" },
  { chave: "inv", titulo: "Investimento", formato: "brl", melhorQuando: null },
  { chave: "fec", titulo: "Fechados", formato: "int", melhorQuando: "sobe" },
];

function Variacao({ valor, formato, melhorQuando }) {
  if (valor == null || valor === 0 || !melhorQuando) return null;
  const subiu = valor > 0;
  const bom = melhorQuando === "sobe" ? subiu : !subiu;
  const texto = formato === "pct" ? `${(Math.abs(valor) * 100).toFixed(1)}pp` : formatar(Math.abs(valor), formato);
  return (
    <span
      style={{
        fontSize: 11,
        fontWeight: 650,
        color: bom ? "var(--sucesso-texto)" : "var(--critico-texto)",
        marginLeft: 6,
        whiteSpace: "nowrap",
      }}
      title={`${subiu ? "Subiu" : "Caiu"} ${texto} em relação ao mês anterior`}
    >
      {subiu ? "▲" : "▼"} {texto}
    </span>
  );
}

export default function Carteira() {
  const navegar = useNavigate();
  const { ehAdmin, trocarEmpresa, recarregarEmpresas } = useAuth();
  const [itens, setItens] = useState(null);
  const [erro, setErro] = useState("");
  const [novo, setNovo] = useState("");
  const [segmento, setSegmento] = useState("");
  const [criando, setCriando] = useState(false);
  const [abrirForm, setAbrirForm] = useState(false);

  async function carregar() {
    try {
      setItens(await api.carteira());
    } catch (e) {
      setErro(e.message);
    }
  }

  useEffect(() => {
    carregar();
  }, []);

  async function adicionar(e) {
    e.preventDefault();
    setErro("");
    setCriando(true);
    try {
      const empresa = await api.criarEmpresa({ nome: novo, segmento: segmento || null });
      await recarregarEmpresas();
      setNovo("");
      setSegmento("");
      setAbrirForm(false);
      await carregar();
      return empresa;
    } catch (err) {
      setErro(err.message);
    } finally {
      setCriando(false);
    }
  }

  function abrir(item) {
    trocarEmpresa(item.empresa.id);
    navegar(item.ultima_analise_id ? `/analises/${item.ultima_analise_id}` : "/nova");
  }

  async function arquivar(item) {
    if (!window.confirm(`Tirar "${item.empresa.nome}" da carteira? As análises continuam salvas.`)) return;
    try {
      await api.arquivarEmpresa(item.empresa.id);
      await recarregarEmpresas();
      await carregar();
    } catch (e) {
      setErro(e.message);
    }
  }

  if (!itens && !erro) return <div className="vazio">Carregando…</div>;

  const comAnalise = itens?.filter((i) => i.ultimo_mes) || [];
  const semAnalise = itens?.filter((i) => !i.ultimo_mes) || [];

  return (
    <>
      <div className="cabecalho-pagina">
        <div>
          <h1>Carteira</h1>
          <p>
            {itens?.length || 0} cliente(s) · {comAnalise.length} com análise. A variação compara com o
            mês anterior de cada um.
          </p>
        </div>
        {ehAdmin && (
          <button className="primario" onClick={() => setAbrirForm((v) => !v)}>
            {abrirForm ? "Cancelar" : "Adicionar cliente"}
          </button>
        )}
      </div>

      {erro && (
        <div className="aviso erro" style={{ marginBottom: 16 }} role="alert">
          {erro}
        </div>
      )}

      {abrirForm && (
        <form className="cartao" onSubmit={adicionar} style={{ marginBottom: 18, maxWidth: 620 }}>
          <h2>Novo cliente na carteira</h2>
          <p style={{ color: "var(--ink-2)", fontSize: 13.5, margin: "6px 0 14px" }}>
            Ele ganha um espaço isolado no banco. Nada é compartilhado com os outros clientes.
          </p>
          <div className="grade" style={{ gridTemplateColumns: "2fr 1fr", gap: 14 }}>
            <div>
              <label htmlFor="nome-cliente">Nome do cliente</label>
              <input
                id="nome-cliente"
                value={novo}
                onChange={(e) => setNovo(e.target.value)}
                required
                minLength={2}
                placeholder="Contabilidade Horizonte"
              />
            </div>
            <div>
              <label htmlFor="segmento">Segmento (opcional)</label>
              <input
                id="segmento"
                value={segmento}
                onChange={(e) => setSegmento(e.target.value)}
                placeholder="contabilidade"
              />
            </div>
          </div>
          <button className="primario" type="submit" disabled={criando} style={{ marginTop: 16 }}>
            {criando ? "Criando…" : "Criar cliente"}
          </button>
        </form>
      )}

      {itens?.length === 0 && (
        <div className="vazio">
          <h2>Sua carteira está vazia</h2>
          <p>Adicione o primeiro cliente para começar.</p>
        </div>
      )}

      {comAnalise.length > 0 && (
        <section className="cartao" style={{ marginBottom: 18 }}>
          <h2>Clientes com análise</h2>
          <div className="rolagem" style={{ marginTop: 12 }}>
            <table>
              <thead>
                <tr>
                  <th>Cliente</th>
                  <th>Último mês</th>
                  {COLUNAS.map((c) => (
                    <th key={c.chave} style={{ textAlign: "right" }}>
                      {c.titulo}
                    </th>
                  ))}
                  <th style={{ textAlign: "right" }}>Análises</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {comAnalise.map((i) => (
                  <tr key={i.empresa.id}>
                    <td>
                      <button
                        className="discreto"
                        onClick={() => abrir(i)}
                        style={{ padding: 0, color: "var(--verde)", fontWeight: 650 }}
                      >
                        {i.empresa.nome}
                      </button>
                      {i.empresa.segmento && (
                        <div style={{ fontSize: 11.5, color: "var(--ink-muted)" }}>{i.empresa.segmento}</div>
                      )}
                    </td>
                    <td>{i.ultimo_mes}</td>
                    {COLUNAS.map((c) => (
                      <td key={c.chave} className="num">
                        {i.kpis?.[c.chave] == null ? "—" : formatar(i.kpis[c.chave], c.formato)}
                        <Variacao
                          valor={i.variacao?.[c.chave]}
                          formato={c.formato}
                          melhorQuando={c.melhorQuando}
                        />
                      </td>
                    ))}
                    <td className="num">{i.total_analises}</td>
                    <td style={{ textAlign: "right" }}>
                      <button className="discreto" onClick={() => abrir(i)}>
                        abrir
                      </button>
                      {ehAdmin && (
                        <button className="discreto" onClick={() => arquivar(i)}>
                          arquivar
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {itens?.some((i) => i.erro) && (
            <div className="aviso" style={{ marginTop: 14 }}>
              Alguns clientes não puderam ser lidos:{" "}
              {itens
                .filter((i) => i.erro)
                .map((i) => i.empresa.nome)
                .join(", ")}
              .
            </div>
          )}
        </section>
      )}

      {semAnalise.length > 0 && (
        <section className="cartao">
          <h2>Ainda sem análise</h2>
          <p style={{ color: "var(--ink-2)", fontSize: 13.5, margin: "6px 0 14px" }}>
            Suba as planilhas destes clientes para eles entrarem na comparação.
          </p>
          <div className="grade" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))" }}>
            {semAnalise.map((i) => (
              <div
                key={i.empresa.id}
                style={{
                  border: "1px solid var(--borda)",
                  borderRadius: 10,
                  padding: 14,
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: 10,
                }}
              >
                <div>
                  <div style={{ fontWeight: 620 }}>{i.empresa.nome}</div>
                  {i.empresa.segmento && (
                    <div style={{ fontSize: 11.5, color: "var(--ink-muted)" }}>{i.empresa.segmento}</div>
                  )}
                </div>
                <button className="discreto" onClick={() => abrir(i)}>
                  analisar →
                </button>
              </div>
            ))}
          </div>
        </section>
      )}
    </>
  );
}
