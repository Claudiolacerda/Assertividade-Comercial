# Design System: Neriah Data

> Documento descritivo. Ele registra o sistema que o código **já implementa** hoje
> (`frontend/src/index.css`, 1175 linhas, mais os componentes em `frontend/src/`).
> Nenhuma regra aqui é aspiracional: cada token, classe e medida citada existe no
> repositório. Quando uma decisão tem motivo, o motivo está escrito — é o que
> impede que ela seja desfeita por engano seis meses depois.

---

## 1. Visão geral: "a luz sobre o dado"

**Norte criativo:** Neriah significa *luz*. A marca nasce do escuro — `#040D0C`, o
fundo da própria logo — e o verde é a luz que revela o dado. Toda a lógica de
superfície sai daí, e ela não é decorativa:

- **Momentos de marca são escuros.** Site público (hero, chamada final, rodapé) e
  tela de entrada. É onde a pessoa decide se confia no produto; o escuro com o
  brilho verde carrega a identidade.
- **O produto é claro.** Painel, análises, tabelas, carteira. É onde se lê número
  o dia inteiro, e número se lê melhor em tinta escura sobre fundo claro.

A troca de superfície marca a passagem de "isto é uma marca" para "isto é uma
ferramenta". Não é um gradiente de estilo: é a fronteira entre vender e trabalhar.

**Características do sistema**

- Superfícies planas, bordas de 1px, sombra quase inexistente no produto.
- Verde como único acento de marca. Nada de segunda cor de marca.
- Tipografia de sistema (`system-ui`), sem webfont. Carregar fonte custa tempo de
  primeira pintura e o produto não ganha nada com isso.
- Números em `tabular-nums` em toda coluna numérica — alinham na vertical.
- Densidade de ferramenta, não de landing page: 15px de corpo, 13px em tabela.
- Tudo funciona em claro e escuro, por `prefers-color-scheme` **e** por
  `data-theme` manual.

---

## 2. O vocabulário: uma classe por padrão

Não há biblioteca de componentes nem utilitários tipo Tailwind. O sistema é um
arquivo de CSS global com classes semânticas em português, e os componentes React
consomem essas classes. Antes de escrever CSS novo, procure a classe que já existe.

### A regra do consumo

- **Superfície que agrupa conteúdo** → `.cartao`. É a resposta canônica para "como
  eu junto um bloco de coisas". Não invente `.painel-x`, `.caixa-y`, `.bloco-z`.
- **Número em destaque** → `.tile` (com `.rotulo`, `.numero`, `.nota`). Para o KPI
  principal, `.tile.destaque`.
- **Botão** → `button` puro já vem estilizado. Variantes: `.primario` (verde,
  ação principal — uma por tela) e `.discreto` (texto, ação secundária).
- **Gráfico** → `.grafico` + `.grafico-topo` + `.legenda`. Ver §6.
- **Mensagem de estado** → `.aviso`, `.aviso.erro`, `.aviso.ok`.
- **Grade** → `.grade.dois` (duas colunas que colapsam) ou `.grade.tiles` (fileira
  de KPIs). Ambas usam `auto-fit`/`minmax`, então respondem sem media query.

Inventar é permitido quando a forma é realmente nova. Quando inventar, a classe
nova entra no `index.css` na seção temática que lhe cabe — não em CSS inline nem
em um arquivo por página. CSS inline no projeto é aceitável só para valores
calculados em tempo de execução (uma cor de canal, uma largura de barra).

### Inventário por seção do `index.css`

| Linha | Seção | Classes principais |
|---|---|---|
| 13–120 | tokens e base | `:root`, temas, `body`, `h1`–`h3` |
| 123 | marca | `.marca-lockup`, `.marca-nome`, `.marca-sub`, `.sobre-escuro` |
| 154 | controles | `button`, `.primario`, `.discreto`, `input`, `label` |
| 212 | layout do produto | `.app`, `.barra-lateral`, `.nav-item`, `.conteudo`, `.cartao`, `.grade` |
| 289 | stat tiles | `.tile`, `.selo` |
| 331 | gráficos | `.grafico`, `.legenda`, `.dica` |
| 368 | tabelas | `table`, `td.num`, `td.texto`, `.rolagem` |
| 380 | diagnóstico | `.diag` |
| 393 | avisos e navegação | `.aviso`, `.abas`, `.arraste`, `.vazio` |
| 433 | superfícies escuras | `.escuro` + `::before` (luz) + `::after` (malha) |
| 468 | site público | `.topo`, `.hero`, `.moldura`, `.demo-*`, `.tira`, `.secao`, `.passo`, `.cartao-rec`, `.lista-check`, `.rodape` |
| 712 | entrada | `.entrada`, `.entrada-marca`, `.prova`, `.entrada-form` |
| 771 | planos | `.planos`, `.plano`, `.fita` |
| 889 | WhatsApp | `.zap-flutuante` |
| 917 | canvas de cadência | `.editor-cadencia`, `.paleta`, `.inspetor`, `.no-etapa`, overrides do React Flow |
| 1080 | vitrine (home) | `.palco-zap`, `.bolha-zap`, `.palco-fluxo`, `.mini-etapa` |

