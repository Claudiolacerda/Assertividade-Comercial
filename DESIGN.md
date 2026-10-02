---
name: Neriah Data
description: Cruza relatório de tráfego com planilha comercial e diz onde o dinheiro trava.
colors:
  verde: "#08812f"
  verde-dark: "#53ef86"
  verde-vivo: "#53ef86"
  verde-fundo: "#e8fbef"
  verde-fundo-dark: "#0f2318"
  preto-neriah: "#040d0c"
  page: "#f7f9f8"
  page-dark: "#040d0c"
  surface: "#ffffff"
  surface-dark: "#0b1513"
  surface-2: "#f1f4f3"
  surface-2-dark: "#142220"
  ink: "#0a1412"
  ink-dark: "#ffffff"
  ink-2: "#4c5a57"
  ink-2-dark: "#b9c7c3"
  ink-muted: "#66726f"
  ink-muted-dark: "#8b9995"
  grid: "#e4eae8"
  grid-dark: "#1d2b28"
  axis: "#c4cecb"
  axis-dark: "#2c3c39"
  series-1: "#099938"
  series-1-dark: "#0db243"
  series-2: "#2a78d6"
  series-2-dark: "#3987e5"
  series-3: "#e87ba4"
  series-3-dark: "#d55181"
  bom: "#0ca30c"
  atencao: "#fab219"
  serio: "#ec835a"
  critico: "#d03b3b"
  sucesso-texto: "#006300"
  sucesso-texto-dark: "#0ca30c"
  atencao-texto: "#946603"
  atencao-texto-dark: "#fab219"
  serio-texto: "#a4471d"
  serio-texto-dark: "#ec835a"
  critico-texto: "#c0302f"
  critico-texto-dark: "#d96060"
  canal-whatsapp: "#25d366"
  canal-whatsapp-texto: "#16803e"
  canal-ligacao: "#2a78d6"
  canal-ligacao-texto: "#266fc7"
  canal-email: "#7c5cd6"
  canal-email-texto: "#7959d5"
  canal-reuniao: "#099938"
  canal-reuniao-texto: "#08812f"
  canal-espera: "#8b9995"
  canal-espera-texto: "#64726e"
  canal-decisao: "#e08a1e"
  canal-decisao-texto: "#9e6215"
  canal-nota: "#d0567f"
  canal-nota-texto: "#c73768"
typography:
  display:
    fontFamily: "system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "clamp(34px, 5.6vw, 62px)"
    fontWeight: 680
    lineHeight: 1.04
    letterSpacing: "-0.035em"
  headline:
    fontFamily: "system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "clamp(26px, 3.4vw, 38px)"
    fontWeight: 660
    lineHeight: 1.12
    letterSpacing: "-0.028em"
  title:
    fontFamily: "system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "23px"
    fontWeight: 660
    lineHeight: 1.2
    letterSpacing: "-0.015em"
  metric:
    fontFamily: "system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "28px"
    fontWeight: 680
    lineHeight: 1.1
    letterSpacing: "-0.025em"
    fontFeature: "tnum"
  body:
    fontFamily: "system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "12px"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "0.13em"
rounded:
  chip: "4px"
  control: "9px"
  card: "12px"
  panel: "14px"
  frame: "16px"
  pill: "999px"
components:
  button-primary:
    backgroundColor: "{colors.verde}"
    textColor: "#ffffff"
    rounded: "{rounded.control}"
    padding: "11px 16px"
    height: "44px"
    typography: "{typography.body}"
  button-primary-hover:
    backgroundColor: "{colors.verde}"
    textColor: "#ffffff"
  button-primary-dark:
    backgroundColor: "{colors.verde-dark}"
    textColor: "{colors.preto-neriah}"
    rounded: "{rounded.control}"
    padding: "9px 14px"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "9px 14px"
  button-secondary-hover:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.ink}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.control}"
    padding: "5px 9px"
  cta-hero:
    backgroundColor: "{colors.verde-vivo}"
    textColor: "{colors.preto-neriah}"
    rounded: "10px"
    padding: "13px 24px"
  cta-hero-outline:
    backgroundColor: "transparent"
    textColor: "#ffffff"
    rounded: "10px"
    padding: "13px 24px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
    width: "100%"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "18px"
  tile:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "15px 16px"
  tile-featured:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.verde}"
    rounded: "{rounded.card}"
    padding: "15px 16px"
  nav-item:
    backgroundColor: "transparent"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.control}"
    padding: "9px 11px"
  nav-item-active:
    backgroundColor: "{colors.verde-fundo}"
    textColor: "{colors.verde}"
    rounded: "{rounded.control}"
    padding: "9px 11px"
  cadence-node:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "10px"
    padding: "10px 12px"
    width: "210px"
---

# Design System: Neriah Data

