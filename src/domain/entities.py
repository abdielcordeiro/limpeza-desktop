# -*- coding: utf-8 -*-
"""Entidades puras da camada de Domínio."""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from .value_objects import format_bytes


@dataclass
class PartitionInfo:
    """Informações sobre uma partição ou volume montado no sistema operacional."""
    mount_point: str
    drive_letter: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    percent_used: float
    is_os_drive: bool
    role: str
    health_status: str
    health_class: str
    health_desc: str
    filesystem: str = "APFS/NTFS"

    @property
    def total_formatted(self) -> str:
        return format_bytes(self.total_bytes)

    @property
    def used_formatted(self) -> str:
        return format_bytes(self.used_bytes)

    @property
    def free_formatted(self) -> str:
        return format_bytes(self.free_bytes)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["total_formatted"] = self.total_formatted
        data["used_formatted"] = self.used_formatted
        data["free_formatted"] = self.free_formatted
        return data


@dataclass
class AutonomousCleanupRule:
    """Regra declarativa de limpeza autônoma segura."""
    id: str
    name: str
    category: str
    os_platform: str
    description: str
    target_paths: List[str] = field(default_factory=list)
    default_enabled: bool = True
    risk_level: str = "safe"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AutonomousCleanupEntry:
    """Registro de resultado da execução de uma regra ou pasta de limpeza autônoma."""
    id: str
    name: str
    category: str
    target_paths: List[str]
    bytes_freed: int
    files_removed: int
    status: str  # "cleaned", "simulated", "skipped", "partial"
    details: str = ""
    errors_skipped: int = 0

    @property
    def bytes_freed_formatted(self) -> str:
        return format_bytes(self.bytes_freed)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["bytes_freed_formatted"] = self.bytes_freed_formatted
        return data


@dataclass
class CleanableItem:
    """Item ou pasta órfã/cache detectada durante a varredura para limpeza."""
    name: str
    path: str
    size: int
    size_formatted: str
    drive: str
    risk_level: str
    risk_badge: str
    item_type: str
    reason: str
    how_to_fix: str
    is_orphan: bool = False
    was_auto_cleaned: bool = False

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Mantém compatibilidade com templates que usam 'type'
        data["type"] = self.item_type
        return data


@dataclass
class InstalledAppInfo:
    """Informações sobre um aplicativo instalado e seu consumo de disco."""
    name: str
    path: str
    size: int
    size_formatted: str
    drive: str
    vendor: str
    uninstall_hint: str
    can_migrate: bool = False
    target_drive: str = ""
    bundle_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["current_drive"] = self.drive
        data["type"] = "Aplicativo Instalado"
        data["reason"] = f"Ocupa {self.size_formatted} no volume {self.drive}."
        data["how_to_migrate"] = self.uninstall_hint
        data["feasibility_rate"] = "Alta (Recomendado)" if self.can_migrate else "Desinstalação Nativa"
        return data


@dataclass
class OccupantItem:
    """Representa um dos maiores arquivos ou pastas encontrados no sistema."""
    name: str
    path: str
    size: int
    size_formatted: str
    drive: str
    item_type: str  # "Arquivo" ou "Pasta"
    safety_action: str
    safety_badge: str
    safety_recommendation: str
    sub_occupants: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["type"] = self.item_type
        return data


