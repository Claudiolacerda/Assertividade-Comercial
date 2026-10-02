/* A nota do mês.
 *
 * Trinta e sete KPIs não respondem "o mês foi bom?". Esta tela responde, e
 * depois mostra a conta: um número grande, os três pilares que o formam e a
 * lista do que custou ponto, em ordem.
 *
 * Duas regras de desenho que o resto do arquivo segue:
 *
 * 1. Nada aqui é dito só por cor. Faixa, atingimento e pilar fora do cálculo
 *    aparecem em texto; a cor só reforça. Ninguém decide corte de verba por um
 *    tom de verde que não enxerga.
 *
 * 2. Indicador fora do cálculo não é escondido. É justamente onde a operação
 *    não é medida, e esconder deixaria o cliente achando que o Score cobre
 *    mais do que cobre. Ele aparece com o motivo, em voz mais baixa.
 */

import { useState } from "react";

import type {
  CampanhaJet,
  FaixaJet,
  Jet as TipoJet,
  Jev as TipoJev,
  MelhoriaJet,
  PilarJet,
} from "../tipos";

import { formatar } from "./Charts";
import { IconeAtencao, IconeCheck, IconeOk } from "./Icones";

const ROTULO_FAIXA: Record<FaixaJet, string> = {
  excelente: "Excelente",
  bom: "Bom",
  atencao: "Atenção",
  critico: "Crítico",
};

/** O anel que desenha o Score. SVG em vez de gradiente cônico porque precisa
 *  ter rótulo acessível e animar o traço sem repintar o fundo inteiro. */
function Anel({ score, faixa }: { score: number; faixa: FaixaJet }) {
  const r = 52;
  const volta = 2 * Math.PI * r;
  const preenchido = (Math.max(0, Math.min(100, score)) / 100) * volta;
  return (
    <svg className="jet-anel" viewBox="0 0 128 128" role="img"
         aria-label={`Score ${score.toFixed(0)} de 100: ${ROTULO_FAIXA[faixa]}`}>
      <circle cx="64" cy="64" r={r} className="trilho" />
      <circle cx="64" cy="64" r={r} className={`arco ${faixa}`}
              strokeDasharray={`${preenchido} ${volta}`} />
      <text x="64" y="62" className="valor">{score.toFixed(0)}</text>
      <text x="64" y="82" className="base">de 100</text>
    </svg>
  );
}

function Pilar({ pilar }: { pilar: PilarJet }) {
  if (!pilar.pontuado) {
    return (
      <div className="jet-pilar fora">
        <span className="nome">{pilar.rotulo}</span>
        <span className="nota">não pontuado</span>
        <p className="porque">Nenhum indicador deste pilar pôde ser medido neste mês.</p>
      </div>
    );
  }
  const nota = pilar.nota ?? 0;
  return (
    <div className="jet-pilar">
      <span className="nome">{pilar.rotulo}</span>
      <span className="nota">{nota.toFixed(0)}<small>/100</small></span>
      <div className="barra" role="img" aria-label={`${pilar.rotulo}: ${nota.toFixed(0)} de 100`}>
        <span style={{ width: `${Math.max(2, nota)}%` }} />
      </div>
      <p className="porque">
        peso {pilar.peso_efetivo?.toFixed(0) ?? pilar.peso}% do Score ·{" "}
        {pilar.indicadores_dentro} {pilar.indicadores_dentro === 1 ? "indicador" : "indicadores"}
      </p>
    </div>
  );
}

function Melhoria({ item }: { item: MelhoriaJet }) {
  const ehRegistro = item.tipo === "registro";
  return (
    <li className={`jet-melhoria${ehRegistro ? " registro" : ""}`}>
      <span className="selo-custo">
        {ehRegistro ? "registro" : `−${item.custo.toFixed(1)} pts`}
      </span>
      <div className="corpo">
        <strong>{item.titulo}</strong>
        {!ehRegistro && item.valor != null && item.meta != null && (
          <p className="numeros">
            {formatar(item.valor, item.formato ?? "int")}{" "}
            <span className="contra">contra a meta de</span>{" "}
            {item.sentido === "max" ? "no máximo " : ""}
            {formatar(item.meta, item.formato ?? "int")}
            {item.atingimento != null && ` · ${item.atingimento.toFixed(0)}% da meta`}
          </p>
        )}
        <p className="acao">{item.texto}</p>
      </div>
    </li>
  );
}