> Documento descritivo, gerado a partir do código que já está em produção
> (`frontend/src/index.css`, 1175 linhas, mais os componentes em `frontend/src/`).
> Nada aqui é aspiracional: cada token, classe e medida citada existe no
> repositório. O frontmatter acima é a camada normativa — a prosa explica onde e
> por quê, não redefine valor.

## Overview

**Creative North Star: "A Luz Sobre o Dado"**

Neriah significa *luz*. A marca nasce do escuro — `#040D0C`, o fundo da própria
logo — e o verde é a luz que revela o dado. Essa não é uma metáfora de
apresentação: é a regra que governa qual superfície cada tela usa.

Momentos de marca são escuros. Site público e tela de entrada, onde a pessoa
ainda está decidindo se confia no produto, usam o preto da logo com um brilho
verde nascendo atrás do conteúdo e uma malha técnica dissolvida nas bordas. O
produto é claro. Painel, análises, tabelas e carteira — onde se lê número o dia
inteiro — usam tinta escura sobre fundo claro, porque é assim que número se lê.

A troca de superfície marca a passagem de "isto é uma marca" para "isto é uma
ferramenta". A densidade acompanha: 15px de corpo, 13px em tabela, botão de 9px
de raio. É densidade de ferramenta de trabalho, não de página de vendas. O
sistema é deliberadamente plano — a profundidade vem de borda de 1px e de troca
de superfície, quase nunca de sombra.

**Key Characteristics:**

- Verde como único acento de marca; não existe segunda cor de marca.
- Tipografia de sistema, sem webfont — a primeira pintura importa mais.
- Superfícies planas, bordas de 1px, sombra zerada no tema escuro.
- Números sempre em `tabular-nums`, para alinharem na vertical.
- Claro e escuro completos, por `prefers-color-scheme` e por `data-theme`.
- Nenhum estado se comunica só por cor: sempre ícone ou texto junto.

## Colors

Uma paleta de um acento só, sobre um neutro levemente esverdeado, com três cores
de série medidas para daltonismo e quatro de status.

### Primary

- **Verde Neriah** (`verde` / `verde-dark`): o acento da marca e a única cor que
  significa "isto importa". Botão primário, aba ativa, item de navegação ativo,
  borda do KPI em destaque, link. **Troca de valor por tema** — veja a regra
  abaixo. O tom claro é `#08812f` e não o verde da logo: medido, dá 5,01:1 como
  texto sobre branco e 5,01:1 para o branco escrito sobre ele, atendendo os dois
  sentidos de uso.
- **Verde da Logo** (`verde-vivo`): o verde literal do arquivo da logo. Vive
  exclusivamente sobre superfície escura: CTA do hero, números da tira de prova,
  palavra iluminada do título, sub-marca "DATA" no lockup escuro.
- **Lavagem Verde** (`verde-fundo` / `verde-fundo-dark`): realce suave sem peso.
  Fundo do item de navegação ativo, círculo do número do passo, halo do tile em
  destaque, área de arraste quando o arquivo está sobre ela.

### Neutral

- **Preto Neriah** (`preto-neriah`): o fundo da logo, e por isso o preto da
  marca. É o fundo das superfícies de marca e do tema escuro inteiro. Não é
  `#000`, e a diferença é o que o faz parecer tinta e não ausência.
- **Página** (`page` / `page-dark`): o fundo onde tudo repousa.
- **Superfície** (`surface` / `surface-dark`): cartões, tiles, gráficos, barra
  lateral, campos.
- **Superfície Elevada** (`surface-2` / `surface-2-dark`): hover de linha de
  tabela, pílula de dia, trecho de código, botão secundário em hover.
- **Tinta** (`ink` / `ink-dark`): o que se lê — título, valor, frase de
  diagnóstico.
- **Tinta de Apoio** (`ink-2` / `ink-2-dark`): rótulo, parágrafo secundário,
  item de navegação inativo.
- **Tinta Apagada** (`ink-muted` / `ink-muted-dark`): metadado, nota sob o
  número, legenda de eixo.
- **Malha** (`grid` / `grid-dark`) e **Eixo** (`axis` / `axis-dark`): divisória
  de tabela, grade de gráfico, aresta do canvas, borda tracejada do arraste.

### Secondary

As três cores de série dos gráficos. Não são cores de marca: são um alfabeto de
distinção.

- **Série 1 — Verde** (`series-1` / `series-1-dark`)
- **Série 2 — Azul** (`series-2` / `series-2-dark`)
- **Série 3 — Magenta** (`series-3` / `series-3-dark`)

### Tertiary

Status, sempre acompanhados de ícone ou texto, e as sete cores de canal da
cadência (`canal-*`), que identificam meio de contato — WhatsApp, Ligação,
E-mail, Reunião, Espera, Decisão, Nota.

- **Bom** (`bom`), **Atenção** (`atencao`), **Sério** (`serio`),
  **Crítico** (`critico`): escala de severidade do diagnóstico e das metas.
