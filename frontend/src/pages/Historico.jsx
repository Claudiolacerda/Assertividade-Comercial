import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api } from "../api";
import { GraficoEvolucao, S1, S2, S3, dataHora, formatar, mesPorExtenso } from "../components/Charts";
import { useAuth } from "../auth";

const COLUNAS = [
  { chave: "assert", titulo: "Assertividade", formato: "pct" },
  { chave: "cac", titulo: "CAC", formato: "brl" },
  { chave: "cpl", titulo: "CPL", formato: "brl" },
  { chave: "inv", titulo: "Investimento", formato: "brl" },
  { chave: "fec", titulo: "Fechados", formato: "int" },
];

export default function Historico() {
  const { ehAdmin } = useAuth();
  const navegar = useNavigate();
  const [analises, setAnalises] = useState(null);
  const [evolucao, setEvolucao] = useState(null);
  const [erro, setErro] = useState("");

  async function carregar() {
    try {
      const [lista, evo] = await Promise.all([api.analises(), api.evolucao()]);
      setAnalises(lista);
      setEvolucao(evo);
    } catch (e) {
      setErro(e.message);
    }
  }

  useEffect(() => {
    carregar();
  }, []);

  async function excluir(id) {
    if (!window.confirm("Excluir esta análise e os arquivos enviados? Não dá para desfazer.")) return;
    try {
      await api.excluirAnalise(id);
      await carregar();
    } catch (e) {
      setErro(e.message);
    }
  }

  if (erro) return <div className="aviso erro">{erro}</div>;
  if (!analises) return <div className="vazio">Carregando…</div>;

  if (!analises.length) {
    return (
      <div className="vazio">
        <h2>Nenhuma análise ainda</h2>
        <p>Envie o relatório da Meta e a planilha comercial para ver o primeiro painel.</p>
        <button className="primario" onClick={() => navegar("/nova")}>
          Fazer a primeira análise
        </button>
      </div>
    );
  }

  const meses = evolucao?.meses || [];

  return (
    <>
      <div className="cabecalho-pagina">
        <div>
          <h1>Histórico</h1>
          <p>
            {analises.length} análise(s) · {meses.length} mês(es). A evolução usa a última versão de
            cada mês.
          </p>
        </div>
        <button className="primario" onClick={() => navegar("/nova")}>
          Nova análise
        </button>
      </div>

      {meses.length >= 2 && (
        <div className="grade dois" style={{ marginBottom: 18 }}>
          <GraficoEvolucao
            meses={meses}
            chave="assert"
            titulo="Assertividade"
            formato="pct"
            cor={S1}
          />
          <GraficoEvolucao meses={meses} chave="cac" titulo="CAC" formato="brl" cor={S2} />
          <GraficoEvolucao meses={meses} chave="cpl" titulo="Custo por lead" formato="brl" cor={S3} />
          <GraficoEvolucao
            meses={meses}
            chave="inv"
            titulo="Investimento em tráfego"
            formato="brl"
            cor={S1}
          />
        </div>
      )}

      <section className="cartao">
        <h2>Todas as análises</h2>
        <div className="rolagem">
          <table>
            <thead>
              <tr>
                <th>Mês</th>
                <th>Versão</th>
                {COLUNAS.map((c) => (
                  <th key={c.chave} style={{ textAlign: "right" }}>
                    {c.titulo}
                  </th>
                ))}
                <th>Criada em</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {analises.map((a) => (
                <tr key={a.id}>
                  <td>
                    <Link to={`/analises/${a.id}`}>{mesPorExtenso(a.mes_referencia)}</Link>
                  </td>
                  <td>
                    <span className="pastilha-versao">v{a.versao}</span>
                  </td>
                  {COLUNAS.map((c) => (
                    <td key={c.chave} className="num">
                      {a.kpis_resumo?.[c.chave] == null
                        ? "—"
                        : formatar(a.kpis_resumo[c.chave], c.formato)}
                    </td>
                  ))}
                  <td>{dataHora(a.criada_em)}</td>
                  <td style={{ textAlign: "right" }}>
                    <button
                      className="discreto"
                      onClick={() =>
                        api
                          .baixarExcel(a.id, `Assertividade_${a.mes_referencia}_v${a.versao}.xlsx`)
                          .catch((e) => setErro(e.message))
                      }
                    >
                      .xlsx
                    </button>
                    {ehAdmin && (
                      <button className="discreto" onClick={() => excluir(a.id)}>
                        excluir
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
