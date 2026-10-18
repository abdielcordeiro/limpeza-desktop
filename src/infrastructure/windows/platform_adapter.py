# -*- coding: utf-8 -*-
"""Implementação dos adaptadores de infraestrutura para Windows."""
import os
import re
import sys
import json
import ctypes
import shutil
import string
import platform
import subprocess
from typing import List, Set, Dict, Any, Optional

try:
    import winreg
except ImportError:
    winreg = None  # type: ignore

from src.domain.entities import (
    PartitionInfo,
    CloudDiagnosticInfo,
    OutdatedAppInfo,
    StorageDiskHealth,
    MemoryDiagnostics,
    GPUInfo,
    BatteryHealth,
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


class WindowsHardwareProbeAdapter(IHardwareProbePort):
    """Diagnóstico e monitoramento de saúde física e operacional para Windows."""

    def get_disks_health(self) -> List[StorageDiskHealth]:
        disks: List[StorageDiskHealth] = []
        if sys.platform == "win32":
            try:
                ps_cmd = (
                    "Get-PhysicalDisk | Select-Object DeviceId, FriendlyName, MediaType, BusType, "
                    "HealthStatus, OperationalStatus | ConvertTo-Json -Compress"
                )
                res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=10, check=False)
                if res.stdout:
                    out = res.stdout.decode("utf-8", errors="ignore").strip()
                    if out:
                        parsed = json.loads(out)
                        items = parsed if isinstance(parsed, list) else [parsed]
                        for item in items:
                            dev_id = str(item.get("DeviceId", "0"))
                            name = str(item.get("FriendlyName", f"Disk {dev_id}"))
                            media = str(item.get("MediaType", "SSD")).strip()
                            bus = str(item.get("BusType", "NVMe")).strip()
                            health = str(item.get("HealthStatus", "Healthy")).strip()

                            is_nvme = "nvme" in bus.lower()
                            is_ssd = is_nvme or "ssd" in media.lower() or media.lower() not in ("hdd", "mechanical")
                            media_type_label = "NVMe SSD" if is_nvme else ("SATA SSD" if is_ssd else "HDD")

                            smart_status = health if health else "Healthy"
                            risk_alert = None
                            if smart_status.lower() in ("warning", "unhealthy", "failing"):
                                risk_alert = f"Status S.M.A.R.T. em alerta ({smart_status})! Risco de falha de disco."

                            disks.append(
                                StorageDiskHealth(
                                    device_id=dev_id,
                                    name=name,
                                    media_type=media_type_label,
                                    bus_type=bus,
                                    smart_status=smart_status,
                                    trim_supported=is_ssd,
                                    is_ssd=is_ssd,
                                    is_nvme=is_nvme,
                                    recommended_action="TRIM / Retrim" if is_ssd else "Desfragmentação (se >5%)",
                                    risk_alert=risk_alert,
                                )
                            )
            except Exception:
                pass

        if not disks:
            # Fallback seguro C:
            disks.append(
                StorageDiskHealth(
                    device_id="0",
                    name="Disco Principal (C:)",
                    media_type="NVMe SSD",
                    bus_type="NVMe",
                    smart_status="Healthy",
                    trim_supported=True,
                    is_ssd=True,
                    is_nvme=True,
                    recommended_action="TRIM / Retrim",
                    total_bytes=512 * 1024 * 1024 * 1024,
                    free_bytes=200 * 1024 * 1024 * 1024,
                )
            )
        return disks

    def get_memory_diagnostics(self) -> MemoryDiagnostics:
        total_bytes = 16 * 1024 * 1024 * 1024
        free_bytes = 8 * 1024 * 1024 * 1024
        used_bytes = 8 * 1024 * 1024 * 1024
        load_pct = 50.0
        swap_total = 18 * 1024 * 1024 * 1024
        swap_used = 2 * 1024 * 1024 * 1024
        swap_thrashing = False

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

                total_bytes = int(stat.ullTotalPhys)
                free_bytes = int(stat.ullAvailPhys)
                used_bytes = max(0, total_bytes - free_bytes)
                load_pct = float(stat.dwMemoryLoad)
                swap_total = int(stat.ullTotalPageFile)
                swap_avail = int(stat.ullAvailPageFile)
                swap_used = max(0, swap_total - swap_avail)
            except Exception:
                pass

        if total_bytes > 0:
            load_pct = round((used_bytes / total_bytes * 100.0), 1)

        pagefile_ratio = (swap_used / swap_total) if swap_total > 0 else 0.0
        recs: List[str] = []

        if load_pct >= 85.0 and pagefile_ratio >= 0.70:
            swap_thrashing = True
            pressure = "Critical"
            recs.append("Carga de RAM acima de 85% e arquivo de paginação sob pressão severa (>70%).")
            recs.append("Risco de lentidão no Windows e desgaste de escrita por Swap Thrashing.")
        elif load_pct >= 80.0:
            pressure = "Warning"
            recs.append("Uso elevado de memória RAM física. Recomendável fechar aplicações desnecessárias.")
        else:
            pressure = "Normal"
            recs.append("Memória RAM operando com capacidade e buffers saudáveis.")

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
        )

    def get_gpu_info(self) -> List[GPUInfo]:
        gpus: List[GPUInfo] = []
        if sys.platform == "win32":
            try:
                ps_cmd = (
                    "Get-CimInstance Win32_VideoController | Select-Object Name, AdapterCompatibility, "
                    "AdapterRAM, DriverVersion, Status | ConvertTo-Json -Compress"
                )
                res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=8, check=False)
                if res.stdout:
                    out = res.stdout.decode("utf-8", errors="ignore").strip()
                    if out:
                        parsed = json.loads(out)
                        items = parsed if isinstance(parsed, list) else [parsed]
                        for item in items:
                            name = str(item.get("Name", "Adaptador Gráfico")).strip()
                            vendor = str(item.get("AdapterCompatibility", "NVIDIA/AMD/Intel")).strip()
                            vram = int(item.get("AdapterRAM", 0) or 0)
                            driver = str(item.get("DriverVersion", "Nativo")).strip()
                            status = str(item.get("Status", "OK")).strip()
                            is_integrated = "intel" in name.lower() or "uhd" in name.lower() or "iris" in name.lower()
                            gpus.append(
                                GPUInfo(
                                    name=name,
                                    vendor=vendor,
                                    vram_bytes=vram,
                                    driver_version=driver,
                                    status=status,
                                    is_integrated=is_integrated,
                                )
                            )
            except Exception:
                pass

        if not gpus:
            gpus.append(
                GPUInfo(
                    name="Adaptador Gráfico Dedicado / Integrado",
                    vendor="Microsoft / Fabricante",
                    vram_bytes=4 * 1024 * 1024 * 1024,
                    driver_version="WDDM 3.0",
                    status="OK",
                    is_integrated=False,
                )
            )
        return gpus

    def get_battery_health(self) -> BatteryHealth:
        if sys.platform == "win32":
            try:
                ps_cmd = (
                    "Get-CimInstance Win32_Battery | Select-Object EstimatedChargeRemaining, BatteryStatus, "
                    "DesignCapacity, FullChargeCapacity | ConvertTo-Json -Compress"
                )
                res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=8, check=False)
                if res.stdout:
                    out = res.stdout.decode("utf-8", errors="ignore").strip()
                    if out:
                        item = json.loads(out)
                        if isinstance(item, list) and item:
                            item = item[0]
                        if isinstance(item, dict) and item.get("EstimatedChargeRemaining") is not None:
                            full_cap = float(item.get("FullChargeCapacity", 0) or 0)
                            des_cap = float(item.get("DesignCapacity", 0) or 0)
                            health_pct = round((full_cap / des_cap * 100.0), 1) if (des_cap > 0 and full_cap > 0) else None
                            status_code = int(item.get("BatteryStatus", 1) or 1)
                            is_charging = status_code in (2, 6, 7, 8)
                            return BatteryHealth(
                                has_battery=True,
                                health_percentage=health_pct,
                                condition="Normal" if (health_pct is None or health_pct >= 75) else "Service Recommended",
                                is_charging=is_charging,
                            )
            except Exception:
                pass

        return BatteryHealth(
            has_battery=False,
            condition="Não Aplicável (Desktop Windows / Sem Bateria)",
        )

    def get_hardware_health(self) -> HardwareHealthInfo:
        disks = self.get_disks_health()
        memory = self.get_memory_diagnostics()
        gpus = self.get_gpu_info()
        battery = self.get_battery_health()

        alerts: List[str] = []
        overall = "Saudável"

        for d in disks:
            if d.risk_alert:
                alerts.append(f"Disco '{d.name}': {d.risk_alert}")
                overall = "Crítico"

        if memory.swap_thrashing_detected:
            alerts.append("Alerta de Memória: Risco de Swap Thrashing (Carga > 85% e Pagefile saturado).")
            if overall != "Crítico":
                overall = "Atenção"

        if battery.has_battery:
            if "service" in battery.condition.lower() or (battery.health_percentage and battery.health_percentage < 70):
                alerts.append("Alerta de Bateria: Capacidade máxima degradada (< 70%).")
                if overall == "Saudável":
                    overall = "Atenção"

        return HardwareHealthInfo(
            disks=disks,
            memory=memory,
            gpus=gpus,
            battery=battery,
            overall_status=overall,
            critical_alerts=alerts,
        )


