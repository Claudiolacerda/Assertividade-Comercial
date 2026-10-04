# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

**Usuário primário (quem a home precisa convencer):** o dono de um negócio
pequeno ou médio no Brasil que investe em anúncio no Meta e não sabe o que
aquele investimento virou. Ele não é analista: lê relatório de agência sem saber
checar, e a pergunta que ele faz todo mês é "gastei R$ 3 mil, apareceram leads, e
no fim do mês quanto disso virou cliente?". Ele abre o WhatsApp muito mais do que
abre dashboard.

**Usuário secundário (atendido pelo produto, não pela home):** dono de agência ou
gestor de tráfego, que usa o modo agência para analisar vários clientes e provar
resultado. O modo só aparece para quem declara ser agência no cadastro.

**Operador real do sistema:** quem sobe as planilhas é normalmente alguém do
comercial ou o próprio dono, não um técnico. A ferramenta é usada uma vez por
mês, no fechamento — não diariamente.

## Product Purpose

Cruzar o relatório de tráfego do Meta Ads com a planilha de reuniões comerciais e
dizer onde o dinheiro trava: quais campanhas geram lead, quantos leads viram
reunião, quantas reuniões viram cliente, e **por que** o resto parou. O
diagnóstico sai das observações que a própria equipe comercial escreveu na
planilha ("travou no preço", "depende do sócio", "sumiu").

Sucesso é o dono do negócio saber, em uma tela, se o anúncio está caro porque o
anúncio é ruim ou porque o time comercial não fecha — e sair com uma lista de
quem ligar nesta semana.

## Positioning

A maioria das ferramentas de métrica de tráfego no Brasil lê a API da plataforma
de anúncio e para no lead: custo por lead, alcance, impressão. Elas não sabem o
que aconteceu depois, porque esse dado não está na API — está na planilha do
comercial.

O Neriah exige as duas pontas e por isso consegue dizer o que nenhuma delas diz:
custo por cliente fechado, taxa de comparecimento, e o motivo da perda por nome
de cliente. A contrapartida é honesta e precisa aparecer no produto: **sem a
planilha comercial preenchida, o Neriah entrega menos que um dashboard de
tráfego.** A qualidade do preenchimento é o gargalo real do produto.

## Operating Context

- Uso mensal, no fechamento do mês. Não é ferramenta de rotina diária.
- Entrada: um export CSV/XLSX do gerenciador de anúncios do Meta e uma planilha
  de controle comercial, que varia de empresa para empresa — nomes de coluna,
  formato de data e de moeda mudam. O leitor tolera essa variação.
- A planilha comercial costuma chegar incompleta: no primeiro cliente real, 7 de
  13 campos esperados não existiam. Por isso o produto oferece uma planilha
  modelo e mostra uma nota de cobertura dizendo o que deixou de ser analisado.
- Saídas: painel na tela, Excel com fórmulas vivas, mensagem pronta para
  WhatsApp e um canvas de cadência de follow-up.
- O relatório final frequentemente é lido no celular, pelo WhatsApp, por quem
  nunca abriu o sistema.

## Capabilities and Constraints

- Multi-inquilino com schema por cliente no Postgres; organização resolvida pelo
  banco a partir do usuário do token, nunca pelo token.
- Dois tipos de conta: direta (analisa a si mesma) e agência (carteira de
  clientes). O modo agência fica escondido até ser declarado no cadastro.
- O motor aceita variação de planilha, mas recusa o que não for relatório de
  anúncio nem controle comercial (testado: export do Google Ads e planilha de
  estoque são corretamente recusados).
- Dados pessoais de terceiros: o sistema guarda nome de cliente final e
  observações em texto livre sobre pessoas. Isso é responsabilidade LGPD do
  assinante, e o produto não pode tratar esses dados como anônimos.
- Preços já publicados na home. Contato comercial por WhatsApp.
- Autocadastro é desligado em produção; contas são criadas por CLI.

## Brand Commitments

- **Nome:** Neriah Data. Neriah significa "luz".
- **Binding, confirmado pelo usuário:** o símbolo da logo e o verde de marca
  (`#53EF86`) são intocáveis.
- Voz em português do Brasil, direta, sem jargão de agência. O relatório que vai
  para o cliente final não carrega vocabulário técnico do sistema.
- O que é problema de planilha fica no painel do operador; não vai para o
  relatório do cliente final.

## Evidence on Hand

**Real e utilizável:** os números da análise de setembro de 2026 de um cliente
real — R$ 3.651,02 investidos, 81 leads, 35 reuniões realizadas, 9 clientes
fechados, 25,7% de assertividade, R$ 405,67 de custo por cliente. O usuário
autorizou usar os números **sem nomear a empresa**.

Também reais, e vindos dessa mesma análise: "9 clientes travaram em preço", "6
dependem de um decisor oculto", "11 oportunidades paradas há mais de 15 dias".

