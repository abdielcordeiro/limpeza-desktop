# System Design & Modelagem C4 (`limpeza-desktop`)

Este documento descreve a arquitetura de software do **Limpeza & Otimização Desktop Multiplataforma (Windows & macOS)** sob os padrões **Monólito Modular**, **Clean Architecture** e **Arquitetura Hexagonal (Ports & Adapters)**.

---

## 1. Visão Geral e Fluxo de Ponta a Ponta (Execução + Ganchos Interativos Web `127.0.0.1`)

```mermaid
sequenceDiagram
    autonumber
    actor User as Usuário (Terminal Windows / macOS)
    participant CLI as Entrypoint CLI (main.py)
    participant LocalServer as Servidor Local 127.0.0.1 (Launcher & Interactive Web Hooks)
    participant Orchestrator as Application Orchestrator (Use Cases)
    participant OSAdapter as Adapters de SO (Windows / macOS Apple Silicon)
    participant Snapshot as Snapshot & Restore Manager (Local)
    participant Reporter as Gerador Dashboard HTML Offline (8 Abas)

    User->>CLI: Executa comando no terminal (python main.py)
    CLI->>OSAdapter: Detecta SO (Windows/macOS), Privilégios, Partições e Telemetria IOKit/WMI
    CLI->>LocalServer: Inicia servidor estrito em 127.0.0.1 e abre Janela Inicial
    User->>LocalServer: Seleciona SO, Limpeza Autônoma, Scanner Profundo e Tweaks
    LocalServer->>Orchestrator: POST /api/execute (ExecutionPlanDTO)
    alt Se Otimizações (Tweaks) ou Ações Destrutivas selecionadas
        Orchestrator->>Snapshot: Cria Ponto de Restauração + Snapshot JSON de Estado Original
    end
    Orchestrator->>OSAdapter: 1. Executa Limpeza Autônoma (Temp, Containers, Darwin Caches, Dev Caches, Lixeira)
    Orchestrator->>OSAdapter: 2. Executa 5 Camadas (Bundle-ID Correlation) + Scanner BFS Adaptativo + Startup Audit
    Orchestrator->>OSAdapter: 3. Coleta Telemetria Profunda (AppleSmartBattery, Swap/VM, APFS Purgeable, Processos)
    Orchestrator->>Orchestrator: 4. Calcula Longevity Health Score (0-100) e Recomendações Acionáveis
    Orchestrator->>Reporter: Consolida SystemExecutionReport completo
    Reporter-->>LocalServer: Salva outputs/relatorio_limpeza_disco.html e serve /report
    User->>LocalServer: Aciona Ganchos Interativos (/api/file-action, /api/reveal-path, /api/execute-rule, /api/startup-action, /api/process-action, /api/live-health)
    LocalServer->>Orchestrator: Executa ação cirúrgica (Lixeira/Exclusão/Startup/Processo/Upgrade)
    Orchestrator-->>LocalServer: Retorna delta atualizado e regrava relatório HTML
    LocalServer-->>User: Atualiza DOM, métricas de espaço e Longevity Score em tempo real
```

---

## 2. Diagramas C4

### 2.1. Nível 1 — Diagrama de Contexto do Sistema

> [!NOTE]
> Por determinação estrita de privacidade (**RNF-01: Zero-Network Policy**), o sistema opera 100% dentro da máquina local do usuário, sem qualquer conexão com servidores na nuvem ou envio de telemetria.

```mermaid
flowchart TD
    User["👤 Usuário (Windows 10/11 ou macOS Apple Silicon / Intel)"]
    System["🛡️ Limpeza & Otimização Desktop<br/>(CLI + Servidor Local 127.0.0.1 + Motor Autônomo + Consultor de Vida Útil)"]
    OS_FS["💽 Sistema de Arquivos Local<br/>(NTFS / APFS, Partições, Containers Sandboxed, DARWIN_USER_CACHE_DIR, AppData, ~/Library)"]
    OS_Kernel["⚙️ Subsistema Nativo do SO<br/>(Windows Registry, Services, WMI / macOS IOKit ioreg, defaults, launchctl, diskutil, tmutil, vm_stat)"]
    Browser["🌐 Navegador Local do Usuário<br/>(Dashboard Interativo 127.0.0.1 com Ganchos de Ação & Modo Offline)"]

    User -->|"1. Inicia via Terminal e escolhe opções na Janela"| System
    System -->|"2. Varre, analisa, move para Lixeira ou limpa temporários/órfãos"| OS_FS
    System -->|"3. Coleta telemetria IOKit/WMI, audita LaunchAgents e aplica Tweaks com Snapshot"| OS_Kernel
    System -->|"4. Serve Dashboard interativo com Web Hooks locais e relatório HTML offline"| Browser
    Browser -->|"5. Executa exclusões seguras, abre Finder/Explorer, limpa regras e aplica recomendações 1-Click"| User
```

