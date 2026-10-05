# Desliga o Neriah: para a API, o site e o conteiner do banco.
#
# Os dados NAO sao apagados - ficam no volume neriah_dados e nas pastas do
# projeto. Para religar tudo: .\iniciar.ps1

$raiz = $PSScriptRoot
Set-Location $raiz

Write-Host ""
Write-Host "  Desligando o Neriah..." -ForegroundColor Yellow

# uvicorn e vite rodam em janelas separadas; fecha pelos processos
Get-Process python, node -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -and $_.Path.StartsWith($raiz) } |
    ForEach-Object {
        Write-Host "  parando $($_.ProcessName) (PID $($_.Id))" -ForegroundColor DarkGray
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }

try {
    docker stop pg-assertividade *> $null
    Write-Host "  banco parado (os dados continuam salvos)" -ForegroundColor DarkGray
} catch {
    Write-Host "  banco ja estava parado" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "  Tudo desligado." -ForegroundColor Green
Write-Host ""
