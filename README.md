# Assertividade Comercial

Sistema web multiempresa que cruza o **relatório de tráfego da Meta** com a **planilha de
assertividade comercial** e devolve, na tela e em Excel: KPIs, funil completo do anúncio ao
cliente, CAC e ROAS por campanha, assertividade por vendedor, pipeline em aberto e um
**diagnóstico automático** — as conclusões que o cruzamento das duas bases permite tirar.

Cada empresa cliente entra com login próprio e tem os dados em um **schema separado** no
Postgres.

---

## O que o sistema faz

**Lê a planilha como o cliente manda.** Acha o cabeçalho real dentro do arquivo — inclusive
painéis em blocos (“Semana 1”, “Semana 2”…) — e reconhece as colunas por apelido: “Quem fez”
vira Responsável, “Etapa do Funil” vira Status. Aceita `R$ 1.500,00`, `08/09/ 2026`, `17/09/`
e datas sem ano.

**Cruza as duas bases.** Investimento e leads da Meta ligados às reuniões por campanha e por
marcação, gerando CPL, custo por reunião, CAC, ROAS e ROI reais.

**Chega às próprias conclusões.** Cerca de 20 tipos de leitura crítica, entre elas:

- campanha que gastou sem gerar nenhum resultado;
- menor e maior custo por lead, com nome da campanha;
- quem tem maior e menor assertividade na equipe;
- oportunidades paradas há mais de N dias e clientes quentes, nominalmente;
- **quando o número não é confiável, ele diz**: “3 clientes marcados como Fechado têm observação
  de quem ainda vai decidir — se não fecharam, a assertividade real é 17,1% e não 25,7%”;
- “4 dos 9 fechamentos têm a marcação ‘Parceiro’ no nome; se vieram de indicação, o CAC real do
  anúncio é R$ 730,20 e não R$ 405,67”.

**Audita os dados.** Dez checagens linha a linha: status não reconhecido, data fora do mês,
agendamento depois da reunião, duplicidade, fechado sem valor.

**Exporta a planilha formatada** com as taxas como **fórmula viva** do Excel — o cliente muda
uma meta e a coluna Situação recalcula sozinha.

---

## Arquitetura

```
Navegador (React + Recharts)
        │  /api   + cabeçalho X-Empresa (qual cliente da carteira)
        ▼
FastAPI ── motor de análise (pandas + openpyxl)   ← o notebook original, agora biblioteca
        │
        ▼
Postgres
   ├── schema public          organizações, empresas, usuários, acessos
   ├── schema tenant_acme     análises, arquivos    (cliente A da carteira)
   └── schema tenant_beta     análises, arquivos    (cliente B da carteira)
```

**Modo agência — desligado por padrão.** Uma *organização* é quem assina. Quem se
cadastra como empresa analisa só o próprio comercial e não vê carteira nenhuma:
a tela fica com Histórico, Nova análise, Configuração e Equipe. Quem marca
"agência ou gestor de tráfego" no cadastro ganha a **Carteira** e o seletor de
cliente. Quem passar a atender outros clientes depois liga o modo em
Configuração → *Você atende outros clientes?* (sem isso ficaria preso, porque a
tela de adicionar cliente mora dentro da carteira).

Os usuários pertencem à organização, não à empresa — é isso que permite um gestor
de tráfego abrir dez clientes com um login só. Três papéis:

| Papel | Enxerga | Pode |
|---|---|---|
| `admin` | toda a carteira | gerenciar clientes, metas e usuários |
| `membro` | toda a carteira | analisar, não gerencia |
| `cliente` | só as empresas liberadas | ver o próprio painel |

O cliente em foco viaja no cabeçalho `X-Empresa`. O backend só o aceita depois de
confirmar que pertence à organização do usuário — mandar o id alheio devolve 404,
e há teste para isso.

**Isolamento.** Nenhuma consulta de análise nomeia o schema; a sessão é aberta com um
`schema_translate_map` que resolve o schema a partir da empresa em foco, sempre validada contra a
organização lida do banco (nunca do token). Há testes para as duas fronteiras: entre organizações
e, dentro da mesma organização, entre o que um usuário `cliente` pode ver.

