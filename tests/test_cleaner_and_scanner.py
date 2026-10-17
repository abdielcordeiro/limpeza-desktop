# -*- coding: utf-8 -*-
"""Testes do Motor de Limpeza Autônoma e do Scanner 5 Camadas Anti-Falsos Positivos."""
import os
import stat
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from src.domain.entities import AutonomousCleanupRule
from src.domain.value_objects import ExecutionMode, OSPlatform
from src.infrastructure.filesystem.autonomous_cleaner import (
    AutonomousCleanerAdapter,
    _force_remove_file,
    _force_remove_dir,
)
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

    def test_subfolder_drilldown_occupants(self) -> None:
        """Valida que diretórios pesados mapeiam suas maiores subpastas dinamicamente."""
        with tempfile.TemporaryDirectory() as tmpdir:
            heavy_dir = os.path.join(tmpdir, "HeavyDataProject")
            sub_a = os.path.join(heavy_dir, "SubfolderAlpha")
            sub_b = os.path.join(heavy_dir, "SubfolderBeta")
            os.makedirs(sub_a, exist_ok=True)
            os.makedirs(sub_b, exist_ok=True)

            # Sub A: 2 MB, Sub B: 1 MB
            with open(os.path.join(sub_a, "data_a.bin"), "wb") as f:
                f.write(b"A" * (2 * 1024 * 1024))
            with open(os.path.join(sub_b, "data_b.bin"), "wb") as f:
                f.write(b"B" * (1 * 1024 * 1024))

            scanner = DiskScannerAdapter(min_orphan_bytes=512 * 1024)
            partitions = MacOSSystemProbeAdapter().get_partitions()
            top_occupants, _, _ = scanner.scan_and_evaluate(
                target_paths=[tmpdir],
                active_indicators=set(),
                partitions=partitions,
                os_platform=OSPlatform.MACOS,
                top_n=20,
            )

            # Procura pelo HeavyDataProject nos ocupantes
            heavy_occupant = next((o for o in top_occupants if o.name == "HeavyDataProject"), None)
            self.assertIsNotNone(heavy_occupant)
            self.assertEqual(heavy_occupant.item_type, "Pasta")
            self.assertGreaterEqual(len(heavy_occupant.sub_occupants), 2)

            # Verifica ordenação decrescente das subpastas
            first_sub = heavy_occupant.sub_occupants[0]
            second_sub = heavy_occupant.sub_occupants[1]
            self.assertEqual(first_sub["name"], "SubfolderAlpha")
            self.assertGreater(first_sub["size"], second_sub["size"])
            self.assertEqual(second_sub["name"], "SubfolderBeta")

    def test_resilient_cleanup_readonly_file_and_directory(self) -> None:
        """Garante que arquivos e diretórios somente-leitura sejam desbloqueados e removidos."""
        cleaner = AutonomousCleanerAdapter()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_sub = os.path.join(tmpdir, "protected_cache")
            os.makedirs(test_sub, exist_ok=True)
            ro_file = os.path.join(test_sub, "readonly_cache.bin")
            with open(ro_file, "wb") as f:
                f.write(b"L" * 4096)

            # Torna o arquivo somente-leitura (sem permissão de escrita)
            os.chmod(ro_file, stat.S_IREAD | stat.S_IRUSR)

            # Testa remoção forçada direta do arquivo
            _force_remove_file(ro_file)
            self.assertFalse(os.path.exists(ro_file))

            # Cria novo arquivo e subpasta protegidos para testar rmtree e clean_specific_paths
            ro_file2 = os.path.join(test_sub, "another_ro.bin")
            with open(ro_file2, "wb") as f:
                f.write(b"Z" * 8192)
            os.chmod(ro_file2, stat.S_IREAD | stat.S_IRUSR)

            # Cria subdiretório com restrição de escrita no próprio diretório
            locked_sub = os.path.join(test_sub, "locked_dir")
            os.makedirs(locked_sub, exist_ok=True)
            locked_file = os.path.join(locked_sub, "inside_locked.bin")
            with open(locked_file, "wb") as f:
                f.write(b"K" * 2048)
            os.chmod(locked_file, stat.S_IREAD | stat.S_IRUSR)
            os.chmod(locked_sub, stat.S_IREAD | stat.S_IXUSR)  # sem S_IWUSR no diretório pai

            entry = cleaner.clean_specific_paths([test_sub], mode=ExecutionMode.REAL)
            self.assertEqual(entry.status, "cleaned")
            self.assertEqual(entry.files_removed, 2)
            self.assertEqual(entry.bytes_freed, 8192 + 2048)
            self.assertEqual(entry.errors_skipped, 0)
            self.assertFalse(os.path.exists(test_sub))

    def test_trash_rule_identification(self) -> None:
        """Valida que regras de Lixeira (macOS e Windows) são identificadas corretamente."""
        cleaner = AutonomousCleanerAdapter()
        mac_rule = AutonomousCleanupRule(
            id="mac_trash",
            name="Esvaziar Lixeira",
            category="trash",
            os_platform="macos",
            description="desc",
            target_paths=["~/.Trash"],
        )
        win_rule = AutonomousCleanupRule(
            id="win_trash",
            name="Recycle Bin",
            category="trash",
            os_platform="windows",
            description="desc",
            target_paths=["$Recycle.Bin"],
        )
        normal_rule = AutonomousCleanupRule(
            id="win_system_temp",
            name="Temp Files",
            category="system_temp",
            os_platform="windows",
            description="desc",
            target_paths=["%TEMP%"],
        )
        custom_trash = AutonomousCleanupRule(
            id="custom_trash_check",
            name="Custom",
            category="custom",
            os_platform="macos",
            description="desc",
            target_paths=["/Users/test/.trash/sub"],
        )

        self.assertTrue(cleaner._is_trash_rule(mac_rule))
        self.assertTrue(cleaner._is_trash_rule(win_rule))
        self.assertTrue(cleaner._is_trash_rule(custom_trash))
        self.assertFalse(cleaner._is_trash_rule(normal_rule))

    @patch.object(AutonomousCleanerAdapter, "_count_macos_trash_items")
    @patch("subprocess.run")
    def test_macos_trash_rule_dry_run_and_real(self, mock_run, mock_count) -> None:
        """Valida a execução de esvaziamento nativo da Lixeira do macOS."""
        cleaner = AutonomousCleanerAdapter()
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_trash = os.path.join(tmpdir, ".Trash")
            os.makedirs(fake_trash, exist_ok=True)
            f = os.path.join(fake_trash, "item.tmp")
            with open(f, "wb") as fp:
                fp.write(b"X" * 1024)

            rule = AutonomousCleanupRule(
                id="mac_trash",
                name="Esvaziar Lixeira do Usuário",
                category="trash",
                os_platform="macos",
                description="desc",
                target_paths=[fake_trash],
            )

            # 1. Simulação (Dry-Run): Finder reporta 1 item
            mock_count.return_value = 1
            dry_entry = cleaner.execute_rule(rule, mode=ExecutionMode.DRY_RUN)
            self.assertEqual(dry_entry.status, "simulated")
            self.assertEqual(dry_entry.files_removed, 1)
            self.assertIn("Simulação (Dry-Run): 1 itens", dry_entry.details)
            self.assertTrue(os.path.exists(f))  # Arquivo preservado em Dry-Run

            # 2. Modo Real: Finder esvazia itens com sucesso
            mock_count.side_effect = [1, 0]  # antes = 1, depois = 0
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_run.return_value = mock_proc

            real_entry = cleaner.execute_rule(rule, mode=ExecutionMode.REAL)
            self.assertEqual(real_entry.status, "cleaned")
            self.assertEqual(real_entry.files_removed, 1)
            self.assertEqual(real_entry.errors_skipped, 0)
            self.assertEqual(real_entry.bytes_freed, 1024)
            self.assertIn("Lixeira do macOS esvaziada com sucesso", real_entry.details)
            self.assertFalse(os.path.exists(f))  # Arquivo removido no modo Real

    @patch.object(AutonomousCleanerAdapter, "_query_windows_recycle_bin")
    @patch("subprocess.run")
    def test_windows_trash_rule_dry_run_and_real(self, mock_run, mock_query) -> None:
        """Valida a execução de esvaziamento nativo da Lixeira do Windows (Shell32 / PowerShell)."""
        cleaner = AutonomousCleanerAdapter()
        rule = AutonomousCleanupRule(
            id="win_trash",
            name="Esvaziar Lixeira do Windows",
            category="trash",
            os_platform="windows",
            description="desc",
            target_paths=["$Recycle.Bin"],
        )

        # 1. Simulação (Dry-Run)
        mock_query.return_value = (5242880, 4)  # 5 MB, 4 itens
        dry_entry = cleaner.execute_rule(rule, mode=ExecutionMode.DRY_RUN)
        self.assertEqual(dry_entry.status, "simulated")
        self.assertEqual(dry_entry.files_removed, 4)
        self.assertEqual(dry_entry.bytes_freed, 5242880)

        # 2. Modo Real
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc

        real_entry = cleaner.execute_rule(rule, mode=ExecutionMode.REAL)
        self.assertEqual(real_entry.status, "cleaned")
        self.assertEqual(real_entry.files_removed, 4)
        self.assertEqual(real_entry.bytes_freed, 5242880)
        self.assertIn("Lixeira do Windows esvaziada com sucesso", real_entry.details)


if __name__ == "__main__":
    unittest.main()
