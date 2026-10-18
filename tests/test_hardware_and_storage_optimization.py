# -*- coding: utf-8 -*-
"""Testes de Unidade e Integração para Saúde de Hardware e Otimização Inteligente de Storage com Guardrails."""
import unittest
from unittest.mock import patch, MagicMock

from src.domain.entities import (
    StorageDiskHealth,
    MemoryDiagnostics,
    GPUInfo,
    BatteryHealth,
    HardwareHealthInfo,
    StorageOptimizationResult,
    SystemExecutionReport,
    PartitionInfo,
)
from src.domain.ports import (
    IHardwareProbePort,
    IStorageOptimizationPort,
)
from src.domain.value_objects import OSPlatform, ExecutionMode
from src.infrastructure.windows.platform_adapter import (
    WindowsHardwareProbeAdapter,
    WindowsStorageOptimizationAdapter,
)
from src.infrastructure.macos.platform_adapter import (
    MacOSHardwareProbeAdapter,
    MacOSStorageOptimizationAdapter,
)
from src.application.orchestrator import OrchestratorService
from src.presentation.reporters.html_reporter import generate_html_report
from src.presentation.window.local_server import LocalControlPanelServer


class TestHardwareAndStorageDomainEntities(unittest.TestCase):
    """Testa entidades de domínio e serialização em to_dict()."""

    def test_storage_disk_health_creation_and_dict(self):
        disk = StorageDiskHealth(
            device_id="disk0",
            name="Samsung 980 PRO NVMe 1TB",
            media_type="NVMe SSD",
            bus_type="NVMe",
            smart_status="Verified",
            trim_supported=True,
            wear_percentage=2.5,
            temperature_celsius=38,
            power_on_hours=1450,
            is_ssd=True,
            is_nvme=True,
            recommended_action="TRIM / Retrim",
            total_bytes=1000204886016,
            free_bytes=450204886016,
        )
        d = disk.to_dict()
        self.assertEqual(d["device_id"], "disk0")
        self.assertTrue(d["is_ssd"])
        self.assertTrue(d["is_nvme"])
        self.assertTrue(d["trim_supported"])
        self.assertIn("GB", d["total_formatted"])
        self.assertEqual(d["smart_status"], "Verified")

    def test_memory_diagnostics_thrashing_detection(self):
        mem = MemoryDiagnostics(
            total_bytes=16 * 1024 * 1024 * 1024,
            used_bytes=14 * 1024 * 1024 * 1024,
            free_bytes=2 * 1024 * 1024 * 1024,
            load_percentage=89.5,
            pressure_level="Critical",
            swap_total_bytes=8 * 1024 * 1024 * 1024,
            swap_used_bytes=6 * 1024 * 1024 * 1024,
            swap_thrashing_detected=True,
            recommendations=["Fechar abas pesadas do navegador"],
        )
        d = mem.to_dict()
        self.assertEqual(d["pressure_level"], "Critical")
        self.assertTrue(d["swap_thrashing_detected"])
        self.assertIn("GB", d["total_formatted"])
        self.assertIn("GB", d["swap_used_formatted"])
        self.assertEqual(len(d["recommendations"]), 1)

    def test_gpu_info_integrated_vs_dedicated(self):
        gpu_apple = GPUInfo(
            name="Apple M3 Max",
            vendor="Apple",
            vram_bytes=0,
            driver_version="Metal 3",
            status="Ativo",
            is_integrated=True,
        )
        d_apple = gpu_apple.to_dict()
        self.assertEqual(d_apple["vram_formatted"], "Compartilhada / Unificada")

        gpu_nv = GPUInfo(
            name="NVIDIA GeForce RTX 4080",
            vendor="NVIDIA",
            vram_bytes=16 * 1024 * 1024 * 1024,
            driver_version="551.86",
            status="OK",
            is_integrated=False,
        )
        d_nv = gpu_nv.to_dict()
        self.assertIn("16.00 GB", d_nv["vram_formatted"])

    def test_battery_health_desktop_vs_laptop(self):
        batt_desk = BatteryHealth(has_battery=False)
        self.assertFalse(batt_desk.has_battery)
        self.assertIn("Desktop", batt_desk.condition)

        batt_lap = BatteryHealth(
            has_battery=True,
            cycle_count=320,
            health_percentage=88.5,
            condition="Normal",
            is_charging=True,
        )
        d = batt_lap.to_dict()
        self.assertTrue(d["has_battery"])
        self.assertEqual(d["cycle_count"], 320)
        self.assertTrue(d["is_charging"])

    def test_hardware_health_info_aggregation(self):
        hw = HardwareHealthInfo(
            disks=[
                StorageDiskHealth(
                    device_id="0",
                    name="NVMe Main",
                    media_type="NVMe SSD",
                    bus_type="NVMe",
                    smart_status="Healthy",
                    trim_supported=True,
                    is_ssd=True,
                    is_nvme=True,
                )
            ],
            memory=MemoryDiagnostics(
                total_bytes=16 * 1024 * 1024 * 1024,
                used_bytes=8 * 1024 * 1024 * 1024,
                free_bytes=8 * 1024 * 1024 * 1024,
                load_percentage=50.0,
                pressure_level="Normal",
                swap_total_bytes=0,
                swap_used_bytes=0,
                swap_thrashing_detected=False,
            ),
            overall_status="Saudável",
            critical_alerts=[],
        )
        d = hw.to_dict()
        self.assertEqual(d["overall_status"], "Saudável")
        self.assertEqual(len(d["disks"]), 1)
        self.assertIsNotNone(d["memory"])

    def test_system_execution_report_includes_hardware(self):
        rep = SystemExecutionReport(
            session_id="test_session",
            executed_at="18/10/2026 12:00:00",
            os_platform="macos",
            os_version="macOS 15.0",
            execution_mode="real",
            is_admin=True,
            scan_scope="smart_fast",
            hardware_health=HardwareHealthInfo(
                disks=[],
                overall_status="Saudável",
            ),
            storage_optimizations=[
                StorageOptimizationResult(
                    drive="/",
                    media_type="APFS SSD",
                    action_taken="Manutenção APFS",
                    success=True,
                    message="Otimização concluída",
                )
            ],
        )
        d = rep.to_dict()
        self.assertIn("hardware_health", d)
        self.assertIn("storage_optimizations", d)
        self.assertEqual(d["hardware_health"]["overall_status"], "Saudável")
        self.assertEqual(len(d["storage_optimizations"]), 1)


