# Ligar o Neriah no CRM do cliente

O Neriah lê planilha e lê CRM por API. Os dois caminhos terminam no mesmo
lugar: **o conector escreve um CSV e o motor analisa esse CSV**. Não existe
caminho separado para dado vindo de API.

Isso é de propósito, por três razões:

1. Nenhum número muda por ter vindo da API. A suíte que crava os KPIs vale
   para os dois caminhos.
2. Fica a prova. Quando o cliente perguntar "de onde saiu esse 12?", existe um
   arquivo para abrir, com o que o CRM respondeu naquele dia.
3. Reprocessar continua funcionando sem falar com o CRM de novo.

O CSV fica em `dados_clientes/<empresa>/<mês>/<crm>_<mês>.csv`.

---

## CRMs com conector pronto

| CRM | O que o cliente precisa ter em mãos |
|---|---|
| **Pipedrive** | O token em *Configurações pessoais › API* e o domínio da conta (`suaempresa.pipedrive.com`) |
| **API REST (configurável)** | Endereço do endpoint, token, e o mapa de campos (abaixo) |

> **Pipedrive:** o conector foi escrito sobre o contrato da API v1
> (`/api/v1/deals`), sem acesso à documentação oficial na máquina em que foi
> escrito. O primeiro teste com token de verdade confirma ou corrige, e o
> conserto é só nas constantes de `app/core/conectores/pipedrive.py` — nada
> fora desse arquivo conhece o formato do Pipedrive.

---

## O conector configurável

É o que faz funcionar um CRM sem documentação pública — a maioria no Brasil.
Você descreve a API no formulário e o Neriah lê.

```json
{
  "url": "https://api.seucrm.com.br/v1/negocios",
  "auth": { "tipo": "bearer" },
  "itens": "data",
  "paginacao": {
    "tipo": "deslocamento",
    "param": "offset",
    "param_tamanho": "limit",
    "tamanho": 100
  },
  "periodo": {
    "param_de": "data_inicio",
    "param_ate": "data_fim",
    "formato": "%Y-%m-%d"
  },
  "campos": {
    "Cliente": "nome",
    "Status": "situacao",
    "Data do lead": "criado_em",
    "Data de fechamento": "fechado_em",
    "Valor": "valor",
    "Responsável": "vendedor.nome"
  }
}
```

### Campo a campo

| Chave | O que é |
|---|---|
| `url` | O endpoint que **lista** os negócios. Tem de ser `https://` e de endereço público. |
| `auth.tipo` | `bearer` (`Authorization: Bearer <token>`), `cabecalho` (com `auth.nome` e `auth.prefixo`), `parametro` (token na URL, com `auth.nome`), ou `nenhuma`. |
| `itens` | Onde está a **lista** dentro do JSON. `"data"`, `"data.itens"`, ou `""` se a resposta já for uma lista pura. |
| `paginacao.tipo` | `nenhuma`, `deslocamento` (manda `offset=0,100,200…`), `pagina` (`page=1,2,3…`), ou `cursor`. |
| `paginacao.caminho_proximo` | Só no cursor: onde vem o cursor da próxima página (ex.: `"meta.next_cursor"`). |
| `paginacao.caminho_tem_mais` | Opcional: campo booleano que diz se há mais (ex.: `"meta.has_more"`). Sem ele, a última página é a que vier menor que o tamanho pedido. |
| `periodo` | Os parâmetros de filtro por data. Se o CRM não filtra, **omita**: o recorte do mês acontece depois, no motor. |
| `extras` | Parâmetros fixos na URL, ex.: `{"pipeline_id": "3"}`. |
| `campos` | **A esquerda é a coluna do Neriah, a direita é o caminho no JSON do CRM.** Ponto navega para dentro (`vendedor.nome`). |

### Colunas aceitas em `campos`

`Cliente` · `Status` · `Etapa` · `Responsável` · `Valor` · `Origem` ·
`Campanha` · `Produto` · `Data do lead` · `Data da reunião` ·
`Data de fechamento` · `Motivo da perda` · `Observações` · `ID no CRM`

Só `Cliente` é obrigatório. Cada coluna a mais libera indicador — a mesma
tabela que vale para a planilha, em *O que a planilha do cliente precisa ter*
no README.

### A armadilha: mapear só a data de fechamento

O motor situa cada negócio no tempo por **alguma** data. Um mapa que traz
`Data de fechamento` e mais nada descreve bem quem fechou e deixa todo o resto
sem lugar no calendário. Os negócios em aberto somem do mês, a assertividade
sobe porque o **denominador encolheu**, e o número parece ótimo justamente
quando está errado.

Por isso aponte sempre `Data do lead` ou `Data da reunião`. A tela avisa
quando faltam as duas.

---

## O que pedir ao suporte do CRM

Copie e cole:

> Preciso integrar nosso CRM a um sistema de análise por API. Vocês podem me
> informar:
>
> 1. O endereço do endpoint que **lista os negócios/oportunidades** (GET, JSON).
> 2. Como autenticar: token no cabeçalho `Authorization`, em outro cabeçalho,
>    ou como parâmetro na URL? Como eu gero esse token?
> 3. Como funciona a paginação (`offset`/`page`/`cursor`) e qual o tamanho
>    máximo de página.
> 4. Se dá para filtrar por período, com que parâmetros e em que formato de data.
> 5. Um **exemplo de resposta JSON** com um negócio, para eu saber o nome de
>    cada campo (nome do cliente, situação, valor, responsável, data de criação
>    e data de fechamento).
> 6. Se há limite de requisições por minuto.

O item 5 é o que mais economiza tempo: com um exemplo de resposta em mãos, o
mapa de campos sai em cinco minutos.

---

## Segurança

- O token é **cifrado** no banco (`app/security.cifrar`, Fernet) e nunca volta
  pela API. A tela só sabe se existe um token guardado, não qual.
- A chave vem de `CHAVE_CRIPTOGRAFIA`; vazia, é derivada do `JWT_SECRET`.
  **Trocar o `JWT_SECRET` torna ilegível todo token de CRM já salvo** — eles
  não se perdem calados: a tela pede a reconexão.
- A conexão mora no **schema da empresa**, como as análises. O isolamento que
  já protege os números passa a proteger a credencial pelo mesmo mecanismo.
- Endereço só `https://` e só de IP público: endereço livre num sistema que
  roda no servidor é o caminho clássico para fazê-lo buscar o que só ele
  alcança (metadados da nuvem, rede interna, localhost).

---

## Banco: tabela nova em cliente antigo

O schema de cada empresa nasce uma vez, quando a conta é criada. `conexoes_crm`
é a primeira tabela acrescentada depois, então **os clientes já existentes não
a têm** — e a consulta que a cita devolve 500.

```
cd backend
.venv\Scripts\python.exe scripts\migrar_tabelas_novas.py
```

Só cria o que falta. Pode rodar quantas vezes quiser. O `diagnosticar.py`
aponta o problema e indica este script.
