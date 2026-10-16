# -*- coding: utf-8 -*-
"""Servidor HTTP Local (127.0.0.1) para a Janela Inicial de Configuração e Dashboard Interativo."""
import os
import json
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Optional, Tuple

from src.domain.value_objects import OSPlatform, ExecutionMode
from src.application.dtos import ExecutionPlanDTO
from src.application.orchestrator import OrchestratorService
from src.presentation.reporters.html_reporter import generate_html_report


LAUNCHER_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Janela de Configuração — Limpeza & Otimização Desktop</title>
    <style>
        :root {
            --bg-primary: #0B0F19;
            --bg-secondary: #111827;
            --bg-card: #1E293B;
            --accent: #38BDF8;
            --accent-hover: #0EA5E9;
            --text-main: #F8FAFC;
            --text-muted: #94A3B8;
            --border: #334155;
            --success: #10B981;
            --warning: #F59E0B;
            --danger: #EF4444;
        }
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        body {
            background: var(--bg-primary);
            color: var(--text-main);
            line-height: 1.5;
            padding-bottom: 4rem;
        }
        header {
            background: linear-gradient(135deg, #0B0F19 0%, #1E293B 100%);
            border-bottom: 1px solid var(--border);
            padding: 1.25rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }
        .title-group h1 {
            font-size: 1.35rem;
            display: flex;
            align-items: center;
            gap: 0.65rem;
            flex-wrap: wrap;
        }
        .pill {
            font-size: 0.75rem;
            padding: 0.2rem 0.65rem;
            border-radius: 999px;
            background: rgba(56, 189, 248, 0.15);
            color: var(--accent);
            border: 1px solid rgba(56, 189, 248, 0.35);
            white-space: nowrap;
        }
        .container {
            max-width: 1360px;
            margin: 1.5rem auto;
            padding: 0 1.5rem;
        }
        .section-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 1.35rem;
            margin-bottom: 1.25rem;
            overflow: hidden;
        }
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.75rem;
            margin-bottom: 1rem;
            padding-bottom: 0.65rem;
            border-bottom: 1px solid rgba(51, 65, 85, 0.6);
        }
        .grid-2 {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(290px, 1fr));
            gap: 1rem;
        }
        .grid-3 {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(270px, 1fr));
            gap: 0.9rem;
        }
        .item-box {
            background: rgba(15, 23, 42, 0.65);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 0.9rem 1rem;
            min-width: 0;
        }
        label.ctrl-label {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            font-weight: 600;
            font-size: 0.9rem;
        }
        .desc-small {
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 0.35rem;
        }
        .btn {
            background: var(--accent);
            color: #0B0F19;
            border: none;
            padding: 0.6rem 1.15rem;
            border-radius: 8px;
            font-weight: 700;
            font-size: 0.88rem;
            cursor: pointer;
            white-space: nowrap;
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
        }
        .btn.secondary {
            background: rgba(255,255,255,0.05);
            color: var(--text-main);
            border: 1px solid var(--border);
        }
        .btn.danger {
            background: var(--danger);
            color: #fff;
        }
        .btn.cta {
            background: var(--success);
            color: #052e16;
            font-size: 1rem;
            padding: 0.85rem 1.8rem;
        }
        select {
            background: var(--bg-primary);
            color: var(--text-main);
            border: 1px solid var(--border);
            padding: 0.55rem 0.9rem;
            border-radius: 8px;
            font-size: 0.9rem;
        }
        #progress-modal {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(11, 15, 25, 0.88);
            z-index: 999;
            align-items: center;
            justify-content: center;
            padding: 1.5rem;
        }
        .modal-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            max-width: 720px;
            width: 100%;
            padding: 1.75rem;
        }
        .bar-bg {
            background: #0B0F19;
            height: 14px;
            border-radius: 999px;
            overflow: hidden;
            margin: 1rem 0;
        }
        .bar-fill {
            background: var(--accent);
            height: 100%;
            width: 0%;
            transition: width 0.25s ease;
        }
    </style>