class TestWindowsStorageGuardrails(unittest.TestCase):
    """Testa os Guardrails de 4 Camadas para NVMe/SSD e Human-in-the-Loop Safety no Windows."""

    def setUp(self):
        self.adapter = WindowsStorageOptimizationAdapter()

    @patch("subprocess.run")
    def test_guardrail_layer_1_detects_nvme_ssd(self, mock_run):
        # Simula Camada 1: Get-PhysicalDisk retornando NVMe
        mock_run.return_value = MagicMock(
            stdout=b'{"MediaType": "SSD", "BusType": "NVMe", "FriendlyName": "Samsung 980"}'
        )
        label, is_ssd, is_nvme, logs = self.adapter.detect_media_type_with_guardrails("C:")
        self.assertTrue(is_ssd)
        self.assertTrue(is_nvme)
        self.assertIn("NVMe", label)
        self.assertTrue(any("Camada 1" in l for l in logs))

    @patch("subprocess.run")
    def test_guardrail_blocks_defrag_on_nvme_and_runs_trim(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout=b'{"MediaType": "SSD", "BusType": "NVMe", "FriendlyName": "WD Black SN850"}'
        )
        # Execução Real em NVMe
        res = self.adapter.optimize_volume(drive="C:", mode=ExecutionMode.REAL)
        self.assertTrue(res.success)
        self.assertIn("TRIM", res.action_taken)
        # Garante que desfragmentação física foi estritamente proibida
        self.assertNotIn("Defrag", res.action_taken)
        self.assertTrue(any("PROIBIDA para SSD/NVMe" in g for g in res.guardrail_checks))

    @patch("subprocess.run")
    def test_guardrail_dry_run_on_ssd_performs_no_destructive_io(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout=b'{"MediaType": "SSD", "BusType": "SATA", "FriendlyName": "Crucial MX500"}'
        )
        res = self.adapter.optimize_volume(drive="D:", mode=ExecutionMode.DRY_RUN)
        self.assertTrue(res.success)
        self.assertIn("Simulação", res.action_taken)
        self.assertEqual(res.fragmentation_before, 0.0)

    @patch("subprocess.run")
    def test_guardrail_layer_4_fail_safe_default_assumes_ssd_on_error(self, mock_run):
        # Simula erro de comando em todas as camadas
        mock_run.side_effect = Exception("PowerShell execution policy blocked / command error")
        label, is_ssd, is_nvme, logs = self.adapter.detect_media_type_with_guardrails("E:")
        # Camada 4: Fail-Safe Default Absoluto DEVE assumir SSD
        self.assertTrue(is_ssd)
        self.assertTrue(any("Fail-Safe Default Absoluto Ativo" in l for l in logs))

        # E ao otimizar, DEVE aplicar TRIM e bloquear defrag tradicional
        res = self.adapter.optimize_volume(drive="E:", mode=ExecutionMode.DRY_RUN)
        self.assertTrue(res.success)
        self.assertIn("TRIM", res.action_taken)

    @patch("subprocess.run")
    def test_human_in_the_loop_blocks_hdd_defrag_without_confirmation(self, mock_run):
        # Simula identificação unânime de HDD magnético
        def side_effect(cmd, *args, **kwargs):
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
            if "Get-PhysicalDisk" in cmd_str:
                return MagicMock(stdout=b'{"MediaType": "HDD", "BusType": "SATA", "FriendlyName": "Seagate Barracuda"}')
            if "MSFT_PhysicalDisk" in cmd_str:
                return MagicMock(stdout=b'{"SpindleSpeed": 7200, "SeekPenalty": true}')
            return MagicMock(stdout=b"")

        mock_run.side_effect = side_effect

        # Sem confirmação do usuário (user_confirmed=False)
        res = self.adapter.optimize_volume(drive="D:", user_confirmed=False, mode=ExecutionMode.REAL)
        self.assertFalse(res.success)
        self.assertIn("Bloqueado por Segurança", res.action_taken)
        self.assertIn("DISCO RÍGIDO MECÂNICO (HDD)", res.message)
        self.assertIn("Confirma que este disco é de fato um HDD", res.message)

    @patch("subprocess.run")
    def test_human_in_the_loop_allows_hdd_defrag_with_confirmation(self, mock_run):
        def side_effect(cmd, *args, **kwargs):
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
            if "Get-PhysicalDisk" in cmd_str:
                return MagicMock(stdout=b'{"MediaType": "HDD", "BusType": "SATA", "FriendlyName": "WDC Blue 2TB"}')
            if "MSFT_PhysicalDisk" in cmd_str:
                return MagicMock(stdout=b'{"SpindleSpeed": 5400, "SeekPenalty": true}')
            return MagicMock(stdout=b"")

        mock_run.side_effect = side_effect

        # Com confirmação explícita do usuário (user_confirmed=True)
        res = self.adapter.optimize_volume(drive="D:", user_confirmed=True, mode=ExecutionMode.REAL)
        self.assertTrue(res.success)
        self.assertIn("HDD Confirmado", res.action_taken)
        self.assertTrue(res.user_confirmed)

    def test_drive_letter_sanitization_neutralizes_command_injection(self):
        self.assertEqual(self.adapter._sanitize_drive_letter("C; Stop-Computer"), "C")
        self.assertEqual(self.adapter._sanitize_drive_letter("D & calc.exe"), "D")
        self.assertEqual(self.adapter._sanitize_drive_letter("E | rm -rf"), "E")
        self.assertEqual(self.adapter._sanitize_drive_letter("; Invoke-Expression"), "C")
        self.assertEqual(self.adapter._sanitize_drive_letter(""), "C")
        self.assertEqual(self.adapter._sanitize_drive_letter(None), "C")
        self.assertEqual(self.adapter._sanitize_drive_letter("123"), "C")
        self.assertEqual(self.adapter._sanitize_drive_letter("F:"), "F")


