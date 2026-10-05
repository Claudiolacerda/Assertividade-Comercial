# Instalacao de primeira vez do Neriah no Windows.
#
# Existe porque a instalacao tinha cinco passos manuais e cada um deles era um
# lugar para errar: rodar o comando na pasta errada, esquecer o .venv, copiar o
# .env e nao editar, deixar o Postgres de producao no DATABASE_URL. Aqui tudo
# isso e feito e CONFERIDO, e o script para com uma mensagem clara em vez de
# deixar o erro aparecer tres passos adiante.
#
# E seguro rodar de novo: nada que ja esta pronto e refeito, e o .env existente
# nunca e sobrescrito.
#
# Uso:  .\configurar.ps1     e depois  .\iniciar.ps1

$ErrorActionPreference = "Stop"
$raiz = $PSScriptRoot
Set-Location $raiz

function Passo($texto) { Write-Host "`n$texto" -ForegroundColor Cyan }
function Ok($texto)    { Write-Host "  ok  $texto" -ForegroundColor Green }
function Aviso($texto) { Write-Host "  !   $texto" -ForegroundColor Yellow }
function Parar($texto, $comoResolver) {
    Write-Host "`n  PAROU AQUI: $texto" -ForegroundColor Red
    if ($comoResolver) { Write-Host "  $comoResolver" -ForegroundColor Yellow }
    Read-Host "`nEnter para fechar"
    exit 1
}

Write-Host ""
Write-Host "  NERIAH DATA - instalacao" -ForegroundColor Green
Write-Host "  $raiz" -ForegroundColor DarkGray

