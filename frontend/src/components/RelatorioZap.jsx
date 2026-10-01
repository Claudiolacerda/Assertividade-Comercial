/* Relatório para WhatsApp: prévia editável, copiar, abrir e enviar.
 *
 * Três caminhos de propósito. "Abrir no WhatsApp" funciona no primeiro dia, sem
 * credencial nenhuma — e é o que a maioria vai usar. O envio automático só
 * aparece quando o servidor está configurado, em vez de oferecer um botão que
 * falha. */

import { useEffect, useState } from "react";

import { api } from "../api";
import { useAuth } from "../auth";

/** `*texto*` é o negrito do WhatsApp. A prévia precisa mostrar o efeito, não a marcação. */
function negrito(linha) {
  return linha.split(/(\*[^*]+\*)/g).map((p, i) =>
    p.startsWith("*") && p.endsWith("*") && p.length > 2 ? (
      <strong key={i}>{p.slice(1, -1)}</strong>
    ) : (
      p
    ),
  );
}

const hora = () =>
  new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });

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
  const [editando, setEditando] = useState(false);

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
      <h2>Relatório para WhatsApp</h2>
      <p className="sub-cartao" style={{ maxWidth: "70ch" }}>
        O painel é para quem analisa. Isto é para {nomeCliente || "o cliente"} ler no celular: os
        números que importam, as conclusões e quem fechar esta semana.
      </p>

      {/* Destinatário ANTES da ação: antes, o botão de abrir o WhatsApp ficava
          acima do campo de telefone que ele usa. */}
      <div className="zap-destino">
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
        <p className="apoio-campo">
          {automatico
            ? "Envio automático está ligado neste servidor."
            : "Sem número, o botão abre o WhatsApp para você escolher o contato."}
        </p>
      </div>

      {carregando ? (
        <p style={{ color: "var(--ink-2)", marginTop: 14 }}>Montando o texto…</p>
      ) : (
        <>
          <div className="zap-controles">
            <div className="segmentado" role="group" aria-label="Tamanho do relatório">
              {[
                ["Resumo", false],
                ["Completo", true],
              ].map(([rotulo, valor]) => (
                <button
                  key={rotulo}
                  className={completo === valor ? "ativo" : ""}
                  aria-pressed={completo === valor}
                  onClick={() => {
                    setEditado(false);
                    setCompleto(valor);
                  }}
                >
                  {rotulo}
                </button>
              ))}
            </div>
            <button className="discreto" onClick={() => setEditando((v) => !v)}>
              {editando ? "Ver como vai chegar" : "Editar texto"}
            </button>
          </div>

          {editando ? (
            <textarea
              value={texto}
              onChange={(e) => {
                setTexto(e.target.value);
                setEditado(true);
              }}
              rows={18}
              aria-label="Texto do relatório"
              style={{
                marginTop: 12,
                fontFamily: "var(--fonte)",
                fontSize: 13.5,
                lineHeight: 1.55,
                resize: "vertical",
              }}
            />
          ) : (
            /* A prévia mostra o que o cliente vai ver, não a marcação crua. Sem
               rolagem interna: a mensagem inteira numa olhada é o que evita
               mandar a coisa errada. */
            <div className="palco-previa">
              <div className="bolha-zap">
                {texto.split("\n").map((linha, i) =>
                  linha.trim() === "" ? (
                    <div key={i} style={{ height: 7 }} />
                  ) : (
                    <div key={i}>{negrito(linha)}</div>
                  ),
                )}
                <div className="hora">{hora()}</div>
              </div>
            </div>
          )}

          <p style={{ fontSize: 12, color: "var(--ink-muted)", margin: "9px 0 0" }}>
            {texto.length} caracteres · quem assina o relatório é você.
            {!editando && " O que está em negrito aqui chega em negrito lá."}
          </p>

          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", marginTop: 16 }}>
            <a
              className="botao verde"
              href={linkAtual()}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => {
                const destino = (numero || "").replace(/\D/g, "");
                if (!destino) return; // sem número o WhatsApp abre a lista de contatos
                if (!window.confirm(`Abrir conversa com ${numero} e colar o relatório?`)) {
                  e.preventDefault();
                }
              }}
            >
              Abrir no WhatsApp
            </a>
            <button onClick={copiar}>Copiar texto</button>
            {automatico && (
              <button
                className="primario"
                onClick={() => {
                  if (window.confirm(`Enviar o relatório agora para ${numero}?`)) enviar();
                }}
                disabled={enviando || !numero}
              >
                {enviando ? "Enviando…" : "Enviar agora"}
              </button>
            )}
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