- **Tons de texto dos status** (`sucesso-texto`, `atencao-texto`, `serio-texto`,
  `critico-texto`): existem separados dos tons de preenchimento porque a cor que
  funciona como área não funciona como letra. O amarelo de atenção fica em
  1,83:1 escrito sobre branco; o tom de texto correspondente, em 5,05:1.

### Named Rules

**A Regra do Verde por Superfície.** O verde da logo é lindo sobre preto e
ilegível sobre branco — reprova contraste para texto. Por isso o acento troca de
valor por tema (`verde` ≠ `verde-dark`) enquanto `verde-vivo` fica fixo e só
aparece sobre escuro. Teste: se um elemento usa `verde-vivo` e o fundo dele não
é `preto-neriah` ou `.escuro`, é erro.

**A Regra do Par Medido.** Nenhuma cor entra no sistema por aparência. Cada
token de texto foi ajustado em HSL — matiz e saturação preservados, luminância
descida até passar — e conferido contra todos os fundos onde aparece. A
verificação no navegador percorre cada nó de texto das telas nos dois temas e
hoje devolve **zero reprovações**, contra 16 pares reprovados no claro e 1 no
escuro antes desta passagem.

**A Regra da Paleta Medida.** As seis cores de série foram escolhidas e
*medidas*, não aprovadas no olho. O pior par de qualquer combinação, simulado
para protanopia, deuteranopia e tritanopia, fica em ΔE 13,0 no claro e 8,7 no
escuro; o mínimo exigido é 8. Uma tentativa anterior usava verde + laranja e
reprovou com ΔE 4,3 em protanopia — por isso o terceiro slot é magenta e não o
laranja que seria a escolha natural. Trocar qualquer um dos seis valores exige
refazer a medição.

**A Regra dos Três Níveis de Tinta.** Existem `ink`, `ink-2` e `ink-muted`, e só.
Um quarto nível não acrescenta hierarquia, só reduz contraste.

**A Regra do Ícone Obrigatório.** Nenhum estado se comunica apenas por cor. O
diagnóstico usa emoji e é ordenado pelo peso do ícone, não pelo da cor. O selo de
meta traz texto. Cor é reforço, nunca o portador da informação.

**A Regra do Token.** Nenhuma cor literal em componente, com três exceções
justificadas: cor de canal da cadência, o verde do WhatsApp (`#25d366`, marca de
terceiro) e as superfícies escuras do site, que precisam de `rgba(255,255,255,α)`
para transparência sobre o preto.

## Typography

**Display Font:** Archivo Variable (reserva: `system-ui`, `-apple-system`, `Segoe UI`)
**Body Font:** a mesma. Há uma única família em todo o sistema
**Label/Mono Font:** nenhuma; alinhamento numérico vem de `tabular-nums`
**Ícones:** desenhados, em `components/Icones.jsx` — caixa de 16px, traço 1,6,
pontas arredondadas, sempre em `currentColor`

**Character:** uma grotesca de trabalho, desenhada para alta densidade de
informação. Tem personalidade sem chamar atenção para si, que é o que um painel
de números pede.

**A Regra da Fonte Variável.** Archivo é variável, e isso não é preferência: os
pesos deste sistema são 520, 620, 650, 660 e 680, e uma fonte estática
arredondaria todos para a centena mais próxima, achatando a hierarquia que a
Regra dos Pesos Quebrados existe para proteger. Medido: 7 pesos produzem 7
larguras distintas. Trocar por uma fonte sem eixo de peso contínuo quebra o
sistema inteiro, não só o visual.

**Auto-hospedada, nunca por CDN.** Entra pelo pacote, com só o eixo de peso e os
subsets declarados com unicode-range: o navegador baixa 35 KB de latino e só
busca o latin-ext se algum glifo exigir. O preload é emitido pelo código, não
pelo HTML, porque só o bundler sabe o nome final do arquivo; sem ele a troca de
fonte aconteceria depois do layout pronto e devolveria o salto que o sistema
zerou.

### Hierarchy

- **Display** (680, `clamp(34px, 5.6vw, 62px)`, 1.04, `-0.035em`): título do
  hero, limitado a `16ch` para não virar parágrafo.
- **Headline** (660, `clamp(26px, 3.4vw, 38px)`, 1.12, `-0.028em`): título de
  seção do site público.
- **Title** (660, 23/17/14px, 1.2, `-0.015em`): `h1`, `h2` e `h3` dentro do
  produto. A escala é curta porque a hierarquia real vem do cartão, não do
  tamanho.
- **Metric** (680, 28px, 1.1, `-0.025em`, `tnum`): o número do tile. 34px/700 na
  variante de preço de plano.
- **Body** (400, 15px, 1.5): corpo geral. 13px em tabela, 13,5px em frase de
  diagnóstico.
