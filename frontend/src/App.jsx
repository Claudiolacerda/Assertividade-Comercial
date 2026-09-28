import { useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";

import Marca from "./components/Marca";
import { useAuth } from "./auth";
import Analise from "./pages/Analise";
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

/** O site público e a entrada usam sempre o tema escuro da marca, independente
 *  da preferência do sistema — são superfícies de marca, não de leitura. */
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

function Produto() {
  const { usuario, sair } = useAuth();
  return (
    <div className="app">
      <nav className="barra-lateral">
        <div className="marca-barra">
          <Marca tamanho={17} />
          <span className="empresa">{usuario.empresa.nome}</span>
        </div>
        <NavLink to="/" end className={({ isActive }) => `nav-item${isActive ? " ativo" : ""}`}>
          Histórico
        </NavLink>
        <NavLink to="/nova" className={({ isActive }) => `nav-item${isActive ? " ativo" : ""}`}>
          Nova análise
        </NavLink>
        <NavLink to="/configuracao" className={({ isActive }) => `nav-item${isActive ? " ativo" : ""}`}>
          Configuração
        </NavLink>
        <NavLink to="/equipe" className={({ isActive }) => `nav-item${isActive ? " ativo" : ""}`}>
          Equipe
        </NavLink>
        <div style={{ marginTop: "auto", display: "flex", gap: 6, flexWrap: "wrap" }}>
          <BotaoTema />
          <button className="discreto" onClick={sair}>
            sair ({usuario.nome.split(" ")[0]})
          </button>
        </div>
      </nav>

      <main className="conteudo">
        <Routes>
          <Route path="/" element={<Historico />} />
          <Route path="/nova" element={<Upload />} />
          <Route path="/analises/:id" element={<Analise />} />
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
