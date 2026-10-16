# -*- coding: utf-8 -*-
"""Serviço Orquestrador da Aplicação (Use Cases de Limpeza, Scanner, Tweaks e Undo)."""
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable

from src.domain.entities import (
    SystemExecutionReport,
    StateSnapshot,
    TweakExecutionRecord,
    AutonomousCleanupEntry,
)
from src.domain.ports import (
    ISystemProbePort,
    IActiveAppsPort,
    IFileSystemCleanerPort,
    IDiskScannerPort,
    ISystemTweakPort,
    ICloudAndPackagesPort,
    ISnapshotRepositoryPort,
)
from src.domain.value_objects import OSPlatform, ExecutionMode, ScanScope, format_bytes
from src.application.dtos import ExecutionPlanDTO

from src.infrastructure.windows.platform_adapter import (
    WindowsSystemProbeAdapter,
    WindowsActiveAppsAdapter,
    WindowsCloudAndPackagesAdapter,
)
from src.infrastructure.macos.platform_adapter import (
    MacOSSystemProbeAdapter,
    MacOSActiveAppsAdapter,
    MacOSCloudAndPackagesAdapter,
)
from src.infrastructure.filesystem.autonomous_cleaner import AutonomousCleanerAdapter
from src.infrastructure.filesystem.disk_scanner import DiskScannerAdapter
from src.infrastructure.persistence.snapshot_repository import SnapshotRepository
from src.infrastructure.tweaks_adapter import SystemTweakAdapter


ProgressCallback = Callable[[int, str, str], None]


