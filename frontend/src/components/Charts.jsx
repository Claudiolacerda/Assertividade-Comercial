/* Gráficos do painel.
 *
 * Regras seguidas em todos: uma escala por gráfico (nunca dois eixos y), cor por
 * entidade e não por posição no ranking, legenda sempre que houver 2+ séries,
 * rótulos diretos seletivos, grade recessiva, tooltip no hover e "ver tabela"
 * como alternativa acessível aos dados. */

import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const cor = (nome) =>
  getComputedStyle(document.documentElement).getPropertyValue(nome).trim() || "#2a78d6";

export const S1 = "var(--series-1)";
export const S2 = "var(--series-2)";
export const S3 = "var(--series-3)";

const EIXO = { fontSize: 11.5, fill: "var(--ink-muted)" };
const MARGEM = { top: 8, right: 16, bottom: 4, left: 4 };

export const inteiro = (v) => (v == null ? "—" : Number(v).toLocaleString("pt-BR"));
export const porcento = (v, casas = 1) =>
  v == null ? "—" : `${(Number(v) * 100).toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas })}%`;
/** "2026-09" -> "setembro/2026". Quatro formatos para o mesmo conceito viraram um. */
export const mesPorExtenso = (iso) => {
  if (!iso || !/^\d{4}-\d{2}$/.test(iso)) return iso || "—";
  const [ano, mes] = iso.split("-");
  const nome = new Date(Number(ano), Number(mes) - 1, 1).toLocaleDateString("pt-BR", { month: "long" });
  return `${nome}/${ano}`;
};

export const dataHora = (iso) =>
  new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit",
  });

