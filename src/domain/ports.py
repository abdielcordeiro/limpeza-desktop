# -*- coding: utf-8 -*-
"""Interfaces de Porta (Ports - Arquitetura Hexagonal) da camada de Domínio."""
from abc import ABC, abstractmethod
from typing import List, Set, Dict, Any, Optional, Tuple
from .entities import (
    PartitionInfo,
    AutonomousCleanupRule,
    AutonomousCleanupEntry,
    CleanableItem,
    InstalledAppInfo,
    OccupantItem,
    TweakDefinition,
    TweakExecutionRecord,
    StateSnapshot,
    CloudDiagnosticInfo,
    OutdatedAppInfo,
)
from .value_objects import ExecutionMode, OSPlatform


class ISystemProbePort(ABC):
    """Porta para inspeção de sistema operacional, privilégios, RAM e partições."""

    @abstractmethod
    def get_os_platform(self) -> OSPlatform:
        pass

    @abstractmethod
    def get_os_version_string(self) -> str:
        pass

    @abstractmethod
    def is_admin_or_root(self) -> bool:
        pass

    @abstractmethod
    def get_total_ram_kb(self) -> int:
        pass

    @abstractmethod
    def get_partitions(self) -> List[PartitionInfo]:
        pass


class IActiveAppsPort(ABC):
    """Porta para o Algoritmo de 5 Camadas de detecção de softwares ativos."""

    @abstractmethod
    def get_active_indicators(self, drives: List[str]) -> Set[str]:
        pass

    @abstractmethod
    def get_layer_breakdown(self, drives: List[str]) -> Dict[str, int]:
        pass


class IFileSystemCleanerPort(ABC):
    """Porta para o motor de limpeza autônoma de caches, temporários e pastas órfãs."""

    @abstractmethod
    def get_cleanup_rules(self, os_platform: OSPlatform) -> List[AutonomousCleanupRule]:
        pass

    @abstractmethod
    def execute_rule(
        self,
        rule: AutonomousCleanupRule,
        mode: ExecutionMode,
    ) -> AutonomousCleanupEntry:
        pass

    @abstractmethod
    def clean_specific_paths(
        self,
        paths: List[str],
        mode: ExecutionMode,
        category_label: str = "Limpeza Seletiva",
    ) -> AutonomousCleanupEntry:
        pass


class IDiskScannerPort(ABC):
    """Porta para o scanner profundo de pastas órfãs, apps instalados e top 100 arquivos."""

    @abstractmethod
    def scan_and_evaluate(
        self,
        target_paths: List[str],
        active_indicators: Set[str],
        partitions: List[PartitionInfo],
        os_platform: OSPlatform,
        top_n: int = 100,
    ) -> Tuple[List[OccupantItem], List[CleanableItem], List[InstalledAppInfo]]:
        pass


class ISystemTweakPort(ABC):
    """Porta para listagem, aplicação idempotente e reversão (Undo) de Tweaks do SO."""

    @abstractmethod
    def list_available_tweaks(self, os_platform: Optional[OSPlatform] = None) -> List[TweakDefinition]:
        pass

    @abstractmethod
    def capture_current_state(self, tweak: TweakDefinition) -> Dict[str, Any]:
        pass

    @abstractmethod
    def apply_tweak(
        self,
        tweak: TweakDefinition,
        mode: ExecutionMode,
    ) -> TweakExecutionRecord:
        pass

    @abstractmethod
    def revert_tweak(
        self,
        tweak: TweakDefinition,
        previous_state: Optional[Dict[str, Any]],
        mode: ExecutionMode,
    ) -> TweakExecutionRecord:
        pass


class ICloudAndPackagesPort(ABC):
    """Porta para diagnóstico de armazenamento em nuvem (OneDrive/iCloud) e pacotes desatualizados."""

    @abstractmethod
    def analyze_cloud_storage(self) -> List[CloudDiagnosticInfo]:
        pass

    @abstractmethod
    def check_outdated_packages(self) -> List[OutdatedAppInfo]:
        pass


class ISnapshotRepositoryPort(ABC):
    """Porta para persistência e consulta de snapshots locais para Undo."""

    @abstractmethod
    def save_snapshot(self, snapshot: StateSnapshot) -> str:
        pass

    @abstractmethod
    def get_snapshot(self, snapshot_id: str) -> Optional[StateSnapshot]:
        pass

    @abstractmethod
    def get_latest_snapshot(self) -> Optional[StateSnapshot]:
        pass

    @abstractmethod
    def list_snapshots(self) -> List[StateSnapshot]:
        pass
