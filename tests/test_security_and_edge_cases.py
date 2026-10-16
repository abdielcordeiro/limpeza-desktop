# -*- coding: utf-8 -*-
"""Testes de Segurança, Path Traversal, Proteção de Raízes e Casos de Borda."""
import os
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
