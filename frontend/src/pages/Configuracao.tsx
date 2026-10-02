import { useEffect, useState } from "react";

import { api } from "../api";
import { useAuth } from "../auth";
import { mensagemDoErro } from "../erros";

const METAS = [
  { chave: "ctr", titulo: "CTR mínimo no link", tipo: "pct", ajuda: "Cliques ÷ impressões" },
  { chave: "cpl_max", titulo: "Custo por lead máximo", tipo: "brl", ajuda: "Investimento ÷ leads" },
  { chave: "lead_para_reuniao", titulo: "Lead → reunião mínimo", tipo: "pct", ajuda: "Reuniões agendadas ÷ leads" },
  { chave: "comparecimento", titulo: "Comparecimento mínimo", tipo: "pct", ajuda: "Realizadas ÷ (realizadas + no-show)" },
  { chave: "assertividade", titulo: "Assertividade mínima", tipo: "pct", ajuda: "Fechados ÷ reuniões realizadas" },
  { chave: "win_rate", titulo: "Win rate mínimo", tipo: "pct", ajuda: "Fechados ÷ (fechados + perdidos)" },
  { chave: "roas", titulo: "ROAS mínimo", tipo: "x", ajuda: "Receita ÷ investimento" },
  { chave: "cac_max", titulo: "CAC máximo", tipo: "brl", ajuda: "Investimento ÷ clientes fechados" },
];

// pct é guardado como fração (0,25) e editado como número inteiro (25)
const paraTela = (v, tipo) => (tipo === "pct" ? Math.round(v * 1000) / 10 : v);
const paraApi = (v, tipo) => (tipo === "pct" ? Number(v) / 100 : Number(v));

