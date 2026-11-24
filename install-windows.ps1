# ==============================================================================
#  Limpeza & Otimizacao Desktop Multiplataforma (Windows Bootstrap Oneliner)
#  Uso no PowerShell (Admin recomendado):
#  irm https://raw.githubusercontent.com/abdielcordeiro/limpeza-desktop/main/install-windows.ps1 | iex
# ==============================================================================

function Test-RealPython {
    param(
        [string]$ExePath
    )

    if ([string]::IsNullOrWhiteSpace($ExePath)) {
        return $false
    }
    if ($ExePath -match 'WindowsApps') {
        return $false
    }
    if (-not (Test-Path -Path $ExePath -PathType Leaf)) {
        return $false
    }

    try {
        $null = & $ExePath -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" 2>$null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Find-RealPython {
    $candidates = @()

    foreach ($cmdName in @("python", "python3")) {
        $cmds = Get-Command $cmdName -All -ErrorAction SilentlyContinue
        foreach ($cmd in $cmds) {
            if ($cmd.Source) {
                $candidates += $cmd.Source
            }
        }
    }

    $pyLauncher = Get-Command "py" -ErrorAction SilentlyContinue
    if ($pyLauncher -and $pyLauncher.Source -and ($pyLauncher.Source -notmatch 'WindowsApps')) {
        try {
            $resolvedFromPy = & $pyLauncher.Source -3 -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($resolvedFromPy)) {
                $candidates += ($resolvedFromPy | Select-Object -First 1).Trim()
            }
        } catch {
            # Ignora falha do launcher py
        }
    }

    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (Test-RealPython -ExePath $candidate) {
            return $candidate
        }
    }

    return $null
}

