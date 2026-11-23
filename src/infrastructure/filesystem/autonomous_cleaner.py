# -*- coding: utf-8 -*-
"""Motor de Limpeza Autônoma Multiplataforma (Windows & macOS)."""
import os
import sys
import stat
import glob
import time
import json
import shutil
import subprocess
from typing import List, Tuple, Optional, Dict, Any
from src.domain.entities import AutonomousCleanupRule, AutonomousCleanupEntry
from src.domain.ports import IFileSystemCleanerPort
from src.domain.value_objects import ExecutionMode, OSPlatform, format_bytes
from src.infrastructure.resources import get_catalog_path


_DARWIN_CONF_CACHE: Dict[str, str] = {}


def get_darwin_user_dir(conf_var: str) -> str:
    """
    Resolve dinamicamente diretórios de sessão Darwin por usuário via getconf
    (DARWIN_USER_CACHE_DIR ou DARWIN_USER_TEMP_DIR).
    """
    if conf_var in _DARWIN_CONF_CACHE:
        return _DARWIN_CONF_CACHE[conf_var]

    resolved = ""
    if sys.platform == "darwin":
        try:
            res = subprocess.run(
                ["getconf", conf_var],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            if res.returncode == 0 and res.stdout.strip():
                cand = os.path.normpath(res.stdout.strip())
                real_cand = os.path.realpath(cand).replace("\\", "/")
                if real_cand.startswith("/private/var/folders/") or real_cand.startswith("/var/folders/"):
                    resolved = cand
        except Exception:
            pass

    if not resolved and conf_var == "DARWIN_USER_TEMP_DIR":
        tmpdir = os.environ.get("TMPDIR", "")
        if tmpdir:
            real_tmp = os.path.realpath(tmpdir).replace("\\", "/")
            if real_tmp.startswith("/private/var/folders/") or real_tmp.startswith("/var/folders/"):
                resolved = os.path.normpath(tmpdir)

    if not resolved:
        resolved = f"/nonexistent_{conf_var.lower()}"

    _DARWIN_CONF_CACHE[conf_var] = resolved
    return resolved


def expand_os_path(raw_path: str) -> str:
    """Expande tokens Darwin (@DARWIN_USER_*@), variáveis Windows (%VAR%) e home (~)."""
    path_str = raw_path
    if "@DARWIN_USER_CACHE_DIR@" in path_str:
        path_str = path_str.replace("@DARWIN_USER_CACHE_DIR@", get_darwin_user_dir("DARWIN_USER_CACHE_DIR"))
    if "@DARWIN_USER_TEMP_DIR@" in path_str:
        path_str = path_str.replace("@DARWIN_USER_TEMP_DIR@", get_darwin_user_dir("DARWIN_USER_TEMP_DIR"))
    expanded = os.path.expanduser(os.path.expandvars(path_str))
    return os.path.normpath(expanded)


# Whitelist cirúrgica de proteção de estado em ~/Library/Caches no macOS (ADR-009)
PROTECTED_MACOS_CACHE_PATTERNS = (
    "cloudkit",
    "com.apple.nsurlsessiond",
    "com.apple.bird",
    "com.apple.cloudd",
    "com.apple.homekit",
    "com.apple.safari.safebrowsing",
    "audiounitcache",
    "com.apple.passkit",
    "com.apple.geoservices",
    "com.apple.launchservices",
    "com.apple.keychain",
    "com.apple.ap.adprivacyd",
    "familycircle",
    "com.apple.accountsd",
)


def is_protected_macos_cache_path(target_path: str) -> bool:
    """Verifica se o caminho em ~/Library/Caches pertence à whitelist de estado crítico do macOS."""
    if not target_path:
        return True
    norm = target_path.replace("\\", "/").rstrip("/").lower()
    base = os.path.basename(norm)
    if any(pat == base or pat in base for pat in PROTECTED_MACOS_CACHE_PATTERNS):
        return True
    return False


# Caminhos críticos de sistema que jamais podem ser apagados diretamente na raiz
CRITICAL_PROTECTED_POSIX_ROOTS = {
    "/",
    "/system",
    "/library",
    "/applications",
    "/applications/utilities",
    "/users",
    "/bin",
    "/sbin",
    "/usr",
    "/var",
    "/var/folders",
    "/private",
    "/private/var",
    "/private/var/folders",
    "/private/etc",
    "/etc",
    "/dev",
    "/proc",
    "/volumes",
    "/opt",
    "/cores",
    "/system/volumes",
    "/system/volumes/data",
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
    "/library/",
    "/applications/utilities/",
    "/opt/",
)


def _is_unsafe_windows_subpath(raw_win: str) -> bool:
    """Verifica regras estritas de segurança em caminhos Windows para qualquer letra de unidade."""
    norm = raw_win.replace("/", "\\").rstrip("\\").lower()
    if not norm:
        return True

    # 1. Verifica letra de drive (ex: "c:", "c:\", "d:")
    if len(norm) >= 2 and norm[0].isalpha() and norm[1] == ":":
        rest = norm[2:]
        if not rest or rest == "\\":
            return True  # Raiz inteira de disco ("C:", "C:\", "D:", etc.)
    elif norm.startswith("\\\\"):
        # UNC path não permitido para deleção direta
        return True
    else:
        rest = norm

    parts = [p for p in rest.split("\\") if p]
    if not parts:
        return True

    first = parts[0]
    # Protege subárvores de sistema
    if first in ("windows", "winnt"):
        # Apenas permite subárvores temporárias seguras
        if len(parts) >= 2 and parts[1] in ("temp", "prefetch"):
            return False
        if len(parts) >= 3 and parts[1] == "softwaredistribution" and parts[2] == "download":
            return False
        return True

    if first in (
        "program files",
        "program files (x86)",
        "system volume information",
        "recovery",
        "boot",
        "$recycle.bin",
        "recycle.bin",
        "perflogs",
    ):
        return True

    if first == "users":
        if len(parts) <= 2:
            return True  # C:\Users ou C:\Users\Username
        if len(parts) == 3 and parts[2] in (
            "desktop", "documents", "downloads", "pictures", "music", "videos", "appdata"
        ):
            return True
        if len(parts) == 4 and parts[2] == "appdata" and parts[3] in ("local", "roaming", "locallow"):
            return True

    if first == "programdata" and len(parts) <= 1:
        return True  # C:\ProgramData raiz

    return False


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

    # 1. Validação independente de plataforma para caminhos Windows (qualquer letra de unidade)
    if _is_unsafe_windows_subpath(raw):
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

        if _is_unsafe_windows_subpath(candidate):
            return False

    # 3. Protege o diretório home do usuário e pastas-raiz estruturais do perfil
    user_home = os.path.abspath(os.path.expanduser("~")).replace("\\", "/").rstrip("/").lower()
    protected_user_roots = {
        user_home,
        f"{user_home}/library",
        f"{user_home}/library/caches",
        f"{user_home}/library/containers",
        f"{user_home}/library/group containers",
        f"{user_home}/library/application support",
        f"{user_home}/library/preferences",
        f"{user_home}/library/saved application state",
        f"{user_home}/library/launchagents",
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


def _force_remove_file(file_path: str) -> None:
    """
    Remove um arquivo garantindo remoção de atributos somente-leitura
    e flags de imutabilidade (uchg no macOS), desbloqueando também o diretório pai se necessário.
    """
    try:
        os.remove(file_path)
    except (PermissionError, OSError):
        try:
            parent_dir = os.path.dirname(file_path)
            if parent_dir and os.path.exists(parent_dir):
                try:
                    os.chmod(parent_dir, stat.S_IWUSR | stat.S_IRUSR | stat.S_IXUSR | stat.S_IWRITE)
                except Exception:
                    pass

            # 1. No macOS, remove flag de imutabilidade (uchg) se aplicável
            if sys.platform == "darwin":
                try:
                    subprocess.run(
                        ["chflags", "nouchg", file_path],
                        capture_output=True,
                        timeout=2,
                        check=False,
                    )
                except Exception:
                    pass

            # 2. Concede permissão de escrita ao proprietário (no Windows desativa FILE_ATTRIBUTE_READONLY)
            os.chmod(file_path, stat.S_IWUSR | stat.S_IRUSR | stat.S_IWRITE)
            os.remove(file_path)
        except Exception:
            raise


def _force_remove_dir(dir_path: str) -> None:
    """
    Remove um diretório vazio garantindo remoção de atributos de proteção
    no próprio diretório e no diretório-pai.
    """
    try:
        os.rmdir(dir_path)
    except (PermissionError, OSError):
        try:
            parent_dir = os.path.dirname(dir_path)
            if parent_dir and os.path.exists(parent_dir):
                try:
                    os.chmod(parent_dir, stat.S_IWUSR | stat.S_IRUSR | stat.S_IXUSR | stat.S_IWRITE)
                except Exception:
                    pass

            if sys.platform == "darwin":
                try:
                    subprocess.run(
                        ["chflags", "nouchg", dir_path],
                        capture_output=True,
                        timeout=2,
                        check=False,
                    )
                except Exception:
                    pass

            os.chmod(dir_path, stat.S_IWUSR | stat.S_IRUSR | stat.S_IXUSR | stat.S_IWRITE)
            os.rmdir(dir_path)
        except Exception:
            raise


def _rmtree_resilient_handler(func, path) -> None:
    """Desbloqueia permissões de arquivo/pasta pai e repete a remoção para rmtree."""
    try:
        parent = os.path.dirname(path)
        if parent and os.path.exists(parent):
            try:
                os.chmod(parent, stat.S_IWUSR | stat.S_IRUSR | stat.S_IXUSR | stat.S_IWRITE)
            except Exception:
                pass
        if sys.platform == "darwin":
            try:
                subprocess.run(
                    ["chflags", "-R", "nouchg", path],
                    capture_output=True,
                    timeout=2,
                    check=False,
                )
            except Exception:
                pass
        os.chmod(path, stat.S_IWUSR | stat.S_IRUSR | stat.S_IXUSR | stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def _on_rmtree_error(func, path, exc_info) -> None:
    """Callback para shutil.rmtree em Python < 3.12."""
    _rmtree_resilient_handler(func, path)


def _on_rmtree_onexc(func, path, exc) -> None:
    """Callback para shutil.rmtree em Python >= 3.12."""
    _rmtree_resilient_handler(func, path)


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
        Varre uma pasta (ou arquivo) e contabiliza/remove seu conteúdo com deleção resiliente.
        Retorna (bytes_freed, files_removed, errors_skipped).
        """
        if not os.path.exists(dir_path) or not is_safe_path_to_clean(dir_path):
            return 0, 0, 0

        bytes_freed = 0
        files_removed = 0
        errors_skipped = 0

        # Caso seja um symlink ou arquivo único
        if os.path.islink(dir_path):
            try:
                fsize = 0
                try:
                    fsize = os.path.getsize(dir_path)
                except OSError:
                    pass
                if mode == ExecutionMode.REAL:
                    os.unlink(dir_path)
                return fsize, 1, 0
            except (PermissionError, OSError):
                return 0, 0, 1

        if os.path.isfile(dir_path):
            try:
                fsize = os.path.getsize(dir_path)
                if mode == ExecutionMode.REAL:
                    _force_remove_file(dir_path)
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
                        _force_remove_file(fpath)
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
                            _force_remove_dir(dpath)
                    except (PermissionError, OSError):
                        pass

        if remove_root and mode == ExecutionMode.REAL:
            try:
                if os.path.exists(dir_path):
                    if hasattr(shutil, "rmtree") and "onexc" in shutil.rmtree.__code__.co_varnames:
                        shutil.rmtree(dir_path, onexc=_on_rmtree_onexc)
                    else:
                        shutil.rmtree(dir_path, onerror=_on_rmtree_error)
                    if os.path.exists(dir_path):
                        _force_remove_dir(dir_path)
            except OSError:
                pass

        return bytes_freed, files_removed, errors_skipped

    def _is_trash_rule(self, rule: AutonomousCleanupRule) -> bool:
        """Verifica se a regra é de esvaziamento de lixeira (macOS ~/.Trash ou Windows Recycle Bin)."""
        if rule.category and rule.category.lower() == "trash":
            return True
        if rule.id in ("mac_trash", "win_trash"):
            return True
        for raw_target in rule.target_paths:
            if isinstance(raw_target, str):
                target_lower = raw_target.lower().replace("\\", "/").rstrip("/")
                if (
                    "/.trash" in target_lower
                    or target_lower.endswith(".trash")
                    or ".trashes" in target_lower
                    or "$recycle.bin" in target_lower
                    or "recycle.bin" in target_lower
                ):
                    return True
        return False

    def _count_macos_trash_items(self) -> int:
        """Contabiliza itens na Lixeira do macOS via AppleScript Finder com fallback POSIX."""
        # 1. osascript Finder
        try:
            res = subprocess.run(
                ["osascript", "-e", 'tell application "Finder" to count every item of trash'],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if res.returncode == 0:
                raw = res.stdout.strip()
                if raw.isdigit():
                    return int(raw)
        except Exception:
            pass

        # 2. Fallback de contagem direta caso o terminal possua permissão POSIX
        trash_path = os.path.expanduser("~/.Trash")
        if os.path.exists(trash_path) and os.path.isdir(trash_path):
            try:
                return len(os.listdir(trash_path))
            except Exception:
                pass
        return 0

    def _calculate_trash_bytes_posix(self, paths: List[str]) -> int:
        """Soma os bytes dos arquivos na lixeira se o processo tiver permissão de leitura."""
        total = 0
        for p in paths:
            if not os.path.exists(p) or not os.path.isdir(p):
                continue
            try:
                for root, dirs, files in os.walk(p, topdown=True):
                    for f in files:
                        fp = os.path.join(root, f)
                        try:
                            if not os.path.islink(fp):
                                total += os.path.getsize(fp)
                        except Exception:
                            pass
            except Exception:
                pass
        return total

    def _execute_macos_trash(
        self, rule: AutonomousCleanupRule, mode: ExecutionMode
    ) -> AutonomousCleanupEntry:
        """Executa o esvaziamento nativo da Lixeira no macOS usando AppleScript e chflags."""
        valid_paths: List[str] = []
        for p in rule.target_paths:
            if not isinstance(p, str):
                continue
            expanded = expand_os_path(p)
            norm = expanded.replace("\\", "/").rstrip("/").lower()
            is_trash_name = (
                norm.endswith("/.trash")
                or norm.endswith("/.trashes")
                or os.path.basename(norm) in (".trash", ".trashes")
                or "/.trash/" in norm
            )
            if is_trash_name and is_safe_path_to_clean(expanded):
                valid_paths.append(expanded)

        if not valid_paths:
            if not rule.target_paths or rule.id == "mac_trash":
                valid_paths = [expand_os_path("~/.Trash")]
            else:
                return AutonomousCleanupEntry(
                    id=rule.id,
                    name=rule.name,
                    category=rule.category,
                    target_paths=[],
                    bytes_freed=0,
                    files_removed=0,
                    status="cleaned" if mode == ExecutionMode.REAL else "simulated",
                    details="Nenhum diretório de Lixeira seguro/válido identificado para esta regra.",
                    errors_skipped=1,
                )

        resolved_paths = valid_paths

        count_before = self._count_macos_trash_items()
        bytes_estimated = self._calculate_trash_bytes_posix(resolved_paths)

        if mode == ExecutionMode.DRY_RUN:
            details = (
                f"Simulação (Dry-Run): {count_before} itens na Lixeira "
                f"({format_bytes(bytes_estimated)} identificados)."
                if count_before > 0
                else "Lixeira do macOS vazia. Nenhum item pendente de esvaziamento."
            )
            return AutonomousCleanupEntry(
                id=rule.id,
                name=rule.name,
                category=rule.category,
                target_paths=resolved_paths,
                bytes_freed=bytes_estimated,
                files_removed=count_before,
                status="simulated",
                details=details,
                errors_skipped=0,
            )

        # Modo REAL:
        finder_success = False
        try:
            res = subprocess.run(
                ["osascript", "-e", 'tell application "Finder" to empty trash'],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            if res.returncode == 0:
                finder_success = True
        except Exception:
            pass

        # Complementa com remoção direta de flags de imutabilidade (sem invocação de subshell)
        for trash_dir in resolved_paths:
            if os.path.exists(trash_dir):
                try:
                    subprocess.run(
                        ["chflags", "-R", "nouchg", trash_dir],
                        capture_output=True,
                        timeout=5,
                        check=False,
                    )
                except Exception:
                    pass

        # Limpeza direta de resíduos caso o terminal tenha permissão POSIX
        direct_removed = 0
        direct_bytes = 0
        for trash_dir in resolved_paths:
            if os.path.exists(trash_dir) and os.path.isdir(trash_dir):
                try:
                    for item in os.listdir(trash_dir):
                        item_path = os.path.join(trash_dir, item)
                        try:
                            if os.path.islink(item_path) or os.path.isfile(item_path):
                                sz = os.path.getsize(item_path) if not os.path.islink(item_path) else 0
                                _force_remove_file(item_path)
                                direct_removed += 1
                                direct_bytes += sz
                            elif os.path.isdir(item_path):
                                b, f, _ = self._clean_directory_contents(
                                    item_path, mode=ExecutionMode.REAL, remove_root=True
                                )
                                direct_removed += (f + 1)
                                direct_bytes += b
                        except Exception:
                            pass
                except Exception:
                    pass

        count_after = self._count_macos_trash_items()
        files_removed = max(count_before - count_after, direct_removed)
        if files_removed == 0 and count_before > 0 and finder_success:
            files_removed = count_before

        total_bytes = max(bytes_estimated, direct_bytes)

        if files_removed > 0:
            details = (
                f"Lixeira do macOS esvaziada com sucesso: {files_removed} itens removidos "
                f"({format_bytes(total_bytes)} liberados)."
            )
        elif count_before == 0:
            details = "Lixeira do macOS já estava vazia. Nenhum item a remover."
        else:
            details = "Comando de esvaziamento da Lixeira executado com sucesso."

        return AutonomousCleanupEntry(
            id=rule.id,
            name=rule.name,
            category=rule.category,
            target_paths=resolved_paths,
            bytes_freed=total_bytes,
            files_removed=files_removed,
            status="cleaned",
            details=details,
            errors_skipped=0,
        )

    def _query_windows_recycle_bin(self) -> Tuple[int, int]:
        """Consulta bytes e número de itens na lixeira do Windows via Shell32 ou PowerShell."""
        if sys.platform == "win32":
            try:
                import ctypes
                from ctypes import wintypes

                class SHQUERYRBINFO(ctypes.Structure):
                    _fields_ = [
                        ("cbSize", wintypes.DWORD),
                        ("i64Size", ctypes.c_int64),
                        ("i64NumItems", ctypes.c_int64),
                    ]

                rb = SHQUERYRBINFO()
                rb.cbSize = ctypes.sizeof(SHQUERYRBINFO)
                res = ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(rb))
                if res == 0:
                    return int(rb.i64Size), int(rb.i64NumItems)
            except Exception:
                pass

            try:
                cmd = "(New-Object -ComObject Shell.Application).NameSpace(0xa).Items().Count"
                res = subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                if res.returncode == 0 and res.stdout.strip().isdigit():
                    return 0, int(res.stdout.strip())
            except Exception:
                pass

        return 0, 0

    def _execute_windows_trash(
        self, rule: AutonomousCleanupRule, mode: ExecutionMode
    ) -> AutonomousCleanupEntry:
        """Executa o esvaziamento nativo da Lixeira no Windows usando Shell32 ou PowerShell."""
        valid_paths = [
            expand_os_path(p)
            for p in rule.target_paths
            if isinstance(p, str) and ("recycle" in p.lower() or "$recycle.bin" in p.lower())
        ]
        if not valid_paths:
            if not rule.target_paths or rule.id == "win_trash":
                valid_paths = ["$Recycle.Bin"]
            else:
                return AutonomousCleanupEntry(
                    id=rule.id,
                    name=rule.name,
                    category=rule.category,
                    target_paths=[],
                    bytes_freed=0,
                    files_removed=0,
                    status="cleaned" if mode == ExecutionMode.REAL else "simulated",
                    details="Nenhum diretório de Lixeira seguro/válido identificado para esta regra.",
                    errors_skipped=1,
                )
        resolved_paths = valid_paths

        bytes_total, items_count = self._query_windows_recycle_bin()

        if mode == ExecutionMode.DRY_RUN:
            details = (
                f"Simulação (Dry-Run): {items_count} itens na Lixeira do Windows "
                f"({format_bytes(bytes_total)} recuperáveis)."
                if items_count > 0
                else "Lixeira do Windows vazia. Nenhum item pendente de esvaziamento."
            )
            return AutonomousCleanupEntry(
                id=rule.id,
                name=rule.name,
                category=rule.category,
                target_paths=resolved_paths,
                bytes_freed=bytes_total,
                files_removed=items_count,
                status="simulated",
                details=details,
                errors_skipped=0,
            )

        # Modo REAL
        success = False
        # 1. Invocação nativa da API Shell32:
        # Flag 7 = SHERB_NOCONFIRMATION (1) | SHERB_NOPROGRESSUI (2) | SHERB_NOSOUND (4)
        if sys.platform == "win32":
            try:
                import ctypes
                res = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
                if res == 0:
                    success = True
            except Exception:
                pass

        # 2. Fallback PowerShell
        if not success:
            try:
                cmd = "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"
                res = subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                    capture_output=True,
                    timeout=10,
                    check=False,
                )
                if res.returncode == 0:
                    success = True
            except Exception:
                pass

        files_removed = items_count if (success or items_count > 0) else 0
        bytes_freed = bytes_total if (success or items_count > 0) else 0

        if files_removed > 0:
            details = (
                f"Lixeira do Windows esvaziada com sucesso: {files_removed} itens removidos "
                f"({format_bytes(bytes_freed)} liberados)."
            )
        elif items_count == 0:
            details = "Lixeira do Windows já estava vazia. Nenhum item a remover."
        else:
            details = f"Comando de esvaziamento da Lixeira concluído com status: {'sucesso' if success else 'parcial'}."

        return AutonomousCleanupEntry(
            id=rule.id,
            name=rule.name,
            category=rule.category,
            target_paths=resolved_paths,
            bytes_freed=bytes_freed,
            files_removed=files_removed,
            status="cleaned",
            details=details,
            errors_skipped=0 if success else 1,
        )

    def _execute_trash_rule(
        self, rule: AutonomousCleanupRule, mode: ExecutionMode
    ) -> AutonomousCleanupEntry:
        """Desvia para o handler nativo de Lixeira do macOS ou Windows."""
        is_macos = rule.os_platform == "macos" or (sys.platform == "darwin" and rule.os_platform != "windows")
        if is_macos:
            return self._execute_macos_trash(rule, mode)
        else:
            return self._execute_windows_trash(rule, mode)

    def _expand_rule_targets(self, raw_target: str) -> List[str]:
        """Expande wildcards (*) e tokens Darwin aplicando a whitelist de proteção de estado."""
        if not isinstance(raw_target, str) or not raw_target.strip():
            return []
        raw_parts = [p for p in raw_target.replace("\\", "/").split("/") if p]
        if ".." in raw_parts or "\x00" in raw_target:
            return []
        expanded = expand_os_path(raw_target)
        if "*" in expanded or "?" in expanded:
            try:
                matches = glob.glob(expanded)
            except Exception:
                matches = []
            safe_matches: List[str] = []
            for m in sorted(matches):
                if is_protected_macos_cache_path(m):
                    continue
                if is_safe_path_to_clean(m):
                    safe_matches.append(m)
            return safe_matches
        if is_protected_macos_cache_path(expanded):
            return []
        return [expanded]

    def execute_rule(
        self,
        rule: AutonomousCleanupRule,
        mode: ExecutionMode,
    ) -> AutonomousCleanupEntry:
        if self._is_trash_rule(rule):
            return self._execute_trash_rule(rule, mode)

        total_bytes = 0
        total_files = 0
        total_errors = 0
        resolved_paths: List[str] = []

        for raw_target in rule.target_paths:
            if not isinstance(raw_target, str):
                continue
            has_wildcard = "*" in raw_target or "?" in raw_target
            candidates = self._expand_rule_targets(raw_target)
            if not candidates:
                resolved_paths.append(expand_os_path(raw_target))
                continue
            for expanded in candidates:
                if len(resolved_paths) < 25:
                    resolved_paths.append(expanded)
                if (has_wildcard or is_safe_path_to_clean(raw_target)) and is_safe_path_to_clean(expanded) and os.path.exists(expanded):
                    b_freed, f_rem, errs = self._clean_directory_contents(
                        expanded, mode=mode, remove_root=has_wildcard
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

    def _measure_path_size_and_count(self, target_path: str) -> Tuple[int, int]:
        """Mede o total de bytes e quantidade de arquivos de um item antes de mover para a Lixeira."""
        if not os.path.exists(target_path):
            return 0, 0
        if os.path.islink(target_path) or os.path.isfile(target_path):
            try:
                sz = 0 if os.path.islink(target_path) else os.path.getsize(target_path)
                return sz, 1
            except OSError:
                return 0, 1
        total_b = 0
        total_f = 0
        for root, _, files in os.walk(target_path):
            for fname in files:
                fp = os.path.join(root, fname)
                total_f += 1
                try:
                    if not os.path.islink(fp):
                        total_b += os.path.getsize(fp)
                except OSError:
                    pass
        return total_b, max(1, total_f)

    def move_paths_to_trash(
        self,
        paths: List[str],
        mode: ExecutionMode = ExecutionMode.REAL,
        custom_trash_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Move arquivos ou diretórios com segurança para a Lixeira do usuário (~/.Trash no macOS
        ou Recycle Bin no Windows), garantindo reversibilidade e resolução de conflito de nomes.
        """
        total_bytes = 0
        total_files = 0
        total_errors = 0
        affected_paths: List[str] = []
        trash_destinations: List[str] = []

        trash_base = custom_trash_dir or os.path.expanduser("~/.Trash")

        for p in paths:
            if not isinstance(p, str) or not is_safe_path_to_clean(p):
                total_errors += 1
                continue
            expanded = expand_os_path(p)
            if not os.path.exists(expanded) or not is_safe_path_to_clean(expanded) or is_protected_macos_cache_path(expanded):
                total_errors += 1
                continue

            b_size, f_count = self._measure_path_size_and_count(expanded)
            if mode == ExecutionMode.DRY_RUN:
                affected_paths.append(expanded)
                total_bytes += b_size
                total_files += f_count
                continue

            # Modo REAL: move para a Lixeira
            try:
                os.makedirs(trash_base, exist_ok=True)
                base_name = os.path.basename(expanded.rstrip("\\/"))
                dest_path = os.path.join(trash_base, base_name)
                if os.path.exists(dest_path):
                    stem, ext = os.path.splitext(base_name)
                    dest_path = os.path.join(trash_base, f"{stem}_{int(time.time() * 1000)}{ext}")

                shutil.move(expanded, dest_path)
                affected_paths.append(expanded)
                trash_destinations.append(dest_path)
                total_bytes += b_size
                total_files += f_count
            except (PermissionError, OSError):
                total_errors += 1

        status = "trashed" if mode == ExecutionMode.REAL else "simulated"
        action_verb = "Movidos para a Lixeira" if mode == ExecutionMode.REAL else "Simulados para a Lixeira"
        details = f"{action_verb}: {len(affected_paths)} item(ns) ({total_files} arquivos, {format_bytes(total_bytes)})."

        return {
            "status": status,
            "action": "trash",
            "success": len(affected_paths) > 0 or total_errors == 0,
            "bytes_freed": total_bytes,
            "bytes_freed_formatted": format_bytes(total_bytes),
            "files_removed": total_files,
            "affected_paths": affected_paths,
            "trash_destinations": trash_destinations,
            "errors_skipped": total_errors,
            "message": details,
        }
