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

### RF-12: Esvaziamento Nativo da Lixeira e Deleção Resiliente de Arquivos Read-Only / Bloqueados
- **Descrição:** Garantir que o esvaziamento da Lixeira (macOS e Windows) e a limpeza de pastas órfãs/caches ocorra com sucesso mesmo na presença de proteções de sistema (TCC do macOS), atributos somente leitura (`readonly`) ou flags de arquivo imutáveis (`uchg`).
- **Critérios de Aceite:**
  1. **Esvaziamento Nativo da Lixeira no macOS:** A regra `mac_trash` deve utilizar a API oficial do Finder via AppleScript (`tell application "Finder" to empty trash`) para transpor a restrição de TCC (`PermissionError: [Errno 1] Operation not permitted`), complementado por rotina de limpeza de flags (`chflags -R nouchg ~/.Trash/*`) e remoção direta.
  2. **Esvaziamento Nativo da Lixeira no Windows:** A regra de lixeira deve utilizar a API Win32 nativa `SHEmptyRecycleBinW` da `shell32.dll` (ou PowerShell `Clear-RecycleBin -Force -ErrorAction SilentlyContinue`) para garantir que todos os arquivos sejam removidos e a interface do Windows Explorer atualizada.
  3. **Deleção Resiliente de Arquivos e Pastas com Read-Only:** Implementar handler de remoção forçada em `_clean_directory_contents` e `clean_specific_paths`. Se `os.remove`, `os.rmdir` ou `shutil.rmtree` falharem por falta de permissão de escrita, o sistema deve automaticamente adicionar permissão de escrita (`os.chmod(path, stat.S_IWRITE | stat.S_IWUSR)`) e tentar a exclusão novamente antes de contabilizar erro.
  4. **Suporte a Simulação (Dry-Run):** Em modo `DRY_RUN`, consultar o número de itens na lixeira via AppleScript (macOS) ou WMI/Shell32 (Windows) e reportar o volume recuperável sem esvaziar o conteúdo real.
  5. **Auditoria e Logs:** Registrar detalhadamente na saída do console e no relatório HTML quantos arquivos foram removidos com sucesso da lixeira e de cada diretório de cache.


---