</head>
<body>
    <header>
        <div class="title-group">
            <h1>
                🚀 Limpeza & Otimização Desktop Multiplataforma
                <span class="pill" id="os-badge">Detectando SO...</span>
                <span class="pill" id="priv-badge">Privilégio</span>
            </h1>
            <p style="font-size:0.84rem;color:var(--text-muted);margin-top:0.2rem;">
                Política Zero-Network • Nenhum dado sai da sua máquina • Catálogo WinUtil Sanitizado & macOS Nativo
            </p>
        </div>
        <div style="display:flex;gap:0.75rem;align-items:center;">
            <label for="os-selector" style="font-size:0.85rem;color:var(--text-muted);">Plataforma / Catálogo:</label>
            <select id="os-selector" onchange="loadContext(this.value)">
                <option value="windows">🪟 Windows (10 / 11)</option>
                <option value="macos">🍎 macOS (Apple Silicon / Intel)</option>
            </select>
        </div>
    </header>

    <div class="container">
        <!-- PARTIÇÕES E MODO DE OPERAÇÃO -->
        <div class="section-card">
            <div class="section-header">
                <h2>1. Ambiente, Partições Detectadas & Modo de Execução</h2>
                <span class="pill" id="ram-badge">RAM</span>
            </div>
            <div class="grid-3" id="partitions-list" style="margin-bottom:1.1rem;"></div>
            <div class="grid-2">
                <div class="item-box">
                    <div style="font-weight:700;margin-bottom:0.5rem;">Modo de Operação:</div>
                    <div style="display:flex;flex-direction:column;gap:0.45rem;">
                        <label class="ctrl-label">
                            <input type="radio" name="exec_mode" value="real" checked>
                            <span>Execução Autônoma Real (Limpar & Otimizar Agora)</span>
                        </label>
                        <label class="ctrl-label">
                            <input type="radio" name="exec_mode" value="dry_run">
                            <span>Simulação Segura (Dry-Run / Apenas Diagnóstico)</span>
                        </label>
                    </div>
                </div>
                <div class="item-box">
                    <div style="font-weight:700;margin-bottom:0.5rem;">Escopo da Varredura de Disco:</div>
                    <select id="scan-scope" style="width:100%;">
                        <option value="smart_fast">⚡ Rápida Inteligente (Pastas de Usuário, Caches, Apps e Downloads - Recomendado)</option>
                        <option value="full_disks">💽 Completa em Todos os Discos Montados</option>
                        <option value="appdata_library">📂 Apenas AppData (Windows) / ~/Library (macOS)</option>
                    </select>
                    <p class="desc-small">Usa algoritmo de 5 Camadas Anti-Falsos Positivos para proteger todos os seus softwares instalados.</p>
                </div>
            </div>
        </div>

        <!-- MÓDULO 1: LIMPEZA AUTÔNOMA -->
        <div class="section-card">
            <div class="section-header">
                <h2>2. Módulo 1: Limpeza Autônoma de Espaço</h2>
                <label class="ctrl-label" style="color:var(--warning);">
                    <input type="checkbox" id="auto-clean-orphans">
                    <span>Auto-remover Pastas Órfãs Verificadas (5 Camadas)</span>
                </label>
            </div>
            <div class="grid-3" id="cleanup-rules-grid"></div>
        </div>

        <!-- MÓDULO 2: OTIMIZAÇÃO DO SISTEMA (TWEAKS) -->
        <div class="section-card">
            <div class="section-header">
                <h2>3. Módulo 2: Otimização do Sistema (WinUtil Sanitizado / macOS Tweaks)</h2>
                <div style="display:flex;gap:0.5rem;flex-wrap:wrap;">
                    <button class="btn secondary" onclick="applyPreset('standard')">⭐ Preset Padrão Recomendado</button>
                    <button class="btn secondary" onclick="applyPreset('minimal')">🛡️ Mínimo Seguro</button>
                    <button class="btn secondary" onclick="applyPreset('advanced')">⚡ Avançado</button>
                    <button class="btn secondary" onclick="applyPreset('none')">Desmarcar Todos</button>
                    <button class="btn danger" onclick="triggerUndo()">⏪ Reverter Otimizações Anteriores (Undo)</button>
                </div>
            </div>
            <div class="grid-3" id="tweaks-grid"></div>
        </div>

        <!-- MÓDULO 3: RADAR DE ARQUIVOS GIGANTES, APPS & NUVEM -->
        <div class="section-card">
            <div class="section-header">
                <h2>4. Módulo 3: Radar de Arquivos Gigantes, Aplicativos & Nuvem</h2>
            </div>
            <div class="grid-3">
                <div class="item-box">
                    <label class="ctrl-label">
                        <input type="checkbox" id="run-disk-scan" checked>
                        <span>Mapear Top 100 Arquivos Gigantes, Pastas Órfãs & Apps por Tamanho</span>
                    </label>
                    <p class="desc-small">Identifica quais aplicativos comem mais espaço e lista resíduos de programas já desinstalados.</p>
                </div>
                <div class="item-box">
                    <label class="ctrl-label">
                        <input type="checkbox" id="run-cloud-diag" checked>
                        <span>Diagnosticar Espaço Físico do OneDrive / iCloud Drive</span>
                    </label>
                    <p class="desc-small">Mede espaço local retido por sincronização em nuvem e mostra como liberar sem apagar arquivos online.</p>
                </div>
                <div class="item-box">
                    <label class="ctrl-label">
                        <input type="checkbox" id="check-updates">
                        <span>Consultar atualizações de softwares (winget / brew) [Opt-In]</span>
                    </label>
                    <p class="desc-small">Opcional: consulta o gerenciador oficial da máquina por versões novas de pacotes instalados.</p>
                </div>
            </div>
        </div>

        <div style="display:flex;justify-content:flex-end;align-items:center;gap:1rem;margin-top:1.5rem;">
            <span id="status-inline" style="color:var(--text-muted);font-size:0.9rem;"></span>
            <button class="btn cta" onclick="startExecution()">🚀 Iniciar Limpeza & Otimização</button>
        </div>
    </div>

    <!-- MODAL DE PROGRESSO EM TEMPO REAL -->
    <div id="progress-modal">
        <div class="modal-card">
            <h2 id="prog-step">Executando Limpeza & Otimização...</h2>
            <div class="bar-bg"><div class="bar-fill" id="prog-bar"></div></div>
            <div style="display:flex;justify-content:space-between;font-size:0.85rem;color:var(--text-muted);margin-bottom:0.75rem;">
                <span id="prog-pct">0%</span>
                <span>Processamento 100% Local</span>
            </div>
            <pre id="prog-logs" style="background:#0B0F19;padding:1rem;border-radius:10px;height:210px;overflow-y:auto;font-size:0.78rem;color:#94A3B8;white-space:pre-wrap;"></pre>
        </div>
    </div>

    <script>
        let CURRENT_CTX = null;

        function escapeHtml(value) {
            if (value === null || value === undefined) return '';
            return String(value)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        async function loadContext(osOverride) {
            const url = osOverride ? `/api/context?os=${encodeURIComponent(osOverride)}` : '/api/context';
            const res = await fetch(url);
            CURRENT_CTX = await res.json();

            document.getElementById('os-selector').value = CURRENT_CTX.selected_os;
            document.getElementById('os-badge').textContent = CURRENT_CTX.os_version;
            document.getElementById('priv-badge').textContent = CURRENT_CTX.is_admin ? '🔓 Admin / Root Ativo' : '👤 Usuário Padrão';
            const ramGb = (CURRENT_CTX.total_ram_kb / (1024 * 1024)).toFixed(1);
            document.getElementById('ram-badge').textContent = `RAM Física: ${ramGb} GB`;

            document.getElementById('partitions-list').innerHTML = (CURRENT_CTX.partitions || []).map(p => `
                <div class="item-box">
                    <div style="display:flex;justify-content:space-between;white-space:nowrap;">
                        <strong>💽 ${escapeHtml(p.drive_letter)}</strong>
                        <span class="pill">${escapeHtml(p.percent_used)}% usado</span>
                    </div>
                    <div class="desc-small">Livre: <strong>${escapeHtml(p.free_formatted)}</strong> de ${escapeHtml(p.total_formatted)} (${escapeHtml(p.health_status)})</div>
                </div>
            `).join('');

            document.getElementById('cleanup-rules-grid').innerHTML = (CURRENT_CTX.cleanup_rules || []).map(r => `
                <div class="item-box">
                    <label class="ctrl-label">
                        <input type="checkbox" class="rule-cb" value="${escapeHtml(r.id)}" ${r.default_enabled ? 'checked' : ''}>
                        <span>${escapeHtml(r.name)}</span>
                    </label>
                    <p class="desc-small">${escapeHtml(r.description)}</p>
                </div>
            `).join('');

            renderTweaksGrid('standard');
        }

        function renderTweaksGrid(presetMode) {
            const tweaks = CURRENT_CTX ? (CURRENT_CTX.tweaks || []) : [];
            document.getElementById('tweaks-grid').innerHTML = tweaks.map(t => {
                let checked = false;
                if (presetMode === 'minimal') checked = t.preset === 'minimal';
                else if (presetMode === 'standard') checked = (t.preset === 'minimal' || t.preset === 'standard');
                else if (presetMode === 'advanced') checked = (t.preset !== 'fixes');
                return `
                    <div class="item-box">
                        <label class="ctrl-label">
                            <input type="checkbox" class="tweak-cb" value="${escapeHtml(t.id)}" ${checked ? 'checked' : ''}>
                            <span>${escapeHtml(t.name)}</span>
                        </label>
                        <div style="margin-top:0.3rem;">
                            <span class="pill" style="font-size:0.68rem;">${escapeHtml(t.category)}</span>
                        </div>
                        <p class="desc-small">${escapeHtml(t.description)}</p>
                    </div>
                `;
            }).join('');
        }

        function applyPreset(preset) {
            renderTweaksGrid(preset);
        }

        async function triggerUndo() {
            const res = await fetch('/api/undo', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({snapshot_id: 'latest', mode: 'real'})
            });
            const data = await res.json();
            document.getElementById('status-inline').textContent = data.message || 'Undo processado.';
        }

        async function startExecution() {
            const mode = document.querySelector('input[name="exec_mode"]:checked').value;
            const payload = {
                os_platform: document.getElementById('os-selector').value,
                mode: mode,
                scan_scope: document.getElementById('scan-scope').value,
                selected_cleanup_rule_ids: Array.from(document.querySelectorAll('.rule-cb:checked')).map(el => el.value),
                auto_clean_orphans: document.getElementById('auto-clean-orphans').checked,
                selected_tweak_ids: Array.from(document.querySelectorAll('.tweak-cb:checked')).map(el => el.value),
                run_disk_scan: document.getElementById('run-disk-scan').checked,
                run_cloud_diagnostic: document.getElementById('run-cloud-diag').checked,
                check_updates: document.getElementById('check-updates').checked
            };

            document.getElementById('progress-modal').style.display = 'flex';
            await fetch('/api/execute', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });

            const timer = setInterval(async () => {
                const stRes = await fetch('/api/status');
                const st = await stRes.json();
                document.getElementById('prog-bar').style.width = `${st.percent || 0}%`;
                document.getElementById('prog-pct').textContent = `${st.percent || 0}%`;
                document.getElementById('prog-step').textContent = st.step || 'Processando...';
                document.getElementById('prog-logs').textContent = (st.logs || []).join('\\n');
                if (st.completed) {
                    clearInterval(timer);
                    window.location.href = '/report';
                }
            }, 350);
        }

        document.addEventListener('DOMContentLoaded', () => loadContext());
    </script>
