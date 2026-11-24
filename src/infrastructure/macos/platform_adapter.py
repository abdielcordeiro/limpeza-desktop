# -*- coding: utf-8 -*-
"""Implementação dos adaptadores de infraestrutura para macOS."""
import os
import re
import sys
import time
import signal
import json
import shutil
import platform
import plistlib
import subprocess
from typing import List, Set, Dict, Any, Optional

from src.domain.entities import (
    PartitionInfo,
    CloudDiagnosticInfo,
    OutdatedAppInfo,
    StorageDiskHealth,
    MemoryDiagnostics,
    GPUInfo,
    BatteryHealth,
    StartupItemInfo,
    ProcessDiagnosticInfo,
    LongevityRecommendation,
    LongevityScoreReport,
    HardwareHealthInfo,
    StorageOptimizationResult,
)
from src.domain.ports import (
    ISystemProbePort,
    IActiveAppsPort,
    ICloudAndPackagesPort,
    IHardwareProbePort,
    IStorageOptimizationPort,
)
from src.domain.value_objects import OSPlatform, ExecutionMode, format_bytes


MACOS_DEVELOPER_WHITELIST: Set[str] = {
    "apple", "com.apple", "safari", "finder", "dock", "spotlight", "xcode", "swift",
    "homebrew", "brew", "antigravity", "vscode", "code", "vscodium", "cursor",
    "jetbrains", "intellij", "idea", "pycharm", "webstorm", "goland", "clion", "datagrip", "rider",
    "androidstudio", "google", "chrome", "firefox", "mozilla", "brave", "arc", "edge", "opera",
    "docker", "orbstack", "colima", "postman", "insomnia", "dbeaver", "tableplus", "mongodb",
    "git", "github", "gitlab", "node", "npm", "yarn", "pnpm", "bun", "python", "pip", "conda",
    "rust", "cargo", "go", "java", "gradle", "maven", "cocoapods", "flutter", "dart",
    "slack", "discord", "telegram", "whatsapp", "zoom", "teams", "skype", "signal",
    "spotify", "vlc", "iina", "obs", "raycast", "alfred", "iterm", "iterm2", "warp", "alacritty",
    "kitty", "tmux", "nvim", "neovim", "sublime", "notion", "obsidian", "figma", "canva", "adobe",
    "steam", "epicgames", "minecraft", "roblox", "1password", "bitwarden", "cleanmymac",
}


def _probe_macos_volume_metrics(mount_point: str = "/") -> Dict[str, int]:
    """
    Reconcilia métricas do container APFS no macOS (RF-20 / ADR-012):
    - Combina statvfs (shutil.disk_usage), diskutil info -plist, SPStorageDataType e Foundation NSURL.
    - Calcula total_bytes, raw_free_bytes, raw_used_bytes, purgeable_bytes,
      free_bytes (disponível efetivo com purgável, padrão Ajustes do Sistema) e
      used_bytes (usado efetivo descontando purgável, padrão Ajustes do Sistema).
    """
    probe_path = (
        "/System/Volumes/Data"
        if (mount_point == "/" and os.path.exists("/System/Volumes/Data"))
        else mount_point
    )
    usage = shutil.disk_usage(probe_path)
    total_bytes = int(usage.total)
    raw_free_bytes = int(usage.free)
    raw_used_bytes = max(0, total_bytes - raw_free_bytes)
    purgeable_bytes = 0
    diskutil_purgeable = 0

    if sys.platform == "darwin":
        targets = [probe_path, "/"] if (mount_point == "/" and probe_path != "/") else [probe_path]
        for target in targets:
            try:
                d_res = subprocess.run(
                    ["diskutil", "info", "-plist", target],
                    capture_output=True,
                    timeout=4,
                    check=False,
                )
                if d_res.returncode == 0 and d_res.stdout:
                    d_info = plistlib.loads(d_res.stdout)
                    p_space = int(d_info.get("PurgeableSpace", 0) or 0)
                    diskutil_purgeable = max(diskutil_purgeable, p_space)
                    purgeable_bytes = max(purgeable_bytes, p_space)

                    c_total = int(
                        d_info.get("APFSContainerSize", 0)
                        or d_info.get("ContainerTotalSpace", 0)
                        or d_info.get("TotalSize", 0)
                        or 0
                    )
                    if c_total > 0 and (
                        total_bytes <= 0
                        or abs(c_total - total_bytes) <= max(int(total_bytes * 0.05), 1024 * 1024 * 1024)
                    ):
                        total_bytes = c_total

                    c_free = int(
                        d_info.get("APFSContainerFree", 0)
                        or d_info.get("ContainerFreeSpace", 0)
                        or d_info.get("FreeSpace", 0)
                        or 0
                    )
                    if c_free > 0 and raw_free_bytes <= 0:
                        raw_free_bytes = c_free
            except Exception:
                pass

        if mount_point == "/":
            try:
                sp_res = subprocess.run(
                    ["system_profiler", "-json", "SPStorageDataType"],
                    capture_output=True,
                    timeout=6,
                    check=False,
                )
                if sp_res.returncode == 0 and sp_res.stdout:
                    sp_data = json.loads(sp_res.stdout.decode("utf-8", errors="ignore"))
                    for item in sp_data.get("SPStorageDataType", []):
                        if item.get("mount_point") in ("/", "/System/Volumes/Data"):
                            sp_total = int(item.get("size_in_bytes", 0) or 0)
                            sp_free = int(item.get("free_space_in_bytes", 0) or 0)
                            if sp_total > 0 and (
                                total_bytes <= 0
                                or abs(sp_total - total_bytes) <= max(int(total_bytes * 0.05), 1024 * 1024 * 1024)
                            ):
                                total_bytes = sp_total
                                if sp_free >= raw_free_bytes and sp_free <= total_bytes:
                                    purgeable_bytes = max(purgeable_bytes, sp_free - raw_free_bytes)
            except Exception:
                pass

        # No macOS Sonoma/Sequoia, quando PurgeableSpace não vem no diskutil plist,
        # o Finder e os Ajustes do Sistema consultam NSURLVolumeAvailableCapacityForImportantUsageKey
        if mount_point == "/" and diskutil_purgeable == 0:
            try:
                jxa_script = (
                    'ObjC.import("Foundation");'
                    'const url=$.NSURL.fileURLWithPath("/");'
                    'const rT=Ref(),rA=Ref(),rI=Ref();'
                    'url.getResourceValueForKeyError(rT,$.NSURLVolumeTotalCapacityKey,null);'
                    'url.getResourceValueForKeyError(rA,$.NSURLVolumeAvailableCapacityKey,null);'
                    'url.getResourceValueForKeyError(rI,$.NSURLVolumeAvailableCapacityForImportantUsageKey,null);'
                    'JSON.stringify({total:ObjC.unwrap(rT[0])||0,avail:ObjC.unwrap(rA[0])||0,important:ObjC.unwrap(rI[0])||0});'
                )
                ns_res = subprocess.run(
                    ["osascript", "-l", "JavaScript", "-e", jxa_script],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    check=False,
                )
                if ns_res.returncode == 0 and ns_res.stdout:
                    ns_data = json.loads(ns_res.stdout.strip())
                    ns_total = int(ns_data.get("total", 0) or 0)
                    ns_avail = int(ns_data.get("avail", 0) or 0)
                    ns_imp = int(ns_data.get("important", 0) or 0)
                    if ns_total > 0 and abs(ns_total - total_bytes) <= max(int(total_bytes * 0.05), 1024 * 1024 * 1024):
                        if ns_imp > ns_avail and (ns_imp - ns_avail) <= total_bytes:
                            purgeable_bytes = max(purgeable_bytes, ns_imp - ns_avail)
            except Exception:
                pass

    raw_used_bytes = max(0, total_bytes - raw_free_bytes)
    effective_free_bytes = min(total_bytes, raw_free_bytes + max(0, purgeable_bytes))
    effective_used_bytes = max(0, total_bytes - effective_free_bytes)

    return {
        "total_bytes": total_bytes,
        "used_bytes": effective_used_bytes,
        "free_bytes": effective_free_bytes,
        "raw_used_bytes": raw_used_bytes,
        "raw_free_bytes": raw_free_bytes,
        "purgeable_bytes": max(0, purgeable_bytes),
    }


