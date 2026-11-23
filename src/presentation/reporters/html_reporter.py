# -*- coding: utf-8 -*-
"""Gerador do Relatório e Dashboard HTML Estático 100% Offline (Zero-Network)."""
import os
import json
from typing import Dict, Any, Union
from src.domain.entities import SystemExecutionReport


def generate_html_report(
    report: Union[SystemExecutionReport, Dict[str, Any]],
    output_filename: str = "outputs/relatorio_limpeza_disco.html",
) -> str:
    """
    Gera o arquivo HTML 100% autocontido e offline com as 7 abas estruturadas:
    1. Resumo & Saúde dos Discos
    2. Limpeza Autônoma Executada
    3. Aplicativos Grandes & Migração
    4. Pastas Órfãs & Caches Detectados
    5. Top 100 Maiores Arquivos & Pastas
    6. Otimizações do Sistema (WinUtil / macOS Tweaks)
    7. Cloud (OneDrive / iCloud) & Atualizações de Apps
    """
    data_dict = report.to_dict() if isinstance(report, SystemExecutionReport) else dict(report)
    data_json = json.dumps(data_dict, ensure_ascii=False).replace("</", "<\\/")

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard de Limpeza & Otimização Desktop (Windows & macOS)</title>
    <style>
        :root {{
            --bg-primary: #0B0F19;
            --bg-secondary: #111827;
            --bg-card: #1E293B;
            --bg-card-hover: #273549;
            --accent-primary: #38BDF8;
            --accent-hover: #0EA5E9;
            --text-main: #F8FAFC;
            --text-muted: #94A3B8;
            --border-color: #334155;
            --success-color: #10B981;
            --warning-color: #F59E0B;
            --danger-color: #EF4444;
            --purple-color: #A855F7;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }}

        body {{
            background-color: var(--bg-primary);
            color: var(--text-main);
            line-height: 1.55;
            min-height: 100vh;
            overflow-x: hidden;
        }}

        header {{
            background: linear-gradient(135deg, #0B0F19 0%, #1E293B 100%);
            border-bottom: 1px solid var(--border-color);
            padding: 1.25rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }}

        .logo-area {{
            min-width: 0;
        }}

        .logo-area h1 {{
            font-size: 1.35rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.65rem;
        }}

        .badge-pill {{
            background: rgba(56, 189, 248, 0.14);
            color: var(--accent-primary);
            font-size: 0.75rem;
            padding: 0.2rem 0.65rem;
            border-radius: 999px;
            border: 1px solid rgba(56, 189, 248, 0.35);
            white-space: nowrap;
            font-weight: 600;
        }}

        .logo-area p {{
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-top: 0.25rem;
        }}

        .header-stats {{
            display: flex;
            gap: 0.85rem;
            align-items: center;
            flex-wrap: wrap;
        }}

        .stat-box {{
            background: var(--bg-card);
            padding: 0.65rem 1.1rem;
            border-radius: 12px;
            border: 1px solid var(--border-color);
            text-align: center;
            min-width: 135px;
        }}

        .stat-box .val {{
            font-size: 1.15rem;
            font-weight: 700;
            color: var(--accent-primary);
            white-space: nowrap;
        }}

        .stat-box .val.green {{
            color: var(--success-color);
        }}

        .stat-box .lbl {{
            font-size: 0.7rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.04em;
            white-space: nowrap;
        }}

        nav.tabs-nav {{
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-color);
            display: flex;
            overflow-x: auto;
            padding: 0 1.5rem;
            gap: 0.35rem;
        }}

        .tab-btn {{
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 0.9rem 1.1rem;
            font-size: 0.88rem;
            font-weight: 600;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            transition: all 0.18s ease;
            white-space: nowrap;
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
        }}

        .tab-btn:hover {{
            color: var(--text-main);
            background: rgba(255, 255, 255, 0.03);
        }}

        .tab-btn.active {{
            color: var(--accent-primary);
            border-bottom-color: var(--accent-primary);
        }}

        main.container {{
            max-width: 1480px;
            width: 100%;
            margin: 1.5rem auto;
            padding: 0 1.5rem 3rem 1.5rem;
        }}

        .tab-content {{
            display: none;
        }}

        .tab-content.active {{
            display: block;
        }}

        .grid-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(310px, 1fr));
            gap: 1.25rem;
            margin-bottom: 1.5rem;
        }}

        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 1.35rem;
            min-width: 0;
            max-width: 100%;
            overflow: hidden;
        }}

        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 0.85rem;
        }}

        .card-title {{
            font-size: 1.02rem;
            font-weight: 600;
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .badge {{
            padding: 0.22rem 0.65rem;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 600;
            white-space: nowrap;
            display: inline-block;
        }}

        .badge.success {{ background: rgba(16, 185, 129, 0.15); color: var(--success-color); border: 1px solid rgba(16, 185, 129, 0.35); }}
        .badge.warning {{ background: rgba(245, 158, 11, 0.15); color: var(--warning-color); border: 1px solid rgba(245, 158, 11, 0.35); }}
        .badge.danger {{ background: rgba(239, 68, 68, 0.15); color: var(--danger-color); border: 1px solid rgba(239, 68, 68, 0.35); }}
        .badge.purple {{ background: rgba(168, 85, 247, 0.15); color: var(--purple-color); border: 1px solid rgba(168, 85, 247, 0.35); }}
        .badge.info {{ background: rgba(56, 189, 248, 0.15); color: var(--accent-primary); border: 1px solid rgba(56, 189, 248, 0.35); }}

        .hw-grid-2 {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr));
            gap: 1.25rem;
            margin-bottom: 1.5rem;
        }}

        .hw-subcard {{
            background: rgba(11, 15, 25, 0.65);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 0.9rem 1.1rem;
            margin-top: 0.75rem;
            min-width: 0;
            overflow: hidden;
            box-sizing: border-box;
        }}

        .hw-metric-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.35rem 0;
            border-bottom: 1px dashed rgba(51, 65, 85, 0.4);
            font-size: 0.85rem;
            gap: 0.5rem;
            min-width: 0;
        }}

        .hw-metric-row:last-child {{
            border-bottom: none;
        }}

        .hw-metric-val {{
            font-weight: 600;
            text-align: right;
            word-break: break-word;
        }}

        .progress-bar-bg {{
            background: #0B0F19;
            height: 10px;
            border-radius: 999px;
            overflow: hidden;
            margin: 0.75rem 0;
        }}

        .progress-bar-fill {{
            height: 100%;
            border-radius: 999px;
        }}

        .toolbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.85rem;
            margin-bottom: 1.15rem;
            background: var(--bg-card);
            padding: 1rem 1.25rem;
            border-radius: 12px;
            border: 1px solid var(--border-color);
        }}

        .filter-controls {{
            display: flex;
            gap: 0.75rem;
            align-items: center;
            flex-wrap: wrap;
        }}

        input[type="text"], select {{
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 0.55rem 0.9rem;
            border-radius: 8px;
            font-size: 0.88rem;
        }}

        .btn {{
            background: var(--accent-primary);
            color: #0B0F19;
            border: none;
            padding: 0.58rem 1.1rem;
            border-radius: 8px;
            font-size: 0.86rem;
            font-weight: 700;
            cursor: pointer;
            white-space: nowrap;
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            transition: opacity 0.15s;
        }}

        .btn:hover {{
            opacity: 0.92;
        }}

        .btn.secondary {{
            background: transparent;
            color: var(--text-main);
            border: 1px solid var(--border-color);
        }}

        .btn.danger {{
            background: var(--danger-color);
            color: #fff;
        }}

        .btn.success {{
            background: var(--success-color);
            color: #052e16;
        }}

        .table-wrapper {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            overflow-x: auto;
            max-width: 100%;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }}

        th, td {{
            padding: 0.85rem 1rem;
            border-bottom: 1px solid rgba(51, 65, 85, 0.6);
            font-size: 0.86rem;
            vertical-align: middle;
        }}

        th {{
            background: rgba(15, 23, 42, 0.6);
            color: var(--text-muted);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.74rem;
            white-space: nowrap;
        }}

        td.nowrap {{
            white-space: nowrap;
        }}

        .path-cell {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            font-size: 0.78rem;
            color: var(--text-muted);
            word-break: break-all;
            max-width: 460px;
        }}

        label.checkbox-inline {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            font-size: 0.86rem;
        }}

        .toast-banner {{
            display: none;
            margin-bottom: 1rem;
            padding: 0.9rem 1.2rem;
            border-radius: 10px;
            background: rgba(16, 185, 129, 0.16);
            border: 1px solid var(--success-color);
            color: var(--text-main);
            font-weight: 500;
        }}

        .header-actions {{
            display: flex;
            gap: 0.65rem;
            align-items: center;
            flex-wrap: wrap;
        }}

        .btn.header-btn {{
            font-size: 0.8rem;
            padding: 0.45rem 0.85rem;
            text-decoration: none;
        }}

        .btn-expand-sub {{
            background: rgba(56, 189, 248, 0.12);
            color: var(--accent-primary);
            border: 1px solid rgba(56, 189, 248, 0.3);
            padding: 0.25rem 0.6rem;
            border-radius: 6px;
            font-size: 0.74rem;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            transition: all 0.15s ease;
            margin-top: 0.35rem;
        }}

        .btn-expand-sub:hover {{
            background: rgba(56, 189, 248, 0.22);
            border-color: var(--accent-primary);
        }}

        .subfolder-container {{
            background: rgba(11, 15, 25, 0.85);
            border-left: 3px solid var(--accent-primary);
            border-radius: 0 8px 8px 0;
            padding: 0.75rem 1rem;
            margin: 0.5rem 0;
        }}

        .subfolder-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.35rem 0;
            border-bottom: 1px dashed rgba(51, 65, 85, 0.5);
            font-size: 0.82rem;
        }}

        .subfolder-item:last-child {{
            border-bottom: none;
        }}

        .subfolder-meta {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}

        .subfolder-bar {{
            width: 75px;
            height: 6px;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 999px;
            overflow: hidden;
            display: inline-block;
        }}

        .subfolder-fill {{
            height: 100%;
            background: var(--accent-primary);
            border-radius: 999px;
        }}

        .btn-act {{
            background: rgba(56, 189, 248, 0.12);
            color: var(--accent-primary);
            border: 1px solid rgba(56, 189, 248, 0.3);
            padding: 0.22rem 0.55rem;
            border-radius: 6px;
            font-size: 0.74rem;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            white-space: nowrap;
            transition: all 0.15s ease;
        }}
        .btn-act:hover {{
            background: rgba(56, 189, 248, 0.25);
            border-color: var(--accent-primary);
        }}
        .btn-act.danger {{
            background: rgba(239, 68, 68, 0.12);
            color: var(--danger-color);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }}
        .btn-act.danger:hover {{
            background: rgba(239, 68, 68, 0.25);
            border-color: var(--danger-color);
        }}
        .btn-act.success {{
            background: rgba(16, 185, 129, 0.12);
            color: var(--success-color);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }}
        .btn-act.success:hover {{
            background: rgba(16, 185, 129, 0.25);
            border-color: var(--success-color);
        }}
        .btn-act.warning {{
            background: rgba(245, 158, 11, 0.12);
            color: var(--warning-color);
            border: 1px solid rgba(245, 158, 11, 0.3);
        }}
        .btn-act.warning:hover {{
            background: rgba(245, 158, 11, 0.25);
            border-color: var(--warning-color);
        }}
        .btn-act.purple {{
            background: rgba(168, 85, 247, 0.12);
            color: var(--purple-color);
            border: 1px solid rgba(168, 85, 247, 0.3);
        }}
        .btn-act.purple:hover {{
            background: rgba(168, 85, 247, 0.25);
            border-color: var(--purple-color);
        }}

        /* Raio-X de Armazenamento & Explorador Cirúrgico (RF-18 & RF-19) */
        .xray-category-card {{
            background: rgba(15, 23, 42, 0.75);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.15rem;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            min-width: 0;
            box-sizing: border-box;
            transition: border-color 0.15s ease;
        }}

        .xray-category-card:hover {{
            border-color: rgba(56, 189, 248, 0.4);
        }}

        .xray-item-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.4rem 0;
            border-bottom: 1px dashed rgba(51, 65, 85, 0.45);
            font-size: 0.82rem;
            gap: 0.5rem;
            min-width: 0;
        }}

        .xray-item-row:last-child {{
            border-bottom: none;
        }}

        .xray-item-name {{
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            min-width: 0;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 0.78rem;
        }}

        .breadcrumb-segment {{
            cursor: pointer;
            color: var(--accent-primary);
            text-decoration: underline;
            white-space: nowrap;
        }}

        .breadcrumb-segment:hover {{
            color: var(--accent-hover);
        }}
    </style>
