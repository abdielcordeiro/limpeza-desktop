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

---

## ADR-008: Diagnóstico Nativo Zero-Dependency de Hardware e Otimização Diferenciada de Disco (HDD Defrag vs SSD TRIM / APFS Maintenance)
- **Status:** Aceito
- **Data:** 2026-10-18
- **Contexto:**
  O sistema já analisa o consumo lógico de espaço em disco e aplica otimizações de sistema operacional, mas não oferecia visibilidade da saúde física e operacional dos componentes de hardware (Storage SSD/HDD, Memória RAM, GPU e Bateria). Além disso, usuários de Windows frequentemente buscam a "desfragmentação de disco" como ferramenta de manutenção, sem saber que desfragmentar um SSD moderno é prejudicial (desgaste desnecessário de ciclos de gravação nas células NAND) e que no macOS o sistema de arquivos APFS possui arquitetura completamente diferente (Copy-On-Write sem desfragmentação manual).
- **Decisão:**
  1. **Coleta de Métricas de Hardware 100% Nativa (Zero Network & Zero Dependências C++):**
     - **Windows:** Utilizar chamadas de sistema Win32 via `ctypes` (`GlobalMemoryStatusEx`) e comandos nativos PowerShell/CIM (`Get-PhysicalDisk`, `Get-StorageReliabilityCounter`, `Win32_VideoController`, `Win32_Battery`), garantindo execução sem requerer bibliotecas C++ externas compiladas.
     - **macOS:** Utilizar chamadas POSIX/Darwin nativas (`sysctl`, `vm_stat`) e utilitários integrados do sistema (`system_profiler -json SPStorageDataType SPDisplaysDataType SPPowerDataType`, `diskutil info`), que retornam estruturas JSON prontas para parsing seguro.
  2. **Estratégia de Otimização Diferenciada de Disco & Guardrails Anti-Degradação de NVMe:**
     - **Guardrails de Detecção (4 Camadas):**
       - 1ª Camada: `Get-PhysicalDisk` (`MediaType` e `BusType: NVMe`).
       - 2ª Camada: WMI `MSFT_PhysicalDisk` (`SeekPenalty == False` e `SpindleSpeed == 0` para SSD).
       - 3ª Camada: Pré-checagem nativa do Windows (`defrag /A`).
       - 4ª Camada (Fail-Safe Default): Em qualquer dúvida, ambiguidade ou falha de detecção, o sistema **assume obrigatoriamente que a unidade é SSD/NVMe**.
     - **Confirmação Obrigatória com Usuário (Human-in-the-Loop):** Se um disco for classificado como HDD mecânico e a desfragmentação de clusters for solicitada, o sistema exibe alerta formal com o modelo do disco e exige confirmação explícita do usuário de que se trata realmente de um disco mecânico. Se o usuário negar ou indicar que é SSD, a desfragmentação de blocos é cancelada imediatamente.
     - **Windows HDD Confirmado:** Análise de taxa de fragmentação e desfragmentação tradicional de clusters (`Optimize-Volume -DriveLetter <X> -Defrag` ou `defrag.exe <X>: /U /V`).
     - **Windows SSD / NVMe:** **Proibição estrita de defrag tradicional**. Execução exclusiva de **Retrim / TRIM e Consolidação de Slabs** (`Optimize-Volume -DriveLetter <X> -ReTrim` ou `defrag.exe <X>: /L`), informando ao controlador SSD os blocos liberados para o Garbage Collector.
     - **macOS (APFS & HFS+):** Não realizar desfragmentação de blocos (incompatível com a semântica Copy-on-Write do APFS e desnecessária em memória flash). Executar manutenção de integridade de metadados (`diskutil verifyVolume /`), verificação de suporte a **TRIM** nativo e limpeza de snapshots órfãos (`tmutil thinlocalsnapshots`).
  3. **Central de Alertas Preventivos e Recomendações Educativas:**
     - Exibir no Dashboard HTML cards visuais com status de saúde (S.M.A.R.T. Verified/Failing, Nível de Pressão de Memória / Swap Thrashing, Saúde e Ciclos da Bateria, Status de TRIM e Temperatura/VRAM de GPU), acompanhados de diagnósticos acionáveis para o usuário.
