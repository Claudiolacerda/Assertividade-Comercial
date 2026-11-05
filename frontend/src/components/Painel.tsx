/* Peças do painel: stat tiles, diagnóstico e tabela genérica. */

import { useState } from "react";

import { formatar } from "./Charts";
import { IconeAtencao, IconeOk, IconeQueda, ICONES_NIVEL } from "./Icones";

const porcento1 = (v: number) => `${(v * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;

/* O selo depende do VEREDITO, não de comparar o número com a meta.
 *
 * Uma taxa de 25,7% sobre 35 reuniões tem faixa provável de 14% a 42%: a meta
 * de 30% cai dentro dela, e chamar isso de "fora da meta" é afirmar uma
 * reprovação que o dado não sustenta. A terceira resposta — "ainda não dá para
 * dizer" — é a que faltava, e é a que impede o cliente de trocar vendedor por
 * causa de uma oscilação que é sorteio. */
const SELOS = {
  dentro: { classe: "ok", texto: "dentro da meta" },
  fora: { classe: "fora", texto: "fora da meta" },
  indistinguivel: { classe: "incerto", texto: "ainda não dá para dizer" },
  amostra_pequena: { classe: "incerto", texto: "poucos casos para comparar" },
};

/** Número em destaque. Quando há meta, o selo traz ícone + texto (nunca só cor). */
export function Tile({ kpi, destaque = false }) {
  if (!kpi) return null;
  const temMeta = kpi.meta_tipo != null;
  const faixa = kpi.faixa;
  /* Sem faixa calculada (indicador que não é proporção, como CAC ou receita),
     o selo continua sendo a comparação direta: ali não há amostra para medir. */
  const selo = temMeta
    ? SELOS[faixa?.veredito] || (kpi.dentro_da_meta ? SELOS.dentro : SELOS.fora)
    : null;
  const incerto = selo?.classe === "incerto";
  return (
    <div className={`tile${destaque ? " destaque" : ""}`}>
      <span className="rotulo">{kpi.rotulo}</span>
      <div className="numero">{kpi.texto}</div>
      {faixa && faixa.n > 0 && (
        <div className="faixa-amostral" title={`Faixa provável da taxa real, com ${faixa.n} casos`}>
          {porcento1(faixa.min)} a {porcento1(faixa.max)} · {faixa.n} casos
        </div>
      )}
      {selo ? (
        <span className={`selo ${selo.classe}`}>
          {selo.classe === "ok" ? <IconeOk tamanho={12} /> : <IconeAtencao tamanho={12} />}{" "}
          {selo.texto} ({kpi.meta_tipo === "min" ? "mín." : "máx."}{" "}
          {formatar(kpi.meta_valor, kpi.formato)})
        </span>
      ) : (
        <div className="nota">{kpi.explicacao}</div>
      )}
      {incerto && faixa?.nota && <div className="nota">{faixa.nota}</div>}
    </div>
  );
}

const ICONES = {
  "🔴": "critico",
  "🔥": "quente",
  "⚠️": "atencao",
  "✅": "ok",
  "ℹ️": "info",
};

/** O motor devolve o nível com emoji embutido; aqui ele vira chave de ícone. */
function nivelDe(texto = "") {
  const achado = Object.keys(ICONES).find((i) => texto.includes(i));
  return achado ? ICONES[achado] : "info";
}

const semEmoji = (t = "") => t.replace(/[🔴⚠️✅🔥ℹ️]/gu, "").trim();

/* Os apontamentos chegam num fluxo só. Sem agrupar, a linha que faz o cliente
 * ganhar dinheiro hoje tem o mesmo peso de uma observação informativa — e o
 * usuário com quatro minutos lê as três primeiras e vai embora. */
const GRUPOS = [
  {
    id: "agir",
    titulo: "Para agir agora",
    apoio: "O que muda dinheiro esta semana.",
    aceita: (n, area) => n === "critico" || n === "quente",
  },
  {
    id: "metas",
    titulo: "Fora da meta",
    apoio: "Indicadores abaixo do que você definiu em Configuração.",
    aceita: (n, area) => n === "atencao" && area !== "Dados",
  },
  {
    id: "dados",
    titulo: "Confiabilidade do número",
    apoio: "O que a planilha deixou de contar, e por isso o número pode estar otimista.",
    aceita: (n, area) => n === "atencao" && area === "Dados",
  },
];

function Linha({ item }) {
  const nivel = nivelDe(item.Nível);
  const Icone = ICONES_NIVEL[nivel];
  return (
    <div className="diag">
      <span className={`icone n-${nivel}`}>
        <Icone />
      </span>
      <div>
        <div className="texto">{item.Diagnóstico}</div>
        <div className="area">
          {item.Área} · {semEmoji(item.Nível) || "informação"}
        </div>
      </div>
    </div>
  );
}

/** A oportunidade principal, promovida acima de tudo. É a razão da assinatura. */
export function Destaque({ itens }) {
  const alvo = (itens || []).find((d) => nivelDe(d.Nível) === "quente")
    || (itens || []).find((d) => nivelDe(d.Nível) === "critico");
  if (!alvo) return null;
  const nivel = nivelDe(alvo.Nível);
  const Icone = ICONES_NIVEL[nivel];
  return (
    <div className={`destaque-diag n-${nivel}`}>
      <span className="icone">
        <Icone tamanho={20} />
      </span>
      <div>
        <div className="rotulo">{semEmoji(alvo.Nível) || alvo.Área}</div>
        <p>{alvo.Diagnóstico}</p>
      </div>
    </div>
  );
}

/** Diagnóstico automático, agrupado por o que o usuário faz com cada bloco. */
export function Diagnostico({ itens }) {
  const [abertos, setAbertos] = useState(false);
  if (!itens?.length) return null;

  const usados = new Set();
  const blocos = GRUPOS.map((g) => {
    const lista = itens.filter((d) => {
      const n = nivelDe(d.Nível);
      if (usados.has(d) || !g.aceita(n, d.Área)) return false;
      usados.add(d);
      return true;
    });
    return { ...g, lista };
  }).filter((b) => b.lista.length);

  const resto = itens.filter((d) => !usados.has(d));

  return (
    <div className="cartao">
      <h2>O que os números estão dizendo</h2>
      <p className="sub-cartao">
        Conclusões do cruzamento das duas planilhas: {itens.length} apontamentos.
      </p>

      {blocos.map((b) => (
        <section className="bloco-diag" key={b.id}>
          <h3>
            {b.titulo} <span className="conta">{b.lista.length}</span>
          </h3>
          <p className="apoio">{b.apoio}</p>
          {b.lista.map((d, i) => (
            <Linha item={d} key={i} />
          ))}
        </section>
      ))}

      {resto.length > 0 && (
        <section className="bloco-diag">
          <button
            className="discreto revelar"
            onClick={() => setAbertos((v) => !v)}
            aria-expanded={abertos}
          >
            <span className="seta">
              <IconeQueda tamanho={13} />
            </span>
            {abertos ? "Ocultar" : "Ver"} dentro da meta e informações
            <span className="conta">{resto.length}</span>
          </button>
          {/* grid-template-rows 0fr->1fr: a única forma de animar "altura
              automática" sem medir nada em JS nem travar em max-height chutado. */}
          <div className={`sanfona${abertos ? " aberta" : ""}`}>
            <div>
              {resto.map((d, i) => (
                <Linha item={d} key={i} />
              ))}
            </div>
          </div>
        </section>
      )}
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
export function TabelaDados({
  titulo,
  subtitulo,
  linhas,
  limite = 200,
}: {
  titulo: string;
  subtitulo?: string;
  linhas: Record<string, unknown>[] | null | undefined;
  limite?: number;
}) {
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
                      {ehNumero(v) ? formatar(v, formatoDaColuna(c)) : ((v as string | null) ?? "—")}
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
          Mostrando {limite} de {linhas.length} linhas. A planilha exportada traz todas.
        </p>
      )}
    </section>
  );
}
