# -*- coding: utf-8 -*-
"""Testes de resolução de recursos, especificação PyInstaller e scripts de bootstrap oneliner."""
import os
import sys
import shutil
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


if __name__ == "__main__":
    unittest.main()
