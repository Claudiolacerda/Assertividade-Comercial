import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import App from "./App";
import { ProvedorAuth } from "./auth";
import urlArchivo from "@fontsource-variable/archivo/files/archivo-latin-wght-normal.woff2?url";

import "./tailwind.css";
import "./index.css";

/* A fonte precisa chegar antes da primeira pintura. O `swap` do Fontsource
   troca a fonte depois do layout pronto, e isso reintroduziria o salto que
   este projeto zerou. O preload vai por aqui, e não no HTML, porque só o
   bundler sabe o nome final do arquivo. */
const preload = document.createElement("link");
preload.rel = "preload";
preload.as = "font";
preload.type = "font/woff2";
preload.crossOrigin = "anonymous";
preload.href = urlArchivo;
document.head.prepend(preload);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <ProvedorAuth>
        <App />
      </ProvedorAuth>
    </BrowserRouter>
  </React.StrictMode>,
);