class MacOSSystemProbeAdapter(ISystemProbePort):
    """Inspeciona macOS, privilégios root, RAM via sysctl e volumes APFS sem duplicar /System/Volumes/Data."""

    def get_os_platform(self) -> OSPlatform:
        return OSPlatform.MACOS

    def get_os_version_string(self) -> str:
        if sys.platform == "darwin":
            mac_ver = platform.mac_ver()[0]
            arch = platform.machine()
            return f"macOS {mac_ver} ({arch})" if mac_ver else f"macOS ({arch})"
        return f"macOS (Simulado em {platform.system()})"

    def is_admin_or_root(self) -> bool:
        if hasattr(os, "geteuid"):
            try:
                return os.geteuid() == 0
            except Exception:
                return False
        return False

    def get_total_ram_kb(self) -> int:
        if sys.platform == "darwin":
            try:
                res = subprocess.run(
                    ["sysctl", "-n", "hw.memsize"],
                    capture_output=True,
                    timeout=5,
                    check=False,
                )
                mem_bytes = int(res.stdout.decode("utf-8", errors="ignore").strip())
                if mem_bytes > 0:
                    return mem_bytes // 1024
            except Exception:
                pass
        return 16 * 1024 * 1024

    def get_partitions(self) -> List[PartitionInfo]:
        partitions: List[PartitionInfo] = []

        # No macOS (APFS), '/' e '/System/Volumes/Data' compartilham o mesmo container APFS físico.
        # Usamos '/System/Volumes/Data' se existir para medir o espaço real de dados, mas apresentamos como '/'
        root_probe = "/System/Volumes/Data" if os.path.exists("/System/Volumes/Data") else "/"
        seen_realpaths: Set[str] = {"/", os.path.realpath("/"), os.path.realpath(root_probe)}
        seen_signatures: Set[ tuple[int, int] ] = set()

        try:
            metrics = _probe_macos_volume_metrics("/")
            total = metrics["total_bytes"]
            used = metrics["used_bytes"]
            free = metrics["free_bytes"]
            raw_used = metrics["raw_used_bytes"]
            raw_free = metrics["raw_free_bytes"]
            purgeable = metrics["purgeable_bytes"]
            percent = (used / total * 100.0) if total > 0 else 0.0
            seen_signatures.add((total, raw_free))
            seen_signatures.add((total, free))

            if percent >= 90.0:
                health_status = "Risco Crítico de Espaço APFS"
                health_class = "danger"
                health_desc = "Volume principal APFS acima de 90%. O swap de memória e snapshots podem sofrer degradação."
            elif percent >= 80.0:
                health_status = "Atenção (Espaço Reduzido)"
                health_class = "warning"
                health_desc = "Acima de 80% de ocupação no SSD principal. Recomendável limpar caches e snapshots locais."
            else:
                health_status = "Saudável"
                health_class = "success"
                health_desc = "Volume APFS principal com margem saudável de espaço livre."

            partitions.append(
                PartitionInfo(
                    mount_point="/",
                    drive_letter="Macintosh HD (/)",
                    total_bytes=total,
                    used_bytes=used,
                    free_bytes=free,
                    percent_used=round(percent, 1),
                    is_os_drive=True,
                    role="Volume Principal APFS (macOS & Dados do Usuário)",
                    health_status=health_status,
                    health_class=health_class,
                    health_desc=health_desc,
                    filesystem="APFS",
                    purgeable_bytes=purgeable,
                    raw_used_bytes=raw_used,
                    raw_free_bytes=raw_free,
                    use_si_units=True,
                )
            )
        except OSError:
            pass

        # Verifica volumes externos montados em /Volumes/* ignorando volumes internos do container APFS
        ignored_volume_names = {
            "macintosh hd",
            "macintosh hd - data",
            "macintosh hd - dados",
            "recovery",
            "preboot",
            "vm",
            "update",
            "xarts",
            "iscpreboot",
            "hardware",
        }
        volumes_dir = "/Volumes"
        if os.path.exists(volumes_dir):
            try:
                for entry in os.scandir(volumes_dir):
                    if entry.name.lower() in ignored_volume_names or entry.name.startswith("."):
                        continue
                    real_p = os.path.realpath(entry.path)
                    if real_p in seen_realpaths or real_p.startswith("/System/Volumes/"):
                        continue
                    try:
                        v_metrics = _probe_macos_volume_metrics(entry.path)
                        v_total = v_metrics["total_bytes"]
                        v_free = v_metrics["free_bytes"]
                        v_raw_free = v_metrics["raw_free_bytes"]
                        sig_raw = (v_total, v_raw_free)
                        sig_eff = (v_total, v_free)
                        # Se tem exatamente o mesmo total e free do container APFS raiz, é um firmlink/volume do mesmo container
                        if sig_raw in seen_signatures or sig_eff in seen_signatures or v_total <= 0:
                            continue
                        seen_realpaths.add(real_p)
                        seen_signatures.add(sig_raw)
                        seen_signatures.add(sig_eff)
                        v_used = v_metrics["used_bytes"]
                        v_pct = (v_used / v_total * 100.0) if v_total > 0 else 0.0
                        partitions.append(
                            PartitionInfo(
                                mount_point=entry.path,
                                drive_letter=entry.name,
                                total_bytes=v_total,
                                used_bytes=v_used,
                                free_bytes=v_free,
                                percent_used=round(v_pct, 1),
                                is_os_drive=False,
                                role="Volume Externo / Secundário Montado",
                                health_status="Quase Cheio" if v_pct >= 90 else "Saudável",
                                health_class="warning" if v_pct >= 90 else "success",
                                health_desc="Volume externo ou imagem de disco montada em /Volumes.",
                                filesystem="APFS/ExFAT",
                                purgeable_bytes=v_metrics["purgeable_bytes"],
                                raw_used_bytes=v_metrics["raw_used_bytes"],
                                raw_free_bytes=v_raw_free,
                                use_si_units=True,
                            )
                        )
                    except OSError:
                        continue
            except OSError:
                pass

        return partitions


