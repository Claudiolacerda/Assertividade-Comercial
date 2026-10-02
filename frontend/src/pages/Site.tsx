/* Página pública da Neriah Data.
 *
 * Os números e as frases de diagnóstico mostrados aqui são de uma análise real
 * (setembro/2026, o caso que originou o produto) — nada é ilustrativo. É o que
 * torna a demonstração convincente: quem chega vê exatamente o tipo de conclusão
 * que vai receber. */

import { useState } from "react";
import { Link } from "react-router-dom";

import Marca from "../components/Marca";
import Planos, { BotaoZap, IconeZap, WHATSAPP_EXIBICAO, linkZap } from "../components/Planos";
import Recursos from "../components/Recursos";
import {
  ICONES_NIVEL,
  IconeAtencao,
  IconeCheck,
  IconeDiagonal,
  IconeQueda,
  IconeSubida,
} from "../components/Icones";

const FUNIL = [
  { etapa: "Cliques no link", valor: 516, pct: 100 },
  { etapa: "Leads e conversas", valor: 81, pct: 15.7 },
  { etapa: "Reuniões agendadas", valor: 36, pct: 7.0 },
  { etapa: "Reuniões realizadas", valor: 35, pct: 6.8 },
  { etapa: "Clientes fechados", valor: 9, pct: 1.7 },
];

const DIAGNOSTICOS = [
  {
    nivel: "atencao",
    tx: (
      <>
        3 clientes marcados como <b>Fechado</b> têm observação de quem ainda vai decidir. Se não
        fecharam, a assertividade real é <b>17,1%</b> e não 25,7%.
      </>
    ),
  },
  {
    nivel: "critico",
    tx: (
      <>
        4 dos 9 fechamentos têm marcação de parceiro no nome. Se vieram de indicação, o{" "}
        <b>CAC real do anúncio é R$ 730,20</b> — não R$ 405,67.
      </>
    ),
  },
  {
    nivel: "quente",
    tx: (
      <>
        <b>7 clientes quentes</b> para fechar agora: Nilton, Arnaldo, Josefina, Jonas, Lauro, Romildo,
        Nelson.
      </>
    ),
  },
  {
    nivel: "atencao",
    tx: (
      <>
        11 oportunidades em aberto há mais de 15 dias. Vale follow-up ou dar como perdida.
      </>
    ),
  },
];

const CONCLUSOES = [
  {
    marcador: "Atribuição",
    texto: (
      <>
        “4 dos 9 fechamentos têm a marcação ‘Parceiro’ no nome. Hoje contam como tráfego pago (CAC R$
        405,67). Se vieram de indicação, o <b>CAC real do anúncio é R$ 730,20</b>.”
      </>
    ),
  },
  {
    marcador: "Confiabilidade do número",
    texto: (
      <>
        “3 clientes marcados como Fechado têm observação de quem ainda vai decidir. Se não fecharam,
        a <b>assertividade real é 17,1%</b> e não 25,7%.”
      </>
    ),
  },
  {
    marcador: "Desperdício",
    texto: (
      <>
        “A campanha X investiu R$ 1.240,00, gerou 6 reuniões e <b>nenhum fechamento</b>.”
      </>
    ),
  },
  {
    marcador: "Objeções",
    texto: (
      <>
        “Sinais mais frequentes nas observações: <b>preço/orçamento (9 clientes)</b>; promessa de
        fechamento (9); decide com cônjuge/sócio (6).”
      </>
    ),
  },
  {
    marcador: "Risco escondido",
    texto: (
      <>
        “Nenhuma reunião está marcada como perdida. 22 estão só como ‘Reunião feita’.{" "}
        <b>Sem registrar perdas, a assertividade real fica escondida.</b>”
      </>
    ),
  },
  {
    marcador: "Pipeline",
    texto: (
      <>
        “<b>7 clientes quentes</b> para fechar agora” — nominalmente, com o que cada um disse na
        última conversa.
      </>
    ),
  },
];