**Relatório no WhatsApp.** Toda análise vira uma mensagem curta para o cliente final:
os quatro números que ele cobra, a variação sobre o mês anterior e quem fechar esta semana pelo
nome. Editável antes de mandar. Três caminhos de envio — copiar, abrir o WhatsApp Web (funciona
sem nenhuma credencial) ou envio automático via Evolution API ou WhatsApp Cloud API.

**Cadência.** Um canvas onde cada etapa tem canal, dia e roteiro. O diferencial não é desenhar:
é `POST /api/cadencias {analise_id}`, que monta o fluxo a partir das objeções que a análise
encontrou — reancorar preço porque N clientes travaram nisso, material para o decisor porque M
dependem de terceiro, reabrir as oportunidades paradas.

**Planilha-modelo e nota da planilha.** O gargalo real não é o motor, é a coluna que falta na
planilha do cliente. Toda análise devolve uma `cobertura` — quantos dos 13 campos foram
reconhecidos e o que cada ausência está custando em indicador — e `/api/modelo/planilha-comercial.xlsx`
entrega um Excel pronto que destrava os 13.

```
backend/
  app/
    core/            MOTOR — independente de web e de banco
      config_analise.py   metas, apelidos de coluna, regras de status, sinais
      texto.py            normalização de texto, números e datas brasileiras
      leitura.py          leitura tolerante e mapeamento de colunas
      metricas.py         definição única de cada taxa (tela e Excel)
      pipeline.py         orquestra tudo → objeto Resultado
      excel.py            planilha formatada com fórmulas vivas
    models.py       public (empresas, usuários) + tenant (análises, arquivos)
    db.py           conexão e isolamento por schema
    security.py     bcrypt + JWT
    routers/        auth.py, analises.py
  tests/            49 testes (motor + API + isolamento)
frontend/
  src/components/   gráficos e peças do painel
  src/pages/        entrada, upload, análise, histórico, configuração, equipe
```

---

## Rodando localmente

Pré-requisitos: Python 3.11+, Node 20+, Postgres 14+.

```bash
# 1. Banco
createdb assertividade
psql -c "CREATE USER assert_app WITH PASSWORD 'assert_dev_pwd';"
psql -c "ALTER DATABASE assertividade OWNER TO assert_app;"

# 2. Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # ajuste DATABASE_URL e JWT_SECRET
uvicorn app.main:app --reload # http://localhost:8000/docs

# 3. Frontend (outro terminal)
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

As tabelas do schema `public` são criadas sozinhas na primeira subida; o schema de cada
empresa é criado no cadastro dela.

## Atalho no Windows

Na raiz do projeto há dois scripts que dispensam decorar caminhos — eles
descobrem sozinhos onde estão, então funcionam de qualquer pasta:

```powershell
.\iniciar.ps1   # sobe banco, API e site, e abre o navegador
.\parar.ps1     # desliga tudo (os dados continuam salvos)
```

Dá para rodar clicando com o botão direito no arquivo → *Executar com o
PowerShell*. Na primeira vez, se faltar o ambiente Python ou o `.env`, o script
diz exatamente o que fazer em vez de falhar no meio.

## Abrindo no VS Code

O repositório já vem com `.vscode/` configurado. Ao abrir a pasta, o VS Code
sugere as extensões necessárias (Python, Pylance, Debugpy, ESLint, Docker) —
aceite e siga:

**Primeira vez** — `Ctrl+Shift+P` → `Tasks: Run Task` → **Instalar dependências
(primeira vez)**. Cria o ambiente Python, instala o backend e o frontend.

Depois crie o `backend/.env` a partir do `.env.example` (é ele que guarda a
senha do banco e a chave dos tokens; nunca vai para o Git).

**No dia a dia** — `Ctrl+Shift+B` roda a tarefa **▶ Subir tudo**: liga o Postgres
no Docker, sobe a API em `localhost:8000` e o front em `localhost:5173`.

As demais tarefas (`Ctrl+Shift+P` → `Tasks: Run Task`):

| Tarefa | O que faz |
|---|---|
| `1 · Banco (Docker)` | Sobe ou religa o contêiner do Postgres |
| `2 · API (backend)` | FastAPI com recarga automática |
| `3 · Front (frontend)` | Vite com recarga automática |
| `Testes do backend` | Os 49 testes (também roda pela aba Testing) |
| `Build do frontend` | Gera `frontend/dist` para publicar |

**Depurar** — na aba Run and Debug:

- **API (depurar)** — ponto de parada em qualquer lugar do backend, inclusive
  dentro do motor de análise, enquanto o navegador usa o sistema.
- **Motor de análise (arquivo atual)** — roda o arquivo Python aberto, útil para
  testar uma mudança no motor sem subir a API.
- **API + Front** — sobe os dois e abre o navegador já anexado.

A aba **Testing** lista os 49 testes individualmente: dá para rodar um só e ver
onde parou, o que ajuda quando um KPI muda de valor.

### Testes

```bash
cd backend && python3 -m pytest -q
```

### Migrando um banco anterior ao modo agência

Se o banco foi criado antes da carteira (usuário preso a uma empresa):

```bash
cd backend
python3 scripts/migrar_para_agencia.py            # mostra o que faria
python3 scripts/migrar_para_agencia.py --aplicar  # executa
```

Cada empresa vira uma organização do tipo `direta` com ela mesma na carteira.
Logins, análises e schemas ficam como estavam. O script é idempotente.

Os testes do motor usam as planilhas reais de `dados/` como referência: se um refactor mudar
qualquer KPI, o teste quebra. Os testes de API precisam de um Postgres acessível (são pulados
sozinhos se não houver).

---

## Deploy

Com Docker, na própria VPS:

```bash
cat > .env <<'EOF'
POSTGRES_PASSWORD=<senha forte>
JWT_SECRET=<python3 -c "import secrets; print(secrets.token_urlsafe(48))">
ORIGENS_PERMITIDAS=https://seu-dominio.com.br
PERMITIR_AUTOCADASTRO=False
EOF

