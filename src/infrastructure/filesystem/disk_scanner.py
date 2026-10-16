# -*- coding: utf-8 -*-
"""Scanner Profundo Multiplataforma (Windows & macOS) com os.scandir e 5 Camadas Anti-Falsos Positivos."""
import os
import plistlib
import heapq
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple
from src.domain.entities import (
    PartitionInfo,
    OccupantItem,
    CleanableItem,
    InstalledAppInfo,
)
from src.domain.ports import IDiskScannerPort
from src.domain.value_objects import OSPlatform, SafetyClassification, format_bytes


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
    "cloudstorage",
    "mobile documents",
    "keychains",
    "webkit",
    "caches",
    "system",
    "program files",
    "program files (x86)",
    "programdata",
    "common files",
    "windows defender",
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


def _fast_dir_size(dir_path: str, max_files: int = 3000) -> int:
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
                            total += entry.stat(follow_symlinks=False).st_size
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

    def __init__(self, min_orphan_bytes: int = 1024 * 1024) -> None:
        # 1 MB padrão para órfãos (permite achar pastas órfãs reais sem ruído de pastas vazias)
        self.min_orphan_bytes = min_orphan_bytes

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
            while queue and visited_dirs < 2500:
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

                # Se for um bundle .app ou node_modules/.git, mede de forma agregada rápida sem explodir a árvore
                if dir_base.endswith(".app") or dir_base in {"node_modules", ".git"}:
                    agg_size = _fast_dir_size(current_dir)
                    if agg_size > 0:
                        folder_sizes[current_dir] = folder_sizes.get(current_dir, 0) + agg_size
                        path_obj = Path(current_dir)
                        for parent in path_obj.parents:
                            p_str = str(parent)
                            if p_str.startswith(base_target):
                                folder_sizes[p_str] = folder_sizes.get(p_str, 0) + agg_size
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
                                    fsize = entry.stat(follow_symlinks=False).st_size
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

            # 4. Caches de Dev Tools
            if any(
                k in norm_l
                for k in ("pip/cache", "npm-cache", "yarn/cache", ".gradle/caches", ".nuget/packages", "deriveddata")
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
                        reason="Cache de pacotes ou artefatos de compilação reconstruíveis.",
                        how_to_fix="Pode ser limpo com segurança.",
                        is_orphan=False,
                    )
                )
                continue

            # 5. Verificação de Pastas Órfãs (5 Camadas) em AppData (Windows) e ~/Library (macOS)
            parent_dir = os.path.dirname(f_path.rstrip("\\/")).replace("\\", "/").lower()
            is_direct_orphan_container = any(
                parent_dir.endswith(container_suffix)
                for container_suffix in (
                    "/appdata/local",
                    "/appdata/roaming",
                    "/appdata/locallow",
                    "/library/application support",
                    "/library/containers",
                    "/library/saved application state",
                    "/library/caches",
                    "/library/preferences",
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
            for sub_p, sub_sz in direct_children[:5]:
                if sub_sz > 512 * 1024:  # Maior que 512 KB
                    pct = round((sub_sz / f_size * 100), 1) if f_size > 0 else 0.0
                    sub_occupants.append({
                        "name": os.path.basename(sub_p.rstrip("\\/")) or sub_p,
                        "path": sub_p,
                        "size": sub_sz,
                        "size_formatted": format_bytes(sub_sz),
                        "percent_of_parent": pct,
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
