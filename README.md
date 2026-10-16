# 🛡️ Limpeza & Otimização Desktop Multiplataforma (Windows & macOS)

Sistema completo de **Limpeza Autônoma de Espaço**, **Detecção de Pastas Órfãs (5 Camadas Anti-Falsos Positivos)**, **Mapeamento de Aplicativos e Arquivos Gigantes** e **Otimização Profunda de Sistema (Motor WinUtil Sanitizado no Windows & Otimizador Nativo no macOS)** com **Snapshot & Reversão (`Undo`)**.

---

## 🔒 Política Estrita Zero-Network & Privacidade Absoluta

- **100% Python Standard Library:** Zero pacotes externos de terceiros (`pip`).
- **Zero Telemetria / Zero Conexões Externas:** Nenhum dado da máquina, IP ou telemetria é enviado para servidores externos.
- **WinUtil 100% Sanitizado:** Todos os 8 pontos de comunicação externa do `ChrisTitusTech/winutil` (`christitus.com`, `OOSU10.exe`, listas remotas `hosts`, Chocolatey remoto e Google Fonts) foram auditados e banidos (veja [`docs/architecture/03-WINUTIL-REVERSE-ENGINEERING-AUDIT.md`](file:///Users/abdielcordeiro/IdeaProjects/limpeza-desktop/docs/architecture/03-WINUTIL-REVERSE-ENGINEERING-AUDIT.md)).

---

## 🚀 Como Executar (Windows e macOS)

### 1. Janela Inicial Interativa de Navegação (Recomendado)
Abre automaticamente a interface gráfica local (`127.0.0.1`) no seu navegador para selecionar o sistema operacional, regras de limpeza autônoma, presets de Tweaks e escopo da varredura:

```bash
python3 main.py
# Ou no Windows:
python main.py
```

### 2. Execução Autônoma Direto no Terminal (`--auto`)
Executa a limpeza autônoma e otimizações do preset padrão diretamente pelo terminal e gera o Dashboard HTML final em `outputs/relatorio_limpeza_disco.html`:

```bash
python3 main.py --auto
```

### 3. Simulação Segura (`--dry-run --headless`)
Analisa todo o potencial de limpeza e valida todos os Tweaks sem apagar nenhum arquivo nem alterar configurações do SO:

```bash
python3 main.py --dry-run --headless
```

### 4. Reverter Otimizações Anteriores (`--undo`)
Restaura de forma idempotente os valores originais da máquina salvos no último Snapshot (`outputs/snapshots/`):

```bash
python3 main.py --undo latest
```

---

## 🧪 Executar a Suíte de Testes Automatizados

```bash
python3 -m unittest discover -s tests -v
```

---

## 📚 Documentação de Engenharia (`docs/`)

- [Índice Geral (`docs/00-INDEX.md`)](file:///Users/abdielcordeiro/IdeaProjects/limpeza-desktop/docs/00-INDEX.md)
- [Requisitos Funcionais e Não-Funcionais (`docs/requirements/RF-RNF.md`)](file:///Users/abdielcordeiro/IdeaProjects/limpeza-desktop/docs/requirements/RF-RNF.md)
- [System Design & Diagramas C4 (`docs/architecture/01-SYSTEM-DESIGN-C4.md`)](file:///Users/abdielcordeiro/IdeaProjects/limpeza-desktop/docs/architecture/01-SYSTEM-DESIGN-C4.md)
- [Architecture Decision Records (`docs/architecture/02-ADR.md`)](file:///Users/abdielcordeiro/IdeaProjects/limpeza-desktop/docs/architecture/02-ADR.md)
- [Dossiê de Engenharia Reversa e Auditoria WinUtil (`docs/architecture/03-WINUTIL-REVERSE-ENGINEERING-AUDIT.md`)](file:///Users/abdielcordeiro/IdeaProjects/limpeza-desktop/docs/architecture/03-WINUTIL-REVERSE-ENGINEERING-AUDIT.md)
