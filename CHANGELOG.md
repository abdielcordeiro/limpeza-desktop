# Changelog

Todas as alterações notáveis neste projeto serão documentadas neste arquivo.

O formato segue as diretrizes do [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adota o [Semantic Versioning](https://semver.org/lang/pt-BR/).

---

## [1.3.1] - 2026-11-23

### Corrigido / Adicionado
- **Reconciliação Exata de Capacidade e Ocupação de Disco no macOS APFS (RF-20 / ADR-012):**
  - Reconciliação exata de capacidade e ocupação do container APFS no macOS (`_probe_macos_volume_metrics`) combinando `statvfs` (`shutil.disk_usage`), `diskutil info -plist`, `system_profiler SPStorageDataType` e Foundation `NSURLVolumeAvailableCapacityForImportantUsageKey`.
  - Formatação nativa em **Base-10 SI Decimal ($1000^3\text{ bytes} = 1\text{ GB}$)** para volumes macOS (`245.11 GB` total / `217.10 GB` usado), eliminando a defasagem visual de `7,37%` (~15 GB) causada pela formatação binária (`GiB`, $1024^3$) quando comparada aos Ajustes do Sistema do macOS.
  - Exibição dual transparente na Janela Inicial (`/`), Aba 1 e Aba 8 do Dashboard HTML: métricas principais no padrão Ajustes do macOS (`SI 1000³`), acompanhadas de `⚡ Alocado Bruto APFS`, `♻️ Espaço Purgável APFS`, `💽 Livre Físico Imediato` e `📐 Equivalente Binário (IEC 1024³ GiB)`.
  - Sincronização 1:1 entre `MacOSSystemProbeAdapter.get_partitions()` (`PartitionInfo`) e `MacOSHardwareProbeAdapter.get_disks_health()` (`StorageDiskHealth`).

---

## [1.3.0] - 2026-11-23

### Adicionado
- **Raio-X Real das Categorias Ocultas de Armazenamento (RF-18 / ADR-011):**
  - Desvendamento completo de **"Documentos"** (revelando o "espaço fantasma" ocultado pelo macOS) e **"Dados do Sistema" (`System Data`)** através de `StorageXRayReport` e `StorageCategoryBreakdown`.
  - Descoberta dinâmica de 100% das pastas visíveis de projetos (`~/Documents`, `~/IdeaProjects`, `~/Desktop`, `~/Downloads`, etc.) e pastas ocultas na raiz da Home `~` (`~/.gemini`, `~/.cursor`, `~/.vscode`, `~/.gradle`, `~/.npm`, `~/.cargo`, `~/.m2`, `~/.ollama`, `~/.docker`, etc.) no escopo padrão `SMART_FAST`.
  - Mapeamento e classificação de **Artefatos Reconstruíveis de Projetos** (`node_modules`, `.venv`, `venv`, `target`, `build`, `.dart_tool`, `.next`, `Pods`) com inclusão direta na lista de limpeza assistida.
- **Explorador Cirúrgico de Diretórios Sob Demanda com Drill-Down Infinito (RF-19 / ADR-011):**
  - Novo endpoint REST local `POST /api/inspect-directory` em `127.0.0.1` com proteção inviolável contra path traversal (`..`), null bytes e flags.
  - Painel/modal com navegação recursiva por breadcrumb, ordenação decrescente por tamanho físico real (`st_blocks * 512`), classificação de segurança e ações diretas (`📂 Abrir`, `🗑️ Lixeira`, `🔥 Excluir`).
  - Botão `🔍 Explorar` integrado aos cards do Raio-X e à tabela de Top Maiores Ocupantes.
- **Efetividade Máxima na Limpeza Autônoma:**
  - Ativação por padrão (`default_enabled: true`) das regras de desenvolvimento (`mac_jetbrains_caches`, `mac_node_js_caches`, `mac_python_dev_caches`, `mac_jvm_native_mobile_caches`, `win_dev_caches`).
  - Limpeza profunda de `@DARWIN_USER_CACHE_DIR@/*` e remoção completa de subpastas expandidas por wildcard (`remove_root=True`).
  - Suporte multi-perfil Chromium (`/*/Cache`, `/*/Code Cache`) e IDEs modernas (Windsurf, Antigravity, Postman).
- **Suíte de Testes Automatizados:**
  - Criação de `tests/test_storage_xray_and_inspector.py` elevando a suíte para **77 testes automatizados** passando 100% verdes com verificação estrita Zero-Network.

---

## [1.2.0] - 2026-11-20

### Adicionado
- **Suporte Avançado a macOS Apple Silicon (ARM64 & x86_64):**
  - Detecção nativa da arquitetura Apple Silicon (M1/M2/M3/M4) e macOS Sonoma / Sequoia.
  - Varredura adaptativa inspirada nos ecossistemas auditados (`tw93/Mole`, `Pearcleaner`, `mac-cleanup-py`, `Stats`, `OnyX`) sob estrita política Zero-Network.
- **Catálogo com 16+ Regras de Limpeza Cirúrgica (`safe_cleanup_rules.json`):**
  - Limpeza profunda e segura de Darwin User Temp (`/var/folders/*`), Caches de Usuário com Whitelist (`~/Library/Caches`), Containers Sandboxed (`~/Library/Containers`), Caches de Subsistema Darwin (Metal Shaders, QuickLook), DiagnosticReports (`CrashReporter`), Ecossistemas de Desenvolvimento (Apple Xcode `DerivedData`, iOS/watchOS/tvOS `DeviceSupport`, CoreSimulator, Homebrew, Docker Desktop, OrbStack, Colima) e caches transitórios de navegadores/Electron.
- **7 Novos Endpoints REST Locais na Aplicação Web (`127.0.0.1`):**
  - `GET /api/live-health`: Telemetria em tempo real de hardware, memória, bateria e Longevity Health Score.
  - `POST /api/file-action`: Ações pontuais de arquivo (mover para Lixeira com proteção ou exclusão irreversível com guardrails).
  - `POST /api/reveal-path`: Revelação nativa do item no Finder (`open -R`) ou Windows Explorer (`explorer.exe /select,`).
  - `POST /api/execute-rule`: Execução pontual sob demanda de regras individuais do catálogo (modos Real e Dry-Run).
  - `POST /api/startup-action`: Auditoria e remoção de inicializadores órfãos (`LaunchAgents` e `LaunchDaemons` no macOS; chaves `Run` no Registro do Windows).
  - `POST /api/process-action`: Encerramento monitorado de processos com alto consumo de recursos (com proteção inviolável a processos de sistema).
  - `POST /api/upgrade-packages`: Atualização segura de pacotes de desenvolvimento desatualizados (Homebrew formulae/casks e WinGet).
- **Longevity Health Score (0–100) & Motor Consultivo de Vida Útil:**
  - Cálculo ponderado de integridade e desgaste do dispositivo com penalidades baseadas em telemetria real:
    - Saúde e contagem de ciclos da bateria Apple Silicon / Windows BatteryReport.
    - Desgaste percentual de SSD/NVMe (S.M.A.R.T. Wear Level).
    - Pressão de memória RAM e uso excessivo de Swap em disco (prevenção de degradação da memória flash).
    - Sobrecarga de itens de inicialização em segundo plano e processos com alta carga contínua.
  - Recomendações acionáveis e consultivas personalizadas no Dashboard HTML.
- **Auditoria de `LaunchAgents` e `LaunchDaemons` Órfãos:**
  - Inspeção automática em `~/Library/LaunchAgents`, `/Library/LaunchAgents` e `/Library/LaunchDaemons`.
  - Cruzamento de cada `.plist` com os binários de destino em disco para identificação de persistências fantasmas deixadas por apps já desinstalados.
- **Telemetria Nativa IOKit da Bateria (macOS):**
  - Extração direta via `ioreg -rn AppleSmartBattery -a` (formato plist) sem ferramentas externas.
  - Coleta de capacidade projetada vs real (`AppleRawMaxCapacity` / `DesignCapacity`), contagem de ciclos (`CycleCount`), temperatura, amperagem instantânea, voltagem e estado de saúde (`Condition`).
- **Prevenção de Write Amplification em APFS & Guardrails de Armazenamento:**
  - Proteção total contra desfragmentação em SSDs e drives NVMe formatados em APFS/NTFS.
  - Execução diferenciada: TRIM e manutenção nativa via `diskutil apfs` / `defrag.exe /O /L` para prolongar a vida útil das células NAND.
- **Guardrails de Segurança Reforçados (Anti-Path Traversal & Root Protection):**
  - Rejeição sumária de payloads de travessia de diretório (`../`, `..\`, null bytes `\x00`).
  - Lista de proteção estrita contendo mais de 50 caminhos e raízes críticas do sistema operacional (`/`, `/System`, `/Library`, `/Applications`, `/usr`, `/private`, `C:\`, `C:\Windows`, etc.).
  - Proteção de integridade para PIDs críticos do sistema operacional (`PID <= 100`, `kernel_task`, `launchd`, `csrss.exe`, etc.).

### Modificado
- **Dashboard HTML Responsivo (8 Abas):**
  - Nova aba interativa de Saúde de Hardware, Bateria e Longevity Score.
  - Botões reativos para execução de regras individuais, remoção de itens, revelação no Finder/Explorer e atualização de telemetria em tempo real via polling/fetch local seguro.
- **Orquestrador de Serviços (`OrchestratorService`):**
  - Integração dos novos adaptadores de diagnóstico de hardware, auditoria de persistência e gerenciamento seguro de processos.
- **Suíte de Testes Automatizados:**
  - Adição de `tests/test_security_guardrails_audit.py` com testes exaustivos de path traversal, guardrails de deleção, proteção de PID e isolamento de privilégios.
  - Atualização dos testes de relatório, rotas de API local e diagnóstico de storage/hardware (69 testes unitários passando 100% verdes).

### Corrigido
- **Eliminação de Sintaxe Duplicada no JavaScript do Relatório HTML:**
  - Remoção de bloco duplicado/órfão no gerador `src/presentation/reporters/html_reporter.py` que causava `SyntaxError: Identifier 'REPORT_DATA' has already been declared`.
  - Implementação de isolamento defensivo com `try-catch` na inicialização de cada aba do Dashboard (`initDashboard`, `initHwTab`, etc.) prevenindo interrupção em cascata de abas subsequentes.
  - Adição de validação sintática automatizada via `node --check` no teste `tests/test_report_and_server.py`.

### Segurança & Conformidade
- **100% de Conformidade com o RNF-01 (Zero-Network / Zero-Telemetry):**
  - Nenhuma biblioteca externa adicionada; código 100% em Python Standard Library.
  - Nenhuma conexão externa realizada; o servidor HTTP opera exclusivamente na interface de loopback `127.0.0.1`.

---

## [1.1.0] - 2026-11-20

### Adicionado
- **Diagnóstico de Saúde de Hardware e Periféricos (RF-13):**
  - Telemetria de integridade de discos rígidos e SSDs/NVMe (S.M.A.R.T.).
  - Monitoramento de pressão de memória RAM e volume de Swap.
  - Diagnóstico de GPU e status geral de alimentação/bateria.
- **Otimização Inteligente de Armazenamento com Guardrails Anti-Degradação (RF-14):**
  - Detecção da mídia de armazenamento (SSD/NVMe vs HDD mecânico).
  - Guardrail impenetrável impedindo desfragmentação destrutiva em memórias flash.
  - Otimização adequada por tipo de mídia: TRIM em SSDs e defrag sequencial apenas em HDDs mecânicos após confirmação do usuário.
- **ADR-008:** Registro de Decisão Arquitetural sobre diagnóstico nativo sem dependências e otimização diferenciada de storage.

---

## [1.0.0] - 2026-11-20

### Adicionado
- **Janela de Configuração Pré-Execução e Servidor Local (RF-01):**
  - Servidor embutido em `127.0.0.1` com interface gráfica amigável no navegador padrão.
- **Motor de Limpeza Autônoma para Windows e macOS (RF-02):**
  - Limpeza segura de arquivos temporários, logs de usuário e relatórios de erro.
- **Algoritmo de 5 Camadas Anti-Falsos Positivos (RF-03):**
  - Caça a resíduos e pastas órfãs com proteção por processos em execução, chaves de Registro, diretórios de instalação, serviços e tarefas ativas.
- **Scanner de Grandes Arquivos e Aplicativos (RF-04):**
  - Mapeamento das 100 maiores pastas/arquivos e análise de espaço ocupado por softwares instalados.
- **Motor de Otimização Sanitizado do WinUtil com Snapshot e Undo (RF-05):**
  - Otimizações de desempenho e privacidade para Windows e macOS com reversão de estado segura via arquivo de snapshot JSON.
- **Dashboard HTML Autônomo e Responsivo (RF-06):**
  - Relatório final exportável em arquivo HTML único, interativo e sem dependência de internet.
- **Ganchos Interativos & Reanálise On-Demand (RF-07 a RF-11):**
  - Reanálise em tempo real (`/api/reanalyze`), remoção reativa de órfãos na tabela e drill-down em subpastas com mini gráficos visuais.
- **Esvaziamento Nativo da Lixeira Multiplataforma (RF-12):**
  - Integração via AppleScript no macOS e `SHEmptyRecycleBin` via `ctypes` no Windows, com remoção resiliente de arquivos marcados como somente leitura (`readonly`).
- **Empacotamento Standalone & CI/CD Multiplataforma:**
  - Especificação `limpeza.spec` para PyInstaller (binários standalone sem necessidade de Python pré-instalado).
  - Scripts de bootstrap oneliner `install-macos.sh` e `install-windows.ps1`.
  - Workflows do GitHub Actions para Quality Gates (`ci.yml`) e Publicação de Releases (`release.yml`).