---

## 3. Cores

### A regra do token

Nenhum valor de cor literal em componente, com três exceções justificadas:
cor de canal da cadência (§6), verde do WhatsApp (`#25d366`, é cor de marca de
terceiro) e as superfícies de marca do site escuro, que usam `rgba(255,255,255,α)`
porque precisam de transparência sobre o fundo preto.

### Marca

| Token | Claro | Escuro | Papel |
|---|---|---|---|
| `--verde` | `#099938` | `#53ef86` | Verde funcional. **Troca de valor por tema** — ver a regra abaixo |
| `--verde-vivo` | `#53ef86` | `#53ef86` | Verde da logo. Só sobre escuro, nunca sobre branco |
| `--verde-fundo` | `#e8fbef` | `#0f2318` | Lavagem verde para realce suave (nav ativa, numeração de passo) |
| `--preto-neriah` | `#040d0c` | — | Fundo da logo. É o preto da marca, não `#000` |

**A regra do verde-por-superfície.** O verde da logo (`#53ef86`) é lindo sobre
preto e ilegível sobre branco — reprova contraste para texto. Por isso `--verde`
é `#099938` no tema claro e `#53ef86` no escuro, enquanto `--verde-vivo` fica fixo
e só aparece em superfície escura. Escrever `--verde-vivo` num contexto claro é
sempre erro.

### Superfícies e tinta (produto)

| Token | Claro | Escuro |
|---|---|---|
| `--page` | `#f7f9f8` | `#040d0c` |
| `--surface` | `#ffffff` | `#0b1513` |
| `--surface-2` | `#f1f4f3` | `#142220` |
| `--ink` | `#0a1412` | `#ffffff` |
| `--ink-2` | `#4c5a57` | `#b9c7c3` |
| `--ink-muted` | `#7d8a87` | `#8b9995` |
| `--grid` | `#e4eae8` | `#1d2b28` |
| `--axis` | `#c4cecb` | `#2c3c39` |
| `--borda` | `rgba(10,20,18,.1)` | `rgba(255,255,255,.1)` |

Três níveis de tinta e só três: `--ink` para o que se lê, `--ink-2` para apoio,
`--ink-muted` para metadado. Um quarto nível não aumenta hierarquia, só reduz
contraste.

### Séries de gráfico

| Token | Claro | Escuro |
|---|---|---|
| `--series-1` | `#099938` | `#0db243` |
| `--series-2` | `#2a78d6` | `#3987e5` |
| `--series-3` | `#e87ba4` | `#d55181` |

**A regra da paleta validada.** Estas três cores foram escolhidas e medidas, não
escolhidas e aprovadas no olho. O pior par de qualquer combinação, simulado para
protanopia, deuteranopia e tritanopia, fica em **ΔE 13,0 no claro** e **8,7 no
escuro**; o mínimo exigido é 8. Uma tentativa anterior usava verde + laranja e
reprovou com ΔE 4,3 em protanopia — por isso o terceiro slot é magenta e não
laranja, que seria a escolha "natural". **Trocar qualquer um dos seis valores
exige refazer a medição.** Não é uma preferência estética; é o que impede que um
cliente daltônico leia o gráfico errado.

### Status

| Token | Valor | Uso |
|---|---|---|
| `--bom` | `#0ca30c` | Meta batida |
| `--atencao` | `#fab219` | Fora da meta, sem urgência |
| `--serio` | `#ec835a` | Fora da meta com impacto |
| `--critico` | `#d03b3b` | Exige ação, e ação destrutiva (`.discreto` de excluir) |
| `--sucesso-texto` | `#006300` claro / `#0ca30c` escuro | Verde de sucesso **em texto** |