Os arquivos de origem em `dados/meta/` e `dados/reunioes/` são cópias
**anonimizadas** da planilha real, porque o repositório é público. Toda a
estrutura e todos os números foram preservados (a suíte de 74 testes confere
os KPIs contra eles); o que mudou foram os nomes das pessoas, a marcação de
parceria e o nome da empresa, trocados por fictícios um a um. A empresa
aparece como "Contabilidade Horizonte", que não existe. Nenhum nome real de
cliente final está no repositório, nem no histórico do git.

Consequência prática: se você precisar citar um cliente do exemplo em texto de
produto, use os nomes fictícios. Trocar por nomes reais reintroduz dado
pessoal de terceiro em repositório público, o que o usuário não tem permissão
para fazer.

**Onde entra o modelo de linguagem (JEV).** O JET calcula e o JEV escreve. A
fronteira é dura: número vem de código, palavra vem do modelo. O produto vende
"o CAC real", e um número que o modelo tivesse derivado poderia estar errado
justamente onde o cliente corta verba. Por isso o modelo recebe os números
prontos e formatados, é instruído a não fazer conta nem em algarismo nem por
extenso, e o que ele devolve não alimenta nenhum cálculo nem aparece como
número na tela.

O usuário decidiu que só agregado sai da máquina: números, nomes de campanha
(que são códigos de mídia) e contagens por categoria de sinal. Nome de cliente
final, texto livre das observações e nome de quem fez a reunião ficam. Isso tem
um custo conhecido e aceito: sem o texto livre, o JEV não conserta a
classificação de objeção, que hoje sai de palavras-chave e erra — "Marido
trocou de contabilidade e não tem interesse" é classificado como "decide com
cônjuge" quando é um lead perdido. Quem for revisitar essa decisão precisa
saber que é isso que está sobre a mesa, e que a saída limpa seria
pseudonimizar antes de enviar.

**CRMs que o motor já lê.** O gargalo do produto nunca foi o motor, é a
planilha que chega. Seis formatos de exportação foram testados com a mesma base
de 32 negócios por baixo: HubSpot, Pipedrive, RD Station, Agendor, DataCrazy e
Datalitics. Os seis passam, e os testes em `tests/test_crms.py` seguram isso.

O que o teste revelou é o tamanho real do gargalo: quatro dos seis eram
recusados de saída, e um derrubava a análise com exceção. A causa quase nunca
era o motor, era vocabulário — "Deal Name" não começa por "Cliente", e "Ganha"
no feminino não casa com "ganho". Antes de prometer integração com qualquer
CRM novo, rode uma exportação de verdade dele contra esse arquivo: o custo de
suportar mais um costuma ser uma linha na tabela de apelidos, não código.

**Dois modelos, porque são duas pessoas.** Quem não tem CRM precisa de uma
planilha para preencher, e recebe a de sempre, em português. Quem já tem CRM não
quer preencher nada: quer saber o que marcar na tela de exportação. Para esse,
existe o gabarito do HubSpot, com os nomes de propriedade que ele vê no próprio
CRM e uma aba de cinco passos. O circuito é fechado por teste: a planilha é
gerada, preenchida e devolvida ao motor, para que modelo e tabela de apelidos
nunca saiam de sincronia em silêncio — um modelo que o próprio sistema não lê é
pior que nenhum modelo, porque a pessoa segue a instrução e leva um erro.

Duas das seis fixtures (DataCrazy e Datalitics) são reconstruções plausíveis,
não o arquivo real — esses produtos existem e são relevantes para o público do
Neriah, mas o formato de exportação deles não é público. Quem tiver acesso a
uma exportação de verdade deve substituir a fixture.

**Ausências que trabalho futuro não pode fabricar:**

- Não há depoimento assinado de ninguém.
- Não há permissão para nomear a empresa cliente.
- Não há logo de cliente, estudo de caso, número de assinantes, prêmio, menção
  de imprensa ou benchmark de mercado.
- Há um cliente real, não uma base. Qualquer plural ("empresas confiam") seria
  falso.

## Product Principles

1. **O diagnóstico é o produto, não o gráfico.** O valor está na frase que diz o
   que fazer na segunda-feira, não na barra bonita. Gráfico sem conclusão escrita
   é entrega pela metade.
2. **A honestidade sobre a planilha é parte da entrega.** Quando o dado não veio,
   o produto diz o que deixou de ser analisado em vez de preencher o buraco com
   uma métrica vazia.
3. **O destinatário final não abre dashboard.** Toda entrega precisa de uma forma
   que caiba numa tela de celular e numa conversa de WhatsApp.
4. **Número se lê em superfície clara; marca se afirma no escuro.** A troca de
   superfície separa vender de trabalhar.
5. **Nada se comunica só por cor.** Daltonismo e tela ruim de celular são o caso
   normal, não a exceção.

## Accessibility & Inclusion

- A paleta de séries dos gráficos é medida para protanopia, deuteranopia e
  tritanopia (pior par ΔE 13,0 no claro e 8,7 no escuro; mínimo exigido 8).
- Todo estado traz ícone ou texto além da cor.
- Todo gráfico oferece "ver tabela" como alternativa aos dados.
- Português do Brasil é a única língua; não há requisito de internacionalização.
