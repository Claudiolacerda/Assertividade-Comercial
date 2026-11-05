/* "E se eu investir mais?" — a resposta que os meses analisados conseguem dar.
 *
 * É a pergunta mais cara da agência e a mais fácil de responder errado, então
 * esta tela mostra o método junto com o número, e não em letra miúda: quantos
 * meses entraram na conta, quanto do resultado o investimento explica, e quais
 * cenários estão fora de qualquer coisa que já foi praticada. Quando os meses
 * não bastam para uma regressão, ela diz isso e cai numa regra de três
 * anunciada como regra de três, em vez de desenhar uma reta fingida. */

import { useState } from "react";

import { api } from "../api";

import { GraficoProjecao, formatar, inteiro, mesPorExtenso, reais } from "./Charts";
import { ICONES_NIVEL, IconeAtencao } from "./Icones";

const PCT = (v: number) => `${v > 0 ? "+" : ""}${Math.round(v * 100)}%`;

const umaCasa = (v: number) =>
  Number(v).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

/** Formata um número PREVISTO, que não tem a precisão de um número medido.
 *
 * "R$ 15.028,33 de receita no mês que vem" promete centavos que ninguém pode
 * prever, e os centavos contaminam a leitura do resto. Em contagem pequena a
 * casa decimal fica, porque a diferença entre 6,2 e 6,9 clientes é meio
 * cliente e importa; em contagem grande ela some. */
function previsto(valor: number, formato: string) {
  if (valor == null) return "—";
  if (formato === "brl") return `R$ ${Math.round(valor).toLocaleString("pt-BR")}`;
  /* O corte em 20: meio cliente num mês de 8 é informação ("6,2 a 7,6"), meia
     visita num mês de 120 leads é ruído com cara de precisão. */
  if (formato === "int") return Math.abs(valor) >= 20 ? inteiro(valor) : umaCasa(valor);
  return formatar(valor, formato);
}

/** Um número previsto, com a faixa embaixo quando ela existe. */
function Previsto({ dado, formato }) {
  if (!dado) return <td className="num">—</td>;
  return (
    <td className="num">
      <div className="valor">{previsto(dado.valor, formato)}</div>
      {dado.min != null && (
        <div className="faixa">
          {previsto(dado.min, formato)} a {previsto(dado.max, formato)}
        </div>
      )}
    </td>
  );
}