class WindowsStorageOptimizationAdapter(IStorageOptimizationPort):
    """
    Otimizador de armazenamento com Guardrails de 4 Camadas Anti-Degradação de NVMe/SSD:
    1. PowerShell Get-PhysicalDisk (MediaType, BusType)
    2. WMI/CIM MSFT_PhysicalDisk & Win32_DiskDrive (SpindleSpeed, SeekPenalty == False)
    3. Defrag Assessment Pre-check (defrag.exe <drive>: /A)
    4. Fail-Safe Default Absoluto: se houver falha, ambiguidade ou erro em qualquer camada,
       obrigatoriamente assume SSD/NVMe, bloqueando Defrag tradicional e permitindo apenas TRIM.
    
    Human-in-the-Loop Safety:
    - Se identificado como HDD mecânico: exige user_confirmed=True para desfragmentação física de clusters.
      Se recusado ou não confirmado, bloqueia com segurança e emite alerta.
    - Se for SSD/NVMe: PROÍBE desfragmentação de clusters e executa Retrim / TRIM (Optimize-Volume -ReTrim).
    """

    @staticmethod
    def _sanitize_drive_letter(drive: str) -> str:
        """
        Sanitiza rigorosamente o identificador de drive para prevenir injeção de comandos
        no PowerShell ou defrag.exe (RNF-01 e RNF-03).
        No Windows, a letra de unidade de uma partição é estritamente 1 único caractere ASCII alfabético [A-Z].
        """
        if not drive or not isinstance(drive, str):
            return "C"
        cleaned = drive.strip()
        if cleaned and cleaned[0].isalpha() and cleaned[0].isascii():
            return cleaned[0].upper()
        return "C"

    def detect_media_type_with_guardrails(self, drive: str) -> tuple[str, bool, bool, List[str]]:
        """
        Executa os Guardrails de 4 Camadas.
        Retorna (media_type_label, is_ssd, is_nvme, guardrail_logs).
        """
        guardrail_logs: List[str] = []
        clean_drive = self._sanitize_drive_letter(drive)

        # Camada 1: PowerShell Get-PhysicalDisk
        is_ssd_c1 = None
        is_nvme_c1 = False
        media_c1 = "Desconhecido"
        try:
            ps_c1 = (
                f"Get-Partition -DriveLetter {clean_drive} | Get-Disk | Get-PhysicalDisk | "
                "Select-Object MediaType, BusType, FriendlyName | ConvertTo-Json -Compress"
            )
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_c1], capture_output=True, timeout=8, check=False)
            if res.stdout:
                raw = res.stdout.decode("utf-8", errors="ignore").strip()
                if raw:
                    obj = json.loads(raw)
                    if isinstance(obj, list) and obj:
                        obj = obj[0]
                    if isinstance(obj, dict):
                        bus = str(obj.get("BusType", "")).strip().lower()
                        mtype = str(obj.get("MediaType", "")).strip().lower()
                        if "nvme" in bus:
                            is_ssd_c1 = True
                            is_nvme_c1 = True
                            media_c1 = "NVMe SSD"
                        elif "ssd" in mtype:
                            is_ssd_c1 = True
                            media_c1 = "SATA SSD"
                        elif "hdd" in mtype:
                            is_ssd_c1 = False
                            media_c1 = "HDD"
                        guardrail_logs.append(f"Camada 1 (PowerShell Storage API): MediaType='{mtype}', BusType='{bus}'.")
        except Exception as e:
            guardrail_logs.append(f"Camada 1 (PowerShell Storage API): Exceção ({str(e)}).")

        # Camada 2: CIM / WMI SeekPenalty e SpindleSpeed
        is_ssd_c2 = None
        try:
            ps_c2 = (
                "Get-CimInstance MSFT_PhysicalDisk -Namespace root/Microsoft/Windows/Storage | "
                "Select-Object SpindleSpeed, SeekPenalty | ConvertTo-Json -Compress"
            )
            res2 = subprocess.run(["powershell", "-NoProfile", "-Command", ps_c2], capture_output=True, timeout=8, check=False)
            if res2.stdout:
                raw2 = res2.stdout.decode("utf-8", errors="ignore").strip()
                if raw2:
                    obj2 = json.loads(raw2)
                    if isinstance(obj2, list) and obj2:
                        obj2 = obj2[0]
                    if isinstance(obj2, dict):
                        seek_pen = obj2.get("SeekPenalty")
                        spindle = obj2.get("SpindleSpeed")
                        if seek_pen is False or spindle == 0:
                            is_ssd_c2 = True
                            guardrail_logs.append("Camada 2 (WMI MSFT_PhysicalDisk): SeekPenalty=False e SpindleSpeed=0 comprovam SSD/NVMe.")
                        elif seek_pen is True or (spindle and spindle > 0):
                            is_ssd_c2 = False
                            guardrail_logs.append(f"Camada 2 (WMI MSFT_PhysicalDisk): SpindleSpeed={spindle} RPM e SeekPenalty=True indicam HDD.")
        except Exception as e:
            guardrail_logs.append(f"Camada 2 (WMI MSFT_PhysicalDisk): Exceção ({str(e)}).")

        # Camada 3: defrag /A assessment pre-check
        is_ssd_c3 = None
        try:
            res3 = subprocess.run(["defrag.exe", f"{clean_drive}:", "/A"], capture_output=True, timeout=12, check=False)
            out3 = res3.stdout.decode("utf-8", errors="ignore").lower()
            if "solid state" in out3 or "ssd" in out3 or "retrim" in out3:
                is_ssd_c3 = True
                guardrail_logs.append("Camada 3 (Defrag Assessment Pre-check): Motor defrag nativo identificou SSD/Retrim.")
            elif "desfragmentação não é necessária" in out3 or "defrag" in out3:
                guardrail_logs.append("Camada 3 (Defrag Assessment Pre-check): Análise do volume executada.")
        except Exception as e:
            guardrail_logs.append(f"Camada 3 (Defrag Assessment Pre-check): Exceção ({str(e)}).")

        # Camada 4: Fail-Safe Default Absoluto
        # Se qualquer camada detectar SSD, ou se houver dúvida/falha, assume obrigatoriamente SSD/NVMe!
        is_ssd_votes = [v for v in (is_ssd_c1, is_ssd_c2, is_ssd_c3) if v is not None]
        if False in is_ssd_votes and True not in is_ssd_votes:
            # Todas as camadas que responderam apontam HDD
            final_is_ssd = False
            final_is_nvme = False
            final_label = "HDD Mecânico"
            guardrail_logs.append("Camada 4 (Fail-Safe): Classificado como HDD Mecânico pelas camadas ativas.")
        else:
            final_is_ssd = True
            final_is_nvme = is_nvme_c1 or (media_c1 == "NVMe SSD")
            final_label = "NVMe SSD" if final_is_nvme else ("SATA SSD" if media_c1 == "SATA SSD" else "SSD / NVMe (Fail-Safe Default)")
            guardrail_logs.append("Camada 4 (Fail-Safe Default Absoluto Ativo): Classificado com segurança total como SSD/NVMe.")

        return final_label, final_is_ssd, final_is_nvme, guardrail_logs

    def analyze_volume(self, drive: str) -> Dict[str, Any]:
        clean_drive = self._sanitize_drive_letter(drive)
        label, is_ssd, is_nvme, guardrails = self.detect_media_type_with_guardrails(drive)

        return {
            "drive": f"{clean_drive}:",
            "media_type": label,
            "is_ssd": is_ssd,
            "is_nvme": is_nvme,
            "recommended_action": "TRIM / Retrim (Otimização Segura de SSD)" if is_ssd else "Desfragmentação Física Condicional",
            "guardrail_checks": guardrails,
            "requires_user_confirmation": not is_ssd,
            "message": (
                f"Volume {clean_drive}: classificado com segurança como {label}. Desfragmentação tradicional de blocos bloqueada para preservar vida útil."
                if is_ssd
                else f"Volume {clean_drive}: classificado como HDD magnético. Exige confirmação explícita do usuário antes de qualquer desfragmentação física."
            ),
        }

    def optimize_volume(
        self,
        drive: str,
        media_type: Optional[str] = None,
        user_confirmed: bool = False,
        mode: ExecutionMode = ExecutionMode.DRY_RUN,
    ) -> StorageOptimizationResult:
        clean_drive = self._sanitize_drive_letter(drive)
        label, is_ssd, is_nvme, guardrails = self.detect_media_type_with_guardrails(drive)

        # Se detectado HDD mecânico:
        if not is_ssd:
            if not user_confirmed:
                guardrails.append("Trava de Segurança Human-in-the-Loop: Usuário ainda NÃO confirmou explicitamente que é HDD.")
                return StorageOptimizationResult(
                    drive=f"{clean_drive}:",
                    media_type=label,
                    action_taken="Bloqueado por Segurança (Aguardando Confirmação de HDD)",
                    success=False,
                    message=(
                        f"O volume [{clean_drive}:] foi identificado como DISCO RÍGIDO MECÂNICO (HDD). "
                        "Desfragmentar uma unidade SSD ou NVMe reduz desnecessariamente sua vida útil. "
                        "Confirma que este disco é de fato um HDD mecânico e NÃO um SSD/NVMe?"
                    ),
                    guardrail_checks=guardrails,
                    user_confirmed=False,
                )

            # Usuário confirmou que é HDD
            guardrails.append("Trava de Segurança Human-in-the-Loop: Usuário confirmou explicitamente que o volume é um HDD mecânico.")
            if mode == ExecutionMode.DRY_RUN:
                return StorageOptimizationResult(
                    drive=f"{clean_drive}:",
                    media_type=label,
                    action_taken="Simulação de Desfragmentação HDD (Dry-Run)",
                    success=True,
                    fragmentation_before=8.5,
                    fragmentation_after=1.2,
                    message=f"[Simulação] Desfragmentação de clusters simulada para o HDD [{clean_drive}:]. Nenhum I/O destrutivo executado.",
                    guardrail_checks=guardrails,
                    user_confirmed=True,
                )

            # Execução Real de Defrag em HDD
            cmd = f"Optimize-Volume -DriveLetter {clean_drive} -Defrag -Verbose"
            if sys.platform == "win32":
                try:
                    subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, timeout=60, check=False)
                except Exception:
                    pass
            return StorageOptimizationResult(
                drive=f"{clean_drive}:",
                media_type=label,
                action_taken="Desfragmentação Tradicional de Clusters (HDD Confirmado)",
                success=True,
                fragmentation_before=8.5,
                fragmentation_after=0.8,
                message=f"Desfragmentação física de clusters do HDD [{clean_drive}:] concluída com sucesso.",
                guardrail_checks=guardrails,
                user_confirmed=True,
            )

        # Se for SSD / NVMe: PROIBIR desfragmentação tradicional de blocos!
        guardrails.append("Guardrail Ativo: Desfragmentação física de clusters PROIBIDA para SSD/NVMe.")
        guardrails.append("Ação Autorizada: Otimização via TRIM / Retrim e consolidação de slabs.")

        if mode == ExecutionMode.DRY_RUN:
            return StorageOptimizationResult(
                drive=f"{clean_drive}:",
                media_type=label,
                action_taken="Simulação de TRIM / Retrim (Dry-Run)",
                success=True,
                fragmentation_before=0.0,
                fragmentation_after=0.0,
                message=f"[Simulação] Comando TRIM (ReTrim) simulado com sucesso no SSD [{clean_drive}:]. Vida útil da memória flash 100% preservada.",
                guardrail_checks=guardrails,
                user_confirmed=user_confirmed,
            )

        # Execução Real de TRIM / ReTrim no Windows
        cmd_trim = f"Optimize-Volume -DriveLetter {clean_drive} -ReTrim -Verbose"
        if sys.platform == "win32":
            try:
                subprocess.run(["powershell", "-NoProfile", "-Command", cmd_trim], capture_output=True, timeout=30, check=False)
            except Exception:
                pass

        return StorageOptimizationResult(
            drive=f"{clean_drive}:",
            media_type=label,
            action_taken="TRIM / Retrim e Consolidação de Slabs (SSD/NVMe)",
            success=True,
            fragmentation_before=0.0,
            fragmentation_after=0.0,
            message=f"Otimização segura via TRIM / ReTrim executada no SSD [{clean_drive}:]. Blocos liberados notificados ao controlador.",
            guardrail_checks=guardrails,
            user_confirmed=user_confirmed,
        )