- **Label** (700, 11–12,5px, `0.06–0.13em`, caixa alta): marcador curto —
  sobretítulo de seção, área do diagnóstico, título da paleta, sub-marca.

### Named Rules

**A Regra dos Pesos Quebrados.** Os pesos são 520, 620, 640, 650, 660, 680 — não
400/500/600/700. Com fonte variável de sistema esses meios-termos renderizam, e a
diferença entre 620 e 650 é o que separa "rótulo" de "título" sem mudar tamanho.
Arredondar para a centena achata a hierarquia.

**A Regra do Aperto Proporcional.** O `letter-spacing` negativo cresce com o
tamanho: `-0.015em` nos títulos do produto, `-0.025em` nos números, `-0.035em` no
hero. Texto de corpo não recebe nenhum.

**A Regra da Caixa Alta Curta.** Caixa alta com `letter-spacing` largo é para
marcador de uma ou duas palavras. Nunca frase.

**A Regra do Número Tabular.** Todo número que possa aparecer empilhado — coluna
de tabela, valor de tooltip, dia da cadência, caminho da janela demonstrativa —
leva `font-variant-numeric: tabular-nums`.

## Layout

O produto usa uma grade de duas colunas: barra lateral fixa de 236px e conteúdo
elástico limitado a 1320px. O site público usa um contêiner centrado de 1140px
com 24px de calha.

A densidade é de ferramenta. Conteúdo com 26px de respiro superior e 30px
lateral; cartão com 18px internos; tile com 15px/16px; célula de tabela com
8px/10px. Seção de site público respira muito mais: 86px verticais, 76–88px no
hero.

Grades de repetição usam `auto-fit` com `minmax` e **não têm media query**:
`.grade.dois` (380px), `.grade.tiles` (210px), `.planos` (248px), `.passos`
(260px), `.cartoes` (300px), `.palco-fluxo` (210px), `.tira` (190px). Elas
respondem à largura disponível sozinhas.

As quebras explícitas existem só onde um layout específico precisa mudar de
forma:

- **980px** — o corpo da demonstração e as seções de duas colunas viram uma; a
  tela de entrada deixa de ser dividida.
- **880px** — a barra lateral vira barra horizontal rolável no topo e o app passa
  a uma coluna.
- **900px** — no editor de cadência a paleta encolhe para 64px (só ícones) e o
  inspetor vira sobreposição.
- **760px / 620px** — setas da vitrine somem; o botão flutuante do WhatsApp perde
  o rótulo e fica só ícone.

**A Regra da Grade Que Se Vira.** Antes de escrever media query, pergunte se
`auto-fit` + `minmax` resolve. Nas sete grades acima resolveu, e cada media query
não escrita é uma quebra a menos para manter.

**Dívida conhecida:** a escala de espaçamento é consistente na prática (4, 6, 9,
11, 14, 16, 18, 22, 26px) mas não existe como token — por isso não aparece no
frontmatter. Promovê-la a `spacing` é o próximo passo óbvio do sistema.

## Elevation & Depth

O sistema é plano. A profundidade vem de três degraus de superfície —
`page` → `surface` → `surface-2` — e de uma borda de 1px. Sombra é exceção, não
ferramenta de hierarquia.

### Shadow Vocabulary

- **Repouso**: aposentada. Cartão, tile e gráfico declaravam borda de 1px *e*
  sombra larga ao mesmo tempo — o cartão fantasma. Hoje a elevação é declarada
  uma vez só, pela borda.
- **Flutuante** (`0 12px 40px rgba(10,20,18,.12)` / `rgba(0,0,0,.5)` no escuro):
  só para o que flutua de verdade — tooltip, inspetor sobreposto no celular.
- **Moldura do hero** (`0 30px 90px rgba(0,0,0,.55), 0 0 0 1px rgba(83,239,134,.07)`):
  a única sombra dramática do sistema, e só porque o painel demonstrativo precisa
  parecer um objeto sobre a superfície de marca.
- **CTA verde** (`0 8px 28px rgba(83,239,134,.26)`): halo verde sob o botão do
  hero. Exclusivo de superfície escura.

### Named Rules

**A Regra da Sombra Zerada no Escuro.** No tema escuro a sombra de repouso vira
`none`. Sombra preta sobre fundo quase preto não eleva nada — só suja a borda.
Quem separa no escuro é a borda e o degrau de superfície.

**A Regra da Borda Antes da Sombra.** Precisa separar dois blocos? 1px de borda.
Sombra entra só quando o elemento realmente flutua sobre o conteúdo.

**A Regra da Elevação Única.** Borda ou sombra, nunca os dois no mesmo elemento.
Borda de 1px sob sombra larga não soma profundidade, só suja o contorno.