### RF-13: Diagnóstico e Monitoramento de Saúde de Hardware e Periféricos (SSD/HDD S.M.A.R.T., RAM, GPU e Bateria)
- **Descrição:** Coletar métricas essenciais de integridade física e operacional dos principais componentes e periféricos do computador (Storage SSD/HDD, Memória RAM, Placa de Vídeo / GPU, Processador e Bateria de Laptops) utilizando ferramentas nativas do sistema operacional (WMI/PowerShell no Windows e sysctl/system_profiler/diskutil no macOS), sem dependências pesadas em C++ ou bibliotecas proprietárias de telemetria.
- **Critérios de Aceite:**
  1. **Saúde de SSD / HDD:**
     - **Windows:** Detectar tipo de mídia (`MediaType`: SSD, HDD, NVMe), status de integridade (`HealthStatus`: Healthy, Warning, Unhealthy), percentual de desgaste (`Wear` / vida útil restante se disponível via `Get-StorageReliabilityCounter`), horas ligado (`PowerOnHours`), temperatura operacional e previsão de falha S.M.A.R.T. (`MSStorageDriver_FailurePredictStatus`).
     - **macOS:** Consultar `system_profiler SPStorageDataType` / `SPNVMeDataType` / `diskutil info` para obter status S.M.A.R.T. (`Verified`, `Failing`, `Not Supported`), suporte a TRIM (`TRIM Support: Yes/No`), protocolo de conexão (Apple Fabric / NVMe / SATA) e capacidade total/livre.
  2. **Diagnóstico de Memória RAM & Pressão de Swap:**
     - **Windows:** Medir percentual de carga de memória (`dwMemoryLoad`), RAM física total vs livre e relação de tamanho do arquivo de paginação (`TotalPageFile` vs `AvailPageFile`). Emitir alerta se a carga de RAM estiver acima de 85% e o arquivo de paginação estiver sob uso intenso (risco de lentidão e desgaste acelerado do SSD por swap contínuo).
     - **macOS:** Inspecionar `vm_stat` e `sysctl` para obter RAM total, RAM ativa/inativa/wired, memória comprimida e uso de swap (`sysctl vm.swapusage`). Avaliar nível de pressão de memória (`Normal`, `Warning`, `Critical`).
  3. **Diagnóstico de Placa de Vídeo (GPU):**
     - **Windows:** Identificar adaptadores gráficos via WMI (`Win32_VideoController`), extraindo Modelo/Fabricante (NVIDIA, AMD, Intel), VRAM dedicada, versão do driver instalada e status operacional. Se `nvidia-smi` estiver no PATH, extrair temperatura da GPU, uso atual de VRAM e consumo em watts.
     - **macOS:** Consultar `system_profiler SPDisplaysDataType` identificando o modelo da GPU / SoC Apple Silicon (ex: Apple M1/M2/M3/M4 Max/Pro, AMD Radeon, Intel Iris), núcleos de GPU e suporte à API Metal.
  4. **Diagnóstico de Bateria e Alimentação (Laptops):**
     - **Windows:** Consultar `Win32_Battery` ou gerar dados de capacidade (`FullChargeCapacity` vs `DesignCapacity`) para calcular a saúde percentual da bateria (`Health = FullCharge / Design * 100`) e estimativa de tempo restante.
     - **macOS:** Consultar `system_profiler SPPowerDataType` obtendo contagem de ciclos (`Cycle Count`), condição da bateria (`Normal`, `Service Recommended`), capacidade máxima percentual e estado de carregamento.
  5. **Motor de Alertas Preventivos e Ações Recomendadas:**
     - Alerta de Falha Iminente de Disco (S.M.A.R.T. com Warning/Failing): recomendação imediata de backup dos dados pessoais.
     - Alerta de RAM Crítica / Swap Thrashing: recomendação de encerramento de processos em background ou aumento de memória física.
     - Alerta de Bateria Degradada (> 800-1000 ciclos ou saúde < 80%): recomendação de recalibração ou substituição para evitar estufamento.
     - Alerta de TRIM Inativo em SSDs externos/secundários.

---

