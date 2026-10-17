# -*- coding: utf-8 -*-
"""Testes de Segurança, Path Traversal, Proteção de Raízes e Casos de Borda."""
import os
import stat
import tempfile
import unittest
from src.domain.entities import AutonomousCleanupRule
from src.domain.value_objects import ExecutionMode, OSPlatform
from src.infrastructure.filesystem.autonomous_cleaner import (
    is_safe_path_to_clean,
    AutonomousCleanerAdapter,
)
from src.application.orchestrator import OrchestratorService
from src.presentation.window.local_server import LocalControlPanelServer


class TestSecurityAndEdgeCases(unittest.TestCase):
    def setUp(self):
        self.cleaner = AutonomousCleanerAdapter()

    def test_path_safety_blocks_critical_posix_roots(self):
        dangerous_paths = [
            "/",
            "/system",
            "/System",
            "/Library",
            "/Applications",
            "/Users",
            "/bin",
            "/sbin",
            "/usr",
            "/private/etc",
            "/etc",
            "/dev",
            "/proc",
        ]
        for path in dangerous_paths:
            self.assertFalse(
                is_safe_path_to_clean(path),
                f"Caminho crítico POSIX não foi bloqueado: {path}",
            )

    def test_path_safety_blocks_critical_windows_roots(self):
        dangerous_win = [
            "c:",
            "C:",
            "C:\\",
            "C:\\Windows",
            "C:\\Windows\\System32",
            "C:\\Windows\\SysWOW64",
            "C:\\Program Files",
            "C:\\Program Files (x86)",
            "C:\\Users",
            "D:\\",
            "E:",
        ]
        for path in dangerous_win:
            self.assertFalse(
                is_safe_path_to_clean(path),
                f"Caminho crítico Windows não foi bloqueado: {path}",
            )

    def test_path_safety_blocks_path_traversal_and_null_bytes(self):
        traversals = [
            "/Users/test/Library/Caches/../../etc/passwd",
            "C:\\temp\\..\\Windows\\System32",
            "../etc/shadow",
            "folder/../../root",
            "/tmp/test\x00evil",
            "",
            None,
        ]
        for path in traversals:
            self.assertFalse(
                is_safe_path_to_clean(path),
                f"Tentativa de Traversal/Null byte não foi bloqueada: {path}",
            )

    def test_cleaner_refuses_to_touch_protected_path(self):
        # Mesmo se chamarmos _clean_directory_contents diretamente em um caminho proibido
        bytes_freed, files_removed, errors = self.cleaner._clean_directory_contents(
            "/System", mode=ExecutionMode.REAL
        )
        self.assertEqual(bytes_freed, 0)
        self.assertEqual(files_removed, 0)

    def test_local_server_api_dispatch_security_and_contracts(self):
        orchestrator = OrchestratorService()
        server = LocalControlPanelServer(orchestrator=orchestrator)

        # 1. GET /api/context
        status, ctype, body = server.dispatch_request("GET", "/api/context?os=macos")
        self.assertEqual(status, 200)
        self.assertIn("selected_os", body)

        status_win, _, body_win = server.dispatch_request("GET", "/api/context?os=windows")
        self.assertEqual(status_win, 200)
        self.assertEqual(body_win["selected_os"], "windows")

        # 2. GET /api/status
        status, _, body = server.dispatch_request("GET", "/api/status")
        self.assertEqual(status, 200)
        self.assertIn("running", body)

        # 3. POST /api/clean-selected bloqueia tentativa com caminho crítico
        status, _, res = server.dispatch_request(
            "POST",
            "/api/clean-selected",
            payload={"paths": ["/System", "/etc/passwd", "C:\\Windows\\System32"], "mode": "real"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(res["bytes_freed"], 0)
        self.assertEqual(res["files_removed"], 0)

        # 4. POST /api/undo com snapshot inexistente trata graciosamente
        status, _, undo_res = server.dispatch_request(
            "POST",
            "/api/undo",
            payload={"snapshot_id": "non_existent_snapshot_id", "mode": "dry_run"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(undo_res["reverted_count"], 0)

        # 5. Rota inválida retorna 404
        status, _, _ = server.dispatch_request("GET", "/api/invalid-endpoint")
        self.assertEqual(status, 404)

    def test_trash_rule_isolation_refuses_dangerous_paths(self):
        """Garante que regras de lixeira com caminhos críticos/perigosos sejam bloqueadas e não toquem arquivos fora da lixeira."""
        dangerous_trash_rule = AutonomousCleanupRule(
            id="malicious_custom_trash",
            name="Regra Maliciosa de Lixeira",
            category="trash",
            os_platform="macos",
            description="desc",
            target_paths=["/System", "/etc", "~", "C:\\Windows\\System32"],
        )
        entry = self.cleaner.execute_rule(dangerous_trash_rule, mode=ExecutionMode.REAL)
        self.assertEqual(entry.files_removed, 0)
        self.assertEqual(entry.bytes_freed, 0)
        self.assertEqual(entry.errors_skipped, 1)
        self.assertIn("Nenhum diretório de Lixeira seguro/válido", entry.details)

    def test_dry_run_absolute_guarantee_no_deletions(self):
        """Garante que em modo DRY_RUN nenhum arquivo (normal, somente-leitura ou subpasta) seja apagado."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_sub = os.path.join(tmpdir, "cache_sample")
            os.makedirs(test_sub, exist_ok=True)
            norm_file = os.path.join(test_sub, "norm.log")
            ro_file = os.path.join(test_sub, "locked.bin")
            with open(norm_file, "w") as f:
                f.write("standard log")
            with open(ro_file, "wb") as f:
                f.write(b"M" * 4096)
            os.chmod(ro_file, stat.S_IREAD | stat.S_IRUSR)

            # Executa simulação
            entry = self.cleaner.clean_specific_paths([test_sub], mode=ExecutionMode.DRY_RUN)
            self.assertEqual(entry.status, "simulated")
            self.assertEqual(entry.files_removed, 2)
            self.assertEqual(entry.bytes_freed, len("standard log") + 4096)

            # Verifica que todos os arquivos continuam rigorosamente intactos no disco
            self.assertTrue(os.path.exists(norm_file))
            self.assertTrue(os.path.exists(ro_file))
            with open(norm_file, "r") as f:
                self.assertEqual(f.read(), "standard log")
            self.assertEqual(os.path.getsize(ro_file), 4096)

    def test_symlink_clean_specific_paths_real_mode(self):
        """Garante que a remoção de symlinks apaga apenas o link simbólico sem tocar no arquivo alvo original."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_file = os.path.join(tmpdir, "original_doc.txt")
            with open(target_file, "w") as f:
                f.write("conteudo vital que nao pode ser destruido")

            link_path = os.path.join(tmpdir, "link_to_doc.tmp")
            try:
                os.symlink(target_file, link_path)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks não suportados no ambiente atual")

            entry = self.cleaner.clean_specific_paths([link_path], mode=ExecutionMode.REAL)
            self.assertEqual(entry.status, "cleaned")
            self.assertEqual(entry.files_removed, 1)

            # O symlink foi removido, mas o arquivo de destino original permanece intacto
            self.assertFalse(os.path.islink(link_path))
            self.assertTrue(os.path.exists(target_file))
            with open(target_file, "r") as f:
                self.assertEqual(f.read(), "conteudo vital que nao pode ser destruido")


if __name__ == "__main__":
    unittest.main()
