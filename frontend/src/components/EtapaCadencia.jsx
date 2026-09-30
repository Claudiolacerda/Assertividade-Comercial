/* O nó do canvas: uma etapa da cadência.
 *
 * Cada canal tem cor e ícone próprios — a leitura do fluxo tem que funcionar de
 * relance, sem ler texto. As cores aqui são de identidade de canal, não de série
 * de gráfico: não competem com a paleta dos dashboards. */

import { Handle, Position } from "@xyflow/react";

export const CANAIS = {
  whatsapp: { rotulo: "WhatsApp", icone: "💬", cor: "#25d366" },
  ligacao: { rotulo: "Ligação", icone: "📞", cor: "#2a78d6" },
  email: { rotulo: "E-mail", icone: "✉️", cor: "#7c5cd6" },
  reuniao: { rotulo: "Reunião", icone: "🤝", cor: "#099938" },
  espera: { rotulo: "Espera", icone: "⏳", cor: "#8b9995" },
  condicao: { rotulo: "Decisão", icone: "🔀", cor: "#e08a1e" },
  nota: { rotulo: "Nota", icone: "📌", cor: "#d0567f" },
};

export default function EtapaCadencia({ data, selected }) {
  const canal = CANAIS[data.canal] || CANAIS.nota;
  return (
    <div className={`no-etapa${selected ? " selecionado" : ""}`} style={{ "--cor-canal": canal.cor }}>
      <Handle type="target" position={Position.Left} />

      <div className="no-topo">
        <span className="no-canal">
          <span aria-hidden="true">{canal.icone}</span> {canal.rotulo}
        </span>
        <span className="no-dia">D+{data.dia ?? 0}</span>
      </div>

      <div className="no-titulo">{data.titulo || "Sem título"}</div>
      {data.texto && <div className="no-texto">{data.texto}</div>}

      <Handle type="source" position={Position.Right} />
    </div>
  );
}
