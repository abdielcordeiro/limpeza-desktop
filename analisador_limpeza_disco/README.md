# Analisador de Limpeza e Saúde de Discos Windows

Ecossistema modular em Python para varredura dinâmica de discos Windows, eliminação de falsos positivos de programas em uso (Postman, Antigravity, VSCode, etc.) e geração de um **Dashboard HTML Interativo** com checklist de acompanhamento.

---

## 🚀 Como Executar

A partir do diretório raiz do projeto (`d:\Projetos\servease-scripts`), execute:

```bash
python analisador_limpeza_disco/main.py
```

Você verá o menu interativo com as opções de varredura:
1. **Varredura Completa em TODAS as Partições** (Recomendado)
2. **Escolher uma Partição Específica** (ex: `C:`, `D:`)
3. **Focar Exclusivamente na Pasta AppData**

Ao final da execução, o relatório HTML interativo será gerado em:
`analisador_limpeza_disco/outputs/relatorio_limpeza_disco.html`

---

## 📊 Recursos Principais

1. **Dashboard HTML Interativo Monopágina**:
   - Sem dependências de bibliotecas externas complexas.
   - Design moderno com Dark Mode, gráficos de progresso e estatísticas em tempo real.
   - **Checklist Interativo**: Marque itens como limpos e acompanhe o total de gigabytes liberados. O estado fica salvo automaticamente no navegador via `localStorage`.

2. **Detecção Dinâmica de Partições (C:, D:, E:, etc.)**:
   - Identificação de cada partição, tamanho total, espaço livre, porcentagem de uso e alertas visuais de risco do sistema.

3. **Zero Falsos Positivos (Algoritmo de 5 Camadas)**:
   - Cruza programas instalados no Registro do Windows, `%LOCALAPPDATA%\Programs`, Atalhos do Menu Iniciar, Processos em Execução e Whitelist Dev para nunca marcar Postman, Antigravity, VSCode, Firefox, Zoom, etc. como órfãos.

4. **Guia de Migração C: -> D:**:
   - Identifica aplicações pesadas no SSD do Sistema Operacional e fornece orientações sobre viabilidade e transferência.

5. **Diagnóstico do Microsoft OneDrive**:
   - Mede a pegada de espaço físico do OneDrive no disco e exibe o passo a passo para desvincular o computador e liberar espaço sem perder dados na nuvem.

---

## 📁 Estrutura de Arquivos

```text
analisador_limpeza_disco/
├── main.py                         # Ponto de entrada e orquestrador
├── README.md                       # Este guia rápido
├── ARQUITETURA.md                  # Documentação detalhada da arquitetura técnica
├── core/                           # Núcleo de lógica de negócio e varredura
│   ├── partitions.py               # Mapeamento dinâmico de partições e saúde
│   ├── active_apps.py              # Algoritmo de 5 camadas de detecção de apps
│   ├── scanner.py                  # Varredura de arquivos gigantes e pastas
│   ├── evaluator.py                # Classificador de risco e migrações
│   └── onedrive.py                 # Diagnóstico do OneDrive
├── reporters/                      # Geradores de apresentação
│   └── html_reporter.py            # Gerador do Dashboard HTML Interativo
└── outputs/                        # Pasta de saída dos relatórios (ignorada no Git)
    └── .gitkeep
```