export const reais = (v) =>
  v == null
    ? "—"
    : `R$ ${Number(v).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export function formatar(valor, formato) {
  if (formato === "brl") return reais(valor);
  if (formato === "pct") return porcento(valor);
  if (formato === "x") return `${Number(valor).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}x`;
  return inteiro(valor);
}

/* ---------------------------------------------------------------- */
function Dica({ active, payload, label, formatos = {} }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="dica">
      <div className="titulo">{label}</div>
      {payload.map((p) => (
        <div className="linha" key={p.dataKey}>
          <span className="marca-cor" style={{ background: p.color, width: 9, height: 9, borderRadius: 2 }} />
          <span>{p.name}</span>
          <span className="valor">{formatar(p.value, formatos[p.dataKey] || "int")}</span>
        </div>
      ))}
    </div>
  );
}

function Legenda({ itens }) {
  if (itens.length < 2) return null; // uma série só: o título já a nomeia
  return (
    <ul className="legenda">
      {itens.map((i) => (
        <li key={i.nome}>
          <span className="marca-cor" style={{ background: i.cor }} />
          {i.nome}
        </li>
      ))}
    </ul>
  );
}

function Tabela({ colunas, linhas }) {
  return (
    <div className="rolagem" style={{ maxHeight: 300 }}>
      <table>
        <thead>
          <tr>
            {colunas.map((c) => (
              <th key={c.chave} style={c.num ? { textAlign: "right" } : undefined}>
                {c.titulo}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {linhas.map((l, i) => (
            <tr key={i}>
              {colunas.map((c) => (
                <td key={c.chave} className={c.num ? "num" : undefined}>
                  {c.num ? formatar(l[c.chave], c.formato) : (l[c.chave] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Moldura comum: título, subtítulo, legenda e alternância gráfico/tabela. */
export function Quadro({ titulo, subtitulo, legenda = [], tabela, altura = 260, children }) {
  const [verTabela, setVerTabela] = useState(false);
  return (
    <section className="grafico">
      <div className="grafico-topo">
        <h2>{titulo}</h2>
        {tabela && (
          <button className="discreto" onClick={() => setVerTabela((v) => !v)}>
            {verTabela ? "ver gráfico" : "ver tabela"}
          </button>
        )}
      </div>
      {subtitulo && <p className="legenda-sub">{subtitulo}</p>}
      {verTabela ? (
        <Tabela {...tabela} />
      ) : (
        <>
          <Legenda itens={legenda} />
          <div style={{ width: "100%", height: altura }}>
            <ResponsiveContainer>{children}</ResponsiveContainer>
          </div>
        </>
      )}
    </section>
  );
}

/* ================================================================ */
/* Funil: barras horizontais, cor única (o comprimento já é a magnitude).  */
/* Impressões ficam fora — a escala esconderia as outras etapas.           */
export function GraficoFunil({ funil }) {
  const dados = funil
    .filter((f) => f.Etapa !== "Impressões")
    .map((f) => ({
      etapa: f.Etapa.replace(" (tráfego pago)", "").replace(" / conversas (Meta)", ""),
      quantidade: f.Quantidade,
      conversao: f["Conversão da etapa anterior (%)"],
      custo: f["Custo por etapa (R$)"],
    }));
  return (
    <Quadro
      titulo="Funil do anúncio ao cliente"
      subtitulo="Impressões ficam fora do gráfico: a escala esconderia as outras etapas."
      altura={250}
      tabela={{
        colunas: [
          { chave: "etapa", titulo: "Etapa" },
          { chave: "quantidade", titulo: "Quantidade", num: true, formato: "int" },
          { chave: "conversao", titulo: "Conversão da etapa anterior", num: true, formato: "pct" },
          { chave: "custo", titulo: "Custo por etapa", num: true, formato: "brl" },
        ],
        linhas: dados,
      }}
    >
      <BarChart data={dados} layout="vertical" margin={{ ...MARGEM, left: 8, right: 56 }} barSize={18}>
        <CartesianGrid horizontal={false} stroke="var(--grid)" />
        <XAxis type="number" tick={EIXO} axisLine={{ stroke: "var(--axis)" }} tickLine={false} />
        <YAxis
          type="category"
          dataKey="etapa"
          width={168}
          tick={EIXO}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          content={<Dica formatos={{ quantidade: "int" }} />}
          cursor={{ fill: "var(--surface-2)" }}
        />
        <Bar
          dataKey="quantidade"
          name="Quantidade"
          fill={S1}
          radius={[0, 4, 4, 0]}
          label={{
            position: "right",
            fill: "var(--ink-2)",
            fontSize: 11.5,
            formatter: (v) => inteiro(v),
          }}
        />
      </BarChart>
    </Quadro>
  );
}

/* ---------------------------------------------------------------- */
/* Status das reuniões: categorias nominais, uma cor só.            */
export function GraficoStatus({ porStatus }) {
  const dados = porStatus.map((s) => ({
    status: s["Status padronizado"],
    quantidade: s.Quantidade,
    parte: s["% do total (%)"],
  }));
  return (
    <Quadro
      titulo="Status das reuniões"
      subtitulo="Como cada etapa da sua planilha foi classificada."
      tabela={{
        colunas: [
          { chave: "status", titulo: "Status" },
          { chave: "quantidade", titulo: "Reuniões", num: true, formato: "int" },
          { chave: "parte", titulo: "% do total", num: true, formato: "pct" },
        ],
        linhas: dados,
      }}
    >
      <BarChart data={dados} margin={MARGEM} barSize={30}>
        <CartesianGrid vertical={false} stroke="var(--grid)" />
        <XAxis
          dataKey="status"
          tick={EIXO}
          axisLine={{ stroke: "var(--axis)" }}
          tickLine={false}
          interval={0}
          height={50}
          angle={-18}
          textAnchor="end"
        />
        <YAxis tick={EIXO} axisLine={false} tickLine={false} allowDecimals={false} />
        <Tooltip content={<Dica formatos={{ quantidade: "int" }} />} cursor={{ fill: "var(--surface-2)" }} />
        <Bar
          dataKey="quantidade"
          name="Reuniões"
          fill={S1}
          radius={[4, 4, 0, 0]}
          label={{ position: "top", fill: "var(--ink-2)", fontSize: 11.5 }}
        />
      </BarChart>
    </Quadro>
  );
}

/* ---------------------------------------------------------------- */
/* Assertividade por responsável, com a meta como linha de referência. */
export function GraficoResponsavel({ porResponsavel, meta }) {
  const chave = "Assertividade - fechamento s/ realizadas (%)";
  const dados = porResponsavel
    .filter((r) => r["Reuniões realizadas"] > 0)
    .map((r) => ({
      responsavel: r.Responsável,
      assertividade: r[chave],
      realizadas: r["Reuniões realizadas"],
      fechados: r.Fechados,
    }));
  if (!dados.length) return null;
  return (
    <Quadro
      titulo="Assertividade por responsável"
      subtitulo={`Fechados ÷ reuniões realizadas. A linha tracejada é a meta (${porcento(meta)}).`}
      tabela={{
        colunas: [
          { chave: "responsavel", titulo: "Responsável" },
          { chave: "realizadas", titulo: "Realizadas", num: true, formato: "int" },
          { chave: "fechados", titulo: "Fechados", num: true, formato: "int" },
          { chave: "assertividade", titulo: "Assertividade", num: true, formato: "pct" },
        ],
        linhas: dados,
      }}
    >
      <BarChart data={dados} margin={MARGEM} barSize={34}>
        <CartesianGrid vertical={false} stroke="var(--grid)" />
        <XAxis dataKey="responsavel" tick={EIXO} axisLine={{ stroke: "var(--axis)" }} tickLine={false} interval={0} />
        <YAxis tick={EIXO} axisLine={false} tickLine={false} tickFormatter={(v) => `${Math.round(v * 100)}%`} />
        <Tooltip content={<Dica formatos={{ assertividade: "pct" }} />} cursor={{ fill: "var(--surface-2)" }} />
        <ReferenceLine
          y={meta}
          stroke="var(--ink-muted)"
          strokeDasharray="5 4"
          strokeWidth={2}
          label={{ value: `meta ${porcento(meta, 0)}`, position: "right", fill: "var(--ink-muted)", fontSize: 11 }}
        />
        <Bar
          dataKey="assertividade"
          name="Assertividade"
          radius={[4, 4, 0, 0]}
          label={{ position: "top", fill: "var(--ink-2)", fontSize: 11.5, formatter: (v) => porcento(v, 0) }}
        >
          {/* Cor por entidade: fica igual quando a lista é filtrada */}
          {dados.map((d) => (
            <Cell key={d.responsavel} fill={S1} />
          ))}
        </Bar>
      </BarChart>
    </Quadro>
  );
}

/* ---------------------------------------------------------------- */
/* Semana a semana: três contagens na MESMA unidade -> um eixo só.  */
export function GraficoSemanas({ porSemana }) {
  const dados = porSemana.map((s) => ({
    semana: s.Semana,
    agendadas: s["Reuniões agendadas"],
    realizadas: s["Reuniões realizadas"],
    fechados: s.Fechados,
  }));
  const legenda = [
    { nome: "Agendadas", cor: cor("--series-1") },
    { nome: "Realizadas", cor: cor("--series-2") },
    { nome: "Fechados", cor: cor("--series-3") },
  ];
  return (
    <Quadro
      titulo="Semana a semana"
      subtitulo="Todas as séries são contagens de reuniões, por isso dividem o mesmo eixo."
      legenda={legenda}
      tabela={{
        colunas: [
          { chave: "semana", titulo: "Semana" },
          { chave: "agendadas", titulo: "Agendadas", num: true, formato: "int" },
          { chave: "realizadas", titulo: "Realizadas", num: true, formato: "int" },
          { chave: "fechados", titulo: "Fechados", num: true, formato: "int" },
        ],
        linhas: dados,
      }}
    >
      <LineChart data={dados} margin={MARGEM}>
        <CartesianGrid vertical={false} stroke="var(--grid)" />
        <XAxis dataKey="semana" tick={EIXO} axisLine={{ stroke: "var(--axis)" }} tickLine={false} />
        <YAxis tick={EIXO} axisLine={false} tickLine={false} allowDecimals={false} />
        <Tooltip content={<Dica />} cursor={{ stroke: "var(--axis)", strokeWidth: 1 }} />
        <Line type="monotone" dataKey="agendadas" name="Agendadas" stroke={S1} strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
        <Line type="monotone" dataKey="realizadas" name="Realizadas" stroke={S2} strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
        <Line type="monotone" dataKey="fechados" name="Fechados" stroke={S3} strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
      </LineChart>
    </Quadro>
  );
}

/* ---------------------------------------------------------------- */
/* Investimento por campanha: uma medida, uma cor.                  */
export function GraficoCampanhas({ metaCampanhas }) {
  const dados = metaCampanhas
    .filter((c) => c["Investimento (R$)"] > 0)
    .slice(0, 8)
    .map((c) => ({
      campanha: c.Campanha.length > 34 ? `${c.Campanha.slice(0, 33)}…` : c.Campanha,
      nomeCompleto: c.Campanha,
      investimento: c["Investimento (R$)"],
      leads: c["Leads / resultados"],
      cpl: c["Custo por lead (R$)"],
    }));
  if (!dados.length) return null;
  return (
    <Quadro
      titulo="Investimento por campanha"
      subtitulo="Oito maiores do período. Leads e CPL aparecem no hover e na tabela."
      altura={Math.max(220, dados.length * 34 + 40)}
      tabela={{
        colunas: [
          { chave: "nomeCompleto", titulo: "Campanha" },
          { chave: "investimento", titulo: "Investimento", num: true, formato: "brl" },
          { chave: "leads", titulo: "Leads", num: true, formato: "int" },
          { chave: "cpl", titulo: "Custo por lead", num: true, formato: "brl" },
        ],
        linhas: dados,
      }}
    >
      <BarChart data={dados} layout="vertical" margin={{ ...MARGEM, right: 78 }} barSize={18}>
        <CartesianGrid horizontal={false} stroke="var(--grid)" />
        <XAxis type="number" tick={EIXO} axisLine={{ stroke: "var(--axis)" }} tickLine={false} />
        <YAxis type="category" dataKey="campanha" width={210} tick={EIXO} axisLine={false} tickLine={false} />
        <Tooltip
          content={<Dica formatos={{ investimento: "brl" }} />}
          cursor={{ fill: "var(--surface-2)" }}
        />
        <Bar
          dataKey="investimento"
          name="Investimento"
          fill={S1}
          radius={[0, 4, 4, 0]}
          label={{ position: "right", fill: "var(--ink-2)", fontSize: 11.5, formatter: (v) => reais(v) }}
        />
      </BarChart>
    </Quadro>
  );
}

/* ---------------------------------------------------------------- */
/* Evolução mês a mês. UM indicador por gráfico: assertividade (%) e
   CAC (R$) não compartilham escala, então são dois gráficos, nunca dois eixos. */
export function GraficoEvolucao({ meses, chave, titulo, formato, cor: corLinha = S1, meta }) {
  const dados = meses
    .filter((m) => m[chave] != null)
    .map((m) => ({ mes: m.mes_referencia, valor: m[chave] }));
  if (dados.length < 2) return null;
  return (
    <Quadro
      titulo={titulo}
      subtitulo={`Última análise de cada mês. ${dados.length} meses no histórico.`}
      tabela={{
        colunas: [
          { chave: "mes", titulo: "Mês" },
          { chave: "valor", titulo: titulo, num: true, formato },
        ],
        linhas: dados,
      }}
    >
      <LineChart data={dados} margin={MARGEM}>
        <CartesianGrid vertical={false} stroke="var(--grid)" />
        <XAxis dataKey="mes" tick={EIXO} axisLine={{ stroke: "var(--axis)" }} tickLine={false} />
        <YAxis
          tick={EIXO}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => (formato === "pct" ? `${Math.round(v * 100)}%` : formatar(v, formato))}
          width={formato === "brl" ? 78 : 52}
        />
        <Tooltip content={<Dica formatos={{ valor: formato }} />} cursor={{ stroke: "var(--axis)" }} />
        {meta != null && (
          <ReferenceLine y={meta} stroke="var(--ink-muted)" strokeDasharray="5 4" strokeWidth={2} />
        )}
        <Line
          type="monotone"
          dataKey="valor"
          name={titulo}
          stroke={corLinha}
          strokeWidth={2}
          dot={{ r: 4 }}
          activeDot={{ r: 6 }}
        />
      </LineChart>
    </Quadro>
  );
}
