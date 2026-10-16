# -*- coding: utf-8 -*-
"""Implementação dos adaptadores de infraestrutura para Windows."""
import os
import re
import sys
import ctypes
import shutil
import string
import platform
import subprocess
from typing import List, Set, Dict

try:
    import winreg
except ImportError:
    winreg = None  # type: ignore

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


WINDOWS_DEVELOPER_WHITELIST: Set[str] = {
    "antigravity", "postman", "vscode", "code", "vscodium", "jetbrains", "pycharm", "intellij",
    "webstorm", "clion", "datagrip", "goland", "rider", "androidstudio", "eclipse", "sublime",
    "httptoolkit", "insomnia", "dbeaver", "mongodbcompass", "mongodb", "docker", "docker desktop",
    "git", "github", "gitlab", "node", "nodejs", "npm", "nvm", "yarn", "pnpm", "bun",
    "python", "pip", "conda", "anaconda", "miniconda", "rust", "cargo", "go", "golang",
    "java", "jdk", "jre", "gradle", "maven", "nuget", "dotnet", "dotnet-sdk",
    "google", "chrome", "mozilla", "firefox", "brave", "edge", "msedge", "opera", "vivaldi",
    "discord", "slack", "telegram", "whatsapp", "zoom", "teams", "skype", "signal",
    "notion", "obsidian", "trello", "figma", "canva", "adobe", "acrobat",
    "microsoft", "windows", "packages", "nvidia", "intel", "amd", "realtek", "asus",
    "rog", "lenovo", "dell", "hp", "logitech", "razer", "corsair",
    "steam", "steamapps", "epicgames", "fortnite", "fortnitegame", "minecraft", ".minecraft",
    "lunarclient", "riot games", "leagueoflegends", "valorant", "gog galaxy", "ubisoft",
    "ea desktop", "battlenet", "roblox", "spotify",
}


