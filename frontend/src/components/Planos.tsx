/* Planos e contato.
 *
 * O preço está por cliente analisado porque é assim que a agência pensa o custo
 * dela. O botão de cada plano abre o WhatsApp com a mensagem já escrita — em
 * venda consultiva o primeiro passo é a conversa, não o cartão de crédito. */

import { IconeCheck } from "./Icones";

export const WHATSAPP = "5583998539248";
export const WHATSAPP_EXIBICAO = "(83) 99853-9248";

export function linkZap(mensagem) {
  return `https://wa.me/${WHATSAPP}?text=${encodeURIComponent(mensagem)}`;
}

export function IconeZap({ tamanho = 18 }) {
  return (
    <svg width={tamanho} height={tamanho} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M17.47 14.38c-.3-.15-1.75-.86-2.02-.96-.27-.1-.47-.15-.67.15-.2.3-.77.96-.94 1.16-.17.2-.35.22-.64.08-.3-.15-1.25-.46-2.38-1.47-.88-.78-1.47-1.75-1.65-2.05-.17-.3-.02-.46.13-.6.13-.13.3-.35.45-.52.15-.17.2-.3.3-.5.1-.2.05-.37-.02-.52-.08-.15-.67-1.61-.92-2.2-.24-.58-.49-.5-.67-.51h-.57c-.2 0-.52.07-.8.37-.27.3-1.04 1.02-1.04 2.48s1.07 2.88 1.22 3.08c.15.2 2.1 3.2 5.08 4.49.71.3 1.26.49 1.7.63.71.22 1.36.19 1.87.12.57-.09 1.75-.72 2-1.41.25-.69.25-1.28.17-1.41-.07-.13-.27-.2-.57-.35z" />
      <path d="M12.04 2C6.58 2 2.13 6.45 2.13 11.91c0 1.75.46 3.45 1.32 4.95L2 22l5.25-1.38a9.9 9.9 0 0 0 4.79 1.22h.01c5.46 0 9.91-4.45 9.91-9.91 0-2.65-1.03-5.14-2.9-7.01A9.85 9.85 0 0 0 12.04 2zm0 18.15h-.01a8.23 8.23 0 0 1-4.19-1.15l-.3-.18-3.12.82.83-3.04-.2-.31a8.2 8.2 0 0 1-1.26-4.38c0-4.54 3.7-8.24 8.25-8.24 2.2 0 4.27.86 5.83 2.42a8.19 8.19 0 0 1 2.41 5.83c0 4.54-3.7 8.23-8.24 8.23z" />
    </svg>
  );
}

const PLANOS = [
  {
    nome: "Empresa",
    publico: "Para quem analisa o próprio comercial",
    preco: "197",
    unitario: null,
    itens: [
      "1 empresa",
      "Análises ilimitadas, todo mês",
      "Diagnóstico automático completo",
      "Planilha em Excel com fórmulas vivas",
      "Histórico e evolução mês a mês",
    ],
    destaque: false,
    mensagem:
      "Olá! Vi o site da Neriah Data e quero saber mais sobre o plano Empresa (R$ 197/mês).",
  },
  {
    nome: "Agência Início",
    publico: "Gestor de tráfego começando a carteira",
    preco: "397",
    unitario: "R$ 79 por cliente",
    itens: [
      "Até 5 clientes",
      "Carteira com todos lado a lado",
      "Metas próprias por cliente",
      "Acesso para a sua equipe",
      "Tudo do plano Empresa",
    ],
    destaque: false,
    mensagem:
      "Olá! Vi o site da Neriah Data e quero saber mais sobre o plano Agência Início (R$ 397/mês).",
  },
  {
    nome: "Agência Crescimento",
    publico: "Agência com carteira formada",
    preco: "897",
    unitario: "R$ 60 por cliente",
    itens: [
      "Até 15 clientes",
      "Login para o cliente final ver o painel dele",
      "Comparativo e variação entre meses",
      "Suporte prioritário",
      "Tudo do Agência Início",
    ],
    destaque: true,
    mensagem:
      "Olá! Vi o site da Neriah Data e quero saber mais sobre o plano Agência Crescimento (R$ 897/mês).",
  },
  {
    nome: "Agência Escala",
    publico: "Operação com time comercial",
    preco: "1.497",
    unitario: "R$ 50 por cliente",
    itens: [
      "Até 40 clientes",
      "Implantação assistida das planilhas",
      "Treinamento do time",
      "Canal direto com quem desenvolve",
      "Tudo do Agência Crescimento",
    ],
    destaque: false,
    mensagem:
      "Olá! Vi o site da Neriah Data e quero saber mais sobre o plano Agência Escala (R$ 1.497/mês).",
  },
];

export default function Planos() {
  return (
    <section className="secao clara faixa" id="planos">
      <div className="limite">
        <div className="secao-topo">
          <h2>Custa menos que um cliente perdido</h2>
          <p>
            Preço por cliente analisado, porque é assim que a sua conta fecha. Sem fidelidade e sem
            taxa de setup. No plano anual, dois meses por nossa conta.
          </p>
        </div>

        <div className="planos">
          {PLANOS.map((p) => (
            <div className={`plano${p.destaque ? " destaque" : ""}`} key={p.nome}>
              {p.destaque && <span className="fita">mais escolhido</span>}
              <div className="nome">{p.nome}</div>
              <div className="publico">{p.publico}</div>

              <div className="preco">
                <span className="moeda">R$</span>
                <span className="valor">{p.preco}</span>
                <span className="periodo">/mês</span>
              </div>
              <div className="unitario">{p.unitario || " "}</div>

              <ul>
                {p.itens.map((i) => (
                  <li key={i}>
                    <span className="v"><IconeCheck tamanho={11} /></span>
                    <span>{i}</span>
                  </li>
                ))}
              </ul>

              <a
                className={`botao ${p.destaque ? "verde" : "claro"}`}
                href={linkZap(p.mensagem)}
                target="_blank"
                rel="noopener noreferrer"
              >
                Falar no WhatsApp
              </a>
            </div>
          ))}
        </div>

        <p className="nota-planos">
          Ainda em dúvida?{" "}
          <strong>A primeira análise é gratuita.</strong> Mande as suas duas planilhas e receba o
          diagnóstico da sua operação antes de decidir.{" "}
          <a href={linkZap("Olá! Quero fazer a primeira análise gratuita da Neriah Data.")} target="_blank" rel="noopener noreferrer">
            Começar pelo WhatsApp
          </a>
          .
        </p>
      </div>
    </section>
  );
}

/** Botão fixo de WhatsApp, presente em todo o site público. */
export function BotaoZap() {
  return (
    <a
      className="zap-flutuante"
      href={linkZap("Olá! Vim pelo site da Neriah Data e quero saber mais.")}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`Falar no WhatsApp ${WHATSAPP_EXIBICAO}`}
    >
      <IconeZap tamanho={20} />
      <span className="rotulo-zap">Falar no WhatsApp</span>
    </a>
  );
}