**A regra do ícone obrigatório.** Nenhum status se comunica só por cor. O
diagnóstico usa emoji (`🔴 🔥 ⚠️ ✅ ℹ️`) e a ordenação é pelo peso do ícone, não
pelo da cor (`Painel.jsx`, `PESO`). O `.selo` tem `.ok`/`.fora` com texto.
`--sucesso-texto` existe separado de `--bom` exatamente porque o verde que serve
de preenchimento não serve de letra no claro.

---

## 4. Tipografia

**Família única:** `system-ui, -apple-system, "Segoe UI", sans-serif`.

Não há webfont, não há segunda família, não há monoespaçada global. O que pede
alinhamento numérico usa `font-variant-numeric: tabular-nums` em vez de trocar de
família.

### Escala

| Papel | Tamanho | Peso | Observação |
|---|---|---|---|
| Corpo | 15px | 400 | `line-height: 1.5` |
| `h1` produto | 23px | 660 | `letter-spacing: -.015em` |
| `h2` produto | 17px | 660 | |
| `h3` produto | 14px | 660 | |
| Hero `h1` | `clamp(34px, 5.6vw, 62px)` | 680 | `letter-spacing: -.035em`, `max-width: 16ch` |
| `h2` de seção | `clamp(26px, 3.4vw, 38px)` | 660 | |
| Número de tile | 28px | 680 | `letter-spacing: -.025em` |
| Preço de plano | 34px | 700 | |
| Tabela | 13px | — | cabeçalho 12px/650 |
| Rótulo sobrescrito | 11–12,5px | 700 | caixa alta, `letter-spacing` .06–.13em |

**A regra dos pesos quebrados.** Os pesos são 520, 620, 640, 650, 660, 680 — não
400/500/600/700. Com fonte variável de sistema esses meios-termos renderizam, e a
diferença entre 620 e 650 é o que separa "rótulo" de "título" sem precisar mudar
tamanho. Arredondar tudo para a centena achata a hierarquia.

**A regra do tracking negativo cresce com o tamanho.** −0,015em nos títulos do
produto, −0,025em nos números, −0,035em no hero. Texto grande precisa de mais
aperto; texto de corpo, de nenhum.

**A regra da caixa alta curta.** `letter-spacing` largo em caixa alta é para
marcador curto (`.area`, `.super`, `.paleta-titulo`, `.marca-sub`). Nunca frase.

---

## 5. Elevação e material

O produto é plano. Profundidade vem de borda e de mudança de superfície, não de
sombra.

| Token | Claro | Escuro |
|---|---|---|
| `--sombra` | `0 1px 2px rgba(10,20,18,.04), 0 2px 8px rgba(10,20,18,.05)` | `none` |
| `--sombra-alta` | `0 12px 40px rgba(10,20,18,.12)` | `0 12px 40px rgba(0,0,0,.5)` |
| `--raio` | `12px` | cartões e tiles |
| — | `9px` | botões, inputs, nav, avisos |
| — | `999px` | selos e pílulas |

**A regra da sombra zero no escuro.** `--sombra` vira `none` no tema escuro. Sombra
preta sobre fundo quase preto não eleva nada, só suja a borda. No escuro quem
separa é `--borda` e o degrau `--page` → `--surface`.

**A regra da borda antes da sombra.** Precisa separar dois blocos? 1px de
`--borda`. Sombra entra só em coisa que flutua de verdade: tooltip (`.dica`),
inspetor em celular, moldura do hero.

**A regra dos três degraus.** `--page` (fundo) → `--surface` (cartão) →
`--surface-2` (hover, pílula, código). Um quarto degrau não existe, e **cartão
dentro de cartão é proibido** — se precisa agrupar dentro de um `.cartao`, use
borda, espaçamento ou `<h3>`.

### As superfícies de marca

`.escuro` tem duas camadas, e é o único lugar do sistema com decoração:

- `::before` — **a luz.** Dois gradientes radiais verdes (`rgba(83,239,134,.16)`
  e `.10`) nascendo atrás do conteúdo, no topo. É a metáfora da marca, literal.
- `::after` — **a malha técnica.** Grade de 64px a 3,2% de branco, com
  `mask-image` radial que a dissolve nas bordas. Sinaliza "ferramenta de dados"
  sem virar papel de parede.

Ambas em `z-index` negativo com `isolation: isolate` no pai, para não capturar
clique nem cobrir conteúdo.