---

### 2.2. Nível 2 — Diagrama de Containers (Monólito Modular)

```mermaid
flowchart TB
    subgraph Host["Máquina Local do Usuário (Windows ou macOS)"]
        CLI["💻 Terminal Entrypoint<br/>(main.py)"]
        GUI_Server["🪟 Servidor HTTP Local 127.0.0.1<br/>(local_server.py: Launcher UI + REST Web Hooks API)"]
        
        subgraph CoreApp["Núcleo da Aplicação (Clean Architecture / Hexagonal)"]
            ModProbe["📦 Módulo: System Probe<br/>(Detecção de SO, Partições APFS/NTFS e Saúde)"]
            ModCleaner["📦 Módulo: Autonomous & Surgical Cleaner<br/>(Temp, Containers, Darwin Caches, Dev Ecosystems, Quarentena Lixeira)"]
            ModScanner["📦 Módulo: Deep Scanner & Bundle-ID Orphans<br/>(BFS Adaptativo 25k, st_blocks APFS, 12 Pastas ~/Library, Sub-Occupants)"]
            ModOptimizer["📦 Módulo: System Optimizer<br/>(Motor Declarativo WinUtil Sanitizado & macOS Tweaks)"]
            ModCloud["📦 Módulo: Cloud & Packages<br/>(Diagnóstico OneDrive / iCloud & Upgrade Interativo winget / brew)"]
            ModHardware["📦 Módulo: Hardware Telemetry, Startup & Longevity Advisor<br/>(IOKit ioreg Battery, VM Pressure, S.M.A.R.T., LaunchAgents Audit, Top Processes, Score 0-100)"]
        end

        Catalogs["📄 Catálogos Declarativos Offline<br/>(windows_tweaks.json, macos_tweaks.json, safe_cleanup_rules.json)"]
        Snapshots["⏪ Cofre de Snapshots & Undo<br/>(outputs/snapshots/*.json)"]
        HTMLReport["📊 Dashboard HTML Interativo (8 Abas)<br/>(outputs/relatorio_limpeza_disco.html)"]
    end

    CLI --> GUI_Server
    GUI_Server --> CoreApp
    ModOptimizer --> Catalogs
    ModCleaner --> Catalogs
    ModOptimizer --> Snapshots
    ModCleaner --> Snapshots
    ModHardware --> Snapshots
    CoreApp --> HTMLReport
    HTMLReport -.->|"Web Hooks Locais (/api/*)"| GUI_Server
```

---

### 2.3. Nível 3 — Diagrama de Componentes (Ports & Adapters)

