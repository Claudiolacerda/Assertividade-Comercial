# Sobe o Neriah inteiro no Windows: banco, API e site.
#
# Pode ser executado de qualquer lugar - $PSScriptRoot aponta para a pasta deste
# arquivo, entao nao importa em que diretorio o PowerShell esteja.
#
# Uso: clique com o botao direito neste arquivo -> "Executar com o PowerShell"
#      ou, no terminal:  .\iniciar.ps1

$ErrorActionPreference = "Stop"
$raiz = $PSScriptRoot
Set-Location $raiz

Write-Host ""
Write-Host "  NERIAH DATA - iniciando" -ForegroundColor Green
Write-Host "  $raiz" -ForegroundColor DarkGray
Write-Host ""

# ------------------------------------------------- 0. Estado do repositorio
# Um `git pull` interrompido deixa MERGE_HEAD para tras e todo pull seguinte
# falha. Sem este aviso o script subia alegremente a versao ANTIGA, e quem
# rodou o pull junto com o script no mesmo bloco acha que atualizou.
$merge = Join-Path $raiz ".git\MERGE_HEAD"
if (Test-Path $merge) {
    Write-Host "[0/3] Ha uma fusao do git pela metade neste repositorio." -ForegroundColor Yellow
    Write-Host "      Enquanto ela existir, nenhum 'git pull' funciona e voce roda codigo antigo." -ForegroundColor Yellow
    Write-Host "      Veja o que ha com 'git status' e, se nao houver nada seu, resolva com:" -ForegroundColor Yellow
    Write-Host "        git merge --abort" -ForegroundColor White
    Write-Host "        git fetch origin" -ForegroundColor White
    Write-Host "        git reset --hard origin/claude/jolly-dirac-q1cf0x" -ForegroundColor White
    $segue = Read-Host "`nSubir assim mesmo, com o codigo como esta? (s/N)"
    if ($segue -notmatch '^[sS]') { exit 1 }
}

# ---------------------------------------------------------------- 1. Banco
Write-Host "[1/3] Banco de dados..." -NoNewline
try {
    docker info *> $null
} catch {
    Write-Host " ERRO" -ForegroundColor Red
    Write-Host "      O Docker Desktop nao esta rodando. Abra ele e tente de novo." -ForegroundColor Yellow
    Read-Host "`nEnter para fechar"
    exit 1
}

$existe = docker ps -a --filter "name=pg-assertividade" --format "{{.Names}}"
if (-not $existe) {
    Write-Host " criando conteiner..." -NoNewline
    # -v: volume nomeado, para os dados sobreviverem a remocao do conteiner
    docker run --name pg-assertividade `
        -e POSTGRES_PASSWORD=assert123 -e POSTGRES_DB=assertividade `
        -p 5432:5432 -v neriah_dados:/var/lib/postgresql/data `
        -d postgres:16 *> $null
} else {
    docker start pg-assertividade *> $null
}
Write-Host " ok" -ForegroundColor Green

# -------------------------------------------------- 1b. Migracoes pendentes
# Idempotentes: se ja estiver tudo certo, nao fazem nada e nao demoram nada.
$venvPy = Join-Path $raiz "backend\.venv\Scripts\python.exe"
if (Test-Path $venvPy) {
    Write-Host "[1b/3] Migracoes..." -NoNewline
    Push-Location (Join-Path $raiz "backend")
    $saida = & $venvPy "scripts\migrar_ordem_colunas.py" 2>&1
    Pop-Location
    if ($saida -match "convertida") {
        Write-Host " aplicada" -ForegroundColor Green
        Write-Host "      As colunas do resultado passaram de JSONB para JSON." -ForegroundColor DarkGray
        Write-Host "      Analises antigas seguem com a ordem de coluna embaralhada;" -ForegroundColor DarkGray
        Write-Host "      refaca a analise do mes para ela sair na ordem certa." -ForegroundColor DarkGray
    } else {
        Write-Host " nada pendente" -ForegroundColor Green
    }
}

# ---------------------------------------------------------------- 2. Backend
$venv = Join-Path $raiz "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $venv)) {
    Write-Host "[2/3] Ambiente Python nao encontrado." -ForegroundColor Yellow
    Write-Host "      Rode uma vez:" -ForegroundColor Yellow
    Write-Host "        cd `"$raiz\backend`"" -ForegroundColor White
    Write-Host "        python -m venv .venv" -ForegroundColor White
    Write-Host "        .\.venv\Scripts\Activate.ps1" -ForegroundColor White
    Write-Host "        pip install -r requirements.txt" -ForegroundColor White
    Read-Host "`nEnter para fechar"
    exit 1
}
if (-not (Test-Path (Join-Path $raiz "backend\.env"))) {
    Write-Host "[2/3] Falta o backend\.env." -ForegroundColor Yellow
    Write-Host "      Ele e ignorado pelo git, entao numa copia nova do projeto nao vem junto." -ForegroundColor Yellow
    Write-Host "      Crie com:" -ForegroundColor Yellow
    Write-Host "        Copy-Item backend\.env.example backend\.env" -ForegroundColor White
    Write-Host "      e no arquivo: AMBIENTE=desenvolvimento, descomente o DATABASE_URL local" -ForegroundColor Yellow
    Write-Host "      e gere o JWT_SECRET com:" -ForegroundColor Yellow
    Write-Host "        python -c `"import secrets; print(secrets.token_urlsafe(48))`"" -ForegroundColor White
    Read-Host "`nEnter para fechar"
    exit 1
}