---

## 6. Componentes

### Marca (`Marca.jsx`)

Lockup de símbolo PNG transparente + "NERIAH / DATA" em texto. O nome é texto, não
imagem, para acompanhar a tinta do tema. `.marca-sub` ("DATA") leva
`letter-spacing: .38em` e a cor verde. Em superfície escura, o pai recebe
`.sobre-escuro` e o nome vira branco com o sub em `--verde-vivo`.

Tudo dimensionado em `em` a partir de um `fontSize` na raiz, então
`<Marca tamanho={28} />` escala o lockup inteiro proporcionalmente.

### Botões

Um `.primario` por tela. Verde cheio, texto branco no claro — e **texto
`--preto-neriah` no escuro e sobre `.sobre-escuro`**, porque branco sobre
`#53ef86` reprova contraste. Hover: `brightness(1.08)` + `translateY(-1px)`.

`.discreto` é botão de texto, 13px, sem borda. Ação destrutiva é `.discreto` com
`color: var(--critico)` inline — nunca um botão vermelho cheio, que convida ao
clique acidental.

**Foco:** `outline: 2px solid var(--verde)` com `offset: 2px`, em input, select,
button e `a`. Nunca removido.

### Stat tiles

`.tile` com `.rotulo` (12,5px/620 em `--ink-2`), `.numero` (28px/680) e `.nota`
(12px em `--ink-muted`). O KPI que a página existe para mostrar leva `.destaque`:
borda verde, número verde e um halo de 3px em `--verde-fundo`.

`.selo` logo abaixo diz se bateu a meta — pílula com borda, `.ok` em
`--sucesso-texto` e `.fora` em `--critico`, **sempre com texto junto**.

### Gráficos (`Charts.jsx`, Recharts)

As regras estão no cabeçalho do arquivo e valem para todo gráfico novo:

1. **Uma escala por gráfico.** Nunca dois eixos y — é a forma mais fácil de
   fabricar uma correlação que não existe.
2. **Cor por entidade, não por posição.** A campanha X é verde em todos os
   gráficos, mesmo que caia do 1º para o 4º lugar no mês seguinte.
3. **Legenda a partir de 2 séries.** Com uma só, o título já a nomeia
   (`Legenda` retorna `null` abaixo de 2).
4. **Grade recessiva.** `--grid` para a malha, `--axis` para o eixo, 11,5px em
   `--ink-muted` nos rótulos.
5. **"Ver tabela" em todo gráfico.** Alternativa acessível aos dados, e a saída
   para quem quer copiar o número.
6. **Tooltip é `.dica`**, não o padrão do Recharts: mesma borda, mesmo raio,
   valor em `tabular-nums`.

Formatação centralizada: `inteiro`, `porcento`, `reais`, `formatar` — todas em
`pt-BR`. Valor nulo é `—`, nunca `0` nem `NaN`.

### Tabelas

13px, `border-collapse`, divisória em `--grid`. Cabeçalho é `sticky` com fundo
`--surface`. `td.num` alinha à direita com `tabular-nums`; `td.texto` libera a
quebra de linha e pede `min-width: 260px`. O conjunto vai dentro de `.rolagem`
(`overflow-x: auto`), porque tabela de análise não cabe em celular e esmagar
coluna é pior que rolar.

### Diagnóstico (`.diag`)

Ícone + área em caixa alta + frase. **Ordenado por urgência, não por ordem de
geração** — `PESO` em `Painel.jsx` coloca `🔴` antes de `🔥`, `⚠️`, `✅`, `ℹ️`.
Ícone com `aria-hidden`, porque a frase já diz o que ele diz.

### Canvas de cadência (React Flow)

O React Flow traz tema próprio; o `index.css` o reescreve para obedecer aos
tokens — `--axis` nas arestas, `--verde` na aresta selecionada, `--surface` nos
controles e no minimapa.

**Cores de canal** (`EtapaCadencia.jsx`, `CANAIS`): WhatsApp `#25d366`, Ligação
`#2a78d6`, E-mail `#7c5cd6`, Reunião `#099938`, Espera `#8b9995`, Decisão
`#e08a1e`, Nota `#d0567f`.

**A regra do canal não é série.** Essas sete cores são identidade de canal e
convivem com a paleta de gráfico sem competir, porque nunca aparecem no mesmo
elemento. A cor entra pela borda esquerda de 3px do nó, via `--cor-canal`, e cada
canal tem **ícone próprio** — o fluxo tem que ser legível de relance e sem depender
de cor.

