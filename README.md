# 🛡️ Limpeza & Otimização Desktop Multiplataforma (Windows & macOS)

Sistema completo e autônomo de **Limpeza de Espaço em Disco**, **Caça a Pastas Órfãs (Algoritmo de 5 Camadas Anti-Falsos Positivos)**, **Radar de Arquivos Gigantes e Aplicativos Pesados** e **Otimização do Sistema Operacional (Engenharia Reversa Sanitizada do WinUtil para Windows & Otimizador Nativo para macOS)** com suporte a **Snapshot de Estado e Reversão (`Undo`)**.

---

## 🔒 Política Estrita Zero-Network & Privacidade Absoluta

- **100% Python Standard Library:** Desenvolvido exclusivamente com bibliotecas nativas do Python (`os`, `sys`, `shutil`, `pathlib`, `subprocess`, `json`, `winreg`, `plistlib`, `ctypes`, `http.server`). **Zero dependências externas (`pip`)**.
- **Zero Telemetria / Zero Conexões Externas:** Nenhum arquivo pessoal, dado da máquina, endereço IP ou log é transmitido para fora da sua máquina.
- **Engenharia Reversa Sanitizada do WinUtil:** Todos os 8 pontos de comunicação externa identificados no `ChrisTitusTech/winutil` (`christitus.com`, download do binário fechado `OOSU10.exe`, injeção remota de listas no arquivo `hosts`, instaladores remotos do Chocolatey e fontes externas do Google) foram **estritamente auditados e banidos**. Veja o laudo completo em [`docs/architecture/03-WINUTIL-REVERSE-ENGINEERING-AUDIT.md`](file:///Users/abdielcordeiro/IdeaProjects/limpeza-desktop/docs/architecture/03-WINUTIL-REVERSE-ENGINEERING-AUDIT.md).

---

## 🧭 Guia de Execução: Qual comando utilizar?

A aplicação possui 4 modos principais de operação para atender a diferentes necessidades:

| Modo de Execução | Comando | Abre Janela? | Apaga Arquivos Reais? | Aplica Tweaks Reais? | Para que serve? |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **1. Visual Interativo** *(Recomendado)* | `python3 main.py` | **Sim (127.0.0.1)** | Conforme você marcar | Conforme você marcar | Abre o painel no navegador para você ver as opções, escolher o que limpar e acompanhar o progresso ao vivo. |
| **2. Simulação Segura** *(Dry-Run)* | `python3 main.py --dry-run --headless` | Não (Terminal) | **Não (Simulação)** | **Não (Simulação)** | Audita o disco e simula os ganhos sem risco. Gera o relatório HTML para você ver o que liberaria. |
| **3. Autônomo Direto** *(Rápido)* | `python3 main.py --auto` | Não (Terminal) | **Sim (Temporários Seguros)** | **Sim (Preset Seguro)** | Faxina rápida pelo terminal com 1 comando. Limpa temporários seguros, aplica tweaks essenciais e entrega o HTML. |
| **4. Reversão de Tweaks** *(Desfazer)* | `python3 main.py --undo latest` | Não (Terminal) | Não | **Restaura Estado Anterior** | Restaura os valores originais do sistema que estavam salvos no último snapshot antes das otimizações. |

---

## 🚀 Detalhamento dos Comandos

### 1. Janela Inicial Interativa de Navegação (Recomendado)
Ao rodar este comando, o terminal inicializa um servidor local estritamente seguro (`127.0.0.1`) e **abre automaticamente uma janela no seu navegador padrão**:

```bash
python3 main.py
# No Windows:
python main.py
```

**O que você pode fazer na janela:**
1. **Confirmar o Sistema Operacional e Discos:** Auto-detecta Windows ou macOS e lista as partições ativas (`C:`, `D:`, volumes APFS).
2. **Selecionar Regras de Limpeza Autônoma:**
   - Caches do Sistema e Pastas `%TEMP%` / `~/Library/Logs`.
   - Shaders de GPU (`DXCache`, `GLCache`, WebKit Metal).
   - Relatórios de Erro e Crash Dumps (`WER`, `CrashReporter`).
   - Caches de Navegadores e Frameworks Electron (WhatsApp, Discord, VSCode, Slack, Postman).
   - Caches de Ferramentas de Desenvolvimento (`pip`, `npm`, `yarn`, `gradle`, `nuget`, `Homebrew`, `Xcode DerivedData`).
   - *(Opcional)* Checkbox para **Auto-limpar Pastas Órfãs Verificadas**.
3. **Escolher Otimizações de Sistema (Tweaks):**
   - Presets rápidos: `Padrão Recomendado`, `Mínimo Seguro`, `Avançado` ou `Nenhum`.
   - Seleção individual de cada tweak com descrição clara e nível de risco.
   - Botão **"Desfazer Otimizações (Undo)"** para reverter modificações anteriores.
4. **Acompanhar o Progresso ao Vivo:** Barra de porcentagem, etapa atual e console de log em tempo real.
5. **Dashboard de Resultados Interativo & Reativo:** Ao terminar, a tela exibe o relatório com os gigabytes liberados, ranking dos maiores arquivos e ferramentas dinâmicas:
   - **🔄 Reanálise On-Demand:** Permite reanalisar discos, ocupantes e métricas com um clique direto pelo Dashboard sem reiniciar o comando no terminal.
   - **🗑️ Remoção Reativa de Órfãos (Passo 4):** Ao selecionar e limpar pastas órfãs e caches, os itens são removidos do disco e **desaparecem imediatamente da tabela**, atualizando em tempo real o espaço liberado e pendências.
   - **📂 Drill-down de Subpastas (Passo 5):** Expansão sanfonada limpa nos maiores diretórios para inspecionar exatamente quais subpastas consomem mais espaço com mini barras de proporção visual.
   - **⚙️ Retorno ao Formulário Inicial:** Botão de navegação direto no topo do Dashboard para voltar à tela inicial (`/`) e realizar novas configurações a qualquer momento.

---

### 2. Simulação Segura no Terminal (`--dry-run --headless`)
Executa toda a análise diretamente pelo terminal **sem alterar nenhum bit no sistema operacional**:

```bash
python3 main.py --dry-run --headless
```

- Mede e calcula exatamente quanto espaço você liberaria.
- Cruza as 5 camadas de proteção para detectar pastas órfãs reais.
- Mapeia os 100 maiores arquivos da máquina e os aplicativos instalados mais pesados com subpastas detalhadas.
- Salva o relatório completo em `outputs/relatorio_limpeza_disco.html` e imprime o link no terminal.

---

### 3. Execução Autônoma Direta pelo Terminal (`--auto`)
Para quem deseja uma limpeza rápida e direta sem abrir janelas:

```bash
python3 main.py --auto
```

- Aplica a limpeza autônoma dos temporários 100% seguros.
- Aplica as otimizações essenciais do SO com criação automática de Snapshot.
- Gera o relatório HTML em `outputs/relatorio_limpeza_disco.html` e abre o navegador com o resumo final.

---

### 4. Reversão de Otimizações (`--undo`)
Toda vez que uma otimização é executada, o sistema captura o estado anterior exato da sua máquina (Registro do Windows, serviços ou `defaults` do macOS) em um arquivo JSON em `outputs/snapshots/`.

Para desfazer as alterações e voltar ao estado original:

```bash
# Reverte o último lote de otimizações aplicado:
python3 main.py --undo latest

# Ou reverte um snapshot específico:
python3 main.py --undo snapshot_20261016_072856
```

---

## ⚙️ Opções Avançadas da Linha de Comando (CLI Flags)

Você pode customizar o comportamento do comando passando parâmetros adicionais:

| Flag | Valores | Descrição |
| :--- | :--- | :--- |
| `--preset` | `minimal`, `standard`, `advanced`, `none` | Define o conjunto de Tweaks a aplicar (padrão: `standard`). |
| `--os` | `windows`, `macos` | Força a plataforma alvo para simulação ou inspeção de catálogos. |
| `--no-browser` | *(flag)* | Impede a abertura automática do navegador web ao concluir. |
| `--output` | `<caminho_do_arquivo.html>` | Customiza o caminho de saída do relatório HTML gerado. |

**Exemplo de uso avançado:**
```bash
# Simulação no terminal forçando perfil do Windows com preset avançado:
python3 main.py --dry-run --headless --os windows --preset advanced
```

---

## 🧪 Testes Automatizados e Qualidade

O projeto conta com uma suíte de 13 testes automatizados cobrindo Domínio, Catálogos, Algoritmo de 5 Camadas, Limpeza Segura, Reversibilidade (`Undo`), Drill-down de Subpastas, Reanálise On-Demand, Proteção contra Path Traversal e Auditoria Estática Zero-Network:

```bash
python3 -m unittest discover -s tests -v
```

---

## 📚 Documentação Técnica Completa (`docs/`)

Para detalhes arquiteturais aprofundados, consulte a documentação oficial:
- [**Índice Geral (`docs/00-INDEX.md`)**](file:///Users/abdielcordeiro/IdeaProjects/limpeza-desktop/docs/00-INDEX.md)
- [**Requisitos Funcionais e Não-Funcionais (`docs/requirements/RF-RNF.md`)**](file:///Users/abdielcordeiro/IdeaProjects/limpeza-desktop/docs/requirements/RF-RNF.md)
- [**System Design & Diagramas C4 (`docs/architecture/01-SYSTEM-DESIGN-C4.md`)**](file:///Users/abdielcordeiro/IdeaProjects/limpeza-desktop/docs/architecture/01-SYSTEM-DESIGN-C4.md)
- [**Decisões Arquiteturais — ADRs (`docs/architecture/02-ADR.md`)**](file:///Users/abdielcordeiro/IdeaProjects/limpeza-desktop/docs/architecture/02-ADR.md)
- [**Dossiê de Engenharia Reversa e Auditoria de Privacidade do WinUtil (`docs/architecture/03-WINUTIL-REVERSE-ENGINEERING-AUDIT.md`)**](file:///Users/abdielcordeiro/IdeaProjects/limpeza-desktop/docs/architecture/03-WINUTIL-REVERSE-ENGINEERING-AUDIT.md)
