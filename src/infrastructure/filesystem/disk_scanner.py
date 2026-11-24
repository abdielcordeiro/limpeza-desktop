# -*- coding: utf-8 -*-
"""Scanner Profundo Multiplataforma (Windows & macOS) com os.scandir e 5 Camadas Anti-Falsos Positivos."""
import os
import plistlib
import heapq
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple, Optional
from src.domain.entities import (
    PartitionInfo,
    OccupantItem,
    CleanableItem,
    InstalledAppInfo,
    HardwareHealthInfo,
    DirectoryInspectionNode,
    StorageCategoryBreakdown,
    StorageXRayReport,
)
from src.domain.ports import IDiskScannerPort
from src.domain.value_objects import OSPlatform, SafetyClassification, format_bytes
from src.infrastructure.filesystem.autonomous_cleaner import (
    is_safe_path_to_clean,
    get_darwin_user_dir,
)


# Diretórios virtuais ou imutáveis do SO que devem ser podados para evitar loops e travamentos
PRUNED_DIR_NAMES = {
    "$recycle.bin",
    "system volume information",
    "winsxs",
    "servicing",
    ".spotlight-v100",
    ".fseventsd",
    ".trashes",
    ".documentrevisions-v100",
    ".temporaryitems",
    "dev",
    "proc",
    "cores",
}

PRUNED_ABSOLUTE_PREFIXES = (
    "/system/volumes",
    "/system/library",
    "/dev",
    "/proc",
    "/private/var/vm",
    "/private/var/folders",
    "/volumes/recovery",
    "/volumes/preboot",
    "/volumes/vm",
    "c:\\windows\\winsxs",
    "c:\\windows\\servicing",
    "c:\\windows\\installer",
)

# Pastas estruturais do SO que jamais podem ser marcadas como órfãs
STRUCTURAL_PROTECTED_NAMES = {
    "appdata",
    "local",
    "locallow",
    "roaming",
    "programs",
    "microsoft",
    "windows",
    "packages",
    "apple",
    "library",
    "application support",
    "containers",
    "group containers",
    "caches",
    "logs",
    "preferences",
    "saved application state",
    "httpstorages",
    "cookies",
    "application scripts",
    "cloudstorage",
    "mobile documents",
    "keychains",
    "webkit",
    "developer",
    "xcode",
    "coresimulator",
    "mobilesync",
    "backup",
    "messages",
    "attachments",
    "mail",
    "safari",
    "system",
    "program files",
    "program files (x86)",
    "programdata",
    "common files",
    "windows defender",
}

# Artefatos Reconstruíveis de Projetos de Desenvolvimento (RF-18 / ADR-011)
REBUILDABLE_PROJECT_ARTIFACTS = {
    "node_modules",
    ".venv",
    "venv",
    "target",
    "build",
    ".dart_tool",
    ".next",
    ".nuxt",
    "dist",
    "pods",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".parcel-cache",
    ".turbo",
}


def classify_item_safety(item_path: str, item_type: str) -> Tuple[str, str, str]:
    """
    Classifica o nível de segurança de um arquivo ou pasta entre as 4 categorias exigidas:
    - 🚫 Não Apagar (Sistema Operacional)
    - ⚙️ Desinstalar via Sistema / App
    - ✅ Limpeza Direta (Sem Risco ao SO)
    - ⚠️ Avaliar Conteúdo Pessoal
    """
    norm = item_path.replace("\\", "/").lower()

    # 1. Protegido do Sistema Operacional
    os_protected_patterns = (
        "/windows/",
        "c:/windows",
        "/system32",
        "/syswow64",
        "/winsxs",
        "/system/",
        "/usr/",
        "/bin/",
        "/sbin/",
        "/private/var/db",
        "/library/apple",
        "/library/extensions",
        "$recycle.bin",
        "system volume information",
    )
    if any(pat in norm for pat in os_protected_patterns):
        return (
            SafetyClassification.DO_NOT_DELETE.value,
            "danger",
            "Componente essencial do Sistema Operacional. Nunca modifique ou exclua manualmente.",
        )

    # 2. Limpeza Direta (Caches, Temp, Dumps, Shaders)
    direct_clean_patterns = (
        "/temp/",
        "/tmp/",
        "/cache/",
        "/caches/",
        "/dxcache",
        "/glcache",
        "/d3dscache",
        "/nv_cache",
        "/prefetch",
        "/crashdumps",
        "/crashreporter",
        "/diagnosticreports",
        "/deriveddata",
        "/code cache",
        "/gpucache",
        "/cachestorage",
        "/ebwebview",
        "/.trash",
    )
    if any(pat in norm for pat in direct_clean_patterns) or norm.endswith(
        (".tmp", ".dmp", ".log", ".dmg", ".iso", ".msi")
    ):
        return (
            SafetyClassification.DIRECT_CLEAN.value,
            "success",
            "Cache transitório, log, temporário ou imagem de instalador reconstruível. Limpeza direta 100% segura.",
        )

    # 3. Aplicativos Instalados
    app_patterns = (
        "/program files",
        "/program files (x86)",
        "/appdata/local/programs",
        "/applications/",
        ".app",
        "/steamlibrary",
        "/epic games",
    )
    if any(pat in norm for pat in app_patterns):
        return (
            SafetyClassification.UNINSTALL_VIA_OS.value,
            "warning",
            "Software ou pacote de aplicativo instalado. Desinstale via Configurações do Sistema ou gerenciador oficial.",
        )

    # 4. Conteúdo Pessoal do Usuário
    return (
        SafetyClassification.REVIEW_PERSONAL.value,
        "purple",
        "Arquivo ou diretório de dados do usuário. Revise o conteúdo antes de mover ou remover.",
    )


GENERIC_INDICATOR_STOPWORDS = {
    "com", "org", "net", "io", "app", "apps", "mac", "macos", "win", "windows",
    "desktop", "client", "helper", "install", "installer", "installed", "uninstall",
    "uninstalled", "setup", "update", "updater", "service", "services", "agent",
    "daemon", "system", "user", "data", "core", "base", "tool", "tools", "util",
}