export default function Site() {
  const [menuAberto, setMenuAberto] = useState(false);
  return (
    <div className="site">
      {/* ---------------- topo + hero ---------------- */}
      <div className="escuro sobre-escuro">
        <header className="topo faixa">
          <div className="limite">
            <Marca tamanho={19} />
            {/* Sem isto, no celular "Planos" e "Como funciona" eram inalcançáveis:
                o único caminho até o preço era rolar a página inteira. */}
            <button
              className="menu-movel"
              aria-expanded={menuAberto}
              aria-controls="nav-site"
              onClick={() => setMenuAberto((v) => !v)}
            >
              <span className="barrinhas" aria-hidden="true">
                <span />
                <span />
                <span />
              </span>
              Menu
            </button>
            <nav id="nav-site" className={menuAberto ? "aberto" : ""} onClick={() => setMenuAberto(false)}>
              <a href="#como">
                Como funciona
              </a>
              <a href="#conclusoes">
                O que ele conclui
              </a>
              <a href="#planilha">
                Sua planilha
              </a>
              <a href="#cadencia">
                Cadência
              </a>
              <a href="#planos">
                Planos
              </a>
              <Link className="botao verde" to="/entrar" style={{ padding: "9px 18px", fontSize: 14 }}>
                Entrar
              </Link>
            </nav>
          </div>
        </header>

        <section className="hero faixa">
          <div className="limite">
            <span className="etiqueta">
              <span className="ponto" />
              Análise · Relatório no WhatsApp · Cadência
            </span>

            <h1>
              Luz sobre o que o seu tráfego <span className="luz">realmente vendeu</span>
            </h1>

            <p className="chamada">
              Você sabe quanto gastou em anúncio. Sabe quantas reuniões aconteceram. O que ninguém
              te diz é quanto custou <em>cada cliente que assinou</em> — e o que fazer na segunda-feira.
              A Neriah cruza as duas planilhas, manda o resultado no WhatsApp do cliente e desenha a
              cadência para destravar quem ficou no meio do caminho.
            </p>

            <div className="acoes">
              <Link className="botao verde" to="/entrar">
                Analisar minhas planilhas →
              </Link>
              <a className="botao vazado" href="#como">
                Ver como funciona
              </a>
            </div>

            {/* painel demonstrativo — dados reais de uma análise */}
            <div className="moldura">
              {/* O facho: a luz que revela o dado, literal. Varre o painel uma
                  vez; cada elemento acende quando ele passa por cima. */}
              <span className="facho" aria-hidden="true" />

              <div className="barra-janela">
                <span className="bolinha" />
                <span className="bolinha" />
                <span className="bolinha" />
                <span className="caminho">neriah.data / análise / setembro 2026</span>
              </div>

              <div className="demo">
                <div className="demo-tiles">
                  <div className="demo-tile forte" style={{ "--atraso": "475ms" }}>
                    <div className="r">ASSERTIVIDADE</div>
                    <div className="v">25,7%</div>
                    <div className="d">9 fechados ÷ 35 reuniões</div>
                  </div>
                  <div className="demo-tile" style={{ "--atraso": "731ms" }}>
                    <div className="r">CAC</div>
                    <div className="v">R$ 405,67</div>
                    <div className="d">meta máx. R$ 800,00</div>
                  </div>
                  <div className="demo-tile" style={{ "--atraso": "987ms" }}>
                    <div className="r">CUSTO POR LEAD</div>
                    <div className="v">R$ 45,07</div>
                    <div className="d">acima da meta</div>
                  </div>
                  <div className="demo-tile" style={{ "--atraso": "1244ms" }}>
                    <div className="r">INVESTIMENTO</div>
                    <div className="v">R$ 3.651</div>
                    <div className="d">81 leads no período</div>
                  </div>
                </div>

                <div className="demo-corpo">
                  <div className="demo-bloco">
                    <h4>Funil do anúncio ao cliente</h4>
                    {FUNIL.map((f, i) => (
                      <div
                        className="barra-linha"
                        key={f.etapa}
                        style={{ "--atraso": `${590 + i * 26}ms` }}
                      >
                        <span className="et">{f.etapa}</span>
                        <span className="tr">
                          <span className="pr" style={{ width: `${Math.max(f.pct, 2.5)}%` }} />
                        </span>
                        <span className="nm">{f.valor}</span>
                      </div>
                    ))}
                  </div>

                  <div className="demo-bloco">
                    <h4>O que os números estão dizendo</h4>
                    {DIAGNOSTICOS.map((d, i) => (
                      <div className="demo-diag" key={i} style={{ "--atraso": `${1105 + i * 30}ms` }}>
                        <span className={`ic n-${d.nivel}`}>
                          {(() => {
                            const I = ICONES_NIVEL[d.nivel];
                            return <I tamanho={13} />;
                          })()}
                        </span>
                        <span className="tx">{d.tx}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <div className="tira faixa">
          <div className="limite">
            <div>
              <div className="n">24</div>
              <div className="l">campos reconhecidos sozinho, com qualquer nome de coluna</div>
            </div>
            <div>
              <div className="n">37</div>
              <div className="l">indicadores calculados por análise</div>
            </div>
            <div>
              <div className="n">~20</div>
              <div className="l">tipos de conclusão automática</div>
            </div>
            <div>
              <div className="n">2</div>
              <div className="l">colunas é tudo que sua planilha precisa ter</div>
            </div>
          </div>
        </div>
      </div>

      {/* ---------------- como funciona ---------------- */}
      <section className="secao clara faixa" id="como">
        <div className="limite">
          <div className="secao-topo">
            <h2>Três passos. Nenhuma planilha reformatada.</h2>
            <p>
              A maior parte das ferramentas exige que você arrume a planilha antes. A Neriah faz o
              contrário: ela se adapta ao arquivo que a sua equipe já preenche todo dia.
            </p>
          </div>

          <div className="passos">
            <div className="passo">
              <div className="num">1</div>
              <h3>Suba os dois arquivos</h3>
              <p>
                O relatório do Gerenciador de Anúncios e a sua planilha comercial, do jeito que
                estão. CSV ou Excel, em português ou inglês, com blocos por semana, datas pela
                metade, valores em “R$ 1.500,00”.
              </p>
            </div>
            <div className="passo">
              <div className="num">2</div>
              <h3>A Neriah reconhece e cruza</h3>
              <p>
                Ela acha o cabeçalho dentro do arquivo e entende que “Quem fez” é o responsável e
                “Etapa do Funil” é o status. Depois liga o investimento da Meta às reuniões, por
                campanha.
              </p>
            </div>
            <div className="passo">
              <div className="num">3</div>
              <h3>Recebe conclusões, não só gráficos</h3>
              <p>
                Painel com KPIs, funil e evolução mês a mês, a leitura crítica em texto e o Excel com
                fórmulas vivas. O resumo vai pronto para o WhatsApp do cliente — e o Neriah ainda
                desenha a cadência para destravar quem não fechou.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ---------------- conclusões ---------------- */}
      <section className="secao alterna faixa" id="conclusoes">
        <div className="limite">
          <div className="secao-topo">
            <h2>Ela chega às próprias conclusões — inclusive as incômodas</h2>
            <p>
              Um dashboard comum mostra o número. A Neriah avisa quando o número não merece
              confiança. Todas as frases abaixo saíram de análises reais, exatamente como aparecem
              na tela.
            </p>
          </div>

          <div className="cartoes">
            {CONCLUSOES.map((c) => (
              <div className="cartao-rec" key={c.marcador}>
                <div className="marcador">{c.marcador}</div>
                <p>{c.texto}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ---------------- WhatsApp e cadência ---------------- */}
      <Recursos />

      {/* ---------------- sua planilha ---------------- */}
      <section className="secao clara faixa" id="planilha">
        <div className="limite duas-colunas">
          <div>
            <div className="secao-topo" style={{ marginBottom: 26 }}>
              <h2>O mínimo é duas colunas. O resto vai destravando.</h2>
              <p>
                Nada de projeto de implantação. Se a sua planilha tem cliente e etapa, você já tem
                análise hoje — e a própria Neriah te diz o que falta para liberar o resto.
              </p>
            </div>
            <ul className="lista-check">
              <li>
                <span className="v"><IconeCheck tamanho={11} /></span>
                <span>
                  <b>Cliente + etapa do funil</b> — o mínimo. Já entrega assertividade, funil, CAC e
                  pipeline.
                </span>
              </li>
              <li>
                <span className="v"><IconeCheck tamanho={11} /></span>
                <span>
                  <b>Valor do contrato</b> — libera receita, ticket médio, ROAS e ROI.
                </span>
              </li>
              <li>
                <span className="v"><IconeCheck tamanho={11} /></span>
                <span>
                  <b>Campanha</b> — mostra qual anúncio realmente vende, com CAC por campanha.
                </span>
              </li>
              <li>
                <span className="v"><IconeCheck tamanho={11} /></span>
                <span>
                  <b>Quem fez</b> — compara assertividade entre vendedores.
                </span>
              </li>
              <li>
                <span className="v"><IconeCheck tamanho={11} /></span>
                <span>
                  <b>Motivo da perda</b> — win rate confiável e o que mais trava a venda.
                </span>
              </li>
            </ul>
            <div style={{ marginTop: 26 }}>
              <a className="botao verde" href="/api/modelo/planilha-comercial.xlsx">
                Baixar a planilha-modelo
              </a>
              <p style={{ fontSize: 12.5, color: "var(--ink-muted)", margin: "10px 0 0" }}>
                Excel pronto, com a lista de etapas e uma aba explicando o que cada coluna destrava.
              </p>
            </div>
          </div>

          <div>
            <div className="cartao" style={{ padding: 22 }}>
              <div className="marcador" style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", color: "var(--ink-muted)", marginBottom: 14 }}>
                Auditoria automática dos dados
              </div>
              <p style={{ margin: "0 0 16px", fontSize: 14, color: "var(--ink-2)", lineHeight: 1.6 }}>
                Antes de calcular, a Neriah confere linha a linha e mostra o que pode estar
                distorcendo o resultado:
              </p>
              {[
                "Status que ela não reconheceu",
                "Data de agendamento depois da reunião",
                "Mesmo cliente duplicado na mesma data",
                "Fechamento sem valor preenchido",
                "Fechado cuja observação diz que ainda vai decidir",
                "Data fora do mês analisado",
              ].map((t) => (
                <div
                  key={t}
                  style={{
                    display: "flex",
                    gap: 10,
                    alignItems: "center",
                    padding: "9px 0",
                    borderBottom: "1px solid var(--grid)",
                    fontSize: 13.5,
                  }}
                >
                  <span style={{ color: "var(--atencao-texto)", display: "inline-flex" }}><IconeAtencao tamanho={13} /></span>
                  <span style={{ color: "var(--ink)" }}>{t}</span>
                </div>
              ))}
              <p style={{ margin: "16px 0 0", fontSize: 12.5, color: "var(--ink-muted)" }}>
                Cada apontamento vem com o nome do cliente e a linha, para a correção ser feita na
                origem.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ---------------- para agências ---------------- */}
      <section className="secao alterna faixa">
        <div className="limite">
          <div className="secao-topo">
            <h2>Pare de entregar print do Gerenciador</h2>
            <p>
              O cliente não compra CPM. Ele compra cliente novo. A Neriah traduz o seu trabalho na
              única língua que o dono do negócio entende: quanto entrou e quanto custou.
            </p>
          </div>
          <div className="passos">
            <div className="passo">
              <div className="num"><IconeSubida /></div>
              <h3>Cada cliente no seu espaço</h3>
              <p>
                Login próprio e banco isolado por empresa. Um cliente nunca alcança o dado do outro
                — e você mostra isso na reunião de fechamento.
              </p>
            </div>
            <div className="passo">
              <div className="num"><IconeDiagonal /></div>
              <h3>Histórico mês a mês</h3>
              <p>
                Assertividade, CAC e custo por lead em série temporal. É o gráfico que renova
                contrato: a prova de que o trabalho está melhorando o resultado.
              </p>
            </div>
            <div className="passo">
              <div className="num"><IconeQueda /></div>
              <h3>Excel com fórmula viva</h3>
              <p>
                O relatório baixado não tem número congelado: o cliente muda a meta na célula e a
                planilha inteira recalcula sozinha.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ---------------- planos ---------------- */}
      <Planos />

      {/* ---------------- chamada final ---------------- */}
      <div className="escuro sobre-escuro">
        <section className="chamada-final faixa">
          <div className="limite">
            <h2>
              O dado já está na sua planilha.
              <br />
              Falta <span style={{ color: "var(--verde-vivo)" }}>luz</span> sobre ele.
            </h2>
            <p>
              Suba o relatório da Meta e a planilha comercial do último mês. Em segundos você vê o
              CAC real, a assertividade de verdade e o que está travando cada venda.
            </p>
            <div className="acoes">
              <Link className="botao verde" to="/entrar">
                Começar agora →
              </Link>
              <a
                className="botao vazado"
                href={linkZap("Olá! Vim pelo site da Neriah Data e quero conversar sobre os planos.")}
                target="_blank"
                rel="noopener noreferrer"
              >
                <IconeZap /> Falar no WhatsApp
              </a>
            </div>
          </div>
        </section>

        <footer className="rodape faixa">
          <div className="limite">
            <Marca tamanho={15} />
            <a
              href={linkZap("Olá! Vim pelo site da Neriah Data.")}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "var(--verde-vivo)", textDecoration: "none", display: "inline-flex", gap: 7, alignItems: "center" }}
            >
              <IconeZap tamanho={16} /> {WHATSAPP_EXIBICAO}
            </a>
            <span>Neriah · luz — inteligência de dados para quem vive de vender.</span>
          </div>
        </footer>
      </div>

      <BotaoZap />
    </div>
  );
}