**A Regra do Cartão Sem Filho.** Cartão dentro de cartão é proibido. Para agrupar
dentro de um cartão, use borda, espaçamento ou um `h3`. O terceiro degrau de
superfície é o limite do sistema.

### As superfícies de marca

A classe `.escuro` é o único lugar com decoração, e ela tem duas camadas em
`z-index` negativo sob `isolation: isolate`:

- **A luz** — uma fonte com direção, no eixo de 100° do facho (ver Components).
  Substituiu dois gradientes radiais centrados: aqueles eram brilho de SaaS, que
  não dizia de onde vinha nem o que iluminava. Este tem origem, e a origem é a
  mesma do feixe.
- **A malha técnica** — grade de 64px a 3,2% de branco, com máscara radial que a
  dissolve nas bordas. Diz "ferramenta de dados" sem virar papel de parede.

## Shapes

O raio cresce com a área do elemento: 4px em chip de código, 9px em controle
(botão, campo, item de navegação, aviso), 12px em cartão e tile, 14px em painel
de seção e plano, 16px na moldura do hero, e `999px` em pílula e selo.

Borda é sempre 1px, na cor `borda` (10% da tinta sobre o fundo). Há três usos de
borda mais espessa, e todos carregam significado: 3px à esquerda no cartão de
recurso e no nó de cadência (identidade de canal), 2px no plano em destaque, e
1,5px tracejada na área de arraste — tracejada porque é a convenção universal de
"solte aqui".

**A Regra do Raio Proporcional.** Elemento pequeno, raio pequeno. Um botão com
raio de cartão parece inflado; um cartão com raio de botão parece rígido.

**A Regra da Barra de Canal.** A borda esquerda de 3px é reservada para
identidade — canal da cadência, destaque de recurso, severidade de aviso. Não é
decoração, e usá-la como tal destrói o sinal.

## Components

### Buttons

- **Shape:** cantos suaves (9px), 1px de borda, transição de 140ms em fundo,
  borda e posição.
- **Primary:** verde cheio com texto branco no claro — e texto `preto-neriah` no
  escuro e sobre superfície de marca, porque branco sobre `#53ef86` reprova
  contraste. Padding 9px/14px, peso 620. **Um por tela.**
- **Hover / Focus:** o primário ganha `brightness(1.08)` e sobe 1px; os demais
  trocam o fundo para a superfície elevada. Foco é sempre
  `outline: 2px solid` em verde com 2px de deslocamento, em botão, campo, select
  e link — nunca removido.
- **Secondary:** superfície com borda, tinta normal. O botão padrão do sistema.
- **Ghost:** `.discreto` — texto puro, 13px, sem borda, 5px/9px de padding.
  **Ação destrutiva é um ghost com cor crítica**, nunca um botão vermelho cheio,
  que convida ao clique acidental.
- **CTA do hero:** variante exclusiva de superfície escura — verde da logo, texto
  preto, 10px de raio, 13px/24px, com halo verde. A versão vazada usa borda
  branca a 22%.

### Cards / Containers

- **Corner Style:** 12px.
- **Background:** superfície sobre página; no site público, o cartão inverte
  (usa `page` quando a seção é clara) para manter sempre um degrau de contraste.
- **Shadow Strategy:** sombra de repouso no claro, nenhuma no escuro. Ver
  Elevation & Depth.
- **Border:** 1px.
- **Internal Padding:** 18px (cartão), 15px/16px (tile), 20–24px (cartão de
  seção).

### Inputs / Fields

- **Style:** superfície com borda de 1px, 9px de raio, 10px/12px de padding,
  largura total. Rótulo acima, 13px, peso 620, em tinta de apoio.
- **Focus:** contorno verde de 2px com 2px de deslocamento.
- **Arraste de arquivo:** borda tracejada de 1,5px que vira sólida e verde quando
  preenchida, e ganha lavagem verde quando o arquivo está sobre ela.

### Navigation

- **Produto:** barra lateral de 236px com o lockup no topo e o nome da empresa
  sob ele. Item em 14px/520, 9px de raio; hover troca a superfície; ativo ganha
  lavagem verde, tinta verde e peso 650. No celular vira barra horizontal
  rolável.
- **Site público:** topo fixo com desfoque de 12px sobre o preto a 72%, links em
  branco a 72% que acendem no hover.
- **Abas:** sublinhado de 2px, verde quando ativa, com peso maior. Rolagem
  horizontal quando não cabem.

### Stat Tiles

A unidade de leitura do painel: rótulo (12,5px/620 em tinta de apoio), número
(28px/680) e nota (12px em tinta apagada). O KPI pelo qual a página existe leva a
variante em destaque — borda verde, número verde e um halo de 3px em lavagem
verde. Abaixo, um selo em pílula diz se bateu a meta, com texto, nunca só cor.

### Charts

- **Shape:** cartão de 12px com título, subtítulo em tinta apagada e legenda
  acima da área de plotagem.