### RF-14: Otimização Inteligente de Armazenamento (Desfragmentação HDD vs TRIM SSD no Windows & Otimização APFS no macOS) com Guardrails Anti-Degradação de NVMe
- **Descrição:** Oferecer um recurso de ajuste e manutenção preventiva dos discos do usuário durante a rotina de limpeza, diferenciando estritamente unidades de estado sólido (SSD/NVMe) de discos rígidos magnéticos tradicionais (HDD) para maximizar desempenho sem degradar a vida útil da memória flash.
- **Critérios de Aceite:**
  1. **Guardrails Anti-Degradação de 4 Camadas para Identificação de NVMe/SSD:**
     - **Camada 1 (PowerShell Storage API):** `Get-PhysicalDisk` inspecionando `MediaType` (SSD, HDD, SCM) e `BusType` (NVMe, SATA, USB).
     - **Camada 2 (WMI/CIM Fallback & SeekPenalty):** Consulta a `MSFT_PhysicalDisk` e `Win32_DiskDrive`. Avaliação de `SpindleSpeed` (RPM = 0 indica SSD; 5400/7200 RPM indica HDD) e `SeekPenalty` (`SeekPenalty == False` comprova ausência de cabeça mecânica, confirmando SSD/NVMe).
     - **Camada 3 (Defrag Assessment Pre-check):** Execução de `defrag <drive>: /A` onde o motor nativo do Windows sinaliza a recomendação do volume (Retrim vs Defrag).
     - **Camada 4 (Fail-Safe Default Absoluto):** Se qualquer camada falhar, retornar nulo ou houver discrepância entre fontes de dados, o sistema **obrigatoriamente assume que a unidade é um SSD/NVMe**, bloqueando de forma irreversível a desfragmentação tradicional de blocos e liberando apenas TRIM.
  2. **Validação e Confirmação Explícita com o Usuário (Human-in-the-Loop Safety):**
     - A interface gráfica e a CLI devem listar explicitamente cada partição com o tipo de mídia identificado (ex: `C: [NVMe SSD - Samsung 980 PRO 1TB] - Otimização Segura: TRIM`).
     - **Trava de Segurança para HDD:** Caso uma partição seja identificada como HDD mecânico e a desfragmentação tradicional seja solicitada, o sistema deve **obrigatoriamente solicitar confirmação explícita ao usuário** (via diálogo na Janela/Dashboard ou prompt no terminal):
       > *"O volume [X:] foi identificado como DISCO RÍGIDO MECÂNICO (HDD). Desfragmentar uma unidade SSD ou NVMe reduz desnecessariamente sua vida útil. Confirma que este disco é de fato um HDD mecânico e NÃO um SSD/NVMe?"*
     - Caso o usuário responda Negativo ou assinale que se trata de um SSD, a desfragmentação de blocos é cancelada imediatamente e a unidade é reclassificada para tratamento de SSD (apenas TRIM).
  3. **Execução Diferenciada no Windows:**
     - **Se HDD Confirmado:** Executar análise de taxa de fragmentação (`defrag.exe <drive>: /A` ou `Optimize-Volume -DriveLetter <drive> -Analyze`). Se fragmentação > 5%, executar desfragmentação tradicional (`Optimize-Volume -DriveLetter <drive> -Defrag` ou `defrag.exe <drive>: /U /V`).
     - **Se SSD / NVMe:** **PROIBIR desfragmentação tradicional**. Executar exclusivamente **Retrim / TRIM e Consolidação de Slabs** (`Optimize-Volume -DriveLetter <drive> -ReTrim` ou `defrag.exe <drive>: /L`), informando ao controlador SSD quais blocos liberados podem ser limpos internamente pelo Garbage Collector.
  4. **Manutenção Preventiva de Disco no macOS (APFS & HFS+):**
     - No macOS moderno com APFS (Apple Silicon e Macs com SSD), desfragmentação manual não existe por projeto arquitetural do APFS (Copy-on-Write com gerenciamento dinâmico).
     - O recurso de "Ajuste de Disco" no macOS deve executar:
       - Verificação de consistência e integridade das estruturas de catálogo APFS via `diskutil verifyVolume /`.
       - Diagnóstico de suporte a TRIM (`TRIM Support`) para garantir que o kernel está notificando o SSD.
       - Consolidação e expurgo de snapshots locais antigos (`tmutil thinlocalsnapshots / <bytes> 4`) para liberar espaço retido por blocos COW órfãos.
  5. **Segurança Operacional e Idempotência:**
     - Operações de otimização de disco devem rodar com prioridade baixa de I/O para não congelar o sistema do usuário.
     - Se o computador for um laptop rodando exclusivamente em bateria com menos de 20% de carga, a otimização de disco deve ser pausada/alertada para evitar desligamento abrupto no meio de I/O intensivo.
  6. **Modo Simulação (Dry-Run):**
     - Em modo `dry-run`, o sistema apenas analisa a taxa de fragmentação (Windows HDD), consulta status TRIM e integridade do volume APFS (macOS) e relata o que seria executado sem acionar I/O destrutivo.

---

