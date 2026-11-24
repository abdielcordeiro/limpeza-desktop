# Índice de Documentação de Engenharia (`limpeza-desktop`)

Bem-vindo à documentação oficial de arquitetura, requisitos, engenharia reversa e plano de execução do **Limpeza & Otimização Desktop Multiplataforma (Windows & macOS Apple Silicon / Intel)**.

> [!IMPORTANT]
> **Premissa Documentation-First & Privacy-First:** Toda evolução deste produto deve ser precedida pela atualização dos documentos abaixo. Nenhuma funcionalidade que realize envio de telemetria, chamadas de rede não autorizadas ou execução de binários remotos de terceiros é permitida.

---

## 📚 Estrutura da Documentação

### 1. Requisitos do Produto (`docs/requirements/`)
- [**RF-RNF.md — Requisitos Funcionais e Não-Funcionais**](file:///Users/abdielcordeiro/IdeaProjects/limpeza-desktop/docs/requirements/RF-RNF.md)
  - Especificação detalhada dos Requisitos Funcionais (**RF-01 a RF-19**):
    - **RF-01 a RF-06:** Janela de Seleção Pré-Execução, Motor de Limpeza Autônoma Windows/macOS, Algoritmo Anti-Falsos Positivos de 5 Camadas, Scanner de Grandes Arquivos e Aplicativos, Motor de Otimização inspirado no WinUtil com Undo/Backup e Dashboard HTML Final.
    - **RF-07 a RF-12:** Reanálise On-Demand, Remoção Reativa na UI, Drill-Down de Subpastas, Navegação Bidirecional, Distribuição Standalone (PyInstaller + Bootstrap Oneliner) e Esvaziamento Nativo da Lixeira.
    - **RF-13 a RF-14:** Diagnóstico de Saúde de Hardware/Periféricos e Otimização Inteligente de Armazenamento com Guardrails Anti-Degradação de NVMe.
    - **RF-15:** Varredura Profunda e Limpeza Cirúrgica para macOS Apple Silicon (Containers Sandboxed, Dev Ecosystems, Darwin User Caches, APFS System Data & Bundle-ID Correlation).
    - **RF-16:** Ganchos Interativos na Aplicação Web para Ações Diretas de Arquivo (`/api/file-action` Lixeira/Exclusão, `/api/reveal-path` Finder/Explorer, `/api/execute-rule` e `/api/upgrade-packages`).
    - **RF-17:** Telemetria Profunda de Saúde (IOKit `ioreg`), Inspetor de Persistência/Processos (`LaunchAgents` Órfãos & Processos Zumbis) e Motor Consultivo de Vida Útil (`Longevity Health Score 0–100`).
    - **RF-18:** Raio-X Real das Categorias Ocultas de Armazenamento (Desvendando "Documentos" & "Dados do Sistema", Pastas Ocultas `~/.*`, Artefatos Reconstruíveis de Projetos `node_modules`/`.venv`/`target`/`build` e Ativação Padrão de Caches Dev).
    - **RF-19:** Explorador Interativo de Árvore de Diretórios Sob Demanda (`POST /api/inspect-directory`) com Drill-Down Infinito.
    - **RF-20:** Reconciliação Exata de Capacidade e Ocupação de Disco no macOS APFS (Padrão SI Decimal $1000^3$ vs Binário IEC $1024^3$ & Espaço Purgável).
  - Especificação dos Requisitos Não-Funcionais (**RNF-01 a RNF-04**: Política Zero-Network / Zero-Telemetry, Idempotência e Reversibilidade, Isolamento de Privilégios, Performance de I/O e Memória).

### 2. Arquitetura, ADRs e Dossiês de Engenharia Reversa (`docs/architecture/`)
- [**01-SYSTEM-DESIGN-C4.md — Arquitetura Hexagonal, Clean Arch e Modelo C4**](file:///Users/abdielcordeiro/IdeaProjects/limpeza-desktop/docs/architecture/01-SYSTEM-DESIGN-C4.md)
  - Diagramas C4 (Contexto, Containers, Componentes e Implantação) e Diagrama de Sequência com Web Hooks Locais (`127.0.0.1`) em Mermaid.js.
  - Divisão em Contextos Delimitados (Bounded Contexts) sob arquitetura Ports & Adapters (`Domain`, `Application`, `Infrastructure`, `Presentation`).
- [**02-ADR.md — Architecture Decision Records (Decisões Arquiteturais)**](file:///Users/abdielcordeiro/IdeaProjects/limpeza-desktop/docs/architecture/02-ADR.md)
  - **ADR-001:** Arquitetura Hexagonal Multiplataforma (Strategy Pattern para Windows `nt` e macOS `darwin`).
  - **ADR-002:** Transcrição Declarativa e Sanitização Zero-Network do `ChrisTitusTech/winutil`.
  - **ADR-003:** Mecanismo de Idempotência, Ponto de Restauração e Snapshot Local Reversível (`Undo`).
  - **ADR-004:** Janela de Navegação Pré-Execução e Relatório HTML Autônomo (Zero Dependências Externas).
  - **ADR-005:** Reanálise On-Demand, Reatividade no DOM e Drill-Down Dinâmico de Subpastas.
  - **ADR-006:** Empacotamento Autocontido (PyInstaller) e Distribuição Standalone via GitHub Releases.
  - **ADR-007:** Esvaziamento Nativo da Lixeira Multiplataforma com Deleção Resiliente de Readonly.
  - **ADR-008:** Diagnóstico Nativo Zero-Dependency de Hardware e Otimização Diferenciada de Disco (HDD Defrag vs SSD TRIM / APFS Maintenance).
  - **ADR-009:** Engenharia Reversa Zero-Network do Ecossistema macOS (`Mole`, `Pearcleaner`, `mac-cleanup-py`, `Stats`, `OnyX`) e Motor de Varredura Adaptativa com Correlação por Bundle-ID.
  - **ADR-010:** Arquitetura de Ganchos Interativos Web (`127.0.0.1`), Quarentena Padrão via Lixeira e Motor Consultivo de Vida Útil (`Longevity Health Score`).
  - **ADR-011:** Raio-X das Categorias Ocultas de Armazenamento ("Documentos" & "Dados do Sistema"), Varredura Completa da Home (`~`), Artefatos Reconstruíveis de Projetos e Navegação em Árvore Sob Demanda (`/api/inspect-directory`).
  - **ADR-012:** Reconciliação de Armazenamento APFS no macOS (Unidades SI Base-10 $1000^3$ vs IEC Base-2 $1024^3$ e Desconto de `PurgeableSpace`).
- [**03-WINUTIL-REVERSE-ENGINEERING-AUDIT.md — Dossiê de Engenharia Reversa e Auditoria de Privacidade do WinUtil (Windows)**](file:///Users/abdielcordeiro/IdeaProjects/limpeza-desktop/docs/architecture/03-WINUTIL-REVERSE-ENGINEERING-AUDIT.md)
  - Mapeamento completo de chaves de Registro (`HKLM`/`HKCU`), Serviços, Tarefas Agendadas e Comandos do `ChrisTitusTech/winutil` e bloqueio de 7 vetores de rede externa.
- [**04-MACOS-CLEANERS-REVERSE-ENGINEERING-AUDIT.md — Dossiê de Engenharia Reversa e Auditoria Zero-Network: Ecossistema macOS (Apple Silicon) & Longevidade**](file:///Users/abdielcordeiro/IdeaProjects/limpeza-desktop/docs/architecture/04-MACOS-CLEANERS-REVERSE-ENGINEERING-AUDIT.md)
  - Engenharia reversa e auditoria Zero-Network de `tw93/Mole`, `mac-cleanup/mac-cleanup-py`, `alienator88/Pearcleaner`, `exelban/stats` e `Titanium Software OnyX`.
  - Mapeamento de caches de usuário com whitelist, containers sandboxed, diretórios Darwin por usuário, ecossistemas de desenvolvimento, correlação por `CFBundleIdentifier`, auditoria de `LaunchAgents` órfãos e telemetria IOKit (`ioreg -rn AppleSmartBattery -a`).

### 3. Roadmap & Plano de Execução SDD (`docs/roadmap/`)
- [**01-EXECUTION-PLAN-MACOS-DEEP-CLEAN-AND-WEB-HOOKS.md — Plano de Execução Técnico & Roadmap SDD**](file:///Users/abdielcordeiro/IdeaProjects/limpeza-desktop/docs/roadmap/01-EXECUTION-PLAN-MACOS-DEEP-CLEAN-AND-WEB-HOOKS.md)
  - Diagnóstico executivo dos 8 gargalos do macOS e da aplicação Web, contratos de domínio, especificação dos 7 novos endpoints REST locais (`127.0.0.1`), roteiro de implementação em 5 fases e matriz de rastreabilidade.
