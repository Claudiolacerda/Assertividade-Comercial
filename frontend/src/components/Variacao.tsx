/* Por que a receita mudou. A pergunta que o cliente faz primeiro.
 *
 * O painel já mostrava os cinco indicadores da cadeia lado a lado, e obrigava
 * o usuário a comparar cada um com o do mês passado e juntar de cabeça. Quem
 * tem quatro minutos não faz essa conta — responde "o mercado estava fraco" e
 * perde a reunião.
 *
 * Aqui a diferença vem repartida entre os fatores, com a barra proporcional ao
 * efeito em reais. A soma das barras é exatamente a variação do topo: não há
 * resíduo, não há "outros". */

import { formatar, reais } from "./Charts";
import { IconeAtencao, IconeOk } from "./Icones";

const pct = (v: number) => `${v > 0 ? "+" : ""}${(v * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;

export default function Variacao({ dados }) {
  if (!dados) return null;
  if (!dados.disponivel) {
    return (
      <section className="cartao variacao">
        <h2>Por que a receita mudou</h2>
        <p className="motivo">{dados.motivo}</p>
      </section>
    );
  }

  const { contribuicoes = [], variacao_reais: total } = dados;
  /* A escala das barras sai do maior efeito em módulo, não da receita: o que
     se compara aqui é o peso de um fator contra o outro. */
  const maior = Math.max(...contribuicoes.map((c) => Math.abs(c.efeito_reais)), 1);
  const subiu = total >= 0;

  return (
    <section className="cartao variacao">
      <div className="topo-variacao">
        <div>
          <h2>Por que a receita mudou</h2>
          <p className="sub">
            De {dados.mes_anterior} para {dados.mes_atual}, repartido entre os cinco fatores da
            cadeia. As parcelas somam exatamente a variação, sem sobra.
          </p>
        </div>
        <div className={`total-variacao ${subiu ? "subiu" : "caiu"}`}>
          <span className="rotulo">receita</span>
          <strong>
            {subiu ? "+" : "−"}
            {reais(Math.abs(total)).replace("R$ ", "R$ ")}
          </strong>
          <span className="rotulo">{pct(dados.variacao_pct)}</span>
        </div>
      </div>

      <p className="leitura-variacao">
        {subiu ? <IconeOk tamanho={13} /> : <IconeAtencao tamanho={13} />} {dados.leitura}
      </p>

      <ul className="fatores">
        {contribuicoes.map((c) => {
          const positivo = c.efeito_reais >= 0;
          const largura = Math.round((Math.abs(c.efeito_reais) / maior) * 100);
          return (
            <li key={c.fator}>
              <div className="nome">
                <strong>{c.rotulo}</strong>
                <span className="de-para">
                  {formatar(c.antes, c.formato)} → {formatar(c.depois, c.formato)} ·{" "}
                  {pct(c.variacao)}
                </span>
              </div>
              <div className="barra">
                <span className={positivo ? "sobe" : "desce"} style={{ width: `${largura}%` }} />
              </div>
              <div className={`efeito ${positivo ? "sobe" : "desce"}`}>
                {positivo ? "+" : "−"}
                {reais(Math.abs(c.efeito_reais))}
              </div>
            </li>
          );
        })}
      </ul>

      <p className="ressalva">
        Cada parcela responde "quanto da variação da receita veio deste fator, mantendo os outros
        como estavam". {dados.base_leads === "paga" && "O volume de leads aqui é o que a Meta reportou."}
      </p>
    </section>
  );
}
