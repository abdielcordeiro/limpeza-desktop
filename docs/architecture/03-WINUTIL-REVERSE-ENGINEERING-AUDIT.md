# Dossiê de Engenharia Reversa e Auditoria de Privacidade: `ChrisTitusTech/winutil`

Este documento registra a engenharia reversa completa realizada sobre o repositório [ChrisTitusTech/winutil](https://github.com/ChrisTitusTech/winutil), detalhando:
1. **Auditoria de Bibliotecas, Envios de Rede e Privacidade:** Separação rigorosa entre o que é **Suspeito / Risco de Vazamento para o Criador ou Terceiros (Banido)** vs. o que é **Protegido / Nativo do Sistema Operacional (Mantido e Auditado)**.
2. **Mapeamento Técnico Completo dos Mecanismos de Limpeza e Tweaks:** Chaves de Registro, Serviços, Tarefas Agendadas e Comandos Nativos que serão transcritos para o nosso motor local.

---

## 🔍 1. LAUDO DE AUDITORIA: O QUE É SUSPEITO VS. O QUE É PROTEGIDO

> [!IMPORTANT]
> **Objetivo da Auditoria:** Garantir que **nenhum dado do sistema do usuário ou dado sensível** seja enviado para fora pelo criador do `winutil` (Chris Titus), por servidores externos de terceiros ou por bibliotecas obscuras.

### 1.1. 🚨 O que foi identificado como SUSPEITO / RISCO no `winutil` (100% Banido da nossa aplicação)

Analisamos todos os scripts PowerShell (`functions/public/`, `functions/private/`, `scripts/main.ps1`) e arquivos declarativos (`config/*.json`) do WinUtil. Abaixo estão todos os pontos onde o WinUtil realiza conexões externas ou executa código de terceiros não auditável:

| # | Componente no WinUtil | Comportamento no Código Original | Destino Externo | Veredito da Auditoria & Ação Tomada |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **Bootstrap & Links para Servidor do Criador (`christitus.com`)** | O script principal é baixado de `https://christitus.com/win` (`Invoke-RestMethod \| iex`) e os botões de ajuda em `config/tweaks.json` disparam acessos para `https://winutil.christitus.com/...`. | Servidores controlados pelo criador (`christitus.com`) | **🔴 SUSPEITO / BANIDO:** Expõe o IP, horário de execução e cabeçalhos do sistema do usuário aos servidores do autor. **Removido 100%:** nosso código roda localmente sem nenhum link ou ping para `christitus.com`. |
| **2** | **Download de Executável Fechado `OOSU10.exe` (`Invoke-WPFOOSU.ps1`)** | Baixa silenciosamente via `Invoke-WebRequest` o binário `https://dl5.oo-software.com/files/ooshutup10/OOSU10.exe` para `%TEMP%` e o executa com privilégios de **Administrador**. | Servidores da empresa privada O&O Software GmbH (`oo-software.com`) | **🔴 CRÍTICO / BANIDO:** É um binário `.exe` compilado de código fechado (closed-source). Como não há código-fonte aberto, é impossível garantir que ele não envie telemetria ou dados da máquina. **Removido 100%:** aplicamos as chaves de privacidade do Windows diretamente via Python nativo (`winreg`), 100% aberto e auditável. |
| **3** | **Injeção de Lista Remota no arquivo `hosts` (`WPFTweaksBlockAdobeNet`)** | Executa `Invoke-RestMethod` baixando um arquivo texto de um repositório de terceiros (`Ruddernation-Designs/Adobe-URL-Block-List`) e grava direto em `C:\Windows\System32\drivers\etc\hosts`. | Repositório GitHub de terceiro não-oficial (`Ruddernation-Designs`) | **🔴 ALTO RISCO / BANIDO:** Risco grave de *Supply-Chain / DNS Hijacking*. Se o dono desse repositório externo alterar o arquivo, ele pode redirecionar qualquer domínio (inclusive bancos ou serviços críticos) na máquina do usuário. **Removido 100%.** |
| **4** | **Download e Execução Remota do Chocolatey (`Install-WinUtilChoco.ps1`)** | Usa `System.Net.WebClient.DownloadString('https://community.chocolatey.org/install.ps1') \| iex` para instalar o Chocolatey na máquina como Admin. | `community.chocolatey.org` | **🟠 SUSPEITO / BANIDO:** Executa script remoto arbitrário da internet na máquina do usuário. **Removido 100%.** |
| **5** | **Download de Binário `oscdimg.exe` (`Invoke-Microwin.ps1`)** | Baixa um executável `.exe` hospedado externamente caso não exista na máquina. | GitHub / CDNs externas | **🟠 SUSPEITO / BANIDO:** Download de binário externo sem validação criptográfica estrita. **Removido 100%.** |
| **6** | **Alteração de Servidores DNS (`Set-WinUtilDNS.ps1`)** | Altera as configurações de placa de rede (`Set-DnsClientServerAddress`) para provedores externos (`1.1.1.1`, `8.8.8.8`, `9.9.9.9`, AdGuard). | Provedores DNS externos | **🟡 DESATIVADO:** Redireciona as consultas de rede da máquina. Não será executado automaticamente. |
| **7** | **Carregamento de Fontes Externas no Relatório HTML (`fonts.googleapis.com`)** | O relatório HTML antigo continha `<link href="https://fonts.googleapis.com/...">`, que ao abrir no navegador fazia uma requisição para os servidores do Google. | `fonts.googleapis.com` / `fonts.gstatic.com` | **🟡 REMOVIDO:** O novo Dashboard HTML usa exclusivamente fontes nativas do sistema (`-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Roboto, sans-serif`), garantindo **zero requisições externas** ao abrir o relatório. |

---

### 1.2. 🛡️ O que é PROTEGIDO / SEGURO (Auditado e Mantido na Nossa Aplicação)

Para garantir segurança máxima contra ataques de cadeia de suprimentos (*supply-chain attacks*) ou vazamento de dados por bibliotecas de terceiros:

| Camada / Recurso | Tecnologia Utilizada | Por que é 100% Protegido e Seguro? |
| :--- | :--- | :--- |
| **Dependências Python** | **100% Python Standard Library** (`os`, `sys`, `shutil`, `pathlib`, `subprocess`, `json`, `winreg`, `plistlib`, `ctypes`, `http.server`, `urllib.parse`, `webbrowser`) | **Zero pacotes `pip` de terceiros!** Não dependemos de bibliotecas externas no PyPI que possam sofrer sequestro de pacote ou conter código malicioso oculto. Todo o código é nativo do Python oficial. |
| **Janela Inicial & Dashboard (`127.0.0.1`)** | `http.server.HTTPServer(('127.0.0.1', port))` | O servidor web local faz *bind* estritamente no endereço de loopback `127.0.0.1`. Ele **não é acessível pela rede Wi-Fi/LAN nem pela internet** e apenas serve a interface gráfica local entre o navegador do usuário e o processo Python local. |
| **Comandos de Otimização (Windows)** | Binários nativos assinados pela Microsoft em `C:\Windows\System32`: `reg.exe` / `winreg`, `sc.exe`, `schtasks.exe`, `powercfg.exe`, `cleanmgr.exe`, `dism.exe`, `sfc.exe`, `netsh.exe`, `ipconfig.exe` | Nenhum executável externo é baixado. Todos os comandos invocam apenas ferramentas originais do próprio Windows, operando localmente sobre o Registro e Serviços da máquina. |
| **Comandos de Otimização (macOS)** | Binários nativos assinados pela Apple em `/usr/bin` e `/usr/sbin`: `defaults`, `diskutil`, `launchctl`, `tmutil`, `dscacheutil`, `pkgutil`, `mdutil` | Operam 100% localmente no macOS sem comunicação externa. |
| **Verificador de Atualizações (`winget` / `brew`)** | `winget upgrade --include-unknown` (Windows) e `brew outdated --json` (macOS) | Utiliza exclusivamente os gerenciadores oficiais já instalados pelo próprio usuário no sistema operacional para comparar versões instaladas com o catálogo público. Nenhum dado pessoal, arquivo ou informação da máquina é enviado para nós ou para terceiros. |

---

## ⚙️ 2. ENGENHARIA REVERSA: O QUE SERÁ TRANSCRITO (100% LOCAL & SEGURO)

Abaixo está o inventário completo das operações legítimas do WinUtil que funcionam localmente no sistema operacional e que serão incorporadas ao nosso motor:

### 2.1. Limpeza Profunda do Sistema (Windows)
1. **Limpeza de Temporários e Prefetch (`WPFTweaksDeleteTempFiles`):**
   - `%TEMP%\*` (Arquivos temporários do usuário)
   - `%SystemRoot%\Temp\*` (Arquivos temporários do sistema)
   - `%SystemRoot%\Prefetch\*` (Cache de pré-carregamento antigo)
2. **Limpeza de Disco Nativa e WinSxS (`WPFTweaksDiskCleanup`):**
   - `cleanmgr.exe /d C: /VERYLOWDISK`
   - `Dism.exe /online /Cleanup-Image /StartComponentCleanup /ResetBase` (Compactação segura da pasta `C:\Windows\WinSxS` removendo versões substituídas de updates).
3. **Cache de Delivery Optimization (`WPFTweaksDeliveryOptimization`):**
   - Desativa P2P de atualizações (`HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\DeliveryOptimization\Config` -> `DODownloadMode = 0`) e limpa o cache local (`Delete-DeliveryOptimizationCache`).
4. **Storage Sense (`WPFTweaksStorage`):**
   - `HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\StorageSense\Parameters\StoragePolicy` -> `01 = 1`.
5. **Hibernação (`WPFTweaksHiber`):**
   - `powercfg.exe /hibernate off` (Remove o arquivo gigante `C:\hiberfil.sys` em desktops/máquinas que não usam hibernação, liberando de 6 GB a 32 GB instantaneamente).

---

### 2.2. Tweaks Essenciais de Privacidade, Telemetria e Performance (`Essential Tweaks`)

#### A. Ponto de Restauração e Backup (`WPFTweaksRestorePoint`)
- `HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\SystemRestore` -> `SystemRestorePointCreationFrequency = 0` (`DWord`, Original: `1440`).
- Criação de ponto de restauração local antes de aplicar otimizações (`Enable-ComputerRestore` + `Checkpoint-Computer`) + **Snapshot JSON local** contendo os valores exatos do usuário antes da modificação.

#### B. Bloqueio Total da Telemetria da Microsoft (`WPFTweaksTele`)
- **Chaves de Registro:**
  - `HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\DataCollection` -> `AllowTelemetry = 0` (Original: `1`)
  - `HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection` -> `AllowTelemetry = 0`, `DoNotShowFeedbackNotifications = 1`
  - `HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager` -> `ContentDeliveryAllowed = 0`, `OemPreInstalledAppsEnabled = 0`, `PreInstalledAppsEnabled = 0`, `PreInstalledAppsEverEnabled = 0`, `SilentInstalledAppsEnabled = 0`, `SubscribedContent-338387Enabled = 0`, `SubscribedContent-338388Enabled = 0`, `SubscribedContent-338389Enabled = 0`, `SubscribedContent-353698Enabled = 0`, `SystemPaneSuggestionsEnabled = 0`
  - `HKCU:\Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo` -> `Enabled = 0`
  - `HKCU:\Software\Microsoft\Windows\CurrentVersion\Privacy` -> `TailoredExperiencesWithDiagnosticDataEnabled = 0`
  - `HKLM:\SOFTWARE\Policies\Microsoft\Windows\AdvertisingInfo` -> `DisabledByGroupPolicy = 1`
  - `HKLM:\SOFTWARE\Microsoft\Windows\Windows Error Reporting` -> `Disabled = 1`
  - `HKCU:\SOFTWARE\Microsoft\Siuf\Rules` -> `NumberOfSIUFInPeriod = 0`
  - `HKLM:\SOFTWARE\Policies\Microsoft\Windows\System` -> `UploadUserActivities = 0`, `PublishUserActivities = 0`, `EnableActivityFeed = 0`
  - Variável de ambiente: `POWERSHELL_TELEMETRY_OPTOUT = 1`
- **Tarefas Agendadas Desativadas (`Scheduled Tasks`):**
  - `\Microsoft\Windows\Application Experience\Microsoft Compatibility Appraiser`
  - `\Microsoft\Windows\Application Experience\ProgramDataUpdater`
  - `\Microsoft\Windows\Autochk\Proxy`
  - `\Microsoft\Windows\Customer Experience Improvement Program\Consolidator`
  - `\Microsoft\Windows\Customer Experience Improvement Program\UsbCeip`
  - `\Microsoft\Windows\DiskDiagnostic\Microsoft-Windows-DiskDiagnosticDataCollector`
  - `\Microsoft\Windows\Feedback\Siuf\DmClient`
  - `\Microsoft\Windows\Feedback\Siuf\DmClientOnScenarioDownload`
  - `\Microsoft\Windows\Windows Error Reporting\QueueReporting`
  - `\Microsoft\Windows\Application Experience\MareBackup`
  - `\Microsoft\Windows\Application Experience\StartupAppTask`
  - `\Microsoft\Windows\Application Experience\PcaPatchDbTask`
  - `\Microsoft\Windows\Maps\MapsUpdateTask`

#### C. Otimização de Serviços e Agrupamento `svchost.exe` (`WPFTweaksServices`)
- **Cálculo de `SvcHostSplitThresholdInKB`:**
  - Calcula a memória RAM total física em KB e grava em `HKLM:\SYSTEM\CurrentControlSet\Control\SvcHostSplitThresholdInKB` (Original: `380000`), reduzindo dezenas de processos `svchost.exe` fragmentados.
- **Serviços de Telemetria Desativados (`Disabled`):**
  - `DiagTrack` (Connected User Experiences and Telemetry)
  - `dmwappushservice` (WAP Push Message Routing Service)
  - `RemoteRegistry`, `tzautoupdate`, `shpamsvc`, `UevAgentService`
- **Serviços Secundários alterados para Inicialização Sob Demanda (`Manual`):**
  - Mais de 45 serviços que vêm em `Automatic` sem necessidade contínua (`MapsBroker`, `lfsvc`, `RetailDemo`, `WMPNetworkSvc`, `XblAuthManager`, `XblGameSave`, `XboxGipSvc`, `XboxNetApiSvc`, `WalletService`, `PhoneSvc`, `Fax`, `wisvc`, `WpcMonSvc`, etc.), fazendo com que só consumam RAM/CPU se o usuário abrir o recurso correspondente.

#### D. GameDVR, Localização, Wi-Fi Sense, Consumer Features e Taskbar End Task
- **`WPFTweaksDVR` (Desativar gravação em background Xbox GameDVR para ganhar FPS/CPU):**
  - `HKCU:\System\GameConfigStore` -> `GameDVR_FSEBehavior = 2`, `GameDVR_Enabled = 0`, `GameDVR_DXGIHonorFSEWindowsCompatible = 1`, `GameDVR_HonorUserFSEBehaviorMode = 1`
  - `HKLM:\SOFTWARE\Policies\Microsoft\Windows\GameDVR` -> `AllowGameDVR = 0`
- **`WPFTweaksLoc` (Desativar Rastreamento de Localização):**
  - `HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location` -> `Value = "Deny"`
  - `HKLM:\SYSTEM\CurrentControlSet\Services\lfsvc\Service\Configuration` -> `Status = 0`
- **`WPFTweaksWifi` (Desativar Wi-Fi Sense):**
  - `HKLM:\Software\Microsoft\PolicyManager\default\WiFi\AllowWiFiHotSpotReporting` -> `Value = 0`
  - `HKLM:\Software\Microsoft\PolicyManager\default\WiFi\AllowAutoConnectToWiFiSenseHotspots` -> `Value = 0`
- **`WPFTweaksConsumerFeatures` (Impedir download silencioso de jogos/apps patrocinados na Microsoft Store):**
  - `HKLM:\SOFTWARE\Policies\Microsoft\Windows\CloudContent` -> `DisableWindowsConsumerFeatures = 1`
- **`WPFTweaksEndTask` (Botão "Finalizar Tarefa" direto no clique direito da Barra de Tarefas do Windows 11):**
  - `HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced\TaskbarDeveloperSettings` -> `TaskbarEndTask = 1`

---

### 2.3. Tweaks Avançados, Planos de Energia e Reparos (`Advanced Tweaks & Fixes`)

1. **Plano de Energia Desempenho Máximo (`WPFAddUltPerf` - Ultimate Performance):**
   - `powercfg -duplicatescheme e9a42b02-d5df-448d-aa00-03f14749eb61` e ativação idempotente via `powercfg -setactive <GUID>`.
2. **Desativação de Windows Copilot, Recall e Windows AI (`WPFTweaksWindowsAI` / `WPFTweaksDisableRecall`):**
   - `HKLM` e `HKCU` `\SOFTWARE\Policies\Microsoft\Windows\WindowsCopilot` -> `TurnOffWindowsCopilot = 1`
   - `HKLM` e `HKCU` `\SOFTWARE\Policies\Microsoft\Windows\WindowsAI` -> `DisableAIDataAnalysis = 1`
   - `HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced` -> `ShowCopilotButton = 0`
   - `Disable-WindowsOptionalFeature -FeatureName Recall -Online -NoRestart`
3. **Menu de Contexto Clássico no Windows 11 (`WPFTweaksRightClickMenu`):**
   - Criação da chave `HKCU:\Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\InprocServer32` com valor vazio `""`.
4. **Debloat do Microsoft Edge e Desativação do Bing Search no Menu Iniciar (`WPFTweaksEdgeDebloat` & `WPFTweaksBing`):**
   - Políticas em `HKLM:\SOFTWARE\Policies\Microsoft\Edge` (`StartupBoostEnabled = 0`, `BackgroundModeEnabled = 0`, `ShoppingAssistantEnabled = 0`, `HubsSidebarEnabled = 0`) e `HKCU:\Software\Microsoft\Windows\CurrentVersion\Search` (`BingSearchEnabled = 0`).
5. **Efeitos Visuais para Melhor Desempenho (`WPFTweaksDisplay`):**
   - Ajuste de `VisualFXSetting = 3`, `TaskbarAnimations = 0`, `MinAnimate = 0`, `EnableAeroPeek = 0`.
6. **Módulos de Reparo do Sistema (`Fixes`):**
   - **Reset Windows Update:** Para serviços `BITS, wuauserv, appidsvc, cryptsvc`, limpa fila BITS e rotaciona `SoftwareDistribution` / `catroot2`, reiniciando os serviços.
   - **Reset Network:** `netsh winsock reset`, `netsh int ip reset`, `ipconfig /flushdns`.
   - **System Corruption Scan:** `DISM /Online /Cleanup-Image /RestoreHealth` + `sfc /scannow`.