Layout do editor: `position: fixed; inset: 0` em três colunas — paleta 186px,
tela elástica, inspetor 300px. Abaixo de 900px a paleta encolhe para 64px (só
ícones) e o inspetor vira sobreposição com `--sombra-alta`.

### Planos

`.plano` em `auto-fit minmax(248px, 1fr)`. O do meio leva `.destaque`: borda verde
de 2px, sombra verde suave e `.fita` ("mais escolhido") em pílula no topo. Destaque
discreto, de propósito — plano do meio gritando lê como pressão de venda.

### Vitrine da home (`Recursos.jsx`)

**A regra do conteúdo real.** A bolha de WhatsApp e os quatro cartões de cadência
na home mostram o texto e o fluxo que a análise de setembro realmente gerou —
"9 clientes travaram em preço", "6 dependem de um decisor oculto". Não é
*lorem ipsum* nem número inventado. Se a vitrine mentir, a primeira análise do
cliente vira decepção.

`.bolha-zap` imita o balão do WhatsApp (`#dcf8c6` no claro, `#075e54` no escuro,
raio `12px 12px 12px 3px`) porque o reconhecimento é o argumento.

---

## 7. Responsivo

Três quebras, todas motivadas por um layout específico:

- **980px** — `.demo-corpo` e `.duas-colunas` viram uma coluna; `.entrada` deixa de
  ser dividida.
- **880px** — a barra lateral vira barra horizontal rolável no topo e `.app` passa
  a uma coluna.
- **900px / 760px / 620px** — editor de cadência, setas da vitrine e rótulo do
  botão flutuante do WhatsApp.

Grades que usam `auto-fit`/`minmax` (`.grade`, `.planos`, `.passos`, `.cartoes`,
`.palco-fluxo`, `.tira`) **não têm media query** e não devem ganhar uma: já
respondem à largura disponível.

---

## 8. Faça e não faça

### Faça

- Use `--verde` e deixe o tema resolver o valor.
- Use `--verde-vivo` **apenas** sobre superfície escura.
- Use `tabular-nums` em qualquer número que apareça em coluna.
- Dê ícone **e** texto a todo status.
- Mantenha o produto claro e os momentos de marca escuros.
- Ponha `aria-hidden` em ícone decorativo e mantenha o `outline` de foco.
- Comente no CSS a decisão que parece errada mas não é (há três exemplos no
  arquivo: o `display: block` das barras, o `overflow: hidden` da entrada, o
  motivo de `.escuro` não poder carregá-lo).
- Formate em `pt-BR` e mostre `—` para nulo.

### Não faça

- Não escreva hex em componente — use token (as três exceções estão em §3).
- Não troque uma cor de série sem refazer a medição de daltonismo.
- Não use `--verde-vivo` sobre branco, nem texto branco sobre `--verde-vivo`.
- Não aninhe `.cartao` dentro de `.cartao`.
- Não ponha segundo eixo y num gráfico.
- Não adicione webfont.
- Não arredonde os pesos quebrados para 400/500/600/700.
- Não comunique estado só por cor.
- Não use sombra para separar no tema escuro.
- Não escreva frase em caixa alta com `letter-spacing` largo.
- Não use número falso na vitrine da home.
- Não crie CSS por página — o sistema é um arquivo só, por seção temática.

---

## 9. Dívidas conhecidas

Registradas porque fingir que não existem é pior que admiti-las:

- **Não há validador de paleta no repositório.** Os números de ΔE da §3 vieram de
  uma medição feita durante o desenvolvimento, mas o script não foi versionado.
  Trocar uma cor de série hoje depende de refazer a medição à mão. Versionar um
  `scripts/validate_palette.js` que rode em CI resolveria.
- **Não há teste visual automatizado.** As telas foram conferidas com Playwright
  pontualmente, sem baseline de regressão.
- **A escala de espaçamento é implícita.** Os valores (4, 6, 9, 11, 14, 16, 18,
  22, 26px) são consistentes na prática, mas não existem como token. São o
  candidato mais óbvio a virar `--esp-1`…`--esp-6`.
- **`font-size` em `px`.** Funciona, mas ignora o ajuste de tamanho de fonte do
  navegador. Migrar para `rem` é acessibilidade real, não purismo.