- **Consequências:**
  - Usuários recebem orientações educativas e precisas sobre a conservação física do computador, com risco zero de desgaste indevido ou degradação de SSDs/NVMes graças aos guardrails de 4 camadas e validação com o usuário.
  - Mantém adesão estrita ao **RNF-01 (Zero-Network Policy)** e **RNF-03 (Zero Dependências Pesadas)**.

---

## ADR-009: Engenharia Reversa Zero-Network do Ecossistema macOS (`Mole`, `Pearcleaner`, `mac-cleanup-py`, `Stats`, `OnyX`) e Motor de Varredura Adaptativa com Correlação por Bundle-ID
- **Status:** Aceito
- **Data:** 2026-11-20
- **Contexto:**
  Durante o diagnóstico de eficácia no macOS Apple Silicon (M1/M2/M3/M4), identificou-se que a varredura e limpeza inicial recuperava pouco espaço real devido a 5 limitações técnicas:
  1. O catálogo `safe_cleanup_rules.json` possuía apenas 6 regras estáticas no macOS, deixando de limpar `~/Library/Caches/*` de forma abrangente, caches de containers sandboxed (`~/Library/Containers/*/Data/Library/Caches`), diretórios Darwin por usuário (`DARWIN_USER_CACHE_DIR` em `/private/var/folders/.../C/`) e ecossistemas pesados de desenvolvimento (Xcode DeviceSupport/Archives, JetBrains IDEs, CocoaPods, uv, Poetry, pnpm, Yarn Berry, Bun, Playwright, Go, Flutter).
  2. O scanner `DiskScannerAdapter` possuía um limite rígido de `visited_dirs < 2500` no BFS e `_fast_dir_size(max_files=3000)`, truncando mais de 80% da árvore `~/Library` e subestimando tamanhos de pacotes grandes.
  3. O método `get_homebrew_and_pkgutil()` dividia todos os pacotes `com.apple.pkg.*` em palavras curtas de 3 letras, gerando falsos negativos na detecção de pastas órfãs.
  4. `LaunchAgents` órfãos (cujo binário apontado no `.plist` já havia sido desinstalado) continuavam sendo lidos pela Camada 3 como indicadores ativos, protegendo indevidamente pastas órfãs.
  5. A leitura de bateria via `system_profiler SPPowerDataType` falhava ao converter strings com símbolo `%` (`"94%"`) em `float`.
- **Decisão:**
  1. **Transcrição Local Sanitizada (Zero-Network):** Incorporar as regras de limpeza profunda inspiradas no `tw93/Mole` e `mac-cleanup-py` em 15+ categorias cirúrgicas no `safe_cleanup_rules.json`, protegidas por uma Whitelist de Estado (`CloudKit`, `nsurlsessiond`, `HomeKit`, `AudioUnitCache`, `Keychain`) e resolução dinâmica segura de `getconf DARWIN_USER_CACHE_DIR` / `DARWIN_USER_TEMP_DIR`.
  2. **Correlação Estruturada por `CFBundleIdentifier` e Auditoria de `LaunchAgents` (Inspirado no `Pearcleaner`):**
     - Filtrar stopwords e pacotes base do sistema em `pkgutil`, correlacionando os 12 diretórios da `~/Library` por `CFBundleIdentifier`, prefixo Reverse-DNS e nome canônico.
     - Inspecionar o binário executável (`Program` / `ProgramArguments[0]`) de cada `.plist` em `LaunchAgents`/`LaunchDaemons`: se o binário alvo não existir no disco, classificá-lo como **Agente de Inicialização Órfão** e excluí-lo da Camada 3 de proteção.
  3. **Orçamento Adaptativo BFS e Blocos Físicos APFS (`st_blocks * 512`):**
     - Expandir o orçamento do scanner para até `25.000` diretórios e `25.000` arquivos por bundle fechado, priorizando `st_blocks * 512` no macOS para refletir a ocupação física real no container APFS.
  4. **Telemetria IOKit Direta (`ioreg -rn AppleSmartBattery -a`):**
     - Coletar métricas de bateria via `ioreg` com `plistlib.loads` (< 15ms, 100% imune a formatação textual), `diskutil info -plist /` para `Purgeable Space` e `vm_stat` com `hw.pagesize` (`16384` bytes no Apple Silicon).