def matches_active_software(folder_name: str, active_indicators: Set[str]) -> bool:
    """
    Verifica se o nome da pasta ou identificador Reverse-DNS (ex: com.vendor.app)
    possui correspondência nas 5 camadas de softwares ativos.
    """
    import re as _re

    clean = folder_name.strip().lower()
    if not clean:
        return True

    if clean in STRUCTURAL_PROTECTED_NAMES or clean.startswith("com.apple.") or clean.startswith("microsoft."):
        return True

    # Remove sufixos comuns do macOS
    for suffix in (".savedstate", ".binarycookies", ".plist"):
        if clean.endswith(suffix):
            clean = clean[: -len(suffix)]

    if clean in active_indicators and clean not in GENERIC_INDICATOR_STOPWORDS:
        return True

    # Tokeniza identificadores Reverse-DNS (com.empresa.app), separadores e CamelCase
    raw_words = _re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|[a-z0-9]+", folder_name)
    delim_words = clean.replace(".", " ").replace("-", " ").replace("_", " ").split()
    tokens = {
        w.lower()
        for w in (raw_words + delim_words)
        if len(w) > 2 and w.lower() not in GENERIC_INDICATOR_STOPWORDS
    }

    for indicator in active_indicators:
        if len(indicator) < 3 or indicator in GENERIC_INDICATOR_STOPWORDS:
            continue
        if indicator == clean or indicator in tokens:
            return True
        if len(indicator) >= 6 and (
            clean.startswith(indicator)
            or clean.endswith(indicator)
            or f".{indicator}" in clean
        ):
            return True

    return False


def _effective_file_size(st: os.stat_result) -> int:
    """
    Retorna o tamanho efetivo ocupado em disco, usando min(st_size, st_blocks * 512)
    no macOS/POSIX para evitar distorção por sparse files ou stubs online do iCloud.
    """
    logical = st.st_size
    if hasattr(st, "st_blocks") and st.st_blocks is not None and st.st_blocks > 0:
        physical = st.st_blocks * 512
        return min(logical, physical) if logical > 0 else physical
    return logical


def _fast_dir_size(dir_path: str, max_files: int = 25000) -> int:
    """Calcula rapidamente o tamanho de um pacote fechado (.app, node_modules, .git) via os.scandir."""
    total = 0
    seen = 0
    stack = [dir_path]
    while stack and seen < max_files:
        curr = stack.pop()
        try:
            with os.scandir(curr) as it:
                for entry in it:
                    seen += 1
                    if seen > max_files:
                        break
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_file(follow_symlinks=False):
                            total += _effective_file_size(entry.stat(follow_symlinks=False))
                        elif entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                    except OSError:
                        continue
        except OSError:
            continue
    return total


def _extract_drive_label(path: str, os_platform: OSPlatform) -> str:
    if os_platform == OSPlatform.WINDOWS:
        drive, _ = os.path.splitdrive(path)
        return (drive.upper() + "\\") if drive else "C:\\"
    norm = path.replace("\\", "/")
    if norm.startswith("/Volumes/"):
        parts = norm.split("/")
        if len(parts) >= 3:
            return f"/Volumes/{parts[2]}"
    return "/"


