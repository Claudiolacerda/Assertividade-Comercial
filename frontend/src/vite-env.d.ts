/// <reference types="vite/client" />

import "react";

declare module "react" {
  /* O sistema usa variáveis CSS como canal de dados para o estilo
     (--cor-canal, --atraso, --ind-x). Sem esta extensão o TypeScript recusa
     qualquer custom property dentro de `style`, e a alternativa seria espalhar
     `as React.CSSProperties` por dezenas de componentes. */
  interface CSSProperties {
    [variavel: `--${string}`]: string | number | undefined;
  }
}
