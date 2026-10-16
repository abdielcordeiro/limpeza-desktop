# Requisitos Funcionais (RF) e Não-Funcionais (RNF)

Este documento define o escopo funcional, critérios de aceite e restrições não-funcionais do sistema **Limpeza & Otimização Desktop Multiplataforma (Windows & macOS)**.

---

## 1. Requisitos Funcionais (RF)

### RF-01: Inicialização via Terminal e Janela de Navegação Pré-Execução
- **Descrição:** Ao executar o comando único no terminal (Windows ou macOS), o sistema deve abrir uma **Janela de Configuração Interativa** antes de iniciar qualquer operação destrutiva ou varredura pesada.
- **Critérios de Aceite:**
  1. Detectar automaticamente o Sistema Operacional hospedeiro (`Windows` ou `macOS`), permitindo ao usuário visualizar/confirmar o ambiente e as partições/volumes disponíveis.
  2. Permitir ao usuário escolher quais módulos e categorias deseja executar na sessão:
     - **Módulo 1 — Limpeza Autônoma de Temporários e Caches:** Exclusão automática de arquivos temporários do sistema, caches de navegadores/Electron, shaders de GPU, dumps de erro e caches de ferramentas de desenvolvimento.
     - **Módulo 2 — Diagnóstico de Resíduos Órfãos, Arquivos Gigantes e Aplicativos Pesados:** Varredura profunda para identificar pastas de softwares já desinstalados, top maiores arquivos do disco e tamanho real dos aplicativos instalados.
     - **Módulo 3 — Otimização e Performance do Sistema (Motor WinUtil no Windows / Motor Nativo no macOS):** Seleção de Tweaks Essenciais, Tweaks Avançados, Planos de Energia e Reparos de Sistema, incluindo presets (`Padrão Recomendado`, `Mínimo/Seguro`, `Personalizado`) e opção de `Reverter Otimizações (Undo)`.
     - **Módulo 4 — Diagnóstico de Armazenamento em Nuvem (OneDrive / iCloud Drive) e Atualizações de Softwares.**
  3. Oferecer modo **Execução Real (Autônoma)** e modo **Simulação (Dry-Run / Apenas Diagnóstico)**.

---

### RF-02: Motor de Limpeza Autônoma Multiplataforma (Windows & macOS)
- **Descrição:** O sistema deve liberar espaço físico em disco de forma autônoma nos alvos selecionados como seguros, contabilizando exatamente quantos bytes/megabytes/gigabytes foram liberados e registrando cada item removido ou eventual bloqueio de permissão/arquivo em uso.
- **Critérios de Aceite (Windows):**
  1. Limpar `%TEMP%` (pasta temporária do usuário), `%SystemRoot%\Temp` e `%SystemRoot%\Prefetch`.
  2. Limpar caches de Shaders de GPU (`DXCache`, `GLCache`, `D3DSCache`, `NV_Cache`).
  3. Limpar relatórios de erro e dumps (`CrashDumps`, `Windows Error Reporting - WER`, `CrashReports`).
  4. Limpar caches transitórios de navegadores e frameworks Electron (`CacheStorage`, `EBWebView`, `GPUCache`, `Code Cache`) preservando cookies, sessões e dados de login.
  5. Limpar caches de pacotes de desenvolvimento (quando autorizado pelo usuário): `pip\cache`, `npm-cache`, `yarn\cache`, `.gradle\caches`, `.nuget\packages`.
  6. Executar limpeza opcional de cache do Windows Update (`SoftwareDistribution\Download`), Delivery Optimization Cache e Component Store (`cleanmgr` / `Dism.exe /StartComponentCleanup`).
- **Critérios de Aceite (macOS):**
  1. Limpar caches de usuário em `~/Library/Caches/*` (respeitando whitelist de proteção de estados críticos) e logs em `~/Library/Logs/*`.
  2. Limpar relatórios de diagnóstico e falhas em `~/Library/Application Support/CrashReporter` e `~/Library/Logs/DiagnosticReports`.
  3. Limpar artefatos de compilação e desenvolvimento (quando selecionados): Xcode (`~/Library/Developer/Xcode/DerivedData`, `Archives`, `CoreSimulator/Caches`), Homebrew (`~/Library/Caches/Homebrew`), npm (`~/.npm/_cacache`), pip (`~/Library/Caches/pip`), Gradle (`~/.gradle/caches`), Cargo (`~/.cargo/registry/cache`).
  4. Limpar arquivos temporários da sessão e Lixeira (`~/.Trash`) quando solicitado.