- **Regras invioláveis:** uma escala por gráfico (nunca dois eixos y); cor por
  entidade e não por posição no ranking; legenda a partir de duas séries; grade
  recessiva; tooltip com a identidade do sistema, não a do Recharts; e **"ver
  tabela" em todo gráfico**, como alternativa acessível e como saída para quem
  quer copiar o número.
- **Formatação:** centralizada em `pt-BR`. Nulo é `—`, nunca `0` nem `NaN`.

### Tables

13px, divisória em malha, cabeçalho fixo com fundo de superfície. Coluna numérica
alinhada à direita em `tabular-nums`; coluna de texto libera a quebra com 260px
mínimos. Tudo dentro de um contêiner com rolagem horizontal — tabela de análise
não cabe em celular, e rolar é melhor que esmagar coluna.

### Cadence Node (componente de assinatura)

O nó do canvas de cadência, e o componente mais distintivo do sistema. Cartão de
210px com borda esquerda de 3px na cor do canal, raio de 10px. No topo, o canal
com ícone à esquerda e a pílula do dia (`D+2`) à direita; abaixo, título em
13px/640 e descrição em 11,5px limitada a três linhas.

Cada um dos sete canais tem cor **e** ícone próprios, porque o fluxo precisa ser
legível de relance e sem depender de cor. As alças de conexão herdam a cor do
canal, e as arestas levam ponta de seta — sem ela não dá para ler a direção do
fluxo.

**A Regra das Duas Cores de Canal.** Cada canal carrega `cor` e `corTexto`. A
primeira preenche a barra e a alça, onde 3:1 basta por serem elementos não
textuais; a segunda escreve o rótulo, onde são exigidos 4,5:1. O verde do
WhatsApp fica em 1,98:1 como letra: bom na barra, ilegível escrito. O React Flow traz tema próprio, e o sistema o reescreve para obedecer aos
tokens: aresta em eixo, aresta selecionada em verde, controles e minimapa em
superfície.

### Segmented control

Alternador de duas opções mutuamente exclusivas (`Resumo | Completo` no relatório
de WhatsApp). Trilho em superfície elevada com 9px de raio e 3px de respiro
interno; a opção ativa ganha a superfície branca, peso 650 e uma sombra de 1px.
Substitui a caixa de seleção solta que ficava longe do que ela reescrevia.

### Prévia do WhatsApp

A mensagem renderizada como o cliente vai receber — balão verde, negrito de
verdade no lugar dos asteriscos, hora — dentro de um palco em superfície
elevada. **Sem rolagem interna:** ver a mensagem inteira de uma vez é o que
impede mandar a coisa errada. "Editar texto" troca o balão pelo campo de edição;
o padrão é ver, não editar.

### Cartão de destaque do diagnóstico

A oportunidade principal, promovida acima dos KPIs: lavagem verde, borda verde,
ícone de nível e a frase em 16px/560. É a linha que paga a assinatura, e antes
ela tinha o mesmo peso de uma observação informativa no meio de dezoito.

### Base técnica

React 18 com TypeScript, Vite, e Tailwind v4 com o contrato de tokens do shadcn.

**A Regra do Preflight Ausente.** O reset do Tailwind **não** é importado. Ele
zera margens, tamanhos de fonte, bordas e estilos de lista que este CSS assume
existirem, e importá-lo recriaria o design. Entram só o tema e as utilidades, e
as utilidades vivem na camada `utilities`, que perde para CSS sem camada: o
sistema semântico em português continua vencendo por construção.

**O contrato do shadcn não traz valores novos.** `--primary` aponta para o verde
do Neriah, `--background` para a página, `--radius` para o raio do cartão,
`--chart-1..3` para as séries já medidas para daltonismo. Um componente do
shadcn colocado aqui nasce com a cor certa sem ninguém redesenhar nada, e no
tema escuro `--primary-foreground` vira o preto da marca, porque a Regra do
Verde por Superfície vale também para ele.

### Movimento

Uma curva e três durações, e cada duração significa uma distância.

| Token | Valor | Para quê |
|---|---|---|
| `--curva` | `cubic-bezier(0.16, 1, 0.3, 1)` | Toda chegada. Desaceleração natural, sem salto elástico |
| `--t-feedback` | 130ms | Hover, cor, foco — o que responde ao dedo |
| `--t-estado` | 210ms | Aba, alternador, prévia — o que muda de estado |
| `--t-camada` | 300ms | Inspetor, sanfona — o que se move no espaço |

**A Regra da Saída Mais Rápida.** Pressionar um botão dura 70ms, metade de
qualquer outra coisa. Esperar para algo sumir lê como latência, nunca como
cuidado.

**A Regra do Movimento Que Explica.** Cada animação do sistema responde a uma
pergunta: o indicador de aba diz *de onde para onde* você foi; o inspetor entra
pela direita porque é de lá que ele vem; a seta do recolher gira para dizer em
que estado o botão está. Movimento que não responde a nada é dívida.

