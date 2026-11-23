# -*- coding: utf-8 -*-
"""Testes de Unidade e Integração do Raio-X de Armazenamento e Inspetor Cirúrgico (RF-18 & RF-19 / ADR-011)."""
import os
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from src.domain.entities import (
    DirectoryInspectionNode,
    StorageCategoryBreakdown,
    StorageXRayReport,
    SystemExecutionReport,
    PartitionInfo,
    HardwareHealthInfo,
    StorageDiskHealth,
)
from src.domain.value_objects import OSPlatform, ExecutionMode
from src.infrastructure.filesystem.disk_scanner import (
    DiskScannerAdapter,
    REBUILDABLE_PROJECT_ARTIFACTS,
)
from src.infrastructure.filesystem.autonomous_cleaner import AutonomousCleanerAdapter
from src.application.orchestrator import OrchestratorService
from src.presentation.window.local_server import LocalControlPanelServer


class TestStorageXRayDomainAndScanner(unittest.TestCase):
    """Testa entidades, detecção de artefatos de build e construção do Raio-X."""

    def test_storage_xray_entities_and_serialization(self) -> None:
        """Valida a integridade das dataclasses de Raio-X e sua serialização em to_dict()."""
        node = DirectoryInspectionNode(
            name="node_modules",
            path="/Users/test/project/node_modules",
            size=104857600,  # 100 MB
            size_formatted="100.00 MB",
            percent_of_parent=45.5,
            item_type="Pasta",
            is_hidden=False,
            safety_action="✅ Limpeza Direta",
            safety_badge="success",
            safety_recommendation="Pode ser reconstruído com npm install",
            can_delete=True,
            children_count=42,
        )
        d_node = node.to_dict()
        self.assertEqual(d_node["name"], "node_modules")
        self.assertEqual(d_node["size"], 104857600)
        self.assertTrue(d_node["can_delete"])

        breakdown = StorageCategoryBreakdown(
            category_id="doc_visible_projects",
            title="Projetos & Pastas Visíveis",
            os_equivalent="Documentos (macOS Storage)",
            total_bytes=1073741824,  # 1 GB
            total_formatted="1.00 GB",
            description="Projetos do usuário",
            why_os_hides_it="O macOS agrega sem destrinchar linguagens",
            top_items=[d_node],
        )
        d_breakdown = breakdown.to_dict()
        self.assertEqual(d_breakdown["category_id"], "doc_visible_projects")
        self.assertEqual(len(d_breakdown["top_items"]), 1)

        xray = StorageXRayReport(
            documents_total_bytes=2147483648,
            documents_visible_bytes=1073741824,
            documents_hidden_dotfiles_bytes=536870912,
            documents_rebuildable_artifacts_bytes=536870912,
            system_data_tracked_bytes=5368709120,
            categories=[breakdown],
        )
        self.assertEqual(xray.documents_total_formatted, "2.00 GB")
        self.assertEqual(xray.documents_visible_formatted, "1.00 GB")
        self.assertEqual(xray.system_data_tracked_formatted, "5.00 GB")

        d_xray = xray.to_dict()
        self.assertIn("documents_total_bytes", d_xray)
        self.assertEqual(len(d_xray["categories"]), 1)

    def test_rebuildable_project_artifacts_detection_in_scan(self) -> None:
        """RF-18: Valida detecção de node_modules e .venv como CleanableItem reconstruível."""
        scanner = DiskScannerAdapter(min_orphan_bytes=500)
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir = os.path.join(tmpdir, "MyWebProject")
            nm_dir = os.path.join(proj_dir, "node_modules")
            venv_dir = os.path.join(proj_dir, ".venv")
            src_dir = os.path.join(proj_dir, "src")
            os.makedirs(nm_dir, exist_ok=True)
            os.makedirs(venv_dir, exist_ok=True)
            os.makedirs(src_dir, exist_ok=True)

            # Cria arquivos para ter tamanho mensurável
            with open(os.path.join(nm_dir, "package.json"), "wb") as f:
                f.write(b"X" * 2000)
            with open(os.path.join(venv_dir, "python.bin"), "wb") as f:
                f.write(b"Y" * 3000)
            with open(os.path.join(src_dir, "main.py"), "wb") as f:
                f.write(b"Z" * 1000)

            occupants, cleanables, installed = scanner.scan_and_evaluate(
                target_paths=[proj_dir],
                active_indicators=set(),
                partitions=[],
                os_platform=OSPlatform.MACOS,
            )

            # Valida que node_modules e .venv foram catalogados como artefatos reconstruíveis
            rebuildable_items = [
                c for c in cleanables
                if "Artefato Reconstruível" in c.item_type
            ]
            self.assertTrue(len(rebuildable_items) >= 2, f"Esperado ao menos 2 artefatos, obteve: {rebuildable_items}")
            paths_found = [c.path for c in rebuildable_items]
            self.assertIn(nm_dir, paths_found)
            self.assertIn(venv_dir, paths_found)
            for item in rebuildable_items:
                self.assertEqual(item.risk_badge, "info")
                self.assertFalse(item.is_orphan)
                self.assertIn("Reconstruível", item.risk_level)

    def test_build_storage_xray_categories_breakdown(self) -> None:
        """RF-18: Valida que build_storage_xray constrói as 8 categorias de armazenamento."""
        scanner = DiskScannerAdapter()
        with tempfile.TemporaryDirectory() as fake_home:
            # Cria pastas visíveis
            doc_dir = os.path.join(fake_home, "Documents")
            idea_dir = os.path.join(fake_home, "IdeaProjects", "AppDemo")
            nm_dir = os.path.join(idea_dir, "node_modules")
            # Cria pastas ocultas (dotfiles)
            gemini_dir = os.path.join(fake_home, ".gemini")
            gradle_dir = os.path.join(fake_home, ".gradle")
            # Cria subpastas de Library
            lib_caches = os.path.join(fake_home, "Library", "Caches", "com.test.app")
            lib_app_sup = os.path.join(fake_home, "Library", "Application Support", "Code")

            os.makedirs(doc_dir, exist_ok=True)
            os.makedirs(nm_dir, exist_ok=True)
            os.makedirs(gemini_dir, exist_ok=True)
            os.makedirs(gradle_dir, exist_ok=True)
            os.makedirs(lib_caches, exist_ok=True)
            os.makedirs(lib_app_sup, exist_ok=True)

            with open(os.path.join(doc_dir, "file.pdf"), "wb") as f:
                f.write(b"A" * 1024)
            with open(os.path.join(nm_dir, "index.js"), "wb") as f:
                f.write(b"B" * 1024)
            with open(os.path.join(gemini_dir, "state.json"), "wb") as f:
                f.write(b"C" * 1024)
            with open(os.path.join(lib_caches, "cache.dat"), "wb") as f:
                f.write(b"D" * 1024)

            hw_mock = HardwareHealthInfo(
                overall_status="Saudável",
                disks=[
                    StorageDiskHealth(
                        device_id="/dev/disk1s1",
                        name="Macintosh HD",
                        media_type="Apple Fabric NVMe",
                        bus_type="Apple Fabric",
                        smart_status="Verified",
                        trim_supported=True,
                        purgeable_bytes=5368709120,  # 5 GB
                    )
                ]
            )

            with patch("os.path.expanduser", side_effect=lambda p: p.replace("~", fake_home) if p.startswith("~") else p):
                xray = scanner.build_storage_xray(
                    os_platform=OSPlatform.MACOS,
                    partitions=[],
                    hardware_health=hw_mock,
                )

            self.assertIsInstance(xray, StorageXRayReport)
            self.assertEqual(len(xray.categories), 8)
            cat_ids = [c.category_id for c in xray.categories]
            self.assertIn("doc_visible_projects", cat_ids)
            self.assertIn("doc_hidden_dotfiles", cat_ids)
            self.assertIn("doc_rebuildable_artifacts", cat_ids)
            self.assertIn("sys_containers_vms", cat_ids)
            self.assertIn("sys_app_support", cat_ids)
            self.assertIn("sys_caches_darwin", cat_ids)
            self.assertIn("sys_dev_toolchains_pkgs", cat_ids)
            self.assertIn("sys_vm_snapshots_ai", cat_ids)

            # Verifica se o espaço purgável foi incorporado na categoria 8
            cat8 = next(c for c in xray.categories if c.category_id == "sys_vm_snapshots_ai")
            names = [it["name"] for it in cat8.top_items]
            self.assertTrue(any("Espaço Purgável" in n for n in names))


