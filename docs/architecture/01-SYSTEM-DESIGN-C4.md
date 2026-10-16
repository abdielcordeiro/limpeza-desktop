# System Design & Modelagem C4 (`limpeza-desktop`)

Este documento descreve a arquitetura de software do **Limpeza & Otimização Desktop Multiplataforma (Windows & macOS)** sob os padrões **Monólito Modular**, **Clean Architecture** e **Arquitetura Hexagonal (Ports & Adapters)**.

---

## 1. Visão Geral e Fluxo de Ponta a Ponta

```mermaid
sequenceDiagram
    autonumber
    actor User as Usuário (Terminal Windows / macOS)
    participant CLI as Entrypoint CLI (main.py)
    participant LauncherUI as Janela de Seleção & Navegação (Launcher UI)
    participant Orchestrator as Application Orchestrator (Use Cases)
    participant OSAdapter as Adapters de SO (Windows / macOS)
    participant Snapshot as Snapshot & Restore Manager (Local)
    participant Reporter as Gerador Dashboard HTML Offline

    User->>CLI: Executa comando no terminal (python main.py)
    CLI->>OSAdapter: Detecta SO (Windows/macOS), Privilégios (Admin/Root) e Partições
    CLI->>LauncherUI: Abre Janela Gráfica para o usuário escolher opções
    User->>LauncherUI: Seleciona SO, Limpeza Autônoma, Análise de Arquivos/Apps e Tweaks
    LauncherUI->>Orchestrator: Envia ExecutionPlanDTO validado
    alt Se Otimizações (Tweaks) ou Limpeza Autônoma selecionadas
        Orchestrator->>Snapshot: Cria Ponto de Restauração + Snapshot JSON de Estado Original
    end
    Orchestrator->>OSAdapter: 1. Executa Limpeza Autônoma (Temp, Caches, Shaders, Dumps)
    Orchestrator->>OSAdapter: 2. Executa 5 Camadas de Apps Ativos + Varredura de Órfãos, Grandes Arquivos e Apps
    Orchestrator->>OSAdapter: 3. Aplica Tweaks Selecionados (WinUtil Sanitizado / Otimizador macOS)
    Orchestrator->>Reporter: Consolida ExecutionResult (Espaço Liberado + Diagnóstico + Tweaks)
    Reporter-->>CLI: Salva outputs/relatorio_limpeza_disco.html
    CLI-->>User: Exibe link clicável no terminal e abre o Dashboard HTML no navegador
```

---

## 2. Diagramas C4

### 2.1. Nível 1 — Diagrama de Contexto do Sistema

> [!NOTE]
> Por determinação estrita de privacidade (**RNF-01: Zero-Network Policy**), o sistema opera 100% dentro da máquina local do usuário, sem qualquer conexão com servidores na nuvem ou envio de telemetria.

```mermaid
flowchart TD
    User["👤 Usuário (Windows 10/11 ou macOS)"]
    System["🛡️ Limpeza & Otimização Desktop<br/>(CLI + Janela de Seleção + Motor Autônomo + Relatório HTML)"]
    OS_FS["💽 Sistema de Arquivos Local<br/>(NTFS / APFS, Partições, Caches, AppData, ~/Library)"]
    OS_Kernel["⚙️ Subsistema Nativo do SO<br/>(Windows Registry, Services, Task Scheduler, PowerCfg / macOS defaults, launchctl, diskutil)"]
    Browser["🌐 Navegador Local do Usuário<br/>(Visualização do Dashboard HTML Offline)"]

    User -->|"1. Inicia via Terminal e escolhe opções na Janela"| System
    System -->|"2. Varre, analisa e limpa temporários/órfãos"| OS_FS
    System -->|"3. Cria Backup/Restore Point e aplica Tweaks locais"| OS_Kernel
    System -->|"4. Gera relatório HTML 100% offline e entrega link"| Browser
    Browser -->|"5. Exibe ganhos, arquivos gigantes e apps para limpeza assistida"| User
```

---

### 2.2. Nível 2 — Diagrama de Containers (Monólito Modular)

```mermaid
flowchart TB
    subgraph Host["Máquina Local do Usuário (Windows ou macOS)"]
        CLI["💻 Terminal Entrypoint<br/>(main.py)"]
        GUI_Wizard["🪟 Janela de Navegação & Seleção<br/>(Presentation Layer: GUI Nativa / Local Web UI)"]
        
        subgraph CoreApp["Núcleo da Aplicação (Clean Architecture / Hexagonal)"]
            ModProbe["📦 Módulo: System Probe<br/>(Detecção de SO, Partições e Saúde)"]
            ModCleaner["📦 Módulo: Autonomous Cleaner<br/>(Limpeza Segura de Temp, Caches, Shaders, Dumps)"]
            ModScanner["📦 Módulo: Deep Scanner & Orphans<br/>(5 Camadas Active Apps, Órfãos, Top Arquivos e Apps Grandes)"]
            ModOptimizer["📦 Módulo: System Optimizer<br/>(Motor Declarativo WinUtil Sanitizado & macOS Tweaks)"]
            ModCloud["📦 Módulo: Cloud & Packages<br/>(Diagnóstico OneDrive / iCloud & Apps)"]
        end

        Catalogs["📄 Catálogos Declarativos Offline<br/>(catalogs/windows_tweaks.json, catalogs/macos_tweaks.json)"]
        Snapshots["⏪ Cofre de Snapshots & Undo<br/>(outputs/snapshots/*.json)"]
        HTMLReport["📊 Dashboard HTML Interativo<br/>(outputs/relatorio_limpeza_disco.html)"]
    end

    CLI --> GUI_Wizard
    GUI_Wizard --> CoreApp
    ModOptimizer --> Catalogs
    ModOptimizer --> Snapshots
    ModCleaner --> Snapshots
    CoreApp --> HTMLReport
```

