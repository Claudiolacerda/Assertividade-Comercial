/* Canvas de cadência.
 *
 * Arrastar, ligar e editar como num quadro branco — mas o que o diferencia de um
 * Miro é o botão "Sugerir pela análise": o fluxo nasce das objeções que a equipe
 * registrou na planilha, não de um modelo genérico. */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  useReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { api } from "../api";
import EtapaCadencia, { CANAIS } from "../components/EtapaCadencia";

const tiposDeNo = { etapa: EtapaCadencia };

/** O backend guarda {nos, ligacoes}; o React Flow fala {nodes, edges}. */
const paraTela = (fluxo) => ({
  nodes: (fluxo?.nos || []).map((n) => ({ ...n, type: n.type || "etapa" })),
  edges: (fluxo?.ligacoes || []).map((e) => ({ ...e, animated: true })),
});
const paraBanco = (nodes, edges) => ({
  nos: nodes.map(({ id, type, position, data }) => ({ id, type, position, data })),
  ligacoes: edges.map(({ id, source, target }) => ({ id, source, target })),
});

function Editor({ cadencia, aoSalvar, aoVoltar }) {
  const inicial = useMemo(() => paraTela(cadencia.fluxo), [cadencia.fluxo]);
  const [nodes, setNodes] = useState(inicial.nodes);
  const [edges, setEdges] = useState(inicial.edges);
  const [nome, setNome] = useState(cadencia.nome);
  const [selecionado, setSelecionado] = useState(null);
  const [sujo, setSujo] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [salvoEm, setSalvoEm] = useState(null);
  const { screenToFlowPosition } = useReactFlow();
  const proximoId = useRef(Date.now());

  const marcarSujo = () => setSujo(true);

  const onNodesChange = useCallback((mudancas) => {
    setNodes((ns) => applyNodeChanges(mudancas, ns));
    // arrastar e selecionar não são alterações que valha salvar sozinhas
    if (mudancas.some((m) => m.type === "remove" || (m.type === "position" && m.dragging === false))) {
      setSujo(true);
    }
  }, []);

  const onEdgesChange = useCallback((mudancas) => {
    setEdges((es) => applyEdgeChanges(mudancas, es));
    if (mudancas.some((m) => m.type === "remove")) setSujo(true);
  }, []);

  const onConnect = useCallback((conexao) => {
    setEdges((es) => addEdge({ ...conexao, animated: true, id: `e${Date.now()}` }, es));
    setSujo(true);
  }, []);

  function adicionar(canal) {
    const id = `n${proximoId.current++}`;
    // nasce no centro da área visível, não em cima do que já existe
    const pos = screenToFlowPosition({
      x: window.innerWidth / 2,
      y: window.innerHeight / 2 - 60,
    });
    const ultimoDia = nodes.reduce((m, n) => Math.max(m, n.data?.dia ?? 0), 0);
    setNodes((ns) => [
      ...ns,
      {
        id,
        type: "etapa",
        position: { x: pos.x + Math.random() * 40, y: pos.y + Math.random() * 40 },
        data: { canal, titulo: CANAIS[canal].rotulo, dia: ultimoDia, texto: "" },
      },
    ]);
    setSelecionado(id);
    setSujo(true);
  }

  function alterarNo(campo, valor) {
    setNodes((ns) =>
      ns.map((n) => (n.id === selecionado ? { ...n, data: { ...n.data, [campo]: valor } } : n)),
    );
    setSujo(true);
  }

  function removerNo() {
    setNodes((ns) => ns.filter((n) => n.id !== selecionado));
    setEdges((es) => es.filter((e) => e.source !== selecionado && e.target !== selecionado));
    setSelecionado(null);
    setSujo(true);
  }

  const salvar = useCallback(async () => {
    setSalvando(true);
    try {
      await api.salvarCadencia(cadencia.id, { nome, fluxo: paraBanco(nodes, edges) });
      setSujo(false);
      setSalvoEm(new Date());
      aoSalvar?.();
    } finally {
      setSalvando(false);
    }
  }, [cadencia.id, nome, nodes, edges, aoSalvar]);

  // Salva sozinho 2s depois da última mexida — ninguém deveria perder desenho
  // por esquecer de clicar em salvar.
  useEffect(() => {
    if (!sujo) return;
    const t = setTimeout(salvar, 2000);
    return () => clearTimeout(t);
  }, [sujo, salvar]);

  // Avisa antes de fechar a aba com alteração pendente
  useEffect(() => {
    const aviso = (e) => {
      if (sujo) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", aviso);
    return () => window.removeEventListener("beforeunload", aviso);
  }, [sujo]);

  const no = nodes.find((n) => n.id === selecionado);

  return (
    <div className="editor-cadencia">
      <header className="editor-topo">
        <div style={{ display: "flex", alignItems: "center", gap: 12, minWidth: 0, flex: 1 }}>
          <button className="discreto" onClick={aoVoltar}>
            ← cadências
          </button>
          <input
            value={nome}
            onChange={(e) => {
              setNome(e.target.value);
              setSujo(true);
            }}
            aria-label="Nome da cadência"
            style={{ fontWeight: 650, fontSize: 15, maxWidth: 380, border: "1px solid transparent" }}
          />
          <span style={{ fontSize: 12, color: "var(--ink-muted)", whiteSpace: "nowrap" }}>
            {salvando
              ? "salvando…"
              : sujo
                ? "alterações não salvas"
                : salvoEm
                  ? `salvo ${salvoEm.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}`
                  : "salvo"}
          </span>
        </div>
        <button className="primario" onClick={salvar} disabled={salvando || !sujo}>
          Salvar
        </button>
      </header>

      <div className="editor-corpo">
        <aside className="paleta">
          <div className="paleta-titulo">Arraste para o fluxo</div>
          {Object.entries(CANAIS).map(([chave, c]) => (
            <button key={chave} className="paleta-item" onClick={() => adicionar(chave)}>
              <span style={{ color: c.cor }} aria-hidden="true">
                {c.icone}
              </span>
              {c.rotulo}
            </button>
          ))}
          <p className="paleta-dica">
            Clique para adicionar. Ligue as etapas arrastando da bolinha da direita até a da esquerda
            da próxima.
          </p>
        </aside>

        <div className="tela-fluxo">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={tiposDeNo}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={(_, n) => setSelecionado(n.id)}
            onPaneClick={() => setSelecionado(null)}
            fitView
            proOptions={{ hideAttribution: false }}
            deleteKeyCode={["Backspace", "Delete"]}
          >
            <Background gap={22} size={1} color="var(--grid)" />
            <Controls showInteractive={false} />
            <MiniMap pannable zoomable nodeColor={(n) => CANAIS[n.data?.canal]?.cor || "#8b9995"} />
          </ReactFlow>

          {nodes.length === 0 && (
            <div className="fluxo-vazio">
              <h3>Fluxo vazio</h3>
              <p>Escolha um canal na lateral para criar a primeira etapa.</p>
            </div>
          )}
        </div>

        {no && (
          <aside className="inspetor">
            <div className="paleta-titulo">Etapa</div>

            <label htmlFor="i-canal">Canal</label>
            <select id="i-canal" value={no.data.canal} onChange={(e) => alterarNo("canal", e.target.value)}>
              {Object.entries(CANAIS).map(([k, c]) => (
                <option key={k} value={k}>
                  {c.rotulo}
                </option>
              ))}
            </select>

            <label htmlFor="i-titulo" style={{ marginTop: 14 }}>
              Título
            </label>
            <input id="i-titulo" value={no.data.titulo || ""} onChange={(e) => alterarNo("titulo", e.target.value)} />

            <label htmlFor="i-dia" style={{ marginTop: 14 }}>
              Dia (a partir do lead)
            </label>
            <input
              id="i-dia"
              type="number"
              min="0"
              max="365"
              value={no.data.dia ?? 0}
              onChange={(e) => alterarNo("dia", Number(e.target.value))}
            />

            <label htmlFor="i-texto" style={{ marginTop: 14 }}>
              Roteiro / mensagem
            </label>
            <textarea
              id="i-texto"
              rows={8}
              value={no.data.texto || ""}
              onChange={(e) => alterarNo("texto", e.target.value)}
              placeholder="Oi {nome}! …"
            />
            <p style={{ fontSize: 12, color: "var(--ink-muted)", margin: "7px 0 0" }}>
              Use <code>{"{nome}"}</code> para o nome do cliente na hora de enviar.
            </p>

            <button className="discreto" onClick={removerNo} style={{ marginTop: 18, color: "var(--critico)" }}>
              Remover etapa
            </button>
          </aside>
        )}
      </div>
    </div>
  );
}

export default function Cadencia() {
  const [lista, setLista] = useState(null);
  const [modelos, setModelos] = useState([]);
  const [analises, setAnalises] = useState([]);
  const [aberta, setAberta] = useState(null);
  const [erro, setErro] = useState("");
  const [criando, setCriando] = useState(false);

  async function carregar() {
    try {
      const [cs, ms, as] = await Promise.all([api.cadencias(), api.modelosCadencia(), api.analises()]);
      setLista(cs);
      setModelos(ms);
      setAnalises(as.filter((a) => a.status === "concluida"));
    } catch (e) {
      setErro(e.message);
    }
  }

  useEffect(() => {
    carregar();
  }, []);

  async function criar(payload) {
    setErro("");
    setCriando(true);
    try {
      const nova = await api.criarCadencia(payload);
      const completa = await api.cadencia(nova.id);
      setAberta(completa);
      await carregar();
    } catch (e) {
      setErro(e.message);
    } finally {
      setCriando(false);
    }
  }

  async function abrir(id) {
    try {
      setAberta(await api.cadencia(id));
    } catch (e) {
      setErro(e.message);
    }
  }

  async function excluir(id, nome) {
    if (!window.confirm(`Arquivar a cadência "${nome}"?`)) return;
    try {
      await api.excluirCadencia(id);
      await carregar();
    } catch (e) {
      setErro(e.message);
    }
  }

  if (aberta) {
    return (
      <ReactFlowProvider>
        <Editor
          key={aberta.id}
          cadencia={aberta}
          aoSalvar={carregar}
          aoVoltar={() => {
            setAberta(null);
            carregar();
          }}
        />
      </ReactFlowProvider>
    );
  }

  if (!lista && !erro) return <div className="vazio">Carregando cadências…</div>;

  return (
    <>
      <div className="cabecalho-pagina">
        <div>
          <h1>Cadência</h1>
          <p>
            Desenhe o fluxo de follow-up da sua equipe. Cada etapa tem canal, dia e roteiro — e o
            Neriah sabe sugerir o fluxo a partir das objeções que a sua análise encontrou.
          </p>
        </div>
      </div>

      {erro && (
        <div className="aviso erro" style={{ marginBottom: 16 }} role="alert">
          {erro}
        </div>
      )}

      {analises.length > 0 && (
        <section className="cartao destaque-sugestao" style={{ marginBottom: 18 }}>
          <h2>Sugerir a partir da análise</h2>
          <p style={{ color: "var(--ink-2)", fontSize: 14, margin: "7px 0 14px", maxWidth: "75ch" }}>
            O fluxo nasce do que a sua planilha mostrou: as objeções mais frequentes, os clientes
            quentes pelo nome e as oportunidades que pararam de andar. É a diferença entre um quadro
            branco e uma cadência que já sabe onde a sua venda trava.
          </p>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
            {analises.slice(0, 3).map((a) => (
              <button
                key={a.id}
                className="primario"
                disabled={criando}
                onClick={() => criar({ analise_id: a.id })}
              >
                Gerar de {a.mes_referencia}
              </button>
            ))}
          </div>
        </section>
      )}

      <section className="cartao" style={{ marginBottom: 18 }}>
        <h2>Começar de um modelo</h2>
        <div className="grade" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", marginTop: 14 }}>
          {modelos.map((m) => (
            <button
              key={m.chave}
              className="modelo-cadencia"
              disabled={criando}
              onClick={() => criar({ modelo: m.chave })}
            >
              <span className="nome">{m.nome}</span>
              <span className="desc">{m.descricao}</span>
              <span className="etapas">{m.etapas} etapas</span>
            </button>
          ))}
          <button className="modelo-cadencia" disabled={criando} onClick={() => criar({})}>
            <span className="nome">Começar em branco</span>
            <span className="desc">Uma tela vazia, para montar do seu jeito.</span>
            <span className="etapas">0 etapas</span>
          </button>
        </div>
      </section>

      <section className="cartao">
        <h2>Suas cadências</h2>
        {!lista?.length ? (
          <p style={{ color: "var(--ink-2)", fontSize: 14, marginTop: 8 }}>
            Nenhuma ainda. Gere pela análise ou escolha um modelo acima.
          </p>
        ) : (
          <div className="rolagem" style={{ marginTop: 12 }}>
            <table>
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Etapas</th>
                  <th>Atualizada</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {lista.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <button
                        className="discreto"
                        style={{ padding: 0, color: "var(--verde)", fontWeight: 650 }}
                        onClick={() => abrir(c.id)}
                      >
                        {c.nome}
                      </button>
                      {c.descricao && (
                        <div style={{ fontSize: 11.5, color: "var(--ink-muted)", maxWidth: 560 }}>
                          {c.descricao}
                        </div>
                      )}
                    </td>
                    <td className="num">{c.etapas}</td>
                    <td>{new Date(c.atualizada_em).toLocaleDateString("pt-BR")}</td>
                    <td style={{ textAlign: "right" }}>
                      <button className="discreto" onClick={() => abrir(c.id)}>
                        abrir
                      </button>
                      <button className="discreto" onClick={() => excluir(c.id, c.nome)}>
                        arquivar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
