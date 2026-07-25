# -*- coding: utf-8 -*-
import os
import json
from typing import List, Dict, Any

def generate_html_report(
    partitions: List[Dict[str, Any]],
    top_occupants: List[Dict[str, Any]],
    clean_suggestions: List[Dict[str, Any]],
    migration_suggestions: List[Dict[str, Any]],
    onedrive_info: Dict[str, Any],
    output_filename: str = "relatorio_limpeza_disco.html"
) -> str:
    """
    Gera o Dashboard HTML Interativo completo com 5 abas, layout horizontal expandido,
    filtro corrigido por partição para Maiores Ocupantes, análise aprofundada dos gargalos da AppData e salvamento via localStorage.
    """
    
    # Prepara os dados serializados em JSON para consumo seguro no JavaScript do Dashboard
    data_json = json.dumps({
        'partitions': partitions,
        'top_occupants': top_occupants,
        'clean_suggestions': clean_suggestions,
        'migration_suggestions': migration_suggestions,
        'onedrive_info': onedrive_info
    }, ensure_ascii=False)

    html_content = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard de Limpeza & Saúde dos Discos Windows</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0F172A;
            --bg-secondary: #1E293B;
            --bg-card: #1E293B;
            --bg-card-hover: #334155;
            --accent-primary: #38BDF8;
            --accent-hover: #0EA5E9;
            --text-main: #F8FAFC;
            --text-muted: #94A3B8;
            --border-color: #334155;
            --success-color: #10B981;
            --warning-color: #F59E0B;
            --danger-color: #EF4444;
            --purple-color: #8B5CF6;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
        }

        body {
            background-color: var(--bg-primary);
            color: var(--text-main);
            line-height: 1.6;
            padding: 0;
            margin: 0;
            min-height: 100vh;
        }

        header {
            background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
            border-bottom: 1px solid var(--border-color);
            padding: 1.25rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }

        .logo-area h1 {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-main);
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .logo-area h1 span.badge-title {
            background: rgba(56, 189, 248, 0.15);
            color: var(--accent-primary);
            font-size: 0.75rem;
            padding: 0.2rem 0.6rem;
            border-radius: 999px;
            border: 1px solid rgba(56, 189, 248, 0.3);
        }

        .logo-area p {
            font-size: 0.875rem;
            color: var(--text-muted);
            margin-top: 0.25rem;
        }

        .header-stats {
            display: flex;
            gap: 1.5rem;
            align-items: center;
        }

        .stat-box {
            background: var(--bg-card);
            padding: 0.75rem 1.25rem;
            border-radius: 12px;
            border: 1px solid var(--border-color);
            text-align: center;
        }

        .stat-box .val {
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--accent-primary);
        }

        .stat-box .lbl {
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        nav.tabs-nav {
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-color);
            display: flex;
            overflow-x: auto;
            padding: 0 2rem;
            gap: 0.5rem;
        }

        .tab-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 1rem 1.25rem;
            font-size: 0.95rem;
            font-weight: 500;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            transition: all 0.2s ease;
            white-space: nowrap;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .tab-btn:hover {
            color: var(--text-main);
            background: rgba(255, 255, 255, 0.03);
        }

        .tab-btn.active {
            color: var(--accent-primary);
            border-bottom-color: var(--accent-primary);
            font-weight: 600;
        }

        /* Container Expandido na Horizontal */
        main.container {
            max-width: 96%;
            width: 100%;
            margin: 1.5rem auto;
            padding: 0 1rem;
        }

        .tab-content {
            display: none;
            animation: fadeIn 0.3s ease-in-out;
        }

        .tab-content.active {
            display: block;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .grid-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.5rem;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }

        .card:hover {
            border-color: var(--accent-primary);
            transform: translateY(-2px);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }

        .card-title {
            font-size: 1.1rem;
            font-weight: 600;
        }

        .badge {
            padding: 0.25rem 0.75rem;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }

        .badge.success { background: rgba(16, 185, 129, 0.15); color: var(--success-color); border: 1px solid rgba(16, 185, 129, 0.3); }
        .badge.warning { background: rgba(245, 158, 11, 0.15); color: var(--warning-color); border: 1px solid rgba(245, 158, 11, 0.3); }
        .badge.danger { background: rgba(239, 68, 68, 0.15); color: var(--danger-color); border: 1px solid rgba(239, 68, 68, 0.3); }
        .badge.purple { background: rgba(139, 92, 246, 0.15); color: var(--purple-color); border: 1px solid rgba(139, 92, 246, 0.3); }

        .progress-bar-bg {
            background: #0F172A;
            height: 12px;
            border-radius: 999px;
            overflow: hidden;
            margin: 1rem 0 0.5rem 0;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }

        .progress-bar-fill {
            height: 100%;
            border-radius: 999px;
            transition: width 0.5s ease;
        }

        .progress-bar-fill.success { background: linear-gradient(90deg, #10B981, #34D399); }
        .progress-bar-fill.warning { background: linear-gradient(90deg, #F59E0B, #FBBF24); }
        .progress-bar-fill.danger { background: linear-gradient(90deg, #EF4444, #F87171); }

        .category-selector-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }

        .cat-btn {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 1.25rem;
            display: flex;
            align-items: center;
            gap: 1rem;
            cursor: pointer;
            text-align: left;
            transition: all 0.2s ease;
            position: relative;
        }

        .cat-btn:hover {
            border-color: var(--accent-primary);
            background: var(--bg-card-hover);
        }

        .cat-btn.active {
            border-color: var(--accent-primary);
            background: rgba(56, 189, 248, 0.08);
            box-shadow: 0 0 15px rgba(56, 189, 248, 0.15);
        }

        .cat-icon {
            font-size: 2rem;
            line-height: 1;
        }

        .cat-info {
            flex: 1;
        }

        .cat-title {
            font-size: 0.95rem;
            font-weight: 700;
            color: var(--text-main);
            margin-bottom: 0.2rem;
        }

        .cat-desc {
            font-size: 0.78rem;
            color: var(--text-muted);
            line-height: 1.3;
        }

        .cat-badge {
            font-size: 0.8rem;
            font-weight: 700;
            padding: 0.25rem 0.55rem;
            border-radius: 8px;
            white-space: nowrap;
        }

        .category-banner {
            background: rgba(30, 41, 59, 0.8);
            border: 1px solid var(--border-color);
            border-left: 4px solid var(--accent-primary);
            padding: 1rem 1.25rem;
            border-radius: 10px;
            margin-bottom: 1.5rem;
            font-size: 0.9rem;
            color: var(--text-main);
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .filter-bar {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            padding: 1rem 1.25rem;
            border-radius: 14px;
            margin-bottom: 1.5rem;
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
            align-items: center;
        }

        .filter-input, .filter-select {
            background: #0F172A;
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 0.6rem 1rem;
            border-radius: 8px;
            font-size: 0.9rem;
            outline: none;
        }

        .filter-input {
            flex: 1;
            min-width: 250px;
        }

        .filter-input:focus, .filter-select:focus {
            border-color: var(--accent-primary);
        }

        .toggle-resolved-btn {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 0.6rem 1.1rem;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            white-space: nowrap;
        }

        .toggle-resolved-btn.active {
            border-color: var(--accent-primary);
            color: var(--accent-primary);
            background: rgba(56, 189, 248, 0.12);
        }

        .table-responsive {
            overflow-x: auto;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            width: 100%;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.9rem;
            table-layout: auto;
        }

        th {
            background: #111827;
            color: var(--text-muted);
            font-weight: 600;
            padding: 0.85rem 1rem;
            border-bottom: 1px solid var(--border-color);
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
            white-space: nowrap;
        }

        td {
            padding: 0.85rem 1rem;
            border-bottom: 1px solid var(--border-color);
            vertical-align: middle;
        }

        tr:hover td {
            background: var(--bg-card-hover);
        }

        tr.resolved td {
            opacity: 0.4;
            text-decoration: line-through;
        }

        .custom-checkbox {
            width: 20px;
            height: 20px;
            cursor: pointer;
            accent-color: var(--success-color);
        }

        /* Colunas & Botão Copiar */
        .col-check { width: 45px; text-align: center; }
        .col-name { min-width: 160px; max-width: 220px; word-break: break-word; font-weight: 600; }
        .col-risk { min-width: 160px; white-space: nowrap; }
        .col-drive { width: 80px; text-align: center; white-space: nowrap; }
        .col-size { width: 110px; text-align: right; white-space: nowrap; }
        .col-diag { min-width: 240px; max-width: 380px; word-break: break-word; }
        .col-path { min-width: 300px; max-width: 520px; }

        .path-container {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            flex-wrap: wrap;
        }

        .path-code {
            font-family: monospace;
            background: #0F172A;
            padding: 0.35rem 0.6rem;
            border-radius: 6px;
            font-size: 0.78rem;
            color: #7DD3FC;
            word-break: break-all;
            overflow-wrap: anywhere;
            white-space: normal;
            flex: 1;
        }

        .btn-copy {
            background: rgba(56, 189, 248, 0.12);
            border: 1px solid rgba(56, 189, 248, 0.3);
            color: var(--accent-primary);
            padding: 0.3rem 0.6rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            white-space: nowrap;
        }

        .btn-copy:hover {
            background: var(--accent-primary);
            color: #0F172A;
        }

        .step-card {
            background: #0F172A;
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.25rem;
            margin-bottom: 1rem;
        }

        .step-card h4 {
            color: var(--accent-primary);
            font-size: 1rem;
            margin-bottom: 0.5rem;
        }

        .step-card p {
            color: var(--text-main);
            font-size: 0.9rem;
            margin-bottom: 0.5rem;
        }

        .step-card .effect {
            font-size: 0.825rem;
            color: var(--success-color);
            font-style: italic;
        }

        footer {
            text-align: center;
            padding: 2rem;
            color: var(--text-muted);
            font-size: 0.85rem;
            border-top: 1px solid var(--border-color);
            margin-top: 4rem;
        }
    </style>
</head>
<body>

    <header>
        <div class="logo-area">
            <h1>📊 Analisador de Limpeza de Disco <span class="badge-title">Windows Multi-Drive</span></h1>
            <p>Diagnóstico inteligente de partições, eliminação de falsos positivos e checklist de evolução</p>
        </div>
        <div class="header-stats">
            <div class="stat-box">
                <div class="val" id="total-freed-header">0.00 MB</div>
                <div class="lbl">Espaço Liberado</div>
            </div>
            <div class="stat-box">
                <div class="val" id="pending-clean-header">0</div>
                <div class="lbl">Itens Pendentes</div>
            </div>
        </div>
    </header>

    <nav class="tabs-nav">
        <button class="tab-btn active" onclick="switchTab('tab-partitions', this)">💻 Visão Geral das Partições</button>
        <button class="tab-btn" onclick="switchTab('tab-clean', this)">🧹 Limpeza Segura & Órfãos (<span id="count-clean-badge">0</span>)</button>
        <button class="tab-btn" onclick="switchTab('tab-occupants', this)">📁 Maiores Ocupantes</button>
        <button class="tab-btn" onclick="switchTab('tab-migration', this)">🚚 Guia de Migração (C: -> D:)</button>
        <button class="tab-btn" onclick="switchTab('tab-onedrive', this)">☁️ Diagnóstico OneDrive</button>
    </nav>

    <main class="container">

        <!-- ABA 1: Visão Geral das Partições -->
        <div id="tab-partitions" class="tab-content active">
            <h2 style="margin-bottom: 1.5rem;">Saúde das Partições Mapeadas no Sistema</h2>
            <div class="grid-cards" id="partitions-grid"></div>
        </div>

        <!-- ABA 2: Limpeza Segura & Órfãos -->
        <div id="tab-clean" class="tab-content">
            <h2 style="margin-bottom: 1rem;">Checklist Interativo de Limpeza Segura & AppData</h2>
            <p style="color: var(--text-muted); margin-bottom: 1.5rem;">
                Selecione a visão desejada para focar nos maiores gargalos da pasta AppData, resíduos órfãos permanentes ou caches reincidentes.
            </p>

            <!-- Categorias Visuais (Sub-Abas de Limpeza) -->
            <div class="category-selector-grid">
                <button class="cat-btn active" id="cat-btn-all" onclick="selectCleanCategory('ALL', this)">
                    <div class="cat-icon">📋</div>
                    <div class="cat-info">
                        <div class="cat-title">Todos os Itens</div>
                        <div class="cat-desc">Visão consolidada de todas as sugestões</div>
                    </div>
                </button>

                <button class="cat-btn" id="cat-btn-appdata" onclick="selectCleanCategory('APPDATA', this)">
                    <div class="cat-icon">💥</div>
                    <div class="cat-info">
                        <div class="cat-title">Gargalos da AppData</div>
                        <div class="cat-desc">DXCache GPU, Electron, WhatsApp, Dumps e Caches</div>
                    </div>
                    <div class="cat-badge danger" id="cat-badge-appdata">0 MB</div>
                </button>

                <button class="cat-btn" id="cat-btn-orphans" onclick="selectCleanCategory('ORPHAN', this)">
                    <div class="cat-icon">🗑️</div>
                    <div class="cat-info">
                        <div class="cat-title">Resíduos Órfãos (Permanentes)</div>
                        <div class="cat-desc">Pastas de apps desinstalados (liberação real permanente)</div>
                    </div>
                    <div class="cat-badge warning" id="cat-badge-orphans">0 MB</div>
                </button>

                <button class="cat-btn" id="cat-btn-caches" onclick="selectCleanCategory('CACHE', this)">
                    <div class="cat-icon">⚡</div>
                    <div class="cat-info">
                        <div class="cat-title">Caches & Temporários (Reincidentes)</div>
                        <div class="cat-desc">Caches e logs descartáveis (recriados pelo uso)</div>
                    </div>
                    <div class="cat-badge success" id="cat-badge-caches">0 MB</div>
                </button>
            </div>

            <div class="category-banner" id="category-banner-info">
                <span>📋 Exibindo todos os resíduos órfãos, gargalos do AppData e arquivos temporários descartáveis detectados.</span>
            </div>

            <div class="filter-bar">
                <input type="text" id="search-clean" class="filter-input" placeholder="🔍 Buscar por nome do arquivo, pasta ou caminho..." oninput="filterCleanTable()">
                <select id="filter-risk" class="filter-select" onchange="filterCleanTable()">
                    <option value="ALL">Todos os Riscos</option>
                    <option value="Seguro">Apenas Seguro / Apagar</option>
                    <option value="Órfão">Apenas Resíduos Órfãos</option>
                </select>
                <select id="filter-drive" class="filter-select" onchange="filterCleanTable()">
                    <option value="ALL">Todas as Partições</option>
                </select>
                <button class="toggle-resolved-btn" id="btn-toggle-resolved" onclick="toggleShowResolved(this)">
                    👁️ Mostrar Itens Concluídos (<span id="resolved-count-badge">0</span>)
                </button>
            </div>

            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th class="col-check">OK</th>
                            <th class="col-name">Item Detectado</th>
                            <th class="col-risk">Classificação de Risco</th>
                            <th class="col-drive">Partição</th>
                            <th class="col-size">Tamanho</th>
                            <th class="col-diag">Diagnóstico / O que fazer</th>
                            <th class="col-path">Caminho Completo</th>
                        </tr>
                    </thead>
                    <tbody id="clean-table-body"></tbody>
                </table>
            </div>
        </div>

        <!-- ABA 3: Maiores Ocupantes -->
        <div id="tab-occupants" class="tab-content">
            <h2 style="margin-bottom: 1rem;">Maiores Arquivos e Pastas do Sistema</h2>
            <p style="color: var(--text-muted); margin-bottom: 1.5rem;">
                Ranking dos conteúdos mais pesados do sistema com diagnósticos de segurança para exclusão ou desinstalação.
            </p>

            <div class="filter-bar">
                <input type="text" id="search-occupants" class="filter-input" placeholder="🔍 Filtrar ocupantes por nome ou caminho..." oninput="filterOccupantsTable()">
                <select id="filter-occupants-type" class="filter-select" onchange="filterOccupantsTable()">
                    <option value="ALL">Todos os Tipos (Pastas e Arquivos)</option>
                    <option value="Pasta">Apenas Pastas</option>
                    <option value="Arquivo">Apenas Arquivos</option>
                </select>
                <select id="filter-occupants-drive" class="filter-select" onchange="filterOccupantsTable()">
                    <option value="ALL">Todas as Partições</option>
                </select>
                <select id="filter-occupants-safety" class="filter-select" onchange="filterOccupantsTable()">
                    <option value="ALL">Todas as Ações Recomendadas</option>
                    <option value="Não Apagar">🚫 Não Apagar (Sistema Operacional)</option>
                    <option value="Painel de Controle">⚙️ Desinstalar via Painel / App</option>
                    <option value="Limpeza Direta">✅ Limpeza Direta (Sem Risco ao SO)</option>
                </select>
            </div>

            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th style="width: 100px;">Tipo</th>
                            <th style="min-width: 180px; max-width: 240px;">Nome do Item</th>
                            <th style="width: 90px; text-align: center;">Partição</th>
                            <th style="width: 120px; text-align: right;">Tamanho</th>
                            <th style="min-width: 250px; max-width: 380px;">Ação Recomendada & Diagnóstico</th>
                            <th style="min-width: 300px; max-width: 500px;">Caminho Completo</th>
                        </tr>
                    </thead>
                    <tbody id="occupants-table-body"></tbody>
                </table>
            </div>
        </div>

        <!-- ABA 4: Guia de Migração C: -> D: -->
        <div id="tab-migration" class="tab-content">
            <h2 style="margin-bottom: 1rem;">Sugestões de Migração para Liberar o SSD do Sistema (C:)</h2>
            <p style="color: var(--text-muted); margin-bottom: 1.5rem;">
                Mover programas grandes e bibliotecas para partições secundárias mantém o SO rápido e previne travamentos por espaço reduzido.
            </p>

            <div class="table-responsive" style="margin-bottom: 2rem;">
                <table>
                    <thead>
                        <tr>
                            <th style="min-width: 180px;">Aplicação / Pasta</th>
                            <th style="width: 100px; text-align: center;">Drive Atual</th>
                            <th style="width: 110px; text-align: right;">Tamanho</th>
                            <th style="width: 140px;">Viabilidade</th>
                            <th style="min-width: 250px;">Recomendação de Transferência</th>
                            <th>Caminho de Origem</th>
                        </tr>
                    </thead>
                    <tbody id="migration-table-body"></tbody>
                </table>
            </div>

            <div style="background: var(--bg-card); padding: 1.5rem; border-radius: 16px; border: 1px solid var(--border-color);">
                <h3 style="color: var(--accent-primary); margin-bottom: 1rem;">💡 Como Funciona a Viabilidade e Taxa de Sucesso?</h3>
                <ul style="color: var(--text-main); font-size: 0.95rem; margin-left: 1.25rem; line-height: 1.8;">
                    <li><strong>Taxa de Liberação Esperada:</strong> Entre <strong>50% e 80% do disco C:</strong> pode ser mantido livre transferindo Jogos, Mídias e Instaladores para o D:.</li>
                    <li><strong>O que PODE ser movido:</strong> Jogos da Steam/Epic, Downloads, Documentos e Instaladores Secundários.</li>
                    <li><strong>O que SEMPRE fica no C::</strong> Arquivos essenciais do Windows (<code class="path-code" style="display:inline;">C:\\Windows</code>), Drivers e componentes de inicialização.</li>
                </ul>
            </div>
        </div>

        <!-- ABA 5: Diagnóstico OneDrive -->
        <div id="tab-onedrive" class="tab-content">
            <h2 style="margin-bottom: 1rem;">Diagnóstico e Remoção de Vínculo do OneDrive</h2>
            <div id="onedrive-summary-card" style="margin-bottom: 2rem;"></div>
            <h3 style="margin-bottom: 1rem;">Passo a Passo de Resolução Recomendado:</h3>
            <div id="onedrive-steps-list"></div>
        </div>

    </main>

    <footer>
        <p>Analisador de Limpeza de Disco Windows | Gerado dinamicamente para otimização de SSDs e múltiplos discos</p>
    </footer>

    <script>
        const rawData = DATA_JSON_PLACEHOLDER;

        // Estado inicial e persistência no localStorage
        let resolvedItems = JSON.parse(localStorage.getItem('resolved_disk_items') || '[]');
        let selectedCategory = 'ALL';
        let showResolved = false;

        function escapeHtml(str) {
            if (!str) return '';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }

        function matchDriveString(targetDrive, selectedDriveOption) {
            if (!selectedDriveOption || selectedDriveOption === 'ALL') return true;
            if (!targetDrive) return false;
            const cleanTarget = String(targetDrive).split(':')[0].toLowerCase().trim();
            const cleanSelected = String(selectedDriveOption).split(':')[0].toLowerCase().trim();
            return cleanTarget === cleanSelected;
        }

        function isItemAppData(item) {
            const path = String(item.path || '').split(String.fromCharCode(92)).join('/').toLowerCase();
            const type = String(item.type || '').toLowerCase();
            return path.indexOf('/appdata/') !== -1 || type.indexOf('appdata') !== -1;
        }

        function isItemOrphan(item) {
            if (!item) return false;
            const risk = String(item.risk_level || '').toLowerCase();
            const type = String(item.type || '').toLowerCase();
            return risk.includes('órfão') || type.includes('órfão') || type.includes('desinstalado');
        }

        function switchTab(tabId, btn) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));

            const targetTab = document.getElementById(tabId);
            if (targetTab) {
                targetTab.classList.add('active');
            }
            if (btn) {
                btn.classList.add('active');
            }
        }

        function selectCleanCategory(cat, btn) {
            selectedCategory = cat;
            document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');

            const banner = document.getElementById('category-banner-info');
            if (banner) {
                if (cat === 'ORPHAN') {
                    banner.innerHTML = '<span>🗑️ <strong>Resíduos Órfãos:</strong> Pastas de softwares desinstalados. A exclusão libera espaço <strong>REAL e PERMANENTE</strong> no seu SSD.</span>';
                } else if (cat === 'CACHE') {
                    banner.innerHTML = '<span>⚡ <strong>Caches & Temporários:</strong> Caches de navegadores e logs. Podem ser apagados para <strong>liberação imediata</strong>, mas são reconstruídos com o uso.</span>';
                } else if (cat === 'APPDATA') {
                    banner.innerHTML = '<span>💥 <strong>Gargalos da AppData:</strong> Maior acumulador de espaço no SSD! Focado em Shaders de GPU (DXCache), caches de Electron/WhatsApp, relatórios WER e dumps de erros.</span>';
                } else {
                    banner.innerHTML = '<span>📋 <strong>Visão Consolidada:</strong> Exibindo todos os resíduos órfãos, gargalos do AppData e arquivos temporários descartáveis detectados.</span>';
                }
            }

            filterCleanTable();
        }

        function toggleShowResolved(btn) {
            showResolved = !showResolved;
            if (btn) {
                if (showResolved) {
                    btn.classList.add('active');
                    btn.innerHTML = `👁️ Ocultar Itens Concluídos (<span id="resolved-count-badge">${resolvedItems.length}</span>)`;
                } else {
                    btn.classList.remove('active');
                    btn.innerHTML = `👁️ Mostrar Itens Concluídos (<span id="resolved-count-badge">${resolvedItems.length}</span>)`;
                }
            }
            filterCleanTable();
        }

        function renderPartitions() {
            const grid = document.getElementById('partitions-grid');
            if (!rawData.partitions || rawData.partitions.length === 0) {
                grid.innerHTML = '<p>Nenhuma partição encontrada.</p>';
                return;
            }
            grid.innerHTML = rawData.partitions.map(p => `
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">Partição ${escapeHtml(p.drive_letter)}</div>
                        <span class="badge ${escapeHtml(p.health_class)}">${escapeHtml(p.health_status)}</span>
                    </div>
                    <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1rem;">${escapeHtml(p.role)}</p>
                    <div style="font-size: 1.25rem; font-weight: 700; margin-bottom: 0.25rem;">
                        ${escapeHtml(p.used_formatted)} <span style="font-size: 0.85rem; color: var(--text-muted); font-weight: 400;">usados de ${escapeHtml(p.total_formatted)}</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill ${escapeHtml(p.health_class)}" style="width: ${p.percent_used}%;"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: var(--text-muted); margin-top: 0.5rem;">
                        <span>Uso: <strong>${p.percent_used}%</strong></span>
                        <span>Livre: <strong>${escapeHtml(p.free_formatted)}</strong></span>
                    </div>
                    <p style="font-size: 0.8rem; margin-top: 1rem; color: var(--text-main);">${escapeHtml(p.health_desc)}</p>
                </div>
            `).join('');
        }

        function renderCleanTable() {
            const tbody = document.getElementById('clean-table-body');
            document.getElementById('count-clean-badge').innerText = rawData.clean_suggestions ? rawData.clean_suggestions.length : 0;

            if (!rawData.clean_suggestions || rawData.clean_suggestions.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--success-color); font-weight: 600;">Nenhum resíduo órfão ou temporário detectado.</td></tr>';
                return;
            }

            tbody.innerHTML = rawData.clean_suggestions.map((item, idx) => {
                const isResolved = resolvedItems.includes(item.path);
                const safePathAttr = encodeURIComponent(item.path);
                const isOrphan = isItemOrphan(item);
                const isAppData = isItemAppData(item);

                return `
                    <tr class="${isResolved ? 'resolved' : ''}" id="row-clean-${idx}" data-path="${safePathAttr}" data-drive="${escapeHtml(item.drive)}" data-orphan="${isOrphan ? 'true' : 'false'}" data-appdata="${isAppData ? 'true' : 'false'}" data-resolved="${isResolved ? 'true' : 'false'}">
                        <td class="col-check">
                            <input type="checkbox" class="custom-checkbox clean-checkbox" data-path="${safePathAttr}" ${isResolved ? 'checked' : ''}>
                        </td>
                        <td class="col-name"><div>${escapeHtml(item.name)}</div></td>
                        <td class="col-risk"><span class="badge ${escapeHtml(item.risk_badge)}">${escapeHtml(item.risk_level)}</span></td>
                        <td class="col-drive"><strong>${escapeHtml(item.drive)}</strong></td>
                        <td class="col-size"><strong>${escapeHtml(item.size_formatted)}</strong></td>
                        <td class="col-diag">
                            <div>${escapeHtml(item.reason)}</div>
                            <div style="font-size: 0.75rem; color: var(--accent-primary); margin-top: 0.25rem;">💡 ${escapeHtml(item.how_to_fix)}</div>
                        </td>
                        <td class="col-path">
                            <div class="path-container">
                                <span class="path-code">${escapeHtml(item.path)}</span>
                                <button class="btn-copy" onclick="copyToClipboard('${safePathAttr}', this)" title="Copiar caminho completo">📋 Copiar</button>
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');
        }

        function setupEventListeners() {
            const cleanTbody = document.getElementById('clean-table-body');
            if (cleanTbody) {
                cleanTbody.addEventListener('change', function(e) {
                    if (e.target && e.target.classList.contains('clean-checkbox')) {
                        const rawPath = decodeURIComponent(e.target.getAttribute('data-path'));
                        toggleItemResolved(rawPath);
                    }
                });
            }
        }

        function toggleItemResolved(path) {
            if (resolvedItems.includes(path)) {
                resolvedItems = resolvedItems.filter(p => p !== path);
            } else {
                resolvedItems.push(path);
            }
            localStorage.setItem('resolved_disk_items', JSON.stringify(resolvedItems));
            renderCleanTable();
            filterCleanTable();
            updateStats();
        }

        function updateStats() {
            let freedBytes = 0;
            let pendingCount = 0;
            let appdataBytes = 0;
            let orphanBytes = 0;
            let cacheBytes = 0;

            if (rawData.clean_suggestions) {
                rawData.clean_suggestions.forEach(item => {
                    if (resolvedItems.includes(item.path)) {
                        freedBytes += item.size;
                    } else {
                        pendingCount++;
                    }

                    if (isItemAppData(item)) {
                        appdataBytes += item.size;
                    }
                    if (isItemOrphan(item)) {
                        orphanBytes += item.size;
                    } else {
                        cacheBytes += item.size;
                    }
                });
            }

            const totalFreedEl = document.getElementById('total-freed-header');
            if (totalFreedEl) totalFreedEl.innerText = formatSize(freedBytes);

            const pendingEl = document.getElementById('pending-clean-header');
            if (pendingEl) pendingEl.innerText = pendingCount;
            
            const badge = document.getElementById('resolved-count-badge');
            if (badge) badge.innerText = resolvedItems.length;

            const bAppData = document.getElementById('cat-badge-appdata');
            if (bAppData) bAppData.innerText = formatSize(appdataBytes);

            const bOrphans = document.getElementById('cat-badge-orphans');
            if (bOrphans) bOrphans.innerText = formatSize(orphanBytes);

            const bCaches = document.getElementById('cat-badge-caches');
            if (bCaches) bCaches.innerText = formatSize(cacheBytes);
        }

        function formatSize(bytes) {
            if (bytes <= 0) return "0.00 MB";
            const units = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
            let i = 0;
            while (bytes >= 1024 && i < units.length - 1) {
                bytes /= 1024;
                i++;
            }
            return bytes.toFixed(2) + ' ' + units[i];
        }

        function populateDriveFilterOptions() {
            const cleanSelect = document.getElementById('filter-drive');
            const occSelect = document.getElementById('filter-occupants-drive');

            if (!rawData.partitions) return;
            rawData.partitions.forEach(p => {
                if (cleanSelect) {
                    const opt = document.createElement('option');
                    opt.value = p.drive_letter;
                    opt.innerText = `Partição ${p.drive_letter}`;
                    cleanSelect.appendChild(opt);
                }
                if (occSelect) {
                    const opt = document.createElement('option');
                    opt.value = p.drive_letter;
                    opt.innerText = `Partição ${p.drive_letter}`;
                    occSelect.appendChild(opt);
                }
            });
        }

        function filterCleanTable() {
            const search = document.getElementById('search-clean').value.toLowerCase();
            const risk = document.getElementById('filter-risk').value;
            const drive = document.getElementById('filter-drive').value;

            document.querySelectorAll('#clean-table-body tr').forEach(row => {
                const text = row.innerText.toLowerCase();
                const matchesSearch = text.includes(search);
                const matchesRisk = risk === 'ALL' || text.includes(risk.toLowerCase());
                
                const rowDrive = row.getAttribute('data-drive');
                const matchesDrive = matchDriveString(rowDrive, drive);

                const isOrphan = row.getAttribute('data-orphan') === 'true';
                const isAppData = row.getAttribute('data-appdata') === 'true';
                const isResolved = row.getAttribute('data-resolved') === 'true';

                let matchesCategory = true;
                if (selectedCategory === 'ORPHAN') {
                    matchesCategory = isOrphan;
                } else if (selectedCategory === 'CACHE') {
                    matchesCategory = !isOrphan;
                } else if (selectedCategory === 'APPDATA') {
                    matchesCategory = isAppData;
                }

                let matchesResolvedVis = true;
                if (isResolved && !showResolved) {
                    matchesResolvedVis = false;
                }

                if (matchesSearch && matchesRisk && matchesDrive && matchesCategory && matchesResolvedVis) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        }

        function renderOccupantsTable() {
            const tbody = document.getElementById('occupants-table-body');
            if (!rawData.top_occupants || rawData.top_occupants.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">Nenhum item ocupante encontrado.</td></tr>';
                return;
            }
            tbody.innerHTML = rawData.top_occupants.map(item => {
                const safePathAttr = encodeURIComponent(item.path);
                return `
                    <tr data-type="${escapeHtml(item.type)}" data-drive="${escapeHtml(item.drive)}" data-safety="${escapeHtml(item.safety_action)}">
                        <td><span class="badge ${item.type === 'Pasta' ? 'purple' : 'success'}">${escapeHtml(item.type)}</span></td>
                        <td><strong>${escapeHtml(item.name)}</strong></td>
                        <td style="text-align: center;"><strong>${escapeHtml(item.drive)}</strong></td>
                        <td style="text-align: right;"><strong>${escapeHtml(item.size_formatted)}</strong></td>
                        <td>
                            <div><span class="badge ${escapeHtml(item.safety_badge)}">${escapeHtml(item.safety_action)}</span></div>
                            <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 0.25rem;">${escapeHtml(item.safety_recommendation)}</div>
                        </td>
                        <td>
                            <div class="path-container">
                                <span class="path-code">${escapeHtml(item.path)}</span>
                                <button class="btn-copy" onclick="copyToClipboard('${safePathAttr}', this)" title="Copiar caminho completo">📋 Copiar</button>
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');
        }

        function filterOccupantsTable() {
            const search = document.getElementById('search-occupants').value.toLowerCase();
            const type = document.getElementById('filter-occupants-type').value;
            const drive = document.getElementById('filter-occupants-drive').value;
            const safety = document.getElementById('filter-occupants-safety').value;

            document.querySelectorAll('#occupants-table-body tr').forEach(row => {
                const text = row.innerText.toLowerCase();
                const matchesSearch = text.includes(search);
                
                const rowType = row.getAttribute('data-type');
                const rowDrive = row.getAttribute('data-drive');
                const rowSafety = row.getAttribute('data-safety');

                const matchesType = type === 'ALL' || rowType === type;
                const matchesDrive = matchDriveString(rowDrive, drive);
                const matchesSafety = safety === 'ALL' || rowSafety.includes(safety);

                if (matchesSearch && matchesType && matchesDrive && matchesSafety) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        }

        function renderMigrationTable() {
            const tbody = document.getElementById('migration-table-body');
            if (!rawData.migration_suggestions || rawData.migration_suggestions.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--success-color); font-weight: 600;">Seu SSD C: está limpo! Não há programas pesados instalados inapropriadamente nele.</td></tr>`;
                return;
            }
            tbody.innerHTML = rawData.migration_suggestions.map(item => {
                const safePathAttr = encodeURIComponent(item.path);
                return `
                    <tr>
                        <td><strong>${escapeHtml(item.name)}</strong></td>
                        <td style="text-align: center;"><strong>${escapeHtml(item.current_drive)}</strong></td>
                        <td style="text-align: right;"><strong>${escapeHtml(item.size_formatted)}</strong></td>
                        <td><span class="badge success">${escapeHtml(item.feasibility_rate)}</span></td>
                        <td>${escapeHtml(item.reason)} <br><small style="color: var(--accent-primary);">${escapeHtml(item.how_to_migrate)}</small></td>
                        <td>
                            <div class="path-container">
                                <span class="path-code">${escapeHtml(item.path)}</span>
                                <button class="btn-copy" onclick="copyToClipboard('${safePathAttr}', this)" title="Copiar caminho completo">📋 Copiar</button>
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');
        }

        function renderOneDriveInfo() {
            const info = rawData.onedrive_info;
            const summaryCard = document.getElementById('onedrive-summary-card');
            const stepsList = document.getElementById('onedrive-steps-list');

            if (!info || !info.is_installed) {
                summaryCard.innerHTML = `<div class="card"><h3 style="color: var(--success-color);">Nenhuma conta ativa do OneDrive consumindo espaço local.</h3></div>`;
                return;
            }

            const safePathAttr = encodeURIComponent(info.path);

            summaryCard.innerHTML = `
                <div class="card" style="border-color: ${info.is_consuming_heavy_space ? 'var(--warning-color)' : 'var(--border-color)'};">
                    <div class="card-header">
                        <div class="card-title">Pasta Local do OneDrive Mapeada</div>
                        <span class="badge ${info.is_consuming_heavy_space ? 'warning' : 'success'}">
                            ${info.is_consuming_heavy_space ? 'Consumo Elevado' : 'Consumo Normal'}
                        </span>
                    </div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: var(--accent-primary);">
                        ${escapeHtml(info.consumed_formatted)} <span style="font-size: 0.9rem; color: var(--text-muted); font-weight: 400;">em ${info.file_count} arquivos sincronizados</span>
                    </div>
                    <div style="margin-top: 0.75rem;" class="path-container">
                        <span class="path-code">${escapeHtml(info.path)}</span>
                        <button class="btn-copy" onclick="copyToClipboard('${safePathAttr}', this)" title="Copiar caminho do OneDrive">📋 Copiar</button>
                    </div>
                </div>
            `;

            stepsList.innerHTML = info.recommendations.map(rec => `
                <div class="step-card">
                    <h4>${escapeHtml(rec.step)}</h4>
                    <p>${escapeHtml(rec.action)}</p>
                    <div class="effect">✨ Resultado: ${escapeHtml(rec.effect)}</div>
                </div>
            `).join('');
        }

        function copyToClipboard(encodedPath, btn) {
            const rawPath = decodeURIComponent(encodedPath);
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(rawPath).then(() => {
                    showCopyFeedback(btn);
                }).catch(() => {
                    fallbackCopyText(rawPath, btn);
                });
            } else {
                fallbackCopyText(rawPath, btn);
            }
        }

        function showCopyFeedback(btn) {
            if (!btn) return;
            const originalText = btn.innerHTML;
            btn.innerHTML = '✅ Copiado!';
            btn.style.background = 'var(--success-color)';
            btn.style.color = '#0F172A';
            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.style.background = '';
                btn.style.color = '';
            }, 1500);
        }

        function fallbackCopyText(text, btn) {
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            try {
                document.execCommand('copy');
                showCopyFeedback(btn);
            } catch (err) {
                console.error('Falha ao copiar:', err);
            }
            document.body.removeChild(textArea);
        }

        function initApp() {
            renderPartitions();
            renderCleanTable();
            renderOccupantsTable();
            renderMigrationTable();
            renderOneDriveInfo();
            populateDriveFilterOptions();
            setupEventListeners();
            updateStats();
            filterCleanTable();
        }

        window.onload = initApp;
    </script>
</body>
</html>
"""

    html_final = html_content.replace("DATA_JSON_PLACEHOLDER", data_json)

    os.makedirs(os.path.dirname(os.path.abspath(output_filename)), exist_ok=True)
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(html_final)

    return os.path.abspath(output_filename)
