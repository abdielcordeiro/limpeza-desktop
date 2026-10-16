# Architecture Decision Records (ADRs)

Este documento registra as decisões arquiteturais críticas do projeto **Limpeza & Otimização Desktop Multiplataforma**.

---

## ADR-001: Arquitetura Hexagonal Multiplataforma (Windows `nt` e macOS `darwin`)
- **Status:** Aceito
- **Data:** 2026-10-15
- **Contexto:**
  O código inicial do repositório (`analisador_limpeza_disco/`) foi construído apenas para Windows (acoplado a letras de drive `C:\`, `winreg`, `tasklist` e `winget`) e apenas listava sugestões de limpeza sem executar a limpeza autônoma nem otimizações de sistema. O produto agora precisa rodar tanto no **Windows** quanto no **macOS** a partir do terminal, realizando limpeza autônoma e otimização profunda.
- **Decisão:**
  Adotar **Clean Architecture + Hexagonal (Ports & Adapters)** com injeção automática do adaptador do sistema operacional (`WindowsPlatformAdapter` quando `sys.platform == "win32"` e `MacOSPlatformAdapter` quando `sys.platform == "darwin"`), permitindo que o usuário também simule ou inspecione os catálogos de ambos os sistemas na janela inicial.
- **Consequências:**
  - Domínio 100% desacoplado de APIs específicas do SO.
  - Facilidade para testar todas as regras de negócio no macOS e no Windows usando mocks/fakes nas portas de infraestrutura.

---

## ADR-002: Transcrição Declarativa e Sanitização Zero-Network do `ChrisTitusTech/winutil`
- **Status:** Aceito
- **Data:** 2026-10-15
- **Contexto:**
  O repositório `ChrisTitusTech/winutil` possui um excelente catálogo de otimizações para Windows (Registro, Serviços, Scheduled Tasks, Planos de Energia e Limpeza), mas é escrito em PowerShell + WPF acoplado ao Windows e contém **8 pontos de comunicação externa** (incluindo download do executável fechado `OOSU10.exe`, modificação do arquivo `hosts` a partir de URLs externas no GitHub, scripts remotos do Chocolatey e links de rastreamento).
- **Decisão:**
  1. Transcrever toda a base de conhecimento de Tweaks e Limpezas do WinUtil para um catálogo JSON declarativo local (`src/infrastructure/catalogs/windows_tweaks.json`) consumido diretamente pelo nosso motor Python nativo (`winreg`, `sc.exe`, `schtasks.exe`, `powercfg.exe`, `dism.exe`).
  2. **Banir 100% das chamadas de rede e downloads externos** identificados na auditoria do WinUtil.
  3. Substituir a necessidade do `O&O ShutUp10++` (`OOSU10.exe`) pela aplicação direta e transparente das chaves de Registro de privacidade documentadas no próprio catálogo local.
- **Consequências:**
  - Execução 100% privada, auditável, offline e sem dependência de servidores de terceiros.

---

## ADR-003: Idempotência, Ponto de Restauração e Snapshot Local Reversível (`Undo`)
- **Status:** Aceito
- **Data:** 2026-10-15
- **Contexto:**
  Otimizações de sistema operacional (alteração de serviços para `Manual`/`Disabled`, chaves `HKLM`/`HKCU` e `defaults` do macOS) exigem segurança absoluta contra falhas e capacidade de reversão caso o usuário deseje voltar ao estado anterior.
- **Decisão:**
  1. Antes de aplicar qualquer bateria de Tweaks, o sistema salva um **Snapshot de Estado Local** (`outputs/snapshots/snapshot_<timestamp>.json`) contendo o valor exato que estava configurado na máquina do usuário antes da alteração (além do `OriginalValue` padrão de fábrica mapeado do WinUtil).
  2. No Windows, quando executado como Administrador, dispara a criação de um Ponto de Restauração do Sistema (`Checkpoint-Computer`).
  3. Todas as operações de escrita são **idempotentes**: aplicar o mesmo tweak múltiplas vezes verifica se o estado desejado já está ativo antes de recriar recursos (ex: evitando duplicação infinita do plano de energia *Ultimate Performance*).

---

## ADR-004: Janela de Navegação Pré-Execução + Dashboard HTML Final 100% Offline
- **Status:** Aceito
- **Data:** 2026-10-15
- **Contexto:**
  O usuário precisa rodar um comando no terminal que primeiro abra uma janela para escolher o sistema operacional e o que deseja executar (limpeza autônoma, análise de arquivos/apps gigantes, otimizações/tweaks do sistema), e ao final gere um link de uma página HTML estruturada com todos os resultados.
- **Decisão:**
  - Fornecer uma interface gráfica inicial de seleção intuitiva (compatível com Windows e macOS sem dependências externas complexas) onde o usuário configura sua execução.
  - Gerar o relatório final em `outputs/relatorio_limpeza_disco.html` totalmente autocontido (CSS e JS inline, sem requisição externa para `fonts.googleapis.com`, garantindo zero vazamento de IP ao abrir o relatório).
