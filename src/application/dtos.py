# -*- coding: utf-8 -*-
"""DTOs de entrada e configuração da camada de Aplicação."""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from src.domain.value_objects import OSPlatform, ExecutionMode, ScanScope


@dataclass
class ExecutionPlanDTO:
    """Plano de execução validado enviado pela Janela Inicial ou pela CLI."""
    os_platform: OSPlatform = field(default_factory=OSPlatform.detect_current)
    mode: ExecutionMode = ExecutionMode.DRY_RUN
    scan_scope: ScanScope = ScanScope.SMART_FAST
    specific_drive: Optional[str] = None
    selected_cleanup_rule_ids: List[str] = field(default_factory=list)
    auto_clean_orphans: bool = False
    selected_tweak_ids: List[str] = field(default_factory=list)
    check_updates: bool = False
    run_disk_scan: bool = True
    run_cloud_diagnostic: bool = True

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ExecutionPlanDTO":
        os_str = str(payload.get("os_platform", OSPlatform.detect_current().value)).lower()
        os_plat = OSPlatform.WINDOWS if os_str == "windows" else OSPlatform.MACOS

        mode_str = str(payload.get("mode", "dry_run")).lower()
        mode = ExecutionMode.REAL if mode_str == "real" else ExecutionMode.DRY_RUN

        scope_str = str(payload.get("scan_scope", "smart_fast")).lower()
        scope_map = {
            "smart_fast": ScanScope.SMART_FAST,
            "full_disks": ScanScope.FULL_DISKS,
            "appdata_library": ScanScope.APPDATA_LIBRARY,
            "specific_drive": ScanScope.SPECIFIC_DRIVE,
        }
        scan_scope = scope_map.get(scope_str, ScanScope.SMART_FAST)

        return cls(
            os_platform=os_plat,
            mode=mode,
            scan_scope=scan_scope,
            specific_drive=payload.get("specific_drive"),
            selected_cleanup_rule_ids=list(payload.get("selected_cleanup_rule_ids", [])),
            auto_clean_orphans=bool(payload.get("auto_clean_orphans", False)),
            selected_tweak_ids=list(payload.get("selected_tweak_ids", [])),
            check_updates=bool(payload.get("check_updates", False)),
            run_disk_scan=bool(payload.get("run_disk_scan", True)),
            run_cloud_diagnostic=bool(payload.get("run_cloud_diagnostic", True)),
        )