# ------------------------------------------------------- 1. A pasta certa
# O erro mais comum foi rodar comando de dentro de backend\ ou de uma copia
# antiga do projeto. Dois arquivos provam que esta e a raiz da versao atual.
Passo "[1/6] Conferindo a pasta..."
foreach ($prova in @("backend\requirements.txt", "frontend\package.json", "backend\app\core\jet.py")) {
    if (-not (Test-Path (Join-Path $raiz $prova))) {
        Parar "nao achei $prova aqui." `
              "Esta pasta nao e a raiz do projeto atual. Rode o script de dentro da pasta que tem backend\ e frontend\."
    }
}
Ok "raiz do projeto confirmada"

# -------------------------------------------------------- 2. Estado do git
Passo "[2/6] Conferindo o git..."
if (Test-Path (Join-Path $raiz ".git\MERGE_HEAD")) {
    Parar "ha uma fusao do git pela metade." `
          "Resolva antes:  git merge --abort  ;  git fetch origin  ;  git reset --hard origin/claude/jolly-dirac-q1cf0x"
}
try {
    $branch = (git rev-parse --abbrev-ref HEAD 2>$null)
    $commit = (git rev-parse --short HEAD 2>$null)
    Ok "branch $branch, commit $commit"
    if ($branch -eq "main") {
        Aviso "voce esta na main. O trabalho fica em claude/jolly-dirac-q1cf0x."
        Aviso "Troque com:  git checkout claude/jolly-dirac-q1cf0x"
    }
} catch {
    Aviso "nao consegui ler o git (nao e repositorio?). Seguindo mesmo assim."
}

# -------------------------------------------------------------- 3. Python
Passo "[3/6] Ambiente Python..."
$venv = Join-Path $raiz "backend\.venv\Scripts\python.exe"
if (Test-Path $venv) {
    Ok "backend\.venv ja existe"
} else {
    try { $v = (python --version 2>&1) } catch {
        Parar "o comando 'python' nao existe." `
              "Instale o Python 3.11+ de python.org e marque 'Add python.exe to PATH' no instalador."
    }
    Write-Host "  criando o ambiente ($v)..." -NoNewline
    Push-Location (Join-Path $raiz "backend")
    python -m venv .venv
    Pop-Location
    if (-not (Test-Path $venv)) {
        Parar "a criacao do ambiente falhou." `
              "Tente a mao:  cd backend  ;  python -m venv .venv --without-pip  ;  .\.venv\Scripts\python.exe -m ensurepip"
    }
    Write-Host " ok" -ForegroundColor Green
}

Write-Host "  instalando as dependencias (1 a 3 minutos)..." -ForegroundColor DarkGray
& $venv -m pip install --upgrade pip --quiet
& $venv -m pip install -r (Join-Path $raiz "backend\requirements.txt") --timeout 120 --retries 10
if ($LASTEXITCODE -ne 0) {
    Parar "o pip falhou." "Rode a mao e me mande o erro:  backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt"
}
Set-Content -Path (Join-Path $raiz "backend\.venv\.instalado-em") -Value (Get-Date -Format o)
Ok "dependencias do Python instaladas"

# ------------------------------------------------------------------ 4. .env
# Ele e ignorado pelo git, entao nunca vem numa copia nova. Montar a mao era o
# passo que mais dava errado: ficava com o banco de producao e uma chave que
# nao e chave.
Passo "[4/6] Arquivo de configuracao (.env)..."
$env_ = Join-Path $raiz "backend\.env"
if (Test-Path $env_) {
    Ok "backend\.env ja existe (nao vou mexer)"
} else {
    # PERMITIR_AUTOCADASTRO vai para True porque isto e uma instalacao de
    # desenvolvimento na maquina de quem desenvolve: e a rede de seguranca para
    # entrar pelo navegador se o criar_conta.py falhar. Em producao fica False.
    $exemplo = Get-Content (Join-Path $raiz "backend\.env.example") -Raw
    $chave = & $venv -c "import secrets; print(secrets.token_urlsafe(48))"
    $texto = $exemplo `
        -replace "AMBIENTE=producao", "AMBIENTE=desenvolvimento" `
        -replace "JWT_SECRET=troque-esta-chave", "JWT_SECRET=$chave" `
        -replace 'ORIGENS_PERMITIDAS=https://seu-dominio\.com\.br', 'ORIGENS_PERMITIDAS=http://localhost:5173,http://127.0.0.1:5173' `
        -replace "PERMITIR_AUTOCADASTRO=False", "PERMITIR_AUTOCADASTRO=True" `
        -replace '(?m)^DATABASE_URL=postgresql\+psycopg2://usuario:senha@host:5432/assertividade$', `
                 'DATABASE_URL=postgresql+psycopg2://postgres:assert123@localhost:5432/assertividade'
    # UTF8 SEM BOM. O `Set-Content -Encoding UTF8` do PowerShell 5.1 escreve com
    # BOM, e o BOM entra como parte da primeira linha do .env.
    [System.IO.File]::WriteAllText($env_, $texto, (New-Object System.Text.UTF8Encoding $false))
    Ok "backend\.env criado, apontando para o Postgres local e com JWT_SECRET gerado"
}

# -------------------------------------------------------------- 5. Frontend
Passo "[5/6] Dependencias do site..."
try { $n = (node --version 2>&1) } catch {
    Parar "o comando 'node' nao existe." "Instale o Node 20+ de nodejs.org e abra um terminal novo."
}
$modulos = Join-Path $raiz "frontend\node_modules"
if (Test-Path (Join-Path $modulos ".instalado-em")) {
    Ok "frontend\node_modules ja existe"
} else {
    Write-Host "  npm install ($n) - 1 a 2 minutos..." -ForegroundColor DarkGray
    Push-Location (Join-Path $raiz "frontend")
    npm install
    Pop-Location
    if (-not (Test-Path $modulos)) { Parar "o npm install falhou." "Rode a mao em frontend\ e me mande o erro." }
    Set-Content -Path (Join-Path $modulos ".instalado-em") -Value (Get-Date -Format o)
    Ok "dependencias do site instaladas"
}

# ---------------------------------------------------------------- 6. Docker
Passo "[6/6] Docker..."
try {
    docker info *> $null
    Ok "Docker Desktop esta rodando"
} catch {
    Aviso "o Docker Desktop nao esta aberto."
    Aviso "Abra ele antes de rodar .\iniciar.ps1 - e dele que vem o banco de dados."
}

Write-Host ""
Write-Host "  Instalacao concluida." -ForegroundColor Green
Write-Host ""
Write-Host "  Agora falta criar a sua conta (uma vez so). Com o Docker aberto:" -ForegroundColor White
Write-Host "    .\iniciar.ps1" -ForegroundColor Cyan
Write-Host "    # espere subir, feche as janelas, e entao:" -ForegroundColor DarkGray
Write-Host "    backend\.venv\Scripts\python.exe backend\scripts\criar_conta.py ``" -ForegroundColor Cyan
Write-Host "      --organizacao `"Sua Agencia`" --nome `"Claudio`" --email voce@email.com ``" -ForegroundColor Cyan
Write-Host "      --tipo agencia --cliente `"Nome do Cliente`"" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Ele mostra a senha UMA vez. Anote." -ForegroundColor Yellow
Write-Host ""
Read-Host "Enter para fechar"
