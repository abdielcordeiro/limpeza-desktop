# 🛡️ Limpeza & Otimização Desktop (Windows & macOS)

Aplicação multiplataforma para análise de disco, limpeza segura de caches/temporários e otimização reversível do sistema operacional. Opera **100% localmente** com política estrita **Zero-Network** (sem telemetria e sem envio de dados externos).

---

## ✨ Como Funciona

Ao iniciar, a aplicação abre um painel interativo no seu navegador local (`127.0.0.1`) onde você pode:

- **Analisar o Uso do Disco:** Mapeia partições, arquivos pesados, aplicativos instalados e pastas residuais que ocupam espaço desnecessário.
- **Limpar Caches e Temporários com Segurança:** Remove arquivos temporários do sistema, caches de navegadores, shaders de GPU, relatórios de erro e caches de ferramentas de desenvolvimento conforme a sua seleção.
- **Otimizar o Sistema com Reversão:** Aplica ajustes recomendados de desempenho e privacidade salvando um ponto de restauração automático para desfazer alterações quando desejar.

---

## ⚡ Execução com 1 Comando

Não é necessário instalar Python ou configurar dependências manualmente. Basta executar o comando correspondente ao seu sistema:

### 🍎 macOS (Terminal / zsh)
```bash
curl -fsSL https://raw.githubusercontent.com/abdielcordeiro/limpeza-desktop/main/install-macos.sh | bash
```

### 🪟 Windows (PowerShell)
```powershell
irm https://raw.githubusercontent.com/abdielcordeiro/limpeza-desktop/main/install-windows.ps1 | iex
```

### 🪟 Windows (CMD / Prompt de Comando)
```cmd
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/abdielcordeiro/limpeza-desktop/main/install-windows.ps1 | iex"
```

---

## 🛠️ Modos de Uso Opcionais (Via Flags)

Caso esteja executando diretamente pelo terminal ou a partir do código-fonte, você pode utilizar os seguintes parâmetros:

- **`--dry-run --headless`**: Simula toda a análise de disco e limpeza sem alterar ou apagar nenhum arquivo, gerando apenas o relatório HTML final.
- **`--auto`**: Executa a limpeza automática de arquivos temporários seguros e otimizações essenciais diretamente no terminal, sem abrir o painel no navegador.
- **`--undo latest`**: Restaura as configurações originais do sistema a partir do último ponto de restauração salvo antes das otimizações.
