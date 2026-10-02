/* Sistema de ícones do Neriah.
 *
 * Desenhados, não emoji. Emoji muda de forma e de cor a cada sistema
 * operacional, não acompanha a tinta do tema e não tem peso de traço
 * consistente — três coisas que um ícone de produto precisa ter.
 *
 * Regras: 16px de caixa, traço de 1,6, pontas e junções arredondadas, tudo em
 * currentColor. Quem define a cor é quem usa. Todos decorativos: pela Regra do
 * Ícone Obrigatório o texto sempre vem junto, então o leitor de tela não perde
 * nada ao ignorá-los. */

function Svg({ children, tamanho = 16 }) {
  return (
    <svg
      width={tamanho}
      height={tamanho}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      style={{ flex: "none", display: "block" }}
    >
      {children}
    </svg>
  );
}

/* ---------------------------------------------------- canais da cadência */

export const IconeWhatsApp = (p) => (
  <Svg {...p}>
    <path d="M2.6 13.4 3.5 10.5A5.4 5.4 0 1 1 5.6 12.6z" />
    <path d="M6.1 6.3c.2 1.9 1.7 3.4 3.6 3.6" strokeWidth="1.3" />
  </Svg>
);

export const IconeLigacao = (p) => (
  <Svg {...p}>
    <path d="M3 3.3h2.4l1 2.5-1.4 1a7 7 0 0 0 3.2 3.2l1-1.4 2.5 1V12a1.3 1.3 0 0 1-1.4 1.3A9.7 9.7 0 0 1 2.7 4.7 1.3 1.3 0 0 1 3 3.3z" />
  </Svg>
);

export const IconeEmail = (p) => (
  <Svg {...p}>
    <rect x="1.8" y="3.6" width="12.4" height="8.8" rx="1.4" />
    <path d="m2.4 4.6 5.6 4 5.6-4" />
  </Svg>
);

export const IconeReuniao = (p) => (
  <Svg {...p}>
    <circle cx="5.6" cy="5.3" r="2.1" />
    <circle cx="11" cy="6.1" r="1.7" />
    <path d="M1.9 13.1c0-2 1.7-3.4 3.7-3.4s3.7 1.4 3.7 3.4" />
    <path d="M11 9.8c1.7 0 3.1 1.1 3.1 2.6" strokeWidth="1.3" />
  </Svg>
);

export const IconeEspera = (p) => (
  <Svg {...p}>
    <circle cx="8" cy="8" r="6.1" />
    <path d="M8 4.6V8l2.3 1.5" />
  </Svg>
);

export const IconeDecisao = (p) => (
  <Svg {...p}>
    <path d="M2.2 3.5h2.3l3 4.5 3 4.5h2.4" />
    <path d="M2.2 12.5h2.3l2-3" />
    <path d="m12 1.9 2.1 1.6L12 5.1" />
    <path d="m12 10.9 2.1 1.6L12 14.1" />
  </Svg>
);

export const IconeNota = (p) => (
  <Svg {...p}>
    <path d="M9.6 1.9 14.1 6.4 11.9 8.6 11 7.7 8.3 10.4l.5 2.6-1 1-6-6 1-1 2.6.5L7.4 4.4l-.9-.9z" />
    <path d="m2.6 13.4 2.1-2.1" strokeWidth="1.3" />
  </Svg>
);

/* -------------------------------------------- níveis do diagnóstico */

export const IconeCritico = (p) => (
  <Svg {...p}>
    <circle cx="8" cy="8" r="6.1" />
    <path d="M8 4.9v3.6" />
    <path d="M8 11.1h.01" strokeWidth="2" />
  </Svg>
);

export const IconeQuente = (p) => (
  <Svg {...p}>
    <path d="M8 1.6c2.6 2.2 3.9 4.2 3.9 6a3.9 3.9 0 0 1-7.8 0c0-1.8 1.3-3.8 3.9-6z" />
    <path d="M8 13.8c-1.1 0-2-.9-2-2 0-.9.7-1.9 2-3 1.3 1.1 2 2.1 2 3 0 1.1-.9 2-2 2z" strokeWidth="1.3" />
  </Svg>
);

export const IconeAtencao = (p) => (
  <Svg {...p}>
    <path d="M7 2.4a1.2 1.2 0 0 1 2 0l5.1 9.1a1.2 1.2 0 0 1-1 1.8H2.9a1.2 1.2 0 0 1-1-1.8z" />
    <path d="M8 6.2v2.9" />
    <path d="M8 11.3h.01" strokeWidth="2" />
  </Svg>
);

export const IconeOk = (p) => (
  <Svg {...p}>
    <circle cx="8" cy="8" r="6.1" />
    <path d="m5.3 8.2 1.9 1.9 3.5-4" />
  </Svg>
);

export const IconeInfo = (p) => (
  <Svg {...p}>
    <circle cx="8" cy="8" r="6.1" />
    <path d="M8 7.4v3.7" />
    <path d="M8 4.9h.01" strokeWidth="2" />
  </Svg>
);

/* ------------------------------------------------------- interface */

export const IconeCheck = (p) => (
  <Svg {...p}>
    <path d="m3.2 8.4 3.2 3.2 6.4-7.2" />
  </Svg>
);

export const IconeSol = (p) => (
  <Svg {...p}>
    <circle cx="8" cy="8" r="3.1" />
    <path d="M8 1.3v1.4M8 13.3v1.4M1.3 8h1.4M13.3 8h1.4M3.3 3.3l1 1M11.7 11.7l1 1M12.7 3.3l-1 1M4.3 11.7l-1 1" />
  </Svg>
);

export const IconeLua = (p) => (
  <Svg {...p}>
    <path d="M13.3 9.6A5.9 5.9 0 0 1 6.4 2.7a5.9 5.9 0 1 0 6.9 6.9z" />
  </Svg>
);

export const IconeSair = (p) => (
  <Svg {...p}>
    <path d="M6.2 2.7H3.4a.9.9 0 0 0-.9.9v8.8a.9.9 0 0 0 .9.9h2.8" />
    <path d="M10.4 11.1 13.5 8l-3.1-3.1" />
    <path d="M13.5 8H6.4" />
  </Svg>
);

export const IconeSubida = (p) => (
  <Svg {...p}>
    <path d="M8 13V3.4" />
    <path d="m3.9 7.5 4.1-4.1 4.1 4.1" />
  </Svg>
);

export const IconeQueda = (p) => (
  <Svg {...p}>
    <path d="M8 3v9.6" />
    <path d="m3.9 8.5 4.1 4.1 4.1-4.1" />
  </Svg>
);

export const IconeDiagonal = (p) => (
  <Svg {...p}>
    <path d="M4 12 12 4" />
    <path d="M6.6 4H12v5.4" />
  </Svg>
);

/** Nível do diagnóstico -> componente. A chave é o texto que o motor devolve. */
export const ICONES_NIVEL = {
  critico: IconeCritico,
  quente: IconeQuente,
  atencao: IconeAtencao,
  ok: IconeOk,
  info: IconeInfo,
};