class TestMacOSStorageAndHardwareAdapters(unittest.TestCase):
    """Testa adaptação para macOS com APFS maintenance e hardware probe."""

    def setUp(self):
        self.opt_adapter = MacOSStorageOptimizationAdapter()
        self.hw_adapter = MacOSHardwareProbeAdapter()

    def test_macos_storage_analyze_blocks_traditional_defrag(self):
        analysis = self.opt_adapter.analyze_volume("/")
        self.assertTrue(analysis["is_ssd"])
        self.assertIn("APFS", analysis["media_type"])
        self.assertEqual(analysis["fragmentation_percent"], 0.0)
        self.assertTrue(any("Copy-On-Write" in g for g in analysis["guardrail_checks"]))

    def test_macos_storage_optimize_dry_run(self):
        res = self.opt_adapter.optimize_volume("/", mode=ExecutionMode.DRY_RUN)
        self.assertTrue(res.success)
        self.assertIn("Simulação", res.action_taken)
        self.assertEqual(res.fragmentation_before, 0.0)

    @patch("subprocess.run")
    def test_macos_storage_optimize_real_executes_verify_and_thin(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout=b"The volume Macintosh HD appears to be OK.")
        res = self.opt_adapter.optimize_volume("/", mode=ExecutionMode.REAL)
        self.assertTrue(res.success)
        self.assertIn("Manutenção APFS", res.action_taken)
        self.assertIn("snapshots", res.action_taken.lower())

    def test_macos_hardware_probe_returns_valid_aggregates(self):
        hw = self.hw_adapter.get_hardware_health()
        self.assertIsInstance(hw, HardwareHealthInfo)
        self.assertTrue(len(hw.disks) >= 1)
        self.assertIsNotNone(hw.memory)
        self.assertTrue(hw.memory.total_bytes > 0)
        self.assertTrue(len(hw.gpus) >= 1)
        self.assertIsNotNone(hw.battery)

    def test_macos_target_sanitization_neutralizes_flags_and_injection(self):
        self.assertEqual(self.opt_adapter._sanitize_target("--help"), "/")
        self.assertEqual(self.opt_adapter._sanitize_target("-all"), "/")
        self.assertEqual(self.opt_adapter._sanitize_target("; rm -rf /"), "/")
        self.assertEqual(self.opt_adapter._sanitize_target(""), "/")
        self.assertEqual(self.opt_adapter._sanitize_target(None), "/")
        self.assertEqual(self.opt_adapter._sanitize_target("/Volumes/ExternalSSD"), "/Volumes/ExternalSSD")
        self.assertEqual(self.opt_adapter._sanitize_target("disk1s1"), "disk1s1")