**A Regra da Entrada Onde Algo Chega.** O produto não tem coreografia de
carregamento. A única entrada encadeada é a dos KPIs, porque ali o conteúdo
realmente chega depois da análise — 240ms cada, 35ms de intervalo, **teto de
175ms no atraso total**. Passar disso deixa de ser chegada e vira espera.

**A Regra do Padrão Visível.** Nenhuma animação parte de invisível por JavaScript.
Se o script falhar, o conteúdo está lá.

Técnicas: o indicador de aba e o polegar do alternador são posicionados por
**medição** (`useLayoutEffect` + `offsetLeft`/`offsetWidth`), nunca por cálculo —
os rótulos têm larguras diferentes e a barra rola no celular. Ambos usam
`translateX` + `scaleX` sobre um elemento de 1px, em vez de animar `width`, que
é propriedade de layout. A sanfona usa `grid-template-rows: 0fr → 1fr`, a única
forma de animar altura automática sem medir nada e sem travar num `max-height`
chutado.

Medido: 58 fps no desktop e 56 no celular durante troca de aba mais sanfona,
com `transform`, `opacity` e cor apenas. Nenhuma biblioteca de animação.

**Movimento reduzido.** Sai todo deslocamento no espaço: varredura, entrada
encadeada, deslizes, viagem do indicador. **Fica o feedback que confirma uma
ação** — o afundar do botão, a cor, a opacidade. A ordem das regras importa:
pressionar é também estar com o mouse em cima, então a regra de `:hover` precisa
vir **antes** da de `:active`, ou o botão fica mudo para quem mais precisa da
confirmação.

### O Campo de Fluxo (FlowField)

O fundo do Hero. Um campo vetorial de ruído move 600 partículas que deixam
rastros luminosos, em canvas. Vem do Kokonut UI (MIT), adaptado.

**Só no Hero.** Nenhuma outra seção recebe o efeito, e isso é regra, não
acidente: a página tem sete seções e exatamente um canvas.

**A Regra do Véu.** O campo fica atrás de texto, e isso é perigoso. Medido: um
risco de luz passando atrás do parágrafo do Hero derrubava o contraste para
**1,94:1**, contra os 4,5:1 exigidos — e a média ficava em 8,85, o que esconde o
problema de qualquer verificador que olhe só a média. O véu (`.fundo-hero::after`)
escurece a coluna central, onde vivem título, parágrafo e botões, e deixa o
campo aparecer nas laterais e embaixo. Depois dele: 7,28:1 no pior pixel.
A vinheta que vem no componente faz o contrário, protege as bordas e expõe o
centro, então ela não substitui o véu.

**Camadas.** O campo é a textura mais funda, em `z-index: -3`; a luz de
`.escuro` vem acima dele (-2) e a malha técnica acima dela (-1). O conteúdo do
Hero fica sobre os três.

**Irmão, nunca envoltório.** O wrapper do componente tem `overflow: hidden`, e o
cabeçalho do site é `position: sticky` dentro do mesmo bloco. Envolver o Hero no
componente mataria o menu grudado.

**O que foi corrigido no componente.** O `ctx.scale(dpr, dpr)` era cumulativo:
cada `resize` multiplicava a escala anterior. Ele media a janela em vez do
elemento. E não parava nunca: agora respeita `prefers-reduced-motion` com um
quadro estático, para quando sai da tela e para quando a aba fica oculta.

**Convivência com o facho.** São dois efeitos no mesmo Hero, e a Regra do
Momento Único diz que apenas um pode ser protagonista. O campo roda em
`sparse`, com intensidade 0,5 e ponto de 1px, para ser cenário: o facho segue
sendo o momento. Subir a densidade ou a intensidade inverte essa relação e
quebra a regra.

### O Facho — o momento de assinatura

O único efeito extraordinário do sistema, e ele vive em um lugar só: o painel
demonstrativo da hero. Um feixe de luz entra pela esquerda, varre o painel uma
vez em 1,75s e sai. Onde ele passa, o dado **resolve**: cada número sai de
`blur(7px)` dessaturado para nítido e colorido, com um deslocamento de 5px.

**Por que existe.** Neriah significa luz, e o produto não cria o dado — ele
revela o que já estava na planilha. O facho executa essa frase na frente de quem
chega, sem precisar escrevê-la. Os números que ele acende são reais, de setembro
de 2026.

**Como funciona.** `@property --facho` registra uma porcentagem como tipo
animável; sem esse registro o navegador não interpola uma posição dentro de um
gradiente e o feixe salta em vez de deslizar. O gradiente é assimétrico de
propósito: rastro curto atrás (−6%), para não lavar o dado recém-revelado, e
halo longo à frente (+22%), caindo sobre o que ainda está borrado.

