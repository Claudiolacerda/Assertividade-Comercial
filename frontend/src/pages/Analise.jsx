import { useEffect, useState, useLayoutEffect, useRef } from "react";
import { useParams } from "react-router-dom";

import { useAuth } from "../auth";

import { api } from "../api";
import {
  GraficoCampanhas,
  GraficoFunil,
  GraficoResponsavel,
  GraficoSemanas,
  GraficoStatus,
} from "../components/Charts";
import NotaPlanilha from "../components/NotaPlanilha";
import RelatorioZap from "../components/RelatorioZap";
import { Destaque, Diagnostico, TabelaDados, Tile } from "../components/Painel";

const ABAS = [
  { id: "resumo", titulo: "Resumo" },
  { id: "trafego", titulo: "Tráfego pago" },
  { id: "comercial", titulo: "Comercial" },
  { id: "pipeline", titulo: "Pipeline e objeções" },
  { id: "relatorio", titulo: "Relatório WhatsApp" },
  { id: "qualidade", titulo: "Qualidade dos dados" },
];

export default function Analise() {
  const { id } = useParams();
  const { empresa } = useAuth();
  const [analise, setAnalise] = useState(null);
  const [erro, setErro] = useState("");
  const [aba, setAba] = useState("resumo");
  const barraAbas = useRef(null);

  /* O indicador é posicionado por medição, não por cálculo: os rótulos têm
     larguras diferentes e a barra rola no celular. useLayoutEffect para a
     posição valer já na primeira pintura, sem salto. */
  useLayoutEffect(() => {
    const barra = barraAbas.current;
    if (!barra) return;
    const ativa = barra.querySelector(".aba.ativa");
    if (!ativa) return;
    const mover = () => {
      barra.style.setProperty("--ind-x", `${ativa.offsetLeft}px`);
      barra.style.setProperty("--ind-w", `${ativa.offsetWidth}px`);
    };
    mover();
    const ro = new ResizeObserver(mover);
    ro.observe(barra);
    return () => ro.disconnect();
    // `analise` entra nas dependências porque as abas só existem depois que o
    // resultado chega: sem isso o efeito roda cedo demais, não acha a aba ativa
    // e o indicador fica invisível até a primeira troca.
  }, [aba, analise]);
  const [baixando, setBaixando] = useState(false);

  useEffect(() => {
    let ativo = true;
    setAnalise(null);
    setErro("");
    api
      .analise(id)
      .then((a) => ativo && setAnalise(a))
      .catch((e) => ativo && setErro(e.message));
    return () => {
      ativo = false;
    };
  }, [id]);

  if (erro) return <div className="aviso erro">{erro}</div>;
  if (!analise) return <div className="vazio">Carregando análise…</div>;

  const r = analise.resultado;
  if (!r) return <div className="aviso erro">Esta análise não tem resultado salvo.</div>;

  const { kpis, tabelas } = r;
  const tabela = (nome) => tabelas?.[nome] || [];

  async function baixar() {
    setBaixando(true);
    try {
      await api.baixarExcel(analise.id, `Assertividade_${analise.mes_referencia}_v${analise.versao}.xlsx`);
    } catch (e) {
      setErro(e.message);
    } finally {
      setBaixando(false);
    }
  }

  return (
    <>
      <div className="cabecalho-pagina">
        <div>
          <h1>{r.nome_mes}</h1>
          <p>
            Versão {analise.versao} · {r.tem_valor ? "com valores de contrato" : "sem coluna de valor na planilha"}
            {" · "}
            {tabela("base_reunioes").length} reuniões analisadas
          </p>
        </div>
        <button className="primario" onClick={baixar} disabled={baixando}>
          {baixando ? "Gerando…" : "Baixar planilha (.xlsx)"}
        </button>
      </div>

      {r.avisos?.length > 0 && (
        <div className="grade" style={{ marginBottom: 18 }}>
          {r.avisos.map((a, i) => (
            <div className="aviso" key={i}>
              {a}
            </div>
          ))}
        </div>
      )}

      {/* role/aria-selected são o que diz ao leitor de tela qual visão está
          aberta: o sublinhado verde sozinho não é exposto a ninguém. */}
      <div className="abas" role="tablist" aria-label="Visões da análise" ref={barraAbas}>
        {/* Um indicador só, que viaja entre as abas. Seis sublinhados que acendem
            e apagam não dizem de onde para onde você foi; este diz. */}
        <span className="indicador-aba" aria-hidden="true" />
        {ABAS.map((a) => (
          <button
            key={a.id}
            id={`aba-${a.id}`}
            role="tab"
            aria-selected={aba === a.id}
            aria-controls={`painel-${a.id}`}
            className={`aba${aba === a.id ? " ativa" : ""}`}
            onClick={() => setAba(a.id)}
          >
            {a.titulo}
          </button>
        ))}
      </div>

      {aba === "resumo" && (
        <div
          className="grade"
          role="tabpanel"
          id="painel-resumo"
          aria-labelledby="aba-resumo"
          tabIndex={-1}
        >
          <Destaque itens={r.diagnostico} />
          <div className="grade tiles">
            <Tile kpi={kpis.assert} destaque />
            <Tile kpi={kpis.cac} />
            <Tile kpi={kpis.cpl} />
            <Tile kpi={kpis.inv} />
            {kpis.roas && <Tile kpi={kpis.roas} />}
            <Tile kpi={kpis.fec} />
          </div>
          <Diagnostico itens={r.diagnostico} />
          <NotaPlanilha cobertura={r.cobertura} />
          <div className="grade dois">
            <GraficoFunil funil={tabela("funil")} />
            <GraficoStatus porStatus={tabela("por_status")} />
          </div>
        </div>
      )}

      {aba === "trafego" && (
        <div
          className="grade"
          role="tabpanel"
          id="painel-trafego"
          aria-labelledby="aba-trafego"
          tabIndex={-1}
        >
          <div className="grade tiles">
            <Tile kpi={kpis.inv} />
            <Tile kpi={kpis.imp} />
            <Tile kpi={kpis.clq} />
            <Tile kpi={kpis.ctr} />
            <Tile kpi={kpis.cpc} />
            <Tile kpi={kpis.cpl} />
          </div>
          <GraficoCampanhas metaCampanhas={tabela("meta_campanhas")} />
          <TabelaDados
            titulo="Desempenho por campanha"
            subtitulo={
              r.tipos_resultado?.length > 1
                ? `Atenção: há tipos de resultado diferentes somados como lead (${r.tipos_resultado.join(", ")}).`
                : "Investimento, leads e custo por lead de cada campanha."
            }
            linhas={tabela("meta_campanhas")}
          />
          {tabela("campanha_x_vendas").length > 0 ? (
            <TabelaDados
              titulo="Qual campanha realmente vende"
              subtitulo="Meta cruzada com as reuniões: CAC e ROAS por campanha."
              linhas={tabela("campanha_x_vendas")}
            />
          ) : (
            <div className="aviso">
              Para saber qual campanha vende, registre na planilha comercial de qual campanha veio
              cada lead (coluna “Campanha”). Aí esta tabela mostra CAC e ROAS por anúncio.
            </div>
          )}
          <TabelaDados titulo="Por conjunto de anúncios" linhas={tabela("meta_conjuntos")} />
          <TabelaDados titulo="Por anúncio (criativo)" linhas={tabela("meta_anuncios")} />
        </div>
      )}

      {aba === "comercial" && (
        <div
          className="grade"
          role="tabpanel"
          id="painel-comercial"
          aria-labelledby="aba-comercial"
          tabIndex={-1}
        >
          <div className="grade tiles">
            <Tile kpi={kpis.ag} />
            <Tile kpi={kpis.real} />
            <Tile kpi={kpis.fec} />
            <Tile kpi={kpis.neg} />
            <Tile kpi={kpis.sd} />
            <Tile kpi={kpis.assert} destaque />
          </div>
          <div className="grade dois">
            <GraficoSemanas porSemana={tabela("por_semana")} />
            <GraficoResponsavel
              porResponsavel={tabela("por_responsavel")}
              meta={kpis.assert?.meta_valor ?? 0.25}
            />
          </div>
          <TabelaDados titulo="Por responsável" linhas={tabela("por_responsavel")} />
          <TabelaDados titulo="Por semana" linhas={tabela("por_semana")} />
          <TabelaDados titulo="Por dia da semana" linhas={tabela("por_dia")} />
          <TabelaDados
            titulo="Por marcação no nome do cliente"
            subtitulo="Sufixo depois do hífen (ex.: “Wagner - Parceiro” → Parceiro)."
            linhas={tabela("por_marcacao")}
          />
          <TabelaDados titulo="Por origem" linhas={tabela("por_origem")} />
          <TabelaDados titulo="Por produto" linhas={tabela("por_produto")} />
          <TabelaDados
            titulo="Como cada texto da planilha foi classificado"
            subtitulo="Transparência da classificação: nada é caixa-preta."
            linhas={tabela("mapa_status")}
          />
          <TabelaDados titulo="Ciclo de venda" linhas={tabela("ciclo")} />
          <TabelaDados titulo="Tempo entre agendamento e reunião" linhas={tabela("tempo_agendamento")} />
        </div>
      )}

      {aba === "pipeline" && (
        <div
          className="grade"
          role="tabpanel"
          id="painel-pipeline"
          aria-labelledby="aba-pipeline"
          tabIndex={-1}
        >
          <div className="grade tiles">
            {kpis.vneg && <Tile kpi={kpis.vneg} />}
            {kpis.fcst && <Tile kpi={kpis.fcst} />}
            <Tile kpi={kpis.neg} />
            <Tile kpi={kpis.per} />
          </div>
          <TabelaDados
            titulo="Oportunidades em aberto"
            subtitulo="Ordenadas por temperatura: 🔥 quente, 🌤️ morna, ❄️ com sinal de perda."
            linhas={tabela("pipeline")}
          />
          <TabelaDados
            titulo="Sinais nas observações"
            subtitulo="O que os comentários da sua equipe revelam sobre objeções."
            linhas={tabela("sinais_resumo")}
          />
          <TabelaDados titulo="Sinal por status" linhas={tabela("sinais_por_status")} />
          <TabelaDados titulo="Motivos de perda" linhas={tabela("motivos_perda")} />
          <TabelaDados titulo="Lista de perdas" linhas={tabela("lista_perdas")} />
          <TabelaDados titulo="No-show, remarcadas e canceladas" linhas={tabela("noshow")} />
          <TabelaDados
            titulo="Todas as observações"
            subtitulo="Cliente a cliente, com os sinais identificados."
            linhas={tabela("observacoes")}
          />
        </div>
      )}

      {aba === "relatorio" && (
        <div
          className="grade"
          role="tabpanel"
          id="painel-relatorio"
          aria-labelledby="aba-relatorio"
          tabIndex={-1}
        >
          <RelatorioZap analiseId={analise.id} nomeCliente={empresa?.nome} />
        </div>
      )}

      {aba === "qualidade" && (
        <div
          className="grade"
          role="tabpanel"
          id="painel-qualidade"
          aria-labelledby="aba-qualidade"
          tabIndex={-1}
        >
          <NotaPlanilha cobertura={r.cobertura} />
          <TabelaDados
            titulo="Resumo dos problemas"
            subtitulo="Corrija na origem e os números do próximo mês ficam mais confiáveis."
            linhas={r.resumo_qualidade}
          />
          <TabelaDados titulo="Detalhe linha a linha" linhas={r.qualidade} />
          <TabelaDados
            titulo="Como as colunas dos seus arquivos foram reconhecidas"
            subtitulo="Se algo aparece como “NÃO ENCONTRADA”, renomeie a coluna na planilha."
            linhas={r.mapeamento}
          />
          <TabelaDados titulo="Base de reuniões tratada" linhas={tabela("base_reunioes")} limite={100} />
          <TabelaDados titulo="Base da Meta tratada" linhas={tabela("base_meta")} limite={100} />
        </div>
      )}
    </>
  );
}