---

### 2.3. Nível 3 — Diagrama de Componentes (Ports & Adapters)

```mermaid
flowchart LR
    subgraph Presentation["Camada de Entrada & Apresentação (Primary Adapters)"]
        EntryCLI["CLI Runner"]
        ConfigWindow["Selection Window (Wizard UI)"]
        HTMLGen["HTML Dashboard Generator"]
    end

    subgraph Application["Camada de Aplicação (Use Cases)"]
        UC_Plan["BuildExecutionPlanUseCase"]
        UC_Clean["RunAutonomousCleanupUseCase"]
        UC_Scan["AnalyzeDiskAndOrphansUseCase"]
        UC_Opt["ApplySystemTweaksUseCase"]
        UC_Undo["RevertSystemTweaksUseCase"]
    end

    subgraph Domain["Camada de Domínio (Pura - Sem Dependências Externas)"]
        Entities["Entities: Partition, CleanableItem,InstalledApp, SystemTweak, ExecutionReport"]
        ValueObjects["Value Objects: RiskLevel, OSPlatform, ByteSize, TweakAction"]
        DomainEvents["Domain Events: SpaceFreedEvent, TweakAppliedEvent, SnapshotCreatedEvent"]
        Ports["Interfaces de Porta (Ports):<br/>IOSProbePort, IActiveAppsPort, IFileSystemCleanerPort, ISystemTweakPort, ISnapshotRepositoryPort"]
    end

    subgraph Infrastructure["Camada de Infraestrutura (Secondary Adapters)"]
        WinAdapter["🪟 Windows Adapter<br/>(winreg, sc.exe, schtasks, powercfg, dism, cleanmgr)"]
        MacAdapter["🍎 macOS Adapter<br/>(plistlib, defaults, launchctl, diskutil, tmutil, dscacheutil)"]
        LocalFSAdapter["📂 FileSystem & Snapshot JSON Adapter"]
    end

    EntryCLI --> ConfigWindow
    ConfigWindow --> UC_Plan
    UC_Plan --> UC_Clean
    UC_Plan --> UC_Scan
    UC_Plan --> UC_Opt
    UC_Plan --> UC_Undo

    UC_Clean --> Ports
    UC_Scan --> Ports
    UC_Opt --> Ports
    UC_Undo --> Ports

    Ports -.->|"Implementado por"| WinAdapter
    Ports -.->|"Implementado por"| MacAdapter
    Ports -.->|"Implementado por"| LocalFSAdapter
```

---

## 3. Organização de Diretórios Proposta (Clean Architecture)

```text
limpeza-desktop/
├── main.py                                     # Ponto de entrada único (Terminal Windows & macOS)
├── README.md                                   # Guia de uso multiplataforma
├── docs/                                       # Documentação de Engenharia (System Design, RF/RNF, ADRs, WinUtil Audit)
│   ├── 00-INDEX.md
│   ├── requirements/
│   │   └── RF-RNF.md
│   └── architecture/
│       ├── 01-SYSTEM-DESIGN-C4.md
│       ├── 02-ADR.md
│       └── 03-WINUTIL-REVERSE-ENGINEERING-AUDIT.md
├── src/                                        # Código-fonte estruturado em Clean Architecture
│   ├── domain/                                 # Entidades puras, Value Objects, Eventos e Portas (Interfaces)
│   │   ├── entities/
│   │   ├── value_objects/
│   │   ├── events/
│   │   └── ports/
│   ├── application/                            # Casos de Uso e Orquestração (Idempotente)
│   │   ├── dtos/
│   │   ├── use_cases/
│   │   └── services/
│   ├── infrastructure/                         # Adaptadores concretos de Sistema Operacional e Persistência Local
│   │   ├── catalogs/                           # JSONs declarativos 100% offline (WinUtil sanitizado + macOS)
│   │   │   ├── windows_tweaks.json
│   │   │   ├── macos_tweaks.json
│   │   │   └── safe_cleanup_rules.json
│   │   ├── windows/                            # Adaptadores específicos Windows (winreg, services, tasks, powercfg)
│   │   ├── macos/                              # Adaptadores específicos macOS (plist, defaults, launchctl, caches)
│   │   ├── filesystem/                         # Scanner de alta performance (os.scandir) e Executor de Limpeza
│   │   └── persistence/                        # Repositório local de Snapshots/Undo e Logs de Auditoria
│   └── presentation/                           # Interfaces de Usuário
│       ├── window/                             # Janela Gráfica Inicial de Seleção (SO, Módulos, Tweaks)
│       ├── cli/                                # Formatador de progresso no terminal
│       └── reporters/                          # Gerador do Dashboard HTML Interativo Offline
├── tests/                                      # Testes Automatizados (Unitários, Arquitetura e Idempotência)
└── outputs/                                    # Relatórios HTML gerados e Snapshots de Reversão (Undo)
```
