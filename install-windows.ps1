# ==============================================================================
#  🛡️ Limpeza & Otimização Desktop Multiplataforma (Windows Bootstrap Oneliner)
#  Uso no PowerShell (Admin recomendado):
#  irm https://raw.githubusercontent.com/abdielcordeiro/limpeza-desktop/main/install-windows.ps1 | iex
# ==============================================================================
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Repo = "abdielcordeiro/limpeza-desktop"
$BinaryName = "limpeza-windows.exe"
$TargetDir = Join-Path $env:TEMP "limpeza-desktop-bin"
$TargetPath = Join-Path $TargetDir $BinaryName
$ReleaseUrl = "https://github.com/$Repo/releases/latest/download/$BinaryName"

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "  🛡️  LIMPEZA & OTIMIZAÇÃO DESKTOP (WINDOWS STANDALONE)" -ForegroundColor Cyan
Write-Host "  Repositório Oficial: https://github.com/$Repo" -ForegroundColor DarkGray
Write-Host "==============================================================================" -ForegroundColor Cyan

if (-not (Test-Path $TargetDir)) {
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
}

Write-Host "⬇️  Obtendo versão standalone oficial mais recente ($BinaryName)..." -ForegroundColor Yellow

$downloadOk = $false
try {
    Invoke-WebRequest -Uri $ReleaseUrl -OutFile $TargetPath -UseBasicParsing -ErrorAction Stop
    if ((Test-Path $TargetPath) -and ((Get-Item $TargetPath).Length -gt 100000)) {
        $downloadOk = $true
    }
} catch {
    $downloadOk = $false
}

if ($downloadOk) {
    Write-Host "✅ Executável standalone validado com sucesso!" -ForegroundColor Green
    Write-Host "🚀 Inicializando painel local em 127.0.0.1..." -ForegroundColor Green
    & $TargetPath $args
    exit $LASTEXITCODE
}

# Fallback se a release ainda não estiver publicada no GitHub
Write-Host "ℹ️  Release binária ainda não disponível no GitHub Releases." -ForegroundColor Yellow
Write-Host "🔄 Acionando fallback direto via runtime Python local..." -ForegroundColor Yellow

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command py -ErrorAction SilentlyContinue
}

if ($pythonCmd) {
    $zipPath = Join-Path $TargetDir "repo.zip"
    $extractDir = Join-Path $TargetDir "source"
    $archiveUrl = "https://github.com/$Repo/archive/refs/heads/main.zip"

    Write-Host "⬇️  Baixando código-fonte oficial em $TargetDir..." -ForegroundColor DarkGray
    Invoke-WebRequest -Uri $archiveUrl -OutFile $zipPath -UseBasicParsing
    
    if (Test-Path $extractDir) {
        Remove-Item -Path $extractDir -Recurse -Force
    }
    Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force
    
    $subFolder = Get-ChildItem -Path $extractDir -Directory | Select-Object -First 1
    if ($subFolder) {
        Set-Location $subFolder.FullName
        Write-Host "🚀 Executando aplicação..." -ForegroundColor Green
        & $pythonCmd.Source "main.py" $args
        exit $LASTEXITCODE
    }
}

Write-Host "❌ Não foi possível inicializar a aplicação. Verifique sua conexão à internet." -ForegroundColor Red
exit 1