# Mesma logica do npm mais abaixo, pelo mesmo motivo: um `git pull` que traz
# dependencia nova deixa a API quebrada e o script nao percebe. O sintoma do
# lado do Python e pior que o do site - a janela da API morre com ImportError
# e some, e sobra um site no ar conversando com nada.
$req     = Join-Path $raiz "backend\requirements.txt"
$carimboPy = Join-Path $raiz "backend\.venv\.instalado-em"
$precisaPy = $false
if (-not (Test-Path $carimboPy)) { $precisaPy = $true }
elseif ((Get-Item $req).LastWriteTime -gt (Get-Item $carimboPy).LastWriteTime) { $precisaPy = $true }

if ($precisaPy) {
    Write-Host "[2/3] Instalando dependencias do Python..." -ForegroundColor Yellow
    & $venv -m pip install -r $req --timeout 120 --retries 10
    if ($LASTEXITCODE -eq 0) { Set-Content -Path $carimboPy -Value (Get-Date -Format o) }
    else {
        Write-Host "      Falhou a instalacao. Rode a mao:" -ForegroundColor Yellow
        Write-Host "        cd `"$raiz\backend`"; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt" -ForegroundColor White
        Read-Host "`nEnter para fechar"
        exit 1
    }
}

Write-Host "[2/3] API em http://localhost:8000 ..." -NoNewline
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$raiz\backend'; .\.venv\Scripts\Activate.ps1; " +
    "Write-Host 'API - Neriah Data' -ForegroundColor Green; " +
    "uvicorn app.main:app --reload"
)
Write-Host " ok (janela separada)" -ForegroundColor Green

# ---------------------------------------------------------------- 3. Frontend
# Instala quando node_modules nao existe OU quando o package-lock mudou depois
# da ultima instalacao. Sem a segunda condicao, um `git pull` que traz dependencia
# nova deixa o site quebrado e o script nao percebe - foi o que aconteceu.
$frontend = Join-Path $raiz "frontend"
$modulos  = Join-Path $frontend "node_modules"
$lock     = Join-Path $frontend "package-lock.json"
$carimbo  = Join-Path $modulos ".instalado-em"

$precisa = $false
if (-not (Test-Path $modulos)) { $precisa = $true }
elseif (-not (Test-Path $carimbo)) { $precisa = $true }
elseif ((Get-Item $lock).LastWriteTime -gt (Get-Item $carimbo).LastWriteTime) { $precisa = $true }

if ($precisa) {
    Write-Host "[3/3] Instalando dependencias do site (1 a 2 minutos)..." -ForegroundColor Yellow
    Push-Location $frontend
    npm install
    Pop-Location
    if (Test-Path $modulos) { Set-Content -Path $carimbo -Value (Get-Date -Format o) }
}

Write-Host "[3/3] Site em http://localhost:5173 ..." -NoNewline
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$raiz\frontend'; " +
    "Write-Host 'SITE - Neriah Data' -ForegroundColor Green; " +
    "npm run dev"
)
Write-Host " ok (janela separada)" -ForegroundColor Green

Write-Host ""
Write-Host "  Abrindo o navegador em alguns segundos..." -ForegroundColor DarkGray
Start-Sleep -Seconds 9
Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "  Pronto. Para desligar, feche as duas janelas ou rode .\parar.ps1" -ForegroundColor Green
Write-Host ""
Read-Host "Enter para fechar esta janela"
