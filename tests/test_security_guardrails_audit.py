# -*- coding: utf-8 -*-
"""
Bateria de Testes de Auditoria de Segurança, Guardrails Anti-Deleção e Integridade (Fases 1 a 4).
Valida proteção impenetrável contra:
- Path Traversal ('../', '..\\', null bytes).
- Deleção de raízes e subárvores críticas de sistema no macOS e Windows (C:, D:, /System, /Library, /opt/homebrew, etc.).
- Exclusão ou terminação indevida de processos vitais do SO (PID <= 100, kernel_task, launchd, csrss, etc.).
- Injeção de comandos em /api/upgrade-packages e /api/reveal-path.
- Tentativas de requisição Cross-Origin maliciosa (CSRF via navegador).
"""
import os
import sys
import unittest
import tempfile
from unittest.mock import MagicMock, patch

from src.infrastructure.filesystem.autonomous_cleaner import (
    is_safe_path_to_clean,
    is_protected_macos_cache_path,
    AutonomousCleanerAdapter,
)
from src.application.orchestrator import OrchestratorService
from src.presentation.window.local_server import LocalControlPanelServer
from src.infrastructure.macos.platform_adapter import (
    MacOSCloudAndPackagesAdapter,
    MacOSHardwareProbeAdapter,
)
from src.infrastructure.windows.platform_adapter import (
    WindowsCloudAndPackagesAdapter,
    WindowsHardwareProbeAdapter,
)
from src.domain.value_objects import ExecutionMode


