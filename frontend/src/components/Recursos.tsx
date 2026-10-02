/* As duas entregas que fecham o ciclo: o relatório que o cliente lê e a cadência
 * que a equipe executa. Mostradas com conteúdo real — o mesmo texto e o mesmo
 * fluxo que a análise de setembro gerou. */

import { CANAIS } from "./EtapaCadencia";
import { IconeCheck } from "./Icones";

const MENSAGEM = [
  { t: "*Contabilidade Horizonte · setembro/2026*", forte: true },
  { t: "" },
  { t: "• Investido em anúncio: *R$ 3.651,02*" },
  { t: "• Leads gerados: *81*" },
  { t: "• Reuniões realizadas: *35*" },
  { t: "• Clientes fechados: *9*" },
  { t: "" },
  { t: "• Assertividade: *25,7%*  ✅" },
  { t: "• Custo por cliente: *R$ 405,67*  ✅" },
  { t: "" },
  { t: "*O que os números estão dizendo*", forte: true },
  { t: "⚠️ 11 oportunidades em aberto há mais de 15 dias." },
  { t: "" },
  { t: "*Para fechar esta semana* (7)", forte: true },
  { t: "Nilton, Arnaldo, Josefina, Jonas, Lauro…" },
];

const ETAPAS = [
  { chave: "nota", dia: 0, titulo: "7 clientes quentes", texto: "Nilton, Arnaldo, Josefina, Jonas…" },
  { chave: "ligacao", dia: 0, titulo: "Ligar para os quentes", texto: "Objetivo: marcar a assinatura." },
  { chave: "whatsapp", dia: 1, titulo: "Reancorar valor", texto: "9 clientes travaram em preço." },
  { chave: "reuniao", dia: 4, titulo: "Call com os dois", texto: "6 dependem de um decisor oculto." },
];

function Bolha() {
  return (
    <div className="bolha-zap">
      {MENSAGEM.map((l, i) =>
        l.t === "" ? (
          <div key={i} style={{ height: 7 }} />
        ) : (
          <div key={i} className={l.forte ? "forte" : ""}>
            {l.t.replace(/\*/g, "")}
          </div>
        ),
      )}
      <div className="hora">12:04 ✓✓</div>
    </div>
  );
}

export default function Recursos() {
  return (
    <>
      {/* -------- relatório no WhatsApp -------- */}
      <section className="secao clara faixa" id="whatsapp">
        <div className="limite duas-colunas">
          <div>
            <div className="secao-topo" style={{ marginBottom: 22 }}>
              <h2>O seu cliente não abre dashboard. Ele abre o WhatsApp.</h2>
              <p>
                Todo mês a análise vira uma mensagem que cabe numa tela: os números que o dono do
                negócio cobra, o que mudou desde o mês passado e quem fechar esta semana, pelo nome.
              </p>
            </div>
            <ul className="lista-check">
              <li>
                <span className="v"><IconeCheck tamanho={11} /></span>
                <span>
                  <b>Editável antes de mandar.</b> Quem assina o relatório é você, não o gerador.
                </span>
              </li>
              <li>
                <span className="v"><IconeCheck tamanho={11} /></span>
                <span>
                  <b>Funciona no primeiro dia.</b> Abre o WhatsApp com a mensagem pronta, sem
                  precisar configurar nada.
                </span>
              </li>
              <li>
                <span className="v"><IconeCheck tamanho={11} /></span>
                <span>
                  <b>Ou automático.</b> Conecte a sua Evolution API ou a API oficial da Meta e o
                  envio sai sozinho.
                </span>
              </li>
              <li>
                <span className="v"><IconeCheck tamanho={11} /></span>
                <span>
                  <b>Sem recado técnico.</b> O que é problema de planilha fica no painel, não vai
                  para o cliente.
                </span>
              </li>
            </ul>
          </div>

          <div className="palco-zap">
            <Bolha />
          </div>
        </div>
      </section>

      {/* -------- cadência -------- */}
      <section className="secao alterna faixa" id="cadencia">
        <div className="limite">
          <div className="secao-topo">
            <h2>Descobrir onde trava é metade. A outra é o que fazer na segunda.</h2>
            <p>
              Um canvas para desenhar o follow-up da equipe: arrastar, ligar, editar. A diferença
              para um quadro branco é o botão de sugerir: o fluxo nasce das objeções que a sua
              planilha registrou, não de um modelo que serve para qualquer negócio.
            </p>
          </div>

          <div className="palco-fluxo">
            {ETAPAS.map((e, i) => (
              <div
                key={e.titulo}
                className="mini-etapa"
                style={{ "--cor-canal": CANAIS[e.chave].cor, "--cor-canal-texto": CANAIS[e.chave].corTexto }}
              >
                <div className="mini-topo">
                  <span className="mini-canal">
                    {(() => {
                      const I = CANAIS[e.chave].Icone;
                      return <I tamanho={13} />;
                    })()}
                    {CANAIS[e.chave].rotulo}
                  </span>
                  <span className="mini-dia">D+{e.dia}</span>
                </div>
                <div className="mini-titulo">{e.titulo}</div>
                <div className="mini-texto">{e.texto}</div>
                {i < ETAPAS.length - 1 && <span className="mini-seta" aria-hidden="true" />}
              </div>
            ))}
          </div>

          <p className="nota-fluxo">
            Este fluxo não foi inventado para a imagem: saiu da análise de setembro. O “9 clientes
            travaram em preço” e o “6 dependem de um decisor oculto” vieram das observações que a
            equipe escreveu na própria planilha.
          </p>
        </div>
      </section>
    </>
  );
}
