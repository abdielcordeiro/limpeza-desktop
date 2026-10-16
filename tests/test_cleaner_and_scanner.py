# -*- coding: utf-8 -*-
"""Testes do Motor de Limpeza Autônoma e do Scanner 5 Camadas Anti-Falsos Positivos."""
import os
import tempfile
import unittest

from src.domain.entities import AutonomousCleanupRule
from src.domain.value_objects import ExecutionMode, OSPlatform
from src.infrastructure.filesystem.autonomous_cleaner import AutonomousCleanerAdapter
from src.infrastructure.filesystem.disk_scanner import DiskScannerAdapter, matches_active_software
from src.infrastructure.windows.platform_adapter import WindowsActiveAppsAdapter
from src.infrastructure.macos.platform_adapter import MacOSActiveAppsAdapter, MacOSSystemProbeAdapter


class TestAutonomousCleanerAndScanner(unittest.TestCase):
    """Testa limpeza DRY_RUN vs REAL e detecção de pastas órfãs sem falsos positivos."""

    def test_autonomous_cleaner_dry_run_and_real_mode(self) -> None:
        cleaner = AutonomousCleanerAdapter()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Cria 3 arquivos temporários de teste (total = 15000 bytes)
            sub = os.path.join(tmpdir, "subcache")
            os.makedirs(sub, exist_ok=True)
            f1 = os.path.join(tmpdir, "temp1.tmp")
            f2 = os.path.join(sub, "shader2.cache")
            with open(f1, "wb") as fp:
                fp.write(b"A" * 5000)
            with open(f2, "wb") as fp:
                fp.write(b"B" * 10000)

            rule = AutonomousCleanupRule(
                id="test_rule",
                name="Regra Temporária de Teste",
                category="system_temp",
                os_platform="macos",
                description="Teste",
                target_paths=[tmpdir],
            )

            # 1. Modo DRY_RUN: calcula exatamente 15000 bytes e 2 arquivos, mas NÃO apaga
            dry_entry = cleaner.execute_rule(rule, mode=ExecutionMode.DRY_RUN)
            self.assertEqual(dry_entry.status, "simulated")
            self.assertEqual(dry_entry.bytes_freed, 15000)
            self.assertEqual(dry_entry.files_removed, 2)
            self.assertTrue(os.path.exists(f1))
            self.assertTrue(os.path.exists(f2))

            # 2. Modo REAL: remove os arquivos e contabiliza 15000 bytes liberados
            real_entry = cleaner.execute_rule(rule, mode=ExecutionMode.REAL)
            self.assertEqual(real_entry.status, "cleaned")
            self.assertEqual(real_entry.bytes_freed, 15000)
            self.assertEqual(real_entry.files_removed, 2)
            self.assertFalse(os.path.exists(f1))
            self.assertFalse(os.path.exists(f2))

    def test_five_layers_orphan_detection_zero_false_positives(self) -> None:
        win_active = WindowsActiveAppsAdapter().get_active_indicators([])
        mac_active = MacOSActiveAppsAdapter().get_active_indicators([])

        # Softwares conhecidos na whitelist de 5 camadas NUNCA devem ser marcados como órfãos
        self.assertTrue(matches_active_software("Code", win_active))
        self.assertTrue(matches_active_software("Discord", win_active))
        self.assertTrue(matches_active_software("com.apple.Safari", mac_active))
        self.assertTrue(matches_active_software("com.jetbrains.intellij", mac_active))
        self.assertTrue(matches_active_software("Spotify", mac_active))

        # Software fictício desinstalado não deve constar nas 5 camadas
        self.assertFalse(matches_active_software("ObsoleteUninstalledApp2017", win_active))
        self.assertFalse(matches_active_software("com.xyzcorp.removedtool99", mac_active))

        # Testa o DiskScannerAdapter identificando a pasta órfã dentro de Library/Application Support
        with tempfile.TemporaryDirectory() as tmpdir:
            app_support = os.path.join(tmpdir, "Library", "Application Support")
            active_dir = os.path.join(app_support, "Spotify")
            orphan_dir = os.path.join(app_support, "ObsoleteUninstalledApp2017")
            os.makedirs(active_dir, exist_ok=True)
            os.makedirs(orphan_dir, exist_ok=True)

            # Cria 2 MB em cada pasta
            with open(os.path.join(active_dir, "data.bin"), "wb") as f:
                f.write(b"X" * (2 * 1024 * 1024))
            with open(os.path.join(orphan_dir, "leftover.bin"), "wb") as f:
                f.write(b"Y" * (2 * 1024 * 1024))

            scanner = DiskScannerAdapter(min_orphan_bytes=512 * 1024)
            partitions = MacOSSystemProbeAdapter().get_partitions()
            _, clean_suggestions, _ = scanner.scan_and_evaluate(
                target_paths=[tmpdir],
                active_indicators=mac_active,
                partitions=partitions,
                os_platform=OSPlatform.MACOS,
                top_n=50,
            )

            orphan_names = {c.name for c in clean_suggestions if c.is_orphan}
            self.assertIn("ObsoleteUninstalledApp2017", orphan_names)
            self.assertNotIn("Spotify", orphan_names)


if __name__ == "__main__":
    unittest.main()
