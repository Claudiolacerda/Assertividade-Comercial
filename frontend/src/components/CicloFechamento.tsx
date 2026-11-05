/* Quando o negócio fecha, contando também os que ainda não fecharam.
 *
 * A média do ciclo olha só para quem fechou. Como os ciclos longos ainda não
 * terminaram, ela enxerga só os curtos: o viés é sistemático e sempre
 * otimista, e o número sai bonito justamente quando a operação está travando.
 *
 * A curva de Kaplan-Meier usa o negócio em aberto como informação parcial
 * ("já passou de 45 dias sem fechar"). Por isso as duas aparecem lado a lado:
 * a diferença entre elas é a medida do viés, e é o que convence. */

import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { porcento } from "./Charts";

const EIXO = { fontSize: 11.5, fill: "var(--ink-muted)" };

export default function CicloFechamento({ km }) {
  if (!km?.marcos?.length) return null;

  const curva = km.curva.map((p) => ({ dias: p.dias, acumulado: p.acumulado }));
  const ultimo = curva[curva.length - 1];
  const limite = Math.max(km.limite_dias || 0, ultimo?.dias || 0);
  /* Dois acertos de desenho, nenhum deles sobre o dado:
     1. o trecho plano até o fim do acompanhamento é informação — ele diz que
        se continuou olhando e ninguém mais fechou;
     2. o degrau só aparece quando há um ponto DEPOIS dele (é assim que o
        "stepAfter" desenha), então sem uma ponta final o último fechamento
        some do gráfico. A ponta vai 6% além do fim do acompanhamento e a linha
        tracejada marca onde a observação realmente terminou. */
  const ponta = limite > 0 ? limite * 1.06 : 1;
  /* A escada é montada a mão, com dois pontos por degrau, em vez de confiar no
     "stepAfter" do Recharts: ali o último degrau precisa de um ponto depois
     dele para existir, e o fechamento mais tardio sumia do gráfico justamente
     por ser o último. Com os pontos explícitos a curva desenha o que a conta
     diz, sem depender de como a biblioteca interpola. */
  const dados: { dias: number; acumulado: number }[] = [{ dias: 0, acumulado: 0 }];
  let anterior = 0;
  for (const ponto of curva) {
    dados.push({ dias: ponto.dias, acumulado: anterior });
    dados.push({ dias: ponto.dias, acumulado: ponto.acumulado });
    anterior = ponto.acumulado;
  }
  dados.push({ dias: ponta, acumulado: anterior });

  return (
    <section className="cartao ciclo-km">
      <h2>Quando o negócio fecha</h2>
      <p className="sub">
        Inclui os {km.em_aberto_ou_perdidos} negócios que ainda não fecharam, como informação
        parcial. São {km.fechados} fechamentos em {km.n} negócios acompanhados, e a linha
        tracejada marca até onde se observou.
      </p>

      <p className="leitura-ciclo">{km.leitura}</p>

      <div className="marcos">
        {km.marcos.map((m) => (
          <div className="marco" key={m.dias}>
            <span className="prazo">até {m.dias} dias</span>
            <strong>{porcento(m.fechado, 0)}</strong>
          </div>
        ))}
      </div>

      <div style={{ width: "100%", height: 200 }}>
        <ResponsiveContainer>
          <AreaChart data={dados} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis
              dataKey="dias"
              type="number"
              allowDecimals={false}
              tick={EIXO}
              axisLine={{ stroke: "var(--axis)" }}
              tickLine={false}
              tickFormatter={(v) => `${v}d`}
            />
            <YAxis
              tick={EIXO}
              axisLine={false}
              tickLine={false}
              width={44}
              domain={[0, 1]}
              tickFormatter={(v) => porcento(v, 0)}
            />
            <Tooltip
              formatter={(v: number) => [porcento(v, 1), "fechado até aqui"]}
              labelFormatter={(v) => `${v} dias`}
              contentStyle={{
                background: "var(--surface)",
                border: "1px solid var(--borda)",
                borderRadius: 9,
                fontSize: 13,
              }}
            />
            <ReferenceLine
              x={limite}
              stroke="var(--axis)"
              strokeDasharray="3 3"
              /* Sem rótulo no gráfico: encostado na borda direita ele era
                 cortado, e no topo cobria o trecho em 100%. A legenda da linha
                 fica no texto acima, onde cabe inteira. */
            />
            <Area
              type="linear"
              dataKey="acumulado"
              stroke="var(--series-1)"
              fill="var(--series-1)"
              fillOpacity={0.14}
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {km.media_ingenua != null && (
        <p className="ressalva">
          A média simples do ciclo, contando só quem fechou, dá{" "}
          <strong>{km.media_ingenua.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} dias</strong>
          . Ela ignora os negócios ainda abertos, e como os ciclos longos são justamente os que
          ainda não terminaram, ela sempre sai mais curta que a realidade. A curva acima não tem
          esse viés.
        </p>
      )}
    </section>
  );
}