```mermaid
flowchart LR
    subgraph Presentation["Camada de Entrada & Apresentação (Primary Adapters)"]
        EntryCLI["CLI Runner (main.py)"]
        LocalWebServer["LocalControlPanelServer (127.0.0.1)<br/>• GET /, /report, /api/context, /api/status, /api/live-health<br/>• POST /api/execute, /api/clean-selected, /api/file-action<br/>• POST /api/reveal-path, /api/execute-rule, /api/reanalyze<br/>• POST /api/inspect-directory, /api/optimize-disk<br/>• POST /api/startup-action, /api/process-action<br/>• POST /api/upgrade-packages, /api/undo"]
        HTMLGen["HTML Dashboard Generator (html_reporter.py)"]
    end

    subgraph Application["Camada de Aplicação (OrchestratorService / Use Cases)"]
        UC_Plan["Build & Execute Plan"]
        UC_Clean["Autonomous & Single-Rule Cleanup"]
        UC_FileAct["Interactive File Action (Trash / Delete / Reveal / Inspect Tree)"]
        UC_Scan["Deep Disk Scan, Storage X-Ray ('Documentos' & 'Dados do Sistema') & Bundle-ID Orphans"]
        UC_Opt["Apply & Revert System Tweaks (Undo)"]
        UC_Hw["Live Hardware Telemetry, Startup & Process Inspector"]
        UC_Advisor["Longevity Health Score (0-100) & Actionable Advisor"]
        UC_DskOpt["Storage Optimizer (4-Layer NVMe Guardrails)"]
    end

    subgraph Domain["Camada de Domínio (Pura - Sem Dependências Externas)"]
        Entities["Entities: PartitionInfo, CleanableItem, OccupantItem, InstalledAppInfo,<br/>StorageCategoryBreakdown, StorageXRayReport, DirectoryInspectionNode,<br/>HardwareHealthInfo, StorageDiskHealth, MemoryDiagnostics, BatteryHealth,<br/>StartupItemInfo, ProcessDiagnosticInfo, LongevityRecommendation, LongevityScoreReport"]
        ValueObjects["Value Objects: OSPlatform, RiskLevel, SafetyClassification, ExecutionMode, ScanScope"]
        Ports["Interfaces de Porta (Ports):<br/>ISystemProbePort, IActiveAppsPort, IFileSystemCleanerPort, IDiskScannerPort,<br/>ISystemTweakPort, ICloudAndPackagesPort, IHardwareProbePort, IStorageOptimizationPort, ISnapshotRepositoryPort"]
    end

    subgraph Infrastructure["Camada de Infraestrutura (Secondary Adapters)"]
        WinAdapter["🪟 Windows Adapter<br/>(winreg, sc.exe, schtasks, powercfg, Optimize-Volume, ctypes, WMI/CIM, explorer.exe)"]
        MacAdapter["🍎 macOS Apple Silicon Adapter<br/>(ioreg AppleSmartBattery, plistlib, defaults, launchctl, diskutil -plist, tmutil, vm_stat, getconf, open -R)"]
        LocalFSAdapter["📂 FileSystem, Native Trash & Snapshot JSON Adapter"]
    end

    EntryCLI --> LocalWebServer
    LocalWebServer --> UC_Plan
    LocalWebServer --> UC_Clean
    LocalWebServer --> UC_FileAct
    LocalWebServer --> UC_Scan
    LocalWebServer --> UC_Opt
    LocalWebServer --> UC_Hw
    LocalWebServer --> UC_Advisor
    LocalWebServer --> UC_DskOpt
    LocalWebServer --> HTMLGen

    UC_Plan --> Ports
    UC_Clean --> Ports
    UC_FileAct --> Ports
    UC_Scan --> Ports
    UC_Opt --> Ports
    UC_Hw --> Ports
    UC_Advisor --> Ports
    UC_DskOpt --> Ports

    Ports -.->|"Implementado por"| WinAdapter
    Ports -.->|"Implementado por"| MacAdapter
    Ports -.->|"Implementado por"| LocalFSAdapter
```

---

### 2.4. Nível 4 — Diagrama de Implantação e Distribuição Standalone (Deployment Diagram)