@dataclass
class TweakDefinition:
    """Definição declarativa de uma otimização de sistema (Windows WinUtil / macOS)."""
    id: str
    name: str
    category: str
    panel: str
    os_platform: str
    preset: str  # "minimal", "standard", "advanced", "fixes"
    risk_level: str
    description: str
    registry_changes: List[Dict[str, Any]] = field(default_factory=list)
    service_changes: List[Dict[str, Any]] = field(default_factory=list)
    scheduled_tasks: List[str] = field(default_factory=list)
    invoke_commands: List[str] = field(default_factory=list)
    undo_commands: List[str] = field(default_factory=list)
    requires_admin: bool = False
    benefit: str = ""
    undo_hint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TweakExecutionRecord:
    """Registro de execução ou reversão de um Tweak de sistema."""
    tweak_id: str
    name: str
    category: str
    action: str  # "apply", "undo", "dry_run"
    success: bool
    message: str
    previous_state: Dict[str, Any] = field(default_factory=dict)
    applied_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StateSnapshot:
    """Snapshot local contendo o estado anterior das configurações antes da otimização."""
    snapshot_id: str
    created_at: str
    os_platform: str
    mode: str
    entries: Dict[str, Any] = field(default_factory=dict)
    tweaks_applied: List[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CloudDiagnosticInfo:
    """Diagnóstico de armazenamento em nuvem (OneDrive / iCloud Drive)."""
    provider_name: str
    is_installed: bool
    path: str
    consumed_bytes: int
    consumed_formatted: str
    file_count: int
    is_consuming_heavy_space: bool
    recommendations: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OutdatedAppInfo:
    """Aplicativo com atualização pendente detectado via winget ou brew."""
    name: str
    app_id: str
    current_version: str
    latest_version: str
    source: str
    drive: str
    risk_level: str
    risk_badge: str
    risk_reason: str
    upgrade_cmd: str

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["id"] = self.app_id
        return data


@dataclass
class SystemExecutionReport:
    """Agregado raiz consolidando todos os resultados da sessão de limpeza e otimização."""
    session_id: str
    executed_at: str
    os_platform: str
    os_version: str
    execution_mode: str
    is_admin: bool
    scan_scope: str
    total_bytes_freed: int = 0
    total_files_removed: int = 0
    potential_extra_bytes: int = 0
    snapshot_id: Optional[str] = None
    partitions: List[PartitionInfo] = field(default_factory=list)
    autonomous_cleanups: List[AutonomousCleanupEntry] = field(default_factory=list)
    clean_suggestions: List[CleanableItem] = field(default_factory=list)
    installed_apps: List[InstalledAppInfo] = field(default_factory=list)
    top_occupants: List[OccupantItem] = field(default_factory=list)
    tweaks_executed: List[TweakExecutionRecord] = field(default_factory=list)
    cloud_diagnostics: List[CloudDiagnosticInfo] = field(default_factory=list)
    outdated_apps: List[OutdatedAppInfo] = field(default_factory=list)
    active_indicators_count: int = 0
    execution_logs: List[str] = field(default_factory=list)

    @property
    def total_bytes_freed_formatted(self) -> str:
        return format_bytes(self.total_bytes_freed)

    @property
    def potential_extra_bytes_formatted(self) -> str:
        return format_bytes(self.potential_extra_bytes)

    def to_dict(self) -> Dict[str, Any]:
        primary_cloud = (
            self.cloud_diagnostics[0].to_dict()
            if self.cloud_diagnostics
            else {
                "provider_name": "OneDrive / iCloud",
                "is_installed": False,
                "path": "Não detectado",
                "consumed_bytes": 0,
                "consumed_formatted": "0.00 B",
                "file_count": 0,
                "is_consuming_heavy_space": False,
                "recommendations": [],
            }
        )
        return {
            "session_id": self.session_id,
            "executed_at": self.executed_at,
            "os_platform": self.os_platform,
            "os_version": self.os_version,
            "execution_mode": self.execution_mode,
            "is_admin": self.is_admin,
            "scan_scope": self.scan_scope,
            "total_bytes_freed": self.total_bytes_freed,
            "total_bytes_freed_formatted": self.total_bytes_freed_formatted,
            "total_files_removed": self.total_files_removed,
            "potential_extra_bytes": self.potential_extra_bytes,
            "potential_extra_bytes_formatted": self.potential_extra_bytes_formatted,
            "snapshot_id": self.snapshot_id,
            "active_indicators_count": self.active_indicators_count,
            "partitions": [p.to_dict() for p in self.partitions],
            "autonomous_cleanups": [c.to_dict() for c in self.autonomous_cleanups],
            "clean_suggestions": [c.to_dict() for c in self.clean_suggestions],
            "installed_apps": [a.to_dict() for a in self.installed_apps],
            "migration_suggestions": [a.to_dict() for a in self.installed_apps],
            "top_occupants": [o.to_dict() for o in self.top_occupants],
            "tweaks_executed": [t.to_dict() for t in self.tweaks_executed],
            "cloud_diagnostics": [c.to_dict() for c in self.cloud_diagnostics],
            "onedrive_info": primary_cloud,
            "outdated_apps": [u.to_dict() for u in self.outdated_apps],
            "execution_logs": list(self.execution_logs),
        }