</head>
<body>
    <header>
        <div class="logo-area">
            <h1>
                🛡️ Relatório de Limpeza & Otimização Desktop
                <span class="badge-pill" id="hdr-os">SO</span>
                <span class="badge-pill" id="hdr-mode">Modo</span>
            </h1>
            <p id="hdr-sub">Política Estrita Zero-Network • 100% Executado Localmente</p>
        </div>
        <div class="header-actions">
            <a href="/" class="btn secondary header-btn" title="Voltar ao Formulário Inicial de Escolha">⚙️ Nova Configuração / Início</a>
            <button class="btn header-btn" id="btn-reanalyze" onclick="triggerReanalyze()" title="Reanalisar Discos e Ocupantes">🔄 Reanalisar Sistema</button>
        </div>
        <div class="header-stats">
            <div class="stat-box">
                <div class="val green" id="stat-freed">0.00 B</div>
                <div class="lbl">Espaço Trabalhado (Autônomo)</div>
            </div>
            <div class="stat-box">
                <div class="val" id="stat-potential">0.00 B</div>
                <div class="lbl">Adicional Recuperável</div>
            </div>
            <div class="stat-box">
                <div class="val" id="stat-tweaks">0</div>
                <div class="lbl">Tweaks Processados</div>
            </div>
            <div class="stat-box">
                <div class="val" id="stat-apps">0</div>
                <div class="lbl">Apps Mapeados</div>
            </div>
            <div class="stat-box">
                <div class="val" id="stat-hw">Saudável</div>
                <div class="lbl">Saúde Hardware</div>
            </div>
        </div>
    </header>

    <nav class="tabs-nav">
        <button class="tab-btn active" onclick="switchTab('tab-overview', this)">1. Resumo & Saúde dos Discos</button>
        <button class="tab-btn" onclick="switchTab('tab-auto', this)">2. Limpeza Autônoma Executada</button>
        <button class="tab-btn" onclick="switchTab('tab-apps', this)">3. Aplicativos Grandes & Migração</button>
        <button class="tab-btn" onclick="switchTab('tab-orphans', this)">4. Pastas Órfãs & Caches Detectados</button>
        <button class="tab-btn" onclick="switchTab('tab-top100', this)">5. Top 100 Maiores Arquivos & Pastas</button>
        <button class="tab-btn" onclick="switchTab('tab-tweaks', this)">6. Otimizações do Sistema (WinUtil / macOS)</button>
        <button class="tab-btn" onclick="switchTab('tab-cloud', this)">7. Cloud (OneDrive / iCloud) & Updates</button>
        <button class="tab-btn" onclick="switchTab('tab-hardware', this)">8. Saúde de Hardware & Otimização de Storage</button>
    </nav>

    <main class="container">
        <div id="action-toast" class="toast-banner"></div>

        <!-- ABA 1: RESUMO & SAÚDE DOS DISCOS -->
        <section id="tab-overview" class="tab-content active">
            <div class="grid-cards" id="partitions-grid"></div>

            <!-- RAIO-X REAL DO ARMAZENAMENTO (RF-18 / ADR-011) -->
            <div id="storage-xray-section" style="margin-top:1.5rem;margin-bottom:1.5rem;">
                <div class="card" style="border: 1px solid rgba(56, 189, 248, 0.4); background: linear-gradient(145deg, #111827 0%, #1E293B 100%);">
                    <div class="card-header" style="flex-wrap:wrap;gap:0.75rem;">
                        <div class="card-title" style="font-size:1.15rem;display:flex;align-items:center;gap:8px;">
                            <span>🔍 Raio-X Real do Armazenamento: Desvendando "Documentos" e "Dados do Sistema"</span>
                        </div>
                        <span class="badge info">ADR-011 • Visibilidade Completa da Home (~)</span>
                    </div>
                    <p style="color:var(--text-muted);font-size:0.86rem;margin-bottom:1.25rem;">
                        O macOS agrupa gigabytes nas categorias opacas <strong>"Documentos"</strong> (escondendo dotfiles <code>~/.*</code> e dependências <code>node_modules</code>) e <strong>"Dados do Sistema"</strong> (sem botão nativo de inspeção). Este painel destrincha cirurgicamente o peso real de cada árvore.
                    </p>

                    <!-- 3 KPIs de Destaque no Topo -->
                    <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(280px, 1fr));gap:1rem;margin-bottom:1.5rem;">
                        <div style="background:rgba(15, 23, 42, 0.7);padding:1rem 1.25rem;border-radius:10px;border:1px solid var(--border-color);min-width:0;box-sizing:border-box;">
                            <div style="font-size:0.78rem;color:var(--text-muted);text-transform:uppercase;font-weight:600;white-space:nowrap;">📄 Pasta Pessoal (~ / "Documentos" do macOS)</div>
                            <div style="font-size:1.6rem;font-weight:700;color:var(--accent-primary);margin:0.25rem 0;white-space:nowrap;" id="xray-doc-total">0.00 B</div>
                            <div style="display:flex;flex-direction:column;gap:4px;font-size:0.76rem;margin-top:0.4rem;">
                                <div style="display:flex;justify-content:space-between;white-space:nowrap;"><span style="color:var(--text-muted);">Projetos & Pastas Visíveis:</span> <strong id="xray-doc-visible">0.00 B</strong></div>
                                <div style="display:flex;justify-content:space-between;white-space:nowrap;"><span style="color:var(--warning-color);">👻 Pastas Ocultas (~/.*):</span> <strong id="xray-doc-hidden" style="color:var(--warning-color);">0.00 B</strong></div>
                                <div style="display:flex;justify-content:space-between;white-space:nowrap;"><span style="color:var(--purple-color);">🧱 Builds Reconstruíveis:</span> <strong id="xray-doc-rebuildable" style="color:var(--purple-color);">0.00 B</strong></div>
                            </div>
                        </div>
                        <div style="background:rgba(15, 23, 42, 0.7);padding:1rem 1.25rem;border-radius:10px;border:1px solid var(--border-color);min-width:0;box-sizing:border-box;">
                            <div style="font-size:0.78rem;color:var(--text-muted);text-transform:uppercase;font-weight:600;white-space:nowrap;">⚙️ Dados do Sistema Mapeados (System Data)</div>
                            <div style="font-size:1.6rem;font-weight:700;color:var(--text-main);margin:0.25rem 0;white-space:nowrap;" id="xray-sys-total">0.00 B</div>
                            <p style="font-size:0.78rem;color:var(--text-muted);margin-top:0.4rem;">
                                Containers sandboxed, caches Darwin, SDKs Xcode, Homebrew, Swap/VM e Snapshots locais.
                            </p>
                        </div>
                        <div style="background:rgba(15, 23, 42, 0.7);padding:1rem 1.25rem;border-radius:10px;border:1px solid var(--border-color);min-width:0;box-sizing:border-box;">
                            <div style="font-size:0.78rem;color:var(--text-muted);text-transform:uppercase;font-weight:600;white-space:nowrap;">🧹 Potencial Recuperável Mapeado</div>
                            <div style="font-size:1.6rem;font-weight:700;color:var(--success-color);margin:0.25rem 0;white-space:nowrap;" id="xray-recoverable-total">0.00 B</div>
                            <p style="font-size:0.78rem;color:var(--text-muted);margin-top:0.4rem;">
                                Caches, pastas órfãs e artefatos de build elegíveis para remoção ou quarentena segura.
                            </p>
                        </div>
                    </div>

                    <!-- Grid dos 8 Cards de Categorias -->
                    <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(360px, 1fr));gap:1rem;" id="xray-categories-grid">
                    </div>
                </div>
            </div>

            <!-- MODAL / PAINEL DO EXPLORADOR CIRÚRGICO DE DIRETÓRIOS (RF-19) -->
            <div id="inspector-modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.78);z-index:9999;backdrop-filter:blur(6px);align-items:center;justify-content:center;padding:1.5rem;">
                <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:14px;width:100%;max-width:1100px;max-height:90vh;display:flex;flex-direction:column;box-shadow:0 20px 40px rgba(0,0,0,0.6);overflow:hidden;">
                    <!-- Header do Modal -->
                    <div style="padding:1.1rem 1.5rem;border-bottom:1px solid var(--border-color);display:flex;justify-content:space-between;align-items:center;background:var(--bg-card);">
                        <div style="display:flex;align-items:center;gap:10px;min-width:0;">
                            <span style="font-size:1.25rem;">📂</span>
                            <div style="min-width:0;">
                                <div style="font-weight:700;font-size:1.05rem;white-space:nowrap;">Explorador Cirúrgico de Diretórios (Drill-Down Nível a Nível)</div>
                                <div style="font-size:0.76rem;color:var(--text-muted);">Navegação recursiva infinita • Tamanho físico real no disco</div>
                            </div>
                        </div>
                        <button class="btn secondary" onclick="closeDirectoryInspector()" style="padding:0.35rem 0.75rem;font-size:0.85rem;">✖ Fechar</button>
                    </div>

                    <!-- Breadcrumbs & Navegação Superior -->
                    <div style="padding:0.75rem 1.5rem;background:rgba(15, 23, 42, 0.6);border-bottom:1px solid var(--border-color);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.75rem;">
                        <div id="inspector-breadcrumbs" style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:0.82rem;min-width:0;">
                        </div>
                        <div style="display:flex;align-items:center;gap:8px;">
                            <button class="btn secondary" id="btn-inspector-up" onclick="inspectorGoUp()" style="font-size:0.78rem;padding:0.3rem 0.65rem;" title="Subir um nível de diretório">⬆️ Subir Nível</button>
                            <span class="badge info" id="inspector-summary-badge" style="white-space:nowrap;">0 itens</span>
                        </div>
                    </div>

                    <!-- Tabela de Itens do Diretório Atual -->
                    <div style="flex:1;overflow-y:auto;padding:1rem 1.5rem;">
                        <div id="inspector-loading" style="display:none;text-align:center;padding:2rem;color:var(--accent-primary);">
                            ⏳ Carregando subpastas e calculando tamanho físico...
                        </div>
                        <div class="table-wrapper" id="inspector-table-wrapper">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Nome</th>
                                        <th>Tipo</th>
                                        <th>Tamanho</th>
                                        <th>Impacto na Pasta</th>
                                        <th>Segurança</th>
                                        <th style="text-align:right;">Ações Diretas</th>
                                    </tr>
                                </thead>
                                <tbody id="inspector-tbody">
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <div class="card-title">📋 Log de Auditoria da Sessão Local</div>
                    <span class="badge success">Zero-Telemetry Verificado</span>
                </div>
                <pre id="session-logs" style="background:#0B0F19;padding:1rem;border-radius:10px;font-size:0.8rem;color:#94A3B8;max-height:280px;overflow-y:auto;white-space:pre-wrap;"></pre>
            </div>
        </section>

        <!-- ABA 2: LIMPEZA AUTÔNOMA EXECUTADA -->
        <section id="tab-auto" class="tab-content">
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Regra / Categoria</th>
                            <th>Status</th>
                            <th>Arquivos</th>
                            <th>Espaço Liberado / Simulado</th>
                            <th>Detalhes e Caminhos</th>
                            <th>Ação</th>
                        </tr>
                    </thead>
                    <tbody id="auto-cleanup-tbody"></tbody>
                </table>
            </div>
        </section>

        <!-- ABA 3: APLICATIVOS GRANDES & MIGRAÇÃO -->
        <section id="tab-apps" class="tab-content">
            <div class="toolbar">
                <div class="filter-controls">
                    <input type="text" id="apps-search" placeholder="Filtrar aplicativo instalado..." oninput="renderInstalledApps()">
                </div>
                <span class="badge warning" id="apps-count-badge">0 aplicativos listados</span>
            </div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Aplicativo</th>
                            <th>Tamanho</th>
                            <th>Volume / Drive</th>
                            <th>Fornecedor / Bundle</th>
                            <th>Recomendação de Desinstalação / Migração</th>
                            <th>Ação</th>
                        </tr>
                    </thead>
                    <tbody id="installed-apps-tbody"></tbody>
                </table>
            </div>
        </section>

        <!-- ABA 4: PASTAS ÓRFÃS & CACHES DETECTADOS -->
        <section id="tab-orphans" class="tab-content">
            <div class="toolbar">
                <div class="filter-controls">
                    <label class="checkbox-inline">
                        <input type="checkbox" id="select-all-orphans" onchange="toggleAllOrphans(this.checked)">
                        <span>Selecionar Todos</span>
                    </label>
                    <input type="text" id="orphans-search" placeholder="Buscar pasta órfã ou cache..." oninput="renderOrphans()">
                </div>
                <div class="filter-controls" style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
                    <label class="checkbox-inline" style="white-space:nowrap;font-size:0.83rem;color:var(--text-main);">
                        <input type="radio" name="orphan-op-mode" id="op-mode-trash" value="trash" checked>
                        <span>🗑️ Mover p/ Lixeira (Recomendado)</span>
                    </label>
                    <label class="checkbox-inline" style="white-space:nowrap;font-size:0.83rem;color:var(--danger-color);">
                        <input type="radio" name="orphan-op-mode" id="op-mode-delete" value="delete">
                        <span>🔥 Exclusão Permanente</span>
                    </label>
                    <button class="btn success" onclick="executeSelectedCleanup()">🧹 Executar Ação nos Itens Selecionados</button>
                </div>
            </div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Sel.</th>
                            <th>Item / Pasta</th>
                            <th>Tamanho</th>
                            <th>Tipo</th>
                            <th>Classificação (5 Camadas)</th>
                            <th>Diagnóstico & Caminho</th>
                            <th>Ações</th>
                        </tr>
                    </thead>
                    <tbody id="orphans-tbody"></tbody>
                </table>
            </div>
        </section>

        <!-- ABA 5: TOP 100 MAIORES ARQUIVOS & PASTAS -->
        <section id="tab-top100" class="tab-content">
            <div class="toolbar">
                <div class="filter-controls">
                    <input type="text" id="top-search" placeholder="Buscar por nome ou caminho..." oninput="renderTopOccupants()">
                    <select id="top-safety-filter" onchange="renderTopOccupants()">
                        <option value="ALL">Todas as Classificações de Segurança</option>
                        <option value="🚫 Não Apagar">🚫 Não Apagar (Sistema Operacional)</option>
                        <option value="⚙️ Desinstalar">⚙️ Desinstalar via Sistema / App</option>
                        <option value="✅ Limpeza Direta">✅ Limpeza Direta (Sem Risco ao SO)</option>
                        <option value="⚠️ Avaliar">⚠️ Avaliar Conteúdo Pessoal</option>
                    </select>
                </div>
            </div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Nome</th>
                            <th>Tipo</th>
                            <th>Tamanho</th>
                            <th>Classificação de Segurança</th>
                            <th>Caminho & Recomendação</th>
                            <th>Ações</th>
                        </tr>
                    </thead>
                    <tbody id="top100-tbody"></tbody>
                </table>
            </div>
        </section>

        <!-- ABA 6: OTIMIZAÇÕES DO SISTEMA (WINUTIL / MACOS TWEAKS) -->
        <section id="tab-tweaks" class="tab-content">
            <div class="toolbar">
                <div>
                    <strong>Snapshot de Reversão Salvo:</strong>
                    <span id="snapshot-id-label" class="badge-pill">Nenhum snapshot nesta sessão</span>
                </div>
                <div>
                    <button class="btn danger" onclick="revertLastSnapshot()">⏪ Reverter Tweaks (Undo)</button>
                </div>
            </div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Otimização (Tweak)</th>
                            <th>Categoria</th>
                            <th>Ação</th>
                            <th>Status & Resultado</th>
                        </tr>
                    </thead>
                    <tbody id="tweaks-tbody"></tbody>
                </table>
            </div>
        </section>

        <!-- ABA 7: CLOUD (ONEDRIVE / ICLOUD) & ATUALIZAÇÕES -->
        <section id="tab-cloud" class="tab-content">
            <div class="grid-cards" id="cloud-cards"></div>
            <div class="card">
                <div class="card-header">
                    <div class="card-title">📦 Atualizações de Softwares Detectadas (winget / brew)</div>
                    <div style="display:flex;gap:8px;align-items:center;">
                        <span class="badge purple" id="updates-count-badge">0 pacotes</span>
                        <button class="btn-act purple" onclick="upgradePackage('__all__')">🚀 Atualizar Todos</button>
                        <button class="btn-act" style="border:1px solid var(--border-color);color:var(--text-muted);" onclick="upgradePackage('__cleanup__')">🧹 Limpar Cache</button>
                    </div>
                </div>
                <div class="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th>Software</th>
                                <th>Versão Atual</th>
                                <th>Nova Versão</th>
                                <th>Risco</th>
                                <th>Comando de Atualização</th>
                                <th>Ação</th>
                            </tr>
                        </thead>
                        <tbody id="updates-tbody"></tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- ABA 8: SAÚDE DE HARDWARE, LONGEVIDADE & PROCESSOS -->
        <section id="tab-hardware" class="tab-content">
            <!-- PAINEL DE DESTAQUE DO SCORE DE LONGEVIDADE (0-100) (RF-17) -->
            <div class="card" style="margin-bottom:1.5rem;background:linear-gradient(135deg, rgba(30,41,59,0.9) 0%, rgba(15,23,42,0.9) 100%);border:1px solid rgba(56,189,248,0.4);">
                <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:1rem;margin-bottom:1rem;">
                    <div style="display:flex;align-items:center;gap:1rem;">
                        <span style="font-size:2.5rem;font-weight:800;color:var(--accent-primary);line-height:1;" id="longevity-score-num">--</span>
                        <div>
                            <div style="font-size:0.8rem;text-transform:uppercase;color:var(--text-muted);font-weight:700;letter-spacing:0.04em;">Score de Saúde & Longevidade do Hardware</div>
                            <span class="badge success" id="longevity-grade-badge">Calculando...</span>
                        </div>
                    </div>
                    <div>
                        <button class="btn secondary" style="font-size:0.8rem;padding:0.45rem 0.9rem;" id="btn-live-health" onclick="refreshLiveHealth()">
                            🔄 Atualizar Telemetria em Tempo Real
                        </button>
                    </div>
                </div>
                
                <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(220px, 1fr));gap:1rem;margin-top:0.5rem;">
                    <div class="hw-subcard" style="margin-top:0;">
                        <div style="display:flex;justify-content:space-between;font-size:0.82rem;white-space:nowrap;margin-bottom:0.25rem;">
                            <span style="color:var(--text-muted)">1. Armazenamento & NAND:</span>
                            <strong id="pilar-storage-score">-- / 35</strong>
                        </div>
                        <div class="progress-bar-bg" style="margin:0.25rem 0;height:7px;"><div id="pilar-storage-bar" class="progress-bar-fill" style="width:0%;background:var(--accent-primary);"></div></div>
                    </div>
                    <div class="hw-subcard" style="margin-top:0;">
                        <div style="display:flex;justify-content:space-between;font-size:0.82rem;white-space:nowrap;margin-bottom:0.25rem;">
                            <span style="color:var(--text-muted)">2. Memória & Swap SSD:</span>
                            <strong id="pilar-memory-score">-- / 25</strong>
                        </div>
                        <div class="progress-bar-bg" style="margin:0.25rem 0;height:7px;"><div id="pilar-memory-bar" class="progress-bar-fill" style="width:0%;background:var(--success-color);"></div></div>
                    </div>
                    <div class="hw-subcard" style="margin-top:0;">
                        <div style="display:flex;justify-content:space-between;font-size:0.82rem;white-space:nowrap;margin-bottom:0.25rem;">
                            <span style="color:var(--text-muted)">3. Higiene & Boot:</span>
                            <strong id="pilar-hygiene-score">-- / 20</strong>
                        </div>
                        <div class="progress-bar-bg" style="margin:0.25rem 0;height:7px;"><div id="pilar-hygiene-bar" class="progress-bar-fill" style="width:0%;background:var(--purple-color);"></div></div>
                    </div>
                    <div class="hw-subcard" style="margin-top:0;">
                        <div style="display:flex;justify-content:space-between;font-size:0.82rem;white-space:nowrap;margin-bottom:0.25rem;">
                            <span style="color:var(--text-muted)">4. Elétrica / Térmica:</span>
                            <strong id="pilar-thermal-score">-- / 20</strong>
                        </div>
                        <div class="progress-bar-bg" style="margin:0.25rem 0;height:7px;"><div id="pilar-thermal-bar" class="progress-bar-fill" style="width:0%;background:var(--warning-color);"></div></div>
                    </div>
                </div>
            </div>

            <!-- GRID DE RECOMENDAÇÕES ACIONÁVEIS DE VIDA ÚTIL (RF-17) -->
            <div class="card" style="margin-bottom:1.5rem;" id="longevity-recommendations-box">
                <div class="card-header">
                    <div class="card-title">💡 Recomendações Acionáveis para Conservação do Hardware</div>
                    <span class="badge info" id="longevity-rec-count">0 Recomendações</span>
                </div>
                <div id="longevity-rec-grid" style="display:grid;grid-template-columns:repeat(auto-fit, minmax(320px, 1fr));gap:1rem;"></div>
            </div>

            <div id="hw-alerts-container"></div>

            <div class="hw-grid-2">
                <!-- CARD DISCOS / STORAGE -->
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">💽 Armazenamento Físico & S.M.A.R.T.</div>
                        <span class="badge info" id="hw-disks-count">0 Unidades</span>
                    </div>
                    <div id="hw-disks-list"></div>
                </div>

                <!-- CARD MEMÓRIA RAM & SWAP -->
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">🧠 Memória RAM & Diagnóstico de Swap</div>
                        <span class="badge" id="hw-ram-pressure-badge">Normal</span>
                    </div>
                    <div id="hw-ram-content"></div>
                </div>

                <!-- CARD GPU -->
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">🎮 Adaptadores Gráficos (GPU)</div>
                        <span class="badge purple" id="hw-gpu-count">0 GPUs</span>
                    </div>
                    <div id="hw-gpu-list"></div>
                </div>

                <!-- CARD BATERIA -->
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">🔋 Bateria & Alimentação</div>
                        <span class="badge" id="hw-battery-badge">Status</span>
                    </div>
                    <div id="hw-battery-content"></div>
                </div>
            </div>

            <!-- SEÇÃO DE PERSISTÊNCIA & STARTUP ITEMS (RF-17) -->
            <div class="card" style="margin-top:1.5rem;">
                <div class="card-header">
                    <div class="card-title">🚀 Agentes de Inicialização & Persistência (LaunchAgents / Startup)</div>
                    <span class="badge" id="startup-count-badge">0 Agentes</span>
                </div>
                <div class="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th>Nome do Agente</th>
                                <th>Escopo</th>
                                <th>Status do Binário</th>
                                <th>Caminho do Executável & Recomendação</th>
                                <th>Ação</th>
                            </tr>
                        </thead>
                        <tbody id="startup-tbody"></tbody>
                    </table>
                </div>
            </div>

            <!-- SEÇÃO DE TOP PROCESSOS CONSUMIDORES & ZUMBIS (RF-17) -->
            <div class="card" style="margin-top:1.5rem;">
                <div class="card-header">
                    <div class="card-title">⚡ Top Processos Consumidores de RAM/CPU & Detecção de Zumbis</div>
                    <span class="badge purple" id="processes-count-badge">Top 10</span>
                </div>
                <div class="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th>PID</th>
                                <th>Nome do Processo</th>
                                <th>CPU %</th>
                                <th>Memória (MB)</th>
                                <th>Estado</th>
                                <th>Ação</th>
                            </tr>
                        </thead>
                        <tbody id="processes-tbody"></tbody>
                    </table>
                </div>
            </div>

            <!-- SEÇÃO DE OTIMIZAÇÃO INTELIGENTE DE ARMAZENAMENTO (RF-14) -->
            <div class="card" style="margin-top:1.5rem;">
                <div class="card-header">
                    <div class="card-title">⚡ Otimização Inteligente de Armazenamento (Guardrails Anti-Degradação de NVMe)</div>
                    <span class="badge success">4 Camadas Ativas</span>
                </div>
                <div style="background:rgba(15,23,42,0.6);border:1px solid var(--border-color);border-radius:10px;padding:1rem;margin-bottom:1.25rem;">
                    <h4 style="font-size:0.92rem;color:var(--accent-primary);margin-bottom:0.35rem;">🛡️ Por que NÃO desfragmentar SSDs ou unidades NVMe?</h4>
                    <p style="font-size:0.83rem;color:var(--text-muted);line-height:1.45;">
                        Diferente de HDDs magnéticos onde arquivos fragmentados exigem movimentação física da cabeça de leitura mecânica, unidades de estado sólido (SSD/NVMe) possuem acesso direto por circuitos integrados flash NAND com tempo de resposta em nanossegundos. Desfragmentar um SSD reescreve blocos indevidamente, desgastando suas células de gravação sem qualquer ganho de desempenho. No Windows, o procedimento seguro é o comando <strong>TRIM / Retrim</strong>. No macOS com APFS (Apple File System), a arquitetura Copy-On-Write realiza alocação dinâmica contínua, onde a otimização segura consiste em <strong>verificação de integridade de metadados e expurgo de snapshots locais órfãos</strong>.
                    </p>
                </div>

                <div class="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th>Volume / Drive</th>
                                <th>Tipo de Mídia Detectado</th>
                                <th>Guardrail de Detecção</th>
                                <th>Ação Segura Recomendada</th>
                                <th>Confirmação / Execução Assistida</th>
                            </tr>
                        </thead>
                        <tbody id="hw-opt-tbody"></tbody>
                    </table>
                </div>

                <div id="hw-opt-result-box" style="display:none;margin-top:1rem;padding:1rem;border-radius:10px;background:rgba(16,185,129,0.12);border:1px solid var(--success-color);">
                    <div style="font-weight:700;color:var(--success-color);margin-bottom:0.35rem;" id="hw-opt-result-title">Otimização de Storage Concluída</div>
                    <p style="font-size:0.85rem;" id="hw-opt-result-msg"></p>
                    <div style="margin-top:0.5rem;font-size:0.78rem;color:var(--text-muted);" id="hw-opt-result-checks"></div>
                </div>
            </div>
        </section>
    </main>

    <script>
        let REPORT_DATA = {data_json};

        function escapeHtml(text) {{
            if (text === null || text === undefined) return '';
            return String(text)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }}

        function escapeAttr(text) {{
            if (text === null || text === undefined) return '';
            return String(text)
                .replace(/&/g, '&amp;')
                .replace(/'/g, '&#39;')
                .replace(/"/g, '&quot;');
        }}

        function setText(id, text) {{
            const el = document.getElementById(id);
            if (el) el.textContent = (text !== null && text !== undefined) ? text : '';
        }}

        function setHtml(id, html) {{
            const el = document.getElementById(id);
            if (el) el.innerHTML = (html !== null && html !== undefined) ? html : '';
        }}

        function switchTab(tabId, btnEl) {{
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            const target = document.getElementById(tabId);
            if (target) target.classList.add('active');
            if (btnEl) btnEl.classList.add('active');
        }}

        function showToast(msg) {{
            const t = document.getElementById('action-toast');
            if (t) {{
                t.textContent = msg;
                t.style.display = 'block';
                setTimeout(() => {{ t.style.display = 'none'; }}, 7000);
            }}
        }}

        function initDashboard() {{
            setText('hdr-os', (REPORT_DATA.os_version || REPORT_DATA.os_platform || 'OS').toUpperCase());
            setText('hdr-mode', REPORT_DATA.execution_mode === 'real' ? 'EXECUÇÃO REAL' : 'SIMULAÇÃO DRY-RUN');
            setText('hdr-sub', `Sessão ${{REPORT_DATA.session_id || '-'}} • Executado em ${{REPORT_DATA.executed_at || '-'}} • ${{REPORT_DATA.active_indicators_count || 0}} indicadores ativos nas 5 camadas`);

            setText('stat-freed', REPORT_DATA.total_bytes_freed_formatted || '0.00 B');
            setText('stat-potential', REPORT_DATA.potential_extra_bytes_formatted || '0.00 B');
            setText('stat-tweaks', (REPORT_DATA.tweaks_executed || []).length);
            setText('stat-apps', (REPORT_DATA.installed_apps || []).length);

            const hwHealth = REPORT_DATA.hardware_health || {{}};
            const hwStatusEl = document.getElementById('stat-hw');
            if (hwStatusEl) {{
                const ov = hwHealth.overall_status || 'Saudável';
                hwStatusEl.textContent = ov;
                hwStatusEl.className = 'val ' + (ov === 'Crítico' ? 'danger' : (ov === 'Atenção' ? 'warning' : 'green'));
            }}

            if (REPORT_DATA.snapshot_id) {{
                setText('snapshot-id-label', REPORT_DATA.snapshot_id);
            }}

            // Partições
            const pGrid = document.getElementById('partitions-grid');
            if (pGrid) {{
                pGrid.innerHTML = (REPORT_DATA.partitions || []).map(p => {{
                    const barColor = p.health_class === 'danger' ? 'var(--danger-color)' : (p.health_class === 'warning' ? 'var(--warning-color)' : 'var(--success-color)');
                    return `<div class="card">
                        <div class="card-header">
                            <div class="card-title">💽 ${{escapeHtml(p.drive_letter)}} <small style="color:var(--text-muted)">(${{escapeHtml(p.role)}})</small></div>
                            <span class="badge ${{escapeHtml(p.health_class)}}">${{escapeHtml(p.health_status)}}</span>
                        </div>
                        <div style="display:flex;justify-content:space-between;font-size:0.85rem;white-space:nowrap;">
                            <span>Usado: <strong>${{escapeHtml(p.used_formatted)}}</strong> (${{p.percent_used}}%)</span>
                            <span>Livre: <strong>${{escapeHtml(p.free_formatted)}}</strong> / ${{escapeHtml(p.total_formatted)}}</span>
                        </div>
                        <div class="progress-bar-bg">
                            <div class="progress-bar-fill" style="width:${{Math.min(p.percent_used, 100)}}%;background:${{barColor}}"></div>
                        </div>
                        ${{(p.purgeable_bytes > 0 || p.total_binary_formatted) ? `
                            <div style="display:flex;flex-wrap:wrap;gap:0.5rem 1rem;font-size:0.76rem;color:var(--text-muted);margin:0.45rem 0;padding:0.45rem 0.65rem;background:rgba(11,15,25,0.55);border-radius:8px;border:1px solid rgba(51,65,85,0.45);">
                                ${{p.purgeable_bytes > 0 ? `
                                    <span style="white-space:nowrap;">⚡ <strong>Alocado Bruto APFS:</strong> ${{escapeHtml(p.raw_used_formatted)}}</span>
                                    <span style="white-space:nowrap;">♻️ <strong>Espaço Purgável:</strong> <strong style="color:var(--accent-primary)">${{escapeHtml(p.purgeable_formatted)}}</strong></span>
                                    <span style="white-space:nowrap;">💽 <strong>Livre Físico Imediato:</strong> ${{escapeHtml(p.raw_free_formatted)}}</span>
                                ` : ''}}
                                ${{p.total_binary_formatted ? `
                                    <span style="white-space:nowrap;">📐 <strong>Binário (IEC 1024³):</strong> ${{escapeHtml(p.used_binary_formatted)}} / ${{escapeHtml(p.total_binary_formatted)}}${{p.purgeable_bytes > 0 && p.raw_used_binary_formatted ? ' (Bruto: ' + escapeHtml(p.raw_used_binary_formatted) + ')' : ''}}</span>
                                ` : ''}}
                            </div>
                        ` : ''}}
                        <p style="font-size:0.8rem;color:var(--text-muted)">${{escapeHtml(p.health_desc)}}</p>
                    </div>`;
                }}).join('');
            }}

            setText('session-logs', (REPORT_DATA.execution_logs || []).join(String.fromCharCode(10)));

            // Limpeza Autônoma
            const autoTbody = document.getElementById('auto-cleanup-tbody');
            if (autoTbody) {{
                const autoList = REPORT_DATA.autonomous_cleanups || [];
                autoTbody.innerHTML = autoList.length ? autoList.map(c => `<tr>
                    <td><strong>${{escapeHtml(c.name)}}</strong><br><small style="color:var(--text-muted)">${{escapeHtml(c.category)}}</small></td>
                    <td class="nowrap"><span class="badge ${{c.status === 'cleaned' ? 'success' : 'warning'}}">${{escapeHtml((c.status || '').toUpperCase())}}</span></td>
                    <td class="nowrap">${{c.files_removed}} arq.</td>
                    <td class="nowrap"><strong>${{escapeHtml(c.bytes_freed_formatted)}}</strong></td>
                    <td><div>${{escapeHtml(c.details)}}</div><div class="path-cell">${{escapeHtml((c.target_paths || []).join(' | '))}}</div></td>
                    <td class="nowrap"><button class="btn-act success" onclick="executeRule('${{escapeAttr(c.id)}}')">🧹 Limpar Agora</button></td>
                </tr>`).join('') : '<tr><td colspan="6">Nenhuma regra de limpeza autônoma executada nesta sessão.</td></tr>';
            }}

            try {{ renderInstalledApps(); }} catch(e) {{ console.error('Erro renderInstalledApps:', e); }}
            try {{ renderOrphans(); }} catch(e) {{ console.error('Erro renderOrphans:', e); }}
            try {{ renderTopOccupants(); }} catch(e) {{ console.error('Erro renderTopOccupants:', e); }}
            try {{ renderStorageXRay(); }} catch(e) {{ console.error('Erro renderStorageXRay:', e); }}
            try {{ renderTweaks(); }} catch(e) {{ console.error('Erro renderTweaks:', e); }}
            try {{ renderCloudAndUpdates(); }} catch(e) {{ console.error('Erro renderCloudAndUpdates:', e); }}
            try {{ renderHardwareAndStorage(); }} catch(e) {{ console.error('Erro renderHardwareAndStorage:', e); }}
        }}

                function renderInstalledApps() {{
            const q = (document.getElementById('apps-search').value || '').toLowerCase();
            const list = (REPORT_DATA.installed_apps || []).filter(a => a.name.toLowerCase().includes(q) || a.path.toLowerCase().includes(q));
            document.getElementById('apps-count-badge').textContent = `${{list.length}} aplicativos listados`;
            document.getElementById('installed-apps-tbody').innerHTML = list.length ? list.map(a => `<tr>
                <td><strong>${{a.name}}</strong><div class="path-cell">${{a.path}}</div></td>
                <td class="nowrap"><strong>${{a.size_formatted}}</strong></td>
                <td class="nowrap"><span class="badge purple">${{a.drive}}</span></td>
                <td>${{a.vendor}} ${{a.bundle_id ? `<br><small style="color:var(--text-muted)">${{a.bundle_id}}</small>` : ''}}</td>
                <td>${{a.uninstall_hint}}</td>
                <td class="nowrap"><button class="btn-act" onclick="revealPath('${{escapeAttr(a.path)}}')">📂 Abrir</button></td>
            </tr>`).join('') : '<tr><td colspan="6">Nenhum aplicativo encontrado para o filtro informado.</td></tr>';
        }}

        function renderOrphans() {{
            const q = (document.getElementById('orphans-search').value || '').toLowerCase();
            const savedChecked = JSON.parse(localStorage.getItem('limpeza_checked_orphans') || '{{}}');
            const list = (REPORT_DATA.clean_suggestions || []).filter(c => c.name.toLowerCase().includes(q) || c.path.toLowerCase().includes(q));
            document.getElementById('orphans-tbody').innerHTML = list.length ? list.map((c, idx) => {{
                const isChecked = savedChecked[c.path] ? 'checked' : '';
                return `<tr>
                    <td>
                        <label class="checkbox-inline">
                            <input type="checkbox" class="orphan-cb" data-path="${{c.path.replace(/"/g, '&quot;')}}" ${{isChecked}} onchange="saveOrphanCheck(this)">
                        </label>
                    </td>
                    <td><strong>${{c.name}}</strong> ${{c.was_auto_cleaned ? '<span class="badge success">Já Limpo</span>' : ''}}</td>
                    <td class="nowrap"><strong>${{c.size_formatted}}</strong></td>
                    <td>${{c.item_type || c.type}}</td>
                    <td class="nowrap"><span class="badge ${{c.risk_badge}}">${{c.risk_level}}</span></td>
                    <td><div>${{c.reason}}</div><div class="path-cell">${{c.path}}</div></td>
                    <td class="nowrap">
                        <button class="btn-act" onclick="revealPath('${{escapeAttr(c.path)}}')">📂 Abrir</button>
                        <button class="btn-act danger" onclick="fileAction('${{escapeAttr(c.path)}}', 'trash')">🗑️ Lixeira</button>
                    </td>
                </tr>`;
            }}).join('') : '<tr><td colspan="7">Nenhuma pasta órfã ou cache pendente encontrado.</td></tr>';
        }}

        function saveOrphanCheck(cb) {{
            const saved = JSON.parse(localStorage.getItem('limpeza_checked_orphans') || '{{}}');
            const p = cb.getAttribute('data-path');
            if (cb.checked) saved[p] = true;
            else delete saved[p];
            localStorage.setItem('limpeza_checked_orphans', JSON.stringify(saved));
        }}

        function toggleAllOrphans(checked) {{
            document.querySelectorAll('.orphan-cb').forEach(cb => {{
                cb.checked = checked;
                saveOrphanCheck(cb);
            }});
        }}

        async function executeSelectedCleanup() {{
            const selected = Array.from(document.querySelectorAll('.orphan-cb:checked')).map(cb => cb.getAttribute('data-path'));
            if (!selected.length) {{
                showToast('Selecione ao menos uma pasta órfã ou cache na tabela para limpar.');
                return;
            }}
            const isDelete = document.getElementById('op-mode-delete') && document.getElementById('op-mode-delete').checked;
            const action = isDelete ? 'delete' : 'trash';
            const verb = isDelete ? 'exclusão permanente' : 'quarentena na Lixeira';
            if (isDelete) {{
                if (!confirm(`Deseja realmente EXCLUIR DEFINITIVAMENTE ${{selected.length}} item(ns) selecionado(s)?`)) return;
            }}
            if (window.location.protocol.startsWith('http')) {{
                try {{
                    showToast(`Processando ${{verb}} de ${{selected.length}} itens...`);
                    const res = await fetch('/api/file-action', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{paths: selected, action: action, mode: 'real'}})
                    }});
                    const data = await res.json();
                    if (data.status === 'ok' || data.status === 'trashed' || data.success) {{
                        const cleanedSet = new Set(data.affected_paths || selected);
                        REPORT_DATA.clean_suggestions = (REPORT_DATA.clean_suggestions || []).filter(c => !cleanedSet.has(c.path));

                        const saved = JSON.parse(localStorage.getItem('limpeza_checked_orphans') || '{{}}');
                        (data.affected_paths || selected).forEach(p => delete saved[p]);
                        localStorage.setItem('limpeza_checked_orphans', JSON.stringify(saved));

                        if (data.total_freed_formatted) {{
                            document.getElementById('stat-freed').textContent = data.total_freed_formatted;
                        }}
                        if (data.potential_extra_formatted) {{
                            document.getElementById('stat-potential').textContent = data.potential_extra_formatted;
                        }}

                        renderOrphans();
                        showToast(`Sucesso! ${{data.bytes_freed_formatted || '0 B'}} liberados (${{verb}}).`);
                    }} else {{
                        showToast(data.message || data.error || 'Erro ao processar limpeza selecionada.');
                    }}
                    return;
                }} catch (e) {{
                    showToast('Erro de comunicação com o servidor local: ' + e.message);
                    return;
                }}
            }}
            showToast(`Selecionados ${{selected.length}} caminhos. Execute pelo painel ativo em 127.0.0.1 para remoção direta.`);
        }}

        function renderTopOccupants() {{
            const q = (document.getElementById('top-search').value || '').toLowerCase();
            const sf = document.getElementById('top-safety-filter').value;
            const list = (REPORT_DATA.top_occupants || []).filter(o => {{
                const matchText = (o.name || '').toLowerCase().includes(q) || (o.path || '').toLowerCase().includes(q);
                const matchSafety = sf === 'ALL' || (o.safety_action && o.safety_action.includes(sf));
                return matchText && matchSafety;
            }});

            document.getElementById('top100-tbody').innerHTML = list.length ? list.map((o, i) => {{
                const hasSubs = Array.isArray(o.sub_occupants) && o.sub_occupants.length > 0;
                const canDel = !String(o.safety_action || '').includes('Não Apagar');
                const subsHtml = hasSubs ? `
                    <div style="margin-top:0.4rem;">
                        <button type="button" class="btn-expand-sub" onclick="toggleSubfolders(${{i}})">
                            <span id="sub-toggle-icon-${{i}}">▶</span> Maiores Subpastas (${{o.sub_occupants.length}})
                        </button>
                        <div id="subfolders-${{i}}" class="subfolder-container" style="display:none;">
                            ${{o.sub_occupants.map(sub => {{
                                const parentBytes = o.size || 1;
                                const pct = Math.min(100, Math.max(4, Math.round((sub.size / parentBytes) * 100)));
                                return `<div class="subfolder-item">
                                    <span class="subfolder-name" title="${{escapeHtml(sub.path)}}">📁 ${{escapeHtml(sub.name)}}</span>
                                    <span class="subfolder-size" style="white-space:nowrap;">${{sub.size_formatted}}</span>
                                    <div class="subfolder-bar"><div class="subfolder-fill" style="width:${{pct}}%"></div></div>
                                    <div style="display:inline-flex;gap:4px;margin-left:6px;">
                                        <button class="btn-act" style="padding:0.15rem 0.4rem;font-size:0.7rem;" onclick="openDirectoryInspector('${{escapeAttr(sub.path)}}')" title="Explorar cirurgicamente">🔍</button>
                                        <button class="btn-act" style="padding:0.15rem 0.4rem;font-size:0.7rem;" onclick="revealPath('${{escapeAttr(sub.path)}}')">📂</button>
                                        <button class="btn-act danger" style="padding:0.15rem 0.4rem;font-size:0.7rem;" onclick="fileAction('${{escapeAttr(sub.path)}}', 'trash')">🗑️</button>
                                    </div>
                                </div>`;
                            }}).join('')}}
                        </div>
                    </div>` : '';

                return `<tr>
                    <td class="nowrap">${{i + 1}}</td>
                    <td><strong>${{escapeHtml(o.name)}}</strong></td>
                    <td class="nowrap">${{o.item_type || o.type}}</td>
                    <td class="nowrap"><strong>${{o.size_formatted}}</strong></td>
                    <td class="nowrap"><span class="badge ${{o.safety_badge}}">${{o.safety_action}}</span></td>
                    <td>
                        <div class="path-cell">${{escapeHtml(o.path)}}</div>
                        <small style="color:var(--text-muted)">${{escapeHtml(o.safety_recommendation || '')}}</small>
                        ${{subsHtml}}
                    </td>
                    <td class="nowrap">
                        ${{(o.item_type || o.type) === 'Pasta' ? `<button class="btn-act" onclick="openDirectoryInspector('${{escapeAttr(o.path)}}')">🔍 Explorar</button>` : ''}}
                        <button class="btn-act" onclick="revealPath('${{escapeAttr(o.path)}}')">📂 Abrir</button>
                        ${{canDel ? `
                            <button class="btn-act danger" onclick="fileAction('${{escapeAttr(o.path)}}', 'trash')">🗑️ Lixeira</button>
                            <button class="btn-act danger" onclick="fileAction('${{escapeAttr(o.path)}}', 'delete')">🔥 Excluir</button>
                        ` : '<span class="badge info" style="font-size:0.7rem;">Protegido</span>'}}
                    </td>
                </tr>`;
            }}).join('') : '<tr><td colspan="7">Nenhum item corresponde aos filtros selecionados.</td></tr>';
        }}

        function toggleSubfolders(idx) {{
            const el = document.getElementById(`subfolders-${{idx}}`);
            const icon = document.getElementById(`sub-toggle-icon-${{idx}}`);
            if (!el) return;
            if (el.style.display === 'none' || !el.style.display) {{
                el.style.display = 'block';
                if (icon) icon.textContent = '▼';
            }} else {{
                el.style.display = 'none';
                if (icon) icon.textContent = '▶';
            }}
        }}

        async function triggerReanalyze() {{
            const btn = document.getElementById('btn-reanalyze');
            if (!window.location.protocol.startsWith('http')) {{
                showToast('A reanálise em tempo real está disponível quando visualizado pelo servidor local (127.0.0.1).');
                return;
            }}
            try {{
                if (btn) {{
                    btn.disabled = true;
                    btn.textContent = '⏳ Reanalisando...';
                }}
                showToast('Reanalisando discos, partições e ocupantes do sistema...');
                const res = await fetch('/api/reanalyze', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}}
                }});
                const data = await res.json();
                if (data.status === 'ok' && data.report) {{
                    REPORT_DATA = data.report;
                    initDashboard();
                    showToast('✅ Sistema reanalisado com sucesso! Métricas e tabelas atualizadas.');
                }} else {{
                    showToast('Aviso: ' + (data.message || 'Não foi possível reanalisar.'));
                }}
            }} catch (e) {{
                showToast('Erro ao reanalisar: ' + e.message);
            }} finally {{
                if (btn) {{
                    btn.disabled = false;
                    btn.textContent = '🔄 Reanalisar Sistema';
                }}
            }}
        }}

        function renderTweaks() {{
            const list = REPORT_DATA.tweaks_executed || [];
            document.getElementById('tweaks-tbody').innerHTML = list.length ? list.map(t => `<tr>
                <td class="nowrap"><code>${{t.tweak_id}}</code></td>
                <td><strong>${{t.name}}</strong></td>
                <td>${{t.category}}</td>
                <td class="nowrap"><span class="badge ${{t.action === 'apply' ? 'success' : 'warning'}}">${{t.action.toUpperCase()}}</span></td>
                <td>${{t.message}}</td>
            </tr>`).join('') : '<tr><td colspan="5">Nenhum tweak selecionado nesta sessão.</td></tr>';
        }}

        async function revertLastSnapshot() {{
            const snapId = REPORT_DATA.snapshot_id || 'latest';
            if (window.location.protocol.startsWith('http')) {{
                try {{
                    const res = await fetch('/api/undo', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{snapshot_id: snapId, mode: 'real'}})
                    }});
                    const data = await res.json();
                    showToast(data.message || 'Otimizações revertidas com sucesso!');
                    return;
                }} catch (e) {{}}
            }}
            showToast(`Para reverter via terminal a qualquer momento, execute: python3 main.py --undo ${{snapId}}`);
        }}

        function renderCloudAndUpdates() {{
            const clouds = REPORT_DATA.cloud_diagnostics || [];
            document.getElementById('cloud-cards').innerHTML = clouds.map(c => `<div class="card">
                <div class="card-header">
                    <div class="card-title">☁️ ${{c.provider_name}}</div>
                    <span class="badge ${{c.is_consuming_heavy_space ? 'warning' : 'success'}}">${{c.consumed_formatted}} (${{c.file_count}} arquivos)</span>
                </div>
                <div class="path-cell" style="margin-bottom:0.75rem">${{c.path}}</div>
                ${{(c.recommendations || []).map(r => `<div style="margin-top:0.5rem;font-size:0.83rem;">
                    <strong>${{r.step}}:</strong> ${{r.action}}<br>
                    <small style="color:var(--text-muted)">${{r.effect}}</small>
                </div>`).join('')}}
            </div>`).join('');

            const upds = REPORT_DATA.outdated_apps || [];
            document.getElementById('updates-count-badge').textContent = `${{upds.length}} pacotes`;
            document.getElementById('updates-tbody').innerHTML = upds.length ? upds.map(u => `<tr>
                <td><strong>${{u.name}}</strong> <small style="color:var(--text-muted)">(${{u.source}})</small></td>
                <td class="nowrap">${{u.current_version}}</td>
                <td class="nowrap"><strong>${{u.latest_version}}</strong></td>
                <td class="nowrap"><span class="badge ${{u.risk_badge}}">${{u.risk_level}}</span></td>
                <td><code>${{u.upgrade_cmd}}</code></td>
                <td class="nowrap"><button class="btn-act success" onclick="upgradePackage('${{escapeAttr(u.app_id)}}')">⬆️ Atualizar</button></td>
            </tr>`).join('') : '<tr><td colspan="6">Nenhuma atualização pendente listada (ou verificação opt-in desativada).</td></tr>';
        }}

        async function fileAction(path, action) {{
            action = action || 'trash';
            const verb = action === 'trash' ? 'mover para a Lixeira' : 'excluir permanentemente';
            if (action === 'delete') {{
                if (!confirm(`Deseja realmente EXCLUIR DEFINITIVAMENTE?\\n${{path}}`)) return;
            }}
            if (!window.location.protocol.startsWith('http')) {{
                showToast(`Ação '${{action}}' simulada para: ${{path}}`);
                return;
            }}
            showToast(`Processando ${{verb}}...`);
            try {{
                const res = await fetch('/api/file-action', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{paths: [path], action: action, mode: 'real'}})
                }});
                const data = await res.json();
                if (data.success || data.status === 'ok' || data.status === 'trashed') {{
                    const affectedSet = new Set(data.affected_paths || [path]);
                    REPORT_DATA.clean_suggestions = (REPORT_DATA.clean_suggestions || []).filter(c => !affectedSet.has(c.path));
                    REPORT_DATA.top_occupants = (REPORT_DATA.top_occupants || []).filter(o => !affectedSet.has(o.path));
                    if (data.total_freed_formatted) document.getElementById('stat-freed').textContent = data.total_freed_formatted;
                    if (data.potential_extra_formatted) document.getElementById('stat-potential').textContent = data.potential_extra_formatted;
                    renderOrphans();
                    renderTopOccupants();
                    showToast(`Sucesso! ${{data.bytes_freed_formatted || '0 B'}} liberados (${{verb}}).`);
                }} else {{
                    showToast(data.message || data.error || 'Não foi possível completar a ação.');
                }}
            }} catch (e) {{
                showToast('Erro de comunicação: ' + e.message);
            }}
        }}

        async function revealPath(path) {{
            if (!window.location.protocol.startsWith('http')) {{
                showToast(`Caminho destacado: ${{path}}`);
                return;
            }}
            try {{
                const res = await fetch('/api/reveal-path', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{path: path}})
                }});
                const data = await res.json();
                if (data.status === 'ok') {{
                    showToast(`Local aberto no gerenciador de arquivos: ${{path}}`);
                }} else {{
                    showToast(data.message || 'Falha ao abrir pasta no gerenciador.');
                }}
            }} catch (e) {{
                showToast('Erro ao abrir local: ' + e.message);
            }}
        }}

        async function executeRule(ruleId) {{
            if (!window.location.protocol.startsWith('http')) {{
                showToast(`Regra '${{ruleId}}' simulada.`);
                return;
            }}
            showToast(`Executando limpeza para a regra '${{ruleId}}'...`);
            try {{
                const res = await fetch('/api/execute-rule', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{rule_id: ruleId, mode: 'real'}})
                }});
                const data = await res.json();
                if (data.status === 'ok') {{
                    if (data.total_freed_formatted) document.getElementById('stat-freed').textContent = data.total_freed_formatted;
                    if (data.entry && REPORT_DATA.autonomous_cleanups) {{
                        const idx = REPORT_DATA.autonomous_cleanups.findIndex(c => c.id === ruleId);
                        if (idx >= 0) REPORT_DATA.autonomous_cleanups[idx] = data.entry;
                        else REPORT_DATA.autonomous_cleanups.push(data.entry);
                        initDashboard();
                    }}
                    showToast(`Regra executada com sucesso! Liberados: ${{data.entry ? data.entry.bytes_freed_formatted : ''}}`);
                }} else {{
                    showToast(data.message || 'Erro ao executar regra.');
                }}
            }} catch (e) {{
                showToast('Erro de comunicação: ' + e.message);
            }}
        }}

        async function refreshLiveHealth() {{
            const btn = document.getElementById('btn-live-health');
            if (!window.location.protocol.startsWith('http')) {{
                showToast('Atualização em tempo real disponível via servidor local 127.0.0.1.');
                return;
            }}
            if (btn) {{ btn.disabled = true; btn.textContent = '⏳ Atualizando...'; }}
            showToast('Coletando telemetria nativa instantânea...');
            try {{
                const res = await fetch(`/api/live-health?os=${{REPORT_DATA.os_platform || ''}}`);
                const data = await res.json();
                if (data.status === 'ok' && data.hardware_health) {{
                    REPORT_DATA.hardware_health = data.hardware_health;
                    renderHardwareAndStorage();
                    showToast('✅ Telemetria de hardware e longevidade atualizadas em tempo real!');
                }} else {{
                    showToast(data.message || 'Falha ao atualizar telemetria.');
                }}
            }} catch (e) {{
                showToast('Erro ao atualizar telemetria: ' + e.message);
            }} finally {{
                if (btn) {{ btn.disabled = false; btn.textContent = '🔄 Atualizar Telemetria em Tempo Real'; }}
            }}
        }}

        async function removeStartupItem(path) {{
            if (!confirm(`Deseja remover este agente de inicialização?\\nUm backup prévio será salvo em outputs/snapshots/.\\n${{path}}`)) return;
            if (!window.location.protocol.startsWith('http')) {{
                showToast(`Remoção simulada do agente: ${{path}}`);
                return;
            }}
            try {{
                const res = await fetch('/api/startup-action', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{path: path, action: 'remove'}})
                }});
                const data = await res.json();
                if (data.status === 'ok') {{
                    if (REPORT_DATA.hardware_health && REPORT_DATA.hardware_health.startup_items) {{
                        REPORT_DATA.hardware_health.startup_items = REPORT_DATA.hardware_health.startup_items.filter(s => s.path !== path);
                        renderHardwareAndStorage();
                    }}
                    showToast('✅ Agente de inicialização removido com backup!');
                }} else {{
                    showToast(data.message || 'Falha ao remover agente.');
                }}
            }} catch (e) {{
                showToast('Erro de comunicação: ' + e.message);
            }}
        }}

        async function terminateProcess(pid) {{
            if (!confirm(`Deseja realmente encerrar o processo PID ${{pid}}?`)) return;
            if (!window.location.protocol.startsWith('http')) {{
                showToast(`Encerramento simulado do processo PID ${{pid}}.`);
                return;
            }}
            try {{
                const res = await fetch('/api/process-action', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{pid: pid, action: 'terminate'}})
                }});
                const data = await res.json();
                if (data.status === 'ok') {{
                    if (REPORT_DATA.hardware_health && REPORT_DATA.hardware_health.top_processes) {{
                        REPORT_DATA.hardware_health.top_processes = REPORT_DATA.hardware_health.top_processes.filter(p => p.pid !== pid);
                        renderHardwareAndStorage();
                    }}
                    showToast(`Processo PID ${{pid}} encerrado.`);
                }} else {{
                    showToast(data.message || 'Não foi possível encerrar o processo.');
                }}
            }} catch (e) {{
                showToast('Erro de comunicação: ' + e.message);
            }}
        }}

        async function upgradePackage(packageId) {{
            showToast(`Executando ação para pacote: ${{packageId}}...`);
            if (!window.location.protocol.startsWith('http')) {{
                showToast(`Atualização simulada para: ${{packageId}}`);
                return;
            }}
            try {{
                const res = await fetch('/api/upgrade-packages', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{package_id: packageId}})
                }});
                const data = await res.json();
                if (data.status === 'ok') {{
                    showToast(`✅ ${{data.message || 'Operação de pacotes concluída com sucesso!'}}`);
                }} else {{
                    showToast(`Aviso: ${{data.message || data.output || 'Falha ao atualizar pacote'}}`);
                }}
            }} catch (e) {{
                showToast('Erro ao atualizar: ' + e.message);
            }}
        }}

        let currentInspectorPath = null;
        let parentInspectorPath = null;

        function renderStorageXRay() {{
            const xray = REPORT_DATA.storage_xray;
            if (!xray) return;

            setText('xray-doc-total', xray.documents_total_formatted || '0.00 B');
            setText('xray-doc-visible', xray.documents_visible_formatted || '0.00 B');
            setText('xray-doc-hidden', xray.documents_hidden_dotfiles_formatted || '0.00 B');
            setText('xray-doc-rebuildable', xray.documents_rebuildable_artifacts_formatted || '0.00 B');
            setText('xray-sys-total', xray.system_data_tracked_formatted || '0.00 B');
            setText('xray-recoverable-total', REPORT_DATA.potential_extra_bytes_formatted || '0.00 B');

            const grid = document.getElementById('xray-categories-grid');
            if (!grid) return;

            const cats = xray.categories || [];
            grid.innerHTML = cats.map(cat => {{
                const isDoc = cat.os_equivalent && cat.os_equivalent.includes('Documentos');
                const badgeClass = isDoc ? 'purple' : 'info';
                const items = cat.top_items || [];

                const itemsHtml = items.length ? items.map(it => `
                    <div class="xray-item-row">
                        <span class="xray-item-name" title="${{escapeHtml(it.path)}}">
                            ${{it.name.startsWith('.') ? '👻 ' : '📁 '}}<strong>${{escapeHtml(it.name)}}</strong>
                        </span>
                        <div style="display:inline-flex;align-items:center;gap:6px;white-space:nowrap;">
                            <strong style="font-size:0.8rem;white-space:nowrap;">${{escapeHtml(it.size_formatted)}}</strong>
                            <button class="btn-act" onclick="openDirectoryInspector('${{escapeAttr(it.path)}}')">🔍 Explorar</button>
                            <button class="btn-act" onclick="revealPath('${{escapeAttr(it.path)}}')">📂 Abrir</button>
                            ${{it.can_delete ? `<button class="btn-act danger" onclick="fileAction('${{escapeAttr(it.path)}}', 'trash')">🗑️</button>` : ''}}
                        </div>
                    </div>
                `).join('') : '<div style="font-size:0.8rem;color:var(--text-muted);padding:0.4rem 0;">Nenhum diretório significativo encontrado nesta categoria.</div>';

                return `
                    <div class="xray-category-card">
                        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:0.5rem;">
                            <div style="min-width:0;">
                                <div style="font-weight:700;font-size:0.95rem;color:var(--text-main);">${{escapeHtml(cat.title)}}</div>
                                <span class="badge ${{badgeClass}}" style="margin-top:0.25rem;">${{escapeHtml(cat.os_equivalent)}}</span>
                            </div>
                            <div style="font-size:1.2rem;font-weight:700;color:var(--accent-primary);white-space:nowrap;">
                                ${{escapeHtml(cat.total_formatted)}}
                            </div>
                        </div>
                        <p style="font-size:0.78rem;color:var(--text-muted);margin:0;">${{escapeHtml(cat.description)}}</p>
                        <div style="font-size:0.75rem;color:var(--warning-color);background:rgba(245,158,11,0.08);padding:0.4rem 0.6rem;border-radius:6px;border-left:2px solid var(--warning-color);">
                            💡 <strong>Por que o macOS oculta/acumula:</strong> ${{escapeHtml(cat.why_os_hides_it)}}
                        </div>
                        <div style="border-top:1px solid rgba(51,65,85,0.4);margin-top:0.35rem;padding-top:0.35rem;">
                            <div style="font-size:0.74rem;color:var(--text-muted);text-transform:uppercase;font-weight:600;margin-bottom:0.25rem;">Maiores Diretórios:</div>
                            ${{itemsHtml}}
                        </div>
                    </div>
                `;
            }}).join('');
        }}

        function openDirectoryInspector(dirPath) {{
            const modal = document.getElementById('inspector-modal');
            if (modal) {{
                modal.style.display = 'flex';
                inspectDirectory(dirPath);
            }}
        }}

        function closeDirectoryInspector() {{
            const modal = document.getElementById('inspector-modal');
            if (modal) modal.style.display = 'none';
        }}

        function inspectorGoUp() {{
            if (parentInspectorPath) {{
                inspectDirectory(parentInspectorPath);
            }}
        }}

        async function inspectDirectory(dirPath) {{
            currentInspectorPath = dirPath;
            const loading = document.getElementById('inspector-loading');
            const tbody = document.getElementById('inspector-tbody');
            const breadcrumbs = document.getElementById('inspector-breadcrumbs');
            const badge = document.getElementById('inspector-summary-badge');
            const btnUp = document.getElementById('btn-inspector-up');

            if (loading) loading.style.display = 'block';
            if (tbody) tbody.innerHTML = '';

            const normalizedPath = dirPath.split('\\\\').join('/');
            const segments = normalizedPath.split('/').filter(Boolean);
            let accum = dirPath.startsWith('/') ? '/' : '';
            const breadcrumbLinks = [];
            if (dirPath.startsWith('/')) {{
                breadcrumbLinks.push(`<span class="breadcrumb-segment" onclick="inspectDirectory('/')">/</span>`);
            }}
            segments.forEach((seg, sIdx) => {{
                accum = accum.endsWith('/') ? accum + seg : accum + '/' + seg;
                const pathForSeg = accum;
                if (sIdx === segments.length - 1) {{
                    breadcrumbLinks.push(`<strong>${{escapeHtml(seg)}}</strong>`);
                }} else {{
                    breadcrumbLinks.push(`<span class="breadcrumb-segment" onclick="inspectDirectory('${{escapeAttr(pathForSeg)}}')">${{escapeHtml(seg)}}</span>`);
                }}
            }});
            if (breadcrumbs) breadcrumbs.innerHTML = breadcrumbLinks.join(' / ');

            if (!window.location.protocol.startsWith('http')) {{
                if (loading) loading.style.display = 'none';
                if (tbody) tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:var(--text-muted);">A inspeção interativa nível a nível está disponível rodando via servidor local (127.0.0.1). Diretório selecionado: <code>${{escapeHtml(dirPath)}}</code></td></tr>`;
                return;
            }}

            try {{
                const res = await fetch('/api/inspect-directory', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{path: dirPath, max_items: 30}})
                }});
                const data = await res.json();
                if (loading) loading.style.display = 'none';

                if (data.status === 'ok') {{
                    parentInspectorPath = data.parent_path || null;
                    if (btnUp) btnUp.disabled = !parentInspectorPath;
                    if (badge) badge.textContent = `${{data.items_count}} itens (${{data.total_formatted}})`;

                    const items = data.items || [];
                    if (!items.length) {{
                        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);">Diretório vazio.</td></tr>';
                        return;
                    }}

                    tbody.innerHTML = items.map(item => {{
                        const isDir = item.item_type === 'Pasta';
                        const icon = isDir ? '📁' : '📄';
                        const pct = Math.min(100, Math.max(3, Math.round(item.percent_of_parent || 0)));
                        const barColor = item.safety_badge === 'danger' ? 'var(--danger-color)' : (item.safety_badge === 'warning' ? 'var(--warning-color)' : 'var(--accent-primary)');

                        return `
                            <tr>
                                <td>
                                    <div style="display:flex;align-items:center;gap:6px;min-width:0;">
                                        <span>${{icon}}</span>
                                        <div style="min-width:0;">
                                            <div style="font-weight:600;font-size:0.84rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="${{escapeHtml(item.name)}}">${{escapeHtml(item.name)}}</div>
                                            <div class="path-cell" style="font-size:0.72rem;">${{escapeHtml(item.path)}}</div>
                                        </div>
                                    </div>
                                </td>
                                <td class="nowrap">${{escapeHtml(item.item_type)}}</td>
                                <td class="nowrap"><strong>${{escapeHtml(item.size_formatted)}}</strong></td>
                                <td class="nowrap" style="min-width:110px;">
                                    <div style="font-size:0.76rem;margin-bottom:2px;">${{item.percent_of_parent}}%</div>
                                    <div class="progress-bar-bg" style="height:5px;width:90px;"><div class="progress-bar-fill" style="width:${{pct}}%;background:${{barColor}}"></div></div>
                                </td>
                                <td class="nowrap"><span class="badge ${{item.safety_badge}}">${{escapeHtml(item.safety_action)}}</span></td>
                                <td class="nowrap" style="text-align:right;">
                                    ${{isDir ? `<button class="btn-act" onclick="inspectDirectory('${{escapeAttr(item.path)}}')">🔍 Entrar</button>` : ''}}
                                    <button class="btn-act" onclick="revealPath('${{escapeAttr(item.path)}}')">📂 Abrir</button>
                                    ${{item.can_delete ? `
                                        <button class="btn-act danger" onclick="inspectorFileAction('${{escapeAttr(item.path)}}', 'trash')">🗑️</button>
                                        <button class="btn-act danger" onclick="inspectorFileAction('${{escapeAttr(item.path)}}', 'delete')">🔥</button>
                                    ` : ''}}
                                </td>
                            </tr>
                        `;
                    }}).join('');
                }} else {{
                    if (tbody) tbody.innerHTML = `<tr><td colspan="6" style="color:var(--danger-color);text-align:center;">Erro: ${{escapeHtml(data.message || 'Falha ao inspecionar diretório.')}}</td></tr>`;
                }}
            }} catch (e) {{
                if (loading) loading.style.display = 'none';
                if (tbody) tbody.innerHTML = `<tr><td colspan="6" style="color:var(--danger-color);text-align:center;">Erro de comunicação: ${{escapeHtml(e.message)}}</td></tr>`;
            }}
        }}

        async function inspectorFileAction(path, action) {{
            await fileAction(path, action);
            if (currentInspectorPath) {{
                inspectDirectory(currentInspectorPath);
            }}
        }}

        function renderHardwareAndStorage() {{
            const hw = REPORT_DATA.hardware_health || {{}};
            const alerts = hw.critical_alerts || [];
            const alertsContainer = document.getElementById('hw-alerts-container');
            if (alertsContainer) {{
                if (alerts.length > 0) {{
                    alertsContainer.innerHTML = `
                        <div style="background:rgba(239,68,68,0.18);border:1px solid var(--danger-color);border-radius:10px;padding:1rem;margin-bottom:1.25rem;">
                            <strong style="color:var(--danger-color);font-size:0.95rem;">⚠️ Alertas Críticos de Integridade Física / Operacional:</strong>
                            <ul style="margin-top:0.4rem;padding-left:1.2rem;font-size:0.85rem;color:var(--text-main);">
                                ${{alerts.map(a => `<li style="margin-bottom:0.25rem;">${{escapeHtml(a)}}</li>`).join('')}}
                            </ul>
                        </div>
                    `;
                }} else {{
                    alertsContainer.innerHTML = '';
                }}
            }}

            // 0. Longevity Health Score (RF-17)
            const longRep = hw.longevity_report || {{}};
            const scoreNumEl = document.getElementById('longevity-score-num');
            if (scoreNumEl) {{
                const score = longRep.total_score !== undefined ? longRep.total_score : 85;
                scoreNumEl.textContent = `${{score}}/100`;
                const gradeEl = document.getElementById('longevity-grade-badge');
                if (gradeEl) {{
                    gradeEl.textContent = longRep.grade_label || 'Saudável';
                    gradeEl.className = 'badge ' + (score >= 90 ? 'success' : (score >= 75 ? 'info' : (score >= 55 ? 'warning' : 'danger')));
                }}
                // Pilares
                const sScore = longRep.storage_score !== undefined ? longRep.storage_score : 30;
                setText('pilar-storage-score', `${{sScore}} / 35`);
                const sBar = document.getElementById('pilar-storage-bar');
                if (sBar) sBar.style.width = `${{Math.round((sScore / 35) * 100)}}%`;

                const mScore = longRep.memory_score !== undefined ? longRep.memory_score : 22;
                setText('pilar-memory-score', `${{mScore}} / 25`);
                const mBar = document.getElementById('pilar-memory-bar');
                if (mBar) mBar.style.width = `${{Math.round((mScore / 25) * 100)}}%`;

                const hScore = longRep.hygiene_score !== undefined ? longRep.hygiene_score : 18;
                setText('pilar-hygiene-score', `${{hScore}} / 20`);
                const hBar = document.getElementById('pilar-hygiene-bar');
                if (hBar) hBar.style.width = `${{Math.round((hScore / 20) * 100)}}%`;

                const tScore = longRep.thermal_battery_score !== undefined ? longRep.thermal_battery_score : 18;
                setText('pilar-thermal-score', `${{tScore}} / 20`);
                const tBar = document.getElementById('pilar-thermal-bar');
                if (tBar) tBar.style.width = `${{Math.round((tScore / 20) * 100)}}%`;
            }}

            // Recomendações de Longevidade
            const recs = longRep.recommendations || [];
            const recCountEl = document.getElementById('longevity-rec-count');
            if (recCountEl) recCountEl.textContent = `${{recs.length}} Recomendação(ões)`;
            const recGridEl = document.getElementById('longevity-rec-grid');
            if (recGridEl) {{
                recGridEl.innerHTML = recs.length ? recs.map(r => {{
                    const sevClass = r.severity === 'critical' ? 'danger' : (r.severity === 'warning' ? 'warning' : 'info');
                    let btnAction = '';
                    if (r.action_type === 'remove_broken_startup') {{
                        btnAction = `<button class="btn-act danger" onclick="removeStartupItem('${{escapeAttr((r.action_payload && r.action_payload.paths && r.action_payload.paths[0]) || '')}}')">${{r.action_label || 'Remover'}}</button>`;
                    }} else if (r.action_type === 'clean_orphans') {{
                        btnAction = `<button class="btn-act success" onclick="switchTab('tab-orphans', document.querySelectorAll('.tab-btn')[3])">${{r.action_label || 'Ir para Órfãos'}}</button>`;
                    }} else if (r.action_type === 'thin_snapshots') {{
                        btnAction = `<button class="btn-act warning" onclick="optimizeDisk('/', false, 0)">${{r.action_label || 'Expurgar'}}</button>`;
                    }} else if (r.action_type === 'terminate_zombies') {{
                        btnAction = `<button class="btn-act danger" onclick="document.getElementById('processes-tbody').scrollIntoView({{behavior:'smooth'}})">${{r.action_label || 'Ver Processos'}}</button>`;
                    }}
                    return `
                        <div class="hw-subcard" style="margin-top:0;display:flex;flex-direction:column;justify-content:space-between;">
                            <div>
                                <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:0.5rem;margin-bottom:0.4rem;">
                                    <strong style="font-size:0.92rem;color:var(--text-main);">${{escapeHtml(r.title)}}</strong>
                                    <span class="badge ${{sevClass}}">${{r.severity.toUpperCase()}}</span>
                                </div>
                                <p style="font-size:0.83rem;color:var(--text-muted);margin-bottom:0.5rem;"><strong>O Que Fazer:</strong> ${{escapeHtml(r.what_to_do)}}</p>
                                <p style="font-size:0.78rem;color:rgba(148,163,184,0.85);margin-bottom:0.6rem;background:rgba(15,23,42,0.6);padding:0.4rem 0.6rem;border-radius:6px;">
                                    🔬 <em>Impacto Físico no Hardware:</em> ${{escapeHtml(r.longevity_impact)}}
                                </p>
                            </div>
                            <div style="margin-top:0.4rem;display:flex;justify-content:flex-end;">
                                ${{btnAction}}
                            </div>
                        </div>
                    `;
                }}).join('') : '<p style="font-size:0.85rem;color:var(--text-muted)">Nenhuma ação corretiva necessária. Todos os subsistemas operando em condições ideais.</p>';
            }}

            // 1. Discos & APFS
            const disks = hw.disks || [];
            const disksCountEl = document.getElementById('hw-disks-count');
            if (disksCountEl) disksCountEl.textContent = `${{disks.length}} Unidade(s)`;
            const disksListEl = document.getElementById('hw-disks-list');
            if (disksListEl) {{
                disksListEl.innerHTML = disks.length ? disks.map(d => {{
                    const isSsd = d.is_ssd;
                    const mediaBadgeClass = d.is_nvme ? 'badge info' : (isSsd ? 'badge success' : 'badge warning');
                    const smartClass = (d.smart_status === 'Verified' || d.smart_status === 'Healthy') ? 'badge success' : 'badge danger';
                    return `
                        <div class="hw-subcard">
                            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;gap:0.5rem;">
                                <strong style="font-size:0.92rem;min-width:0;overflow:hidden;text-overflow:ellipsis;">${{escapeHtml(d.name)}}</strong>
                                <span class="${{mediaBadgeClass}}">${{escapeHtml(d.media_type)}}</span>
                            </div>
                            <div class="hw-metric-row">
                                <span style="color:var(--text-muted)">Barramento / Protocolo:</span>
                                <span class="hw-metric-val">${{escapeHtml(d.bus_type)}}</span>
                            </div>
                            <div class="hw-metric-row">
                                <span style="color:var(--text-muted)">Status S.M.A.R.T.:</span>
                                <span class="${{smartClass}}">${{escapeHtml(d.smart_status)}}</span>
                            </div>
                            <div class="hw-metric-row">
                                <span style="color:var(--text-muted)">Suporte a TRIM:</span>
                                <span class="hw-metric-val">${{d.trim_supported ? '✅ Ativo / Suportado' : '❌ Inativo / N/A'}}</span>
                            </div>
                            ${{d.purgeable_bytes ? `
                                <div class="hw-metric-row">
                                    <span style="color:var(--text-muted)">Espaço Purgável (macOS APFS):</span>
                                    <span class="hw-metric-val" style="color:var(--accent-primary)">${{escapeHtml(d.purgeable_formatted || '0 B')}}</span>
                                </div>
                            ` : ''}}
                            ${{d.apfs_snapshots_count !== undefined && d.apfs_snapshots_count !== null ? `
                                <div class="hw-metric-row">
                                    <span style="color:var(--text-muted)">Snapshots Locais APFS:</span>
                                    <span class="hw-metric-val">${{d.apfs_snapshots_count}} snapshot(s)</span>
                                </div>
                            ` : ''}}
                            <div class="hw-metric-row">
                                <span style="color:var(--text-muted)">Ação Segura Recomendada:</span>
                                <span class="hw-metric-val" style="color:var(--accent-primary)">${{escapeHtml(d.recommended_action)}}</span>
                            </div>
                            ${{d.total_bytes ? `
                                <div class="hw-metric-row">
                                    <span style="color:var(--text-muted)">Capacidade Total:</span>
                                    <span class="hw-metric-val">${{escapeHtml(d.total_formatted || '')}}</span>
                                </div>
                                <div class="hw-metric-row">
                                    <span style="color:var(--text-muted)">Ocupação Efetiva (Padrão SO):</span>
                                    <span class="hw-metric-val">${{escapeHtml(d.used_formatted || '')}} / ${{escapeHtml(d.total_formatted || '')}} (Livre: ${{escapeHtml(d.free_formatted || '')}})</span>
                                </div>
                                ${{d.total_binary_formatted ? `
                                    <div class="hw-metric-row">
                                        <span style="color:var(--text-muted)">Equivalente Binário (IEC 1024³):</span>
                                        <span class="hw-metric-val">${{escapeHtml(d.used_binary_formatted || '')}} / ${{escapeHtml(d.total_binary_formatted || '')}}</span>
                                    </div>
                                ` : ''}}
                            ` : ''}}
                        </div>
                    `;
                }}).join('') : '<p style="font-size:0.85rem;color:var(--text-muted)">Nenhuma unidade de disco mapeada.</p>';
            }}

            // 2. RAM & Swap
            const mem = hw.memory || {{}};
            const ramBadgeEl = document.getElementById('hw-ram-pressure-badge');
            if (ramBadgeEl) {{
                const pLevel = mem.pressure_level || 'Normal';
                ramBadgeEl.textContent = `Pressão: ${{pLevel}}`;
                ramBadgeEl.className = 'badge ' + (pLevel === 'Critical' ? 'danger' : (pLevel === 'Warning' ? 'warning' : 'success'));
            }}
            const ramContentEl = document.getElementById('hw-ram-content');
            if (ramContentEl) {{
                const load = mem.load_percentage || 0;
                const barColor = load >= 88 ? 'var(--danger-color)' : (load >= 75 ? 'var(--warning-color)' : 'var(--success-color)');
                ramContentEl.innerHTML = `
                    <div style="margin-bottom:0.75rem;">
                        <div style="display:flex;justify-content:space-between;font-size:0.85rem;white-space:nowrap;margin-bottom:0.25rem;">
                            <span>Carga Física de RAM:</span>
                            <strong>${{load}}%</strong>
                        </div>
                        <div class="progress-bar-bg" style="margin:0.25rem 0;">
                            <div class="progress-bar-fill" style="width:${{Math.min(load, 100)}}%;background:${{barColor}};"></div>
                        </div>
                    </div>
                    <div class="hw-metric-row">
                        <span style="color:var(--text-muted)">RAM Física Usada / Total:</span>
                        <span class="hw-metric-val">${{escapeHtml(mem.used_formatted || '0 B')}} de ${{escapeHtml(mem.total_formatted || '0 B')}}</span>
                    </div>
                    <div class="hw-metric-row">
                        <span style="color:var(--text-muted)">RAM Livre / Disponível:</span>
                        <span class="hw-metric-val" style="color:var(--success-color)">${{escapeHtml(mem.free_formatted || '0 B')}}</span>
                    </div>
                    ${{mem.wired_bytes ? `
                        <div class="hw-metric-row">
                            <span style="color:var(--text-muted)">Wired Memory (Kernel Darwin):</span>
                            <span class="hw-metric-val">${{escapeHtml(mem.wired_formatted || '0 B')}}</span>
                        </div>
                    ` : ''}}
                    ${{mem.compressed_bytes ? `
                        <div class="hw-metric-row">
                            <span style="color:var(--text-muted)">Memória Comprimida (Compressor):</span>
                            <span class="hw-metric-val">${{escapeHtml(mem.compressed_formatted || '0 B')}}</span>
                        </div>
                    ` : ''}}
                    <div class="hw-metric-row">
                        <span style="color:var(--text-muted)">Arquivo de Paginação (Swap):</span>
                        <span class="hw-metric-val">${{escapeHtml(mem.swap_used_formatted || '0 B')}} de ${{escapeHtml(mem.swap_total_formatted || '0 B')}}</span>
                    </div>
                    ${{mem.page_size_bytes ? `
                        <div class="hw-metric-row">
                            <span style="color:var(--text-muted)">Tamanho de Página (hw.pagesize):</span>
                            <span class="hw-metric-val">${{mem.page_size_bytes === 16384 ? '16 KB (Apple Silicon)' : '4 KB'}}</span>
                        </div>
                    ` : ''}}
                    ${{mem.swap_thrashing_detected ? `
                        <div style="margin-top:0.6rem;padding:0.45rem 0.75rem;background:rgba(239,68,68,0.15);border:1px solid var(--danger-color);border-radius:8px;font-size:0.8rem;color:#fca5a5;">
                            ⚠️ <strong>Swap Thrashing Detectado:</strong> Pressão extrema de memória causando alta taxa de I/O em disco.
                        </div>
                    ` : ''}}
                `;
            }}

            // 3. GPUs
            const gpus = hw.gpus || [];
            const gpuCountEl = document.getElementById('hw-gpu-count');
            if (gpuCountEl) gpuCountEl.textContent = `${{gpus.length}} Adaptador(es)`;
            const gpuListEl = document.getElementById('hw-gpu-list');
            if (gpuListEl) {{
                gpuListEl.innerHTML = gpus.length ? gpus.map(g => `
                    <div class="hw-subcard">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;gap:0.5rem;">
                            <strong style="font-size:0.92rem;min-width:0;overflow:hidden;text-overflow:ellipsis;">${{escapeHtml(g.name)}}</strong>
                            <span class="badge purple">${{escapeHtml(g.vendor)}}</span>
                        </div>
                        <div class="hw-metric-row">
                            <span style="color:var(--text-muted)">Memória de Vídeo (VRAM):</span>
                            <span class="hw-metric-val">${{escapeHtml(g.vram_formatted)}}</span>
                        </div>
                        <div class="hw-metric-row">
                            <span style="color:var(--text-muted)">Driver / Subsistema:</span>
                            <span class="hw-metric-val">${{escapeHtml(g.driver_version)}}</span>
                        </div>
                        <div class="hw-metric-row">
                            <span style="color:var(--text-muted)">Status Operacional:</span>
                            <span class="badge success">${{escapeHtml(g.status)}}</span>
                        </div>
                    </div>
                `).join('') : '<p style="font-size:0.85rem;color:var(--text-muted)">Nenhuma GPU reportada.</p>';
            }}

            // 4. Bateria
            const batt = hw.battery || {{}};
            const battBadgeEl = document.getElementById('hw-battery-badge');
            if (battBadgeEl) {{
                if (batt.has_battery) {{
                    const cond = batt.condition || 'Normal';
                    battBadgeEl.textContent = cond;
                    battBadgeEl.className = 'badge ' + (cond.toLowerCase().includes('service') ? 'danger' : 'success');
                }} else {{
                    battBadgeEl.textContent = 'Alimentação Direta AC';
                    battBadgeEl.className = 'badge info';
                }}
            }}
            const battContentEl = document.getElementById('hw-battery-content');
            if (battContentEl) {{
                if (batt.has_battery) {{
                    battContentEl.innerHTML = `
                        <div class="hw-metric-row">
                            <span style="color:var(--text-muted)">Condição da Bateria:</span>
                            <span class="hw-metric-val">${{escapeHtml(batt.condition)}}</span>
                        </div>
                        <div class="hw-metric-row">
                            <span style="color:var(--text-muted)">Ciclos de Carga:</span>
                            <span class="hw-metric-val">${{batt.cycle_count !== null && batt.cycle_count !== undefined ? batt.cycle_count + ' ciclos' : 'Não reportado'}}</span>
                        </div>
                        <div class="hw-metric-row">
                            <span style="color:var(--text-muted)">Saúde / Capacidade Máxima:</span>
                            <span class="hw-metric-val" style="color:var(--success-color)">${{batt.health_percentage !== null && batt.health_percentage !== undefined ? batt.health_percentage + '%' : 'Adequada'}}</span>
                        </div>
                        ${{batt.design_capacity_mah ? `
                            <div class="hw-metric-row">
                                <span style="color:var(--text-muted)">Capacidade Projeto / Atual:</span>
                                <span class="hw-metric-val">${{batt.max_capacity_mah || '--'}} mAh / ${{batt.design_capacity_mah}} mAh</span>
                            </div>
                        ` : ''}}
                        ${{batt.temperature_celsius !== null && batt.temperature_celsius !== undefined ? `
                            <div class="hw-metric-row">
                                <span style="color:var(--text-muted)">Temperatura Térmica:</span>
                                <span class="hw-metric-val" style="color:${{batt.temperature_celsius > 38 ? 'var(--warning-color)' : 'var(--text-main)'}}">${{batt.temperature_celsius}} °C</span>
                            </div>
                        ` : ''}}
                        <div class="hw-metric-row">
                            <span style="color:var(--text-muted)">Estado de Carregamento:</span>
                            <span class="hw-metric-val">${{batt.is_charging ? '⚡ Carregando' : '🔋 Operando na Bateria'}}</span>
                        </div>
                    `;
                }} else {{
                    battContentEl.innerHTML = `
                        <p style="font-size:0.85rem;color:var(--text-muted);margin-top:0.35rem;">
                            🖥️ Computador operando via fonte contínua AC (Desktop Mac / PC Torre). Diagnóstico de ciclos e desgaste de bateria de laptop não se aplica.
                        </p>
                    `;
                }}
            }}

            // 5. Tabela de Startup Items (RF-17)
            const sItems = hw.startup_items || [];
            const startupBadge = document.getElementById('startup-count-badge');
            if (startupBadge) startupBadge.textContent = `${{sItems.length}} Agente(s)`;
            const startupTbody = document.getElementById('startup-tbody');
            if (startupTbody) {{
                startupTbody.innerHTML = sItems.length ? sItems.map(s => `
                    <tr>
                        <td class="nowrap"><strong>${{escapeHtml(s.name)}}</strong></td>
                        <td class="nowrap"><span class="badge info">${{escapeHtml(s.scope)}}</span></td>
                        <td class="nowrap"><span class="badge ${{s.is_orphan ? 'danger' : 'success'}}">${{escapeHtml(s.status_label)}}</span></td>
                        <td>
                            <div class="path-cell">${{escapeHtml(s.program_target || s.path)}}</div>
                            <small style="color:var(--text-muted);">${{escapeHtml(s.recommendation)}}</small>
                        </td>
                        <td class="nowrap">
                            ${{s.is_orphan ? `
                                <button class="btn-act danger" onclick="removeStartupItem('${{escapeAttr(s.path)}}')">🗑️ Remover (c/ Backup)</button>
                            ` : '<span class="badge success" style="font-size:0.7rem;">Íntegro</span>'}}
                        </td>
                    </tr>
                `).join('') : '<tr><td colspan="5">Nenhum agente de inicialização ou persistência mapeado.</td></tr>';
            }}

            // 6. Tabela de Top Processos & Zumbis (RF-17)
            const procs = hw.top_processes || [];
            const procBadge = document.getElementById('processes-count-badge');
            if (procBadge) procBadge.textContent = `${{procs.length}} Processos`;
            const procTbody = document.getElementById('processes-tbody');
            if (procTbody) {{
                procTbody.innerHTML = procs.length ? procs.map(p => `
                    <tr>
                        <td class="nowrap"><code>${{p.pid}}</code></td>
                        <td><strong>${{escapeHtml(p.name)}}</strong></td>
                        <td class="nowrap">${{p.cpu_percent}}%</td>
                        <td class="nowrap"><strong>${{p.memory_formatted || (p.memory_mb + ' MB')}}</strong></td>
                        <td class="nowrap"><span class="badge ${{p.is_zombie ? 'danger' : 'info'}}">${{escapeHtml(p.state)}}</span></td>
                        <td class="nowrap">
                            ${{p.can_terminate ? `
                                <button class="btn-act danger" onclick="terminateProcess(${{p.pid}})">🛑 Encerrar</button>
                            ` : '<span class="badge info" style="font-size:0.7rem;">Vital do SO</span>'}}
                        </td>
                    </tr>
                `).join('') : '<tr><td colspan="6">Nenhum processo pesado registrado.</td></tr>';
            }}

            // 7. Tabela de Otimização de Storage (RF-14)
            const optTbody = document.getElementById('hw-opt-tbody');
            if (optTbody) {{
                const partitions = REPORT_DATA.partitions || [];
                optTbody.innerHTML = partitions.length ? partitions.map((p, idx) => {{
                    const driveName = p.drive_letter;
                    const fs = (p.filesystem || '').toUpperCase();
                    const isMacApfs = fs.includes('APFS') || REPORT_DATA.os_platform === 'macos';
                    const isHdd = !isMacApfs && (p.role || '').toLowerCase().includes('hdd');
                    const mediaLabel = isMacApfs ? 'APFS SSD (Apple Flash Storage)' : (isHdd ? 'HDD Mecânico' : 'NVMe / SATA SSD');
                    const mediaClass = isMacApfs ? 'badge info' : (isHdd ? 'badge warning' : 'badge success');
                    const recommendedAction = isMacApfs ? 'Manutenção APFS & Expurgo Snapshots' : (isHdd ? 'Desfragmentação Física (Defrag)' : 'TRIM / Retrim (Seguro)');

                    return `
                        <tr>
                            <td class="nowrap"><strong>${{escapeHtml(driveName)}}</strong><br><small style="color:var(--text-muted)">${{escapeHtml(p.mount_point)}}</small></td>
                            <td class="nowrap"><span class="${{mediaClass}}">${{escapeHtml(mediaLabel)}}</span></td>
                            <td class="nowrap"><span class="badge success">4 Camadas Ativas</span></td>
                            <td class="nowrap"><strong>${{escapeHtml(recommendedAction)}}</strong></td>
                            <td>
                                ${{isHdd ? `
                                    <div style="margin-bottom:0.4rem;">
                                        <label class="ctrl-label" style="display:inline-flex;align-items:center;gap:8px;font-size:0.78rem;color:var(--warning-color);cursor:pointer;">
                                            <input type="checkbox" id="chk-hdd-${{idx}}">
                                            <span>Confirmo que é HDD mecânico e autorizo Defrag</span>
                                        </label>
                                    </div>
                                ` : ''}}
                                <button class="btn secondary" style="font-size:0.8rem;padding:0.4rem 0.85rem;" data-drive="${{escapeHtml(p.drive_letter)}}" onclick="optimizeDisk(this, ${{isHdd}}, ${{idx}})">
                                    ⚡ Executar Otimização
                                </button>
                            </td>
                        </tr>
                    `;
                }}).join('') : '<tr><td colspan="5">Nenhum volume disponível para otimização.</td></tr>';
            }}
        }}

        async function optimizeDisk(btnOrDrive, isHdd, idx) {{
            const driveLetter = typeof btnOrDrive === 'string' ? btnOrDrive : (btnOrDrive.getAttribute('data-drive') || 'C:');
            const btnEl = typeof btnOrDrive === 'object' && btnOrDrive ? btnOrDrive : null;
            let confirmHdd = false;
            if (isHdd) {{
                const chk = document.getElementById(`chk-hdd-${{idx}}`);
                if (!chk || !chk.checked) {{
                    alert('⚠️ AVISO DE SEGURANÇA: Para desfragmentar uma partição classificada como HDD magnético, você deve obrigatoriamente marcar a caixa de confirmação para certificar que NÃO se trata de um SSD ou NVMe.');
                    return;
                }}
                confirmHdd = true;
            }}

            if (btnEl) {{
                btnEl.disabled = true;
                btnEl.textContent = '⏳ Otimizando...';
            }}

            showToast(`Iniciando otimização inteligente para o volume ${{driveLetter}}...`);
            try {{
                const res = await fetch('/api/optimize-disk', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{drive: driveLetter, confirm_hdd: confirmHdd, mode: 'real'}})
                }});
                const data = await res.json();
                const resBox = document.getElementById('hw-opt-result-box');
                if (resBox) {{
                    resBox.style.display = 'block';
                    document.getElementById('hw-opt-result-title').textContent = data.action_taken || 'Otimização Concluída';
                    document.getElementById('hw-opt-result-msg').textContent = data.message || 'Operação finalizada com sucesso.';
                    const checks = (data.result && data.result.guardrail_checks) || [];
                    document.getElementById('hw-opt-result-checks').innerHTML = checks.map(c => `• ${{escapeHtml(c)}}<br>`).join('');
                }}
                showToast(`✅ Otimização de ${{driveLetter}} finalizada com sucesso!`);
            }} catch (err) {{
                showToast(`Erro na requisição de otimização: ${{err.message}}`);
            }} finally {{
                if (btnEl) {{
                    btnEl.disabled = false;
                    btnEl.textContent = '⚡ Executar Otimização';
                }}
            }}
        }}

        document.addEventListener('DOMContentLoaded', initDashboard);
    </script>
</body>
</html>"""

    out_abs = os.path.abspath(output_filename)
    os.makedirs(os.path.dirname(out_abs), exist_ok=True)
    with open(out_abs, "w", encoding="utf-8") as f:
        f.write(html_content)
    return out_abs
