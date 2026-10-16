# -*- coding: utf-8 -*-
"""Implementação dos adaptadores de infraestrutura para macOS."""
import os
import re
import sys
import json
import shutil
import platform
import plistlib
import subprocess
from typing import List, Set, Dict

from src.domain.entities import (
    PartitionInfo,
    CloudDiagnosticInfo,
    OutdatedAppInfo,
)
from src.domain.ports import (
    ISystemProbePort,
    IActiveAppsPort,
    ICloudAndPackagesPort,
)
from src.domain.value_objects import OSPlatform, format_bytes


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
            usage = shutil.disk_usage(root_probe)
            total = usage.total
            free = usage.free
            used = total - free if total >= free else usage.used
            percent = (used / total * 100.0) if total > 0 else 0.0
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
                        v_usage = shutil.disk_usage(entry.path)
                        sig = (v_usage.total, v_usage.free)
                        # Se tem exatamente o mesmo total e free do container APFS raiz, é um firmlink/volume do mesmo container
                        if sig in seen_signatures or v_usage.total <= 0:
                            continue
                        seen_realpaths.add(real_p)
                        seen_signatures.add(sig)
                        v_used = v_usage.total - v_usage.free
                        v_pct = (v_used / v_usage.total * 100.0) if v_usage.total > 0 else 0.0
                        partitions.append(
                            PartitionInfo(
                                mount_point=entry.path,
                                drive_letter=entry.name,
                                total_bytes=v_usage.total,
                                used_bytes=v_used,
                                free_bytes=v_usage.free,
                                percent_used=round(v_pct, 1),
                                is_os_drive=False,
                                role="Volume Externo / Secundário Montado",
                                health_status="Quase Cheio" if v_pct >= 90 else "Saudável",
                                health_class="warning" if v_pct >= 90 else "success",
                                health_desc="Volume externo ou imagem de disco montada em /Volumes.",
                                filesystem="APFS/ExFAT",
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
                    if pkg_id:
                        pkgs.add(pkg_id)
                        for part in pkg_id.split("."):
                            if len(part) > 3 and part not in {"com", "org", "apple", "pkg"}:
                                pkgs.add(part)
            except Exception:
                pass
        return pkgs

    def get_launch_agents_and_daemons(self) -> Set[str]:
        """Camada 3: LaunchAgents e LaunchDaemons do usuário e do sistema."""
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