class OrchestratorService:
    """Coordena os módulos de System Probe, Limpeza Autônoma, Scanner 5 Camadas, Tweaks e Undo."""

    def __init__(
        self,
        cleaner: Optional[IFileSystemCleanerPort] = None,
        scanner: Optional[IDiskScannerPort] = None,
        snapshot_repo: Optional[ISnapshotRepositoryPort] = None,
        tweak_adapter: Optional[ISystemTweakPort] = None,
    ) -> None:
        self.win_probe = WindowsSystemProbeAdapter()
        self.win_active = WindowsActiveAppsAdapter()
        self.win_cloud = WindowsCloudAndPackagesAdapter()

        self.mac_probe = MacOSSystemProbeAdapter()
        self.mac_active = MacOSActiveAppsAdapter()
        self.mac_cloud = MacOSCloudAndPackagesAdapter()

        host_probe = (
            self.win_probe
            if OSPlatform.detect_current() == OSPlatform.WINDOWS
            else self.mac_probe
        )
        self.cleaner = cleaner or AutonomousCleanerAdapter()
        self.scanner = scanner or DiskScannerAdapter()
        self.snapshot_repo = snapshot_repo or SnapshotRepository()
        self.tweak_adapter = tweak_adapter or SystemTweakAdapter(system_probe=host_probe)
        self.last_report: Optional[SystemExecutionReport] = None

    def _get_os_ports(
        self, os_platform: OSPlatform
    ) -> tuple[ISystemProbePort, IActiveAppsPort, ICloudAndPackagesPort]:
        if os_platform == OSPlatform.WINDOWS:
            return self.win_probe, self.win_active, self.win_cloud
        return self.mac_probe, self.mac_active, self.mac_cloud

    def get_initial_context(self, os_platform: Optional[OSPlatform] = None) -> Dict[str, Any]:
        """Retorna dados iniciais do sistema para popular a Janela de Configuração."""
        target_os = os_platform or OSPlatform.detect_current()
        probe, _, _ = self._get_os_ports(target_os)
        partitions = probe.get_partitions()
        rules = self.cleaner.get_cleanup_rules(target_os)
        tweaks = self.tweak_adapter.list_available_tweaks(target_os)
        snapshots = self.snapshot_repo.list_snapshots()

        return {
            "detected_os": OSPlatform.detect_current().value,
            "selected_os": target_os.value,
            "os_version": probe.get_os_version_string(),
            "is_admin": probe.is_admin_or_root(),
            "total_ram_kb": probe.get_total_ram_kb(),
            "partitions": [p.to_dict() for p in partitions],
            "cleanup_rules": [r.to_dict() for r in rules],
            "tweaks": [t.to_dict() for t in tweaks],
            "snapshots": [s.to_dict() for s in snapshots],
        }

    def build_default_plan(
        self,
        os_platform: Optional[OSPlatform] = None,
        mode: ExecutionMode = ExecutionMode.DRY_RUN,
        preset: str = "standard",
    ) -> ExecutionPlanDTO:
        """Constrói um plano padrão recomendado para execução autônoma ou CLI headless."""
        target_os = os_platform or OSPlatform.detect_current()
        rules = self.cleaner.get_cleanup_rules(target_os)
        default_rule_ids = [r.id for r in rules if r.default_enabled]

        tweaks = self.tweak_adapter.list_available_tweaks(target_os)
        if preset == "minimal":
            default_tweak_ids = [t.id for t in tweaks if t.preset == "minimal"]
        elif preset == "standard":
            default_tweak_ids = [t.id for t in tweaks if t.preset in ("minimal", "standard")]
        elif preset == "advanced":
            default_tweak_ids = [t.id for t in tweaks if t.preset in ("minimal", "standard", "advanced")]
        else:
            default_tweak_ids = []

        return ExecutionPlanDTO(
            os_platform=target_os,
            mode=mode,
            scan_scope=ScanScope.SMART_FAST,
            selected_cleanup_rule_ids=default_rule_ids,
            auto_clean_orphans=False,
            selected_tweak_ids=default_tweak_ids,
            check_updates=False,
            run_disk_scan=True,
            run_cloud_diagnostic=True,
        )

    def _resolve_scan_targets(
        self,
        plan: ExecutionPlanDTO,
        partitions_mount_points: List[str],
    ) -> List[str]:
        if plan.scan_scope == ScanScope.SPECIFIC_DRIVE and plan.specific_drive:
            if os.path.exists(plan.specific_drive):
                return [plan.specific_drive]

        if plan.scan_scope == ScanScope.FULL_DISKS:
            return partitions_mount_points or [os.path.expanduser("~")]

        user_home = os.path.expanduser("~")
        if plan.os_platform == OSPlatform.WINDOWS:
            appdata_root = os.path.join(os.environ.get("USERPROFILE", user_home), "AppData")
            if plan.scan_scope == ScanScope.APPDATA_LIBRARY:
                return [appdata_root] if os.path.exists(appdata_root) else [user_home]
            # SMART_FAST no Windows
            candidates = [
                appdata_root,
                os.path.join(os.environ.get("USERPROFILE", user_home), "Downloads"),
                os.environ.get("ProgramFiles", r"C:\Program Files"),
                os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
            ]
            existing = [p for p in candidates if p and os.path.exists(p)]
            return existing if existing else [user_home]
        else:
            # macOS
            lib_root = os.path.expanduser("~/Library")
            if plan.scan_scope == ScanScope.APPDATA_LIBRARY:
                return [lib_root] if os.path.exists(lib_root) else [user_home]
            # SMART_FAST no macOS (focado nas pastas de maior acúmulo sem travar o sistema)
            candidates = [
                os.path.expanduser("~/Library/Application Support"),
                os.path.expanduser("~/Library/Containers"),
                os.path.expanduser("~/Library/Saved Application State"),
                os.path.expanduser("~/Library/Caches"),
                os.path.expanduser("~/Library/Logs"),
                os.path.expanduser("~/Downloads"),
                "/Applications",
                os.path.expanduser("~/Applications"),
            ]
            existing = [p for p in candidates if os.path.exists(p)]
            return existing if existing else [user_home]

    def execute_plan(
        self,
        plan: ExecutionPlanDTO,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> SystemExecutionReport:
        """Executa o ciclo completo de limpeza autônoma, varredura profunda, tweaks e diagnóstico."""
        logs: List[str] = []

        def emit(pct: int, step: str, msg: str) -> None:
            timestamped = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
            logs.append(timestamped)
            if progress_cb:
                progress_cb(pct, step, timestamped)

        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        probe, active_port, cloud_port = self._get_os_ports(plan.os_platform)

        emit(
            5,
            "Mapeando Sistema e Partições",
            f"Iniciando sessão {session_id} ({plan.os_platform.value.upper()} | Modo: {plan.mode.value.upper()})",
        )
        partitions = probe.get_partitions()
        all_drives = [p.mount_point for p in partitions]
        emit(
            12,
            "Mapeando Sistema e Partições",
            f"Partições/Volumes detectados: {len(partitions)} ({', '.join(p.drive_letter for p in partitions)})",
        )

        # 1. Motor de Limpeza Autônoma
        autonomous_entries: List[AutonomousCleanupEntry] = []
        total_freed = 0
        total_files_removed = 0

        available_rules = {r.id: r for r in self.cleaner.get_cleanup_rules(plan.os_platform)}
        selected_rules = [
            available_rules[rid]
            for rid in plan.selected_cleanup_rule_ids
            if rid in available_rules
        ]

        if selected_rules:
            emit(
                20,
                "Executando Limpeza Autônoma de Caches e Temporários",
                f"Processando {len(selected_rules)} categorias de limpeza autônoma...",
            )
            for idx, rule in enumerate(selected_rules, 1):
                entry = self.cleaner.execute_rule(rule, mode=plan.mode)
                autonomous_entries.append(entry)
                total_freed += entry.bytes_freed
                total_files_removed += entry.files_removed
                pct = 20 + int((idx / max(len(selected_rules), 1)) * 20)
                emit(
                    pct,
                    f"Limpeza: {rule.name}",
                    f"Regra '{rule.name}': {entry.bytes_freed_formatted} ({entry.files_removed} arquivos) [{entry.status}]",
                )
        else:
            emit(35, "Limpeza Autônoma", "Nenhuma regra de limpeza autônoma selecionada.")

        # 2. Detecção de Softwares Ativos (5 Camadas) + Scanner de Disco
        top_occupants = []
        clean_suggestions = []
        installed_apps = []
        active_indicators_count = 0

        if plan.run_disk_scan:
            emit(
                45,
                "Algoritmo Anti-Falsos Positivos (5 Camadas)",
                "Mapeando indicadores de softwares ativos nas 5 camadas de proteção...",
            )
            active_indicators = active_port.get_active_indicators(all_drives)
            active_indicators_count = len(active_indicators)
            emit(
                52,
                "Algoritmo Anti-Falsos Positivos (5 Camadas)",
                f"Softwares e bundles ativos protegidos: {active_indicators_count} termos verificados.",
            )

            scan_targets = self._resolve_scan_targets(plan, all_drives)
            emit(
                58,
                "Scanner Profundo de Órfãos, Apps e Grandes Arquivos",
                f"Analisando diretórios-alvo ({len(scan_targets)} locais)...",
            )
            top_occupants, clean_suggestions, installed_apps = self.scanner.scan_and_evaluate(
                target_paths=scan_targets,
                active_indicators=active_indicators,
                partitions=partitions,
                os_platform=plan.os_platform,
                top_n=100,
            )
            emit(
                72,
                "Scanner Concluído",
                f"Encontrados: {len(clean_suggestions)} resíduos/caches, {len(installed_apps)} apps instalados e {len(top_occupants)} maiores arquivos/pastas.",
            )

            # Se o usuário marcou auto_clean_orphans, limpa as pastas órfãs verificadas
            if plan.auto_clean_orphans:
                orphan_paths = [c.path for c in clean_suggestions if c.is_orphan]
                if orphan_paths:
                    emit(
                        76,
                        "Auto-Limpeza de Pastas Órfãs Verificadas",
                        f"Limpando {len(orphan_paths)} pastas órfãs verificadas...",
                    )
                    orphan_entry = self.cleaner.clean_specific_paths(
                        orphan_paths,
                        mode=plan.mode,
                        category_label="Remoção Automática de Pastas Órfãs (5 Camadas)",
                    )
                    autonomous_entries.append(orphan_entry)
                    total_freed += orphan_entry.bytes_freed
                    total_files_removed += orphan_entry.files_removed
                    for c in clean_suggestions:
                        if c.is_orphan:
                            c.was_auto_cleaned = plan.mode == ExecutionMode.REAL

        # 3. Otimizações do Sistema (WinUtil Sanitizado / macOS Tweaks) + Snapshot Local
        tweaks_executed: List[TweakExecutionRecord] = []
        snapshot_id: Optional[str] = None

        all_tweaks_map = {
            t.id: t for t in self.tweak_adapter.list_available_tweaks(plan.os_platform)
        }
        selected_tweaks = [
            all_tweaks_map[tid]
            for tid in plan.selected_tweak_ids
            if tid in all_tweaks_map
        ]

        if selected_tweaks:
            snapshot_id = f"snapshot_{session_id}"
            emit(
                80,
                "Criando Snapshot Reversível (Undo)",
                f"Capturando estado original de {len(selected_tweaks)} otimizações em {snapshot_id}.json...",
            )
            snapshot_entries: Dict[str, Any] = {}
            for tw in selected_tweaks:
                snapshot_entries[tw.id] = self.tweak_adapter.capture_current_state(tw)

            snapshot = StateSnapshot(
                snapshot_id=snapshot_id,
                created_at=datetime.now().isoformat(),
                os_platform=plan.os_platform.value,
                mode=plan.mode.value,
                entries=snapshot_entries,
                tweaks_applied=[t.id for t in selected_tweaks],
                description=f"Snapshot automático pré-otimização ({len(selected_tweaks)} tweaks)",
            )
            self.snapshot_repo.save_snapshot(snapshot)

            for idx, tw in enumerate(selected_tweaks, 1):
                rec = self.tweak_adapter.apply_tweak(tw, mode=plan.mode)
                tweaks_executed.append(rec)
                pct = 82 + int((idx / max(len(selected_tweaks), 1)) * 10)
                emit(pct, f"Otimização: {tw.name}", f"Tweak '{tw.id}': {rec.message}")

        # 4. Cloud Storage & Atualizações de Softwares
        cloud_diagnostics = []
        if plan.run_cloud_diagnostic:
            emit(93, "Diagnóstico de Armazenamento em Nuvem", "Analisando impacto de OneDrive / iCloud Drive...")
            cloud_diagnostics = cloud_port.analyze_cloud_storage()

        outdated_apps = []
        if plan.check_updates:
            emit(96, "Consultando Atualizações de Apps", "Verificando pacotes desatualizados (winget / brew)...")
            outdated_apps = cloud_port.check_outdated_packages()
            emit(98, "Atualizações Verificadas", f"Pacotes desatualizados encontrados: {len(outdated_apps)}")

        potential_extra = sum(
            c.size for c in clean_suggestions if not c.was_auto_cleaned
        )

        # Atualiza estado final das partições
        final_partitions = probe.get_partitions() or partitions

        emit(
            100,
            "Concluído com Sucesso!",
            f"Finalizado! Espaço trabalhado na limpeza autônoma: {format_bytes(total_freed)} "
            f"| Potencial adicional mapeado: {format_bytes(potential_extra)}.",
        )

        report = SystemExecutionReport(
            session_id=session_id,
            executed_at=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            os_platform=plan.os_platform.value,
            os_version=probe.get_os_version_string(),
            execution_mode=plan.mode.value,
            is_admin=probe.is_admin_or_root(),
            scan_scope=plan.scan_scope.value,
            total_bytes_freed=total_freed,
            total_files_removed=total_files_removed,
            potential_extra_bytes=potential_extra,
            snapshot_id=snapshot_id,
            partitions=final_partitions,
            autonomous_cleanups=autonomous_entries,
            clean_suggestions=clean_suggestions,
            installed_apps=installed_apps,
            top_occupants=top_occupants,
            tweaks_executed=tweaks_executed,
            cloud_diagnostics=cloud_diagnostics,
            outdated_apps=outdated_apps,
            active_indicators_count=active_indicators_count,
            execution_logs=logs,
        )
        self.last_report = report
        return report

    def clean_selected_items(
        self,
        paths: List[str],
        mode: ExecutionMode = ExecutionMode.REAL,
    ) -> AutonomousCleanupEntry:
        """Executa a limpeza de pastas órfãs ou caches marcados pelo usuário no Dashboard."""
        entry = self.cleaner.clean_specific_paths(
            paths=paths,
            mode=mode,
            category_label="Limpeza Interativa pelo Dashboard",
        )
        if self.last_report:
            self.last_report.autonomous_cleanups.append(entry)
            self.last_report.total_bytes_freed += entry.bytes_freed
            self.last_report.total_files_removed += entry.files_removed
            cleaned_set = {os.path.abspath(p) for p in entry.target_paths}
            for item in self.last_report.clean_suggestions:
                if os.path.abspath(item.path) in cleaned_set:
                    item.was_auto_cleaned = mode == ExecutionMode.REAL
        return entry

    def revert_snapshot(
        self,
        snapshot_id: str = "latest",
        mode: ExecutionMode = ExecutionMode.REAL,
    ) -> List[TweakExecutionRecord]:
        """Reverte todos os Tweaks contidos em um Snapshot salvo (Undo completo)."""
        snapshot = self.snapshot_repo.get_snapshot(snapshot_id)
        if not snapshot:
            return []

        all_tweaks_map = {t.id: t for t in self.tweak_adapter.list_available_tweaks(None)}
        records: List[TweakExecutionRecord] = []

        for tid in snapshot.tweaks_applied:
            tweak_def = all_tweaks_map.get(tid)
            if not tweak_def:
                continue
            prev_state = snapshot.entries.get(tid)
            rec = self.tweak_adapter.revert_tweak(tweak_def, previous_state=prev_state, mode=mode)
            records.append(rec)

        return records
