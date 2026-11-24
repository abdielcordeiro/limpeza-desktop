# -*- coding: utf-8 -*-
"""Testes de resolução de recursos, especificação PyInstaller e scripts de bootstrap oneliner."""
import os
import re
import sys
import shutil
import subprocess
import tempfile
import unittest

from src.infrastructure.resources import get_resource_path, get_catalog_path


class TestStandalonePackagingAndResources(unittest.TestCase):
    """Testa o suporte a PyInstaller standalone e a resolução de catálogos e scripts."""

    def test_catalog_resolution_in_dev_mode(self) -> None:
        """Verifica que todos os catálogos JSON são encontrados em modo desenvolvimento."""
        win_cat = get_catalog_path("windows_tweaks.json")
        mac_cat = get_catalog_path("macos_tweaks.json")
        rules_cat = get_catalog_path("safe_cleanup_rules.json")

        self.assertTrue(os.path.exists(win_cat), f"Catálogo não encontrado: {win_cat}")
        self.assertTrue(os.path.exists(mac_cat), f"Catálogo não encontrado: {mac_cat}")
        self.assertTrue(os.path.exists(rules_cat), f"Catálogo não encontrado: {rules_cat}")

    def test_catalog_resolution_in_meipass_pyinstaller_mode(self) -> None:
        """Simula o runtime do PyInstaller com sys._MEIPASS ativo."""
        with tempfile.TemporaryDirectory() as fake_meipass:
            # Configura sys._MEIPASS
            orig_meipass = getattr(sys, "_MEIPASS", None)
            sys._MEIPASS = fake_meipass  # type: ignore
            try:
                # Cria estrutura de pastas dentro do fake _MEIPASS
                target_catalogs = os.path.join(
                    fake_meipass, "src", "infrastructure", "catalogs"
                )
                os.makedirs(target_catalogs, exist_ok=True)

                fake_catalog_file = os.path.join(target_catalogs, "windows_tweaks.json")
                with open(fake_catalog_file, "w", encoding="utf-8") as f:
                    f.write('{"tweaks": []}')

                # Executa resolução
                resolved = get_catalog_path("windows_tweaks.json")
                self.assertEqual(os.path.abspath(resolved), os.path.abspath(fake_catalog_file))
            finally:
                if orig_meipass is not None:
                    sys._MEIPASS = orig_meipass  # type: ignore
                else:
                    delattr(sys, "_MEIPASS")

    def test_pyinstaller_spec_file_integrity(self) -> None:
        """Valida que o arquivo limpeza.spec está íntegro e referencia todos os recursos."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        spec_path = os.path.join(repo_root, "limpeza.spec")
        self.assertTrue(os.path.exists(spec_path), "limpeza.spec não existe na raiz")

        with open(spec_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("windows_tweaks.json", content)
        self.assertIn("macos_tweaks.json", content)
        self.assertIn("safe_cleanup_rules.json", content)
        self.assertIn("main.py", content)
        self.assertIn("name='limpeza'", content)

    def test_bootstrap_oneliner_scripts_integrity(self) -> None:
        """Valida a presença e integridade dos scripts de bootstrap para macOS e Windows."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # 1. install-macos.sh
        sh_path = os.path.join(repo_root, "install-macos.sh")
        self.assertTrue(os.path.exists(sh_path), "install-macos.sh não existe na raiz")
        with open(sh_path, "r", encoding="utf-8") as f:
            sh_content = f.read()
        self.assertIn("limpeza-macos", sh_content)
        self.assertIn("curl", sh_content)
        self.assertIn("abdielcordeiro/limpeza-desktop", sh_content)

        # 2. install-windows.ps1
        ps_path = os.path.join(repo_root, "install-windows.ps1")
        self.assertTrue(os.path.exists(ps_path), "install-windows.ps1 não existe na raiz")
        with open(ps_path, "r", encoding="utf-8") as f:
            ps_content = f.read()
        self.assertIn("limpeza-windows.exe", ps_content)
        self.assertIn("Invoke-WebRequest", ps_content)
        self.assertIn("abdielcordeiro/limpeza-desktop", ps_content)

    def test_windows_bootstrap_anti_crash_and_nuget_fallback(self) -> None:
        """Valida que install-windows.ps1 não usa exit solto (iex-safe), ignora WindowsApps e tem fallback NuGet."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ps_path = os.path.join(repo_root, "install-windows.ps1")
        with open(ps_path, "r", encoding="utf-8") as f:
            ps_content = f.read()

        # Não pode conter 'exit' como instrução PowerShell fora de comentários
        non_comment_lines = [
            line for line in ps_content.splitlines()
            if not line.lstrip().startswith("#")
        ]
        for line in non_comment_lines:
            self.assertIsNone(
                re.search(r"(?:^|[;\s{}])exit(?:\s+\d+|\s*$|;)", line, re.IGNORECASE),
                f"Encontrado 'exit' inseguro para iex na linha: {line}",
            )

        self.assertIn("Invoke-LimpezaDesktop", ps_content)
        self.assertIn("Test-RealPython", ps_content)
        self.assertIn("WindowsApps", ps_content)
        self.assertIn("https://www.nuget.org/api/v2/package/python/3.11.9", ps_content)
        self.assertIn(r"tools\python.exe", ps_content)

    def test_macos_bootstrap_anti_stub_and_portable_runtime(self) -> None:
        """Valida que install-macos.sh verifica xcode-select -p e possui fallback portátil arm64/x86_64."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sh_path = os.path.join(repo_root, "install-macos.sh")
        with open(sh_path, "r", encoding="utf-8") as f:
            sh_content = f.read()

        self.assertIn("xcode-select -p", sh_content)
        self.assertIn("/usr/bin/python3", sh_content)
        self.assertIn("aarch64-apple-darwin", sh_content)
        self.assertIn("x86_64-apple-darwin", sh_content)
        self.assertIn("python-build-standalone", sh_content)

    def test_main_cp1252_encoding_safety(self) -> None:
        """Valida que main.py reconfigura stdout/stderr para UTF-8 e não lança UnicodeEncodeError sob cp1252."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        main_path = os.path.join(repo_root, "main.py")

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "cp1252"

        proc = subprocess.run(
            [sys.executable, main_path, "--undo", "non_existent_snap", "--dry-run"],
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        combined_output = (proc.stdout or "") + (proc.stderr or "")
        self.assertNotIn("UnicodeEncodeError", combined_output)
        self.assertEqual(proc.returncode, 1)

        # Valida também impressão direta de caracteres Unicode (✓) após importar main
        unicode_check = subprocess.run(
            [
                sys.executable,
                "-c",
                "import main; print('✓ UTF-8 seguro no console Windows')",
            ],
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        self.assertEqual(unicode_check.returncode, 0, unicode_check.stderr)
        self.assertNotIn("UnicodeEncodeError", unicode_check.stderr or "")


if __name__ == "__main__":
    unittest.main()