---

### RF-03: Detecção de Resíduos Órfãos com Algoritmo Anti-Falsos Positivos de 5 Camadas
- **Descrição:** Identificar pastas órfãs deixadas por aplicativos já desinstalados sem jamais classificar erroneamente softwares ativos como lixo.
- **Critérios de Aceite:**
  1. **No Windows (5 Camadas):**
     - Camada 1: Registro do Windows (`HKLM` e `HKCU` `Uninstall` 32/64 bits — `DisplayName` e `InstallLocation`).
     - Camada 2: Diretórios de instalação de usuário (`%LOCALAPPDATA%\Programs`, `Program Files`, `Program Files (x86)`, `ProgramData`).
     - Camada 3: Atalhos do Menu Iniciar (`%APPDATA%` e `%ProgramData%`).
     - Camada 4: Processos em execução ativa (`tasklist`).
     - Camada 5: Whitelist curada de ferramentas de desenvolvimento, produtividade e jogos.
  2. **No macOS (5 Camadas):**
     - Camada 1: Bundles instalados em `/Applications` e `~/Applications` (extraindo `CFBundleName`, `CFBundleDisplayName` e `CFBundleIdentifier` do `Info.plist`).
     - Camada 2: Pacotes registrados via Homebrew (`brew list --formula`, `brew list --cask`) e instaladores Apple (`pkgutil --pkgs`).
     - Camada 3: Agentes e Daemons registrados (`~/Library/LaunchAgents`, `/Library/LaunchAgents`, `/Library/LaunchDaemons`).
     - Camada 4: Processos ativos em execução (`ps -eo comm`).
     - Camada 5: Whitelist curada de ecossistemas macOS/Apple e ferramentas Dev.
  3. Pastas em `AppData` (Windows) ou `~/Library/Application Support`, `~/Library/Containers`, `~/Library/Caches`, `~/Library/Preferences`, `~/Library/Saved Application State` (macOS) que não possuírem correspondência em nenhuma das 5 camadas devem ser listadas como **Resíduos Órfãos Verificados** (com opção de limpeza assistida ou automática).

---

### RF-04: Mapeamento de Arquivos Gigantes e Aplicativos Pesados Instalados
- **Descrição:** Ajudar o usuário a visualizar claramente o que está consumindo o armazenamento da máquina (arquivos grandes esquecidos e aplicativos pesados instalados).
- **Critérios de Aceite:**
  1. Listar os **Top 100 Maiores Arquivos e Pastas** em todas as partições/volumes analisados, aplicando deduplicação hierárquica (não repetir subpastas de uma mesma árvore já reportada).
  2. Classificar cada item em níveis claros de segurança:
     - `🚫 Não Apagar (Sistema Operacional)` (Ex: `C:\Windows\System32`, `/System`, `/Library/Apple`).
     - `⚙️ Desinstalar via Sistema / App` (Softwares instalados em `Program Files` ou `/Applications`).
     - `✅ Limpeza Direta (Sem Risco ao SO)` (Caches, temporários, installers `.dmg`/`.iso`/`.msi` antigos).
     - `⚠️ Avaliar Conteúdo Pessoal` (Documentos, vídeos, backups do usuário).
  3. Apresentar uma aba específica de **Aplicativos Instalados por Tamanho**, permitindo identificar quais softwares ou jogos ocupam mais gigabytes e sugerindo desinstalação segura ou migração de partição (`C:` -> `D:` no Windows ou volume externo no macOS).

---

