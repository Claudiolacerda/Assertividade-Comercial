/* O nó do canvas: uma etapa da cadência.
 *
 * Cada canal tem cor e ícone próprios — a leitura do fluxo tem que funcionar de
 * relance, sem ler texto. As cores aqui são de identidade de canal, não de série
 * de gráfico: não competem com a paleta dos dashboards. */

import { Handle, Position } from "@xyflow/react";
import {
  IconeDecisao,
  IconeEmail,
  IconeEspera,
  IconeLigacao,
  IconeNota,
  IconeReuniao,
  IconeWhatsApp,
} from "./Icones";

/* Cada canal tem DUAS cores: `cor` preenche a barra de identidade e a alça de
 * conexão, onde basta 3:1 por ser elemento não textual; `corTexto` escreve o
 * rótulo, onde são exigidos 4,5:1 sobre superfície clara. O verde do WhatsApp
 * puro, por exemplo, fica em 1,98:1 como letra — bonito na barra, ilegível
 * escrito. */
export const CANAIS = {
  whatsapp: { rotulo: "WhatsApp", Icone: IconeWhatsApp, cor: "#25d366", corTexto: "#16803e" },
  ligacao: { rotulo: "Ligação", Icone: IconeLigacao, cor: "#2a78d6", corTexto: "#266fc7" },
  email: { rotulo: "E-mail", Icone: IconeEmail, cor: "#7c5cd6", corTexto: "#7959d5" },
  reuniao: { rotulo: "Reunião", Icone: IconeReuniao, cor: "#099938", corTexto: "#08812f" },
  espera: { rotulo: "Espera", Icone: IconeEspera, cor: "#8b9995", corTexto: "#64726e" },
  condicao: { rotulo: "Decisão", Icone: IconeDecisao, cor: "#e08a1e", corTexto: "#9e6215" },
  nota: { rotulo: "Nota", Icone: IconeNota, cor: "#d0567f", corTexto: "#c73768" },
};

export default function EtapaCadencia({ data, selected }) {
  const canal = CANAIS[data.canal] || CANAIS.nota;
  return (
    <div
      className={`no-etapa${selected ? " selecionado" : ""}`}
      style={{ "--cor-canal": canal.cor, "--cor-canal-texto": canal.corTexto }}
    >
      <Handle type="target" position={Position.Left} />

      <div className="no-topo">
        <span className="no-canal">
          <canal.Icone tamanho={13} /> {canal.rotulo}
        </span>
        <span className="no-dia">D+{data.dia ?? 0}</span>
      </div>

      <div className="no-titulo">{data.titulo || "Sem título"}</div>
      {data.texto && <div className="no-texto">{data.texto}</div>}

      <Handle type="source" position={Position.Right} />
    </div>
  );
}