docker compose up -d --build
```

O banco não expõe porta para fora; só a `web` (nginx) publica a 8080. Ponha um proxy com
HTTPS (Caddy, Traefik ou o nginx da máquina) na frente.

Em PaaS (Railway, Render, Fly), suba `backend/` e `frontend/` como dois serviços e aponte
`DATABASE_URL` para o Postgres gerenciado.

### Antes de vender o acesso

1. **`JWT_SECRET` novo e secreto.** Com a chave padrão qualquer pessoa forja um token.
2. **`PERMITIR_AUTOCADASTRO=False`** e crie as contas você mesmo (o endpoint de cadastro fica
   fechado; usuários adicionais saem do painel Equipe de cada cliente).
3. **HTTPS obrigatório** — o token trafega no cabeçalho.
4. **Backup do Postgres.** `pg_dump` diário cobre todos os clientes de uma vez; para restaurar
   um cliente só, restaure o schema `tenant_<slug>` dele.
5. As planilhas enviadas ficam em `DIR_UPLOADS` — esse volume também precisa de backup, e é
   dado de cliente: trate como confidencial.

---

## Configuração por cliente

Cada empresa tem a sua, editável em **Configuração** (só o admin):

| O quê | Para quê |
|---|---|
| Metas (CTR, CPL, assertividade, CAC, ROAS…) | definem ✅/⚠️ e alimentam o diagnóstico |
| Marcações não pagas | tira indicações/parceiros do CAC do anúncio |
| Palavras que indicam tráfego pago | como ler a coluna Origem da planilha |
| Probabilidade de fechamento | forecast ponderado do pipeline |
| Dias para negociação parada | quando alertar |
| Classificar perda pela observação | assertividade honesta quando a equipe não registra perdas |

---

## O que a planilha do cliente precisa ter

**Mínimo:** uma coluna de cliente e uma de etapa/status. Nome de coluna o sistema reconhece
sozinho.

**Para liberar mais indicadores:**

| Coluna | Libera |
|---|---|
| Valor / Valor do contrato | receita, ticket médio, **ROAS**, ROI, forecast |
| Campanha | **CAC e ROAS por campanha** (qual anúncio realmente vende) |
| Origem | separar tráfego pago de indicação |
| Quem fez / Responsável | comparação entre vendedores |
| Data de fechamento | ciclo de venda |
| Etapa “Perdido” e motivo | win rate confiável e motivos de perda |

O painel avisa, em texto, o que está faltando e o que aquilo bloqueia.