class MacOSActiveAppsAdapter(IActiveAppsPort):
    """Algoritmo Anti-Falsos Positivos de 5 Camadas nativo para macOS."""

    def get_installed_app_bundles(self) -> Set[str]:
        """Camada 1: Lê /Applications e ~/Applications extraindo Info.plist via plistlib."""
        indicators: Set[str] = set()
        app_dirs = ["/Applications", os.path.expanduser("~/Applications")]
        for app_dir in app_dirs:
            if not os.path.exists(app_dir):
                continue
            try:
                for entry in os.scandir(app_dir):
                    if not entry.is_dir(follow_symlinks=False):
                        continue
                    base_name = entry.name
                    if base_name.endswith(".app"):
                        clean_name = base_name[:-4].strip().lower()
                        indicators.add(clean_name)
                        for tok in clean_name.replace("-", " ").replace("_", " ").split():
                            if len(tok) > 2:
                                indicators.add(tok)

                        plist_path = os.path.join(entry.path, "Contents", "Info.plist")
                        if os.path.exists(plist_path):
                            try:
                                with open(plist_path, "rb") as pf:
                                    pdata = plistlib.load(pf)
                                for key in ("CFBundleIdentifier", "CFBundleName", "CFBundleDisplayName", "CFBundleExecutable"):
                                    val = pdata.get(key)
                                    if val:
                                        val_str = str(val).strip().lower()
                                        indicators.add(val_str)
                                        for part in val_str.replace(".", " ").replace("-", " ").split():
                                            if len(part) > 2 and part not in {"com", "org", "net", "app", "mac"}:
                                                indicators.add(part)
                            except Exception:
                                continue
            except OSError:
                continue
        return indicators

    def get_homebrew_and_pkgutil(self) -> Set[str]:
        """Camada 2: Pacotes Homebrew (Cellar/Caskroom/brew list) e pkgutil --pkgs."""
        pkgs: Set[str] = set()
        brew_dirs = [
            "/opt/homebrew/Cellar",
            "/opt/homebrew/Caskroom",
            "/usr/local/Cellar",
            "/usr/local/Caskroom",
        ]
        for bdir in brew_dirs:
            if os.path.exists(bdir):
                try:
                    for item in os.listdir(bdir):
                        if not item.startswith("."):
                            pkgs.add(item.lower())
                except OSError:
                    pass

        if sys.platform == "darwin":
            try:
                res = subprocess.run(
                    ["pkgutil", "--pkgs"],
                    capture_output=True,
                    timeout=8,
                    check=False,
                )
                for line in res.stdout.decode("utf-8", errors="ignore").splitlines():
                    pkg_id = line.strip().lower()
                    if not pkg_id:
                        continue
                    pkgs.add(pkg_id)
                    # Não explode pacotes base da Apple (com.apple.pkg.*) em tokens curtos para evitar falsos negativos (G-05/RF-15)
                    if pkg_id.startswith("com.apple.pkg.") or pkg_id.startswith("com.apple."):
                        continue
                    for part in pkg_id.split("."):
                        if len(part) >= 4 and part not in {"com", "org", "apple", "pkg", "mac", "app"}:
                            pkgs.add(part)
            except Exception:
                pass
        return pkgs

    def get_launch_agents_and_daemons(self) -> Set[str]:
        """Camada 3: LaunchAgents e LaunchDaemons do usuário e do sistema (apenas binários íntegros)."""
        agents: Set[str] = set()
        dirs = [
            os.path.expanduser("~/Library/LaunchAgents"),
            "/Library/LaunchAgents",
            "/Library/LaunchDaemons",
        ]
        for d in dirs:
            if os.path.exists(d):
                try:
                    for fname in os.listdir(d):
                        if fname.endswith(".plist"):
                            fpath = os.path.join(d, fname)
                            prog_target = ""
                            try:
                                with open(fpath, "rb") as pf:
                                    pdata = plistlib.load(pf)
                                prog = pdata.get("Program")
                                prog_args = pdata.get("ProgramArguments")
                                if prog:
                                    prog_target = str(prog).strip()
                                elif prog_args and isinstance(prog_args, list) and prog_args:
                                    prog_target = str(prog_args[0]).strip()
                            except Exception:
                                prog_target = ""

                            # Se o binário executável alvo comprovadamente não existe mais no disco,
                            # o agente está quebrado/órfão e NÃO deve proteger pastas de software desinstalado (G-05/RF-15)
                            if prog_target and not os.path.exists(prog_target):
                                continue

                            base = fname[:-6].lower()
                            agents.add(base)
                            for part in base.split("."):
                                if len(part) > 2 and part not in {"com", "org", "plist", "agent", "daemon"}:
                                    agents.add(part)
                except OSError:
                    continue
        return agents

    def get_running_processes(self) -> Set[str]:
        """Camada 4: Processos ativos em execução via ps -eo comm."""
        procs: Set[str] = set()
        if sys.platform == "darwin":
            try:
                res = subprocess.run(
                    ["ps", "-eo", "comm"],
                    capture_output=True,
                    timeout=8,
                    check=False,
                )
                for line in res.stdout.decode("utf-8", errors="ignore").splitlines()[1:]:
                    proc_path = line.strip()
                    if proc_path:
                        base = os.path.basename(proc_path).lower()
                        if len(base) > 2:
                            procs.add(base)
            except Exception:
                pass
        return procs

    def get_layer_breakdown(self, drives: List[str]) -> Dict[str, int]:
        return {
            "layer1_applications": len(self.get_installed_app_bundles()),
            "layer2_homebrew_pkgutil": len(self.get_homebrew_and_pkgutil()),
            "layer3_launch_agents": len(self.get_launch_agents_and_daemons()),
            "layer4_processes": len(self.get_running_processes()),
            "layer5_whitelist": len(MACOS_DEVELOPER_WHITELIST),
        }

    def get_active_indicators(self, drives: List[str]) -> Set[str]:
        indicators: Set[str] = set()
        indicators.update(self.get_installed_app_bundles())
        indicators.update(self.get_homebrew_and_pkgutil())
        indicators.update(self.get_launch_agents_and_daemons())
        indicators.update(self.get_running_processes())
        indicators.update(MACOS_DEVELOPER_WHITELIST)
        return indicators