class WindowsSystemProbeAdapter(ISystemProbePort):
    """Inspeciona SO, privilégios de Administrador, RAM e partições A:-Z: no Windows."""

    def get_os_platform(self) -> OSPlatform:
        return OSPlatform.WINDOWS

    def get_os_version_string(self) -> str:
        if sys.platform == "win32":
            return f"Windows {platform.release()} ({platform.version()})"
        return f"Windows (Simulado em {platform.system()})"

    def is_admin_or_root(self) -> bool:
        if sys.platform == "win32":
            try:
                return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
            except Exception:
                return False
        return False

    def get_total_ram_kb(self) -> int:
        if sys.platform == "win32":
            try:
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]

                stat = MEMORYSTATUSEX()
                stat.dwLength = ctypes.sizeof(stat)
                ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))  # type: ignore[attr-defined]
                if stat.ullTotalPhys > 0:
                    return int(stat.ullTotalPhys // 1024)
            except Exception:
                pass
        return 16 * 1024 * 1024  # Fallback 16 GB em KB

    def get_partitions(self) -> List[PartitionInfo]:
        partitions: List[PartitionInfo] = []
        system_drive = os.environ.get("SystemDrive", "C:").upper()
        if not system_drive.endswith("\\"):
            system_drive += "\\"

        candidate_mounts = (
            [f"{letter}:\\" for letter in string.ascii_uppercase]
            if os.name == "nt"
            else ["/"]
        )

        for mount_point in candidate_mounts:
            if not os.path.exists(mount_point):
                continue
            try:
                usage = shutil.disk_usage(mount_point)
                total = usage.total
                free = usage.free
                used = usage.used
                percent = (used / total * 100.0) if total > 0 else 0.0

                is_os_drive = (
                    mount_point.upper().startswith(system_drive)
                    if os.name == "nt"
                    else mount_point == "/"
                )
                if is_os_drive:
                    role = "Sistema Operacional & Aplicações Vitais"
                elif total > 300 * 1024 * 1024 * 1024:
                    role = "Armazenamento Principal, Jogos & Documentos"
                else:
                    role = "Armazenamento Secundário ou Removível"

                if is_os_drive and percent >= 90.0:
                    health_status = "Risco Crítico de Desempenho"
                    health_class = "danger"
                    health_desc = "Acima de 90% de ocupação no disco do SO. Causa lentidão de paginação e travamentos."
                elif is_os_drive and percent >= 80.0:
                    health_status = "Atenção (Espaço Reduzido)"
                    health_class = "warning"
                    health_desc = "Acima de 80% de ocupação. Recomendável executar limpeza autônoma."
                elif percent >= 92.0:
                    health_status = "Partição Quase Cheia"
                    health_class = "warning"
                    health_desc = "Partição de dados com mais de 92% de capacidade utilizada."
                else:
                    health_status = "Saudável"
                    health_class = "success"
                    health_desc = "Espaço livre adequado para operação de alta performance."

                partitions.append(
                    PartitionInfo(
                        mount_point=mount_point,
                        drive_letter=mount_point.rstrip("\\") if os.name == "nt" else "C: (Simulado)",
                        total_bytes=total,
                        used_bytes=used,
                        free_bytes=free,
                        percent_used=round(percent, 1),
                        is_os_drive=is_os_drive,
                        role=role,
                        health_status=health_status,
                        health_class=health_class,
                        health_desc=health_desc,
                        filesystem="NTFS",
                    )
                )
            except (PermissionError, OSError):
                continue

        return partitions


class WindowsActiveAppsAdapter(IActiveAppsPort):
    """Algoritmo Anti-Falsos Positivos de 5 Camadas para Windows."""

    def get_registry_apps(self) -> Set[str]:
        apps: Set[str] = set()
        if not winreg or os.name != "nt":
            return apps

        registry_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        for hkey, subkey_path in registry_keys:
            try:
                with winreg.OpenKey(hkey, subkey_path) as main_key:
                    num_subkeys = winreg.QueryInfoKey(main_key)[0]
                    for i in range(num_subkeys):
                        try:
                            subkey_name = winreg.EnumKey(main_key, i)
                            with winreg.OpenKey(main_key, subkey_name) as subkey:
                                try:
                                    display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                                    if display_name:
                                        name_clean = str(display_name).strip().lower()
                                        apps.add(name_clean)
                                        for word in name_clean.replace("-", " ").replace("_", " ").split():
                                            if len(word) > 2:
                                                apps.add(word)
                                except FileNotFoundError:
                                    pass
                                try:
                                    install_loc, _ = winreg.QueryValueEx(subkey, "InstallLocation")
                                    if install_loc:
                                        folder_name = os.path.basename(str(install_loc).rstrip("\\/")).lower()
                                        if folder_name:
                                            apps.add(folder_name)
                                except FileNotFoundError:
                                    pass
                        except OSError:
                            continue
            except OSError:
                continue
        return apps

    def get_user_programs_apps(self, drives: List[str]) -> Set[str]:
        apps: Set[str] = set()
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        if local_appdata:
            programs_path = os.path.join(local_appdata, "Programs")
            if os.path.exists(programs_path):
                try:
                    for item in os.listdir(programs_path):
                        if os.path.isdir(os.path.join(programs_path, item)):
                            apps.add(item.lower())
                except OSError:
                    pass

        sub_paths = [
            "Program Files", "Program Files (x86)", "ProgramData",
            "Games", "Jogos", "Steam", "SteamLibrary", "Epic Games", "Riot Games", "Aplicativos",
        ]
        for drive in drives:
            for sub in sub_paths:
                p = os.path.join(drive, sub)
                if os.path.exists(p):
                    try:
                        for item in os.listdir(p):
                            if os.path.isdir(os.path.join(p, item)):
                                apps.add(item.lower())
                    except OSError:
                        continue
        return apps

    def get_start_menu_apps(self) -> Set[str]:
        apps: Set[str] = set()
        start_menu_paths = [
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
        ]
        for p in start_menu_paths:
            if os.path.exists(p):
                for _, dirs, files in os.walk(p):
                    for item in dirs + files:
                        clean_item = os.path.splitext(item)[0].lower()
                        if clean_item and len(clean_item) > 2:
                            apps.add(clean_item)
        return apps

    def get_running_processes(self) -> Set[str]:
        procs: Set[str] = set()
        if os.name != "nt":
            return procs
        try:
            res = subprocess.run(
                ["tasklist", "/NH"],
                capture_output=True,
                timeout=10,
                check=False,
            )
            output = res.stdout.decode("utf-8", errors="ignore")
            for line in output.splitlines():
                line_str = line.strip()
                if ".exe" in line_str.lower():
                    parts = line_str.split()
                    if parts:
                        procs.add(parts[0].lower().replace(".exe", ""))
        except Exception:
            pass
        return procs

    def get_layer_breakdown(self, drives: List[str]) -> Dict[str, int]:
        return {
            "layer1_registry": len(self.get_registry_apps()),
            "layer2_install_dirs": len(self.get_user_programs_apps(drives)),
            "layer3_start_menu": len(self.get_start_menu_apps()),
            "layer4_processes": len(self.get_running_processes()),
            "layer5_whitelist": len(WINDOWS_DEVELOPER_WHITELIST),
        }

    def get_active_indicators(self, drives: List[str]) -> Set[str]:
        indicators: Set[str] = set()
        indicators.update(self.get_registry_apps())
        indicators.update(self.get_user_programs_apps(drives))
        indicators.update(self.get_start_menu_apps())
        indicators.update(self.get_running_processes())
        indicators.update(WINDOWS_DEVELOPER_WHITELIST)
        return indicators


class WindowsCloudAndPackagesAdapter(ICloudAndPackagesPort):
    """Diagnóstico OneDrive e verificação de pacotes desatualizados via winget no Windows."""

    def analyze_cloud_storage(self) -> List[CloudDiagnosticInfo]:
        user_profile = os.environ.get("USERPROFILE", os.path.expanduser("~"))
        possible_paths = [
            os.path.join(user_profile, "OneDrive"),
            os.path.join(user_profile, "OneDrive - Personal"),
        ]
        if os.path.exists(user_profile):
            try:
                for item in os.listdir(user_profile):
                    if item.lower().startswith("onedrive"):
                        full_p = os.path.join(user_profile, item)
                        if os.path.isdir(full_p) and full_p not in possible_paths:
                            possible_paths.append(full_p)
            except OSError:
                pass

        found_path = None
        total_bytes = 0
        file_count = 0

        for path in possible_paths:
            if os.path.exists(path):
                found_path = path
                try:
                    for root, _, files in os.walk(path):
                        for f in files:
                            fp = os.path.join(root, f)
                            try:
                                if not os.path.islink(fp):
                                    total_bytes += os.path.getsize(fp)
                                    file_count += 1
                            except OSError:
                                continue
                except OSError:
                    pass
                break

        return [
            CloudDiagnosticInfo(
                provider_name="Microsoft OneDrive",
                is_installed=found_path is not None,
                path=found_path or "Não detectado no perfil padrão",
                consumed_bytes=total_bytes,
                consumed_formatted=format_bytes(total_bytes),
                file_count=file_count,
                is_consuming_heavy_space=total_bytes > 500 * 1024 * 1024,
                recommendations=[
                    {
                        "step": "1. Liberar Espaço sem Apagar da Nuvem (Arquivos sob Demanda)",
                        "action": "Clique com o botão direito na pasta 'OneDrive' no Explorador de Arquivos e selecione 'Liberar espaço'.",
                        "effect": "Remove a cópia física local mantendo os arquivos seguros na nuvem sob demanda.",
                    },
                    {
                        "step": "2. Escolher Pastas Sincronizadas",
                        "action": "Abra Configurações do OneDrive > Conta > Escolher pastas e desmarque backups pesados antigos.",
                        "effect": "Reduz o uso contínuo de SSD e sincronização em segundo plano.",
                    },
                    {
                        "step": "3. Desativar Inicialização Automática (se não utilizar)",
                        "action": "Abra o Gerenciador de Tarefas (Ctrl+Shift+Esc) > Aplicativos de Inicialização > Desabilitar OneDrive.",
                        "effect": "Economiza memória RAM e I/O de disco ao iniciar o Windows.",
                    },
                ],
            )
        ]

    def check_outdated_packages(self) -> List[OutdatedAppInfo]:
        if os.name != "nt":
            return []
        outdated: List[OutdatedAppInfo] = []
        try:
            res = subprocess.run(
                ["winget", "upgrade", "--include-unknown"],
                capture_output=True,
                timeout=40,
                check=False,
            )
            stdout = res.stdout.decode("utf-8", errors="replace")
            lines = [line for line in stdout.splitlines() if line.strip()]
            dash_idx = -1
            for idx, line in enumerate(lines):
                if "---" in line:
                    dash_idx = idx
                    break
            if dash_idx <= 0:
                return []

            for line in lines[dash_idx + 1 :]:
                s = line.strip()
                if not s or "atualizações disponíveis" in s or "upgrades available" in s.lower():
                    break
                parts = re.split(r"\s{2,}", s)
                if len(parts) >= 4:
                    name, app_id, curr_ver, avail_ver = parts[0], parts[1], parts[2], parts[3]
                    source = parts[4] if len(parts) >= 5 else "winget"
                    if app_id.startswith("---"):
                        continue
                    curr_nums = [int(m) for m in re.findall(r"\d+", curr_ver)]
                    late_nums = [int(m) for m in re.findall(r"\d+", avail_ver)]
                    if curr_nums and late_nums and late_nums[0] > curr_nums[0]:
                        risk_level = "Médio/Alto Risco (Major Update)"
                        risk_badge = "warning"
                        risk_reason = f"Mudança de versão principal ({curr_ver} -> {avail_ver})."
                    else:
                        risk_level = "Baixo Risco (Update Incremental)"
                        risk_badge = "success"
                        risk_reason = "Atualização incremental de estabilidade e segurança."

                    outdated.append(
                        OutdatedAppInfo(
                            name=name,
                            app_id=app_id,
                            current_version=curr_ver,
                            latest_version=avail_ver,
                            source=source,
                            drive="C:\\",
                            risk_level=risk_level,
                            risk_badge=risk_badge,
                            risk_reason=risk_reason,
                            upgrade_cmd=f"winget upgrade --id {app_id}",
                        )
                    )
        except Exception:
            return []
        return outdated
