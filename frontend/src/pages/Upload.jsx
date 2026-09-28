import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api";

function Soltar({ id, titulo, ajuda, aceita, arquivos, onArquivos }) {
  const [sobre, setSobre] = useState(false);
  const entrada = useRef(null);

  function receber(lista) {
    onArquivos(Array.from(lista || []));
  }

  return (
    <div>
      <label htmlFor={id}>{titulo}</label>
      <div
        className={`arraste${sobre ? " sobre" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setSobre(true);
        }}
        onDragLeave={() => setSobre(false)}
        onDrop={(e) => {
          e.preventDefault();
          setSobre(false);
          receber(e.dataTransfer.files);
        }}
      >
        <input
          id={id}
          ref={entrada}
          type="file"
          multiple
          accept={aceita}
          onChange={(e) => receber(e.target.files)}
          style={{ display: "none" }}
        />
        <button type="button" onClick={() => entrada.current?.click()}>
          Escolher arquivo
        </button>
        <div style={{ fontSize: 13, marginTop: 8 }}>ou arraste aqui</div>
        <div className="nomes">
          {arquivos.length
            ? arquivos.map((a) => a.name).join(" · ")
            : ajuda}
        </div>
      </div>
    </div>
  );
}

export default function Upload() {
  const navegar = useNavigate();
  const [meta, setMeta] = useState([]);
  const [reunioes, setReunioes] = useState([]);
  const [mes, setMes] = useState("");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function enviar(e) {
    e.preventDefault();
    setErro("");
    if (!meta.length || !reunioes.length) {
      setErro("Envie os dois arquivos: o relatório da Meta e a planilha comercial.");
      return;
    }
    setEnviando(true);
    try {
      const analise = await api.enviarAnalise({
        arquivosMeta: meta,
        arquivosReunioes: reunioes,
        mesReferencia: mes || null,
      });
      navegar(`/analises/${analise.id}`);
    } catch (err) {
      setErro(err.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <>
      <div className="cabecalho-pagina">
        <div>
          <h1>Nova análise</h1>
          <p>
            Envie o relatório do Gerenciador de Anúncios e a planilha de assertividade. O sistema
            reconhece as colunas sozinho — não precisa reformatar nada.
          </p>
        </div>
      </div>

      <form onSubmit={enviar} className="cartao" style={{ maxWidth: 720 }}>
        <div className="grade" style={{ gap: 20 }}>
          <Soltar
            id="arquivos-meta"
            titulo="1. Relatório da Meta (tráfego pago)"
            ajuda="CSV ou XLSX exportado do Gerenciador de Anúncios"
            aceita=".csv,.xlsx"
            arquivos={meta}
            onArquivos={setMeta}
          />
          <Soltar
            id="arquivos-reunioes"
            titulo="2. Planilha de assertividade comercial"
            ajuda="XLSX ou CSV com cliente, etapa do funil e datas"
            aceita=".csv,.xlsx,.xlsm,.xls"
            arquivos={reunioes}
            onArquivos={setReunioes}
          />
          <div style={{ maxWidth: 240 }}>
            <label htmlFor="mes">Mês de referência (opcional)</label>
            <input id="mes" type="month" value={mes} onChange={(e) => setMes(e.target.value)} />
            <p style={{ fontSize: 12, color: "var(--ink-muted)", margin: "6px 0 0" }}>
              Em branco, o sistema descobre pelo conteúdo da planilha.
            </p>
          </div>
        </div>

        {erro && (
          <div className="aviso erro" style={{ margin: "18px 0 0" }} role="alert">
            {erro}
          </div>
        )}

        <div style={{ display: "flex", gap: 10, marginTop: 22, alignItems: "center" }}>
          <button className="primario" type="submit" disabled={enviando}>
            {enviando ? "Analisando…" : "Analisar"}
          </button>
          {enviando && (
            <span style={{ fontSize: 13, color: "var(--ink-2)" }}>
              Lendo as planilhas, cruzando os dados e montando a planilha final.
            </span>
          )}
        </div>
      </form>
    </>
  );
}