**A Regra do Feixe Calculado.** O feixe anda em velocidade **linear**, e é isso
que torna a posição dele previsível: o instante em que cada elemento acende é
calculado a partir da posição horizontal dele, resolvendo a geometria do
`linear-gradient(100deg)` num box de 960×470 (comprimento da linha 1027px). Com
easing, os tempos deixam de ser calculáveis e o feixe descola do que ele acende
— foi exatamente o que aconteceu na primeira versão. Mexer no ângulo, na
duração ou no tamanho do painel exige recalcular os atrasos.

**Degradação.** Sem `@property`, o painel nasce aceso e nada se perde.
Com `prefers-reduced-motion: reduce`, idem — nenhuma varredura.

**A Regra do Momento Único.** Existe **um** momento extraordinário no produto
inteiro, e é este. Um segundo efeito dessa classe em qualquer outra tela não
soma: divide a atenção e transforma assinatura em maneirismo.

### Brand Lockup

Símbolo PNG transparente — o mesmo arquivo serve em superfície clara e escura —
mais "NERIAH / DATA" em texto, para acompanhar a tinta do tema em vez de ficar
preso a um branco de imagem. A sub-marca "DATA" leva `0.38em` de
`letter-spacing`. Tudo dimensionado em `em` a partir de um tamanho na raiz, então
o lockup inteiro escala proporcionalmente com um único número.

## Do's and Don'ts

### Do:

- **Do** usar o token do acento e deixar o tema resolver o valor.
- **Do** reservar o verde da logo para superfície escura, sempre.
- **Do** aplicar `tabular-nums` em qualquer número que possa aparecer empilhado.
- **Do** acompanhar todo estado de ícone ou texto, nunca só de cor.
- **Do** manter o produto claro e os momentos de marca escuros.
- **Do** preferir `auto-fit` + `minmax` a uma media query nova.
- **Do** separar com borda de 1px antes de pensar em sombra.
- **Do** oferecer "ver tabela" em todo gráfico.
- **Do** formatar em `pt-BR` e mostrar `—` para valor nulo.
- **Do** comentar no CSS a decisão que parece errada mas não é — há três
  exemplos no arquivo, e cada um já evitou uma correção equivocada.

### Don't:

- **Don't** escrever hex em componente; as três exceções estão em Colors.
- **Don't** trocar uma cor de série sem refazer a medição de daltonismo.
- **Don't** pôr o verde da logo sobre branco, nem texto branco sobre ele.
- **Don't** aninhar cartão dentro de cartão.
- **Don't** usar segundo eixo y num gráfico.
- **Don't** trocar Archivo por uma fonte sem eixo de peso contínuo.
- **Don't** servir a fonte por CDN de terceiro nem remover o preload.
- **Don't** arredondar os pesos quebrados para 400/500/600/700.
- **Don't** usar sombra para separar no tema escuro.
- **Don't** escrever frase em caixa alta com `letter-spacing` largo.
- **Don't** usar a borda esquerda de 3px como decoração — ela carrega identidade.
- **Don't** remover o contorno de foco.
- **Don't** criar CSS por página; o sistema é um arquivo só, por seção temática.
- **Don't** usar emoji no lugar de ícone de interface — eles mudam de forma por
  sistema operacional, não acompanham a tinta do tema e não têm peso de traço.
  Emoji dentro de texto de mensagem de WhatsApp é conteúdo, e esse fica.
- **Don't** declarar borda e sombra no mesmo elemento.
- **Don't** pôr sobretítulo acima de um título: o título carrega o próprio peso.
- **Don't** deixar `auto-fit` sem teto numa fileira de poucos KPIs — dois tiles
  de 830px segurando os numerais "4" e "0" foi exatamente o que aconteceu.
- **Don't** gravar o resultado da análise em `JSONB`: o Postgres reordena as
  chaves por tamanho e a ordem das chaves É a ordem das colunas da tabela.
- **Don't** criar um segundo momento extraordinário. O facho é o único, e a
  regra acima explica por quê.
- **Don't** aplicar o campo de fluxo em qualquer seção que não seja o Hero.
- **Don't** pôr efeito luminoso atrás de texto sem véu, e sem medir o pior
  pixel: a média mente.
- **Don't** usar `overflow-x: hidden` num ancestral de elemento `sticky`; ele
  força `overflow-y: auto` e cria contêiner de rolagem. Use `clip`.
- **Don't** trocar o `linear` do facho por easing sem recalcular os atrasos de
  cada elemento.
- **Don't** animar `width`, `height`, `top`, `left` ou margem. Use `transform`,
  `scaleX` ou `grid-template-rows`.
- **Don't** dar entrada a uma seção só porque ela existe. Entrada é para
  conteúdo que chega.
- **Don't** pôr a regra de `:hover` depois da de `:active` no bloco de
  movimento reduzido.
