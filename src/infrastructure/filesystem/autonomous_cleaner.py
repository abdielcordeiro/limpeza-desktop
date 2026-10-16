# -*- coding: utf-8 -*-
"""Motor de Limpeza Autônoma Multiplataforma (Windows & macOS)."""
import os
import json
import shutil
from typing import List, Tuple, Optional
from src.domain.entities import AutonomousCleanupRule, AutonomousCleanupEntry
from src.domain.ports import IFileSystemCleanerPort
from src.domain.value_objects import ExecutionMode, OSPlatform, format_bytes
from src.infrastructure.resources import get_catalog_path


def expand_os_path(raw_path: str) -> str:
    """Expande variáveis de ambiente Windows (%VAR%) e diretórios de usuário (~)."""
    expanded = os.path.expanduser(os.path.expandvars(raw_path))
    return os.path.normpath(expanded)


# Caminhos críticos de sistema que jamais podem ser apagados diretamente na raiz
CRITICAL_PROTECTED_POSIX_ROOTS = {
    "/",
    "/system",
    "/library",
    "/applications",
    "/users",
    "/bin",
    "/sbin",
    "/usr",
    "/var",
    "/private",
    "/private/var",
    "/private/etc",
    "/etc",
    "/dev",
    "/proc",
    "/volumes",
    "/opt",
    "/cores",
}

CRITICAL_PROTECTED_POSIX_PREFIXES = (
    "/system/",
    "/bin/",
    "/sbin/",
    "/usr/",
    "/etc/",
    "/private/etc/",
    "/dev/",
    "/proc/",
    "/library/apple/",
    "/library/extensions/",
)

CRITICAL_PROTECTED_WINDOWS_ROOTS = {
    "c:",
    "c:\\",
    "c:\\windows",
    "c:\\windows\\system32",
    "c:\\windows\\syswow64",
    "c:\\windows\\winsxs",
    "c:\\windows\\boot",
    "c:\\program files",
    "c:\\program files (x86)",
    "c:\\users",
    "c:\\programdata",
}

ALLOWED_WINDOWS_DIR_SUBTREES = (
    "c:\\windows\\temp",
    "c:\\windows\\prefetch",
    "c:\\windows\\softwaredistribution\\download",
)


def is_safe_path_to_clean(target_path: str) -> bool:
    """
    Garante que o caminho alvo não contém Path Traversal ('..') nem aponta para
    raízes ou subárvores críticas do sistema operacional (Windows & macOS).
    """
    if not target_path or not isinstance(target_path, str):
        return False

    raw = target_path.strip()
    if not raw or "\x00" in raw:
        return False

    # Bloqueia qualquer tentativa de Path Traversal explícito nos segmentos do caminho
    raw_parts = [p for p in raw.replace("\\", "/").split("/") if p]
    if ".." in raw_parts:
        return False

    # 1. Validação independente de plataforma para caminhos Windows (ex: C:\, C:\Windows\System32)
    raw_win = raw.replace("/", "\\").rstrip("\\").lower()
    if len(raw_win) == 2 and raw_win[0].isalpha() and raw_win[1] == ":":
        return False
    if raw_win in CRITICAL_PROTECTED_WINDOWS_ROOTS:
        return False
    if raw_win.startswith("c:\\windows\\"):
        if not any(
            raw_win == allowed or raw_win.startswith(allowed + "\\")
            for allowed in ALLOWED_WINDOWS_DIR_SUBTREES
        ):
            return False

    # 2. Validação do caminho expandido e resolvido no SO hospedeiro
    expanded = os.path.expanduser(os.path.expandvars(raw))
    abs_path = os.path.abspath(expanded)
    real_path = os.path.realpath(abs_path)

    for candidate in (abs_path, real_path):
        posix_norm = candidate.replace("\\", "/").lower()
        if posix_norm != "/":
            posix_norm = posix_norm.rstrip("/")

        if not posix_norm or posix_norm in CRITICAL_PROTECTED_POSIX_ROOTS:
            return False

        if any(posix_norm.startswith(pref) for pref in CRITICAL_PROTECTED_POSIX_PREFIXES):
            return False

        win_norm = candidate.replace("/", "\\").rstrip("\\").lower()
        if len(win_norm) == 2 and win_norm[0].isalpha() and win_norm[1] == ":":
            return False
        if win_norm in CRITICAL_PROTECTED_WINDOWS_ROOTS:
            return False
        if win_norm.startswith("c:\\windows\\"):
            if not any(
                win_norm == allowed or win_norm.startswith(allowed + "\\")
                for allowed in ALLOWED_WINDOWS_DIR_SUBTREES
            ):
                return False

    # 3. Protege o diretório home do usuário e pastas-raiz estruturais do perfil
    user_home = os.path.abspath(os.path.expanduser("~")).replace("\\", "/").rstrip("/").lower()
    protected_user_roots = {
        user_home,
        f"{user_home}/library",
        f"{user_home}/applications",
        f"{user_home}/desktop",
        f"{user_home}/documents",
        f"{user_home}/downloads",
        f"{user_home}/appdata",
        f"{user_home}/appdata/local",
        f"{user_home}/appdata/roaming",
        f"{user_home}/appdata/locallow",
    }
    for candidate in (abs_path, real_path):
        cand_norm = candidate.replace("\\", "/").rstrip("/").lower()
        if cand_norm in protected_user_roots:
            return False

    return True



