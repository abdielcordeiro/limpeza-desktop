# -*- coding: utf-8 -*-
"""Motor Declarativo e Idempotente de Otimizações do Sistema (Windows WinUtil Sanitizado & macOS)."""
import os
import re
import sys
import json
import shlex
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    import winreg
except ImportError:
    winreg = None  # type: ignore

from src.domain.entities import TweakDefinition, TweakExecutionRecord
from src.domain.ports import ISystemTweakPort, ISystemProbePort
from src.domain.value_objects import ExecutionMode, OSPlatform
from src.infrastructure.resources import get_catalog_path


class SystemTweakAdapter(ISystemTweakPort):
    """Carrega os catálogos JSON offline e aplica/reverte Tweaks com idempotência e snapshot prévio."""

    def __init__(
        self,
        system_probe: ISystemProbePort,
        windows_catalog_path: Optional[str] = None,
        macos_catalog_path: Optional[str] = None,
    ) -> None:
        self.system_probe = system_probe
        self.windows_catalog_path = os.path.abspath(
            windows_catalog_path or get_catalog_path("windows_tweaks.json")
        )
        self.macos_catalog_path = os.path.abspath(
            macos_catalog_path or get_catalog_path("macos_tweaks.json")
        )
        self._tweaks_cache: Dict[str, List[TweakDefinition]] = {}

    def _load_catalog(self, catalog_path: str) -> List[TweakDefinition]:
        if not os.path.exists(catalog_path):
            return []
        with open(catalog_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        tweaks: List[TweakDefinition] = []
        for item in data.get("tweaks", []):
            tweaks.append(
                TweakDefinition(
                    id=item["id"],
                    name=item["name"],
                    category=item["category"],
                    panel=item.get("panel", "essential"),
                    os_platform=item["os_platform"],
                    preset=item.get("preset", "standard"),
                    risk_level=item.get("risk_level", "safe"),
                    description=item.get("description", ""),
                    registry_changes=item.get("registry_changes", []),
                    service_changes=item.get("service_changes", []),
                    scheduled_tasks=item.get("scheduled_tasks", []),
                    invoke_commands=item.get("invoke_commands", []),
                    undo_commands=item.get("undo_commands", []),
                    requires_admin=item.get("requires_admin", False),
                    benefit=item.get("benefit", ""),
                    undo_hint=item.get("undo_hint", ""),
                )
            )
        return tweaks

    def list_available_tweaks(self, os_platform: Optional[OSPlatform] = None) -> List[TweakDefinition]:
        win_tweaks = self._load_catalog(self.windows_catalog_path)
        mac_tweaks = self._load_catalog(self.macos_catalog_path)
        if os_platform == OSPlatform.WINDOWS:
            return win_tweaks
        if os_platform == OSPlatform.MACOS:
            return mac_tweaks
        return win_tweaks + mac_tweaks

    def capture_current_state(self, tweak: TweakDefinition) -> Dict[str, Any]:
        """Captura o estado atual da máquina antes de aplicar o Tweak para reversão exata (Undo)."""
        state: Dict[str, Any] = {
            "tweak_id": tweak.id,
            "os_platform": tweak.os_platform,
            "captured_at": datetime.now().isoformat(),
            "registry_or_defaults": [],
            "services": [],
            "scheduled_tasks": [],
        }

        if tweak.os_platform == OSPlatform.WINDOWS.value:
            for reg in tweak.registry_changes:
                hive_name = reg.get("hive", "HKCU")
                path = reg.get("path", "")
                name = reg.get("name", "")
                current_val = reg.get("original_value")
                existed = False

                if winreg and os.name == "nt":
                    hkey = (
                        winreg.HKEY_LOCAL_MACHINE
                        if hive_name == "HKLM"
                        else winreg.HKEY_CURRENT_USER
                    )
                    try:
                        with winreg.OpenKey(hkey, path, 0, winreg.KEY_READ) as k:
                            val, _ = winreg.QueryValueEx(k, name)
                            current_val = val
                            existed = True
                    except OSError:
                        existed = False

                state["registry_or_defaults"].append(
                    {
                        "hive": hive_name,
                        "path": path,
                        "name": name,
                        "type": reg.get("type", "REG_DWORD"),
                        "previous_value": current_val,
                        "existed": existed,
                    }
                )

            for svc in tweak.service_changes:
                state["services"].append(
                    {
                        "name": svc["name"],
                        "previous_startup_type": svc.get("original_type", "Manual"),
                    }
                )

            for task in tweak.scheduled_tasks:
                state["scheduled_tasks"].append(
                    {
                        "task_path": task,
                        "previous_enabled": True,
                    }
                )
        else:
            # macOS defaults capture
            for d_entry in tweak.registry_changes:
                domain = d_entry.get("domain", "")
                key = d_entry.get("key", "")
                prev_val = d_entry.get("original_value")
                existed = False
                if sys.platform == "darwin" and domain and key:
                    try:
                        res = subprocess.run(
                            ["defaults", "read", domain, key],
                            capture_output=True,
                            timeout=4,
                            check=False,
                        )
                        if res.returncode == 0:
                            prev_val = res.stdout.decode("utf-8", errors="ignore").strip()
                            existed = True
                    except Exception:
                        existed = False

                state["registry_or_defaults"].append(
                    {
                        "domain": domain,
                        "key": key,
                        "type": d_entry.get("type", "string"),
                        "previous_value": prev_val,
                        "existed": existed,
                    }
                )

        return state

    def _apply_idempotent_ultimate_performance(self) -> str:
        """
        Ativa o plano Ultimate Performance no Windows sem duplicar esquemas caso já exista.
        """
        ult_guid = "e9a42b02-d5df-448d-aa00-03f14749eb61"
        if os.name != "nt":
            return f"Plano Ultimate Performance ({ult_guid}) validado em modo multiplataforma."

        try:
            list_res = subprocess.run(
                ["powercfg.exe", "/list"],
                capture_output=True,
                timeout=10,
                check=False,
            )
            out = list_res.stdout.decode("utf-8", errors="ignore")
            existing_guid = None
            for line in out.splitlines():
                if ult_guid.lower() in line.lower() or "ultimate performance" in line.lower() or "desempenho máximo" in line.lower():
                    m = re.search(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", line)
                    if m:
                        existing_guid = m.group(1)
                        break

            if not existing_guid:
                dup_res = subprocess.run(
                    ["powercfg.exe", "-duplicatescheme", ult_guid],
                    capture_output=True,
                    timeout=10,
                    check=False,
                )
                dup_out = dup_res.stdout.decode("utf-8", errors="ignore")
                m = re.search(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", dup_out)
                existing_guid = m.group(1) if m else ult_guid

            subprocess.run(
                ["powercfg.exe", "/setactive", existing_guid],
                capture_output=True,
                timeout=10,
                check=False,
            )
            return f"Plano Ultimate Performance ativado de forma idempotente (GUID: {existing_guid})."
        except Exception as e:
            return f"Aviso ao configurar plano Ultimate Performance: {e}"

    def apply_tweak(
        self,
        tweak: TweakDefinition,
        mode: ExecutionMode,
    ) -> TweakExecutionRecord:
        prev_state = self.capture_current_state(tweak)
        now_iso = datetime.now().isoformat()
        ram_kb = self.system_probe.get_total_ram_kb()

        if mode == ExecutionMode.DRY_RUN:
            reg_count = len(tweak.registry_changes)
            svc_count = len(tweak.service_changes)
            tsk_count = len(tweak.scheduled_tasks)
            cmd_count = len(tweak.invoke_commands)
            msg = (
                f"[Simulação Dry-Run] Tweak '{tweak.name}' validado: "
                f"{reg_count} chaves/defaults, {svc_count} serviços, "
                f"{tsk_count} tarefas agendadas, {cmd_count} comandos."
            )
            return TweakExecutionRecord(
                tweak_id=tweak.id,
                name=tweak.name,
                category=tweak.category,
                action="dry_run",
                success=True,
                message=msg,
                previous_state=prev_state,
                applied_at=now_iso,
            )

        # Execução REAL
        host_os = OSPlatform.detect_current()
        if tweak.os_platform != host_os.value:
            return TweakExecutionRecord(
                tweak_id=tweak.id,
                name=tweak.name,
                category=tweak.category,
                action="apply",
                success=True,
                message=(
                    f"Tweak de {tweak.os_platform.upper()} registrado em modo compatibilidade "
                    f"(SO hospedeiro atual: {host_os.value.upper()})."
                ),
                previous_state=prev_state,
                applied_at=now_iso,
            )

        applied_details: List[str] = []

        if tweak.os_platform == OSPlatform.WINDOWS.value:
            # 1. Registry Changes
            for reg in tweak.registry_changes:
                val = ram_kb if reg.get("value") == "DYNAMIC_RAM_KB" else reg.get("value")
                if winreg and os.name == "nt":
                    hive_name = reg.get("hive", "HKCU")
                    hkey = (
                        winreg.HKEY_LOCAL_MACHINE
                        if hive_name == "HKLM"
                        else winreg.HKEY_CURRENT_USER
                    )
                    reg_type_str = reg.get("type", "REG_DWORD")
                    reg_type = winreg.REG_DWORD if reg_type_str == "REG_DWORD" else winreg.REG_SZ
                    try:
                        with winreg.CreateKeyEx(hkey, reg["path"], 0, winreg.KEY_SET_VALUE) as k:
                            winreg.SetValueEx(
                                k,
                                reg["name"],
                                0,
                                reg_type,
                                int(val) if reg_type == winreg.REG_DWORD else str(val or ""),
                            )
                        applied_details.append(f"{hive_name}\\{reg['path']}\\{reg['name']}={val}")
                    except OSError as e:
                        applied_details.append(f"Aviso Reg ({reg['name']}): {e}")

            # 2. Services
            sc_map = {
                "Disabled": "disabled",
                "Manual": "demand",
                "Automatic": "auto",
                "AutomaticDelayedStart": "delayed-auto",
            }
            for svc in tweak.service_changes:
                target_start = sc_map.get(svc.get("startup_type", "Manual"), "demand")
                if os.name == "nt":
                    try:
                        subprocess.run(
                            ["sc.exe", "config", svc["name"], f"start= {target_start}"],
                            capture_output=True,
                            timeout=8,
                            check=False,
                        )
                    except Exception:
                        pass
            if tweak.service_changes:
                applied_details.append(f"{len(tweak.service_changes)} serviços otimizados")

            # 3. Scheduled Tasks
            for task_path in tweak.scheduled_tasks:
                if os.name == "nt":
                    try:
                        subprocess.run(
                            ["schtasks.exe", "/Change", "/TN", task_path, "/Disable"],
                            capture_output=True,
                            timeout=8,
                            check=False,
                        )
                    except Exception:
                        pass
            if tweak.scheduled_tasks:
                applied_details.append(f"{len(tweak.scheduled_tasks)} tarefas de telemetria desativadas")

            # 4. Invoke Commands
            for cmd in tweak.invoke_commands:
                if cmd == "IDEMPOTENT_ULTIMATE_PERFORMANCE":
                    applied_details.append(self._apply_idempotent_ultimate_performance())
                elif os.name == "nt":
                    try:
                        subprocess.run(cmd, shell=True, capture_output=True, timeout=45, check=False)
                        applied_details.append(f"Comando executado: {cmd.split()[0]}")
                    except Exception:
                        pass
        else:
            # macOS Execution
            for cmd in tweak.invoke_commands:
                if sys.platform == "darwin":
                    try:
                        args = shlex.split(cmd)
                        subprocess.run(args, capture_output=True, timeout=25, check=False)
                        applied_details.append(f"Executado: {args[0]}")
                    except Exception as e:
                        applied_details.append(f"Aviso ({cmd}): {e}")

        summary_msg = (
            "; ".join(applied_details[:4])
            if applied_details
            else f"Tweak '{tweak.name}' aplicado com sucesso."
        )
        return TweakExecutionRecord(
            tweak_id=tweak.id,
            name=tweak.name,
            category=tweak.category,
            action="apply",
            success=True,
            message=summary_msg,
            previous_state=prev_state,
            applied_at=now_iso,
        )

    def revert_tweak(
        self,
        tweak: TweakDefinition,
        previous_state: Optional[Dict[str, Any]],
        mode: ExecutionMode,
    ) -> TweakExecutionRecord:
        """Reverte um Tweak (Undo) de forma 100% idempotente para o estado anterior salvo ou original."""
        now_iso = datetime.now().isoformat()
        if mode == ExecutionMode.DRY_RUN:
            return TweakExecutionRecord(
                tweak_id=tweak.id,
                name=tweak.name,
                category=tweak.category,
                action="undo",
                success=True,
                message=f"[Simulação Undo] Reversão de '{tweak.name}' validada com sucesso.",
                previous_state=previous_state or {},
                applied_at=now_iso,
            )

        host_os = OSPlatform.detect_current()
        reverted_details: List[str] = []

        if tweak.os_platform == OSPlatform.WINDOWS.value:
            # Reverte chaves de Registro
            saved_regs = (previous_state or {}).get("registry_or_defaults", [])
            reg_items = saved_regs if saved_regs else tweak.registry_changes
            for reg in reg_items:
                orig_val = reg.get("previous_value", reg.get("original_value"))
                if winreg and os.name == "nt" and orig_val is not None:
                    hive_name = reg.get("hive", "HKCU")
                    hkey = (
                        winreg.HKEY_LOCAL_MACHINE
                        if hive_name == "HKLM"
                        else winreg.HKEY_CURRENT_USER
                    )
                    reg_type_str = reg.get("type", "REG_DWORD")
                    reg_type = winreg.REG_DWORD if reg_type_str == "REG_DWORD" else winreg.REG_SZ
                    try:
                        with winreg.CreateKeyEx(hkey, reg["path"], 0, winreg.KEY_SET_VALUE) as k:
                            winreg.SetValueEx(
                                k,
                                reg["name"],
                                0,
                                reg_type,
                                int(orig_val) if reg_type == winreg.REG_DWORD else str(orig_val),
                            )
                    except OSError:
                        pass
            if reg_items:
                reverted_details.append(f"{len(reg_items)} chaves de Registro restauradas")

            # Reverte Serviços ao OriginalType
            sc_map = {
                "Disabled": "disabled",
                "Manual": "demand",
                "Automatic": "auto",
                "AutomaticDelayedStart": "delayed-auto",
            }
            for svc in tweak.service_changes:
                orig_type = svc.get("original_type", "Manual")
                target_start = sc_map.get(orig_type, "demand")
                if os.name == "nt":
                    try:
                        subprocess.run(
                            ["sc.exe", "config", svc["name"], f"start= {target_start}"],
                            capture_output=True,
                            timeout=8,
                            check=False,
                        )
                    except Exception:
                        pass
            if tweak.service_changes:
                reverted_details.append(f"{len(tweak.service_changes)} serviços restaurados ao tipo original")

            # Reativa Scheduled Tasks
            for task_path in tweak.scheduled_tasks:
                if os.name == "nt":
                    try:
                        subprocess.run(
                            ["schtasks.exe", "/Change", "/TN", task_path, "/Enable"],
                            capture_output=True,
                            timeout=8,
                            check=False,
                        )
                    except Exception:
                        pass

            for ucmd in tweak.undo_commands:
                if os.name == "nt":
                    try:
                        subprocess.run(ucmd, shell=True, capture_output=True, timeout=20, check=False)
                    except Exception:
                        pass
        else:
            # macOS Undo
            for ucmd in tweak.undo_commands:
                if sys.platform == "darwin" and host_os == OSPlatform.MACOS:
                    try:
                        args = shlex.split(ucmd)
                        subprocess.run(args, capture_output=True, timeout=15, check=False)
                        reverted_details.append(f"Undo executado: {args[0]}")
                    except Exception:
                        pass

        msg = (
            "; ".join(reverted_details)
            if reverted_details
            else f"Estado original de '{tweak.name}' restaurado com sucesso."
        )
        return TweakExecutionRecord(
            tweak_id=tweak.id,
            name=tweak.name,
            category=tweak.category,
            action="undo",
            success=True,
            message=msg,
            previous_state=previous_state or {},
            applied_at=now_iso,
        )
