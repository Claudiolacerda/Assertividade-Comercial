/* Peças do painel: stat tiles, diagnóstico e tabela genérica. */

import { formatar } from "./Charts";

/** Número em destaque. Quando há meta, o selo traz ícone + texto (nunca só cor). */
export function Tile({ kpi, destaque = false }) {
  if (!kpi) return null;
  const temMeta = kpi.meta_tipo != null;
  return (
    <div className={`tile${destaque ? " destaque" : ""}`}>
      <span className="rotulo">{kpi.rotulo}</span>
      <div className="numero">{kpi.texto}</div>
      {temMeta ? (
        <span className={`selo ${kpi.dentro_da_meta ? "ok" : "fora"}`}>
          {kpi.dentro_da_meta ? "✓" : "⚠"}{" "}
          {kpi.dentro_da_meta ? "dentro da meta" : "fora da meta"} (
          {kpi.meta_tipo === "min" ? "mín." : "máx."} {formatar(kpi.meta_valor, kpi.formato)})
        </span>
      ) : (
        <div className="nota">{kpi.explicacao}</div>
      )}
    </div>
  );
}

const ICONES = {
  "🔴": "🔴",
  "⚠️": "⚠️",
  "✅": "✅",
  "🔥": "🔥",
  "ℹ️": "ℹ️",
};

function iconeDe(nivel) {
  const achado = Object.keys(ICONES).find((i) => nivel.includes(i));
  return achado || "ℹ️";
}

const PESO = { "🔴": 0, "🔥": 1, "⚠️": 2, "✅": 3, "ℹ️": 4 };

/** Diagnóstico automático, mais urgente primeiro. */
export function Diagnostico({ itens }) {
  if (!itens?.length) return null;
  const ordenados = [...itens].sort((a, b) => PESO[iconeDe(a.Nível)] - PESO[iconeDe(b.Nível)]);
  return (
    <div className="cartao">
      <h2>O que os números estão dizendo</h2>
      <p style={{ color: "var(--ink-2)", fontSize: 13.5, margin: "4px 0 10px" }}>
        Conclusões geradas pelo cruzamento das duas planilhas — {itens.length} apontamentos.
      </p>
      {ordenados.map((d, i) => (
        <div className="diag" key={i}>
          <span className="icone" aria-hidden="true">
            {iconeDe(d.Nível)}
          </span>
          <div>
            <div className="area">
              {d.Área} · {d.Nível.replace(/[🔴⚠️✅🔥ℹ️]/gu, "").trim() || "informação"}
            </div>
            <div className="texto">{d.Diagnóstico}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

const ehNumero = (v) => typeof v === "number";

function formatoDaColuna(nome) {
  const n = nome.toLowerCase();
  if (n.includes("(r$)")) return "brl";
  if (n.includes("(%)")) return "pct";
  if (n.includes("(x)")) return "x";
  return "int";
}

/** Tabela a partir de qualquer tabela do resultado (as colunas vêm do backend). */
export function TabelaDados({ titulo, subtitulo, linhas, limite = 200 }) {
  if (!linhas?.length) return null;
  const colunas = Object.keys(linhas[0]).filter((c) => !c.startsWith("_"));
  const mostradas = linhas.slice(0, limite);
  return (
    <section className="cartao">
      <h2>{titulo}</h2>
      {subtitulo && (
        <p style={{ color: "var(--ink-2)", fontSize: 13.5, margin: "4px 0 10px" }}>{subtitulo}</p>
      )}
      <div className="rolagem" style={{ maxHeight: 420 }}>
        <table>
          <thead>
            <tr>
              {colunas.map((c) => (
                <th key={c} style={ehNumero(linhas[0][c]) ? { textAlign: "right" } : undefined}>
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {mostradas.map((linha, i) => (
              <tr key={i}>
                {colunas.map((c) => {
                  const v = linha[c];
                  const longo = typeof v === "string" && v.length > 60;
                  return (
                    <td key={c} className={ehNumero(v) ? "num" : longo ? "texto" : undefined}>
                      {ehNumero(v) ? formatar(v, formatoDaColuna(c)) : (v ?? "—")}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {linhas.length > limite && (
        <p style={{ color: "var(--ink-muted)", fontSize: 12.5, marginBottom: 0 }}>
          Mostrando {limite} de {linhas.length} linhas — a planilha exportada traz todas.
        </p>
      )}
    </section>
  );
}
