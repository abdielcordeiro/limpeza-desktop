# -*- coding: utf-8 -*-
"""Serviço Orquestrador da Aplicação (Use Cases de Limpeza, Scanner, Tweaks e Undo)."""
import os
import sys
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable

from src.domain.entities import (
    SystemExecutionReport,
    StateSnapshot,
    TweakExecutionRecord,
    AutonomousCleanupEntry,
    CleanableItem,
    OccupantItem,
    HardwareHealthInfo,
    LongevityRecommendation,
    LongevityScoreReport,
    StorageOptimizationResult,
)
from src.domain.ports import (
    ISystemProbePort,
    IActiveAppsPort,
    IFileSystemCleanerPort,
    IDiskScannerPort,
    ISystemTweakPort,
    ICloudAndPackagesPort,
    ISnapshotRepositoryPort,
    IHardwareProbePort,
    IStorageOptimizationPort,
)
from src.domain.value_objects import OSPlatform, ExecutionMode, ScanScope, format_bytes
from src.application.dtos import ExecutionPlanDTO

from src.infrastructure.windows.platform_adapter import (
    WindowsSystemProbeAdapter,
    WindowsActiveAppsAdapter,
    WindowsCloudAndPackagesAdapter,
    WindowsHardwareProbeAdapter,
    WindowsStorageOptimizationAdapter,
)
from src.infrastructure.macos.platform_adapter import (
    MacOSSystemProbeAdapter,
    MacOSActiveAppsAdapter,
    MacOSCloudAndPackagesAdapter,
    MacOSHardwareProbeAdapter,
    MacOSStorageOptimizationAdapter,
)
from src.infrastructure.filesystem.autonomous_cleaner import AutonomousCleanerAdapter
from src.infrastructure.filesystem.disk_scanner import DiskScannerAdapter
from src.infrastructure.persistence.snapshot_repository import SnapshotRepository
from src.infrastructure.tweaks_adapter import SystemTweakAdapter


ProgressCallback = Callable[[int, str, str], None]


