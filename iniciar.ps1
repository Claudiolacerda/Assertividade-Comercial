# Sobe o Neriah inteiro no Windows: banco, API e site.
#
# Pode ser executado de qualquer lugar — $PSScriptRoot aponta para a pasta deste
# arquivo, então não importa em que diretório o PowerShell esteja.
#
# Uso: clique com o botão direito neste arquivo -> "Executar com o PowerShell"
#      ou, no terminal:  .\iniciar.ps1

$ErrorActionPreference = "Stop"
$raiz = $PSScriptRoot
Set-Location $raiz

Write-Host ""
Write-Host "  NERIAH DATA - iniciando" -ForegroundColor Green
Write-Host "  $raiz" -ForegroundColor DarkGray
Write-Host ""

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
    Write-Host " criando contêiner..." -NoNewline
    # -v: volume nomeado, para os dados sobreviverem a remocao do conteiner
    docker run --name pg-assertividade `
        -e POSTGRES_PASSWORD=assert123 -e POSTGRES_DB=assertividade `
        -p 5432:5432 -v neriah_dados:/var/lib/postgresql/data `
        -d postgres:16 *> $null
} else {
    docker start pg-assertividade *> $null
}
Write-Host " ok" -ForegroundColor Green

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
    Write-Host "      Copie o .env.example e ajuste DATABASE_URL e JWT_SECRET." -ForegroundColor Yellow
    Read-Host "`nEnter para fechar"
    exit 1
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
if (-not (Test-Path (Join-Path $raiz "frontend\node_modules"))) {
    Write-Host "[3/3] Instalando dependencias do site (1 a 2 minutos)..." -ForegroundColor Yellow
    Push-Location (Join-Path $raiz "frontend")
    npm install
    Pop-Location
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