class AutonomousCleanerAdapter(IFileSystemCleanerPort):
    """Implementa a limpeza autônoma e seletiva de caches, temporários e pastas órfãs."""

    def __init__(self, catalog_path: Optional[str] = None) -> None:
        if catalog_path is None:
            catalog_path = get_catalog_path("safe_cleanup_rules.json")
        self.catalog_path = os.path.abspath(catalog_path)

    def get_cleanup_rules(self, os_platform: OSPlatform) -> List[AutonomousCleanupRule]:
        if not os.path.exists(self.catalog_path):
            return []
        try:
            with open(self.catalog_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            rules: List[AutonomousCleanupRule] = []
            for item in data.get("rules", []):
                if item.get("os_platform") == os_platform.value:
                    rules.append(
                        AutonomousCleanupRule(
                            id=item["id"],
                            name=item["name"],
                            category=item["category"],
                            os_platform=item["os_platform"],
                            description=item.get("description", ""),
                            target_paths=item.get("target_paths", []),
                            default_enabled=item.get("default_enabled", True),
                            risk_level=item.get("risk_level", "safe"),
                        )
                    )
            return rules
        except (OSError, json.JSONDecodeError):
            return []

    def _clean_directory_contents(
        self, dir_path: str, mode: ExecutionMode, remove_root: bool = False
    ) -> Tuple[int, int, int]:
        """
        Varre uma pasta (ou arquivo) e contabiliza/remove seu conteúdo.
        Retorna (bytes_freed, files_removed, errors_skipped).
        """
        if not os.path.exists(dir_path) or not is_safe_path_to_clean(dir_path):
            return 0, 0, 0

        bytes_freed = 0
        files_removed = 0
        errors_skipped = 0

        # Caso seja um arquivo único
        if os.path.isfile(dir_path) and not os.path.islink(dir_path):
            try:
                fsize = os.path.getsize(dir_path)
                if mode == ExecutionMode.REAL:
                    os.remove(dir_path)
                return fsize, 1, 0
            except (PermissionError, OSError):
                return 0, 0, 1

        # Percorre de baixo para cima (bottom-up) para medir e deletar com segurança
        for root, dirs, files in os.walk(dir_path, topdown=False):
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    if os.path.islink(fpath):
                        if mode == ExecutionMode.REAL:
                            os.unlink(fpath)
                        files_removed += 1
                        continue
                    fsize = os.path.getsize(fpath)
                    if mode == ExecutionMode.REAL:
                        os.remove(fpath)
                    bytes_freed += fsize
                    files_removed += 1
                except (PermissionError, FileNotFoundError, OSError):
                    errors_skipped += 1

            for dname in dirs:
                dpath = os.path.join(root, dname)
                if mode == ExecutionMode.REAL:
                    try:
                        if os.path.islink(dpath):
                            os.unlink(dpath)
                        else:
                            os.rmdir(dpath)
                    except (PermissionError, OSError):
                        pass

        if remove_root and mode == ExecutionMode.REAL:
            try:
                if os.path.exists(dir_path):
                    shutil.rmtree(dir_path, ignore_errors=True)
            except OSError:
                pass

        return bytes_freed, files_removed, errors_skipped

    def execute_rule(
        self,
        rule: AutonomousCleanupRule,
        mode: ExecutionMode,
    ) -> AutonomousCleanupEntry:
        total_bytes = 0
        total_files = 0
        total_errors = 0
        resolved_paths: List[str] = []

        for raw_target in rule.target_paths:
            if not isinstance(raw_target, str):
                continue
            expanded = expand_os_path(raw_target)
            resolved_paths.append(expanded)
            if is_safe_path_to_clean(raw_target) and is_safe_path_to_clean(expanded) and os.path.exists(expanded):
                b_freed, f_rem, errs = self._clean_directory_contents(
                    expanded, mode=mode, remove_root=False
                )
                total_bytes += b_freed
                total_files += f_rem
                total_errors += errs

        status = "cleaned" if mode == ExecutionMode.REAL else "simulated"
        if total_files == 0 and total_bytes == 0:
            details = "Nenhum arquivo residual acumulado nos diretórios desta regra."
        elif mode == ExecutionMode.REAL:
            details = (
                f"Limpeza autônoma concluída: {total_files} arquivos removidos "
                f"({format_bytes(total_bytes)} liberados)."
            )
            if total_errors > 0:
                details += f" [{total_errors} arquivos em uso pelo SO foram ignorados com segurança]."
        else:
            details = (
                f"Simulação (Dry-Run): {total_files} arquivos identificados "
                f"({format_bytes(total_bytes)} recuperáveis)."
            )

        return AutonomousCleanupEntry(
            id=rule.id,
            name=rule.name,
            category=rule.category,
            target_paths=resolved_paths,
            bytes_freed=total_bytes,
            files_removed=total_files,
            status=status,
            details=details,
            errors_skipped=total_errors,
        )

    def clean_specific_paths(
        self,
        paths: List[str],
        mode: ExecutionMode,
        category_label: str = "Limpeza de Pastas Órfãs & Caches Selecionados",
    ) -> AutonomousCleanupEntry:
        total_bytes = 0
        total_files = 0
        total_errors = 0
        cleaned_paths: List[str] = []

        for p in paths:
            if not isinstance(p, str) or not is_safe_path_to_clean(p):
                total_errors += 1
                continue
            expanded = expand_os_path(p)
            if os.path.exists(expanded) and is_safe_path_to_clean(expanded):
                cleaned_paths.append(expanded)
                b_freed, f_rem, errs = self._clean_directory_contents(
                    expanded, mode=mode, remove_root=True
                )
                total_bytes += b_freed
                total_files += f_rem
                total_errors += errs

        status = "cleaned" if mode == ExecutionMode.REAL else "simulated"
        details = (
            f"{'Removidos' if mode == ExecutionMode.REAL else 'Simulados'} "
            f"{len(cleaned_paths)} diretórios/itens ({total_files} arquivos, {format_bytes(total_bytes)})."
        )
        return AutonomousCleanupEntry(
            id="selective_cleanup",
            name=category_label,
            category="selective",
            target_paths=cleaned_paths,
            bytes_freed=total_bytes,
            files_removed=total_files,
            status=status,
            details=details,
            errors_skipped=total_errors,
        )
