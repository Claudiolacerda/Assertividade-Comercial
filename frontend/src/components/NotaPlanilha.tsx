/* Nota da planilha: o que falta na base do cliente e o que cada ausência custa.
 *
 * O sistema sempre soube quais colunas não achou — o que faltava era transformar
 * isso em tarefa, com o ganho explícito ao lado. É a conversa que muda "sua
 * planilha está incompleta" para "adicione Valor e ganhe ROAS". */

import { api } from "../api";
import { IconeAtencao } from "./Icones";

const ROTULO_IMPACTO = {
  obrigatorio: "obrigatória",
  alto: "alto impacto",
  medio: "médio impacto",
  baixo: "complementar",
};

export default function NotaPlanilha({ cobertura }) {
  if (!cobertura?.campos?.length) return null;

  const { encontrados, total, campos } = cobertura;
  const pct = Math.round((encontrados / total) * 100);
  const faltando = campos.filter((c) => !c.encontrado);
  const completa = faltando.length === 0;

  return (
    <section className="cartao">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
        <div>
          <h2>Nota da planilha</h2>
          <p style={{ color: "var(--ink-2)", fontSize: 13.5, margin: "5px 0 0" }}>
            {completa
              ? "Planilha completa: todos os indicadores estão liberados."
              : `Com ${encontrados} de ${total} campos, ${faltando.length} indicador(es) ainda estão desligados.`}
          </p>
        </div>
        <div style={{ textAlign: "right", flex: "none" }}>
          <div
            style={{
              fontSize: 30,
              fontWeight: 690,
              letterSpacing: "-0.025em",
              color: completa ? "var(--sucesso-texto)" : "var(--verde)",
              lineHeight: 1.1,
            }}
          >
            {encontrados}/{total}
          </div>
          <div style={{ fontSize: 11.5, color: "var(--ink-muted)" }}>campos reconhecidos</div>
        </div>
      </div>

      {/* barra de progresso: role="img" porque o número já está escrito acima */}
      <div
        role="img"
        aria-label={`${pct}% dos campos reconhecidos`}
        style={{
          height: 8,
          borderRadius: 999,
          background: "var(--surface-2)",
          overflow: "hidden",
          margin: "16px 0 18px",
        }}
      >
        <div
          style={{
            display: "block",
            height: "100%",
            width: `${pct}%`,
            borderRadius: 999,
            background: "var(--verde)",
          }}
        />
      </div>

      {faltando.length > 0 && (
        <>
          <div
            style={{
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "0.05em",
              textTransform: "uppercase",
              color: "var(--ink-muted)",
              marginBottom: 10,
            }}
          >
            O que cada coluna ausente destravaria
          </div>
          {faltando.map((c) => (
            <div
              key={c.campo}
              style={{
                display: "flex",
                gap: 11,
                alignItems: "flex-start",
                padding: "10px 0",
                borderBottom: "1px solid var(--grid)",
              }}
            >
              <span style={{ color: "var(--atencao-texto)", flex: "none", marginTop: 1 }}>
                <IconeAtencao tamanho={14} />
              </span>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 13.5, fontWeight: 620 }}>
                  {c.rotulo}{" "}
                  <span style={{ fontWeight: 500, color: "var(--ink-muted)", fontSize: 12 }}>
                    · {ROTULO_IMPACTO[c.impacto]}
                  </span>
                </div>
                <div style={{ fontSize: 13, color: "var(--ink-2)", marginTop: 2 }}>{c.destrava}</div>
              </div>
            </div>
          ))}

          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", marginTop: 16 }}>
            <button className="primario" onClick={() => api.baixarModelo()}>
              Baixar planilha-modelo
            </button>
            <span style={{ fontSize: 12.5, color: "var(--ink-muted)" }}>
              Já vem com todas as colunas e a lista de etapas pronta.
            </span>
          </div>
        </>
      )}

      {completa && (
        <div className="aviso ok">
          Nada a corrigir. Receita, CAC por campanha, ciclo de venda e motivos de perda estão todos
          calculados.
        </div>
      )}
    </section>
  );
}
