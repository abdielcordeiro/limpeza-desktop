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

---

## ADR-005: Reanálise On-Demand, Reatividade no DOM e Drill-Down Dinâmico de Subpastas
- **Status:** Aceito
- **Data:** 2026-10-16
- **Contexto:**
  Durante os testes de usuário no macOS, foram identificadas 4 necessidades de UX:
  1. Capacidade de reanalisar o sistema após limpezas parciais sem reiniciar o processo no terminal.
  2. Atualização imediata do DOM ao limpar pastas órfãs (garantindo que os itens apagados sumam da tela com feedback de sucesso).
  3. Visualização detalhada das subpastas mais pesadas dentro de diretórios gigantes (drill-down limpo sem poluir a tabela).
  4. Navegação bidirecional entre o Dashboard e a Janela Inicial de Parâmetros.
- **Decisão:**
  1. Implementar endpoint `/api/reanalyze` no servidor HTTP local que re-executa a varredura e retorna os dados atualizados para refresh instantâneo.
  2. Implementar atualização reativa no JavaScript de `html_reporter.py`: remoção dos caminhos limpos de `REPORT_DATA.clean_suggestions` e do DOM, com recálculo de métricas em tempo real.
  3. Enriquecer `OccupantItem` com `sub_occupants` computados dinamicamente no `disk_scanner.py`, renderizados com botão de expansão accordion elegante na tabela do Passo 5.
  4. Adicionar botões de navegação no cabeçalho do Dashboard: "⚙️ Nova Configuração / Início" e "🔄 Reanalisar Sistema".

---

## ADR-006: Empacotamento Autocontido (PyInstaller) e Distribuição Standalone via GitHub Releases
- **Status:** Aceito
- **Data:** 2026-10-16
- **Contexto:**
  O usuário demandou poder rodar a aplicação no terminal (Windows ou macOS) com um único comando, sem a fricção de clonar repositório, baixar zip ou precisar ter interpretador Python previamente instalado na máquina.
- **Decisão:**
  1. **Empacotamento Standalone:** Utilizar PyInstaller para gerar executáveis binários de arquivo único (`--onefile`): `limpeza-macos` (macOS) e `limpeza-windows.exe` (Windows).
  2. **Resolução de Recursos Híbrida (`get_resource_path`):** Implementar módulo em `src/infrastructure/resources.py` que detecta a presença de `sys._MEIPASS` (runtime temporário do PyInstaller) para carregar os catálogos JSON offline (`windows_tweaks.json`, `macos_tweaks.json`, `safe_cleanup_rules.json`), com fallback transparente para o sistema de arquivos local em tempo de desenvolvimento.
  3. **Scripts de Bootstrap Oneliner:**
     - macOS: `install-macos.sh` (`curl -fsSL ... | bash`) baixa o binário compilado mais recente do GitHub Releases para `/tmp` e o executa repassando os argumentos de CLI.
     - Windows: `install-windows.ps1` (`irm ... | iex`) baixa `limpeza-windows.exe` para `$env:TEMP` e o executa diretamente.
  4. **Automação de Build na Esteira CI/CD:** Adicionar workflow do GitHub Actions (`.github/workflows/release.yml`) que compila os binários em runners nativos `macos-latest` e `windows-latest` e publica a Release oficial com os artefatos e seus checksums SHA-256.
- **Consequências:**
  - Redução drástica da barreira de entrada para usuários finais não-técnicos.
  - Preservação estrita da política Zero-Network (o binário opera 100% offline em `127.0.0.1`).
  - O código continua totalmente executável em modo interpretado padrão (`python3 main.py`) sem quebrar a experiência de desenvolvimento local.

---

## ADR-007: Esvaziamento Nativo da Lixeira Multiplataforma (Finder AppleScript no macOS & Shell32 no Windows) com Deleção Resiliente de Readonly
- **Status:** Aceito
- **Data:** 2026-10-17
- **Contexto:**
  No macOS, a pasta `~/.Trash` é protegida pelo subsistema de segurança TCC (Transparency, Consent, and Control) da Apple. Chamadas POSIX tradicionais em Python (`os.listdir`, `os.walk`, `os.remove`) geram silenciosamente ou explicitamente `PermissionError: [Errno 1] Operation not permitted`, impedindo o esvaziamento da Lixeira. Adicionalmente, arquivos de caches e pacotes com atributo somente-leitura (`readonly`) ou flags de imutabilidade (`uchg`) causavam falhas silenciosas em `shutil.rmtree` e `os.remove`.
- **Decisão:**
  1. **Esvaziamento Nativo no macOS:** Invocar a API nativa do Finder via AppleScript (`tell application "Finder" to empty trash`) com fallback de shell para remoção forçada de flags (`chflags -R nouchg ~/.Trash/*`). Para contagem em Dry-Run, consultar o Finder (`tell application "Finder" to count every item of trash`).
  2. **Esvaziamento Nativo no Windows:** Invocar a API Win32 `SHEmptyRecycleBinW` da `shell32.dll` (com flags `SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND`) ou fallback para PowerShell `Clear-RecycleBin -Force`.
  3. **Deleção Resiliente de Arquivos Readonly:** Equipar `_clean_directory_contents` e `clean_specific_paths` com um handler de desbloqueio automático: ao encontrar `PermissionError`, aplicar permissão de escrita via `os.chmod(path, stat.S_IWRITE | stat.S_IWUSR)` (e no macOS desativar `uchg`), tentando a exclusão uma segunda vez antes de registrar falha.
- **Consequências:**
  - A Lixeira passa a ser 100% esvaziada em qualquer versão moderna do macOS sem exigir concessão manual de Full Disk Access pelo usuário.
  - Arquivos e pastas residuais de caches bloqueados ou somente-leitura são efetivamente removidos do disco.