function Invoke-LimpezaDesktop {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$CliArgs
    )

    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

        $Repo = "abdielcordeiro/limpeza-desktop"
        $BinaryName = "limpeza-windows.exe"
        $TargetDir = Join-Path $env:TEMP "limpeza-desktop-bin"
        $TargetPath = Join-Path $TargetDir $BinaryName
        $ReleaseUrl = "https://github.com/$Repo/releases/latest/download/$BinaryName"

        Write-Host "==============================================================================" -ForegroundColor Cyan
        Write-Host "  LIMPEZA & OTIMIZACAO DESKTOP (WINDOWS STANDALONE)" -ForegroundColor Cyan
        Write-Host "  Repositorio Oficial: https://github.com/$Repo" -ForegroundColor DarkGray
        Write-Host "==============================================================================" -ForegroundColor Cyan

        if (-not (Test-Path -Path $TargetDir)) {
            New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
        }

        # Passo 1: Binario Standalone Oficial
        Write-Host "Obtendo versao standalone oficial mais recente ($BinaryName)..." -ForegroundColor Yellow
        $downloadOk = $false
        try {
            Invoke-WebRequest -Uri $ReleaseUrl -OutFile $TargetPath -UseBasicParsing -ErrorAction Stop
            if ((Test-Path -Path $TargetPath) -and ((Get-Item -Path $TargetPath).Length -gt 100000)) {
                $downloadOk = $true
            }
        } catch {
            $downloadOk = $false
        }

        if ($downloadOk) {
            Write-Host "Executavel standalone validado com sucesso!" -ForegroundColor Green
            Write-Host "Inicializando painel local em 127.0.0.1..." -ForegroundColor Green
            try {
                if ($CliArgs -and $CliArgs.Count -gt 0) {
                    & $TargetPath @CliArgs
                } else {
                    & $TargetPath
                }
                if ($LASTEXITCODE -ne 0) {
                    Write-Host "Aviso: O aplicativo encerrou com codigo de saida $LASTEXITCODE." -ForegroundColor Yellow
                }
            } catch {
                Write-Host "Erro ao executar o binario standalone: $($_.Exception.Message)" -ForegroundColor Red
            }
            return
        }

        # Passo 2: Busca Segura por Python >= 3.9 Real (ignorando Stub da Microsoft Store)
        Write-Host "Release binaria ainda nao disponivel no GitHub Releases." -ForegroundColor Yellow
        Write-Host "Buscando runtime Python >= 3.9 valido no sistema..." -ForegroundColor Yellow

        $PythonExe = Find-RealPython

        # Passo 3: Runtime Portatil Zero-Install em %TEMP% se nao houver Python >= 3.9
        if (-not $PythonExe) {
            $RuntimeDir = Join-Path $TargetDir "runtime"
            $RuntimeExe = Join-Path $RuntimeDir "tools\python.exe"

            if (Test-RealPython -ExePath $RuntimeExe) {
                Write-Host "Reutilizando runtime Python portatil em cache ($RuntimeExe)..." -ForegroundColor Green
                $PythonExe = $RuntimeExe
            } else {
                Write-Host "Python >= 3.9 nao encontrado. Baixando runtime portatil oficial PSF (NuGet 3.11.9)..." -ForegroundColor Yellow
                $NugetUrl = "https://www.nuget.org/api/v2/package/python/3.11.9"
                $NugetZip = Join-Path $TargetDir "python-3.11.9-portable.zip"

                try {
                    Invoke-WebRequest -Uri $NugetUrl -OutFile $NugetZip -UseBasicParsing -ErrorAction Stop
                    if (Test-Path -Path $RuntimeDir) {
                        Remove-Item -Path $RuntimeDir -Recurse -Force -ErrorAction SilentlyContinue
                    }
                    Expand-Archive -Path $NugetZip -DestinationPath $RuntimeDir -Force
                    Remove-Item -Path $NugetZip -Force -ErrorAction SilentlyContinue
                } catch {
                    Write-Host "Erro ao baixar ou extrair runtime Python portatil: $($_.Exception.Message)" -ForegroundColor Red
                    return
                }

                if (Test-RealPython -ExePath $RuntimeExe) {
                    $PythonExe = $RuntimeExe
                    Write-Host "Runtime Python portatil pronto em $RuntimeExe" -ForegroundColor Green
                } else {
                    Write-Host "Erro: O runtime portatil nao foi validado corretamente em $RuntimeExe." -ForegroundColor Red
                    return
                }
            }
        } else {
            Write-Host "Python real encontrado: $PythonExe" -ForegroundColor Green
        }

        # Passo 4: Download e Execucao Segura do Codigo-Fonte
        $zipPath = Join-Path $TargetDir "repo.zip"
        $extractDir = Join-Path $TargetDir "source"
        $archiveUrl = "https://github.com/$Repo/archive/refs/heads/main.zip"

        Write-Host "Baixando codigo-fonte oficial em $TargetDir..." -ForegroundColor DarkGray
        try {
            Invoke-WebRequest -Uri $archiveUrl -OutFile $zipPath -UseBasicParsing -ErrorAction Stop
            if (Test-Path -Path $extractDir) {
                Remove-Item -Path $extractDir -Recurse -Force -ErrorAction SilentlyContinue
            }
            Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force
            Remove-Item -Path $zipPath -Force -ErrorAction SilentlyContinue
        } catch {
            Write-Host "Erro ao baixar ou extrair o codigo-fonte: $($_.Exception.Message)" -ForegroundColor Red
            return
        }

        $subFolder = Get-ChildItem -Path $extractDir -Directory | Select-Object -First 1
        if (-not $subFolder) {
            Write-Host "Erro: Diretorio do codigo-fonte nao encontrado apos extracao." -ForegroundColor Red
            return
        }

        Push-Location -Path $subFolder.FullName
        try {
            Write-Host "Executando aplicacao..." -ForegroundColor Green
            if ($CliArgs -and $CliArgs.Count -gt 0) {
                & $PythonExe "main.py" @CliArgs
            } else {
                & $PythonExe "main.py"
            }
            if ($LASTEXITCODE -ne 0) {
                Write-Host "Aviso: A aplicacao encerrou com codigo de saida $LASTEXITCODE." -ForegroundColor Yellow
            }
        } catch {
            Write-Host "Erro ao executar main.py: $($_.Exception.Message)" -ForegroundColor Red
        } finally {
            Pop-Location
        }
    } catch {
        Write-Host "Erro inesperado durante a inicializacao: $($_.Exception.Message)" -ForegroundColor Red
        return
    }
}

Invoke-LimpezaDesktop @args