### RF-05: Motor de Otimização do Sistema (WinUtil Sanitizado para Windows & Otimizador Nativo para macOS)
- **Descrição:** Incorporar nativamente todas as otimizações de sistema, privacidade, serviços e desempenho do `ChrisTitusTech/winutil` no Windows (e equivalentes nativos no macOS), operando **100% localmente** através de catálogos declarativos auditáveis.
- **Critérios de Aceite:**
  1. **Tweaks Essenciais (Windows):**
     - Criação de Ponto de Restauração (`SystemRestorePointCreationFrequency = 0` + `Checkpoint-Computer`).
     - Desativação completa de Telemetria da Microsoft (`AllowTelemetry = 0`, `ContentDeliveryManager`, `AdvertisingInfo`, `Siuf`, `WER`, variável `POWERSHELL_TELEMETRY_OPTOUT = 1` e desativação das 13 Scheduled Tasks de telemetria).
     - Otimização de Serviços (`SvcHostSplitThresholdInKB` ajustado ao total de RAM física + conversão dos ~50 serviços secundários para `Manual` e `DiagTrack`/`dmwappushservice` para `Disabled`).
     - Desativação de GameDVR (`GameConfigStore` e `AllowGameDVR = 0`).
     - Desativação de Activity History, Location Tracking, Wi-Fi Sense e Consumer Features (bloqueio de instalação silenciosa de bloatwares).
     - Ativação do botão "Finalizar Tarefa" (End Task) na barra de tarefas do Windows 11 (`TaskbarEndTask = 1`).
     - Gerenciamento de Hibernação (`powercfg /hibernate off` para liberar `hiberfil.sys`) e Storage Sense.
  2. **Tweaks Avançados e Performance (Windows):**
     - Ativação do plano de energia **Ultimate Performance** (`powercfg -duplicatescheme e9a42b02-d5df-448d-aa00-03f14749eb61`).
     - Desativação de Windows Copilot, Windows Recall e recursos de IA em segundo plano (`TurnOffWindowsCopilot`, `DisableAIDataAnalysis`, feature `Recall`, serviço `WSAIFabricSvc`).
     - Menu de Contexto Clássico do Windows 10 no Windows 11 (`CLSID {86ca1aa0-34aa-4e8b-a509-50c905bae2a2}`).
     - Microsoft Edge Debloat e Desativação do Bing Search no Menu Iniciar.
     - Otimização de Efeitos Visuais para Desempenho (`VisualFXSetting`).
     - Ferramentas de Reparo: Reset Windows Update, Reset Network (`winsock`/`ip`/`flushdns`) e System Corruption Scan (`DISM /RestoreHealth` + `sfc /scannow`).
  3. **Otimizações Nativas (macOS):**
     - Limpeza de Cache DNS (`dscacheutil -flushcache` + `mDNSResponder`).
     - Otimização de animações da interface (Dock delay zero, animações de abertura e redimensionamento via `defaults write`).
     - Gerenciamento de snapshots locais do Time Machine (`tmutil listlocalsnapshots /` e `tmutil thinlocalsnapshots`).
     - Reconstrução de cache do LaunchServices e diagnóstico de integridade APFS (`diskutil verifyVolume`).
  4. **Reversão Completa (`Undo`):** Cada tweak aplicado deve salvar o estado anterior exato da máquina em um arquivo local de snapshot (`outputs/snapshots/`) e permitir a restauração individual ou global com 1 clique/comando.

---

### RF-06: Relatório e Dashboard HTML Interativo Final
- **Descrição:** Ao finalizar a execução no terminal, o sistema deve gerar um arquivo HTML autônomo e exibir o link clicável no terminal (além de abri-lo automaticamente no navegador padrão).
- **Critérios de Aceite:**
  1. Exibir o **Relatório de Execução Autônoma**: total de espaço liberado na sessão (Antes vs. Depois), lista de todos os diretórios/arquivos limpos e todos os Tweaks de otimização aplicados.
  2. Exibir as abas organizadas para ação humana assistida:
     - Visão Geral & Saúde dos Discos (Antes vs. Depois).
     - Resultado da Limpeza Autônoma & Tweaks Aplicados.
     - Resíduos Órfãos & Caches Pendentes (com checklist interativo e comandos de remoção).
     - Aplicativos Instalados & Sugestões de Desinstalação/Migração.
     - Top 100 Maiores Arquivos do Sistema.
     - Diagnóstico de Cloud (OneDrive / iCloud) & Atualizações de Softwares.
  3. Persistir o progresso de revisão do usuário no `localStorage` do navegador.