class TestDirectoryInspectorAndEndpoints(unittest.TestCase):
    """Testa inspeção física nível a nível e endpoint REST local com guardrails de segurança."""

    def setUp(self) -> None:
        self.scanner = DiskScannerAdapter()

    def test_inspect_directory_ordering_and_metrics(self) -> None:
        """RF-19: Inspeciona diretório ordenando filhos por tamanho físico decrescente."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sub1 = os.path.join(tmpdir, "heavy_subfolder")
            sub2 = os.path.join(tmpdir, "light_subfolder")
            os.makedirs(sub1, exist_ok=True)
            os.makedirs(sub2, exist_ok=True)

            file_big = os.path.join(tmpdir, "big_archive.zip")
            file_small = os.path.join(tmpdir, "notes.txt")

            with open(file_big, "wb") as f:
                f.write(b"Z" * 100000)
            with open(file_small, "wb") as f:
                f.write(b"N" * 1000)
            with open(os.path.join(sub1, "data.bin"), "wb") as f:
                f.write(b"D" * 50000)
            with open(os.path.join(sub2, "conf.json"), "wb") as f:
                f.write(b"C" * 5000)

            res = self.scanner.inspect_directory(tmpdir, os_platform=OSPlatform.MACOS, max_items=10)
            self.assertEqual(res["name"], os.path.basename(tmpdir))
            self.assertEqual(res["items_count"], 4)
            items = res["items"]
            self.assertEqual(len(items), 4)

            # O primeiro item deve ser big_archive.zip (100.000 bytes)
            self.assertEqual(items[0]["name"], "big_archive.zip")
            self.assertEqual(items[0]["item_type"], "Arquivo")
            self.assertEqual(items[0]["size"], 100000)
            self.assertTrue(items[0]["percent_of_parent"] > 50.0)

            # O segundo item deve ser heavy_subfolder (50.000 bytes)
            self.assertEqual(items[1]["name"], "heavy_subfolder")
            self.assertEqual(items[1]["item_type"], "Pasta")
            self.assertTrue(items[1]["children_count"] >= 1)

    def test_inspect_directory_security_guardrails(self) -> None:
        """Valida que inspect_directory bloqueia path traversal, null bytes e flags."""
        with self.assertRaises(ValueError):
            self.scanner.inspect_directory("/tmp/../etc/shadow", os_platform=OSPlatform.MACOS)

        with self.assertRaises(ValueError):
            self.scanner.inspect_directory("/tmp/folder\x00malicious", os_platform=OSPlatform.MACOS)

        with self.assertRaises(FileNotFoundError):
            self.scanner.inspect_directory("/caminho/completamente/inexistente/xyz", os_platform=OSPlatform.MACOS)

    def test_api_inspect_directory_endpoint(self) -> None:
        """Testa o endpoint POST /api/inspect-directory no LocalControlPanelServer."""
        panel = LocalControlPanelServer()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.log")
            with open(test_file, "wb") as f:
                f.write(b"L" * 2048)

            # 1. Requisição válida
            code, ctype, body = panel.dispatch_request(
                "POST",
                "/api/inspect-directory",
                {"path": tmpdir, "max_items": 15},
            )
            self.assertEqual(code, 200)
            self.assertEqual(body["status"], "ok")
            self.assertEqual(body["items_count"], 1)
            self.assertEqual(body["items"][0]["name"], "test.log")

            # 2. Path Traversal
            code, _, body = panel.dispatch_request(
                "POST",
                "/api/inspect-directory",
                {"path": f"{tmpdir}/../something"},
            )
            self.assertEqual(code, 400)
            self.assertIn("Path Traversal", body["message"])

            # 3. Null bytes
            code, _, body = panel.dispatch_request(
                "POST",
                "/api/inspect-directory",
                {"path": f"{tmpdir}\x00"},
            )
            self.assertEqual(code, 400)

            # 4. Flag injection
            code, _, body = panel.dispatch_request(
                "POST",
                "/api/inspect-directory",
                {"path": "-la"},
            )
            self.assertEqual(code, 400)

            # 5. Diretório inexistente
            code, _, body = panel.dispatch_request(
                "POST",
                "/api/inspect-directory",
                {"path": "/tmp/non_existent_folder_abc_123"},
            )
            self.assertEqual(code, 404)


class TestCleanupRulesAndWildcardEffectiveness(unittest.TestCase):
    """Testa a ativação padrão de caches e a exclusão efetiva de pastas via wildcard."""

    def test_dev_caches_default_enabled_in_catalog(self) -> None:
        """RF-18: Garante que as regras de cache de dev estão ativadas por padrão no catálogo."""
        cleaner = AutonomousCleanerAdapter()
        rules_mac = cleaner.get_cleanup_rules(OSPlatform.MACOS)
        rules_map = {r.id: r for r in rules_mac}

        expected_enabled = [
            "mac_jetbrains_caches",
            "mac_node_js_caches",
            "mac_python_dev_caches",
            "mac_jvm_native_mobile_caches",
        ]
        for r_id in expected_enabled:
            self.assertIn(r_id, rules_map, f"Regra {r_id} não encontrada no catálogo macOS")
            self.assertTrue(rules_map[r_id].default_enabled, f"Regra {r_id} deve ter default_enabled=True")

        rules_win = cleaner.get_cleanup_rules(OSPlatform.WINDOWS)
        win_map = {r.id: r for r in rules_win}
        self.assertIn("win_dev_caches", win_map)
        self.assertTrue(win_map["win_dev_caches"].default_enabled)

    def test_wildcard_cleanup_removes_root_subfolders(self) -> None:
        """RF-18: Garante que alvos com wildcard aplicam remove_root=True removendo as subpastas filhas."""
        cleaner = AutonomousCleanerAdapter()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Simula ~/Library/Caches/* criando subpastas de teste
            cache1 = os.path.join(tmpdir, "com.test.one")
            cache2 = os.path.join(tmpdir, "com.test.two")
            os.makedirs(cache1, exist_ok=True)
            os.makedirs(cache2, exist_ok=True)

            with open(os.path.join(cache1, "c1.tmp"), "wb") as f:
                f.write(b"1" * 1024)
            with open(os.path.join(cache2, "c2.tmp"), "wb") as f:
                f.write(b"2" * 2048)

            from src.domain.entities import AutonomousCleanupRule
            rule = AutonomousCleanupRule(
                id="test_wildcard_rule",
                name="Teste Wildcard",
                category="user_caches",
                os_platform="macos",
                description="Teste",
                target_paths=[f"{tmpdir}/*"],
                default_enabled=True,
            )

            with patch("src.infrastructure.filesystem.autonomous_cleaner.is_safe_path_to_clean", return_value=True):
                entry = cleaner.execute_rule(rule, mode=ExecutionMode.REAL)

            self.assertEqual(entry.files_removed, 2)
            self.assertEqual(entry.bytes_freed, 3072)
            # Como remove_root=True foi aplicado às pastas expandidas pelo wildcard, as subpastas devem ter sido excluídas
            self.assertFalse(os.path.exists(cache1), "Subpasta cache1 deveria ter sido excluída por completo")
            self.assertFalse(os.path.exists(cache2), "Subpasta cache2 deveria ter sido excluída por completo")
            self.assertTrue(os.path.exists(tmpdir), "A pasta pai raiz do wildcard deve ser preservada")


class TestMacOSApfsDiskSizeReconciliation(unittest.TestCase):
    """RF-20 / ADR-012: Testa reconciliação SI Decimal (1000^3) vs Binário IEC (1024^3) e PurgeableSpace no macOS."""

    def test_format_bytes_si_and_binary_exact_user_macos_numbers(self) -> None:
        """Valida conversão matemática exata dos bytes reais do container APFS de 256 GB."""
        from src.domain.value_objects import format_bytes, format_bytes_si, format_bytes_binary

        total_apfs = 245107195904
        raw_free = 27513415271
        raw_used = total_apfs - raw_free  # 217593780633
        purgeable = 493384729
        effective_free = raw_free + purgeable  # 28006800000
        effective_used = total_apfs - effective_free  # 217100395904

        # Base-10 SI (padrão Ajustes do Sistema do macOS)
        self.assertEqual(format_bytes_si(total_apfs), "245.11 GB")
        self.assertEqual(format_bytes_si(raw_used), "217.59 GB")
        self.assertEqual(format_bytes_si(raw_free), "27.51 GB")
        self.assertEqual(format_bytes_si(effective_used), "217.10 GB")
        self.assertEqual(format_bytes_si(effective_free), "28.01 GB")
        self.assertEqual(format_bytes_si(purgeable), "493.38 MB")

        # Base-2 IEC explícito (GiB)
        self.assertEqual(format_bytes_binary(total_apfs), "228.27 GiB")
        self.assertEqual(format_bytes_binary(raw_used), "202.65 GiB")
        self.assertEqual(format_bytes_binary(raw_free), "25.62 GiB")
        self.assertEqual(format_bytes_binary(effective_used), "202.19 GiB")

        # Compatibilidade retroativa de format_bytes()
        self.assertEqual(format_bytes(total_apfs), "228.27 GB")
        self.assertEqual(format_bytes(0), "0.00 B")
        self.assertEqual(format_bytes_si(0), "0.00 B")
        self.assertEqual(format_bytes_binary(0), "0.00 B")

    def test_partition_info_and_storage_disk_health_si_and_binary_properties(self) -> None:
        """Valida serialização dual SI + IEC em PartitionInfo e StorageDiskHealth."""
        total_apfs = 245107195904
        raw_free = 27513415271
        raw_used = 217593780633
        purgeable = 493384729
        eff_free = 28006800000
        eff_used = 217100395904

        part = PartitionInfo(
            mount_point="/",
            drive_letter="Macintosh HD (/)",
            total_bytes=total_apfs,
            used_bytes=eff_used,
            free_bytes=eff_free,
            percent_used=round(eff_used / total_apfs * 100.0, 1),
            is_os_drive=True,
            role="Volume Principal APFS",
            health_status="Atenção",
            health_class="warning",
            health_desc="Teste",
            filesystem="APFS",
            purgeable_bytes=purgeable,
            raw_used_bytes=raw_used,
            raw_free_bytes=raw_free,
            use_si_units=True,
        )
        p_dict = part.to_dict()
        self.assertEqual(p_dict["total_formatted"], "245.11 GB")
        self.assertEqual(p_dict["used_formatted"], "217.10 GB")
        self.assertEqual(p_dict["free_formatted"], "28.01 GB")
        self.assertEqual(p_dict["purgeable_formatted"], "493.38 MB")
        self.assertEqual(p_dict["raw_used_formatted"], "217.59 GB")
        self.assertEqual(p_dict["raw_free_formatted"], "27.51 GB")
        self.assertEqual(p_dict["total_binary_formatted"], "228.27 GiB")
        self.assertEqual(p_dict["used_binary_formatted"], "202.19 GiB")
        self.assertEqual(p_dict["raw_used_binary_formatted"], "202.65 GiB")
        self.assertEqual(p_dict["percent_used"], 88.6)

        disk = StorageDiskHealth(
            device_id="disk0s1",
            name="Macintosh HD (/)",
            media_type="NVMe SSD (Apple Fabric)",
            bus_type="Apple Fabric",
            smart_status="Verified",
            trim_supported=True,
            total_bytes=total_apfs,
            free_bytes=eff_free,
            used_bytes=eff_used,
            purgeable_bytes=purgeable,
            raw_used_bytes=raw_used,
            raw_free_bytes=raw_free,
            use_si_units=True,
        )
        d_dict = disk.to_dict()
        self.assertEqual(d_dict["total_formatted"], "245.11 GB")
        self.assertEqual(d_dict["used_formatted"], "217.10 GB")
        self.assertEqual(d_dict["free_formatted"], "28.01 GB")
        self.assertEqual(d_dict["purgeable_formatted"], "493.38 MB")
        self.assertEqual(d_dict["total_binary_formatted"], "228.27 GiB")
        self.assertEqual(d_dict["used_binary_formatted"], "202.19 GiB")

    def test_probe_macos_volume_metrics_reconciliation_and_consistency(self) -> None:
        """Valida que _probe_macos_volume_metrics reconcilia statvfs, diskutil plist e SPStorageDataType."""
        import plistlib
        from collections import namedtuple
        from src.infrastructure.macos.platform_adapter import (
            _probe_macos_volume_metrics,
            MacOSSystemProbeAdapter,
            MacOSHardwareProbeAdapter,
        )

        UsageTuple = namedtuple("usage", ["total", "used", "free"])
        fake_usage = UsageTuple(
            total=245107195904,
            used=217593780633,
            free=27513415271,
        )
        fake_plist = plistlib.dumps({
            "PurgeableSpace": 493384729,
            "APFSContainerSize": 245107195904,
            "APFSContainerFree": 27513415271,
        })
        fake_sp_json = json.dumps({
            "SPStorageDataType": [
                {
                    "_name": "Macintosh HD",
                    "mount_point": "/",
                    "size_in_bytes": 245107195904,
                    "free_space_in_bytes": 28006800000,
                    "physical_drive": {
                        "device_name": "APPLE SSD AP0256Z",
                        "protocol": "Apple Fabric",
                        "smart_status": "Verified",
                        "trim_support": "Yes",
                    },
                }
            ]
        }).encode("utf-8")

        def fake_subprocess_run(cmd, *args, **kwargs):
            m = MagicMock()
            m.returncode = 0
            if cmd and cmd[0] == "diskutil":
                m.stdout = fake_plist
            elif cmd and cmd[0] == "system_profiler":
                m.stdout = fake_sp_json
            elif cmd and cmd[0] == "tmutil":
                m.stdout = b"com.apple.TimeMachine.2026-11-23-120000.local\n"
            else:
                m.stdout = b""
            return m

        with patch("sys.platform", "darwin"), \
             patch("shutil.disk_usage", return_value=fake_usage), \
             patch("subprocess.run", side_effect=fake_subprocess_run):

            metrics = _probe_macos_volume_metrics("/")
            self.assertEqual(metrics["total_bytes"], 245107195904)
            self.assertEqual(metrics["raw_free_bytes"], 27513415271)
            self.assertEqual(metrics["raw_used_bytes"], 217593780633)
            self.assertEqual(metrics["purgeable_bytes"], 493384729)
            self.assertEqual(metrics["free_bytes"], 28006800000)
            self.assertEqual(metrics["used_bytes"], 217100395904)

            partitions = MacOSSystemProbeAdapter().get_partitions()
            root_part = next(p for p in partitions if p.mount_point == "/")
            self.assertTrue(root_part.use_si_units)
            self.assertEqual(root_part.total_formatted, "245.11 GB")
            self.assertEqual(root_part.used_formatted, "217.10 GB")
            self.assertEqual(root_part.free_formatted, "28.01 GB")
            self.assertEqual(root_part.raw_used_formatted, "217.59 GB")
            self.assertEqual(root_part.total_binary_formatted, "228.27 GiB")

            disks = MacOSHardwareProbeAdapter().get_disks_health()
            root_disk = disks[0]
            self.assertTrue(root_disk.use_si_units)
            self.assertEqual(root_disk.total_formatted, root_part.total_formatted)
            self.assertEqual(root_disk.used_formatted, root_part.used_formatted)
            self.assertEqual(root_disk.free_formatted, root_part.free_formatted)
            self.assertEqual(root_disk.purgeable_formatted, root_part.purgeable_formatted)


if __name__ == "__main__":
    unittest.main()
