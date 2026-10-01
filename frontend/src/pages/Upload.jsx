import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api";
import { IconeCheck } from "../components/Icones";

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
        className={`arraste${sobre ? " sobre" : ""}${arquivos.length ? " preenchido" : ""}`}
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
        {arquivos.length > 0 ? (
          <>
            <div className="anexo-ok">
              <IconeCheck tamanho={14} />
              {arquivos.length === 1 ? "Arquivo anexado" : `${arquivos.length} arquivos anexados`}
            </div>
            <div className="anexo-nomes">
              {arquivos.map((a) => (
                <div key={a.name}>
                  {a.name} <span>{(a.size / 1024).toFixed(0)} KB</span>
                </div>
              ))}
            </div>
            <button type="button" className="discreto" onClick={() => entrada.current?.click()}>
              Trocar arquivo
            </button>
          </>
        ) : (
          <>
            <button type="button" onClick={() => entrada.current?.click()}>
              Escolher arquivo
            </button>
            <div style={{ fontSize: 13, marginTop: 8 }}>ou arraste aqui</div>
            <div className="nomes">{ajuda}</div>
          </>
        )}
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
            onArquivos={(a) => { setMeta(a); setErro(""); }}
          />
          <Soltar
            id="arquivos-reunioes"
            titulo="2. Planilha de assertividade comercial"
            ajuda="XLSX ou CSV com cliente, etapa do funil e datas"
            aceita=".csv,.xlsx,.xlsm,.xls"
            arquivos={reunioes}
            onArquivos={(a) => { setReunioes(a); setErro(""); }}
          />
          <div className="aviso" style={{ borderLeftColor: "var(--verde)" }}>
            Não tem uma planilha organizada?{" "}
            <button
              type="button"
              className="discreto"
              onClick={() => api.baixarModelo()}
              style={{ color: "var(--verde)", fontWeight: 650, padding: 0 }}
            >
              Baixe a planilha-modelo
            </button>{" "}
            — ela já vem com todas as colunas que liberam ROAS, CAC por campanha e ciclo de venda.
          </div>

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
