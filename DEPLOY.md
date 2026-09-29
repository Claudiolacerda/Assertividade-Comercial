# Colocando o Neriah no ar

Do domínio ao primeiro cliente usando. O caminho abaixo põe tudo num servidor só
— banco, API, site e backup — com HTTPS automático.

---

## 1. Registrar o domínio

**https://registro.br** — exige CPF ou CNPJ e o pagamento é anual (domínio `.com.br`
custa poucas dezenas de reais por ano).

Passo a passo no site:

1. Digite o nome desejado na busca da página inicial para ver se está livre
2. Crie a conta (ou entre com gov.br) e adicione o domínio ao carrinho
3. Pague — boleto leva 1 a 3 dias úteis para liberar; **PIX e cartão liberam na hora**

Sugestões de nome, por ordem do que eu escolheria:

| Domínio | Comentário |
|---|---|
| `neriahdata.com.br` | casa com a marca completa, é o mais provável de estar livre |
| `neriah.com.br` | mais curto e forte, mas nome bíblico tem chance de já estar tomado |
| `neriah.app.br` | `.app.br` sinaliza software e costuma ter mais nomes livres |
| `usarneriah.com.br` | alternativa se os anteriores estiverem ocupados |

Se for atender fora do Brasil algum dia, registre também o `.com` (aí em outro
registrador, tipo Cloudflare ou Namecheap — o registro.br só cuida de `.br`).

---

## 2. Contratar o servidor

Uma máquina pequena aguenta bem o começo: **2 vCPU e 4 GB de RAM**. A análise usa
pandas, que consome memória em picos curtos; abaixo de 2 GB há risco de o processo
morrer no meio de uma planilha grande.

Opções no Brasil (latência menor e dado em território nacional, o que simplifica a
conversa de LGPD com o cliente): Hostinger VPS, Locaweb, KingHost, Magalu Cloud.
Fora: Hetzner e DigitalOcean saem mais baratos.

Peça **Ubuntu 24.04** e anote o IP.

### Alternativa: banco gerenciado

Se preferir não cuidar do Postgres, use Neon, Supabase ou RDS: preencha
`DATABASE_URL` no `.env` e remova o serviço `banco` do `docker-compose.yml`. O
resto continua igual. Custa mais, e o backup passa a ser responsabilidade do
provedor — confirme que ele faz.

---

## 3. Apontar o domínio para o servidor

No registro.br, em **Painel → seu domínio → DNS → Editar zona**, crie:

| Tipo | Nome | Valor |
|---|---|---|
| A | `@` | o IP do servidor |
| A | `www` | o IP do servidor |

A propagação leva de minutos a algumas horas. Confira com:

```bash
nslookup neriahdata.com.br
```

**Só siga para o passo 5 depois que o domínio responder com o IP certo** — o
certificado HTTPS é emitido a partir dele, e tentar antes gasta tentativas no
limite do Let's Encrypt.

---

## 4. Preparar o servidor

Conectado por SSH, como root:

```bash
apt update && apt upgrade -y
curl -fsSL https://get.docker.com | sh

# firewall: só SSH e web ficam abertos
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw --force enable

git clone https://github.com/Claudiolacerda/Assertividade-Comercial.git /opt/neriah
cd /opt/neriah
```

---

## 5. Configurar e subir

```bash
cp .env.exemplo .env
nano .env
```

Preencha, no mínimo:

```
DOMINIO=neriahdata.com.br
EMAIL_TLS=voce@seuemail.com.br
POSTGRES_PASSWORD=<senha longa e aleatória>
JWT_SECRET=<gere com o comando abaixo>
PERMITIR_AUTOCADASTRO=False
```

```bash
# gera o JWT_SECRET
docker run --rm python:3.11-slim python -c "import secrets; print(secrets.token_urlsafe(48))"

docker compose up -d --build
docker compose logs -f proxy    # acompanhe a emissão do certificado
```

Quando o log do `proxy` mostrar o certificado emitido, abra
`https://neriahdata.com.br`. O site deve aparecer com o cadeado.

---

## 6. Criar a sua conta

Com `PERMITIR_AUTOCADASTRO=False` a tela de cadastro fica fechada — é você quem
abre as contas, pelo terminal:

```bash
docker compose exec api python scripts/criar_conta.py \
  --organizacao "Neriah Data" \
  --nome "Cláudio Lacerda" \
  --email "claudio@neriahdata.com.br" \
  --tipo agencia \
  --cliente "Contabilidade Horizonte"
```

Ele pede a senha (ou gera uma e mostra, se não houver terminal interativo). Depois
é só entrar em `https://neriahdata.com.br/entrar`.

Para cada cliente novo que assinar, repita o comando com os dados dele — ou, se
for cliente da sua carteira, adicione pela tela **Carteira** sem tocar no servidor.

---

## 7. Conferir o backup

O serviço `backup` roda sozinho: faz uma cópia ao subir e depois toda madrugada,
guardando 14 dias de banco e de planilhas.

```bash
docker compose logs backup            # deve mostrar "backup concluído"
docker compose exec backup ls -lh /backups
```

**Backup que nunca foi restaurado não é backup.** Teste uma vez:

```bash
docker compose exec backup pg_restore --list /backups/banco_<data>.dump | head
```

E **tire os arquivos do servidor** — um backup que mora na mesma máquina não
protege contra a máquina morrer. Copie para o seu computador ou para um bucket:

```bash
docker compose cp backup:/backups ./backups-local
```

---

## 8. Manutenção

```bash
# atualizar o sistema depois de um git push
cd /opt/neriah && git pull && docker compose up -d --build

# ver o que está no ar
docker compose ps

# logs da API
docker compose logs -f api
```

---

## Antes do primeiro contrato assinado

- [ ] `JWT_SECRET` novo e secreto — com a chave de exemplo qualquer pessoa forja um token
- [ ] `PERMITIR_AUTOCADASTRO=False`
- [ ] HTTPS funcionando (cadeado no navegador)
- [ ] Backup testado **e** copiado para fora do servidor
- [ ] Termo de tratamento de dados com o cliente — o sistema guarda nome de cliente
      final e anotações sobre pessoas, o que é dado pessoal de terceiros sob a sua
      responsabilidade
- [ ] Definir por quanto tempo você guarda os dados de um cliente que cancelar