- **Consequências:**
  - Aumento expressivo na descoberta e recuperação segura de gigabytes no macOS Apple Silicon (Containers, Dev Caches, Darwin Caches e Órfãos), mantendo zero falsos positivos e 100% de conformidade com a política Zero-Network.

---

## ADR-010: Arquitetura de Ganchos Interativos Web (`127.0.0.1`), Quarentena Padrão via Lixeira e Motor Consultivo de Vida Útil (`Longevity Health Score`)
- **Status:** Aceito
- **Data:** 2026-11-20
- **Contexto:**
  O usuário precisava que a aplicação Web local (`127.0.0.1`) deixasse de ser apenas um relatório passivo nas Abas 2, 5, 7 e 8 e passasse a oferecer ganchos interativos completos para: (a) apagar ou mover para a Lixeira arquivos/pastas gigantes e subpastas diretamente da UI, (b) abrir a localização no Finder/Explorer, (c) executar regras individuais de limpeza após um Dry-Run, (d) remover `LaunchAgents` órfãos e encerrar processos pesados/zumbis, e (e) receber recomendações acionáveis sobre a saúde e vida útil da máquina.
- **Decisão:**
  1. **Novos Endpoints REST Estritamente Locais (`127.0.0.1`):**
     - `POST /api/file-action`: Executa `trash` (move para `~/.Trash` / Recycle Bin como padrão seguro) ou `delete` (remoção permanente resiliente) para caminhos aprovados pelo guardrail `is_safe_path_to_clean()`, recalculando métricas e atualizando o DOM sem reload.
     - `POST /api/reveal-path`: Abre o item no Finder (`open -R`) ou Windows Explorer (`explorer.exe /select,`).
     - `POST /api/execute-rule`: Executa sob demanda uma única regra de limpeza autônoma da Aba 2.
     - `GET /api/live-health`: Atualiza instantaneamente telemetria de RAM/Swap, Bateria, Processos, Startup Items e `Longevity Health Score` sem re-escanear o disco.
     - `POST /api/startup-action`: Remove ou desativa `LaunchAgents` / itens de inicialização órfãos salvando backup prévio em `outputs/snapshots/`.
     - `POST /api/process-action`: Encerra com segurança (`SIGTERM`) processos de usuário selecionados no inspetor, bloqueando processos críticos do SO (`PID <= 1`, `kernel_task`, `launchd`, `WindowServer`, `System`, `svchost`, `csrss`, `lsass`).
     - `POST /api/upgrade-packages`: Executa `brew upgrade` / `brew cleanup` ou `winget upgrade` sob ação explícita do usuário na Aba 7.
  2. **Motor Consultivo `Longevity Health Score (0–100)`:**
     - Computar score determinístico em 4 pilares (Armazenamento/NAND 35%, Memória/Swap 25%, Higiene/Boot 20%, Bateria/Térmica 20%) acompanhado de cartões `LongevityRecommendation` com botão de ação 1-clique integrado aos endpoints acima.
- **Consequências:**
  - Experiência de painel de controle desktop completo, reativo e seguro, com quarentena nativa via Lixeira e proteção estrita contra exclusão de arquivos do sistema operacional.

---

