# -*- coding: utf-8 -*-
"""Testes de geração do Relatório HTML Offline e das rotas do Servidor Local (127.0.0.1)."""
import os
import tempfile
import unittest

from src.domain.value_objects import ExecutionMode, OSPlatform
from src.application.orchestrator import OrchestratorService
from src.presentation.reporters.html_reporter import generate_html_report
from src.presentation.window.local_server import LocalControlPanelServer


class TestReportAndLocalServer(unittest.TestCase):
    """Valida a geração do relatório HTML de 7 abas e as rotas da API local."""

    def test_generate_html_report_and_local_api_routes(self) -> None:
        orchestrator = OrchestratorService()
        plan = orchestrator.build_default_plan(
            os_platform=OSPlatform.detect_current(),
            mode=ExecutionMode.DRY_RUN,
            preset="minimal",
        )
        plan.run_disk_scan = False
        report = orchestrator.execute_plan(plan)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_html = os.path.join(tmpdir, "relatorio_limpeza_disco.html")
            generated_path = generate_html_report(report, output_filename=out_html)
            self.assertTrue(os.path.exists(generated_path))

            with open(generated_path, "r", encoding="utf-8") as f:
                html_text = f.read()

            # Verifica presença das 7 abas obrigatórias e novos controles de navegação e reanálise
            self.assertIn("1. Resumo & Saúde dos Discos", html_text)
            self.assertIn("2. Limpeza Autônoma Executada", html_text)
            self.assertIn("3. Aplicativos Grandes & Migração", html_text)
            self.assertIn("4. Pastas Órfãs & Caches Detectados", html_text)
            self.assertIn("5. Top 100 Maiores Arquivos & Pastas", html_text)
            self.assertIn("6. Otimizações do Sistema (WinUtil / macOS)", html_text)
            self.assertIn("7. Cloud (OneDrive / iCloud) & Updates", html_text)
            self.assertIn("Nova Configuração / Início", html_text)
            self.assertIn("href=\"/\"", html_text)
            self.assertIn("Reanalisar Sistema", html_text)
            self.assertIn("triggerReanalyze()", html_text)
            self.assertIn("btn-expand-sub", html_text)
            self.assertIn("subfolder-container", html_text)

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


if __name__ == "__main__":
    unittest.main()