### RF-15: Varredura Profunda e Limpeza Cirúrgica para macOS Apple Silicon (Containers, Dev Ecosystems, Darwin Caches, APFS System Data & Bundle-ID Correlation)
- **Descrição:** Maximizar a recuperação real e segura de espaço no macOS (Apple Silicon M1/M2/M3/M4 e Intel), eliminando os gargalos de varredura rasa e cobrindo caches de containers sandboxed, diretórios Darwin por usuário, ecossistemas modernos de desenvolvimento, dados do sistema ("System Data" / APFS Purgeable) e correlação precisa de resíduos órfãos por `CFBundleIdentifier`.
- **Critérios de Aceite:**
  1. **Expansão Cirúrgica do Catálogo de Limpeza Autônoma do macOS (`safe_cleanup_rules.json`):**
     - Varredura segura de `~/Library/Caches/*` protegida por whitelist estrita de estados críticos (`CloudKit`, `com.apple.nsurlsessiond`, `com.apple.bird`, `com.apple.HomeKit`, `com.apple.Safari.SafeBrowsing`, `AudioUnitCache`, `PassKit`, `GeoServices`).
     - Limpeza de caches e logs em Containers Sandboxed: `~/Library/Containers/*/Data/Library/Caches/*`, `~/Library/Containers/*/Data/Library/Logs/*`, `~/Library/Group Containers/*/Library/Caches/*`.
     - Limpeza de caches temporários Darwin por usuário resolvidos via `getconf DARWIN_USER_CACHE_DIR` e `getconf DARWIN_USER_TEMP_DIR` (`/private/var/folders/.../C/` e `/T/`), removendo caches reconstruíveis de Metal shaders, Clang, QuickLook e ícones.
     - Limpeza segmentada por ecossistema de desenvolvimento:
       - **Xcode & Apple SDK:** `DerivedData`, `iOS DeviceSupport`, `watchOS DeviceSupport`, `tvOS DeviceSupport`, `Archives`, `CoreSimulator/Caches`, `com.apple.dt.Xcode`.
       - **JetBrains & Android Studio:** `~/Library/Caches/JetBrains`, `~/Library/Logs/JetBrains`, `~/Library/Caches/Google/AndroidStudio*`.
       - **Node.js / Frontend:** `~/.npm/_cacache`, `~/Library/Caches/Yarn`, `~/.yarn/berry/cache`, `~/Library/Caches/pnpm`, `~/.bun/install/cache`, `~/Library/Caches/Cypress`, `~/Library/Caches/ms-playwright`.
       - **Python:** `~/Library/Caches/pip`, `~/.cache/pip`, `~/Library/Caches/uv`, `~/.cache/uv`, `~/Library/Caches/pypoetry`, `~/.cache/mypy`, `~/.cache/ruff`, `~/.cache/pytest`, `~/.cache/pre-commit`.
       - **JVM / Mobile / Rust / Go:** `~/.gradle/caches`, `~/.cargo/registry/cache`, `~/Library/Caches/go-build`, `~/Library/Caches/CocoaPods`, `~/.pub-cache/_temp`.
       - **Homebrew & Containers:** `~/Library/Caches/Homebrew`, `~/Library/Logs/Homebrew`, logs de Docker/OrbStack/Colima.
  2. **Orçamento Adaptativo de Varredura BFS e Medição Física APFS (`st_blocks * 512`):**
     - Elevar o orçamento da varredura `DiskScannerAdapter` de `2.500` para orçamento adaptativo de até `25.000` diretórios por execução, com medição rápida de pacotes fechados (`.app`, `node_modules`, `.git`, `.xcarchive`, `.simruntime`) de até `25.000` arquivos utilizando blocos físicos reais (`st_blocks * 512`) no macOS para evitar distorção de sparse files ou placeholders do iCloud.
  3. **Escopo `SMART_FAST` Abrangente no macOS:**
     - Incluir `~/Library/Developer`, `~/Library/Group Containers`, `~/Library/HTTPStorages`, `~/Library/WebKit`, `~/.cache`, `~/.npm`, `~/.gradle`, `~/.cargo`, `~/.orbstack`, `~/Library/Messages/Attachments` e `~/Library/Application Support/MobileSync/Backup` (classificando backups de iOS e anexos de mensagens para revisão consciente do usuário).
  4. **Correlação Estruturada de Resíduos Órfãos (Inspirado no Pearcleaner):**
     - Evitar a explosão de pacotes `com.apple.pkg.*` do `pkgutil` em tokens genéricos curtos de 3 letras que causavam falsos negativos.
     - Correlacionar pastas de 12 subdiretórios da `~/Library` (`Application Support`, `Containers`, `Group Containers`, `Caches`, `Preferences`, `Saved Application State`, `HTTPStorages`, `WebKit`, `Logs`, `Cookies`, `Application Scripts`) por `CFBundleIdentifier` completo, prefixo Reverse-DNS e nome canônico do aplicativo.
     - Não incluir `LaunchAgents` quebrados (cujo binário executável alvo não existe mais no disco) na Camada 3 de proteção, permitindo que seus resíduos órfãos sejam detectados.

