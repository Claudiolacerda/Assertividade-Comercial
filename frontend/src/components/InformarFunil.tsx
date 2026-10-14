/* Leads e MQL informados na tela, sem refazer o upload.
 *
 * A planilha de reuniões não tem como dar nenhum dos dois: ela só lista quem
 * chegou a agendar. Até aqui a única porta era a aba Funil da planilha, o que
 * tinha duas consequências ruins: quem já tinha subido o mês precisava subir
 * de novo, e o resultado de uma análise fica gravado como JSON, então ela
 * continua mostrando o que o código daquele dia calculou. Reprocessar resolve
 * as duas coisas de uma vez, e guarda como versão nova em vez de por cima. */

import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api";
import { mensagemDoErro } from "../erros";

export default function InformarFunil({ analiseId, informado }) {
  const navegar = useNavigate();
  const [leads, setLeads] = useState(informado?.leads_recebidos ? String(informado.leads_recebidos) : "");
  const [mql, setMql] = useState(informado?.mql ? String(informado.mql) : "");
  const [rodando, setRodando] = useState(false);
  const [erro, setErro] = useState("");

  const numero = (texto: string) => {
    const n = Number(String(texto).replace(/[^\d]/g, ""));
    return Number.isFinite(n) && n > 0 ? n : undefined;
  };

  async function recalcular() {
    const corpo = { leads_recebidos: numero(leads), mql: numero(mql) };
    /* Campos vazios não são erro: recalcular sem informar nada ainda serve, e
       serve para o segundo caso de uso, que é pôr uma análise antiga no motor
       de hoje. O resultado dela está gravado como JSON desde o dia em que
       rodou, então correção nenhuma do sistema a alcança sem reprocessar. */
    setRodando(true);
    setErro("");
    try {
      const nova = await api.reprocessar(analiseId, corpo);
      /* Vai para a versão nova: a antiga continua no histórico, e deixar a
         tela na velha depois de recalcular faria parecer que nada mudou. */
      navegar(`/analises/${nova.id}`);
    } catch (e) {
      setErro(mensagemDoErro(e));
    } finally {
      setRodando(false);
    }
  }

  return (
    <div className="informar-funil">
      <div className="campos">
        <div>
          <label htmlFor="funil-leads">Leads recebidos no mês</label>
          <input
            id="funil-leads"
            inputMode="numeric"
            placeholder="ex.: 412"
            value={leads}
            onChange={(e) => setLeads(e.target.value)}
          />
          <p className="dica-campo">Todo contato que entrou, de qualquer origem.</p>
        </div>
        <div>
          <label htmlFor="funil-mql">MQL antes do agendamento (opcional)</label>
          <input
            id="funil-mql"
            inputMode="numeric"
            placeholder="deixe em branco"
            value={mql}
            onChange={(e) => setMql(e.target.value)}
          />
          {/* Opcional de verdade: se lead qualificado para você é quem marcou
              reunião, esse número ja esta contado nas linhas da planilha, e
              digitá-lo aqui seria repetir um dado que o sistema tem. */}
          <p className="dica-campo">
            Só se você qualifica o lead <em>antes</em> de marcar a reunião. Quem marcou reunião já
            é contado como lead qualificado.
          </p>
        </div>
        <button className="primario" onClick={recalcular} disabled={rodando}>
          {rodando ? "Recalculando…" : "Recalcular análise"}
        </button>
      </div>
      {erro && <p className="erro-inline">{erro}</p>}
      <p className="dica-campo">
        Recalcula sobre as mesmas planilhas e guarda como uma versão nova. A análise que você já
        enviou ao cliente continua no histórico. Em branco, ele só refaz a conta com a versão atual
        do sistema.
      </p>
    </div>
  );
}