class DiskScannerAdapter(IDiskScannerPort):
    """Implementa varredura rápida e profunda de disco, detecção de órfãos e apps instalados."""

    def __init__(
        self,
        min_orphan_bytes: int = 1024 * 1024,
        max_visited_dirs: int = 25000,
        max_bundle_files: int = 25000,
    ) -> None:
        # 1 MB padrão para órfãos (permite achar pastas órfãs reais sem ruído de pastas vazias)
        self.min_orphan_bytes = min_orphan_bytes
        self.max_visited_dirs = max_visited_dirs
        self.max_bundle_files = max_bundle_files

    def _scan_installed_apps(
        self,
        target_paths: List[str],
        os_platform: OSPlatform,
        folder_sizes: Dict[str, int],
    ) -> List[InstalledAppInfo]:
        """Lista aplicativos instalados por tamanho para diagnóstico e sugestão de migração."""
        apps: List[InstalledAppInfo] = []
        seen_paths: Set[str] = set()

        if os_platform == OSPlatform.MACOS:
            app_roots = ["/Applications", os.path.expanduser("~/Applications")]
            for tpath in target_paths:
                if tpath.endswith("Applications") and tpath not in app_roots:
                    app_roots.append(tpath)

            for root_dir in app_roots:
                if not os.path.exists(root_dir):
                    continue
                try:
                    with os.scandir(root_dir) as it:
                        for entry in it:
                            if not entry.is_dir(follow_symlinks=False) or not entry.name.endswith(".app"):
                                continue
                            if entry.path in seen_paths:
                                continue
                            seen_paths.add(entry.path)
                            app_size = folder_sizes.get(entry.path) or _fast_dir_size(entry.path)
                            if app_size <= 0:
                                continue
                            folder_sizes[entry.path] = app_size
                            app_name = entry.name[:-4]
                            vendor = "Apple / macOS App"
                            bundle_id = ""
                            plist_path = os.path.join(entry.path, "Contents", "Info.plist")
                            if os.path.exists(plist_path):
                                try:
                                    with open(plist_path, "rb") as pf:
                                        plist_data = plistlib.load(pf)
                                    bundle_id = str(plist_data.get("CFBundleIdentifier", ""))
                                    app_name = str(
                                        plist_data.get("CFBundleDisplayName")
                                        or plist_data.get("CFBundleName")
                                        or app_name
                                    )
                                    if bundle_id:
                                        parts = bundle_id.split(".")
                                        if len(parts) >= 2:
                                            vendor = parts[1].capitalize()
                                except Exception:
                                    pass
                            can_migrate = app_size > 250 * 1024 * 1024 and not bundle_id.startswith("com.apple.")
                            apps.append(
                                InstalledAppInfo(
                                    name=app_name,
                                    path=entry.path,
                                    size=app_size,
                                    size_formatted=format_bytes(app_size),
                                    drive=_extract_drive_label(entry.path, os_platform),
                                    vendor=vendor,
                                    uninstall_hint=(
                                        "Para remover no macOS: mova o bundle .app para a Lixeira ou use "
                                        "'brew uninstall --cask' e limpe os resíduos na aba Pastas Órfãs."
                                    ),
                                    can_migrate=can_migrate,
                                    target_drive="/Volumes/ Externo (ou manter no SSD APFS)",
                                    bundle_id=bundle_id,
                                )
                            )
                except OSError:
                    continue
        else:
            # Windows: Program Files, Program Files (x86), %LOCALAPPDATA%\Programs
            win_roots = [
                os.environ.get("ProgramFiles", r"C:\Program Files"),
                os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
            ]
            for tpath in target_paths:
                norm_t = tpath.lower()
                if any(k in norm_t for k in ("program files", "programs", "games", "jogos")):
                    if tpath not in win_roots:
                        win_roots.append(tpath)

            for root_dir in win_roots:
                if not root_dir or not os.path.exists(root_dir):
                    continue
                try:
                    with os.scandir(root_dir) as it:
                        for entry in it:
                            if not entry.is_dir(follow_symlinks=False):
                                continue
                            if entry.name.lower() in {"common files", "windows defender", "microsoft", "windows nt", "internet explorer"}:
                                continue
                            if entry.path in seen_paths:
                                continue
                            seen_paths.add(entry.path)
                            app_size = folder_sizes.get(entry.path) or _fast_dir_size(entry.path)
                            if app_size < 5 * 1024 * 1024:
                                continue
                            folder_sizes[entry.path] = app_size
                            can_migrate = app_size > 500 * 1024 * 1024
                            apps.append(
                                InstalledAppInfo(
                                    name=entry.name,
                                    path=entry.path,
                                    size=app_size,
                                    size_formatted=format_bytes(app_size),
                                    drive=_extract_drive_label(entry.path, os_platform),
                                    vendor=entry.name,
                                    uninstall_hint=(
                                        "Desinstale via 'Configurações > Aplicativos > Aplicativos Instalados' "
                                        "ou reinstale em D:\\Aplicativos para liberar o SSD principal."
                                    ),
                                    can_migrate=can_migrate,
                                    target_drive="D:\\ (ou partição secundária)",
                                )
                            )
                except OSError:
                    continue

        apps.sort(key=lambda a: a.size, reverse=True)
        return apps[:60]

    def scan_and_evaluate(
        self,
        target_paths: List[str],
        active_indicators: Set[str],
        partitions: List[PartitionInfo],
        os_platform: OSPlatform,
        top_n: int = 100,
    ) -> Tuple[List[OccupantItem], List[CleanableItem], List[InstalledAppInfo]]:
        folder_sizes: Dict[str, int] = {}
        # Mantém um min-heap com os maiores arquivos para baixo consumo de RAM (RNF-04)
        largest_files_heap: List[Tuple[int, str, str, str]] = []
        clean_candidates: List[CleanableItem] = []

        normalized_targets = [os.path.abspath(p) for p in target_paths if os.path.exists(p)]

        from collections import deque

        for base_target in normalized_targets:
            base_norm = os.path.realpath(base_target).replace("\\", "/").lower()
            queue = deque([base_target])
            visited_dirs = 0
            while queue and visited_dirs < self.max_visited_dirs:
                current_dir = queue.popleft()
                visited_dirs += 1
                curr_norm = os.path.realpath(current_dir).replace("\\", "/").lower()

                if any(
                    curr_norm.startswith(pref) and not base_norm.startswith(pref)
                    for pref in PRUNED_ABSOLUTE_PREFIXES
                ):
                    continue

                dir_base = os.path.basename(current_dir).lower()
                if dir_base in PRUNED_DIR_NAMES:
                    continue

                # Se for um bundle fechado (.app, .xcarchive, .simruntime), artefato de projeto ou .git, mede de forma agregada rápida
                is_rebuildable = dir_base in REBUILDABLE_PROJECT_ARTIFACTS
                if dir_base.endswith((".app", ".xcarchive", ".simruntime")) or is_rebuildable or dir_base == ".git":
                    agg_size = _fast_dir_size(current_dir, max_files=self.max_bundle_files)
                    if agg_size > 0:
                        folder_sizes[current_dir] = folder_sizes.get(current_dir, 0) + agg_size
                        path_obj = Path(current_dir)
                        for parent in path_obj.parents:
                            p_str = str(parent)
                            if p_str.startswith(base_target):
                                folder_sizes[p_str] = folder_sizes.get(p_str, 0) + agg_size

                        if is_rebuildable and agg_size >= self.min_orphan_bytes:
                            norm_curr = current_dir.replace("\\", "/").lower()
                            is_sys = (
                                norm_curr.startswith("/applications")
                                or norm_curr.startswith("/system")
                                or norm_curr.startswith("c:/windows")
                            )
                            if not is_sys:
                                parent_name = os.path.basename(os.path.dirname(current_dir)) or ""
                                item_name = f"{parent_name}/{dir_base}" if parent_name else dir_base
                                drv = _extract_drive_label(current_dir, os_platform)
                                clean_candidates.append(
                                    CleanableItem(
                                        name=item_name,
                                        path=current_dir,
                                        size=agg_size,
                                        size_formatted=format_bytes(agg_size),
                                        drive=drv,
                                        risk_level="Seguro / Reconstruível (npm / pip / gradle / cargo)",
                                        risk_badge="info",
                                        item_type="Artefato Reconstruível de Projeto (Build / Dependências)",
                                        reason=f"Diretório '{dir_base}' dentro do projeto '{parent_name}'. Ocupa espaço na categoria 'Documentos' do macOS e pode ser recriado a qualquer momento.",
                                        how_to_fix="Mova para a Lixeira ou exclua se não estiver trabalhando ativamente neste projeto agora.",
                                        is_orphan=False,
                                    )
                                )
                    continue

                current_files_size = 0
                try:
                    with os.scandir(current_dir) as it:
                        for entry in it:
                            try:
                                if entry.is_symlink():
                                    continue
                                if entry.is_dir(follow_symlinks=False):
                                    if entry.name.lower() not in PRUNED_DIR_NAMES:
                                        queue.append(entry.path)
                                elif entry.is_file(follow_symlinks=False):
                                    fsize = _effective_file_size(entry.stat(follow_symlinks=False))
                                    current_files_size += fsize
                                    drv = _extract_drive_label(entry.path, os_platform)

                                    if len(largest_files_heap) < top_n * 2:
                                        heapq.heappush(largest_files_heap, (fsize, entry.path, entry.name, drv))
                                    elif fsize > largest_files_heap[0][0]:
                                        heapq.heapreplace(largest_files_heap, (fsize, entry.path, entry.name, drv))

                                    # Verifica se é arquivo temporário/dump grande descartável (> 5 MB)
                                    fname_l = entry.name.lower()
                                    fpath_l = entry.path.replace("\\", "/").lower()
                                    if fsize >= 5 * 1024 * 1024 and (
                                        fname_l.endswith((".tmp", ".dmp", ".log", ".crash"))
                                        or "/temp/" in fpath_l
                                        or "/caches/" in fpath_l
                                        or "/crashdumps/" in fpath_l
                                    ):
                                        clean_candidates.append(
                                            CleanableItem(
                                                name=entry.name,
                                                path=entry.path,
                                                size=fsize,
                                                size_formatted=format_bytes(fsize),
                                                drive=drv,
                                                risk_level="Seguro / Baixo Risco (Pode Apagar)",
                                                risk_badge="success",
                                                item_type="Arquivo Temporário / Dump",
                                                reason="Arquivo temporário, log de execução ou dump de falha descartável.",
                                                how_to_fix="Pode ser limpo autonomamente ou excluído sem risco.",
                                                is_orphan=False,
                                            )
                                        )
                            except (PermissionError, FileNotFoundError, OSError):
                                continue
                except (PermissionError, FileNotFoundError, OSError):
                    continue

                if current_files_size > 0:
                    folder_sizes[current_dir] = folder_sizes.get(current_dir, 0) + current_files_size
                    path_obj = Path(current_dir)
                    for parent in path_obj.parents:
                        p_str = str(parent)
                        if p_str.startswith(base_target):
                            folder_sizes[p_str] = folder_sizes.get(p_str, 0) + current_files_size

        # Avalia pastas agregadas para detectar Órfãos (5 Camadas) e Gargalos de Cache
        for f_path, f_size in folder_sizes.items():
            if f_size < self.min_orphan_bytes:
                continue
            norm_p = f_path.replace("\\", "/")
            norm_l = norm_p.lower()
            folder_name = os.path.basename(f_path.rstrip("\\/"))
            if not folder_name or folder_name.lower() in STRUCTURAL_PROTECTED_NAMES:
                continue

            drv = _extract_drive_label(f_path, os_platform)

            # 1. Caches de Shaders de GPU
            if any(k in norm_l for k in ("dxcache", "glcache", "d3dscache", "nv_cache", "com.apple.webkit.gpu")):
                clean_candidates.append(
                    CleanableItem(
                        name=folder_name,
                        path=f_path,
                        size=f_size,
                        size_formatted=format_bytes(f_size),
                        drive=drv,
                        risk_level="Seguro / Baixo Risco (Pode Apagar)",
                        risk_badge="success",
                        item_type="Cache de GPU & Shaders",
                        reason="Shaders compilados que podem ser recriados automaticamente pelo driver gráfico.",
                        how_to_fix="Limpeza direta 100% segura.",
                        is_orphan=False,
                    )
                )
                continue

            # 2. Relatórios de Erro e Crash Dumps
            if any(k in norm_l for k in ("crashdumps", "/wer/", "crashreports", "crashreporter", "diagnosticreports")):
                clean_candidates.append(
                    CleanableItem(
                        name=folder_name,
                        path=f_path,
                        size=f_size,
                        size_formatted=format_bytes(f_size),
                        drive=drv,
                        risk_level="Seguro / Baixo Risco (Pode Apagar)",
                        risk_badge="success",
                        item_type="Relatórios de Erro & Dumps",
                        reason="Relatórios de falha e dumps de memória acumulados.",
                        how_to_fix="Pode ser excluído com segurança.",
                        is_orphan=False,
                    )
                )
                continue

            # 3. Caches de Navegadores & Electron
            if any(k in norm_l for k in ("cachestorage", "ebwebview", "code cache", "gpucache", "cache_data")):
                clean_candidates.append(
                    CleanableItem(
                        name=folder_name,
                        path=f_path,
                        size=f_size,
                        size_formatted=format_bytes(f_size),
                        drive=drv,
                        risk_level="Seguro / Baixo Risco (Pode Apagar)",
                        risk_badge="success",
                        item_type="Cache de Navegador & Electron",
                        reason="Cache transitório de navegador ou app Electron (preserva logins e dados).",
                        how_to_fix="Limpeza segura de cache de aplicativo.",
                        is_orphan=False,
                    )
                )
                continue

            # 4. Caches de Dev Tools, Compiladores e Ecossistemas (Xcode, JetBrains, Node, Python, JVM, Rust, Go)
            if any(
                k in norm_l
                for k in (
                    "pip/cache",
                    "caches/pip",
                    "npm-cache",
                    "_cacache",
                    "yarn/cache",
                    "caches/yarn",
                    "berry/cache",
                    "caches/pnpm",
                    ".bun/install/cache",
                    ".gradle/caches",
                    ".nuget/packages",
                    "deriveddata",
                    "devicesupport",
                    "coresimulator/caches",
                    "caches/jetbrains",
                    "logs/jetbrains",
                    "caches/homebrew",
                    "caches/cocoapods",
                    "caches/uv",
                    "cache/uv",
                    "caches/pypoetry",
                    "caches/ms-playwright",
                    "caches/cypress",
                    "caches/go-build",
                    ".cargo/registry/cache",
                    ".pub-cache/_temp",
                )
            ):
                clean_candidates.append(
                    CleanableItem(
                        name=folder_name,
                        path=f_path,
                        size=f_size,
                        size_formatted=format_bytes(f_size),
                        drive=drv,
                        risk_level="Seguro / Baixo Risco (Pode Apagar)",
                        risk_badge="success",
                        item_type="Cache de Dev Tools & Builds",
                        reason="Cache de pacotes, símbolos de SDK ou artefatos de compilação reconstruíveis.",
                        how_to_fix="Pode ser limpo com segurança (movido para Lixeira ou excluído).",
                        is_orphan=False,
                    )
                )
                continue

            # 5. Verificação de Pastas Órfãs (5 Camadas) em AppData (Windows) e 12 diretórios da ~/Library (macOS)
            parent_dir = os.path.dirname(f_path.rstrip("\\/")).replace("\\", "/").lower()
            is_direct_orphan_container = any(
                parent_dir.endswith(container_suffix)
                for container_suffix in (
                    "/appdata/local",
                    "/appdata/roaming",
                    "/appdata/locallow",
                    "/library/application support",
                    "/library/containers",
                    "/library/group containers",
                    "/library/saved application state",
                    "/library/caches",
                    "/library/preferences",
                    "/library/httpstorages",
                    "/library/webkit",
                    "/library/logs",
                    "/library/cookies",
                    "/library/application scripts",
                )
            )
            if is_direct_orphan_container:
                if not matches_active_software(folder_name, active_indicators):
                    clean_candidates.append(
                        CleanableItem(
                            name=folder_name,
                            path=f_path,
                            size=f_size,
                            size_formatted=format_bytes(f_size),
                            drive=drv,
                            risk_level="Médio Risco (Resíduo Órfão Verificado)",
                            risk_badge="warning",
                            item_type="Resíduo Órfão de Software Desinstalado",
                            reason=(
                                f"A pasta '{folder_name}' não pertence a nenhum software ativo nas "
                                "5 camadas de verificação (Apps, Registro/Pkg, Inicialização, Processos e Whitelist)."
                            ),
                            how_to_fix="Marque para limpeza assistida no painel ou remova a pasta para recuperar espaço.",
                            is_orphan=True,
                        )
                    )

        # Deduplicação hierárquica (evita reportar pai e filho simultaneamente)
        def deduplicate_cleanables(items: List[CleanableItem]) -> List[CleanableItem]:
            items.sort(key=lambda x: x.size, reverse=True)
            unique: List[CleanableItem] = []
            seen: List[str] = []
            for item in items:
                p_norm = os.path.abspath(item.path).rstrip("\\/")
                if any(
                    p_norm == s or p_norm.startswith(s + os.sep) or s.startswith(p_norm + os.sep)
                    for s in seen
                ):
                    continue
                seen.append(p_norm)
                unique.append(item)
            return unique

        clean_suggestions = deduplicate_cleanables(clean_candidates)[:top_n]

        # Aplicativos instalados por tamanho
        installed_apps = self._scan_installed_apps(normalized_targets, os_platform, folder_sizes)

        # Top 100 Maiores Ocupantes (Arquivos e Pastas deduplicados)
        sorted_folders = sorted(folder_sizes.items(), key=lambda kv: kv[1], reverse=True)
        dedup_folders: List[Tuple[str, int]] = []
        seen_folder_paths: List[str] = []
        for f_path, f_size in sorted_folders:
            if f_path in normalized_targets:
                continue
            p_norm = os.path.abspath(f_path).rstrip("\\/")
            # Evita colocar o pai e todos os seus filhos imediatos repetindo a mesma contagem
            if any(
                p_norm.startswith(s + os.sep) or s.startswith(p_norm + os.sep)
                for s in seen_folder_paths
            ):
                continue
            seen_folder_paths.append(p_norm)
            dedup_folders.append((f_path, f_size))
            if len(dedup_folders) >= top_n:
                break

        raw_occupants: List[OccupantItem] = []
        for f_path, f_size in dedup_folders:
            act_label, badge_cls, rec = classify_item_safety(f_path, "Pasta")
            
            # Mapeia dinamicamente as subpastas mais pesadas (drill-down limpo)
            p_clean = os.path.abspath(f_path).rstrip(os.sep)
            direct_children: List[Tuple[str, int]] = []
            for p_cand, p_sz in folder_sizes.items():
                cand_clean = os.path.abspath(p_cand).rstrip(os.sep)
                if os.path.dirname(cand_clean) == p_clean and cand_clean != p_clean:
                    direct_children.append((p_cand, p_sz))

            if not direct_children and os.path.isdir(f_path):
                try:
                    with os.scandir(f_path) as it:
                        for entry in it:
                            if entry.is_dir(follow_symlinks=False):
                                sz = folder_sizes.get(entry.path, 0)
                                if sz > 0:
                                    direct_children.append((entry.path, sz))
                except (PermissionError, OSError):
                    pass

            direct_children.sort(key=lambda x: x[1], reverse=True)
            sub_occupants: List[Dict[str, Any]] = []
            for sub_p, sub_sz in direct_children[:12]:
                if sub_sz > 512 * 1024:  # Maior que 512 KB
                    pct = round((sub_sz / f_size * 100), 1) if f_size > 0 else 0.0
                    sub_act, sub_badge, sub_rec = classify_item_safety(sub_p, "Pasta")
                    can_del = is_safe_path_to_clean(sub_p) and sub_act != SafetyClassification.DO_NOT_DELETE.value
                    sub_occupants.append({
                        "name": os.path.basename(sub_p.rstrip("\\/")) or sub_p,
                        "path": sub_p,
                        "size": sub_sz,
                        "size_formatted": format_bytes(sub_sz),
                        "percent_of_parent": pct,
                        "safety_action": sub_act,
                        "safety_badge": sub_badge,
                        "safety_recommendation": sub_rec,
                        "can_delete": can_del,
                    })

            raw_occupants.append(
                OccupantItem(
                    name=os.path.basename(f_path.rstrip("\\/")) or f_path,
                    path=f_path,
                    size=f_size,
                    size_formatted=format_bytes(f_size),
                    drive=_extract_drive_label(f_path, os_platform),
                    item_type="Pasta",
                    safety_action=act_label,
                    safety_badge=badge_cls,
                    safety_recommendation=rec,
                    sub_occupants=sub_occupants,
                )
            )

        for fsize, fpath, fname, drv in sorted(largest_files_heap, key=lambda x: x[0], reverse=True)[:top_n]:
            act_label, badge_cls, rec = classify_item_safety(fpath, "Arquivo")
            raw_occupants.append(
                OccupantItem(
                    name=fname,
                    path=fpath,
                    size=fsize,
                    size_formatted=format_bytes(fsize),
                    drive=drv,
                    item_type="Arquivo",
                    safety_action=act_label,
                    safety_badge=badge_cls,
                    safety_recommendation=rec,
                )
            )

        raw_occupants.sort(key=lambda o: o.size, reverse=True)
        return raw_occupants[:top_n], clean_suggestions, installed_apps

    def build_storage_xray(
        self,
        os_platform: OSPlatform,
        partitions: List[PartitionInfo],
        hardware_health: Optional[HardwareHealthInfo] = None,
    ) -> StorageXRayReport:
        """
        Decompõe o armazenamento do sistema nas 8 categorias auditáveis (RF-18 / ADR-011):
        - 3 categorias de Documentos & Pasta Pessoal (~ fora de ~/Library):
          1. doc_visible_projects: Pastas Visíveis & Projetos
          2. doc_hidden_dotfiles: Pastas Ocultas na Raiz (~/.* - "Espaço Fantasma")
          3. doc_rebuildable_artifacts: Artefatos Reconstruíveis de Projetos (node_modules, .venv, etc.)
        - 5 categorias de Dados do Sistema (System Data):
          4. sys_containers_vms: Containers Sandboxed, VMs & Imagens de Disco
          5. sys_app_support: Application Support & Bancos de Estado
          6. sys_caches_darwin: Caches de Usuário & Subsistema Darwin
          7. sys_dev_toolchains_pkgs: Toolchains, SDKs, Simuladores & Package Stores
          8. sys_vm_snapshots_ai: Swap/Memória Virtual, Snapshots APFS, Purgável & Modelos de IA
        """
        user_home = os.path.expanduser("~")
        darwin_cache_dir = get_darwin_user_dir("DARWIN_USER_CACHE_DIR") if os_platform == OSPlatform.MACOS else ""

        def _dir_info(p: str, max_files: int = 3500) -> Optional[Dict[str, Any]]:
            if not p or not os.path.exists(p):
                return None
            try:
                sz = _fast_dir_size(p, max_files=max_files)
                if sz <= 0:
                    return None
                act, badge, _ = classify_item_safety(p, "Pasta")
                can_del = is_safe_path_to_clean(p) and act != SafetyClassification.DO_NOT_DELETE.value
                return {
                    "name": os.path.basename(p.rstrip("/\\")) or p,
                    "path": p,
                    "size": sz,
                    "size_formatted": format_bytes(sz),
                    "safety_action": act,
                    "safety_badge": badge,
                    "can_delete": can_del,
                }
            except Exception:
                return None

        # 1. doc_visible_projects: Pastas Visíveis na Raiz de ~
        cat1_items: List[Dict[str, Any]] = []
        if os.path.exists(user_home):
            try:
                with os.scandir(user_home) as it:
                    for entry in it:
                        if entry.name.startswith(".") or entry.name in ("Library", "Applications", ".Trash"):
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            info = _dir_info(entry.path)
                            if info and info["size"] > 0:
                                cat1_items.append(info)
            except Exception:
                pass
        cat1_items.sort(key=lambda x: x["size"], reverse=True)
        cat1_total = sum(i["size"] for i in cat1_items)
        cat1 = StorageCategoryBreakdown(
            category_id="doc_visible_projects",
            title="Projetos & Pastas Visíveis do Usuário (~/Documents, ~/IdeaProjects, etc.)",
            os_equivalent="Documentos (macOS Storage)",
            total_bytes=cat1_total,
            total_formatted=format_bytes(cat1_total),
            description="Pastas de trabalho, projetos de desenvolvimento e arquivos pessoais mantidos na raiz da pasta do usuário.",
            why_os_hides_it="O macOS agrega todas as pastas de projetos de desenvolvimento nesta categoria geral sem destrinchar linguagens ou árvores de código.",
            top_items=cat1_items[:15],
        )

        # 2. doc_hidden_dotfiles: Pastas Ocultas na Raiz (~/.*)
        cat2_items: List[Dict[str, Any]] = []
        if os.path.exists(user_home):
            try:
                with os.scandir(user_home) as it:
                    for entry in it:
                        if not entry.name.startswith(".") or entry.name == ".Trash":
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            info = _dir_info(entry.path)
                            if info and info["size"] > 0:
                                cat2_items.append(info)
            except Exception:
                pass
        cat2_items.sort(key=lambda x: x["size"], reverse=True)
        cat2_total = sum(i["size"] for i in cat2_items)
        cat2 = StorageCategoryBreakdown(
            category_id="doc_hidden_dotfiles",
            title="Pastas Ocultas na Raiz do Usuário (~/.* — Espaço Fantasma de Documentos)",
            os_equivalent="Documentos (macOS Storage)",
            total_bytes=cat2_total,
            total_formatted=format_bytes(cat2_total),
            description="Diretórios ocultos de ferramentas de desenvolvimento, caches de CLI e configurações globais na raiz da Home.",
            why_os_hides_it="O Ajustes do Sistema do macOS soma estas pastas ocultas dentro da categoria 'Documentos' (seus 18,67 GB), mas o Finder e o navegador de armazenamento da Apple as escondem por começarem com ponto (.).",
            top_items=cat2_items[:15],
        )

        # 3. doc_rebuildable_artifacts: node_modules, .venv, target, build
        cat3_items: List[Dict[str, Any]] = []
        project_roots = [
            i["path"] for i in cat1_items
            if any(k in i["name"].lower() for k in ("project", "idea", "developer", "workspace", "code", "dev", "document"))
        ]
        if not project_roots and os.path.exists(user_home):
            project_roots = [
                os.path.join(user_home, "IdeaProjects"),
                os.path.join(user_home, "Documents"),
                os.path.join(user_home, "Projects"),
            ]

        for root in project_roots:
            if not os.path.exists(root) or not os.path.isdir(root):
                continue
            try:
                with os.scandir(root) as it_p:
                    for proj_entry in it_p:
                        if not proj_entry.is_dir(follow_symlinks=False) or proj_entry.name.startswith("."):
                            continue
                        try:
                            with os.scandir(proj_entry.path) as it_sub:
                                for sub in it_sub:
                                    if sub.is_dir(follow_symlinks=False) and sub.name.lower() in REBUILDABLE_PROJECT_ARTIFACTS:
                                        info = _dir_info(sub.path, max_files=4000)
                                        if info and info["size"] > 0:
                                            info["name"] = f"{proj_entry.name}/{sub.name}"
                                            cat3_items.append(info)
                        except Exception:
                            continue
            except Exception:
                continue

        cat3_items.sort(key=lambda x: x["size"], reverse=True)
        cat3_total = sum(i["size"] for i in cat3_items)
        cat3 = StorageCategoryBreakdown(
            category_id="doc_rebuildable_artifacts",
            title="Artefatos Reconstruíveis de Projetos (node_modules, .venv, target, build)",
            os_equivalent="Documentos (macOS Storage)",
            total_bytes=cat3_total,
            total_formatted=format_bytes(cat3_total),
            description="Pastas de dependências e compilação de código fonte que podem ser excluídas e reconstruídas sob demanda via npm, pip, cargo ou gradle.",
            why_os_hides_it="O sistema operacional não diferencia arquivos de código-fonte de dependências geradas automaticamente.",
            top_items=cat3_items[:15],
        )

        # 4. sys_containers_vms: Containers Sandboxed, VMs & Imagens
        cat4_items: List[Dict[str, Any]] = []
        container_bases = [
            os.path.join(user_home, "Library", "Containers"),
            os.path.join(user_home, "Library", "Group Containers"),
            os.path.join(user_home, ".orbstack"),
            os.path.join(user_home, ".docker"),
            os.path.join(user_home, ".colima"),
        ]
        for base in container_bases:
            if not os.path.exists(base) or not os.path.isdir(base):
                continue
            if base.endswith("Containers"):
                try:
                    with os.scandir(base) as it:
                        for entry in it:
                            if entry.is_dir(follow_symlinks=False):
                                info = _dir_info(entry.path, max_files=2000)
                                if info and info["size"] > 1024 * 1024:
                                    cat4_items.append(info)
                except Exception:
                    pass
            else:
                info = _dir_info(base, max_files=2000)
                if info and info["size"] > 1024 * 1024:
                    cat4_items.append(info)

        cat4_items.sort(key=lambda x: x["size"], reverse=True)
        cat4_total = sum(i["size"] for i in cat4_items)
        cat4 = StorageCategoryBreakdown(
            category_id="sys_containers_vms",
            title="Containers Sandboxed, Docker, OrbStack & VMs",
            os_equivalent="Dados do Sistema / System Data",
            total_bytes=cat4_total,
            total_formatted=format_bytes(cat4_total),
            description="Ambientes isolados da Apple Sandbox (WhatsApp, Slack, Telegram, Final Cut) e imagens virtuais de containers.",
            why_os_hides_it="O macOS cataloga o espaço interno de containers sandboxed como Dados do Sistema para proteger a integridade do sandbox.",
            top_items=cat4_items[:15],
        )

        # 5. sys_app_support: Application Support & Bancos de Estado
        cat5_items: List[Dict[str, Any]] = []
        app_support = os.path.join(user_home, "Library", "Application Support")
        if os.path.exists(app_support) and os.path.isdir(app_support):
            try:
                with os.scandir(app_support) as it:
                    for entry in it:
                        if entry.is_dir(follow_symlinks=False):
                            info = _dir_info(entry.path, max_files=2500)
                            if info and info["size"] > 1024 * 1024:
                                cat5_items.append(info)
            except Exception:
                pass
        cat5_items.sort(key=lambda x: x["size"], reverse=True)
        cat5_total = sum(i["size"] for i in cat5_items)
        cat5 = StorageCategoryBreakdown(
            category_id="sys_app_support",
            title="Application Support, IDEs & Bancos de Estado",
            os_equivalent="Dados do Sistema / System Data",
            total_bytes=cat5_total,
            total_formatted=format_bytes(cat5_total),
            description="Bancos de dados locais, índices de IDEs, backups locais de iOS e dados persistentes de aplicativos instalados.",
            why_os_hides_it="São dados persistentes essenciais para o estado dos aplicativos e não são expostos pelo gerenciador padrão de arquivos.",
            top_items=cat5_items[:15],
        )

        # 6. sys_caches_darwin: Caches de Usuário, Logs & Darwin
        cat6_items: List[Dict[str, Any]] = []
        cache_bases = [
            os.path.join(user_home, "Library", "Caches"),
            os.path.join(user_home, "Library", "Logs"),
        ]
        if darwin_cache_dir and os.path.exists(darwin_cache_dir):
            cache_bases.append(darwin_cache_dir)

        for base in cache_bases:
            if not os.path.exists(base) or not os.path.isdir(base):
                continue
            try:
                with os.scandir(base) as it:
                    for entry in it:
                        if entry.is_dir(follow_symlinks=False):
                            info = _dir_info(entry.path, max_files=2000)
                            if info and info["size"] > 1024 * 1024:
                                cat6_items.append(info)
            except Exception:
                pass
        cat6_items.sort(key=lambda x: x["size"], reverse=True)
        cat6_total = sum(i["size"] for i in cat6_items)
        cat6 = StorageCategoryBreakdown(
            category_id="sys_caches_darwin",
            title="Caches de Usuário, Logs & Subsistema Darwin",
            os_equivalent="Dados do Sistema / System Data",
            total_bytes=cat6_total,
            total_formatted=format_bytes(cat6_total),
            description="Caches de aplicativos de terceiros, logs de sistema, Metal shaders, previews de QuickLook e compilação LLVM/Clang.",
            why_os_hides_it="Arquivos transitórios criados pelos frameworks do macOS para acelerar renderização e abertura de apps.",
            top_items=cat6_items[:15],
        )

        # 7. sys_dev_toolchains_pkgs: SDKs, Simuladores & Homebrew
        cat7_items: List[Dict[str, Any]] = []
        dev_bases = [
            os.path.join(user_home, "Library", "Developer"),
            "/Library/Developer",
            "/opt/homebrew",
            "/usr/local",
            os.path.join(user_home, "Library", "pnpm"),
            os.path.join(user_home, "Library", "Android"),
        ]
        for base in dev_bases:
            if not os.path.exists(base):
                continue
            if os.path.isdir(base):
                try:
                    with os.scandir(base) as it:
                        for entry in it:
                            if entry.is_dir(follow_symlinks=False):
                                info = _dir_info(entry.path, max_files=2500)
                                if info and info["size"] > 1024 * 1024:
                                    cat7_items.append(info)
                except Exception:
                    info = _dir_info(base, max_files=2500)
                    if info:
                        cat7_items.append(info)

        cat7_items.sort(key=lambda x: x["size"], reverse=True)
        cat7_total = sum(i["size"] for i in cat7_items)
        cat7 = StorageCategoryBreakdown(
            category_id="sys_dev_toolchains_pkgs",
            title="SDKs, Simuladores, Homebrew & Stores de Pacotes",
            os_equivalent="Dados do Sistema / System Data",
            total_bytes=cat7_total,
            total_formatted=format_bytes(cat7_total),
            description="Compiladores, runtimes de simuladores do iOS, binários instalados via Homebrew e caches de pacotes.",
            why_os_hides_it="Ferramentas instaladas fora dos diretórios de aplicativos tradicionais não são categorizadas como 'Aplicativos' pelo macOS.",
            top_items=cat7_items[:15],
        )

        # 8. sys_vm_snapshots_ai: Swap, Snapshots APFS, Purgável & IA
        cat8_items: List[Dict[str, Any]] = []
        vm_bases = [
            "/private/var/vm",
            os.path.join(user_home, ".ollama"),
            os.path.join(user_home, ".lmstudio"),
            os.path.join(user_home, ".cache", "huggingface"),
        ]
        for base in vm_bases:
            if not os.path.exists(base):
                continue
            info = _dir_info(base, max_files=2000)
            if info:
                cat8_items.append(info)

        if hardware_health and hardware_health.disks:
            for d in hardware_health.disks:
                if d.purgeable_bytes and d.purgeable_bytes > 0:
                    cat8_items.append({
                        "name": f"Espaço Purgável do APFS ({d.name})",
                        "path": d.device_id,
                        "size": d.purgeable_bytes,
                        "size_formatted": format_bytes(d.purgeable_bytes),
                        "safety_action": "✅ Limpeza Automática do SO",
                        "safety_badge": "info",
                        "can_delete": False,
                    })

        cat8_items.sort(key=lambda x: x["size"], reverse=True)
        cat8_total = sum(i["size"] for i in cat8_items)
        cat8 = StorageCategoryBreakdown(
            category_id="sys_vm_snapshots_ai",
            title="Memória Virtual/Swap, Snapshots APFS, Purgável & Modelos Locais de IA",
            os_equivalent="Dados do Sistema / System Data",
            total_bytes=cat8_total,
            total_formatted=format_bytes(cat8_total),
            description="Arquivo de swap de RAM no SSD, espaço purgado pelo sistema de arquivos APFS e pesos de redes neurais locais.",
            why_os_hides_it="O macOS gerencia blocos APFS Copy-On-Write e swap de memória diretamente pelo kernel Darwin sem interface de usuário.",
            top_items=cat8_items[:15],
        )

        documents_visible = cat1_total
        documents_hidden = cat2_total
        documents_rebuildable = cat3_total
        documents_total = documents_visible + documents_hidden
        system_data_tracked = sum(c.total_bytes for c in [cat4, cat5, cat6, cat7, cat8])

        return StorageXRayReport(
            documents_total_bytes=documents_total,
            documents_visible_bytes=documents_visible,
            documents_hidden_dotfiles_bytes=documents_hidden,
            documents_rebuildable_artifacts_bytes=documents_rebuildable,
            system_data_tracked_bytes=system_data_tracked,
            categories=[cat1, cat2, cat3, cat4, cat5, cat6, cat7, cat8],
        )

    def inspect_directory(
        self,
        dir_path: str,
        os_platform: OSPlatform,
        max_items: int = 30,
    ) -> Dict[str, Any]:
        """Inspeciona os nós filhos de um diretório sob demanda ordenados por tamanho físico (RF-19 / ADR-011)."""
        if not dir_path or not isinstance(dir_path, str):
            raise ValueError("Caminho inválido fornecido.")
        if "\x00" in dir_path:
            raise ValueError("Null bytes não permitidos.")
        norm_path = dir_path.replace("\\", "/")
        parts = [p for p in norm_path.split("/") if p]
        if ".." in parts:
            raise ValueError("Tentativa de path traversal bloqueada.")

        expanded = os.path.expanduser(dir_path)
        if not os.path.exists(expanded):
            raise FileNotFoundError(f"Diretório não encontrado: {dir_path}")
        if not os.path.isdir(expanded):
            raise ValueError(f"O caminho não é um diretório: {dir_path}")

        nodes: List[DirectoryInspectionNode] = []
        raw_items: List[Tuple[str, str, int, bool, int]] = []

        try:
            with os.scandir(expanded) as it:
                for entry in it:
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            sz = _fast_dir_size(entry.path, max_files=12000)
                            children_cnt = 0
                            try:
                                children_cnt = len(os.listdir(entry.path))
                            except Exception:
                                pass
                            raw_items.append((entry.name, entry.path, sz, True, children_cnt))
                        elif entry.is_file(follow_symlinks=False):
                            st = entry.stat(follow_symlinks=False)
                            sz = _effective_file_size(st)
                            raw_items.append((entry.name, entry.path, sz, False, 0))
                    except (PermissionError, FileNotFoundError, OSError):
                        continue
        except (PermissionError, OSError) as e:
            raise PermissionError(f"Sem permissão para ler o diretório {dir_path}: {e}")

        raw_items.sort(key=lambda x: x[2], reverse=True)
        total_dir_bytes = sum(item[2] for item in raw_items)

        for name, path, sz, is_dir, child_cnt in raw_items[:max_items]:
            item_type = "Pasta" if is_dir else "Arquivo"
            pct = round((sz / total_dir_bytes * 100), 1) if total_dir_bytes > 0 else 0.0
            act_label, badge_cls, rec = classify_item_safety(path, item_type)
            can_del = is_safe_path_to_clean(path) and act_label != SafetyClassification.DO_NOT_DELETE.value
            nodes.append(
                DirectoryInspectionNode(
                    name=name,
                    path=path,
                    size=sz,
                    size_formatted=format_bytes(sz),
                    percent_of_parent=pct,
                    item_type=item_type,
                    is_hidden=name.startswith("."),
                    safety_action=act_label,
                    safety_badge=badge_cls,
                    safety_recommendation=rec,
                    can_delete=can_del,
                    children_count=child_cnt,
                )
            )

        parent_p = str(Path(expanded).parent) if str(Path(expanded).parent) != expanded else None

        return {
            "current_path": expanded,
            "parent_path": parent_p,
            "name": os.path.basename(expanded.rstrip("/\\")) or expanded,
            "total_bytes": total_dir_bytes,
            "total_formatted": format_bytes(total_dir_bytes),
            "items_count": len(raw_items),
            "items": [n.to_dict() for n in nodes],
        }