---

### RF-16: Ganchos Interativos na Aplicação Web para Ações Diretas de Arquivo, Execução Granular e Gerenciamento de Pacotes
- **Descrição:** Dotar o Dashboard Web local (`127.0.0.1`) de ganchos interativos em tempo real em todas as abas relevantes, permitindo ao usuário executar ações diretas de limpeza, quarentena na Lixeira, inspeção no Finder/Explorer e atualização de pacotes sem precisar reiniciar o fluxo ou usar o terminal manualmente.
- **Critérios de Aceite:**
  1. **Ação Direta sobre Arquivos e Pastas (`POST /api/file-action`):**
     - Disponível para itens da **Aba 4 (Pastas Órfãs & Caches)** e da **Aba 5 (Top 100 Maiores Arquivos & Pastas + Drill-Down de Subpastas)** que não estejam classificados como `🚫 Não Apagar (Sistema Operacional)`.
     - Suportar dois modos de remoção selecionáveis pelo usuário:
       - **`trash` (Mover para a Lixeira — Padrão Seguro Recomendado):** Move o arquivo ou diretório para a Lixeira nativa do usuário (`~/.Trash` no macOS com resolução de colisão de nomes ou Lixeira do Windows) para fácil recuperação caso necessário.
       - **`delete` (Exclusão Permanente):** Remove definitivamente utilizando o motor resiliente (`_clean_directory_contents` com desbloqueio `chmod`/`chflags nouchg`).
     - Rejeitar com erro HTTP 403 qualquer tentativa de exclusão de caminhos protegidos pelo guardrail `is_safe_path_to_clean()` ou classificados como `DO_NOT_DELETE`.
     - Atualizar reativamente o DOM (removendo a linha do item/subpasta apagada) e recalcular instantaneamente os contadores de espaço liberado no topo do Dashboard.
  2. **Revelar no Finder / Windows Explorer (`POST /api/reveal-path`):**
     - Botão `"📂 Abrir Local"` em cada linha das Abas 3, 4 e 5 que aciona `open -R <path>` no macOS ou `explorer.exe /select,<path>` no Windows para destacar o item no gerenciador de arquivos nativo.
  3. **Execução Individual de Regra de Limpeza Autônoma (`POST /api/execute-rule`):**
     - Na **Aba 2 (Limpeza Autônoma)**, exibir botão `"🧹 Limpar Agora"` para cada regra que tenha sido apenas simulada (`SIMULATED` em modo Dry-Run) ou que possua espaço recuperável, permitindo limpar aquela categoria específica sob demanda e atualizar seu status para `CLEANED` em tempo real.
  4. **Ação Interativa de Atualização e Limpeza de Pacotes (`POST /api/upgrade-packages`):**
     - Na **Aba 7 (Cloud & Atualizações)**, permitir acionar a atualização individual de um pacote (`brew upgrade <id>` / `winget upgrade --id <id>`) ou executar `brew cleanup --prune=all` no macOS diretamente pela interface web, exibindo o resultado em toast/log.

---