## ADR-011: Raio-X das Categorias Ocultas de Armazenamento ("Documentos" & "Dados do Sistema"), Varredura Completa da Home (`~`), Artefatos Reconstruíveis de Projetos e Navegação em Árvore Sob Demanda (`/api/inspect-directory`)
- **Status:** Aceito
- **Data:** 2026-11-22
- **Contexto:**
  Durante os testes em produção no macOS Apple Silicon (`219,68 GB / 245,11 GB usados`), identificou-se que os Ajustes do Sistema do macOS exibiam **`18,67 GB` em Documentos** e **`148,52 GB` em Dados do Sistema**, mas o navegador nativo da Apple não revelava o que ocupava os `18,67 GB` de Documentos (pois oculta todos os `dot-folders` `~/.*` e não agrega árvores de código) nem oferecia inspeção de `Dados do Sistema`. Na nossa aplicação, 5 fatores impediam a visibilidade e a evolução real na remoção:
  1. O escopo padrão `SMART_FAST` no `OrchestratorService._resolve_scan_targets()` olhava apenas `~/Library/...`, `~/Downloads` e 5 dotfiles específicos, deixando de fora `~/Documents`, `~/Desktop`, `~/IdeaProjects` (e demais pastas do usuário em `~`) bem como todas as demais pastas ocultas `~/.*` (`~/.gemini`, `~/.cursor`, `~/.vscode`, `~/.ollama`, `~/.lmstudio`, `~/.docker`, `~/.nvm`, `~/.pyenv`, `~/.sdkman`, `~/.rustup`, `~/.m2`, `~/.pub-cache`, `~/.cocoapods`, `~/.android`, `~/.local`, `~/.config`).
  2. O catálogo `safe_cleanup_rules.json` mantinha `default_enabled: false` nas regras de maior peso para desenvolvedores (`mac_jetbrains_caches`, `mac_node_js_caches`, `mac_python_dev_caches`, `mac_jvm_native_mobile_caches`, `win_dev_caches`), além de limpar apenas 4 subpastas fixas em `@DARWIN_USER_CACHE_DIR@` e apenas o perfil `Default` de navegadores Chromium.
  3. Em `AutonomousCleanerAdapter.execute_rule()`, alvos resolvidos via wildcard (`/*`) eram limpos com `remove_root=False`, mantendo milhares de subpastas de cache vazias.
  4. Em `DiskScannerAdapter.scan_and_evaluate()`, pastas de dependências e build (`node_modules`, `.venv`, `venv`, `target`, `build`, `.dart_tool`, `.next`, `Pods`) eram medidas mas não registradas em `clean_candidates`.
  5. A deduplicação hierárquica em `top_occupants` ocultava subpastas sob a pasta pai e limitava `sub_occupants` a 1 nível de 5 itens, impedindo navegação profunda.
- **Decisão:**
  1. **Descoberta Dinâmica Completa da Home (`~`) em `SMART_FAST`:** Escanear dinamicamente todas as subpastas de primeiro nível de `~` (visíveis e ocultas `~/.*`) junto com os diretórios de `~/Library`, `/Library/Developer` e `/opt/homebrew`.
  2. **Motor de Raio-X de Armazenamento (`StorageXRayReport` & `StorageCategoryBreakdown`):** Decompor explicitamente no relatório e na Aba 1:
     - **Raio-X de "Documentos & Pasta Pessoal (`~`)":** Pastas Visíveis & Projetos (`~/Documents`, `~/IdeaProjects`, `~/Desktop`, `~/Downloads`), Pastas Ocultas `~/.*` ("Espaço Fantasma") e Artefatos Reconstruíveis de Projetos (`node_modules`, `.venv`, `target`, `build`, `.dart_tool`, etc.).
     - **Raio-X de "Dados do Sistema (`System Data`)":** Containers/VMs (`Docker.raw`, `OrbStack`, `Colima`), `Application Support`, `Caches` & Darwin `/private/var/folders`, `Developer` & Simuladores (`CoreSimulator/Devices`, `Android SDK/AVD`), Package Managers (`/opt/homebrew`, `pnpm`, `m2`, `gradle`, `cargo`), Modelos Locais de IA (`ollama`, `lmstudio`, `huggingface`, `.gemini`, `.cursor`), Memória Virtual/Swap/Logs (`/private/var/vm`) e Snapshots APFS/Purgeable.
  3. **Habilitação Padrão (`default_enabled: true`) & Limpeza Profunda Real:** Ativar por padrão todas as regras seguras de caches de desenvolvimento, usar `remove_root=True` para subpastas resolvidas por wildcard (`/*`) e expandir wildcards multi-perfil (`Profile *`) e `@DARWIN_USER_CACHE_DIR@/*`.
  4. **Explorador de Árvore Sob Demanda (`POST /api/inspect-directory`):** Permitir drill-down recursivo infinito em qualquer diretório diretamente pelo Dashboard Web (`127.0.0.1`), listando subpastas e arquivos ordenados por tamanho físico real (`st_blocks * 512`) com ações diretas (`📂 Abrir`, `🗑️ Lixeira`, `🔥 Excluir`).
- **Consequências:**
  - Transparência total sobre os gigabytes ocultos em "Documentos" e "Dados do Sistema" e salto real na recuperação de espaço em máquinas de usuários e desenvolvedores.

---