---

### RF-07: Reanálise On-Demand do Sistema (Re-scan sem Reiniciar)
- **Descrição:** O Dashboard deve disponibilizar uma ação direta de "Reanalisar Sistema" que re-executa a varredura e atualização de métricas do sistema sem exigir encerramento ou reinicialização do comando no terminal.
- **Critérios de Aceite:**
  1. Disponibilizar botão "🔄 Reanalisar Sistema" no cabeçalho do Dashboard.
  2. Disparar nova verificação das partições/volumes, espaço livre, ocupantes e pendências.
  3. Atualizar em tempo real os contadores do topo (`stat-freed`, `stat-potential`) e os dados de cada uma das 7 abas sem perda de contexto.

---

### RF-08: Remoção Reativa e Ocultação Imediata de Pastas Órfãs na UI
- **Descrição:** Ao acionar a limpeza de pastas órfãs e caches selecionados na aba 4, os itens removidos com sucesso devem sair imediatamente da lista visual da tela.
- **Critérios de Aceite:**
  1. Ao clicar em "Limpar Selecionados", disparar requisição para o motor local e receber a lista de caminhos removidos (`cleaned_paths`).
  2. Remover imediatamente os itens apagados da listagem no DOM e atualizar a contagem de itens pendentes.
  3. Atualizar os totais de espaço liberado (`stat-freed`) e potencial adicional recuperável (`stat-potential`).
  4. Exibir feedback visual inequívoco (toast animado) com a quantidade exata de arquivos/pastas removidas e megabytes/gigabytes liberados no disco.

---

### RF-09: Drill-Down Dinâmico de Subpastas Pesadas (Top Ocupantes sem Poluição Visual)
- **Descrição:** Na aba 5 (Top 100 Maiores Arquivos e Pastas), permitir ao usuário expandir dinamicamente as subpastas mais pesadas de cada diretório ocupante.
- **Critérios de Aceite:**
  1. Identificar e calcular o peso das subpastas diretas mais volumosas durante a varredura (`sub_occupants`).
  2. Apresentar na tabela um controle visual intuitivo (ex: botão expansível `▶ Ver Subpastas (N)`) apenas para itens do tipo "Pasta" que possuam subpastas expressivas.
  3. Ao expandir, exibir uma lista aninhada limpa e indentada contendo o nome da subpasta, caminho, tamanho formatado e barra proporcional de impacto em relação à pasta pai.
  4. Manter a visão geral colapsada e limpa por padrão para evitar poluição visual.

---

### RF-10: Navegação Bidirecional entre Dashboard e Formulário Inicial de Seleção
- **Descrição:** Permitir ao usuário alternar facilmente entre o Dashboard de Resultados e a Janela Inicial de Parâmetros/Configuração.
- **Critérios de Aceite:**
  1. Incluir botão de navegação "⚙️ Nova Configuração / Início" no cabeçalho do Dashboard.
  2. Permitir retornar ao formulário inicial em `/` para alterar sistema operacional, escopo de varredura ou selecionar novos módulos/tweaks para nova execução.

---

