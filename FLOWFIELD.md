# FlowField no Hero — passo que falta

O único item da migração que não pôde ser executado, e por quê.

## Por que parou

A política de rede deste ambiente nega os dois hosts de que o `shadcn` CLI
precisa em tempo de execução:

```
ui.shadcn.com     -> 403 (CONNECT negado pela política)
kokonutui.com     -> 403 (CONNECT negado pela política)
registry.npmjs.org -> 200
```

O `npm` funciona, então **tudo que vem do npm já está instalado**: TypeScript,
Tailwind v4, `@tailwindcss/vite`, `clsx`, `tailwind-merge`,
`class-variance-authority` e `lucide-react`. O que falta é só o arquivo do
componente, que mora em `kokonutui.com`.

## Como liberar

No menu do ambiente, na barra de título da sessão: **Edit** → **Network
access**. Adicione `ui.shadcn.com` e `kokonutui.com` aos domínios permitidos, ou
suba o nível de acesso. Os níveis estão descritos em
https://code.claude.com/docs/en/claude-code-on-the-web

## O comando

Com a rede liberada, da pasta `frontend`:

```bash
npx shadcn@latest add https://kokonutui.com/r/flow-field.json
```

O `components.json` já está configurado e aponta o componente para
`src/componentes-ui/`, o utilitário para `@/lib/utils` e o CSS para
`src/tailwind.css`. O alias `@/*` já resolve no `tsconfig.json` e no
`vite.config.ts`.

## Onde aplicar

**Somente como fundo do Hero.** O Hero é o bloco `.escuro.sobre-escuro` em
`src/pages/Site.tsx`, que contém o cabeçalho, o título, a chamada, os botões e o
painel demonstrativo.

O FlowField entra como primeira camada dentro desse bloco, atrás de tudo:

```tsx
<div className="escuro sobre-escuro" style={{ position: "relative" }}>
  <div className="fundo-hero" aria-hidden="true">
    <FlowField />
  </div>
  {/* todo o conteúdo atual do Hero segue aqui, sem alteração */}
</div>
```

Com o CSS:

```css
.fundo-hero {
  position: absolute;
  inset: 0;
  z-index: -3;   /* abaixo da luz (-2) e da malha (-1) de .escuro */
  pointer-events: none;
  overflow: hidden;
}
```

Nenhuma outra seção recebe o efeito: `.secao.clara`, `.secao.alterna`,
`#planos`, `.chamada-final` e o rodapé ficam exatamente como estão.

## Três coisas para decidir na hora de aplicar

**1. O facho já ocupa esse espaço.** O Hero tem o momento de assinatura do
sistema, um feixe que varre o painel na entrada. O DESIGN.md registra a Regra do
Momento Único: dois efeitos extraordinários no mesmo lugar dividem a atenção.
Ou o FlowField fica discreto o bastante para ser cenário do facho, ou um dos
dois sai. Isso é decisão sua, não minha.

**2. A luz e a malha de `.escuro`.** O bloco já tem dois pseudo-elementos de
fundo: o gradiente direcional (`::before`, z-index -2) e a malha técnica
(`::after`, z-index -1). O FlowField precisa ficar abaixo dos dois, ou um deles
sai para não virar sopa de camadas.

**3. Movimento reduzido.** O FlowField anima continuamente. O sistema tem um
caminho de `prefers-reduced-motion` que remove todo deslocamento no espaço, e o
playbook exige que animação não essencial pare quando fora da tela. O
componente precisa respeitar os dois, e isso pode exigir um wrapper.

## Como ficou verificado antes deste passo

| | Linha de base | Depois da migração |
|---|---|---|
| Testes do backend | 74 | 74 |
| Erros de tipo | — | 0 |
| Contraste reprovado (claro / escuro) | 0 / 0 | 0 / 0 |
| Estouro horizontal | 0 | 0 |
| CLS (desktop / celular) | 0,0000 / 0,0000 | 0,0078 / 0,0028 |
| FPS (desktop / celular) | 58 / 56 | 59 / 56 |
| Foco com anel | 21/21 | 21/21 |
| Campos sem rótulo | 0 | 0 |
| Erros de console | 0 | 0 |
