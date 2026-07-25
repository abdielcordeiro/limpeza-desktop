# -*- coding: utf-8 -*-
import os
import sys
import subprocess
from typing import Set, List

try:
    import winreg
except ImportError:
    winreg = None

def get_registry_installed_apps() -> Set[str]:
    """Camada 1: Consulta o Registro do Windows (HKLM e HKCU 32/64 bits) por aplicativos instalados."""
    apps = set()
    if not winreg or os.name != 'nt':
        return apps

    registry_keys = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
    ]

    for hkey, subkey_path in registry_keys:
        try:
            with winreg.OpenKey(hkey, subkey_path) as main_key:
                num_subkeys = winreg.QueryInfoKey(main_key)[0]
                for i in range(num_subkeys):
                    try:
                        subkey_name = winreg.EnumKey(main_key, i)
                        with winreg.OpenKey(main_key, subkey_name) as subkey:
                            # Tenta obter DisplayName
                            try:
                                display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                                if display_name:
                                    name_clean = str(display_name).strip().lower()
                                    apps.add(name_clean)
                                    # Adiciona termos de cada palavra importante
                                    for word in name_clean.replace("-", " ").replace("_", " ").split():
                                        if len(word) > 2:
                                            apps.add(word)
                            except FileNotFoundError:
                                pass

                            # Tenta obter InstallLocation
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

def get_user_programs_folder_apps() -> Set[str]:
    """Camada 2: Mapeia diretórios de programas do usuário (%LOCALAPPDATA%\\Programs)."""
    apps = set()
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if local_appdata:
        programs_path = os.path.join(local_appdata, "Programs")
        if os.path.exists(programs_path):
            try:
                for item in os.listdir(programs_path):
                    item_path = os.path.join(programs_path, item)
                    if os.path.isdir(item_path):
                        apps.add(item.lower())
            except Exception:
                pass
    return apps

def get_start_menu_apps() -> Set[str]:
    """Camada 3: Mapeia atalhos e pastas no Menu Iniciar do Windows."""
    apps = set()
    start_menu_paths = [
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs")
    ]
    for p in start_menu_paths:
        if os.path.exists(p):
            for root, dirs, files in os.walk(p):
                for item in dirs + files:
                    clean_item = os.path.splitext(item)[0].lower()
                    if clean_item and len(clean_item) > 2:
                        apps.add(clean_item)
    return apps

def get_running_process_names() -> Set[str]:
    """Camada 4: Inspeção de processos ativos no momento via tasklist."""
    procs = set()
    if os.name != 'nt':
        return procs
    try:
        output = subprocess.check_output('tasklist', shell=True, stderr=subprocess.DEVNULL).decode('utf-8', errors='ignore')
        for line in output.splitlines():
            line_str = line.strip()
            if '.exe' in line_str.lower():
                parts = line_str.split()
                if parts:
                    proc_name = parts[0].lower().replace('.exe', '')
                    procs.add(proc_name)
    except Exception:
        pass
    return procs

def get_developer_whitelist() -> Set[str]:
    """Camada 5: Whitelist robusta de termos e softwares essenciais para desenvolvedores/usuários."""
    return {
        # Ferramentas Dev & IDEs
        'antigravity', 'postman', 'vscode', 'code', 'vscodium', 'jetbrains', 'pycharm', 'intellij',
        'webstorm', 'clion', 'datagrip', 'goland', 'rider', 'androidstudio', 'eclipse', 'sublime',
        'httptoolkit', 'insomnia', 'dbeaver', 'mongodbcompass', 'mongodb', 'docker', 'docker desktop',
        'git', 'github', 'gitlab', 'node', 'nodejs', 'npm', 'nvm', 'yarn', 'pnpm', 'bun',
        'python', 'pip', 'conda', 'anaconda', 'miniconda', 'rust', 'cargo', 'go', 'golang',
        'java', 'jdk', 'jre', 'gradle', 'maven', 'nuget', 'dotnet', 'dotnet-sdk',

        # Navegadores
        'google', 'chrome', 'mozilla', 'firefox', 'brave', 'edge', 'msedge', 'opera', 'vivaldi',

        # Comunicação & Produtividade
        'discord', 'slack', 'telegram', 'whatsapp', 'zoom', 'teams', 'skype', 'signal',
        'notion', 'obsidian', 'trello', 'figma', 'canva', 'adobe', 'acrobat',

        # Drivers & Sistema
        'microsoft', 'windows', 'packages', 'nvidia', 'intel', 'amd', 'realtek', 'asus',
        'rog', 'lenovo', 'dell', 'hp', 'logitech', 'razer', 'corsair',

        # Games & Launchers
        'steam', 'steamapps', 'epicgames', 'fortnite', 'fortnitegame', 'minecraft', '.minecraft',
        'lunarclient', 'riot games', 'leagueoflegends', 'valorant', 'gog galaxy', 'ubisoft',
        'ea desktop', 'battlenet', 'roblox', 'spotify'
    }

def get_all_active_software_indicators(drives: List[str]) -> Set[str]:
    """
    Consolida as 5 camadas em um único conjunto de termos de softwares ativos para cruzamento
    e garantia de ZERO FALSOS POSITIVOS.
    """
    active_indicators = set()

    # Adiciona Camada 1: Registro
    reg_apps = get_registry_installed_apps()
    active_indicators.update(reg_apps)

    # Adiciona Camada 2: User Programs
    user_prog_apps = get_user_programs_folder_apps()
    active_indicators.update(user_prog_apps)

    # Adiciona Camada 3: Start Menu
    start_apps = get_start_menu_apps()
    active_indicators.update(start_apps)

    # Adiciona Camada 4: Processos Rodando
    running_procs = get_running_process_names()
    active_indicators.update(running_procs)

    # Adiciona Camada 5: Whitelist
    whitelist = get_developer_whitelist()
    active_indicators.update(whitelist)

    # Varredura de pastas de instalação padrão em todos os discos
    sub_paths = [
        "Program Files", "Program Files (x86)", "ProgramData",
        "Games", "Jogos", "Steam", "SteamLibrary", "Epic Games", "Riot Games", "Aplicativos"
    ]
    for drive in drives:
        for sub in sub_paths:
            p = os.path.join(drive, sub)
            if os.path.exists(p):
                try:
                    for item in os.listdir(p):
                        if os.path.isdir(os.path.join(p, item)):
                            active_indicators.add(item.lower())
                except Exception:
                    continue

    return active_indicators
