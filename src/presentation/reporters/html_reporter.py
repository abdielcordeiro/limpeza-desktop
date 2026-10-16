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
    </nav>

    <main class="container">
        <div id="action-toast" class="toast-banner"></div>

        <!-- ABA 1: RESUMO & SAÚDE DOS DISCOS -->
        <section id="tab-overview" class="tab-content active">
            <div class="grid-cards" id="partitions-grid"></div>
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
                <div class="filter-controls">
                    <button class="btn success" onclick="executeSelectedCleanup()">🧹 Executar Limpeza de Itens Selecionados</button>
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
                    <span class="badge purple" id="updates-count-badge">0 pacotes</span>
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
                            </tr>
                        </thead>
                        <tbody id="updates-tbody"></tbody>
                    </table>
                </div>
            </div>
        </section>
    </main>

    <script>
        let REPORT_DATA = {data_json};

        function switchTab(tabId, btnEl) {{
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            const target = document.getElementById(tabId);
            if (target) target.classList.add('active');
            if (btnEl) btnEl.classList.add('active');
        }}

        function showToast(msg) {{
            const t = document.getElementById('action-toast');
            t.textContent = msg;
            t.style.display = 'block';
            setTimeout(() => {{ t.style.display = 'none'; }}, 7000);
        }}

        function initDashboard() {{
            document.getElementById('hdr-os').textContent = (REPORT_DATA.os_version || REPORT_DATA.os_platform || 'OS').toUpperCase();
            document.getElementById('hdr-mode').textContent = REPORT_DATA.execution_mode === 'real' ? 'EXECUÇÃO REAL' : 'SIMULAÇÃO DRY-RUN';
            document.getElementById('hdr-sub').textContent = `Sessão ${{REPORT_DATA.session_id || '-'}} • Executado em ${{REPORT_DATA.executed_at || '-'}} • ${{REPORT_DATA.active_indicators_count || 0}} indicadores ativos nas 5 camadas`;

            document.getElementById('stat-freed').textContent = REPORT_DATA.total_bytes_freed_formatted || '0.00 B';
            document.getElementById('stat-potential').textContent = REPORT_DATA.potential_extra_bytes_formatted || '0.00 B';
            document.getElementById('stat-tweaks').textContent = (REPORT_DATA.tweaks_executed || []).length;
            document.getElementById('stat-apps').textContent = (REPORT_DATA.installed_apps || []).length;

            if (REPORT_DATA.snapshot_id) {{
                document.getElementById('snapshot-id-label').textContent = REPORT_DATA.snapshot_id;
            }}

            // Partições
            const pGrid = document.getElementById('partitions-grid');
            pGrid.innerHTML = (REPORT_DATA.partitions || []).map(p => {{
                const barColor = p.health_class === 'danger' ? 'var(--danger-color)' : (p.health_class === 'warning' ? 'var(--warning-color)' : 'var(--success-color)');
                return `<div class="card">
                    <div class="card-header">
                        <div class="card-title">💽 ${{p.drive_letter}} <small style="color:var(--text-muted)">(${{p.role}})</small></div>
                        <span class="badge ${{p.health_class}}">${{p.health_status}}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;font-size:0.85rem;white-space:nowrap;">
                        <span>Usado: <strong>${{p.used_formatted}}</strong> (${{p.percent_used}}%)</span>
                        <span>Livre: <strong>${{p.free_formatted}}</strong> / ${{p.total_formatted}}</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill" style="width:${{Math.min(p.percent_used, 100)}}%;background:${{barColor}}"></div>
                    </div>
                    <p style="font-size:0.8rem;color:var(--text-muted)">${{p.health_desc}}</p>
                </div>`;
            }}).join('');

            document.getElementById('session-logs').textContent = (REPORT_DATA.execution_logs || []).join('\\n');

            // Limpeza Autônoma
            const autoTbody = document.getElementById('auto-cleanup-tbody');
            const autoList = REPORT_DATA.autonomous_cleanups || [];
            autoTbody.innerHTML = autoList.length ? autoList.map(c => `<tr>
                <td><strong>${{c.name}}</strong><br><small style="color:var(--text-muted)">${{c.category}}</small></td>
                <td class="nowrap"><span class="badge ${{c.status === 'cleaned' ? 'success' : 'warning'}}">${{c.status.toUpperCase()}}</span></td>
                <td class="nowrap">${{c.files_removed}} arq.</td>
                <td class="nowrap"><strong>${{c.bytes_freed_formatted}}</strong></td>
                <td><div>${{c.details}}</div><div class="path-cell">${{(c.target_paths || []).join(' | ')}}</div></td>
            </tr>`).join('') : '<tr><td colspan="5">Nenhuma regra de limpeza autônoma executada nesta sessão.</td></tr>';

            renderInstalledApps();
            renderOrphans();
            renderTopOccupants();
            renderTweaks();
            renderCloudAndUpdates();
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
            </tr>`).join('') : '<tr><td colspan="5">Nenhum aplicativo encontrado para o filtro informado.</td></tr>';
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
                </tr>`;
            }}).join('') : '<tr><td colspan="6">Nenhuma pasta órfã ou cache pendente encontrado.</td></tr>';
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
            if (window.location.protocol.startsWith('http')) {{
                try {{
                    const res = await fetch('/api/clean-selected', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{paths: selected, mode: 'real'}})
                    }});
                    const data = await res.json();
                    if (data.status === 'ok') {{
                        // Remover itens apagados de REPORT_DATA.clean_suggestions
                        const cleanedSet = new Set(data.cleaned_paths || []);
                        REPORT_DATA.clean_suggestions = (REPORT_DATA.clean_suggestions || []).filter(c => !cleanedSet.has(c.path));

                        // Limpar seleções salvas no localStorage
                        const saved = JSON.parse(localStorage.getItem('limpeza_checked_orphans') || '{{}}');
                        (data.cleaned_paths || []).forEach(p => delete saved[p]);
                        localStorage.setItem('limpeza_checked_orphans', JSON.stringify(saved));

                        // Atualizar métricas do cabeçalho
                        if (data.total_freed_formatted) {{
                            document.getElementById('stat-freed').textContent = data.total_freed_formatted;
                        }}
                        if (data.potential_extra_formatted) {{
                            document.getElementById('stat-potential').textContent = data.potential_extra_formatted;
                        }}

                        // Redesenhar tabela de órfãos imediatamente (os itens somem da UI)
                        renderOrphans();

                        showToast(`Sucesso! ${{data.bytes_freed_formatted || '0 B'}} liberados e itens removidos da lista.`);
                    }} else {{
                        showToast(data.message || 'Erro ao processar limpeza selecionada.');
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
                                    <span class="subfolder-size">${{sub.size_formatted}}</span>
                                    <div class="subfolder-bar"><div class="subfolder-fill" style="width:${{pct}}%"></div></div>
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
                </tr>`;
            }}).join('') : '<tr><td colspan="6">Nenhum item corresponde aos filtros selecionados.</td></tr>';
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

        function escapeHtml(text) {{
            if (!text) return '';
            return String(text)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
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
            </tr>`).join('') : '<tr><td colspan="5">Nenhuma atualização pendente listada (ou verificação opt-in desativada).</td></tr>';
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
