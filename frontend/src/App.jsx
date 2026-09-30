import { useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";

import Marca from "./components/Marca";
import { useAuth } from "./auth";
import Analise from "./pages/Analise";
import Cadencia from "./pages/Cadencia";
import Carteira from "./pages/Carteira";
import Configuracao from "./pages/Configuracao";
import Entrada from "./pages/Entrada";
import Equipe from "./pages/Equipe";
import Historico from "./pages/Historico";
import Site from "./pages/Site";
import Upload from "./pages/Upload";

const CHAVE_TEMA = "neriah_tema";

function BotaoTema() {
  const [tema, setTema] = useState(() => {
    try {
      return localStorage.getItem(CHAVE_TEMA) || "";
    } catch {
      return "";
    }
  });

  useEffect(() => {
    if (tema) document.documentElement.setAttribute("data-theme", tema);
    else document.documentElement.removeAttribute("data-theme");
    try {
      if (tema) localStorage.setItem(CHAVE_TEMA, tema);
      else localStorage.removeItem(CHAVE_TEMA);
    } catch {
      /* sem persistência em navegação privada */
    }
  }, [tema]);

  return (
    <button className="discreto" onClick={() => setTema(tema === "dark" ? "light" : "dark")} title="Alternar tema">
      {tema === "dark" ? "☀️ claro" : "🌙 escuro"}
    </button>
  );
}

/** O site público e a entrada são superfícies de marca: sempre no tema claro
 *  da identidade, independentemente da preferência do sistema. */
function ForcarClaro({ children }) {
  useEffect(() => {
    const anterior = document.documentElement.getAttribute("data-theme");
    document.documentElement.setAttribute("data-theme", "light");
    return () => {
      if (anterior) document.documentElement.setAttribute("data-theme", anterior);
      else document.documentElement.removeAttribute("data-theme");
    };
  }, []);
  return children;
}

/** Troca o cliente em foco. Some quando a carteira tem um só. */
function SeletorCliente() {
  const { empresas, empresaId, trocarEmpresa } = useAuth();
  const navegar = useNavigate();
  const local = useLocation();

  if (empresas.length < 2) return null;

  return (
    <div style={{ padding: "0 8px 12px" }}>
      <label htmlFor="seletor-cliente" style={{ fontSize: 11, marginBottom: 4 }}>
        CLIENTE
      </label>
      <select
        id="seletor-cliente"
        value={empresaId || ""}
        onChange={(e) => {
          trocarEmpresa(Number(e.target.value));
          // uma análise pertence a um cliente: manter o id na URL mostraria
          // "não encontrada" ao trocar de cliente
          if (local.pathname.startsWith("/analises/")) navegar("/");
        }}
        style={{ fontSize: 13.5, padding: "7px 9px" }}
      >
        {empresas.map((e) => (
          <option key={e.id} value={e.id}>
            {e.nome}
          </option>
        ))}
      </select>
    </div>
  );
}

function Produto() {
  const { usuario, empresa, sair, temCarteira, ehCliente } = useAuth();
  return (
    <div className="app">
      <nav className="barra-lateral">
        <div className="marca-barra">
          <Marca tamanho={17} />
          <span className="empresa">{usuario.organizacao.nome}</span>
        </div>

        <SeletorCliente />

        {temCarteira && (
          <NavLink to="/carteira" className={({ isActive }) => `nav-item${isActive ? " ativo" : ""}`}>
            Carteira
          </NavLink>
        )}
        <NavLink to="/" end className={({ isActive }) => `nav-item${isActive ? " ativo" : ""}`}>
          Histórico
        </NavLink>
        {!ehCliente && (
          <NavLink to="/nova" className={({ isActive }) => `nav-item${isActive ? " ativo" : ""}`}>
            Nova análise
          </NavLink>
        )}
        {!ehCliente && (
          <NavLink to="/cadencia" className={({ isActive }) => `nav-item${isActive ? " ativo" : ""}`}>
            Cadência
          </NavLink>
        )}
        <NavLink to="/configuracao" className={({ isActive }) => `nav-item${isActive ? " ativo" : ""}`}>
          Configuração
        </NavLink>
        {!ehCliente && (
          <NavLink to="/equipe" className={({ isActive }) => `nav-item${isActive ? " ativo" : ""}`}>
            Equipe
          </NavLink>
        )}

        <div style={{ marginTop: "auto", display: "flex", gap: 6, flexWrap: "wrap" }}>
          <BotaoTema />
          <button className="discreto" onClick={sair}>
            sair ({usuario.nome.split(" ")[0]})
          </button>
        </div>
      </nav>

      <main className="conteudo">
        {/* A key força as telas a recarregar quando o cliente em foco muda */}
        <Routes key={empresa?.id || "sem-empresa"}>
          <Route path="/" element={<Historico />} />
          <Route path="/carteira" element={<Carteira />} />
          <Route path="/nova" element={<Upload />} />
          <Route path="/analises/:id" element={<Analise />} />
          <Route path="/cadencia" element={<Cadencia />} />
          <Route path="/configuracao" element={<Configuracao />} />
          <Route path="/equipe" element={<Equipe />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  const { usuario, carregando } = useAuth();

  if (carregando) return <div className="vazio">Carregando…</div>;

  if (!usuario) {
    return (
      <ForcarClaro>
        <Routes>
          <Route path="/entrar" element={<Entrada />} />
          <Route path="/" element={<Site />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </ForcarClaro>
    );
  }

  return <Produto />;
}
