# -*- coding: utf-8 -*-
"""Testes dos catálogos declarativos (Windows WinUtil Sanitizado & macOS) e Snapshot/Undo."""
import os
import tempfile
import unittest

from src.domain.entities import StateSnapshot
from src.domain.value_objects import OSPlatform, ExecutionMode
from src.infrastructure.windows.platform_adapter import WindowsSystemProbeAdapter
from src.infrastructure.tweaks_adapter import SystemTweakAdapter
from src.infrastructure.persistence.snapshot_repository import SnapshotRepository


class TestCatalogsAndTweaks(unittest.TestCase):
    """Valida a integridade dos catálogos offline e a idempotência/reversão de Tweaks."""

    def setUp(self) -> None:
        self.probe = WindowsSystemProbeAdapter()
        self.adapter = SystemTweakAdapter(system_probe=self.probe)

    def test_windows_tweaks_catalog_completeness(self) -> None:
        win_tweaks = self.adapter.list_available_tweaks(OSPlatform.WINDOWS)
        ids = {t.id for t in win_tweaks}

        expected_ids = {
            "WPFTweaksRestorePoint",
            "WPFTweaksTele",
            "WPFTweaksServices",
            "WPFTweaksDVR",
            "WPFTweaksActivity",
            "WPFTweaksLoc",
            "WPFTweaksWifi",
            "WPFTweaksConsumerFeatures",
            "WPFTweaksEndTask",
            "WPFTweaksHiber",
            "WPFTweaksStorage",
            "WPFTweaksDeliveryOptimization",
            "WPFTweaksDeleteTempFiles",
            "WPFTweaksDiskCleanup",
            "WPFAddUltPerf",
            "WPFTweaksWindowsAI",
            "WPFTweaksRightClickMenu",
            "WPFTweaksEdgeDebloat",
            "WPFTweaksBing",
            "WPFTweaksDisplay",
            "WPFTweaksUTC",
            "WPFFixesNetwork",
            "WPFFixesUpdate",
            "WPFFixesCorrupt",
        }
        self.assertTrue(expected_ids.issubset(ids), f"Faltando tweaks no catálogo Windows: {expected_ids - ids}")

        # Verifica WPFTweaksTele (13 Scheduled Tasks + chaves de registro)
        tele = next(t for t in win_tweaks if t.id == "WPFTweaksTele")
        self.assertEqual(len(tele.scheduled_tasks), 13)
        self.assertGreaterEqual(len(tele.registry_changes), 15)

        # Verifica WPFTweaksServices (~45+ serviços com original_type para reversão)
        svcs = next(t for t in win_tweaks if t.id == "WPFTweaksServices")
        self.assertGreaterEqual(len(svcs.service_changes), 45)
        for s in svcs.service_changes:
            self.assertIn("original_type", s)
            self.assertIn("startup_type", s)

    def test_macos_tweaks_catalog_completeness(self) -> None:
        mac_tweaks = self.adapter.list_available_tweaks(OSPlatform.MACOS)
        ids = {t.id for t in mac_tweaks}
        expected_mac_ids = {
            "MacFlushDNS",
            "MacSpeedUpDock",
            "MacFastWindowResize",
            "MacDisableFinderAnimations",
            "MacDisableLaunchpadAnim",
            "MacDisableCrashDialog",
            "MacThinTimeMachineSnapshots",
            "MacRebuildLaunchServices",
            "MacVerifyAPFS",
        }
        self.assertEqual(expected_mac_ids, ids)

    def test_snapshot_repository_and_idempotent_undo(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = SnapshotRepository(snapshots_dir=tmpdir)
            mac_tweaks = self.adapter.list_available_tweaks(OSPlatform.MACOS)
            dock_tweak = next(t for t in mac_tweaks if t.id == "MacSpeedUpDock")

            state = self.adapter.capture_current_state(dock_tweak)
            snap = StateSnapshot(
                snapshot_id="snapshot_test_001",
                created_at="2026-10-16T00:00:00",
                os_platform="macos",
                mode="dry_run",
                entries={dock_tweak.id: state},
                tweaks_applied=[dock_tweak.id],
                description="Teste unitário de snapshot",
            )
            saved_path = repo.save_snapshot(snap)
            self.assertTrue(os.path.exists(saved_path))

            loaded = repo.get_snapshot("latest")
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.snapshot_id, "snapshot_test_001")

            # Aplica e reverte em modo DRY_RUN (100% seguro e idempotente)
            apply_rec = self.adapter.apply_tweak(dock_tweak, mode=ExecutionMode.DRY_RUN)
            self.assertTrue(apply_rec.success)
            self.assertEqual(apply_rec.action, "dry_run")

            undo_rec = self.adapter.revert_tweak(
                dock_tweak,
                previous_state=loaded.entries[dock_tweak.id],
                mode=ExecutionMode.DRY_RUN,
            )
            self.assertTrue(undo_rec.success)
            self.assertEqual(undo_rec.action, "undo")


if __name__ == "__main__":
    unittest.main()