export default function Configuracao() {
  const { ehAdmin, ehAgencia } = useAuth();
  const [virando, setVirando] = useState(false);
  const [config, setConfig] = useState<any>(null);
  const [erro, setErro] = useState("");
  const [salvo, setSalvo] = useState("");
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    api.configuracao().then(setConfig).catch((e) => setErro(mensagemDoErro(e)));
  }, []);

  if (erro) return <div className="aviso erro">{erro}</div>;
  if (!config) return <div className="vazio">Carregando…</div>;

  const mudarMeta = (chave, tipo) => (e) =>
    setConfig((c) => ({ ...c, metas: { ...c.metas, [chave]: paraApi(e.target.value, tipo) } }));

  async function salvar(e) {
    e.preventDefault();
    setErro("");
    setSalvo("");
    setSalvando(true);
    try {
      const atualizado = await api.salvarConfiguracao({
        metas: config.metas,
        marcacoes_nao_pagas: config.marcacoes_nao_pagas,
        classificar_perda_pela_observacao: config.classificar_perda_pela_observacao,
        prob_fechamento_negociacao: config.prob_fechamento_negociacao,
        dias_alerta_pipeline: config.dias_alerta_pipeline,
        origens_trafego_pago: config.origens_trafego_pago,
        sem_origem_considerar_pago: config.sem_origem_considerar_pago,
      });
      setConfig(atualizado);
      setSalvo("Configuração salva. Vale a partir da próxima análise.");
    } catch (err) {
      setErro(mensagemDoErro(err));
    } finally {
      setSalvando(false);
    }
  }

  return (
    <>
      <div className="cabecalho-pagina">
        <div>
          <h1>Configuração</h1>
          <p>
            As metas definem quais indicadores aparecem como dentro ou fora do alvo, e alimentam o
            diagnóstico automático.
          </p>
        </div>
      </div>

      {!ehAdmin && (
        <div className="aviso" style={{ marginBottom: 16 }}>
          Só o administrador da empresa pode alterar a configuração. Você está vendo os valores
          atuais.
        </div>
      )}

      <form onSubmit={salvar}>
        <section className="cartao" style={{ marginBottom: 16 }}>
          <h2>Metas do seu negócio</h2>
          <div className="grade" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))", marginTop: 14 }}>
            {METAS.map((m) => (
              <div key={m.chave}>
                <label htmlFor={m.chave}>
                  {m.titulo} {m.tipo === "pct" ? "(%)" : m.tipo === "brl" ? "(R$)" : "(x)"}
                </label>
                <input
                  id={m.chave}
                  type="number"
                  step={m.tipo === "pct" ? "0.1" : m.tipo === "x" ? "0.1" : "1"}
                  min="0"
                  value={paraTela(config.metas[m.chave] ?? 0, m.tipo)}
                  onChange={mudarMeta(m.chave, m.tipo)}
                  disabled={!ehAdmin}
                />
                <p style={{ fontSize: 12, color: "var(--ink-muted)", margin: "5px 0 0" }}>{m.ajuda}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="cartao" style={{ marginBottom: 16 }}>
          <h2>Atribuição e pipeline</h2>
          <div className="grade" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", marginTop: 14 }}>
            <div>
              <label htmlFor="marcacoes">Marcações que NÃO vieram de tráfego pago</label>
              <input
                id="marcacoes"
                value={(config.marcacoes_nao_pagas || []).join(", ")}
                onChange={(e) =>
                  setConfig((c) => ({
                    ...c,
                    marcacoes_nao_pagas: e.target.value
                      .split(",")
                      .map((s) => s.trim())
                      .filter(Boolean),
                  }))
                }
                disabled={!ehAdmin}
                placeholder="ex.: Parceiro, Indicação"
              />
              <p style={{ fontSize: 12, color: "var(--ink-muted)", margin: "5px 0 0" }}>
                Sufixo depois do hífen no nome do cliente. Quem estiver aqui sai do CAC do anúncio.
              </p>
            </div>
            <div>
              <label htmlFor="origens">Palavras que indicam tráfego pago na coluna Origem</label>
              <input
                id="origens"
                value={(config.origens_trafego_pago || []).join(", ")}
                onChange={(e) =>
                  setConfig((c) => ({
                    ...c,
                    origens_trafego_pago: e.target.value
                      .split(",")
                      .map((s) => s.trim())
                      .filter(Boolean),
                  }))
                }
                disabled={!ehAdmin}
              />
            </div>
            <div>
              <label htmlFor="prob">Probabilidade de fechar uma negociação aberta (%)</label>
              <input
                id="prob"
                type="number"
                min="0"
                max="100"
                step="5"
                value={Math.round((config.prob_fechamento_negociacao ?? 0.3) * 100)}
                onChange={(e) =>
                  setConfig((c) => ({ ...c, prob_fechamento_negociacao: Number(e.target.value) / 100 }))
                }
                disabled={!ehAdmin}
              />
              <p style={{ fontSize: 12, color: "var(--ink-muted)", margin: "5px 0 0" }}>
                Usada no forecast ponderado do pipeline.
              </p>
            </div>
            <div>
              <label htmlFor="dias">Dias para considerar uma negociação parada</label>
              <input
                id="dias"
                type="number"
                min="1"
                max="365"
                value={config.dias_alerta_pipeline ?? 15}
                onChange={(e) =>
                  setConfig((c) => ({ ...c, dias_alerta_pipeline: Number(e.target.value) }))
                }
                disabled={!ehAdmin}
              />
            </div>
          </div>

          <div style={{ marginTop: 18, display: "grid", gap: 10 }}>
            <label style={{ display: "flex", gap: 9, alignItems: "flex-start", fontWeight: 500 }}>
              <input
                type="checkbox"
                style={{ marginTop: 2 }}
                checked={Boolean(config.classificar_perda_pela_observacao)}
                onChange={(e) =>
                  setConfig((c) => ({ ...c, classificar_perda_pela_observacao: e.target.checked }))
                }
                disabled={!ehAdmin}
              />
              <span>
                Contar como <strong>perdida</strong> a reunião cuja observação tem sinal claro de
                perda (“sem interesse”, “trocou de contabilidade”), mesmo que a etapa diga só
                “Reunião feita”.
                <br />
                <span style={{ fontSize: 12, color: "var(--ink-muted)" }}>
                  Deixa a assertividade mais honesta quando a equipe não registra as perdas.
                </span>
              </span>
            </label>
            <label style={{ display: "flex", gap: 9, alignItems: "flex-start", fontWeight: 500 }}>
              <input
                type="checkbox"
                style={{ marginTop: 2 }}
                checked={Boolean(config.sem_origem_considerar_pago)}
                onChange={(e) =>
                  setConfig((c) => ({ ...c, sem_origem_considerar_pago: e.target.checked }))
                }
                disabled={!ehAdmin}
              />
              <span>
                Se a planilha não tiver coluna de origem, considerar todas as reuniões como vindas
                do tráfego pago.
              </span>
            </label>
          </div>
        </section>

        {!ehAgencia && ehAdmin && (
          <section className="cartao" style={{ marginBottom: 16 }}>
            <h2>Você atende outros clientes?</h2>
            <p style={{ color: "var(--ink-2)", fontSize: 14, margin: "8px 0 14px", maxWidth: "70ch" }}>
              Hoje esta conta analisa só o seu comercial. Ligando o modo agência aparece a{" "}
              <strong>Carteira</strong>: você cadastra quantos clientes quiser, cada um com dados
              isolados, e alterna entre eles com um seletor. Nada do que já existe se perde.
            </p>
            <button
              type="button"
              onClick={async () => {
                if (!window.confirm("Ligar o modo agência? Você poderá adicionar outros clientes.")) return;
                setVirando(true);
                try {
                  await api.mudarTipoOrganizacao("agencia");
                  window.location.reload();
                } catch (e) {
                  setErro(mensagemDoErro(e));
                } finally {
                  setVirando(false);
                }
              }}
              disabled={virando}
            >
              {virando ? "Ligando…" : "Ligar modo agência"}
            </button>
          </section>
        )}

        {salvo && (
          <div className="aviso ok" style={{ marginBottom: 14 }}>
            {salvo}
          </div>
        )}
        {erro && (
          <div className="aviso erro" style={{ marginBottom: 14 }} role="alert">
            {erro}
          </div>
        )}

        {ehAdmin && (
          <button className="primario" type="submit" disabled={salvando}>
            {salvando ? "Salvando…" : "Salvar configuração"}
          </button>
        )}
      </form>
    </>
  );
}
