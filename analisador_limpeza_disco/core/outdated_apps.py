# -*- coding: utf-8 -*-
import os
import sys
import re
import subprocess
import winreg
from typing import List, Dict, Any, Tuple

def get_installed_apps_locations() -> Dict[str, str]:
    """
    Varre o Registro do Windows em busca do InstallLocation dos programas instalados,
    mapeando o nome em caixa baixa para a letra do drive/caminho.
    """
    locations = {}
    registry_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]

    for hkey, subkey_path in registry_paths:
        try:
            with winreg.OpenKey(hkey, subkey_path) as key:
                num_subkeys = winreg.QueryInfoKey(key)[0]
                for i in range(num_subkeys):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            display_name = ""
                            install_loc = ""
                            try:
                                display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                            except OSError:
                                pass
                            try:
                                install_loc, _ = winreg.QueryValueEx(subkey, "InstallLocation")
                            except OSError:
                                pass

                            if display_name and install_loc:
                                drive = os.path.splitdrive(install_loc)[0].upper()
                                if drive:
                                    drive += "\\"
                                    locations[display_name.lower().strip()] = drive
                    except OSError:
                        continue
        except OSError:
            continue

    return locations

def parse_version_numbers(ver_str: str) -> List[int]:
    """Extrai uma lista de inteiros de uma string de versão (ex: '4.78.0' -> [4, 78, 0])."""
    matches = re.findall(r'\d+', ver_str)
    return [int(m) for m in matches] if matches else []

def assess_upgrade_risk(current_ver: str, latest_ver: str, app_name: str) -> Tuple[str, str, str]:
    """
    Avalia o risco da atualização comparando versões major/minor/patch.
    """
    c_lower = current_ver.lower()
    if 'unknown' in c_lower or not current_ver.strip():
        return (
            "Médio Risco (Versão Indefinida)",
            "warning",
            "A versão atualmente instalada não pôde ser determinada pelo winget. Verifique antes de atualizar."
        )

    curr_nums = parse_version_numbers(current_ver)
    late_nums = parse_version_numbers(latest_ver)

    if curr_nums and late_nums:
        # Se a versão major do mais novo for maior
        if late_nums[0] > curr_nums[0]:
            return (
                "Médio/Alto Risco (Major Update)",
                "warning",
                f"Atualização da versão principal ({curr_nums[0]}.x -> {late_nums[0]}.x). Pode conter breaking changes ou alterações estruturais."
            )

    return (
        "Baixo Risco (Update Incremental)",
        "success",
        "Atualização de manutenção/patch contendo correções de bugs, melhorias de desempenho e segurança."
    )

def get_outdated_applications() -> List[Dict[str, Any]]:
    """
    Executa 'winget upgrade --include-unknown' e retorna uma lista estruturada de aplicativos desatualizados.
    """
    print(" -> Consultando o repositório Winget para detectar atualizações de softwares...")
    outdated_apps = []

    try:
        # Executa o winget capture de saída binária para tratar encodings com segurança
        res = subprocess.run(
            ['winget', 'upgrade', '--include-unknown'],
            capture_output=True,
            timeout=45
        )
        
        # Tenta decodificar a saída testando múltiplos encodings comuns no Windows CMD
        stdout = ""
        for encoding in ['utf-8', 'cp850', 'cp1252', 'latin-1']:
            try:
                stdout = res.stdout.decode(encoding)
                if '---' in stdout or 'ID' in stdout:
                    break
            except UnicodeDecodeError:
                continue

        if not stdout:
            stdout = res.stdout.decode('utf-8', errors='replace')

        lines = [line for line in stdout.splitlines() if line.strip()]

        header_idx = -1
        dash_idx = -1
        for idx, line in enumerate(lines):
            if '---' in line:
                dash_idx = idx
                if idx > 0:
                    header_idx = idx - 1
                break

        if dash_idx == -1 or header_idx == -1:
            print(" [Aviso] Nenhuma tabela de atualizações retornada pelo Winget.")
            return []

        header_line = lines[header_idx]

        # Encontra as posições iniciais das colunas no cabeçalho
        idx_id = header_line.find("ID")
        idx_vers = -1
        for v_keyword in ["Versão", "Version", "Vers"]:
            pos = header_line.find(v_keyword)
            if pos != -1 and pos > idx_id:
                idx_vers = pos
                break

        idx_dispon = -1
        for d_keyword in ["Disponível", "Available", "Dispon"]:
            pos = header_line.find(d_keyword)
            if pos != -1 and pos > idx_vers:
                idx_dispon = pos
                break

        idx_origem = -1
        for o_keyword in ["Origem", "Source"]:
            pos = header_line.find(o_keyword)
            if pos != -1 and pos > idx_dispon:
                idx_origem = pos
                break

        # Coleta os locais de instalação mapeados no registro
        installed_locations = get_installed_apps_locations()
        os_drive = os.environ.get("SystemDrive", "C:").upper()
        if not os_drive.endswith("\\"):
            os_drive += "\\"

        for line in lines[dash_idx + 1:]:
            line_str = line.strip()
            if not line_str or line_str.startswith("Os pacotes") or line_str.startswith("Log:") or "atualizações disponíveis" in line_str:
                break

            name, app_id, curr_ver, avail_ver, source = "", "", "", "", "winget"

            if idx_id != -1 and idx_vers != -1 and idx_dispon != -1:
                try:
                    name = line[:idx_id].strip()
                    app_id = line[idx_id:idx_vers].strip()
                    if idx_origem != -1:
                        curr_ver = line[idx_vers:idx_dispon].strip()
                        avail_ver = line[idx_dispon:idx_origem].strip()
                        source = line[idx_origem:].strip()
                    else:
                        curr_ver = line[idx_vers:idx_dispon].strip()
                        avail_ver = line[idx_dispon:].strip()
                except IndexingError:
                    parts = re.split(r'\s{2,}', line.strip())
                    if len(parts) >= 4:
                        name, app_id, curr_ver, avail_ver = parts[0], parts[1], parts[2], parts[3]
            else:
                parts = re.split(r'\s{2,}', line.strip())
                if len(parts) >= 4:
                    name, app_id, curr_ver, avail_ver = parts[0], parts[1], parts[2], parts[3]

            if not name or not app_id or app_id.startswith("---"):
                continue

            # Mapeia drive de instalação
            drive = os_drive
            name_lower = name.lower()
            for loc_name, loc_drive in installed_locations.items():
                if loc_name in name_lower or name_lower in loc_name:
                    drive = loc_drive
                    break

            risk_level, risk_badge, risk_reason = assess_upgrade_risk(curr_ver, avail_ver, name)
            upgrade_cmd = f"winget upgrade --id {app_id}"

            outdated_apps.append({
                'name': name,
                'id': app_id,
                'current_version': curr_ver,
                'latest_version': avail_ver,
                'source': source or 'winget',
                'drive': drive,
                'risk_level': risk_level,
                'risk_badge': risk_badge,
                'risk_reason': risk_reason,
                'upgrade_cmd': upgrade_cmd
            })

    except Exception as e:
        print(f" [Aviso] Não foi possível obter atualizações via Winget: {e}")

    return outdated_apps
