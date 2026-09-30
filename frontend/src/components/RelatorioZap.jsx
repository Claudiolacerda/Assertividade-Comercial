/* Relatório para WhatsApp: prévia editável, copiar, abrir e enviar.
 *
 * Três caminhos de propósito. "Abrir no WhatsApp" funciona no primeiro dia, sem
 * credencial nenhuma — e é o que a maioria vai usar. O envio automático só
 * aparece quando o servidor está configurado, em vez de oferecer um botão que
 * falha. */

import { useEffect, useState } from "react";

import { api } from "../api";
import { useAuth } from "../auth";

export default function RelatorioZap({ analiseId, nomeCliente }) {
  const { ehAdmin } = useAuth();
  const [texto, setTexto] = useState("");
  const [link, setLink] = useState("");
  const [numero, setNumero] = useState("");
  const [completo, setCompleto] = useState(false);
  const [automatico, setAutomatico] = useState(false);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [aviso, setAviso] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [editado, setEditado] = useState(false);

  useEffect(() => {
    let ativo = true;
    setCarregando(true);
    setErro("");
    api
      .previaZap(analiseId, completo)
      .then((d) => {
        if (!ativo) return;
        // não sobrescreve o que a pessoa já editou à mão
        if (!editado) setTexto(d.texto);
        setLink(d.link);
        setNumero((n) => n || d.numero || "");
        setAutomatico(d.envio_automatico);
      })
      .catch((e) => ativo && setErro(e.message))
      .finally(() => ativo && setCarregando(false));
    return () => {
      ativo = false;
    };
    // `editado` fora das dependências de propósito: trocar resumo/completo
    // deve regerar, mas digitar no textarea não deve disparar requisição
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [analiseId, completo]);

  /** O link do backend traz o texto original; se a pessoa editou, refaz aqui. */
  function linkAtual() {
    const so = (numero || "").replace(/\D/g, "");
    const destino = so ? (so.startsWith("55") ? so : `55${so}`) : "";
    return `https://wa.me/${destino}?text=${encodeURIComponent(texto)}`;
  }

  async function copiar() {
    try {
      await navigator.clipboard.writeText(texto);
      setAviso("Texto copiado.");
      setTimeout(() => setAviso(""), 2500);
    } catch {
      setErro("Seu navegador bloqueou a cópia. Selecione o texto e copie manualmente.");
    }
  }

  async function salvarNumero() {
    setErro("");
    try {
      await api.salvarZap(numero);
      setAviso("Número salvo para este cliente.");
      setTimeout(() => setAviso(""), 2500);
    } catch (e) {
      setErro(e.message);
    }
  }

  async function enviar() {
    setErro("");
    setEnviando(true);
    try {
      const r = await api.enviarZap(analiseId, { numero, texto });
      setAviso(r.detalhe || "Enviado.");
    } catch (e) {
      setErro(e.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section className="cartao">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 14, flexWrap: "wrap" }}>
        <div>
          <h2>Relatório para WhatsApp</h2>
          <p style={{ color: "var(--ink-2)", fontSize: 13.5, margin: "5px 0 0", maxWidth: "70ch" }}>
            O painel é para quem analisa. Isto é para {nomeCliente || "o cliente"} ler no celular:
            os números que importam, as conclusões e quem fechar esta semana.
          </p>
        </div>
        <label
          style={{ display: "flex", gap: 8, alignItems: "center", fontWeight: 500, margin: 0, whiteSpace: "nowrap" }}
        >
          <input
            type="checkbox"
            style={{ width: "auto" }}
            checked={completo}
            onChange={(e) => {
              setEditado(false);
              setCompleto(e.target.checked);
            }}
          />
          <span style={{ fontSize: 13 }}>versão completa</span>
        </label>
      </div>

      {carregando ? (
        <p style={{ color: "var(--ink-2)", marginTop: 14 }}>Montando o texto…</p>
      ) : (
        <>
          <textarea
            value={texto}
            onChange={(e) => {
              setTexto(e.target.value);
              setEditado(true);
            }}
            rows={16}
            aria-label="Texto do relatório"
            style={{
              marginTop: 14,
              fontFamily: "var(--fonte)",
              fontSize: 13.5,
              lineHeight: 1.55,
              resize: "vertical",
            }}
          />
          <p style={{ fontSize: 12, color: "var(--ink-muted)", margin: "7px 0 0" }}>
            {texto.length} caracteres · dá para editar antes de mandar — quem assina o relatório é
            você. No WhatsApp, <code>*texto*</code> vira negrito.
          </p>

          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", marginTop: 16 }}>
            <a className="botao verde" href={linkAtual()} target="_blank" rel="noopener noreferrer">
              Abrir no WhatsApp
            </a>
            <button onClick={copiar}>Copiar texto</button>
            {automatico && (
              <button className="primario" onClick={enviar} disabled={enviando || !numero}>
                {enviando ? "Enviando…" : "Enviar agora"}
              </button>
            )}
          </div>

          <div style={{ marginTop: 18, maxWidth: 380 }}>
            <label htmlFor="zap-numero">WhatsApp de {nomeCliente || "destino"}</label>
            <div style={{ display: "flex", gap: 8 }}>
              <input
                id="zap-numero"
                value={numero}
                onChange={(e) => setNumero(e.target.value)}
                placeholder="(83) 99853-9248"
              />
              {ehAdmin && <button onClick={salvarNumero}>Salvar</button>}
            </div>
            <p style={{ fontSize: 12, color: "var(--ink-muted)", margin: "6px 0 0" }}>
              {automatico
                ? "Envio automático está ligado neste servidor."
                : "Sem número, o botão abre o WhatsApp para você escolher o contato."}
            </p>
          </div>

          {aviso && (
            <div className="aviso ok" style={{ marginTop: 14 }}>
              {aviso}
            </div>
          )}
          {erro && (
            <div className="aviso erro" style={{ marginTop: 14 }} role="alert">
              {erro}
            </div>
          )}
        </>
      )}
    </section>
  );
}