class TestSecurityGuardrailsAudit(unittest.TestCase):
    """Testes exaustivos de segurança e guardrails anti-deleção."""

    def test_path_traversal_detection(self) -> None:
        """Garante que qualquer tentativa de Path Traversal é sumariamente rejeitada."""
        traversal_payloads = [
            "../",
            "..\\",
            "../../System",
            "..\\..\\Windows\\System32",
            "C:\\Windows\\..\\Windows\\System32",
            "/Library/../System/Library",
            "~/Library/Caches/../../Library/Preferences",
            "/tmp/foo/../../etc/shadow",
            "safe_folder/../dangerous",
            "a/b/c/../../../",
            "\x00/System",
            "C:\\Temp\x00\\bad",
            "",
            None,
            12345,
        ]
        for payload in traversal_payloads:
            with self.subTest(payload=payload):
                self.assertFalse(
                    is_safe_path_to_clean(payload),
                    f"Falha de segurança: payload traversal '{payload}' foi considerado seguro!",
                )

    def test_posix_macos_critical_system_roots(self) -> None:
        """Garante que raízes e subárvores vitais do macOS / POSIX jamais são autorizadas para limpeza."""
        forbidden_posix = [
            "/",
            "/system",
            "/System",
            "/System/Library",
            "/System/Volumes/Data",
            "/System/Volumes/Data/System",
            "/library",
            "/Library",
            "/Library/LaunchDaemons",
            "/Library/Frameworks",
            "/Library/Preferences",
            "/Library/Application Support",
            "/Library/Apple",
            "/Library/Extensions",
            "/applications",
            "/Applications",
            "/Applications/Utilities",
            "/Applications/Safari.app",
            "/users",
            "/Users",
            "/bin",
            "/sbin",
            "/usr",
            "/usr/bin",
            "/usr/local",
            "/var",
            "/var/folders",
            "/private",
            "/private/var",
            "/private/etc",
            "/etc",
            "/dev",
            "/proc",
            "/opt",
            "/opt/homebrew",
            "/cores",
        ]
        for p in forbidden_posix:
            with self.subTest(path=p):
                self.assertFalse(
                    is_safe_path_to_clean(p),
                    f"Falha de segurança: caminho crítico macOS/POSIX '{p}' foi considerado seguro!",
                )

    def test_windows_multi_drive_critical_roots(self) -> None:
        """Garante que raízes de sistema Windows em qualquer unidade (C:, D:, E:) jamais são liberadas."""
        forbidden_win = [
            "C:",
            "C:\\",
            "D:",
            "D:\\",
            "E:",
            "E:\\",
            "C:\\Windows",
            "D:\\Windows",
            "C:\\Windows\\System32",
            "D:\\Windows\\System32",
            "C:\\Windows\\SysWOW64",
            "C:\\Windows\\WinSxS",
            "C:\\Windows\\Boot",
            "C:\\Program Files",
            "D:\\Program Files",
            "C:\\Program Files\\Common Files",
            "D:\\Program Files\\App",
            "C:\\Program Files (x86)",
            "D:\\Program Files (x86)",
            "C:\\System Volume Information",
            "D:\\System Volume Information",
            "E:\\System Volume Information",
            "C:\\Recovery",
            "D:\\Recovery",
            "C:\\Boot",
            "C:\\$Recycle.Bin",
            "D:\\$Recycle.Bin",
            "C:\\Users",
            "D:\\Users",
            "C:\\Users\\Administrator",
            "D:\\Users\\John",
            "C:\\Users\\John\\Desktop",
            "C:\\Users\\John\\Documents",
            "C:\\Users\\John\\AppData",
            "C:\\Users\\John\\AppData\\Local",
            "C:\\Users\\John\\AppData\\Roaming",
            "C:\\ProgramData",
            "D:\\ProgramData",
        ]
        for p in forbidden_win:
            with self.subTest(path=p):
                self.assertFalse(
                    is_safe_path_to_clean(p),
                    f"Falha de segurança: caminho crítico Windows '{p}' foi considerado seguro!",
                )

    def test_allowed_windows_temp_subtrees(self) -> None:
        """Garante que apenas subpastas temporárias legítimas no Windows são autorizadas."""
        allowed_win = [
            "C:\\Windows\\Temp",
            "D:\\Windows\\Temp",
            "C:\\Windows\\Prefetch",
            "D:\\Windows\\Prefetch",
            "C:\\Windows\\SoftwareDistribution\\Download",
            "D:\\Windows\\SoftwareDistribution\\Download",
            "C:\\Users\\John\\AppData\\Local\\Temp",
            "C:\\ProgramData\\NVIDIA Corporation\\NV_Cache",
        ]
        for p in allowed_win:
            with self.subTest(path=p):
                self.assertTrue(
                    is_safe_path_to_clean(p),
                    f"Falso positivo: subárvore temporária Windows '{p}' deveria ser permitida!",
                )

    def test_macos_cache_state_whitelist_protection(self) -> None:
        """Garante que caches de estado e sincronização do macOS são preservados (ADR-009)."""
        protected_caches = [
            "~/Library/Caches/CloudKit",
            "~/Library/Caches/com.apple.bird",
            "~/Library/Caches/com.apple.cloudd",
            "~/Library/Caches/com.apple.homekit",
            "~/Library/Caches/com.apple.safari.safebrowsing",
            "~/Library/Caches/audiounitcache",
            "~/Library/Caches/com.apple.passkit",
            "~/Library/Caches/com.apple.geoservices",
            "~/Library/Caches/com.apple.keychain",
            "~/Library/Caches/com.apple.accountsd",
        ]
        for target in protected_caches:
            with self.subTest(target=target):
                self.assertTrue(
                    is_protected_macos_cache_path(target),
                    f"Falha de segurança: cache de estado '{target}' deveria estar protegido!",
                )

        cleanable_caches = [
            "~/Library/Caches/Google/Chrome",
            "~/Library/Caches/com.spotify.client",
            "~/Library/Caches/ms-playwright",
            "~/Library/Caches/Homebrew",
        ]
        for target in cleanable_caches:
            with self.subTest(target=target):
                self.assertFalse(
                    is_protected_macos_cache_path(target),
                    f"Falso positivo: cache comum '{target}' não deveria estar na lista protegida!",
                )

    def test_api_file_action_strictly_blocks_unsafe_paths(self) -> None:
        """Valida que POST /api/file-action rejeita sumariamente com 403 caminhos proibidos."""
        panel = LocalControlPanelServer()

        # 1. Caminho de sistema único proibido
        status, _, res = panel.dispatch_request(
            "POST",
            "/api/file-action",
            payload={"paths": ["/System"], "action": "delete"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(res.get("status"), "forbidden")

        # 2. Caminho Windows crítico
        status, _, res = panel.dispatch_request(
            "POST",
            "/api/file-action",
            payload={"paths": ["D:\\Windows\\System32"], "action": "trash"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(res.get("status"), "forbidden")

        # 3. Lote misto contendo um caminho inseguro: DEVE rejeitar o lote inteiro
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            status, _, res = panel.dispatch_request(
                "POST",
                "/api/file-action",
                payload={"paths": [tmp_path, "/etc/shadow"], "action": "trash"},
            )
            self.assertEqual(status, 403)
            self.assertEqual(res.get("status"), "forbidden")
            # Garante que o arquivo seguro NÃO foi alterado/apagado devido à falha do lote
            self.assertTrue(os.path.exists(tmp_path))
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_api_clean_selected_strictly_blocks_unsafe_paths(self) -> None:
        """Valida que POST /api/clean-selected ignora caminhos proibidos sem tocar no sistema."""
        panel = LocalControlPanelServer()
        status, _, res = panel.dispatch_request(
            "POST",
            "/api/clean-selected",
            payload={"paths": ["/Library/LaunchDaemons", "C:\\Windows\\System32"]},
        )
        self.assertEqual(status, 200)
        self.assertEqual(res.get("bytes_freed"), 0)
        self.assertEqual(res.get("files_removed"), 0)
        self.assertEqual(res.get("cleaned_paths"), [])

    def test_api_reveal_path_injection_defense(self) -> None:
        """Valida proteção contra flags maliciosas e injeção em /api/reveal-path."""
        panel = LocalControlPanelServer()

        invalid_targets = [
            "-R",
            "--args",
            "-f",
            "/tmp\x00evil",
            "",
            "   ",
            "/nonexistent/directory/that/does/not/exist/9999",
        ]
        for inv in invalid_targets:
            with self.subTest(target=inv):
                status, _, res = panel.dispatch_request(
                    "POST",
                    "/api/reveal-path",
                    payload={"path": inv},
                )
                self.assertEqual(status, 400)
                self.assertEqual(res.get("status"), "error")

    def test_api_process_action_guardrails(self) -> None:
        """Garante que processos essenciais (PID <= 100) são estritamente protegidos."""
        panel = LocalControlPanelServer()

        protected_pids = [0, 1, 4, 99, 100, -1, "abc"]
        for pid in protected_pids:
            with self.subTest(pid=pid):
                status, _, res = panel.dispatch_request(
                    "POST",
                    "/api/process-action",
                    payload={"pid": pid, "action": "terminate"},
                )
                self.assertEqual(status, 400)
                self.assertEqual(res.get("status"), "error")
                self.assertIn("PID protegido", res.get("message", ""))

    def test_platform_adapters_protect_vital_process_names(self) -> None:
        """Valida que adapters de SO bloqueiam terminação de processos vitais pelo nome."""
        # macOS
        mac_probe = MacOSHardwareProbeAdapter()
        self.assertFalse(mac_probe.terminate_process(0))
        self.assertFalse(mac_probe.terminate_process(1))

        # Windows
        win_probe = WindowsHardwareProbeAdapter()
        self.assertFalse(win_probe.terminate_process(0))
        self.assertFalse(win_probe.terminate_process(4))  # System process PID no Windows

    def test_upgrade_packages_command_and_flag_injection_defense(self) -> None:
        """Garante que /api/upgrade-packages bloqueia flags injetadas e comandos maliciosos."""
        panel = LocalControlPanelServer()

        malicious_pkgs = [
            "--help",
            "-f",
            "--force",
            "git; rm -rf /",
            "git && calc.exe",
            "git | bash",
            "`id`",
            "$(whoami)",
            "git\x00extra",
            "pkg with space",
            "-",
        ]
        for bad in malicious_pkgs:
            with self.subTest(package_id=bad):
                status, _, res = panel.dispatch_request(
                    "POST",
                    "/api/upgrade-packages",
                    payload={"package_id": bad},
                )
                self.assertEqual(status, 400)
                self.assertEqual(res.get("status"), "error")

        # Verifica diretamente nos adapters
        mac_cloud = MacOSCloudAndPackagesAdapter()
        win_cloud = WindowsCloudAndPackagesAdapter()

        res_mac = mac_cloud.upgrade_package("--override")
        self.assertEqual(res_mac["status"], "error")

        res_win = win_cloud.upgrade_package("--silent-injection")
        self.assertEqual(res_win["status"], "error")

    def test_local_server_cross_origin_blocking(self) -> None:
        """Garante que requisições POST com Origin de domínios externos são bloqueadas (CSRF)."""
        import threading
        import http.client

        panel = LocalControlPanelServer()
        httpd, port = panel.create_server(port=0)

        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()

        try:
            # 1. Requisição com Origin externa maliciosa deve receber 403
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            try:
                headers = {
                    "Origin": "http://evil-website.com",
                    "Content-Type": "application/json",
                }
                conn.request("POST", "/api/file-action", body="{}", headers=headers)
                resp = conn.getresponse()
                self.assertEqual(resp.status, 403)
            finally:
                conn.close()

            # 2. Requisição com Origin legítima localhost deve passar pelo filtro de Origin
            conn2 = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            try:
                headers = {
                    "Origin": f"http://127.0.0.1:{port}",
                    "Content-Type": "application/json",
                }
                conn2.request("POST", "/api/execute", body="{}", headers=headers)
                resp2 = conn2.getresponse()
                self.assertEqual(resp2.status, 200)
            finally:
                conn2.close()
        finally:
            httpd.shutdown()
            httpd.server_close()


if __name__ == "__main__":
    unittest.main()