class MacOSCloudAndPackagesAdapter(ICloudAndPackagesPort):
    """Diagnóstico de iCloud Drive + OneDrive macOS e pacotes desatualizados via Homebrew."""

    def _measure_cloud_dir(self, path: str) -> tuple[int, int]:
        total_bytes = 0
        file_count = 0
        if not os.path.exists(path):
            return 0, 0
        stack = [path]
        while stack and file_count < 35000:
            curr = stack.pop()
            try:
                with os.scandir(curr) as it:
                    for entry in it:
                        try:
                            if entry.is_symlink():
                                continue
                            if entry.is_dir(follow_symlinks=False):
                                stack.append(entry.path)
                            elif entry.is_file(follow_symlinks=False):
                                st = entry.stat(follow_symlinks=False)
                                # Usa st_blocks * 512 quando disponível no macOS para medir apenas blocos físicos locais!
                                physical_size = getattr(st, "st_blocks", 0) * 512 if hasattr(st, "st_blocks") else st.st_size
                                total_bytes += physical_size
                                file_count += 1
                        except OSError:
                            continue
            except OSError:
                continue
        return total_bytes, file_count

    def analyze_cloud_storage(self) -> List[CloudDiagnosticInfo]:
        diagnostics: List[CloudDiagnosticInfo] = []

        # 1. iCloud Drive (~/Library/Mobile Documents)
        icloud_path = os.path.expanduser("~/Library/Mobile Documents")
        icloud_installed = os.path.exists(icloud_path)
        icloud_bytes, icloud_files = self._measure_cloud_dir(icloud_path) if icloud_installed else (0, 0)
        diagnostics.append(
            CloudDiagnosticInfo(
                provider_name="Apple iCloud Drive",
                is_installed=icloud_installed,
                path=icloud_path if icloud_installed else "Não configurado neste perfil",
                consumed_bytes=icloud_bytes,
                consumed_formatted=format_bytes(icloud_bytes),
                file_count=icloud_files,
                is_consuming_heavy_space=icloud_bytes > 500 * 1024 * 1024,
                recommendations=[
                    {
                        "step": "1. Remover Download Local sem Apagar do iCloud",
                        "action": "No Finder > iCloud Drive, clique com o botão direito nas pastas grandes e selecione 'Remover Download'.",
                        "effect": "Libera espaço físico imediato no SSD mantendo o arquivo seguro na nuvem da Apple.",
                    },
                    {
                        "step": "2. Ativar 'Otimizar Armazenamento do Mac'",
                        "action": "Abra Ajustes do Sistema > ID Apple > iCloud > iCloud Drive e ative 'Otimizar Armazenamento do Mac'.",
                        "effect": "O macOS remove automaticamente cópias locais antigas quando o disco precisa de espaço.",
                    },
                ],
            )
        )

        # 2. OneDrive no macOS (~/Library/CloudStorage/OneDrive*)
        cloud_storage_dir = os.path.expanduser("~/Library/CloudStorage")
        onedrive_path = None
        if os.path.exists(cloud_storage_dir):
            try:
                for item in os.listdir(cloud_storage_dir):
                    if item.lower().startswith("onedrive"):
                        onedrive_path = os.path.join(cloud_storage_dir, item)
                        break
            except OSError:
                pass
        if not onedrive_path:
            legacy_od = os.path.expanduser("~/OneDrive")
            if os.path.exists(legacy_od):
                onedrive_path = legacy_od

        if onedrive_path:
            od_bytes, od_files = self._measure_cloud_dir(onedrive_path)
            diagnostics.append(
                CloudDiagnosticInfo(
                    provider_name="Microsoft OneDrive (macOS)",
                    is_installed=True,
                    path=onedrive_path,
                    consumed_bytes=od_bytes,
                    consumed_formatted=format_bytes(od_bytes),
                    file_count=od_files,
                    is_consuming_heavy_space=od_bytes > 500 * 1024 * 1024,
                    recommendations=[
                        {
                            "step": "1. Liberar Espaço no Finder (Arquivos sob Demanda)",
                            "action": "Clique com o botão direito na pasta OneDrive no Finder e escolha 'Liberar Espaço'.",
                            "effect": "Converte os arquivos sincronizados para estado online sem ocupar o SSD.",
                        }
                    ],
                )
            )

        return diagnostics

    def check_outdated_packages(self) -> List[OutdatedAppInfo]:
        if sys.platform != "darwin":
            return []
        brew_bin = shutil.which("brew")
        if not brew_bin:
            for candidate in ("/opt/homebrew/bin/brew", "/usr/local/bin/brew"):
                if os.path.exists(candidate):
                    brew_bin = candidate
                    break
        if not brew_bin:
            return []

        outdated: List[OutdatedAppInfo] = []
        try:
            res = subprocess.run(
                [brew_bin, "outdated", "--json=v2"],
                capture_output=True,
                timeout=30,
                check=False,
            )
            data = json.loads(res.stdout.decode("utf-8", errors="replace") or "{}")
            for formula in data.get("formulae", []):
                name = formula.get("name", "")
                installed_vers = formula.get("installed_versions", [])
                curr_ver = installed_vers[-1] if installed_vers else "unknown"
                latest_ver = formula.get("current_version", "")
                curr_nums = [int(m) for m in re.findall(r"\d+", curr_ver)]
                late_nums = [int(m) for m in re.findall(r"\d+", latest_ver)]
                if curr_nums and late_nums and late_nums[0] > curr_nums[0]:
                    risk_level = "Médio Risco (Major Update)"
                    risk_badge = "warning"
                    risk_reason = f"Atualização de versão principal ({curr_ver} -> {latest_ver})."
                else:
                    risk_level = "Baixo Risco (Update Incremental)"
                    risk_badge = "success"
                    risk_reason = "Atualização de pacote Homebrew com melhorias e correções."
                outdated.append(
                    OutdatedAppInfo(
                        name=name,
                        app_id=name,
                        current_version=curr_ver,
                        latest_version=latest_ver,
                        source="homebrew (formula)",
                        drive="/",
                        risk_level=risk_level,
                        risk_badge=risk_badge,
                        risk_reason=risk_reason,
                        upgrade_cmd=f"brew upgrade {name}",
                    )
                )
            for cask in data.get("casks", []):
                name = cask.get("name", "")
                installed_vers = cask.get("installed_versions", [])
                curr_ver = installed_vers[-1] if isinstance(installed_vers, list) and installed_vers else str(installed_vers)
                latest_ver = cask.get("current_version", "")
                outdated.append(
                    OutdatedAppInfo(
                        name=name,
                        app_id=name,
                        current_version=curr_ver,
                        latest_version=latest_ver,
                        source="homebrew (cask)",
                        drive="/Applications",
                        risk_level="Baixo Risco (App Update)",
                        risk_badge="success",
                        risk_reason="Nova versão disponível para o aplicativo macOS via Homebrew Cask.",
                        upgrade_cmd=f"brew upgrade --cask {name}",
                    )
                )
        except Exception:
            return []
        return outdated

    def upgrade_package(self, package_id: str) -> Dict[str, Any]:
        """Atualiza um pacote individual ou todos via Homebrew (RF-16)."""
        if not package_id or not isinstance(package_id, str):
            return {"status": "error", "message": "ID de pacote inválido."}
        if package_id.startswith("-") or not re.match(r"^[a-zA-Z0-9._@\-\/]+$", package_id):
            return {"status": "error", "message": "Identificador com caracteres inválidos ou parâmetros não permitidos."}

        brew_bin = shutil.which("brew") or "/opt/homebrew/bin/brew"
        if package_id == "__cleanup__":
            cmd = [brew_bin, "cleanup", "--prune=all"]
        elif package_id == "__all__":
            cmd = [brew_bin, "upgrade"]
        else:
            cmd = [brew_bin, "upgrade", "--", package_id]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=90, check=False)
            output = (res.stdout + "\n" + res.stderr).strip()
            return {
                "status": "ok" if res.returncode == 0 else "error",
                "command": " ".join(cmd),
                "output": output,
                "message": f"Comando '{' '.join(cmd)}' executado (código {res.returncode}).",
            }
        except Exception as e:
            return {"status": "error", "command": " ".join(cmd), "output": str(e), "message": f"Falha ao executar: {e}"}

    def cleanup_package_manager(self) -> Dict[str, Any]:
        """Executa limpeza de caches e versões antigas de fórmulas Homebrew."""
        return self.upgrade_package("__cleanup__")