### RF-11: Distribuição de Executáveis Standalone Autocontidos e Execução Oneliner
- **Descrição:** Permitir que o usuário final execute a aplicação no terminal (Windows ou macOS) com um **único comando oneliner**, sem necessidade de instalar Python, clonar repositório Git ou instalar dependências.
- **Critérios de Aceite:**
  1. **Empacotamento Standalone Autocontido:** Compilar a aplicação completa com todos os módulos, servidor local e catálogos declarativos embutidos em arquivos executáveis únicos (`limpeza-macos` para macOS e `limpeza-windows.exe` para Windows).
  2. **Zero Dependência do Ambiente Hospedeiro:** O executável deve conter seu próprio runtime isolado, funcionando mesmo em máquinas virgens que nunca tiveram interpretador Python instalado.
  3. **Comando Oneliner macOS:** Fornecer script de bootstrap (`install-macos.sh`) executável via:
     `curl -fsSL https://raw.githubusercontent.com/abdielcordeiro/limpeza-desktop/main/install-macos.sh | bash`
     O script baixa a versão compilada oficial mais recente do GitHub Releases, ajusta permissões e a executa diretamente no terminal.
  4. **Comando Oneliner Windows:** Fornecer script PowerShell de bootstrap (`install-windows.ps1`) executável via:
     `irm https://raw.githubusercontent.com/abdielcordeiro/limpeza-desktop/main/install-windows.ps1 | iex`
     O script baixa a versão oficial `limpeza-windows.exe` e a dispara diretamente.
  5. **Compatibilidade com Flags CLI:** Os scripts oneliner devem aceitar e repassar argumentos (ex: `--dry-run`, `--headless`, `--preset`).
  6. **Resolução de Recursos Embarcados:** O código deve resolver de forma transparente os arquivos de catálogo JSON (`windows_tweaks.json`, `macos_tweaks.json`, `safe_cleanup_rules.json`) tanto em tempo de desenvolvimento quanto empacotado no diretório temporário do executável (`_MEIPASS`).
  7. **Automação CI/CD:** O workflow de release no GitHub Actions deve compilar e disponibilizar os binários e seus hashes SHA-256 a cada nova versão taggeada.

---

## 2. Requisitos Não-Funcionais (RNF)

### RNF-01: Política Estrita Zero-Network & Zero-Telemetry (Privacidade Absoluta)
- **Especificação:** O sistema **JAMAIS** deve enviar qualquer dado da máquina, telemetria, endereço IP ou log para servidores externos, nem baixar scripts ou executáveis de terceiros.
- **Regras de Auditoria:**
  - Proibido o uso de bibliotecas de requisição HTTP (`requests`, `urllib.request`, `http.client`, `Invoke-RestMethod`, `Invoke-WebRequest`, `curl`) no motor de limpeza e otimização.
  - Todos os recursos do `ChrisTitusTech/winutil` que faziam comunicação externa (como bootstrap remoto `christitus.com/win`, download do binário proprietário `OOSU10.exe`, download de lista `hosts` de terceiros no GitHub, instalador remoto do Chocolatey e links de ping para `winutil.christitus.com`) são **estritamente banidos e removidos**.
  - O Dashboard HTML gerado deve funcionar **100% offline** (sem depender de CDNs externos de CSS/JS/Fontes para renderizar perfeitamente).

### RNF-02: Idempotência e Segurança Operacional
- **Especificação:** Executar a limpeza ou um mesmo Tweak 1 vez ou 10 vezes seguidas deve produzir o mesmo estado final consistente no sistema operacional, sem corromper chaves de registro, duplicar planos de energia (`powercfg`) ou gerar efeitos colaterais destrutivos.
- **Mecanismo:**
  - Antes de criar o plano *Ultimate Performance*, verificar se já existe um esquema ativo com esse GUID/nome para evitar dezenas de planos duplicados.
  - Antes de alterar qualquer chave de Registro (`winreg`), Serviço (`sc`) ou preferência (`defaults`), capturar e persistir o estado atual no `SnapshotManager` local caso ainda não tenha sido salvo o baseline original.

### RNF-03: Isolamento de Plataforma e Zero Dependências Pesadas
- **Especificação:** O núcleo deve rodar em Python 3.9+ utilizando prioritariamente a biblioteca padrão do Python (`os`, `sys`, `shutil`, `pathlib`, `subprocess`, `json`, `winreg`, `plistlib`, `ctypes`, `http.server` / `tkinter`), garantindo execução imediata no terminal Windows e macOS sem exigir compiladores C++ ou centenas de megabytes de pacotes externos.

### RNF-04: Eficiência de Memória e CPU
- **Especificação:** Durante a varredura de discos com centenas de milhares de arquivos, utilizar iteradores eficientes (`os.scandir`) e poda imediata de árvores de sistema imutáveis (`WinSxS`, `/System/Volumes/Preboot`, `/System/Volumes/VM`, `/dev`, `/proc`), mantendo o uso de memória RAM abaixo de 150 MB e evitando travamentos de I/O.