class OrchestratorService:
    """Coordena os módulos de System Probe, Limpeza Autônoma, Scanner 5 Camadas, Tweaks, Hardware e Undo."""

    def __init__(
        self,
        cleaner: Optional[IFileSystemCleanerPort] = None,
        scanner: Optional[IDiskScannerPort] = None,
        snapshot_repo: Optional[ISnapshotRepositoryPort] = None,
        tweak_adapter: Optional[ISystemTweakPort] = None,
        win_hw: Optional[IHardwareProbePort] = None,
        win_storage: Optional[IStorageOptimizationPort] = None,
        mac_hw: Optional[IHardwareProbePort] = None,
        mac_storage: Optional[IStorageOptimizationPort] = None,
    ) -> None:
        self.win_probe = WindowsSystemProbeAdapter()
        self.win_active = WindowsActiveAppsAdapter()
        self.win_cloud = WindowsCloudAndPackagesAdapter()
        self.win_hw = win_hw or WindowsHardwareProbeAdapter()
        self.win_storage = win_storage or WindowsStorageOptimizationAdapter()

        self.mac_probe = MacOSSystemProbeAdapter()
        self.mac_active = MacOSActiveAppsAdapter()
        self.mac_cloud = MacOSCloudAndPackagesAdapter()
        self.mac_hw = mac_hw or MacOSHardwareProbeAdapter()
        self.mac_storage = mac_storage or MacOSStorageOptimizationAdapter()

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
        self.last_plan: Optional[ExecutionPlanDTO] = None

    def _get_os_ports(
        self, os_platform: OSPlatform
    ) -> tuple[
        ISystemProbePort,
        IActiveAppsPort,
        ICloudAndPackagesPort,
        IHardwareProbePort,
        IStorageOptimizationPort,
    ]:
        if os_platform == OSPlatform.WINDOWS:
            return self.win_probe, self.win_active, self.win_cloud, self.win_hw, self.win_storage
        return self.mac_probe, self.mac_active, self.mac_cloud, self.mac_hw, self.mac_storage

    def get_initial_context(self, os_platform: Optional[OSPlatform] = None) -> Dict[str, Any]:
        """Retorna dados iniciais do sistema para popular a Janela de Configuração."""
        target_os = os_platform or OSPlatform.detect_current()
        probe, _, _, hw_port, _ = self._get_os_ports(target_os)
        partitions = probe.get_partitions()
        rules = self.cleaner.get_cleanup_rules(target_os)
        tweaks = self.tweak_adapter.list_available_tweaks(target_os)
        snapshots = self.snapshot_repo.list_snapshots()
        hw_health = hw_port.get_hardware_health()

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
            "hardware_health": hw_health.to_dict(),
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
            # SMART_FAST no macOS (focado nas pastas de maior acúmulo sem travar o sistema - RF-15)
            candidates = [
                os.path.expanduser("~/Library/Application Support"),
                os.path.expanduser("~/Library/Containers"),
                os.path.expanduser("~/Library/Group Containers"),
                os.path.expanduser("~/Library/Saved Application State"),
                os.path.expanduser("~/Library/Caches"),
                os.path.expanduser("~/Library/Developer"),
                os.path.expanduser("~/Library/HTTPStorages"),
                os.path.expanduser("~/Library/WebKit"),
                os.path.expanduser("~/Library/Logs"),
                os.path.expanduser("~/.cache"),
                os.path.expanduser("~/.npm"),
                os.path.expanduser("~/.gradle"),
                os.path.expanduser("~/.cargo"),
                os.path.expanduser("~/.orbstack"),
                os.path.expanduser("~/Library/Messages/Attachments"),
                os.path.expanduser("~/Library/Application Support/MobileSync/Backup"),
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
        self.last_plan = plan
        logs: List[str] = []

        def emit(pct: int, step: str, msg: str) -> None:
            timestamped = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
            logs.append(timestamped)
            if progress_cb:
                progress_cb(pct, step, timestamped)

        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        probe, active_port, cloud_port, hw_port, storage_opt_port = self._get_os_ports(plan.os_platform)

        emit(
            5,
            "Mapeando Sistema e Partições",
            f"Iniciando sessão {session_id} ({plan.os_platform.value.upper()} | Modo: {plan.mode.value.upper()})",
        )
        partitions = probe.get_partitions()
        all_drives = [p.mount_point for p in partitions]
        emit(
            10,
            "Mapeando Sistema e Partições",
            f"Partições/Volumes detectados: {len(partitions)} ({', '.join(p.drive_letter for p in partitions)})",
        )

        emit(14, "Diagnóstico de Saúde de Hardware", "Coletando telemetria nativa de SSD/NVMe (S.M.A.R.T.), RAM/Swap, GPU e Bateria...")
        hardware_health = hw_port.get_hardware_health()
        emit(18, "Diagnóstico de Hardware", f"Status geral do hardware: {hardware_health.overall_status} ({len(hardware_health.critical_alerts)} alertas).")

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

        # Calcula o Longevity Health Score (0-100) e recomendações acionáveis (RF-17)
        if hardware_health:
            hardware_health.longevity_report = self.calculate_longevity_score(
                hw_health=hardware_health,
                clean_suggestions=clean_suggestions,
            )

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
            hardware_health=hardware_health,
            storage_optimizations=[],
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
            cleaned_set = {os.path.abspath(p).rstrip("\\/") for p in entry.target_paths}
            remaining_suggestions = []
            for item in self.last_report.clean_suggestions:
                item_norm = os.path.abspath(item.path).rstrip("\\/")
                if item_norm in cleaned_set:
                    item.was_auto_cleaned = mode == ExecutionMode.REAL
                    if mode == ExecutionMode.REAL:
                        self.last_report.potential_extra_bytes = max(
                            0, self.last_report.potential_extra_bytes - item.size
                        )
                        continue  # Remove da lista de pendências da sessão atual!
                remaining_suggestions.append(item)
            if mode == ExecutionMode.REAL:
                self.last_report.clean_suggestions = remaining_suggestions
        return entry

    def reanalyze(
        self,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> SystemExecutionReport:
        """Reanalisa o sistema mantendo o escopo e alvos anteriores, atualizando espaço e pendências."""
        base_plan = self.last_plan or self.build_default_plan()
        reanalyze_plan = ExecutionPlanDTO(
            os_platform=base_plan.os_platform,
            mode=ExecutionMode.DRY_RUN,
            scan_scope=base_plan.scan_scope,
            specific_drive=base_plan.specific_drive,
            selected_cleanup_rule_ids=[],
            selected_tweak_ids=[],
            run_disk_scan=base_plan.run_disk_scan if self.last_plan is not None else True,
            run_cloud_diagnostic=base_plan.run_cloud_diagnostic if self.last_plan is not None else True,
            check_updates=False,
            auto_clean_orphans=False,
        )
        return self.execute_plan(reanalyze_plan, progress_cb=progress_cb)

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

    def diagnose_hardware_health(self, os_platform: Optional[OSPlatform] = None) -> HardwareHealthInfo:
        """Executa diagnóstico de saúde de hardware (Discos, RAM, GPU, Bateria) sob demanda com Longevity Score."""
        target_os = os_platform or (self.last_plan.os_platform if self.last_plan else OSPlatform.detect_current())
        _, _, _, hw_port, _ = self._get_os_ports(target_os)
        hw_health = hw_port.get_hardware_health()
        suggestions = self.last_report.clean_suggestions if self.last_report else None
        hw_health.longevity_report = self.calculate_longevity_score(hw_health, suggestions)
        return hw_health

    def calculate_longevity_score(
        self,
        hw_health: HardwareHealthInfo,
        clean_suggestions: Optional[List[CleanableItem]] = None,
    ) -> LongevityScoreReport:
        """
        Calcula o Longevity Health Score determinístico (0-100) baseado em 4 pilares de engenharia (RF-17).
        Pilar 1: Armazenamento, Margem Livre NAND & Snapshots (35 pts)
        Pilar 2: Memória Unificada & Proteção contra Swap Thrashing (25 pts)
        Pilar 3: Higiene de Caches, Resíduos Órfãos & Persistência de Boot (20 pts)
        Pilar 4: Saúde Elétrica/Térmica & Pacotes (20 pts)
        """
        recommendations: List[LongevityRecommendation] = []

        # -------------------------------------------------------------
        # Pilar 1: Armazenamento, Margem Livre NAND & Snapshots (máx 35 pts)
        # -------------------------------------------------------------
        storage_score = 35
        root_disk = None
        if hw_health.disks:
            root_disk = hw_health.disks[0]
            for d in hw_health.disks:
                if "/" in d.name or "C:" in d.name:
                    root_disk = d
                    break

        if root_disk:
            # 1.1 Margem Livre NAND (Write Amplification)
            if root_disk.total_bytes > 0:
                pct_used = ((root_disk.total_bytes - root_disk.free_bytes) / root_disk.total_bytes) * 100.0
                if pct_used > 90.0:
                    storage_score -= 15
                    recommendations.append(
                        LongevityRecommendation(
                            id="rec_storage_nand_critical",
                            pilar="storage_nand",
                            severity="critical",
                            title="Espaço Livre no SSD Crítico (< 10% livre)",
                            what_to_do="Esvazie a lixeira, apague caches pesados ou desinstale aplicativos não utilizados.",
                            longevity_impact="SSDs precisam de pelo menos 15-20% de blocos livres para Wear Leveling e Over-Provisioning. Menos de 10% causa Write Amplification extremo, degradando as células NAND rapidamente.",
                            action_type="clean_orphans",
                            action_label="🧹 Limpar Resíduos e Caches",
                            action_payload={"category": "selective"},
                        )
                    )
                elif pct_used > 80.0:
                    storage_score -= 8
                    recommendations.append(
                        LongevityRecommendation(
                            id="rec_storage_nand_warning",
                            pilar="storage_nand",
                            severity="warning",
                            title="SSD Próximo do Limite Recomendado (> 80% ocupado)",
                            what_to_do="Faça uma limpeza preventiva de arquivos grandes para manter margem livre de Wear Leveling.",
                            longevity_impact="Manter o SSD abaixo de 80% reduz ciclos de reescrita em blocos adjacentes e preserva a vida útil TBW (Terabytes Written).",
                            action_type="clean_orphans",
                            action_label="🧹 Otimizar Armazenamento",
                            action_payload={"category": "selective"},
                        )
                    )

            # 1.2 Snapshots APFS acumulados
            if root_disk.apfs_snapshots_count > 5:
                storage_score -= 6
                recommendations.append(
                    LongevityRecommendation(
                        id="rec_apfs_snapshots",
                        pilar="storage_nand",
                        severity="warning",
                        title=f"Múltiplos Snapshots APFS Locais Retidos ({root_disk.apfs_snapshots_count} snapshots)",
                        what_to_do="Consolide e expurgue snapshots antigos do Time Machine.",
                        longevity_impact="Snapshots Copy-On-Write retêm gigabytes de dados já apagados pelo usuário no container APFS, impedindo que o SSD realize TRIM nos blocos livres.",
                        action_type="thin_snapshots",
                        action_label="⚡ Consolidar Snapshots APFS",
                        action_payload={"drive": "/"},
                    )
                )
            elif root_disk.apfs_snapshots_count > 2:
                storage_score -= 2

            # 1.3 Integridade S.M.A.R.T.
            if root_disk.smart_status.lower() in ("failing", "fatal", "unhealthy", "warning"):
                storage_score -= 10
                recommendations.append(
                    LongevityRecommendation(
                        id="rec_smart_failure",
                        pilar="storage_nand",
                        severity="critical",
                        title="Alerta de Falha Física Iminente no S.M.A.R.T.",
                        what_to_do="Faça backup imediatamente para um disco externo ou nuvem.",
                        longevity_impact="O controlador do disco detectou setores defeituosos ou falhas térmicas. O risco de perda irrecuperável de dados é imediato.",
                        action_type="none",
                        action_label="⚠️ Backup Imediato Requerido",
                        action_payload={},
                    )
                )

        storage_score = max(0, min(35, storage_score))

        # -------------------------------------------------------------
        # Pilar 2: Memória Unificada & Proteção contra Swap Thrashing (máx 25 pts)
        # -------------------------------------------------------------
        memory_score = 25
        if hw_health.memory:
            mem = hw_health.memory
            if mem.pressure_level == "Critical" or mem.swap_thrashing_detected:
                memory_score -= 15
                recommendations.append(
                    LongevityRecommendation(
                        id="rec_memory_swap_critical",
                        pilar="memory_swap",
                        severity="critical",
                        title="Swap Thrashing Severo no SSD por Falta de RAM",
                        what_to_do="Encerre processos zumbis ou aplicações pesadas em segundo plano.",
                        longevity_impact="No Apple Silicon, a memória SSD é soldada na placa lógica. O swap contínuo a gigabytes por hora gasta a vida útil física (TBW) do Mac, acelerando a perda total da máquina.",
                        action_type="terminate_zombies",
                        action_label="🛑 Encerrar Processos Pesados",
                        action_payload={},
                    )
                )
            elif mem.pressure_level == "Warning" or mem.swap_used_bytes > 512 * 1024 * 1024:
                memory_score -= 7
                recommendations.append(
                    LongevityRecommendation(
                        id="rec_memory_swap_warning",
                        pilar="memory_swap",
                        severity="warning",
                        title="Pressão Moderada de Memória com Paginação em Disco",
                        what_to_do="Feche abas ociosas de navegadores ou aplicações Electron.",
                        longevity_impact="A redução de swap previne lentidão do subsistema I/O e mantém o kernel Darwin responsivo.",
                        action_type="none",
                        action_label="ℹ️ Monitorar Memória",
                        action_payload={},
                    )
                )
            if mem.swapouts_count > 10000:
                memory_score -= 3

        memory_score = max(0, min(25, memory_score))

        # -------------------------------------------------------------
        # Pilar 3: Higiene de Caches, Resíduos Órfãos & Persistência de Boot (máx 20 pts)
        # -------------------------------------------------------------
        hygiene_score = 20
        # 3.1 Agentes de inicialização órfãos (LaunchAgents com binário ausente)
        broken_startups = [s for s in hw_health.startup_items if s.is_orphan]
        if broken_startups:
            hygiene_score -= min(10, len(broken_startups) * 4)
            recommendations.append(
                LongevityRecommendation(
                    id="rec_orphan_launchagents",
                    pilar="hygiene_boot",
                    severity="warning",
                    title=f"{len(broken_startups)} Agente(s) de Inicialização Órfão(s) (LaunchAgents)",
                    what_to_do="Remova os arquivos .plist de persistência que apontam para executáveis excluídos.",
                    longevity_impact="O launchd do macOS tenta invocar repetidamente binários inexistentes a cada boot e intervalo de tempo, consumindo ciclos de CPU, gerando entradas infinitas de log no crash reporter e aumentando o tempo de inicialização.",
                    action_type="remove_broken_startup",
                    action_label="🗑️ Remover Agentes Órfãos",
                    action_payload={"paths": [s.path for s in broken_startups]},
                )
            )

        # 3.2 Volume de resíduos órfãos
        if clean_suggestions:
            orphan_bytes = sum(c.size for c in clean_suggestions if c.is_orphan)
            if orphan_bytes > 10 * 1024 * 1024 * 1024:
                hygiene_score -= 6
                recommendations.append(
                    LongevityRecommendation(
                        id="rec_orphan_folders_heavy",
                        pilar="hygiene_boot",
                        severity="warning",
                        title=f"Mais de {format_bytes(orphan_bytes)} em Pastas Órfãs Detectadas",
                        what_to_do="Mova os resíduos de softwares desinstalados para a Lixeira com segurança.",
                        longevity_impact="Pastas órfãs ocupam nós de índice e blocos no container APFS desnecessariamente.",
                        action_type="clean_orphans",
                        action_label="🗑️ Mover Órfãos p/ Lixeira",
                        action_payload={"category": "selective"},
                    )
                )
            elif orphan_bytes > 2 * 1024 * 1024 * 1024:
                hygiene_score -= 3

        hygiene_score = max(0, min(20, hygiene_score))

        # -------------------------------------------------------------
        # Pilar 4: Saúde Elétrica/Térmica & Pacotes (máx 20 pts)
        # -------------------------------------------------------------
        thermal_battery_score = 20
        if hw_health.battery and hw_health.battery.has_battery:
            b = hw_health.battery
            # Saúde %
            if b.health_percentage is not None:
                if b.health_percentage < 75.0:
                    thermal_battery_score -= 8
                    recommendations.append(
                        LongevityRecommendation(
                            id="rec_battery_degradation",
                            pilar="battery_thermal",
                            severity="warning",
                            title=f"Saúde da Bateria Degradada ({b.health_percentage:.1f}%)",
                            what_to_do="Considere calibrar a bateria ou agendar serviço autorizado Apple.",
                            longevity_impact="Baterias abaixo de 80% perdem estabilidade de voltagem sob pico de carga da CPU/GPU e apresentam risco de expansão física (estufamento).",
                            action_type="none",
                            action_label="⚠️ Manutenção Recomendada",
                            action_payload={},
                        )
                    )
                elif b.health_percentage < 82.0:
                    thermal_battery_score -= 4

            # Ciclos
            if b.cycle_count and b.cycle_count > 850:
                thermal_battery_score -= 4
                recommendations.append(
                    LongevityRecommendation(
                        id="rec_battery_cycles_high",
                        pilar="battery_thermal",
                        severity="warning",
                        title=f"Ciclos de Bateria Elevados ({b.cycle_count} ciclos)",
                        what_to_do="Evite ciclos completos de 0% a 100%. Mantenha a carga entre 20% e 80% sempre que possível.",
                        longevity_impact="Células de Li-Ion sofrem estresse químico máximo nas extremidades (100% sob alta voltagem e < 20% sob depleção profunda).",
                        action_type="none",
                        action_label="ℹ️ Dica de Conservação",
                        action_payload={},
                    )
                )

            # Temperatura
            if b.temperature_celsius and b.temperature_celsius > 38.0:
                thermal_battery_score -= 4
                recommendations.append(
                    LongevityRecommendation(
                        id="rec_battery_temp_high",
                        pilar="battery_thermal",
                        severity="warning",
                        title=f"Temperatura Térmica Elevada na Bateria ({b.temperature_celsius:.1f} °C)",
                        what_to_do="Garanta ventilação e evite carregar o notebook em superfícies macias como sofás ou camas.",
                        longevity_impact="Temperaturas acima de 38 °C aceleram a quebra da camada SEI nos eletrodos de lítio, causando envelhecimento prematuro irreversível.",
                        action_type="none",
                        action_label="🌡️ Verificar Resfriamento",
                        action_payload={},
                    )
                )

        thermal_battery_score = max(0, min(20, thermal_battery_score))

        # Total
        total_score = storage_score + memory_score + hygiene_score + thermal_battery_score

        if total_score >= 90:
            grade_label = "Excelente (90-100)"
        elif total_score >= 75:
            grade_label = "Bom / Saudável (75-89)"
        elif total_score >= 55:
            grade_label = "Atenção Preventiva (55-74)"
        else:
            grade_label = "Crítico / Risco de Degradação (<55)"

        if not recommendations:
            recommendations.append(
                LongevityRecommendation(
                    id="rec_hardware_optimal",
                    pilar="storage_nand",
                    severity="optimal",
                    title="Hardware e Subsistemas em Estado de Conservação Excelente",
                    what_to_do="Continue realizando manutenções preventivas periódicas.",
                    longevity_impact="Seu computador está operando dentro das margens ideais de engenharia, maximizando durabilidade e vida útil do SSD, RAM e bateria.",
                    action_type="none",
                    action_label="✅ Tudo Otimizado",
                    action_payload={},
                )
            )

        return LongevityScoreReport(
            total_score=total_score,
            grade_label=grade_label,
            storage_score=storage_score,
            memory_score=memory_score,
            hygiene_score=hygiene_score,
            thermal_battery_score=thermal_battery_score,
            recommendations=recommendations,
        )

    def execute_file_action(
        self,
        paths: List[str],
        action: str = "trash",
        mode: ExecutionMode = ExecutionMode.REAL,
    ) -> Dict[str, Any]:
        """Executa quarentena (Lixeira) ou exclusão permanente sobre arquivos/pastas (RF-16)."""
        if action == "trash":
            res = self.cleaner.move_paths_to_trash(paths=paths, mode=mode)
        else:
            entry = self.cleaner.clean_specific_paths(paths=paths, mode=mode, category_label="Exclusão Permanente")
            res = {
                "status": entry.status,
                "action": "delete",
                "success": entry.files_removed > 0 or entry.errors_skipped == 0,
                "bytes_freed": entry.bytes_freed,
                "bytes_freed_formatted": entry.bytes_freed_formatted,
                "files_removed": entry.files_removed,
                "affected_paths": entry.target_paths,
                "errors_skipped": entry.errors_skipped,
                "message": entry.details,
            }

        # Atualiza o last_report reativamente
        if self.last_report and res.get("success"):
            b_freed = res.get("bytes_freed", 0)
            f_rem = res.get("files_removed", 0)
            affected_set = {os.path.abspath(p).rstrip("\\/") for p in res.get("affected_paths", [])}

            if mode == ExecutionMode.REAL and b_freed > 0:
                self.last_report.total_bytes_freed += b_freed
                self.last_report.total_files_removed += f_rem
                self.last_report.potential_extra_bytes = max(0, self.last_report.potential_extra_bytes - b_freed)

                # Remove das sugestões de limpeza
                self.last_report.clean_suggestions = [
                    s for s in self.last_report.clean_suggestions
                    if os.path.abspath(s.path).rstrip("\\/") not in affected_set
                ]

                # Remove de top_occupants
                self.last_report.top_occupants = [
                    o for o in self.last_report.top_occupants
                    if os.path.abspath(o.path).rstrip("\\/") not in affected_set
                ]

        res["total_freed_formatted"] = self.last_report.total_bytes_freed_formatted if self.last_report else "0.00 B"
        res["potential_extra_formatted"] = self.last_report.potential_extra_bytes_formatted if self.last_report else "0.00 B"
        return res

    def reveal_path(self, target_path: str) -> Dict[str, Any]:
        """Abre e destaca o caminho no Finder (macOS) ou Windows Explorer (RF-16)."""
        if not target_path or not isinstance(target_path, str):
            return {"status": "error", "message": "Caminho inválido."}
        clean = os.path.normpath(target_path.strip())
        if clean.startswith("-") or "\x00" in clean:
            return {"status": "error", "message": "Caminho malicioso ou com flags bloqueado."}

        target_exists = os.path.exists(clean)
        reveal_target = clean if target_exists else os.path.dirname(clean)
        if not os.path.exists(reveal_target):
            return {"status": "error", "message": "Caminho ou diretório pai não existe no disco."}

        if sys.platform == "darwin":
            cmd = ["open", "-R", "--", reveal_target]
        elif sys.platform == "win32":
            cmd = ["explorer.exe", f"/select,{reveal_target}"]
        else:
            return {"status": "ok", "revealed": False, "path": reveal_target, "message": "Simulação de revelação no gerenciador de arquivos."}

        try:
            subprocess.run(cmd, check=False, timeout=5)
            return {"status": "ok", "revealed": True, "path": reveal_target}
        except Exception as e:
            return {"status": "error", "message": f"Falha ao abrir gerenciador: {e}"}

    def execute_rule_by_id(self, rule_id: str, mode: ExecutionMode = ExecutionMode.REAL) -> Dict[str, Any]:
        """Executa uma regra declarativa individual de limpeza autônoma sob demanda (RF-16)."""
        target_os = self.last_plan.os_platform if self.last_plan else OSPlatform.detect_current()
        rules = self.cleaner.get_cleanup_rules(target_os)
        rule = next((r for r in rules if r.id == rule_id), None)
        if not rule:
            return {"status": "error", "message": f"Regra '{rule_id}' não encontrada no catálogo."}

        entry = self.cleaner.execute_rule(rule, mode=mode)
        if self.last_report:
            existing_idx = next((i for i, e in enumerate(self.last_report.autonomous_cleanups) if e.id == rule_id), None)
            if existing_idx is not None:
                old = self.last_report.autonomous_cleanups[existing_idx]
                if mode == ExecutionMode.REAL:
                    self.last_report.total_bytes_freed += (entry.bytes_freed - old.bytes_freed)
                    self.last_report.total_files_removed += (entry.files_removed - old.files_removed)
                self.last_report.autonomous_cleanups[existing_idx] = entry
            else:
                self.last_report.autonomous_cleanups.append(entry)
                if mode == ExecutionMode.REAL:
                    self.last_report.total_bytes_freed += entry.bytes_freed
                    self.last_report.total_files_removed += entry.files_removed

        return {
            "status": "ok",
            "entry": entry.to_dict(),
            "total_freed_formatted": self.last_report.total_bytes_freed_formatted if self.last_report else entry.bytes_freed_formatted,
        }

    def get_live_health(self, os_platform: Optional[OSPlatform] = None) -> HardwareHealthInfo:
        """Coleta telemetria em tempo real (< 500ms) e recalcula o LongevityScoreReport (RF-17)."""
        target_os = os_platform or (self.last_plan.os_platform if self.last_plan else OSPlatform.detect_current())
        _, _, _, hw_port, _ = self._get_os_ports(target_os)
        hw_health = hw_port.get_hardware_health()
        suggestions = self.last_report.clean_suggestions if self.last_report else None
        hw_health.longevity_report = self.calculate_longevity_score(hw_health, suggestions)
        if self.last_report:
            self.last_report.hardware_health = hw_health
        return hw_health

    def execute_startup_action(self, path: str, action: str = "remove") -> Dict[str, Any]:
        """Remove agente de inicialização órfão com backup prévio (RF-17)."""
        target_os = self.last_plan.os_platform if self.last_plan else OSPlatform.detect_current()
        _, _, _, hw_port, _ = self._get_os_ports(target_os)
        success = hw_port.remove_startup_item(path)
        if success and self.last_report and self.last_report.hardware_health:
            self.last_report.hardware_health.startup_items = [
                s for s in self.last_report.hardware_health.startup_items if s.path != path
            ]
        return {
            "status": "ok" if success else "error",
            "removed_path": path,
            "success": success,
            "message": f"Agente '{os.path.basename(path)}' removido com sucesso." if success else "Falha ao remover agente.",
        }

    def execute_process_action(self, pid: int, action: str = "terminate") -> Dict[str, Any]:
        """Encerra processo de usuário pesado ou zumbi com proteção de segurança (RF-17)."""
        target_os = self.last_plan.os_platform if self.last_plan else OSPlatform.detect_current()
        _, _, _, hw_port, _ = self._get_os_ports(target_os)
        success = hw_port.terminate_process(pid)
        if success and self.last_report and self.last_report.hardware_health:
            self.last_report.hardware_health.top_processes = [
                p for p in self.last_report.hardware_health.top_processes if p.pid != pid
            ]
        return {
            "status": "ok" if success else "error",
            "pid": pid,
            "terminated": success,
            "message": f"Processo PID {pid} encerrado com sucesso." if success else "Não foi possível encerrar o processo (permissão ou processo protegido).",
        }

    def execute_upgrade_packages(self, package_id: str) -> Dict[str, Any]:
        """Atualiza pacotes individuais ou todos via Homebrew / winget (RF-16)."""
        target_os = self.last_plan.os_platform if self.last_plan else OSPlatform.detect_current()
        _, _, cloud_port, _, _ = self._get_os_ports(target_os)
        return cloud_port.upgrade_package(package_id)

    def optimize_storage_volume(
        self,
        drive: str,
        media_type: Optional[str] = None,
        user_confirmed: bool = False,
        mode: ExecutionMode = ExecutionMode.REAL,
    ) -> StorageOptimizationResult:
        """
        Executa otimização inteligente de storage aplicando estritamente os
        Guardrails de 4 Camadas para proteção de NVMe/SSD e Human-in-the-Loop Safety para HDD.
        """
        target_os = self.last_plan.os_platform if self.last_plan else OSPlatform.detect_current()
        _, _, _, _, storage_opt_port = self._get_os_ports(target_os)
        result = storage_opt_port.optimize_volume(
            drive=drive,
            media_type=media_type,
            user_confirmed=user_confirmed,
            mode=mode,
        )
        if self.last_report:
            self.last_report.storage_optimizations.append(result)
        return result