```mermaid
flowchart TD
    subgraph GitHubPlatform["Ecossistema GitHub (Hospedagem & CI/CD)"]
        Repo["Repositório Git<br/>(abdielcordeiro/limpeza-desktop)"]
        GHA["GitHub Actions CI/CD Pipeline<br/>(release.yml)"]
        ReleaseAsset["GitHub Releases Oficial<br/>• limpeza-macos<br/>• limpeza-windows.exe<br/>• checksums.sha256"]
        BootstrapScripts["Scripts de Inicialização Oneliner<br/>• install-macos.sh<br/>• install-windows.ps1"]
    end

    subgraph UserMac["Máquina do Usuário (macOS Apple Silicon / Intel)"]
        MacTerminal["Terminal / zsh<br/>curl -fsSL install-macos.sh | bash"]
        MacRunner["Processo Standalone:<br/>/tmp/limpeza-macos"]
        MacBrowser["Navegador Safari / Chrome / Arc<br/>http://127.0.0.1:porta"]
    end

    subgraph UserWin["Máquina do Usuário (Windows 10/11)"]
        WinTerminal["PowerShell Admin<br/>irm install-windows.ps1 | iex"]
        WinRunner["Processo Standalone:<br/>%TEMP%\\limpeza-windows.exe"]
        WinBrowser["Navegador Edge / Chrome<br/>http://127.0.0.1:porta"]
    end

    Repo -->|"Git Tag v* / Workflow Dispatch"| GHA
    GHA -->|"Compilação PyInstaller Matrix"| ReleaseAsset
    Repo -->|"Raw Content"| BootstrapScripts

    MacTerminal -->|"1. Baixa script de bootstrap"| BootstrapScripts
    MacTerminal -->|"2. Baixa binário mais recente"| ReleaseAsset
    MacTerminal -->|"3. Executa standalone"| MacRunner
    MacRunner -->|"4. Abre painel interativo local"| MacBrowser

    WinTerminal -->|"1. Baixa script de bootstrap"| BootstrapScripts
    WinTerminal -->|"2. Baixa executável mais recente"| ReleaseAsset
    WinTerminal -->|"3. Executa standalone"| WinRunner
    WinRunner -->|"4. Abre painel interativo local"| WinBrowser
```

---

## 3. Organização de Diretórios (Clean Architecture)

```text
limpeza-desktop/
├── main.py                                     # Ponto de entrada único (Terminal Windows & macOS)
├── README.md                                   # Guia de uso multiplataforma
├── install-macos.sh                            # Bootstrap oneliner para macOS
├── install-windows.ps1                         # Bootstrap oneliner para Windows
├── limpeza.spec                                # Especificação PyInstaller standalone
├── docs/                                       # Documentação SDD (System Design, RF/RNF, ADRs, Audits, Roadmap)
│   ├── 00-INDEX.md
│   ├── requirements/
│   │   └── RF-RNF.md
│   ├── architecture/
│   │   ├── 01-SYSTEM-DESIGN-C4.md
│   │   ├── 02-ADR.md
│   │   ├── 03-WINUTIL-REVERSE-ENGINEERING-AUDIT.md
│   │   └── 04-MACOS-CLEANERS-REVERSE-ENGINEERING-AUDIT.md
│   └── roadmap/
│       └── 01-EXECUTION-PLAN-MACOS-DEEP-CLEAN-AND-WEB-HOOKS.md
├── src/                                        # Código-fonte estruturado em Clean Architecture
│   ├── domain/                                 # Entidades puras, Value Objects e Portas (Interfaces)
│   │   ├── entities.py
│   │   ├── value_objects.py
│   │   └── ports.py
│   ├── application/                            # Casos de Uso e Orquestração (Idempotente)
│   │   ├── dtos.py
│   │   └── orchestrator.py
│   ├── infrastructure/                         # Adaptadores concretos de Sistema Operacional e Persistência Local
│   │   ├── resources.py
│   │   ├── tweaks_adapter.py
│   │   ├── catalogs/                           # JSONs declarativos 100% offline (WinUtil sanitizado + macOS Deep Clean)
│   │   │   ├── windows_tweaks.json
│   │   │   ├── macos_tweaks.json
│   │   │   └── safe_cleanup_rules.json
│   │   ├── windows/                            # Adaptadores específicos Windows (winreg, services, tasks, powercfg, WMI)
│   │   │   └── platform_adapter.py
│   │   ├── macos/                              # Adaptadores específicos macOS (ioreg, plistlib, defaults, diskutil, tmutil)
│   │   │   └── platform_adapter.py
│   │   ├── filesystem/                         # Scanner BFS adaptativo (os.scandir) e Executor de Limpeza/Lixeira
│   │   │   ├── autonomous_cleaner.py
│   │   │   └── disk_scanner.py
│   │   └── persistence/                        # Repositório local de Snapshots/Undo
│   │       └── snapshot_repository.py
│   └── presentation/                           # Interfaces de Usuário e Servidor de Web Hooks Locais
│       ├── window/
│       │   └── local_server.py
│       └── reporters/
│           └── html_reporter.py
├── tests/                                      # Testes Automatizados (Unitários, Segurança, Hardware e Zero-Network)
└── outputs/                                    # Relatórios HTML gerados e Snapshots de Reversão (Undo)
```