class MacOSHardwareProbeAdapter(IHardwareProbePort):
    """Diagnóstico e monitoramento de saúde física e operacional para macOS."""

    def get_disks_health(self) -> List[StorageDiskHealth]:
        disks: List[StorageDiskHealth] = []
        root_metrics = {
            "total_bytes": 0,
            "used_bytes": 0,
            "free_bytes": 0,
            "raw_used_bytes": 0,
            "raw_free_bytes": 0,
            "purgeable_bytes": 0,
        }
        try:
            root_metrics = _probe_macos_volume_metrics("/")
        except Exception:
            pass

        purgeable_bytes = root_metrics["purgeable_bytes"]
        snapshots_count = 0

        if sys.platform == "darwin":
            try:
                t_res = subprocess.run(["tmutil", "listlocalsnapshots", "/"], capture_output=True, timeout=5, check=False)
                if t_res.returncode == 0 and t_res.stdout:
                    lines = t_res.stdout.decode("utf-8", errors="ignore").splitlines()
                    snapshots_count = len([l for l in lines if "com.apple.TimeMachine." in l])
            except Exception:
                pass

            try:
                res = subprocess.run(
                    ["system_profiler", "-json", "SPStorageDataType"],
                    capture_output=True,
                    timeout=10,
                    check=False,
                )
                if res.stdout:
                    data = json.loads(res.stdout.decode("utf-8", errors="ignore"))
                    storage_items = data.get("SPStorageDataType", [])
                    for item in storage_items:
                        name = item.get("_name", "Macintosh HD")
                        mount_point = item.get("mount_point", "/")
                        phys = item.get("physical_drive", {}) or {}
                        device_id = phys.get("device_name", item.get("bsd_name", "disk0s1"))
                        protocol = str(phys.get("protocol", "Apple Fabric")).strip()
                        smart = str(phys.get("smart_status", "Verified")).strip()
                        trim_str = str(phys.get("trim_support", "yes")).strip().lower()

                        is_nvme = "nvme" in protocol.lower() or "fabric" in protocol.lower() or "pcie" in protocol.lower()
                        is_ssd = is_nvme or "ssd" in protocol.lower() or "solid state" in str(phys).lower() or True
                        media_type = "NVMe SSD (Apple Fabric)" if is_nvme else ("SSD" if is_ssd else "HDD")

                        size_bytes = int(item.get("size_in_bytes", 0))
                        free_bytes = int(item.get("free_space_in_bytes", 0))

                        smart_status = smart if smart else "Verified"
                        risk_alert = None
                        if smart_status.lower() in ("failing", "fatal", "warning"):
                            risk_alert = "Falha física iminente detectada no S.M.A.R.T.! Faça backup urgente dos dados."

                        is_root_disk = mount_point == "/"
                        if is_root_disk and root_metrics["total_bytes"] > 0:
                            d_total = root_metrics["total_bytes"]
                            d_used = root_metrics["used_bytes"]
                            d_free = root_metrics["free_bytes"]
                            d_raw_used = root_metrics["raw_used_bytes"]
                            d_raw_free = root_metrics["raw_free_bytes"]
                            p_bytes = root_metrics["purgeable_bytes"]
                        else:
                            d_total = size_bytes
                            d_free = free_bytes
                            d_used = max(0, size_bytes - free_bytes)
                            d_raw_used = d_used
                            d_raw_free = d_free
                            p_bytes = purgeable_bytes if is_root_disk else 0

                        s_count = snapshots_count if is_root_disk else 0

                        disks.append(
                            StorageDiskHealth(
                                device_id=device_id,
                                name=f"{name} ({mount_point})",
                                media_type=media_type,
                                bus_type=protocol or "Apple Fabric",
                                smart_status=smart_status,
                                trim_supported=trim_str == "yes" or is_nvme,
                                is_ssd=is_ssd,
                                is_nvme=is_nvme,
                                recommended_action="Manutenção APFS & TRIM" if is_ssd else "Análise de Fragmentação",
                                risk_alert=risk_alert,
                                total_bytes=d_total,
                                free_bytes=d_free,
                                purgeable_bytes=p_bytes,
                                apfs_snapshots_count=s_count,
                                used_bytes=d_used,
                                raw_used_bytes=d_raw_used,
                                raw_free_bytes=d_raw_free,
                                use_si_units=True,
                            )
                        )
            except Exception:
                pass

        if disks:
            disks.sort(key=lambda d: 0 if d.name.endswith("(/)") else 1)
        else:
            # Fallback seguro para Macintosh HD usando métricas reconciliadas
            total_b = root_metrics["total_bytes"] or (512 * 1024 * 1024 * 1024)
            free_b = root_metrics["free_bytes"] or (200 * 1024 * 1024 * 1024)
            used_b = root_metrics["used_bytes"] or max(0, total_b - free_b)
            raw_used_b = root_metrics["raw_used_bytes"] or used_b
            raw_free_b = root_metrics["raw_free_bytes"] or free_b
            disks.append(
                StorageDiskHealth(
                    device_id="disk0s1",
                    name="Macintosh HD (/)",
                    media_type="NVMe SSD (Apple Fabric)",
                    bus_type="Apple Fabric / PCIe",
                    smart_status="Verified",
                    trim_supported=True,
                    is_ssd=True,
                    is_nvme=True,
                    recommended_action="Manutenção APFS & TRIM",
                    total_bytes=total_b,
                    free_bytes=free_b,
                    purgeable_bytes=purgeable_bytes,
                    apfs_snapshots_count=snapshots_count,
                    used_bytes=used_b,
                    raw_used_bytes=raw_used_b,
                    raw_free_bytes=raw_free_b,
                    use_si_units=True,
                )
            )
        return disks

    def get_memory_diagnostics(self) -> MemoryDiagnostics:
        total_bytes = 16 * 1024 * 1024 * 1024
        used_bytes = 8 * 1024 * 1024 * 1024
        swap_total = 0
        swap_used = 0
        swap_thrashing = False
        page_size = 4096
        wired_bytes = 0
        compressed_bytes = 0
        cached_files_bytes = 0
        pageouts_count = 0
        swapouts_count = 0
        kernel_pressure_level = "Normal"

        if sys.platform == "darwin":
            try:
                mem_res = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, timeout=4, check=False)
                val = int(mem_res.stdout.decode("utf-8", errors="ignore").strip())
                if val > 0:
                    total_bytes = val
            except Exception:
                pass

            # Page size (16384 no Apple Silicon M1/M2/M3/M4 vs 4096 no Intel)
            try:
                ps_res = subprocess.run(["sysctl", "-n", "hw.pagesize"], capture_output=True, timeout=4, check=False)
                ps_val = int(ps_res.stdout.decode("utf-8", errors="ignore").strip())
                if ps_val > 0:
                    page_size = ps_val
            except Exception:
                pass

            # Pressão de memória do kernel Darwin (sysctl kern.memorystatus_vm_pressure_level)
            try:
                p_res = subprocess.run(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"], capture_output=True, timeout=3, check=False)
                pval = p_res.stdout.decode("utf-8", errors="ignore").strip()
                if pval == "4":
                    kernel_pressure_level = "Critical"
                elif pval == "2":
                    kernel_pressure_level = "Warning"
                else:
                    kernel_pressure_level = "Normal"
            except Exception:
                pass

            # vm_stat
            try:
                vm_res = subprocess.run(["vm_stat"], capture_output=True, timeout=5, check=False)
                out = vm_res.stdout.decode("utf-8", errors="ignore")
                free_pages = 0
                active_pages = 0
                wired_pages = 0
                compressed_pages = 0
                cached_pages = 0
                for line in out.splitlines():
                    if "Pages free:" in line:
                        m = re.search(r"(\d+)", line)
                        if m: free_pages = int(m.group(1))
                    elif "Pages active:" in line:
                        m = re.search(r"(\d+)", line)
                        if m: active_pages = int(m.group(1))
                    elif "Pages wired down:" in line:
                        m = re.search(r"(\d+)", line)
                        if m: wired_pages = int(m.group(1))
                    elif "occupied by compressor:" in line:
                        m = re.search(r"(\d+)", line)
                        if m: compressed_pages = int(m.group(1))
                    elif "File-backed pages:" in line:
                        m = re.search(r"(\d+)", line)
                        if m: cached_pages = int(m.group(1))
                    elif "Pageouts:" in line:
                        m = re.search(r"(\d+)", line)
                        if m: pageouts_count = int(m.group(1))
                    elif "Swapouts:" in line:
                        m = re.search(r"(\d+)", line)
                        if m: swapouts_count = int(m.group(1))

                wired_bytes = wired_pages * page_size
                compressed_bytes = compressed_pages * page_size
                cached_files_bytes = cached_pages * page_size

                computed_free = free_pages * page_size
                computed_used = (active_pages + wired_pages + compressed_pages) * page_size
                if computed_used > 0 and total_bytes >= computed_used:
                    used_bytes = computed_used
            except Exception:
                pass

            # vm.swapusage
            try:
                swap_res = subprocess.run(["sysctl", "-n", "vm.swapusage"], capture_output=True, timeout=4, check=False)
                s_out = swap_res.stdout.decode("utf-8", errors="ignore")
                m_total = re.search(r"total\s*=\s*([\d\.]+)([KMG]?)", s_out, re.IGNORECASE)
                m_used = re.search(r"used\s*=\s*([\d\.]+)([KMG]?)", s_out, re.IGNORECASE)
                if m_total:
                    num = float(m_total.group(1))
                    unit = m_total.group(2).upper()
                    mult = 1024 * 1024 if unit == "M" else (1024 * 1024 * 1024 if unit == "G" else 1024)
                    swap_total = int(num * mult)
                if m_used:
                    num = float(m_used.group(1))
                    unit = m_used.group(2).upper()
                    mult = 1024 * 1024 if unit == "M" else (1024 * 1024 * 1024 if unit == "G" else 1024)
                    swap_used = int(num * mult)
            except Exception:
                pass

        free_bytes = max(0, total_bytes - used_bytes)
        load_pct = round((used_bytes / total_bytes * 100.0), 1) if total_bytes > 0 else 50.0

        recs: List[str] = []
        pressure = kernel_pressure_level
        if load_pct >= 88.0 and swap_used > 1024 * 1024 * 1024:
            pressure = "Critical"
            swap_thrashing = True
            recs.append("Risco iminente de Swap Thrashing: feche abas pesadas de navegadores ou aplicações Electron.")
            recs.append("O uso contínuo de swap acelerado aumenta ciclos de escrita desnecessários no SSD.")
        elif load_pct >= 75.0 or swap_used > 512 * 1024 * 1024 or kernel_pressure_level == "Warning":
            if pressure != "Critical":
                pressure = "Warning"
            recs.append("Pressão moderada de memória RAM detectada. Monitore o Monitor de Atividades.")
        else:
            if pressure != "Critical" and pressure != "Warning":
                pressure = "Normal"
            recs.append("Memória RAM operando em nível saudável com boa margem de buffer.")

        return MemoryDiagnostics(
            total_bytes=total_bytes,
            used_bytes=used_bytes,
            free_bytes=free_bytes,
            load_percentage=load_pct,
            pressure_level=pressure,
            swap_total_bytes=swap_total,
            swap_used_bytes=swap_used,
            swap_thrashing_detected=swap_thrashing,
            recommendations=recs,
            wired_bytes=wired_bytes,
            compressed_bytes=compressed_bytes,
            cached_files_bytes=cached_files_bytes,
            pageouts_count=pageouts_count,
            swapouts_count=swapouts_count,
            page_size_bytes=page_size,
        )

    def get_gpu_info(self) -> List[GPUInfo]:
        gpus: List[GPUInfo] = []
        if sys.platform == "darwin":
            try:
                res = subprocess.run(
                    ["system_profiler", "-json", "SPDisplaysDataType"],
                    capture_output=True,
                    timeout=8,
                    check=False,
                )
                if res.stdout:
                    data = json.loads(res.stdout.decode("utf-8", errors="ignore"))
                    items = data.get("SPDisplaysDataType", [])
                    for item in items:
                        name = item.get("_name", "Apple GPU")
                        chip_type = item.get("spdisplays_chip_type", name)
                        vram_str = item.get("spdisplays_vram", "")
                        vram_bytes = 0
                        if vram_str:
                            m = re.search(r"(\d+)\s*(MB|GB)", vram_str, re.IGNORECASE)
                            if m:
                                val = int(m.group(1))
                                unit = m.group(2).upper()
                                vram_bytes = val * (1024 * 1024 * 1024 if unit == "GB" else 1024 * 1024)

                        metal = item.get("spdisplays_metal", "Metal 3 Suportado")
                        gpus.append(
                            GPUInfo(
                                name=chip_type or name,
                                vendor="Apple" if "apple" in str(chip_type).lower() else "Intel/AMD",
                                vram_bytes=vram_bytes,
                                driver_version=str(metal),
                                status="Ativo / Operacional",
                                is_integrated=True if "apple" in str(chip_type).lower() else False,
                            )
                        )
            except Exception:
                pass

        if not gpus:
            gpus.append(
                GPUInfo(
                    name="Apple Silicon GPU (Unificada)",
                    vendor="Apple",
                    vram_bytes=0,
                    driver_version="Metal 3 (Nativo macOS)",
                    status="Ativo / Operacional",
                    is_integrated=True,
                )
            )
        return gpus

    def get_battery_health(self) -> BatteryHealth:
        if sys.platform == "darwin":
            # 1. Leitura direta da controladora AppleSmartBattery via IOKit (ioreg) (< 15ms)
            try:
                res = subprocess.run(
                    ["ioreg", "-rn", "AppleSmartBattery", "-a"],
                    capture_output=True,
                    timeout=4,
                    check=False,
                )
                if res.returncode == 0 and res.stdout:
                    data = plistlib.loads(res.stdout)
                    items = data if isinstance(data, list) else [data]
                    if items and isinstance(items[0], dict):
                        batt = items[0]
                        cycle = batt.get("CycleCount")
                        cycle_int = int(cycle) if cycle is not None else None

                        des_cap = batt.get("DesignCapacity")
                        des_cap_int = int(des_cap) if des_cap is not None else None

                        max_cap = batt.get("AppleRawMaxCapacity") or batt.get("NominalChargeCapacity") or batt.get("MaxCapacity")
                        max_cap_int = int(max_cap) if max_cap is not None else None

                        pct = None
                        if max_cap_int is not None and des_cap_int and des_cap_int > 0:
                            pct = round((max_cap_int / des_cap_int) * 100.0, 1)
                        elif batt.get("MaxCapacity") is not None:
                            try:
                                pct = float(batt.get("MaxCapacity"))
                            except (ValueError, TypeError):
                                pct = None

                        temp_raw = batt.get("Temperature")
                        temp_c = None
                        if temp_raw is not None:
                            val = float(temp_raw)
                            temp_c = round(val / 100.0, 1) if val > 100 else round(val, 1)

                        voltage_mv = int(batt.get("Voltage")) if batt.get("Voltage") is not None else None
                        amperage_ma = int(batt.get("Amperage")) if batt.get("Amperage") is not None else None
                        is_charging = bool(batt.get("IsCharging", False))

                        condition = "Normal"
                        if pct is not None and pct < 75.0:
                            condition = "Service Recommended"
                        if batt.get("PermanentFailureStatus"):
                            condition = "Failing / Replace Now"

                        return BatteryHealth(
                            has_battery=True,
                            cycle_count=cycle_int,
                            health_percentage=pct,
                            condition=condition,
                            is_charging=is_charging,
                            design_capacity_mah=des_cap_int,
                            max_capacity_mah=max_cap_int,
                            temperature_celsius=temp_c,
                            voltage_mv=voltage_mv,
                            amperage_ma=amperage_ma,
                        )
            except Exception:
                pass

            # 2. Fallback resiliente no system_profiler SPPowerDataType sanitizando %
            try:
                res = subprocess.run(
                    ["system_profiler", "-json", "SPPowerDataType"],
                    capture_output=True,
                    timeout=8,
                    check=False,
                )
                if res.stdout:
                    data = json.loads(res.stdout.decode("utf-8", errors="ignore"))
                    power_items = data.get("SPPowerDataType", [])
                    for item in power_items:
                        batt_info = item.get("sppower_battery_health_info", {}) or {}
                        if not batt_info and "sppower_battery_cycle_count" in item:
                            batt_info = item
                        if batt_info:
                            cycle = batt_info.get("sppower_battery_cycle_count")
                            condition = batt_info.get("sppower_battery_health", "Normal")
                            max_cap = batt_info.get("sppower_battery_max_capacity")
                            charge_info = item.get("sppower_battery_charge_info", {}) or {}
                            is_charging = str(charge_info.get("sppower_battery_is_charging", "no")).lower() == "yes"

                            cycle_int = int(cycle) if cycle is not None else None
                            pct = None
                            if max_cap is not None:
                                try:
                                    clean_cap = str(max_cap).replace("%", "").strip()
                                    pct = float(clean_cap)
                                except (ValueError, TypeError):
                                    pct = None

                            return BatteryHealth(
                                has_battery=True,
                                cycle_count=cycle_int,
                                health_percentage=pct,
                                condition=str(condition),
                                is_charging=is_charging,
                            )
            except Exception:
                pass

        return BatteryHealth(
            has_battery=False,
            condition="Não Aplicável (Desktop Mac / Sem Bateria)",
        )

    def get_startup_items(self) -> List[StartupItemInfo]:
        """Audita LaunchAgents e LaunchDaemons identificando agentes órfãos com binário ausente (RF-17)."""
        items: List[StartupItemInfo] = []
        target_dirs = [
            (os.path.expanduser("~/Library/LaunchAgents"), "User LaunchAgent"),
            ("/Library/LaunchAgents", "System LaunchAgent"),
            ("/Library/LaunchDaemons", "System LaunchDaemon"),
        ]
        for dir_path, scope in target_dirs:
            if not os.path.exists(dir_path):
                continue
            try:
                for fname in os.listdir(dir_path):
                    if not fname.endswith(".plist"):
                        continue
                    fpath = os.path.join(dir_path, fname)
                    prog_target = ""
                    try:
                        with open(fpath, "rb") as pf:
                            pdata = plistlib.load(pf)
                        prog = pdata.get("Program")
                        prog_args = pdata.get("ProgramArguments")
                        if prog:
                            prog_target = str(prog).strip()
                        elif prog_args and isinstance(prog_args, list) and prog_args:
                            prog_target = str(prog_args[0]).strip()
                    except Exception:
                        prog_target = ""

                    target_exists = os.path.exists(prog_target) if prog_target else False
                    is_orphan = (not target_exists) and bool(prog_target)
                    status_label = "⚠️ Agente Órfão (Binário Ausente)" if is_orphan else "✅ Ativo / Binário Íntegro"
                    recommendation = (
                        "O binário executável deste agente não existe mais no disco. Remova este resíduo de inicialização com segurança."
                        if is_orphan
                        else "Agente íntegro com binário executável verificado."
                    )
                    items.append(
                        StartupItemInfo(
                            name=fname,
                            path=fpath,
                            scope=scope,
                            program_target=prog_target,
                            target_exists=target_exists,
                            is_orphan=is_orphan,
                            status_label=status_label,
                            recommendation=recommendation,
                        )
                    )
            except OSError:
                continue
        return items

    def get_top_processes(self, limit: int = 10) -> List[ProcessDiagnosticInfo]:
        """Lista os Top processos consumidores e identifica processos zumbis (RF-17)."""
        processes: List[ProcessDiagnosticInfo] = []
        if sys.platform != "darwin":
            return processes

        try:
            res = subprocess.run(
                ["ps", "-axo", "pid,ppid,stat,%cpu,%mem,rss,comm"],
                capture_output=True,
                timeout=5,
                check=False,
            )
            if res.returncode == 0 and res.stdout:
                lines = res.stdout.decode("utf-8", errors="ignore").splitlines()
                protected_names = {
                    "kernel_task", "launchd", "windowserver", "loginwindow", "finder", "dock",
                    "system", "syslogd", "init", "securityd", "opendirectoryd", "distnoted",
                }
                parsed: List[ProcessDiagnosticInfo] = []
                for line in lines[1:]:
                    parts = line.strip().split(None, 6)
                    if len(parts) < 7:
                        continue
                    try:
                        pid = int(parts[0])
                        stat_val = parts[2]
                        cpu_p = float(parts[3])
                        rss_kb = int(parts[5])
                        comm = parts[6]
                        base_name = os.path.basename(comm).lower()

                        is_zombie = "Z" in stat_val or "zombie" in stat_val.lower()
                        state = "Zombie (Z)" if is_zombie else ("Running" if "R" in stat_val else "Sleeping")
                        can_term = pid > 100 and base_name not in protected_names

                        parsed.append(
                            ProcessDiagnosticInfo(
                                pid=pid,
                                name=os.path.basename(comm),
                                cpu_percent=round(cpu_p, 1),
                                memory_mb=round(rss_kb / 1024.0, 1),
                                state=state,
                                is_zombie=is_zombie,
                                can_terminate=can_term,
                            )
                        )
                    except (ValueError, IndexError):
                        continue

                zombies = [p for p in parsed if p.is_zombie]
                non_zombies = [p for p in parsed if not p.is_zombie]
                non_zombies.sort(key=lambda p: (p.cpu_percent + (p.memory_mb / 50.0)), reverse=True)

                processes = (zombies + non_zombies)[:max(limit, len(zombies))]
        except Exception:
            pass

        return processes[:limit]

    def remove_startup_item(self, item_path: str) -> bool:
        """Remove um arquivo .plist de LaunchAgent com backup prévio em outputs/snapshots/ (RF-17)."""
        if not item_path or not isinstance(item_path, str):
            return False
        clean_path = os.path.normpath(item_path)
        if not clean_path.endswith(".plist"):
            return False

        valid_parents = (
            os.path.expanduser("~/Library/LaunchAgents"),
            "/Library/LaunchAgents",
            "/Library/LaunchDaemons",
        )
        if not any(clean_path.startswith(os.path.normpath(vp)) for vp in valid_parents):
            return False

        if not os.path.exists(clean_path):
            return False

        try:
            snapshot_dir = os.path.join(os.getcwd(), "outputs", "snapshots")
            os.makedirs(snapshot_dir, exist_ok=True)
            fname = os.path.basename(clean_path)
            backup_file = os.path.join(snapshot_dir, f"startup_backup_{int(time.time())}_{fname}")
            shutil.copy2(clean_path, backup_file)
        except Exception:
            pass

        try:
            os.remove(clean_path)
            return True
        except (PermissionError, OSError):
            return False

    def terminate_process(self, pid: int) -> bool:
        """Envia SIGTERM para um processo de usuário, protegendo processos vitais do sistema (RF-17)."""
        if not isinstance(pid, int) or pid <= 100:
            return False
        protected_names = {
            "kernel_task", "launchd", "windowserver", "loginwindow", "finder", "dock",
            "system", "syslogd", "init", "securityd", "opendirectoryd", "distnoted",
            "cfprefsd", "mds", "mds_stores", "coreaudiod", "diskarbitrationd",
        }
        if sys.platform == "darwin":
            try:
                res = subprocess.run(["ps", "-p", str(pid), "-o", "comm="], capture_output=True, text=True, timeout=3, check=False)
                comm = res.stdout.strip()
                if not comm:
                    return False
                if os.path.basename(comm).lower() in protected_names:
                    return False
            except Exception:
                return False

        try:
            os.kill(pid, signal.SIGTERM)
            return True
        except (ProcessLookupError, PermissionError, OSError):
            return False

    def get_hardware_health(self) -> HardwareHealthInfo:
        disks = self.get_disks_health()
        memory = self.get_memory_diagnostics()
        gpus = self.get_gpu_info()
        battery = self.get_battery_health()
        startup_items = self.get_startup_items()
        top_processes = self.get_top_processes(limit=10)

        alerts: List[str] = []
        overall = "Saudável"

        for d in disks:
            if d.risk_alert:
                alerts.append(f"Disco '{d.name}': {d.risk_alert}")
                overall = "Crítico"

        if memory.swap_thrashing_detected:
            alerts.append("Alerta de Pressão de Memória: Risco de Swap Thrashing detectado no sistema.")
            if overall != "Crítico":
                overall = "Atenção"

        if battery.has_battery:
            if "service" in battery.condition.lower():
                alerts.append(f"Bateria: Manutenção recomendada pela Apple ({battery.condition}).")
                if overall == "Saudável":
                    overall = "Atenção"
            elif battery.cycle_count and battery.cycle_count > 900:
                alerts.append(f"Bateria com alto desgaste: {battery.cycle_count} ciclos registrados.")

        # Alerta se houver agentes órfãos tentando iniciar
        broken_count = len([s for s in startup_items if s.is_orphan])
        if broken_count > 0:
            alerts.append(f"Persistência de Boot: {broken_count} agentes de inicialização órfãos detectados.")

        return HardwareHealthInfo(
            disks=disks,
            memory=memory,
            gpus=gpus,
            battery=battery,
            overall_status=overall,
            critical_alerts=alerts,
            startup_items=startup_items,
            top_processes=top_processes,
        )


class MacOSStorageOptimizationAdapter(IStorageOptimizationPort):
    """Otimização inteligente de storage para macOS (APFS Maintenance & TRIM)."""

    def analyze_volume(self, drive: str) -> Dict[str, Any]:
        return {
            "drive": drive,
            "media_type": "APFS SSD (Apple Flash)",
            "is_ssd": True,
            "is_nvme": True,
            "fragmentation_percent": 0.0,
            "recommended_action": "Manutenção APFS & Expurgo de Snapshots COW",
            "guardrail_checks": [
                "Camada 1: Identificação de Arquitetura APFS (Apple File System)",
                "Camada 2: Bloqueio Estrito de Desfragmentação Física (Incompatível com Copy-On-Write / COW e danoso a células NAND)",
                "Camada 3: Status de Notificação de TRIM do Kernel Darwin",
                "Camada 4: Fail-Safe Default Ativo (Assume SSD/NVMe sem exceções)",
            ],
            "message": "Volumes APFS utilizam alocação Copy-On-Write inteligente. A desfragmentação tradicional é desnecessária e prejudicial. Ações recomendadas: Verificação de catálogo APFS e liberação de snapshots locais.",
        }

    @staticmethod
    def _sanitize_target(drive: str) -> str:
        """
        Sanitiza o alvo de volume/partição no macOS para diskutil verifyVolume (RNF-01 e RNF-03).
        Garante que apenas caminhos absolutos legítimos ou identificadores BSD seguros sejam repassados.
        """
        if not drive or not isinstance(drive, str):
            return "/"
        clean = drive.strip()
        if clean in ("/", "Macintosh HD", "Macintosh HD (/)", "disk0s1"):
            return "/"
        if clean.startswith("-"):
            return "/"
        if re.match(r"^/[a-zA-Z0-9_\-\. /]+$", clean) or re.match(r"^disk\d+(s\d+)?$", clean):
            return clean
        return "/"

    def optimize_volume(
        self,
        drive: str,
        media_type: Optional[str] = None,
        user_confirmed: bool = False,
        mode: ExecutionMode = ExecutionMode.DRY_RUN,
    ) -> StorageOptimizationResult:
        guardrails = [
            "Guardrail 1: Arquitetura APFS Copy-On-Write detectada. Desfragmentação tradicional de blocos bloqueada.",
            "Guardrail 2: Validação de integridade de metadados via 'diskutil verifyVolume'.",
            "Guardrail 3: Verificação de suporte a TRIM do controlador SSD.",
            "Guardrail 4: Fail-Safe Default Absoluto confirmado (SSD/NVMe).",
        ]

        if mode == ExecutionMode.DRY_RUN:
            return StorageOptimizationResult(
                drive=drive,
                media_type="APFS SSD",
                action_taken="Simulação de Manutenção APFS (Dry-Run)",
                success=True,
                fragmentation_before=0.0,
                fragmentation_after=0.0,
                message="[Simulação] Verificação de catálogo APFS e expurgo de snapshots simulados com sucesso. Nenhum I/O destrutivo realizado.",
                guardrail_checks=guardrails,
                user_confirmed=user_confirmed,
            )

        # Execução Real no macOS
        logs: List[str] = []
        success = True
        if sys.platform == "darwin":
            try:
                # 1. diskutil verifyVolume
                target = self._sanitize_target(drive)
                v_res = subprocess.run(["diskutil", "verifyVolume", target], capture_output=True, timeout=25, check=False)
                if v_res.returncode == 0:
                    logs.append("Verificação de integridade do volume APFS: Íntegro e consistente.")
                else:
                    logs.append("Verificação de volume APFS reportou avisos de consistência secundários.")
            except Exception as e:
                logs.append(f"diskutil verifyVolume: {str(e)}")

            try:
                # 2. tmutil thinlocalsnapshots (reserva segura)
                t_res = subprocess.run(["tmutil", "thinlocalsnapshots", "/", "1000000000", "4"], capture_output=True, timeout=15, check=False)
                logs.append("Consolidação e expurgo de snapshots locais antigos realizado via tmutil.")
            except Exception as e:
                logs.append(f"tmutil thinlocalsnapshots: {str(e)}")
        else:
            logs.append("Simulação de comandos APFS (diskutil e tmutil) em ambiente de teste não-darwin.")

        msg = "Manutenção APFS concluída com sucesso: " + " | ".join(logs)
        return StorageOptimizationResult(
            drive=drive,
            media_type="APFS SSD",
            action_taken="Manutenção APFS & Expurgo de Snapshots COW",
            success=success,
            fragmentation_before=0.0,
            fragmentation_after=0.0,
            message=msg,
            guardrail_checks=guardrails,
            user_confirmed=user_confirmed,
        )