</body>
</html>
"""


class LocalControlPanelServer:
    """Gerencia o servidor HTTP local (127.0.0.1) para a Janela Inicial e Dashboard."""

    def __init__(
        self,
        orchestrator: Optional[OrchestratorService] = None,
        output_report_path: str = "outputs/relatorio_limpeza_disco.html",
    ) -> None:
        self.orchestrator = orchestrator or OrchestratorService()
        self.output_report_path = os.path.abspath(output_report_path)
        self._exec_lock = threading.Lock()
        self.state: Dict[str, Any] = {
            "running": False,
            "completed": False,
            "percent": 0,
            "step": "Aguardando início...",
            "logs": [],
            "report_path": self.output_report_path,
        }
        self._httpd: Optional[HTTPServer] = None
        self.port: int = 0

    def _update_progress(self, pct: int, step: str, log_line: str) -> None:
        self.state["percent"] = pct
        self.state["step"] = step
        self.state["logs"].append(log_line)

    def run_plan_sync_or_async(self, payload: Dict[str, Any], background: bool = True) -> bool:
        with self._exec_lock:
            if self.state.get("running"):
                return False
            self.state["running"] = True
            self.state["completed"] = False
            self.state["percent"] = 1
            self.state["step"] = "Iniciando..."
            self.state["logs"] = []

        plan = ExecutionPlanDTO.from_dict(payload if isinstance(payload, dict) else {})

        def worker() -> None:
            try:
                report = self.orchestrator.execute_plan(plan, progress_cb=self._update_progress)
                html_path = generate_html_report(report, output_filename=self.output_report_path)
                self.state["report_path"] = html_path
                self.state["completed"] = True
                print("\n" + "=" * 78)
                print("  EXECUÇÃO CONCLUÍDA COM SUCESSO!")
                print(f"  Espaço Trabalhado (Autônomo): {report.total_bytes_freed_formatted}")
                print(f"  Potencial Adicional Mapeado : {report.potential_extra_bytes_formatted}")
                print(f"  Relatório HTML Offline      : file://{html_path}")
                print(f"  Dashboard Interativo Local  : http://127.0.0.1:{self.port}/report")
                print("=" * 78)
            finally:
                with self._exec_lock:
                    self.state["running"] = False

        if background:
            t = threading.Thread(target=worker, daemon=True)
            t.start()
        else:
            worker()
        return True

    def dispatch_request(
        self,
        method: str,
        raw_path: str,
        payload: Optional[Dict[str, Any]] = None,
        background_exec: bool = True,
    ) -> Tuple[int, str, Any]:
        """
        Despacha requisições da API local (127.0.0.1).
        Retorna (status_code, content_type, body_str_or_dict).
        """
        parsed = urlparse(raw_path)
        payload = payload if isinstance(payload, dict) else {}

        if method.upper() == "GET":
            if parsed.path == "/":
                return 200, "text/html; charset=utf-8", LAUNCHER_HTML

            if parsed.path == "/api/context":
                qs = parse_qs(parsed.query)
                os_param = qs.get("os", [None])[0]
                target_os = None
                if os_param == "windows":
                    target_os = OSPlatform.WINDOWS
                elif os_param == "macos":
                    target_os = OSPlatform.MACOS
                ctx = self.orchestrator.get_initial_context(target_os)
                return 200, "application/json; charset=utf-8", ctx

            if parsed.path == "/api/status":
                return 200, "application/json; charset=utf-8", self.state

            if parsed.path == "/report":
                if not os.path.exists(self.output_report_path):
                    if self.orchestrator.last_report:
                        generate_html_report(
                            self.orchestrator.last_report,
                            output_filename=self.output_report_path,
                        )
                    else:
                        default_plan = self.orchestrator.build_default_plan()
                        rep = self.orchestrator.execute_plan(default_plan)
                        generate_html_report(rep, output_filename=self.output_report_path)
                with open(self.output_report_path, "r", encoding="utf-8") as f:
                    return 200, "text/html; charset=utf-8", f.read()

            return 404, "application/json; charset=utf-8", {"error": "Not found"}

        if method.upper() == "POST":
            if parsed.path == "/api/execute":
                started = self.run_plan_sync_or_async(payload, background=background_exec)
                return (
                    200,
                    "application/json; charset=utf-8",
                    {"started": started, "already_running": not started},
                )

            if parsed.path == "/api/clean-selected":
                raw_paths = payload.get("paths", [])
                paths = [str(p) for p in raw_paths if isinstance(p, str)] if isinstance(raw_paths, list) else []
                mode_str = str(payload.get("mode", "real")).lower()
                mode = ExecutionMode.REAL if mode_str == "real" else ExecutionMode.DRY_RUN
                entry = self.orchestrator.clean_selected_items(paths, mode=mode)
                if self.orchestrator.last_report:
                    generate_html_report(
                        self.orchestrator.last_report,
                        output_filename=self.output_report_path,
                    )
                last_rep = self.orchestrator.last_report
                return (
                    200,
                    "application/json; charset=utf-8",
                    {
                        "status": "ok",
                        "success": True,
                        "bytes_freed": entry.bytes_freed,
                        "bytes_freed_formatted": entry.bytes_freed_formatted,
                        "files_removed": entry.files_removed,
                        "cleaned_paths": entry.target_paths,
                        "errors_skipped": entry.errors_skipped,
                        "message": entry.details,
                        "total_freed_formatted": last_rep.total_bytes_freed_formatted if last_rep else "0.00 B",
                        "potential_extra_formatted": last_rep.potential_extra_bytes_formatted if last_rep else "0.00 B",
                        "remaining_orphans_count": len(last_rep.clean_suggestions) if last_rep else 0,
                    },
                )

            if parsed.path == "/api/reanalyze":
                report = self.orchestrator.reanalyze(progress_cb=self._update_progress)
                generate_html_report(report, output_filename=self.output_report_path)
                return (
                    200,
                    "application/json; charset=utf-8",
                    {
                        "status": "ok",
                        "success": True,
                        "message": "Reanálise concluída com sucesso! Métricas e lista de itens atualizadas.",
                        "report": report.to_dict(),
                    },
                )

            if parsed.path == "/api/undo":
                raw_snap_id = payload.get("snapshot_id", "latest")
                snap_id = str(raw_snap_id) if isinstance(raw_snap_id, str) else "latest"
                mode_str = str(payload.get("mode", "real")).lower()
                mode = ExecutionMode.REAL if mode_str == "real" else ExecutionMode.DRY_RUN
                records = self.orchestrator.revert_snapshot(snap_id, mode=mode)
                return (
                    200,
                    "application/json; charset=utf-8",
                    {
                        "success": True,
                        "reverted_count": len(records),
                        "message": (
                            f"Reversão (Undo) concluída: {len(records)} tweaks restaurados ao estado original."
                            if records
                            else "Nenhum snapshot encontrado para reverter."
                        ),
                    },
                )

        return 404, "application/json; charset=utf-8", {"error": "Not found"}

    def create_server(self, port: int = 0) -> Tuple[HTTPServer, int]:
        panel = self

        class RequestHandler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                pass

            def _write_response(self, status: int, content_type: str, body: Any) -> None:
                if isinstance(body, (dict, list)):
                    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
                else:
                    raw = str(body).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self) -> None:
                status, ctype, body = panel.dispatch_request("GET", self.path)
                self._write_response(status, ctype, body)

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                raw_body = self.rfile.read(length).decode("utf-8", errors="ignore") if length > 0 else "{}"
                try:
                    parsed_json = json.loads(raw_body)
                    payload = parsed_json if isinstance(parsed_json, dict) else {}
                except json.JSONDecodeError:
                    payload = {}
                status, ctype, body = panel.dispatch_request("POST", self.path, payload=payload)
                self._write_response(status, ctype, body)

        httpd = HTTPServer(("127.0.0.1", port), RequestHandler)
        self._httpd = httpd
        self.port = httpd.server_port
        return httpd, self.port

    def start_interactive(self, open_browser: bool = True) -> None:
        httpd, port = self.create_server(port=0)
        url = f"http://127.0.0.1:{port}/"
        print("=" * 78)
        print("  LIMPEZA & OTIMIZAÇÃO DESKTOP MULTIPLATAFORMA (WINDOWS & MACOS)")
        print("=" * 78)
        print(f"  [Janela de Navegação & Configuração]: {url}")
        print("  [Privacidade]: Servidor estritamente local (127.0.0.1) — Zero-Network")
        print("  Pressione Ctrl+C no terminal a qualquer momento para encerrar.")
        print("=" * 78)
        if open_browser:
            try:
                webbrowser.open(url)
            except Exception:
                pass
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[Encerrado pelo usuário]")
        finally:
            httpd.server_close()
