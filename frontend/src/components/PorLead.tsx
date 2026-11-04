/* Quantos leads custa cada resultado, e o plano que sai disso.
 *
 * A pergunta do dono do negócio não é "qual a taxa de agendamento": é "de
 * quantos leads eu preciso para marcar uma reunião, e para fechar um cliente".
 * É a mesma medida de cabeça para baixo, e é a que serve para planejar: com ela
 * dá para dizer quantos leads um mês de três vendas exige antes de ele começar.
 *
 * As duas calculadoras daqui andam nos dois sentidos, porque as duas perguntas
 * aparecem: "tenho tantos leads, o que espero disso" e "quero tantas vendas,
 * de quanto preciso". Nenhuma delas guarda nada: é aritmética sobre os
 * indicadores desta análise, feita na hora. */

import { useState } from "react";

import { formatar } from "./Charts";
import { Tile } from "./Painel";

const inteiro = (v: number) => Math.round(v).toLocaleString("pt-BR");
const umaCasa = (v: number) =>
  v.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

/** Lê o valor de um KPI, ou 0 quando ele não existe nesta análise. */
const valor = (kpis, chave: string) => Number(kpis?.[chave]?.valor) || 0;

export default function PorLead({ kpis, base }) {
  /* Nos dois casos a razão está certa, mas só na base paga ela multiplica
     pelo CPL: na outra, os leads contam indicação e orgânico, que não têm
     custo de anúncio. Por isso o orçamento sai do CAC, e não do CPL. */
  const todasAsOrigens = base === "informada";
  const sufixo = todasAsOrigens ? " (todas as origens)" : " (do tráfego pago)";
  const lpag = valor(kpis, "lpag");
  const lpfec = valor(kpis, "lpfec");
  const agfec = valor(kpis, "agfec");
  const cac = valor(kpis, "cac");

  const [leads, setLeads] = useState("");
  const [vendas, setVendas] = useState("");

  const n = (texto: string) => {
    const v = Number(String(texto).replace(/[^\d]/g, ""));
    return Number.isFinite(v) && v > 0 ? v : 0;
  };
  const leadsSimulados = n(leads);
  const vendasDesejadas = n(vendas);

  /* Sem nenhuma das duas razões não há o que calcular nem o que planejar: o mês
     não marcou reunião nem fechou cliente, e qualquer número aqui seria
     inventado. */
  if (!lpag && !lpfec) {
    return (
      <div className="aviso">
        Este mês não tem reunião marcada nem cliente fechado vindo dos leads, então não há razão
        de leads para calcular. Ela aparece aqui no primeiro mês com resultado.
      </div>
    );
  }

  return (
    <>
      <h2 className="titulo-secao">Quantos leads custa cada resultado</h2>
      <p className="sub-secao">
        A média deste mês. É a taxa de conversão de cabeça para baixo, no formato em que se
        planeja mídia: quantos leads entram para que um resultado saia. A conta é{" "}
        {todasAsOrigens
          ? "sobre o total de leads que você informou, contra todas as reuniões e vendas do mês."
          : "sobre os leads que a Meta reportou, contra as reuniões e vendas que vieram do tráfego pago."}
      </p>
      <div className="grade tiles">
        <Tile kpi={kpis.lpag} destaque />
        <Tile kpi={kpis.agfec} />
        <Tile kpi={kpis.lpfec} destaque />
      </div>

      {lpfec > 0 && (
        <div className="cartao cadeia">
          <h3>A conta de uma venda</h3>
          <div className="elos">
            <span className="elo">
              <strong>{umaCasa(lpfec)}</strong> leads{sufixo}
            </span>
            <span className="seta" aria-hidden="true">
              →
            </span>
            <span className="elo">
              <strong>{agfec ? umaCasa(agfec) : "—"}</strong> reuniões marcadas
            </span>
            <span className="seta" aria-hidden="true">
              →
            </span>
            <span className="elo destacado">
              <strong>1</strong> cliente
            </span>
          </div>
          {cac > 0 && (
            <p className="nota-cadeia">
              No ritmo deste mês, cada cliente novo custou {formatar(cac, "brl")} de anúncio.
            </p>
          )}
        </div>
      )}

      <div className="grade dois">
        <div className="cartao simulador">
          <h3>Tenho leads, o que espero disso?</h3>
          <label htmlFor="sim-leads">Leads no mês{sufixo}</label>
          <input
            id="sim-leads"
            inputMode="numeric"
            placeholder="ex.: 400"
            value={leads}
            onChange={(e) => setLeads(e.target.value)}
          />
          {leadsSimulados > 0 && (
            <ul className="saida">
              {lpag > 0 && (
                <li>
                  <strong>{inteiro(leadsSimulados / lpag)}</strong> reuniões marcadas
                </li>
              )}
              {lpfec > 0 && (
                <li>
                  <strong>{inteiro(leadsSimulados / lpfec)}</strong> clientes fechados
                </li>
              )}
            </ul>
          )}
        </div>

        <div className="cartao simulador">
          <h3>Quero vender, de quanto preciso?</h3>
          <label htmlFor="sim-vendas">Clientes que você quer fechar</label>
          <input
            id="sim-vendas"
            inputMode="numeric"
            placeholder="ex.: 12"
            value={vendas}
            onChange={(e) => setVendas(e.target.value)}
          />
          {vendasDesejadas > 0 && (
            <ul className="saida">
              {agfec > 0 && (
                <li>
                  <strong>{inteiro(vendasDesejadas * agfec)}</strong> reuniões a marcar
                </li>
              )}
              {lpfec > 0 && (
                <li>
                  <strong>{inteiro(vendasDesejadas * lpfec)}</strong> leads a gerar{sufixo}
                </li>
              )}
              {cac > 0 && (
                <li>
                  <strong>{formatar(vendasDesejadas * cac, "brl")}</strong> de investimento em
                  anúncio, no CAC atual
                </li>
              )}
            </ul>
          )}
        </div>
      </div>

      <div className="aviso">
        As duas contas repetem o ritmo deste mês, que é a melhor estimativa que existe e não é uma
        promessa: dobrar o investimento raramente dobra o resultado, porque o público bom se
        esgota antes. Use como ponto de partida e confira no mês seguinte.
        {todasAsOrigens
          ? " O investimento estimado cobre só o anúncio: parte dos leads acima vem de indicação e de busca, que não custam mídia."
          : ""}
      </div>
    </>
  );
}
