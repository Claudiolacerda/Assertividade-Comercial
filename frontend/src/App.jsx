import { useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "./auth";
import Analise from "./pages/Analise";
import Configuracao from "./pages/Configuracao";
import Entrada from "./pages/Entrada";
import Equipe from "./pages/Equipe";
import Historico from "./pages/Historico";
import Upload from "./pages/Upload";

const CHAVE_TEMA = "assertividade_tema";

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

  const proximo = tema === "dark" ? "light" : "dark";
  return (
    <button className="discreto" onClick={() => setTema(proximo)} title="Alternar tema">
      {tema === "dark" ? "☀️ claro" : "🌙 escuro"}
    </button>
  );
}

export default function App() {
  const { usuario, carregando, sair } = useAuth();

  if (carregando) return <div className="vazio">Carregando…</div>;
  if (!usuario) return <Entrada />;

  return (
    <div className="app">
      <nav className="barra-lateral">
        <div className="marca">
          Assertividade
          <small>{usuario.empresa.nome}</small>
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
