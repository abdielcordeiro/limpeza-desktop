# Índice de Documentação de Engenharia (`limpeza-desktop`)

Bem-vindo à documentação oficial de arquitetura, requisitos e engenharia reversa do **Limpeza & Otimização Desktop Multiplataforma (Windows & macOS)**.

> [!IMPORTANT]
> **Premissa Documentation-First & Privacy-First:** Toda evolução deste produto deve ser precedida pela atualização dos documentos abaixo. Nenhuma funcionalidade que realize envio de telemetria, chamadas de rede não autorizadas ou execução de binários remotos de terceiros é permitida.

---

## 📚 Estrutura da Documentação

### 1. Requisitos do Produto (`docs/requirements/`)
- [**RF-RNF.md — Requisitos Funcionais e Não-Funcionais**](file:///Users/abdielcordeiro/IdeaProjects/limpeza-desktop/docs/requirements/RF-RNF.md)
  - Especificação detalhada dos Requisitos Funcionais (Janela de Seleção Pré-Execução, Motor de Limpeza Autônoma Windows/macOS, Algoritmo Anti-Falsos Positivos de 5 Camadas, Scanner de Grandes Arquivos e Aplicativos, Motor de Otimização inspirado no WinUtil com Undo/Backup, Dashboard HTML Final).
  - Especificação dos Requisitos Não-Funcionais (Política Zero-Network / Zero-Telemetry, Idempotência e Reversibilidade, Isolamento de Privilégios, Performance de I/O e Memória).

### 2. Arquitetura e System Design (`docs/architecture/`)
- [**01-SYSTEM-DESIGN-C4.md — Arquitetura Hexagonal, Clean Arch e Modelo C4**](file:///Users/abdielcordeiro/IdeaProjects/limpeza-desktop/docs/architecture/01-SYSTEM-DESIGN-C4.md)
  - Diagramas C4 (Contexto, Containers e Componentes) em Mermaid.js.
  - Divisão em Contextos Delimitados (Bounded Contexts) sob arquitetura Ports & Adapters (Domain, Application, Infrastructure/OS Adapters, UI/Presentation).
  - Fluxo de execução desde o comando no terminal, abertura da janela de configuração, execução autônoma e geração do relatório HTML final.
- [**02-ADR.md — Architecture Decision Records (Decisões Arquiteturais)**](file:///Users/abdielcordeiro/IdeaProjects/limpeza-desktop/docs/architecture/02-ADR.md)
  - **ADR-001:** Arquitetura Hexagonal Multiplataforma (Strategy Pattern para Windows `nt` e macOS `darwin`).
  - **ADR-002:** Transcrição Declarativa e Sanitização Zero-Network do `ChrisTitusTech/winutil`.
  - **ADR-003:** Mecanismo de Idempotência, Ponto de Restauração e Snapshot Local Reversível (`Undo`).
  - **ADR-004:** Janela de Navegação Pré-Execução e Relatório HTML Autônomo (Zero Dependências Externas).
- [**03-WINUTIL-REVERSE-ENGINEERING-AUDIT.md — Dossiê de Engenharia Reversa e Auditoria de Privacidade do WinUtil**](file:///Users/abdielcordeiro/IdeaProjects/limpeza-desktop/docs/architecture/03-WINUTIL-REVERSE-ENGINEERING-AUDIT.md)
  - Mapeamento completo de todas as chaves de Registro (`HKLM`/`HKCU`), Serviços, Tarefas Agendadas e Comandos de Limpeza/Performance do `ChrisTitusTech/winutil`.
  - **Laudo de Auditoria de Segurança e Privacidade:** Identificação dos **8 pontos de comunicação externa / risco de vazamento** presentes no WinUtil original e a estratégia de bloqueio/remoção aplicada em nosso produto.