class TestOrchestratorAndServerIntegration(unittest.TestCase):
    """Testa integração com a camada de aplicação e endpoints HTTP locais."""

    def setUp(self):
        self.orchestrator = OrchestratorService()
        self.server = LocalControlPanelServer(orchestrator=self.orchestrator)

    def test_orchestrator_initial_context_includes_hardware_health(self):
        ctx = self.orchestrator.get_initial_context(OSPlatform.MACOS)
        self.assertIn("hardware_health", ctx)
        self.assertIn("overall_status", ctx["hardware_health"])

    def test_orchestrator_execute_plan_populates_hardware_in_report(self):
        plan = self.orchestrator.build_default_plan(
            os_platform=OSPlatform.MACOS,
            mode=ExecutionMode.DRY_RUN,
        )
        # Limita varredura para ser ultrarrápida no teste
        plan.selected_cleanup_rule_ids = []
        plan.selected_tweak_ids = []
        plan.run_disk_scan = False
        plan.run_cloud_diagnostic = False

        rep = self.orchestrator.execute_plan(plan)
        self.assertIsNotNone(rep.hardware_health)
        self.assertIn(rep.hardware_health.overall_status, ("Saudável", "Atenção", "Crítico"))
        d = rep.to_dict()
        self.assertIn("hardware_health", d)

    def test_server_optimize_disk_endpoint_success(self):
        # Simula chamada AJAX para /api/optimize-disk
        status, ctype, body = self.server.dispatch_request(
            method="POST",
            raw_path="/api/optimize-disk",
            payload={"drive": "/", "confirm_hdd": False, "mode": "dry_run"},
            background_exec=False,
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["success"])
        self.assertIn("result", body)
        self.assertIn("action_taken", body)

    def test_server_optimize_disk_endpoint_requires_hdd_confirmation(self):
        # Se for no Windows e simular HDD:
        win_opt_adapter = MagicMock()
        win_opt_adapter.optimize_volume.return_value = StorageOptimizationResult(
            drive="D:",
            media_type="HDD",
            action_taken="Bloqueado por Segurança (Aguardando Confirmação de HDD)",
            success=False,
            message="Confirma que é HDD mecânico?",
            user_confirmed=False,
        )
        self.orchestrator.win_storage = win_opt_adapter
        self.orchestrator.last_plan = self.orchestrator.build_default_plan(os_platform=OSPlatform.WINDOWS)

        status, ctype, body = self.server.dispatch_request(
            method="POST",
            raw_path="/api/optimize-disk",
            payload={"drive": "D:", "confirm_hdd": False, "mode": "real"},
            background_exec=False,
        )
        self.assertEqual(status, 200)
        self.assertFalse(body["success"])
        self.assertIn("Bloqueado por Segurança", body["action_taken"])

    def test_server_optimize_disk_endpoint_sanitizes_malicious_drive_input(self):
        status, ctype, body = self.server.dispatch_request(
            method="POST",
            raw_path="/api/optimize-disk",
            payload={"drive": "C; Stop-Computer", "confirm_hdd": False, "mode": "dry_run"},
            background_exec=False,
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["success"])
        self.assertIn("result", body)

    def test_html_report_renders_hardware_section_and_tabs(self):
        rep = SystemExecutionReport(
            session_id="hw_test",
            executed_at="18/10/2026 15:00:00",
            os_platform="macos",
            os_version="macOS Sonoma",
            execution_mode="real",
            is_admin=True,
            scan_scope="smart_fast",
            hardware_health=HardwareHealthInfo(
                disks=[
                    StorageDiskHealth(
                        device_id="disk0",
                        name="Macintosh HD",
                        media_type="NVMe SSD (Apple Fabric)",
                        bus_type="Apple Fabric",
                        smart_status="Verified",
                        trim_supported=True,
                        is_ssd=True,
                        is_nvme=True,
                    )
                ],
                memory=MemoryDiagnostics(
                    total_bytes=16 * 1024 * 1024 * 1024,
                    used_bytes=8 * 1024 * 1024 * 1024,
                    free_bytes=8 * 1024 * 1024 * 1024,
                    load_percentage=50.0,
                    pressure_level="Normal",
                    swap_total_bytes=0,
                    swap_used_bytes=0,
                    swap_thrashing_detected=False,
                ),
                overall_status="Saudável",
            ),
        )
        path = generate_html_report(rep, output_filename="outputs/test_hw_report.html")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("tab-hardware", content)
        self.assertIn("Saúde de Hardware & Otimização de Storage", content)
        self.assertIn("Guardrails Anti-Degradação de NVMe", content)
        self.assertIn("TRIM / Retrim", content)
        self.assertIn("renderHardwareAndStorage", content)
        self.assertIn("optimizeDisk", content)


if __name__ == "__main__":
    unittest.main()
