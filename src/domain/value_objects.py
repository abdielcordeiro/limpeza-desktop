# -*- coding: utf-8 -*-
"""Value Objects puros da camada de Domínio."""
import sys
from enum import Enum


class OSPlatform(str, Enum):
    """Plataformas de sistema operacional suportadas pelo produto."""
    WINDOWS = "windows"
    MACOS = "macos"

    @classmethod
    def detect_current(cls) -> "OSPlatform":
        """Detecta automaticamente o sistema operacional hospedeiro."""
        if sys.platform == "win32":
            return cls.WINDOWS
        return cls.MACOS


class RiskLevel(str, Enum):
    """Níveis de risco de limpeza ou de aplicação de otimizações."""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SafetyClassification(str, Enum):
    """Classificações de segurança para arquivos e pastas encontrados no disco."""
    DO_NOT_DELETE = "🚫 Não Apagar (Sistema Operacional)"
    UNINSTALL_VIA_OS = "⚙️ Desinstalar via Sistema / App"
    DIRECT_CLEAN = "✅ Limpeza Direta (Sem Risco ao SO)"
    REVIEW_PERSONAL = "⚠️ Avaliar Conteúdo Pessoal"


class ExecutionMode(str, Enum):
    """Modo de operação da sessão."""
    REAL = "real"
    DRY_RUN = "dry_run"


class ScanScope(str, Enum):
    """Escopo de varredura de disco."""
    SMART_FAST = "smart_fast"
    FULL_DISKS = "full_disks"
    APPDATA_LIBRARY = "appdata_library"
    SPECIFIC_DRIVE = "specific_drive"


def format_bytes(size_bytes: float) -> str:
    """Formata um tamanho em bytes para representação legível (Bytes, KB, MB, GB, TB)."""
    if size_bytes <= 0:
        return "0.00 B"
    value = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024.0:
            if unit == "B":
                return f"{int(value)} B"
            return f"{value:.2f} {unit}"
        value /= 1024.0
    return f"{value:.2f} PB"