### RF-17: Telemetria Profunda de Saúde, Inspetor de Persistência/Processos e Motor Consultivo de Vida Útil (`Longevity Health Score 0–100`)
- **Descrição:** Transformar o painel de Hardware e Saúde em um consultor interativo de conservação e longevidade da máquina, coletando telemetria nativa precisa de engenharia (IOKit/`ioreg` no Apple Silicon e WMI/CIM no Windows), auditando agentes de inicialização órfãos (`LaunchAgents` / `Startup`), inspecionando processos pesados/zumbis e fornecendo recomendações acionáveis em 1 clique.
- **Critérios de Aceite:**
  1. **Telemetria Profunda Apple Silicon & Windows:**
     - **Bateria via IOKit (`ioreg -rn AppleSmartBattery -a`):** Extrair `CycleCount`, `DesignCapacity` (mAh), `RawMaxCapacity` (mAh), saúde calculada real (`%`), temperatura da bateria (`°C`), tensão (`mV`), corrente (`mA`), potência e estado de carga, eliminando falhas de parsing do `system_profiler`.
     - **Memória Unificada & Swap Thrashing:** Ler `hw.pagesize` (`16384` bytes no Apple Silicon), calcular memória `Active`, `Wired`, `Compressed` e `Cached`, ler nível de pressão real do kernel (`kern.memorystatus_vm_pressure_level`) e monitorar contadores de `Pageouts`/`Swapouts`.
     - **Storage APFS & Snapshots:** Extrair `Purgeable Space` (`diskutil info -plist /`) e contagem de snapshots locais do Time Machine (`tmutil listlocalsnapshots /`).
  2. **Auditoria Interativa de Persistência e Inicialização (`LaunchAgents` / `LaunchDaemons` / `Windows Startup`):**
     - Inspecionar todos os arquivos `.plist` em `~/Library/LaunchAgents`, `/Library/LaunchAgents` e `/Library/LaunchDaemons` (e chaves `HKCU/HKLM...\Run` no Windows).
     - Extrair o caminho do binário alvo (`Program` ou `ProgramArguments[0]`) e verificar se o executável existe no disco (`target_exists`).
     - Classificar itens com binário ausente como **Agente Órfão / Quebrado (Broken Startup Agent)** e disponibilizar endpoint `POST /api/startup-action` (com backup automático no diretório de snapshots) para remover ou desativar o agente órfão com 1 clique.
  3. **Inspetor de Processos Pesados & Zumbis e Refresh Leve (`GET /api/live-health` & `POST /api/process-action`):**
     - Listar os Top 10 processos consumidores de RAM e CPU (`ps -axo pid,ppid,stat,%cpu,%mem,rss,comm` no macOS / `tasklist` ou PowerShell `Get-Process` no Windows) e identificar processos zumbis (`stat` começando com `Z`).
     - Permitir atualizar a telemetria de saúde em tempo real via `GET /api/live-health` (< 500ms, sem re-escanear o disco inteiro) e encerrar processos de usuário travados/pesados via `POST /api/process-action` (protegendo processos root/kernel do SO).
  4. **Score de Saúde & Vida Útil (`Longevity Health Score 0–100`) e Consultor de Longevidade:**
     - Calcular um score auditável de `0` a `100` composto por 4 pilares:
       1. *Saúde de Armazenamento, Margem Livre NAND & Snapshots (35 pts)*
       2. *Memória Unificada & Proteção contra Swap Thrashing no SSD (25 pts)*
       3. *Higiene de Caches, Resíduos Órfãos & Persistência de Boot (20 pts)*
       4. *Saúde Elétrica/Térmica (Bateria, Ciclos, Temperatura) & Atualizações (20 pts)*
     - Gerar cartões de **Recomendações Acionáveis de Vida Útil** explicando: **(a) Diagnóstico Atual**, **(b) Impacto Físico na Vida Útil do Hardware** (ex: *Write Amplification* em células NAND flash, desgaste de TBW por swap contínuo, degradação química de Li-Ion) e **(c) Botão de Ação Direta 1-Clique** integrado aos ganchos da API local.

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
