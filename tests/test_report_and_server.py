# -*- coding: utf-8 -*-
"""Testes de geração do Relatório HTML Offline e das rotas do Servidor Local (127.0.0.1)."""
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from src.domain.value_objects import ExecutionMode, OSPlatform
from src.domain.entities import (
    HardwareHealthInfo,
    StorageDiskHealth,
    MemoryDiagnostics,
    BatteryHealth,
    StartupItemInfo,
    ProcessDiagnosticInfo,
    LongevityScoreReport,
)
from src.application.orchestrator import OrchestratorService
from src.infrastructure.persistence.snapshot_repository import SnapshotRepository
from src.presentation.reporters.html_reporter import generate_html_report
from src.presentation.window.local_server import LocalControlPanelServer


class TestReportAndLocalServer(unittest.TestCase):
    """Valida a geração do relatório HTML de 8 abas, ganchos interativos e rotas da API local."""

    def test_generate_html_report_and_local_api_routes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            snap_repo = SnapshotRepository(snapshots_dir=os.path.join(tmpdir, "snapshots"))
            orchestrator = OrchestratorService(snapshot_repo=snap_repo)
            plan = orchestrator.build_default_plan(
                os_platform=OSPlatform.detect_current(),
                mode=ExecutionMode.DRY_RUN,
                preset="minimal",
            )
            plan.run_disk_scan = False
            plan.run_cloud_diagnostic = False
            report = orchestrator.execute_plan(plan)

            out_html = os.path.join(tmpdir, "relatorio_limpeza_disco.html")
            generated_path = generate_html_report(report, output_filename=out_html)
            self.assertTrue(os.path.exists(generated_path))

            with open(generated_path, "r", encoding="utf-8") as f:
                html_text = f.read()

            # Verifica presença das 8 abas e novos controles de navegação e reanálise
            self.assertIn("1. Resumo & Saúde dos Discos", html_text)
            self.assertIn("2. Limpeza Autônoma Executada", html_text)
            self.assertIn("3. Aplicativos Grandes & Migração", html_text)
            self.assertIn("4. Pastas Órfãs & Caches Detectados", html_text)
            self.assertIn("5. Top 100 Maiores Arquivos & Pastas", html_text)
            self.assertIn("6. Otimizações do Sistema (WinUtil / macOS)", html_text)
            self.assertIn("7. Cloud (OneDrive / iCloud) & Updates", html_text)
            self.assertIn("8. Saúde de Hardware & Otimização de Storage", html_text)
            self.assertIn("Nova Configuração / Início", html_text)
            self.assertIn("href=\"/\"", html_text)
            self.assertIn("Reanalisar Sistema", html_text)
            self.assertIn("triggerReanalyze()", html_text)
            self.assertIn("btn-expand-sub", html_text)
            self.assertIn("subfolder-container", html_text)
            self.assertIn("longevity-score-num", html_text)
            self.assertIn("refreshLiveHealth()", html_text)

            # Testa todas as rotas da API local (127.0.0.1)
            panel = LocalControlPanelServer(
                orchestrator=orchestrator,
                output_report_path=out_html,
            )

            # GET /
            status, _, body = panel.dispatch_request("GET", "/")
            self.assertEqual(status, 200)
            self.assertIn("Iniciar Limpeza & Otimização", body)

            # GET /api/context?os=windows
            status, _, ctx_win = panel.dispatch_request("GET", "/api/context?os=windows")
            self.assertEqual(status, 200)
            self.assertEqual(ctx_win["selected_os"], "windows")
            self.assertGreaterEqual(len(ctx_win["tweaks"]), 24)

            # GET /api/context?os=macos
            status, _, ctx_mac = panel.dispatch_request("GET", "/api/context?os=macos")
            self.assertEqual(status, 200)
            self.assertEqual(ctx_mac["selected_os"], "macos")
            self.assertEqual(len(ctx_mac["tweaks"]), 9)

            # POST /api/clean-selected (dry_run)
            dummy_dir = os.path.join(tmpdir, "cache_item")
            os.makedirs(dummy_dir, exist_ok=True)
            with open(os.path.join(dummy_dir, "a.tmp"), "wb") as fp:
                fp.write(b"1234567890")
            status, _, clean_res = panel.dispatch_request(
                "POST",
                "/api/clean-selected",
                payload={"paths": [dummy_dir], "mode": "dry_run"},
            )
            self.assertEqual(status, 200)
            self.assertTrue(clean_res["success"])
            self.assertEqual(clean_res["bytes_freed"], 10)

            # POST /api/clean-selected (real) com retorno enriquecido e reatividade
            status, _, clean_res_real = panel.dispatch_request(
                "POST",
                "/api/clean-selected",
                payload={"paths": [dummy_dir], "mode": "real"},
            )
            self.assertEqual(status, 200)
            self.assertTrue(clean_res_real["success"])
            self.assertIn(dummy_dir, clean_res_real["cleaned_paths"])
            self.assertIn("total_freed_formatted", clean_res_real)
            self.assertIn("potential_extra_formatted", clean_res_real)
            self.assertIn("remaining_orphans_count", clean_res_real)

            # POST /api/reanalyze
            status, _, reanalyze_res = panel.dispatch_request(
                "POST",
                "/api/reanalyze",
            )
            self.assertEqual(status, 200)
            self.assertEqual(reanalyze_res["status"], "ok")
            self.assertIn("report", reanalyze_res)
            self.assertEqual(reanalyze_res["report"]["execution_mode"], "dry_run")

            # POST /api/undo (dry_run)
            status, _, undo_res = panel.dispatch_request(
                "POST",
                "/api/undo",
                payload={"snapshot_id": "latest", "mode": "dry_run"},
            )
            self.assertEqual(status, 200)
            self.assertTrue(undo_res["success"])

            # GET /report
            status, _, rep_body = panel.dispatch_request("GET", "/report")
            self.assertEqual(status, 200)
            self.assertIn("REPORT_DATA", rep_body)

    def test_interactive_file_action_and_guardrails(self) -> None:
        """Testa o endpoint POST /api/file-action (trash e delete) e guardrails de segurança."""
        with tempfile.TemporaryDirectory() as tmpdir:
            snap_repo = SnapshotRepository(snapshots_dir=os.path.join(tmpdir, "snapshots"))
            orchestrator = OrchestratorService(snapshot_repo=snap_repo)
            panel = LocalControlPanelServer(
                orchestrator=orchestrator,
                output_report_path=os.path.join(tmpdir, "report.html"),
            )

            # 1. Cria um arquivo alvo de teste seguro
            safe_target = os.path.join(tmpdir, "test_file.txt")
            with open(safe_target, "w", encoding="utf-8") as f:
                f.write("Hello World 12345")

            # Executa ação "trash" em modo dry_run
            status, _, res_dry = panel.dispatch_request(
                "POST",
                "/api/file-action",
                payload={"paths": [safe_target], "action": "trash", "mode": "dry_run"},
            )
            self.assertEqual(status, 200)
            self.assertTrue(res_dry["success"])
            self.assertEqual(res_dry["status"], "simulated")
            self.assertTrue(os.path.exists(safe_target))

            # Executa ação "delete" em modo real
            status, _, res_del = panel.dispatch_request(
                "POST",
                "/api/file-action",
                payload={"paths": [safe_target], "action": "delete", "mode": "real"},
            )
            self.assertEqual(status, 200)
            self.assertTrue(res_del["success"])
            self.assertEqual(res_del["status"], "cleaned")
            self.assertFalse(os.path.exists(safe_target))

            # 2. Guardrail: Tentativa de apagar caminho crítico proibido pelo SO deve retornar 403 Forbidden
            protected_path = "/System" if os.name != "nt" else "C:\\Windows"
            status, _, res_forbid = panel.dispatch_request(
                "POST",
                "/api/file-action",
                payload={"paths": [protected_path], "action": "delete", "mode": "real"},
            )
            self.assertEqual(status, 403)
            self.assertEqual(res_forbid["status"], "forbidden")

    def test_interactive_reveal_and_execute_rule(self) -> None:
        """Testa POST /api/reveal-path e POST /api/execute-rule."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = OrchestratorService()
            panel = LocalControlPanelServer(
                orchestrator=orchestrator,
                output_report_path=os.path.join(tmpdir, "report.html"),
            )

            # Reveal com caminho seguro existente (usando patch para evitar abrir GUI durante teste)
            sample_file = os.path.join(tmpdir, "sample.log")
            with open(sample_file, "w") as f:
                f.write("test")

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                status, _, res_reveal = panel.dispatch_request(
                    "POST",
                    "/api/reveal-path",
                    payload={"path": sample_file},
                )
                self.assertEqual(status, 200)
                self.assertEqual(res_reveal["status"], "ok")

            # Reveal com injeção de parâmetros (iniciado com -) -> 400 Bad Request
            status, _, res_bad = panel.dispatch_request(
                "POST",
                "/api/reveal-path",
                payload={"path": "--malicious-flag"},
            )
            self.assertEqual(status, 400)

            # Execute-rule com regra conhecida em dry_run
            rule_id = "mac_system_temp" if os.name != "nt" else "win_system_temp"
            status, _, res_rule = panel.dispatch_request(
                "POST",
                "/api/execute-rule",
                payload={"rule_id": rule_id, "mode": "dry_run"},
            )
            self.assertEqual(status, 200)
            self.assertEqual(res_rule["status"], "ok")
            self.assertIn("entry", res_rule)

            # Execute-rule com regra inexistente -> 404
            status, _, res_notfound = panel.dispatch_request(
                "POST",
                "/api/execute-rule",
                payload={"rule_id": "non_existent_rule_9999", "mode": "dry_run"},
            )
            self.assertEqual(status, 404)

    def test_interactive_hardware_startup_and_process_endpoints(self) -> None:
        """Testa GET /api/live-health, POST /api/startup-action, POST /api/process-action e POST /api/upgrade-packages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = OrchestratorService()
            panel = LocalControlPanelServer(
                orchestrator=orchestrator,
                output_report_path=os.path.join(tmpdir, "report.html"),
            )

            # GET /api/live-health
            status, _, res_health = panel.dispatch_request("GET", "/api/live-health")
            self.assertEqual(status, 200)
            self.assertEqual(res_health["status"], "ok")
            self.assertIn("hardware_health", res_health)
            self.assertIn("disks", res_health["hardware_health"])

            # POST /api/startup-action com payload vazio -> 400
            status, _, res_bad_start = panel.dispatch_request(
                "POST",
                "/api/startup-action",
                payload={},
            )
            self.assertEqual(status, 400)

            # POST /api/process-action com PID <= 100 -> bloqueado (400)
            status, _, res_pid_low = panel.dispatch_request(
                "POST",
                "/api/process-action",
                payload={"pid": 1, "action": "terminate"},
            )
            self.assertEqual(status, 400)
            self.assertIn("PID protegido", res_pid_low["message"])

            # POST /api/upgrade-packages com mock de upgrade_package
            with patch.object(orchestrator, "execute_upgrade_packages", return_value={"status": "ok", "message": "Updated"}):
                status, _, res_pkg = panel.dispatch_request(
                    "POST",
                    "/api/upgrade-packages",
                    payload={"package_id": "__all__"},
                )
                self.assertEqual(status, 200)
                self.assertEqual(res_pkg["status"], "ok")

    def test_longevity_score_calculation_logic(self) -> None:
        """Testa o cálculo do Score de Longevidade (0-100) em 4 pilares no OrchestratorService."""
        orchestrator = OrchestratorService()

        # Cenário 1: Hardware Saudável
        hw_healthy = HardwareHealthInfo(
            disks=[
                StorageDiskHealth(
                    device_id="disk0",
                    name="Macintosh HD",
                    media_type="Apple Fabric SSD",
                    bus_type="Apple Fabric",
                    smart_status="Verified",
                    trim_supported=True,
                    is_ssd=True,
                    is_nvme=True,
                    total_bytes=1000 * 1024 * 1024 * 1024,
                    free_bytes=500 * 1024 * 1024 * 1024,  # 50% livre
                    purgeable_bytes=5 * 1024 * 1024 * 1024,
                    apfs_snapshots_count=1,
                )
            ],
            memory=MemoryDiagnostics(
                total_bytes=16 * 1024 * 1024 * 1024,
                used_bytes=8 * 1024 * 1024 * 1024,
                free_bytes=8 * 1024 * 1024 * 1024,
                load_percentage=50.0,
                pressure_level="Normal",
                swap_total_bytes=1024 * 1024 * 1024,
                swap_used_bytes=0,
                swap_thrashing_detected=False,
            ),
            battery=BatteryHealth(
                has_battery=True,
                cycle_count=120,
                health_percentage=98.0,
                condition="Normal",
                temperature_celsius=29.5,
            ),
            startup_items=[],
            top_processes=[],
        )

        score_rep = orchestrator.calculate_longevity_score(hw_healthy, clean_suggestions=[])
        self.assertIsInstance(score_rep, LongevityScoreReport)
        self.assertGreaterEqual(score_rep.total_score, 85)
        self.assertIn("Excelente", score_rep.grade_label)
        self.assertEqual(score_rep.storage_score, 35)
        self.assertEqual(score_rep.memory_score, 25)
        self.assertEqual(score_rep.hygiene_score, 20)
        self.assertEqual(score_rep.thermal_battery_score, 20)

        # Cenário 2: Hardware sob estresse crítico (Disco cheio, Swap thrashing, Temperatura alta, Órfãos)
        hw_critical = HardwareHealthInfo(
            disks=[
                StorageDiskHealth(
                    device_id="disk0",
                    name="Macintosh HD",
                    media_type="Apple Fabric SSD",
                    bus_type="Apple Fabric",
                    smart_status="Verified",
                    trim_supported=True,
                    is_ssd=True,
                    is_nvme=True,
                    total_bytes=1000 * 1024 * 1024 * 1024,
                    free_bytes=30 * 1024 * 1024 * 1024,  # Apenas 3% livre (> 95% usado)
                    purgeable_bytes=45 * 1024 * 1024 * 1024,
                    apfs_snapshots_count=12,
                )
            ],
            memory=MemoryDiagnostics(
                total_bytes=16 * 1024 * 1024 * 1024,
                used_bytes=15 * 1024 * 1024 * 1024,
                free_bytes=1 * 1024 * 1024 * 1024,
                load_percentage=95.0,
                pressure_level="Crítica",
                swap_total_bytes=16 * 1024 * 1024 * 1024,
                swap_used_bytes=12 * 1024 * 1024 * 1024,
                swap_thrashing_detected=True,
            ),
            battery=BatteryHealth(
                has_battery=True,
                cycle_count=950,
                health_percentage=72.0,
                condition="Service Recommended",
                temperature_celsius=46.0,
            ),
            startup_items=[
                StartupItemInfo(
                    name="com.test.orphan",
                    path="/Library/LaunchAgents/com.test.orphan.plist",
                    scope="user_launch_agent",
                    is_orphan=True,
                )
            ],
            top_processes=[
                ProcessDiagnosticInfo(
                    pid=1234,
                    name="zombie_worker",
                    cpu_percent=0.0,
                    memory_mb=10.0,
                    state="Z",
                    is_zombie=True,
                )
            ],
        )

        score_crit = orchestrator.calculate_longevity_score(hw_critical, clean_suggestions=[])
        self.assertLess(score_crit.total_score, 65)
        self.assertIn(score_crit.grade_label, ("Atenção Preventiva (55-74)", "Crítico / Risco de Degradação (<55)", "Bom / Saudável (75-89)"))
        self.assertGreater(len(score_crit.recommendations), 2)

        # Valida que as recomendações cobrem os pilares afetados
        pilares = [r.pilar for r in score_crit.recommendations]
        self.assertIn("storage_nand", pilares)
        self.assertIn("memory_swap", pilares)
        self.assertIn("battery_thermal", pilares)


if __name__ == "__main__":
    unittest.main()