function Campanhas({ campanhas }: { campanhas: CampanhaJet[] }) {
  const [tudo, setTudo] = useState(false);
  if (!campanhas.length) return null;
  const base = campanhas[0].base;
  const mostradas = tudo ? campanhas : campanhas.slice(0, 6);
  return (
    <section className="jet-campanhas">
      <h3>Nota por campanha</h3>
      <p className="sub">
        {base === "venda"
          ? "Pontuadas por cliente fechado, custo por lead e conversão para reunião. Da pior para a melhor."
          : "Pontuadas por custo por lead e CTR. Com a coluna Campanha na planilha de reuniões, elas passam a ser pontuadas por cliente fechado."}
      </p>
      <div className="rolagem">
        <table className="tabela">
          <thead>
            <tr>
              <th scope="col">Campanha</th>
              <th scope="col" className="num">Investido</th>
              {base === "venda" && <th scope="col" className="num">Fechados</th>}
              <th scope="col" className="num">Nota</th>
              <th scope="col">Por quê</th>
            </tr>
          </thead>
          <tbody>
            {mostradas.map((c) => (
              <tr key={c.campanha}>
                <th scope="row" className="nome-campanha">{c.campanha}</th>
                <td className="num">{formatar(c.investido, "brl")}</td>
                {base === "venda" && <td className="num">{c.fechados ?? 0}</td>}
                <td className="num">
                  <span className={`selo-nota ${c.faixa}`}>
                    {c.nota.toFixed(0)} · {ROTULO_FAIXA[c.faixa]}
                  </span>
                </td>
                <td className="porque-campanha">{c.porque}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {campanhas.length > 6 && (
        <button className="discreto" onClick={() => setTudo(!tudo)}>
          {tudo ? "Mostrar só as 6 piores" : `Ver as outras ${campanhas.length - 6}`}
        </button>
      )}
    </section>
  );
}

/* A leitura do JEV. Vem antes da conta porque é o que responde "e daí?", mas
   fica visivelmente separada do Score: ali embaixo tudo é número calculado e
   conferido por teste; aqui em cima é interpretação, e quem lê merece saber a
   diferença. Nenhum número aparece nesta caixa. */
function Leitura({ jev }: { jev?: TipoJev }) {
  if (!jev?.ativo) return null;
  if (!jev.leitura) {
    return <p className="jev-ausente">{jev.motivo}</p>;
  }
  const { leitura, primeiro_passo, pontos, onde_mover_verba } = jev.leitura;
  return (
    <section className="jev">
      <header>
        <span className="marca-jev">JEV</span>
        <span className="aviso-jev">leitura em texto, escrita sobre os números abaixo</span>
      </header>
      <p className="jev-texto">{leitura}</p>

      <div className="jev-primeiro">
        <span className="rotulo">Primeiro passo</span>
        <p>{primeiro_passo}</p>
      </div>

      {pontos.length > 0 && (
        <ol className="jev-pontos">
          {pontos.map((p) => (
            <li key={p.titulo}>
              <strong>{p.titulo}</strong>
              <p>{p.porque}</p>
              {p.indicadores.length > 0 && (
                <p className="apoio">Apoia-se em: {p.indicadores.join(", ")}</p>
              )}
            </li>
          ))}
        </ol>
      )}

      <div className="jev-verba">
        <span className="rotulo">Verba</span>
        <p>{onde_mover_verba}</p>
      </div>
    </section>
  );
}

export default function Jet({ jet, jev }: { jet?: TipoJet; jev?: TipoJev }) {
  if (!jet) {
    return (
      <p className="vazio">
        Esta análise foi feita antes do JET. Rode uma análise nova para ver a nota do mês.
      </p>
    );
  }

  const comCusto = jet.melhorias.filter((m) => m.tipo === "indicador");
  const registros = jet.melhorias.filter((m) => m.tipo === "registro");
  const foraDoCalculo = jet.indicadores.filter((i) => !i.pontuado);

  return (
    <div className="jet">
      <Leitura jev={jev} />

      <section className="jet-topo">
        <Anel score={jet.score} faixa={jet.faixa} />
        <div className="jet-leitura">
          <span className={`selo-faixa ${jet.faixa}`}>
            {jet.faixa === "excelente" || jet.faixa === "bom" ? (
              <IconeOk tamanho={13} />
            ) : (
              <IconeAtencao tamanho={13} />
            )}{" "}
            {ROTULO_FAIXA[jet.faixa]}
          </span>
          <p>{jet.leitura}</p>
          {jet.metas_ausentes.length > 0 && (
            <p className="aviso-metas">
              Sem meta de {jet.metas_ausentes.join(", ")} na planilha. Preencha a aba Metas e o
              Score passa a cobrir também isso.
            </p>
          )}
        </div>
      </section>

      <section className="jet-pilares">
        {jet.pilares.map((p) => <Pilar key={p.chave} pilar={p} />)}
      </section>

      <section className="jet-lista">
        <h3>O que custou pontos</h3>
        {comCusto.length ? (
          <ol>{comCusto.map((m) => <Melhoria key={m.chave ?? m.titulo} item={m} />)}</ol>
        ) : (
          <p className="tudo-certo">
            <IconeCheck tamanho={14} /> Nenhum indicador medido ficou abaixo da meta neste mês.
          </p>
        )}
      </section>

      {registros.length > 0 && (
        <section className="jet-lista">
          <h3>O que impede uma nota mais confiável</h3>
          <p className="sub">
            Estes não tiram pontos: não dá para pontuar o que não foi medido. São o que faz o
            Score do mês que vem valer mais.
          </p>
          <ol>{registros.map((m) => <Melhoria key={m.titulo} item={m} />)}</ol>
        </section>
      )}

      <Campanhas campanhas={jet.campanhas} />

      {foraDoCalculo.length > 0 && (
        <section className="jet-fora">
          <h3>Fora do cálculo</h3>
          <p className="sub">
            O Score não considerou estes indicadores. Aparecem aqui para que ninguém leia a nota
            como se ela cobrisse mais do que cobre.
          </p>
          <ul>
            {foraDoCalculo.map((i) => (
              <li key={i.chave}>
                <strong>{i.rotulo}</strong>
                <span>{i.motivo_fora}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