## ADR-012: Reconciliação de Armazenamento APFS no macOS (Unidades SI Base-10 $1000^3$ vs IEC Base-2 $1024^3$ e Desconto de `PurgeableSpace`)
- **Status:** Aceito
- **Data:** 2026-11-23
- **Contexto:**
  Durante a validação lado a lado com os **Ajustes do Sistema > Geral > Armazenamento** do macOS em um volume APFS de 256 GB (`245.107.195.904` bytes), constatou-se uma divergência visual e numérica importante: enquanto o macOS informava **`217,1 GB de 245,11 GB usados`**, o card principal da nossa aplicação exibia **`Usado: 202.65 GB (88.8%) | Livre: 25.62 GB / 228.27 GB`**.
  A investigação técnica identificou duas causas combinadas:
  1. **Base-2 (IEC `GiB`, $1024^3$) rotulada como `GB` vs Base-10 (SI `GB`, $1000^3$):** Desde o Mac OS X 10.6, todo o ecossistema macOS (`Finder`, `Ajustes do Sistema`, `diskutil`, `system_profiler`) calcula armazenamento em potências de $1000$ ($245.107.195.904 / 1000^3 = 245,11\text{ GB}$ e $217.593.780.633 / 1000^3 = 217,59\text{ GB}$), enquanto `format_bytes()` dividia por $1024^3$ ($228,27\text{ GiB}$ e $202,65\text{ GiB}$), gerando uma defasagem de `7,37%` (~15 GB).
  2. **Alocação Bruta `statvfs` vs Espaço Purgável APFS (`PurgeableSpace`):** A chamada `shutil.disk_usage("/System/Volumes/Data")` retorna apenas blocos físicos livres imediatos (`raw_free = 27,51 GB`), sem contabilizar o `PurgeableSpace` (`~490 MB` a vários GBs em caches/snapshots APFS que o kernel Darwin libera sob demanda). O painel de Armazenamento do macOS (`StorageKit` / `SPStorageDataType`) soma o `PurgeableSpace` ao espaço disponível (`27,51 GB + 0,49 GB = 28,00 GB` disponíveis), resultando em `245,11 GB - 28,00 GB = 217,11 GB` (`217,1 GB`) usados. Além disso, `MacOSSystemProbeAdapter.get_partitions()` e `MacOSHardwareProbeAdapter.get_disks_health()` consultavam fontes distintas sem reconciliação.
- **Decisão:**
  1. **Funções de Formatação Explícitas (`format_bytes_si` em Base-10 $1000^3$ e `format_bytes_binary` em Base-2 $1024^3$):** Manter `format_bytes()` compatível e introduzir formatação SI Decimal (`1000^3`) para volumes e métricas de disco APFS/Storage (`use_si_units=True` no macOS), além de expor os campos binários explícitos (`GiB`) como metadado técnico complementar.
  2. **Sonda Unificada de Container APFS (`_probe_apfs_volume_metrics`):** Reconciliar `shutil.disk_usage`, `diskutil info -plist /System/Volumes/Data` (e `/`) e `system_profiler -json SPStorageDataType` tanto em `MacOSSystemProbeAdapter.get_partitions()` quanto em `MacOSHardwareProbeAdapter.get_disks_health()`, preenchendo em `PartitionInfo` e `StorageDiskHealth`:
     - `total_bytes`, `used_bytes` (efetivo padrão macOS Settings), `free_bytes` (disponível efetivo com purgável)
     - `raw_used_bytes` (alocado físico bruto APFS), `raw_free_bytes` (livre físico imediato `statvfs`), `purgeable_bytes` (`Espaço Purgável APFS`)
  3. **Transparência Visual Dual na UI (Aba 1, Aba 8 e Janela Inicial `/`):** Exibir o valor principal idêntico aos Ajustes do Sistema do macOS (`217.10 GB / 245.11 GB`) acompanhado de uma barra de metadados técnicos exibindo o `Alocado Bruto APFS`, o `Espaço Purgável` e o `Equivalente Binário IEC (GiB)`.
- **Consequências:**
  - Alinhamento 1:1 com os números reportados pelos Ajustes do Sistema do macOS, evitando confusão do usuário e garantindo precisão nos cálculos de saúde NAND e alertas de capacidade em toda a aplicação.