export default function Projecao({ dados }) {
  const [simulado, setSimulado] = useState("");
  const [baixando, setBaixando] = useState(false);
  const [erroPdf, setErroPdf] = useState("");

  async function baixarPdf() {
    setBaixando(true);
    setErroPdf("");
    try {
      await api.baixarProjecaoPdf();
    } catch {
      setErroPdf("Não consegui gerar o PDF agora. Tente de novo em instantes.");
    } finally {
      setBaixando(false);
    }
  }
  if (!dados) return null;

  const { metodo, n_meses, minimo_meses, investimento_atual, faixa_observada } = dados;

  if (metodo === "insuficiente") {
    return (
      <section className="cartao projecao">
        <h2>Se eu mudar o investimento</h2>
        <p className="motivo">
          {dados.motivo} Faltam {Math.max(0, (minimo_meses || 3) - (n_meses || 0))} mês(es) com
          investimento registrado para o sistema conseguir medir o efeito.
        </p>
      </section>
    );
  }

  const regra = metodo === "regra_de_tres";
  const modelos = dados.modelos || {};
  /* Coluna sem modelo seria uma fileira de travessões: acontece de verdade
     quando a planilha de um dos meses não tem coluna de valor e a receita fica
     sem pontos suficientes. */
  const alvos = (dados.alvos || []).filter((a) => modelos[a.chave]);
  const vendas = modelos.fec;

  /* A manchete vem pronta do motor, com o nível junto: ela é a afirmação mais
     lida do cartão e tem de ser idêntica à do PDF. Quando a reta é fraca ela
     MUDA de conteúdo, não só de cor — um número grande e verde acima de uma
     linha dizendo "explica 5% da variação" faz o leitor acreditar no de cima. */
  const manchete = dados.manchete;

  const n = (texto: string) => {
    const v = Number(String(texto).replace(/[^\d]/g, ""));
    return Number.isFinite(v) && v > 0 ? v : 0;
  };
  const invSimulado = n(simulado);
  const prever = (chave: string, inv: number) => {
    const m = modelos[chave];
    if (!m) return null;
    return Math.max(0, m.intercepto + m.inclinacao * inv);
  };
  const foraDaFaixa =
    invSimulado > 0 &&
    faixa_observada &&
    (invSimulado < faixa_observada.min || invSimulado > faixa_observada.max);

  return (
    <section className="cartao projecao">
      <div className="topo-projecao">
        <div>
          <h2>Se eu mudar o investimento</h2>
          <p className="sub">
            {/* Os meses vêm nomeados porque o cartão aparece sozinho na home:
                sem a lista, "3 meses" é uma afirmação que o usuário não tem
                como conferir sem ir atrás no histórico. */}
            {regra
              ? `Ritmo médio de ${n_meses} mês(es) analisado(s)`
              : `Tendência medida em ${n_meses} meses analisados`}
            {!!(dados.pontos || []).length && (
              <> ({dados.pontos.map((p) => mesPorExtenso(p.mes_referencia)).join(", ")})</>
            )}
            .{" "}
            {faixa_observada && (
              <>
                O investimento já praticado vai de {reais(faixa_observada.min)} a{" "}
                {reais(faixa_observada.max)} por mês.
              </>
            )}
          </p>
        </div>
        {/* O PDF existe para a reunião: a tela convence quem já confia no
            sistema, o documento convence quem vai perguntar de onde saiu. */}
        <div className="acoes-projecao">
          <button className="discreto" onClick={baixarPdf} disabled={baixando}>
            {baixando ? "Gerando…" : "Baixar PDF"}
          </button>
        </div>
        {!regra && vendas?.r2 != null && (
          <div className="confianca">
            <span className="rotulo">o investimento explica</span>
            <strong>{Math.round(vendas.r2 * 100)}%</strong>
            <span className="rotulo">da variação de vendas</span>
          </div>
        )}
      </div>

      {erroPdf && <p className="erro-inline">{erroPdf}</p>}

      {manchete && (
        <p className={`manchete${manchete.nivel === "ok" ? "" : " fraca"}`}>{manchete.texto}</p>
      )}

      {/* A leitura: a tabela diz O QUE, isto diz E DAÍ. Vem do backend pronta e
          determinística, pela mesma razão do JET: o número e a frase têm de
          concordar sempre. */}
      {!!(dados.leitura || []).length && (
        <ul className="leitura">
          {dados.leitura.map((l, i: number) => {
            const Icone = ICONES_NIVEL[l.nivel] || ICONES_NIVEL.info;
            return (
              <li key={i} className={l.nivel}>
                <span className="marca" aria-hidden="true">
                  <Icone tamanho={14} />
                </span>
                <span>{l.texto}</span>
              </li>
            );
          })}
        </ul>
      )}

      {regra && (
        <div className="aviso" style={{ marginBottom: 14 }}>
          <strong>Ainda não é uma regressão.</strong> {dados.motivo}
        </div>
      )}

      {!regra && (
        <GraficoProjecao
          pontos={dados.pontos}
          modelo={modelos.fec}
          alvo="fec"
          titulo="Clientes fechados"
          formato="int"
        />
      )}

      <div className="rolagem">
        <table className="cenarios">
          <thead>
            <tr>
              <th>Cenário</th>
              <th style={{ textAlign: "right" }}>Investimento</th>
              {alvos.map((a) => (
                <th key={a.chave} style={{ textAlign: "right" }}>
                  {a.rotulo}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {(dados.cenarios || []).map((c) => (
              <tr key={c.variacao} className={c.variacao === 0 ? "atual" : ""}>
                <td>
                  {c.variacao === 0 ? "hoje" : PCT(c.variacao)}
                  {c.fora_do_historico && (
                    <span className="fora" title="Fora do que já foi praticado">
                      <IconeAtencao tamanho={11} /> nunca testado
                    </span>
                  )}
                </td>
                <td className="num">
                  {/* Sem centavos: "investir R$ 4.381,22" sugere uma precisão
                      que um cenário de +20% não tem. */}
                  <div className="valor">{previsto(c.investimento, "brl")}</div>
                </td>
                {alvos.map((a) => (
                  <Previsto key={a.chave} dado={c[a.chave]} formato={a.formato} />
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="simular">
        <label htmlFor="proj-inv">Investir quanto no mês?</label>
        <input
          id="proj-inv"
          inputMode="numeric"
          placeholder={`ex.: ${Math.round(investimento_atual || 3000)}`}
          value={simulado}
          onChange={(e) => setSimulado(e.target.value)}
        />
        {invSimulado > 0 && (
          <ul className="saida">
            {alvos.map((a) => {
              const v = prever(a.chave, invSimulado);
              return v == null ? null : (
                <li key={a.chave}>
                  <strong>{previsto(v, a.formato)}</strong> {a.rotulo.toLowerCase()}
                </li>
              );
            })}
          </ul>
        )}
        {foraDaFaixa && (
          <p className="alerta-faixa">
            <IconeAtencao tamanho={12} /> Esse valor está fora da faixa já praticada. A conta
            continua valendo como ordem de grandeza, não como promessa: o resultado por real tende
            a cair conforme o público bom se esgota.
          </p>
        )}
      </div>

      {(dados.avisos || []).map((a: string, i: number) => (
        <p className="ressalva" key={i}>
          {a}
        </p>
      ))}
      <p className="ressalva">
        Os meses mostram o que andou junto, não o que causou o quê: campanha, oferta e equipe
        mudaram no mesmo período. Cada mês novo analisado deixa esta conta mais firme.
      </p>
    </section>
  );
}
