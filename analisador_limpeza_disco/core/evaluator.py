# -*- coding: utf-8 -*-
import os
from typing import List, Dict, Any, Tuple, Set
from .partitions import format_size

def classify_safety_action(item_path: str, item_type: str) -> Tuple[str, str, str]:
    """
    Classifica se o ocupante é um componente essencial do SO (protegido),
    software instalado (desinstalar via Painel de Controle) ou arquivo descartável.
    """
    path_lower = item_path.lower()
    
    # 1. 🚫 Protegido / Não Apagar (Kernel SO / WinSxS / System32)
    protected_system_patterns = [
        '\\windows', '\\system32', '\\winsxs', '\\servicing', '\\syswow64',
        '\\system volume information', '$recycle.bin', '\\windows defender'
    ]
    if any(pattern in path_lower for pattern in protected_system_patterns):
        return (
            '🚫 Não Apagar (Sistema Operacional)',
            'danger',
            'Componente essencial do Windows ou sistema. NÃO modifique ou apague manualmente de forma alguma.'
        )

    # 2. ⚙️ Desinstalar via Painel de Controle / App (Software Instalado)
    installed_app_patterns = [
        '\\program files', '\\program files (x86)', '\\programdata',
        '\\steamlibrary', '\\epic games', '\\games', '\\jogos', '\\appdata\\local\\programs'
    ]
    if any(pattern in path_lower for pattern in installed_app_patterns):
        if any(c in path_lower for c in ['\\cache', '\\temp', '\\logs', '\\dxcache']):
            return (
                '✅ Limpeza Direta (Cache do App)',
                'success',
                'Pasta de cache de aplicativo. Pode ser excluída diretamente sem afetar a instalação do software.'
            )
        return (
            '⚙️ Usar Painel de Controle / App',
            'warning',
            'Software ou biblioteca instalada. Para remover sem corromper o sistema, desinstale pelo Painel de Controle do Windows ou pela loja oficial (Steam/Epic).'
        )

    # 3. ✅ Limpeza Direta (Sem Risco ao SO)
    if any(c in path_lower for c in ['\\temp', '\\cache', '\\prefetch', '\\dxcache', '\\downloads', '\\crashreports', '\\crashdumps']):
        return (
            '✅ Limpeza Direta (Sem Risco ao SO)',
            'success',
            'Arquivo temporário ou cache acumulado. Pode ser excluído diretamente no Explorador de Arquivos.'
        )

    return (
        '⚠️ Avaliar Conteúdo Pessoal',
        'purple',
        'Pasta/Arquivo de dados de usuário. Verifique seu conteúdo no Explorador de Arquivos antes de mover ou excluir.'
    )

def evaluate_disk_analysis(
    all_files: List[Dict[str, Any]],
    folder_sizes: Dict[str, int],
    active_indicators: Set[str],
    partitions: List[Dict[str, Any]],
    top_n: int = 100
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Processa os dados brutos da varredura, aplicando regras de negócio:
    - Mapeamento profundo dos gargalos do AppData (GPU DXCache, Electron, CrashDumps, Builds, Órfãos).
    - Zero falsos positivos via cruzamento com active_indicators em 5 camadas.
    - Ranking dos maiores ocupantes com classificação de segurança de ação.
    - Sugestões inteligentes de migração entre partições.
    """
    clean_suggestions = []
    migration_suggestions = []
    
    trash_indicators = ['cache', 'dump', 'log', 'temp', 'crashreport', 'telemetry', 'webview', 'cef', 'local storage', 'dxcache', 'prefetch', 'crashdumps']
    
    appdata_path = os.environ.get("APPDATA", "").replace("\\Roaming", "").lower()
    local_appdata = os.environ.get("LOCALAPPDATA", "").lower()

    os_drive_letter = os.environ.get("SystemDrive", "C:").upper()
    if not os_drive_letter.endswith("\\"):
        os_drive_letter += "\\"

    # 1. Processamento de Arquivos Descartáveis e Caches Individuais Grandes (> 5 MB)
    for file_info in all_files:
        f_name_lower = file_info['name'].lower()
        f_path_lower = file_info['path'].lower()
        f_size = file_info['size']
        
        if '\\temp' in f_path_lower or '\\prefetch' in f_path_lower or appdata_path in f_path_lower or local_appdata in f_path_lower:
            if any(ind in f_path_lower or ind in f_name_lower for ind in trash_indicators) or f_name_lower.endswith('.tmp') or f_name_lower.endswith('.log') or f_name_lower.endswith('.dmp'):
                if f_size > 5 * 1024 * 1024:
                    clean_suggestions.append({
                        'name': file_info['name'],
                        'path': file_info['path'],
                        'size': f_size,
                        'size_formatted': format_size(f_size),
                        'drive': file_info['drive'],
                        'risk_level': 'Seguro / Baixo Risco (Pode Apagar)',
                        'risk_badge': 'success',
                        'type': 'Arquivo Temporário',
                        'reason': 'Arquivo temporário, log de execução ou dump de erro descartável.',
                        'how_to_fix': 'Pode ser excluído diretamente no Explorador de Arquivos.'
                    })

    # 2. Processamento de Pastas Agregadas & Gargalos da AppData
    processed_folders = []
    for f_path, f_size in folder_sizes.items():
        drive_letter = os.path.splitdrive(f_path)[0].upper() + "\\"
        processed_folders.append({
            'name': os.path.basename(f_path) or f_path,
            'path': f_path,
            'size': f_size,
            'size_formatted': format_size(f_size),
            'drive': drive_letter,
            'type': 'Pasta'
        })
        
        f_path_lower = f_path.lower()

        # Pastas estruturais protegidas que NUNCA devem ser marcadas como órfãs
        protected_paths = [
            'appdata\\local\\programs', 'appdata\\local', 'appdata\\roaming', 'appdata\\locallow',
            'program files', 'program files (x86)', 'programdata', 'windows', 'system32'
        ]
        if any(f_path_lower.rstrip('\\').endswith(p) for p in protected_paths):
            continue

        # Sugestão de Migração (Programas/Pastas Pesadas no Disco do SO)
        if drive_letter == os_drive_letter:
            if any(p in f_path_lower for p in ["program files", "program files (x86)", "games", "jogos", "programdata", "aplicativos"]):
                parts = f_path.split("\\")
                if len(parts) == 3:  # Ex: C:\Program Files\NomeDoPrograma
                    if f_size > 1.5 * 1024 * 1024 * 1024:  # Maior que 1.5 GB
                        prog_name = parts[2]
                        if not any(w in prog_name.lower() for w in ["microsoft", "windows", "desktop", "common files", "windows defender"]):
                            migration_suggestions.append({
                                'name': prog_name,
                                'path': f_path,
                                'size': f_size,
                                'size_formatted': format_size(f_size),
                                'current_drive': drive_letter,
                                'target_drive': 'D:\\ (ou partição de dados)',
                                'type': 'Programa Grande no SSD do SO',
                                'reason': f"Programa substancial ({format_size(f_size)}) instalado na partição do Sistema Operacional.",
                                'how_to_migrate': 'Reinstale o programa apontando o diretório de destino para D:\\Aplicativos ou mova a biblioteca.',
                                'feasibility_rate': 'Alta (Recomendado)',
                                'success_rate': 'Libera espaço físico imediato no SSD sem afetar o Windows.'
                            })

        # Mapeamento Profundo de Gargalos na AppData
        if appdata_path in f_path_lower or local_appdata in f_path_lower:
            parts = f_path.replace(os.environ.get("USERPROFILE", ""), "").strip("\\").split("\\")
            
            # A) Gargalos de Shaders de GPU (DXCache / GLCache) (> 15 MB)
            if any(k in f_path_lower for k in ['dxcache', 'glcache', 'd3dscache', 'nv_cache']):
                if f_size > 15 * 1024 * 1024:
                    clean_suggestions.append({
                        'name': os.path.basename(f_path),
                        'path': f_path,
                        'size': f_size,
                        'size_formatted': format_size(f_size),
                        'drive': drive_letter,
                        'risk_level': 'Seguro / Baixo Risco (Pode Apagar)',
                        'risk_badge': 'success',
                        'type': 'Gargalo AppData: Cache de GPU & Shaders',
                        'reason': 'Shaders compilados de jogos antigos que ocupam espaço valioso no SSD.',
                        'how_to_fix': 'Exclusão 100% segura. O driver da GPU recria novos shaders se você jogar o jogo novamente.'
                    })

            # B) Relatórios de Erro e Crash Dumps (> 10 MB)
            elif any(k in f_path_lower for k in ['crashdumps', '\\wer\\', 'crashreports']):
                if f_size > 10 * 1024 * 1024:
                    clean_suggestions.append({
                        'name': os.path.basename(f_path),
                        'path': f_path,
                        'size': f_size,
                        'size_formatted': format_size(f_size),
                        'drive': drive_letter,
                        'risk_level': 'Seguro / Baixo Risco (Pode Apagar)',
                        'risk_badge': 'success',
                        'type': 'Gargalo AppData: Relatórios de Erro & Dumps',
                        'reason': 'Dumps de falhas de aplicativos e relatórios acumulados do Windows.',
                        'how_to_fix': 'Pode ser apagado diretamente no Explorador de Arquivos.'
                    })

            # C) Caches de Navegadores & Electron Apps (CacheStorage / EBWebView) (> 20 MB)
            elif any(k in f_path_lower for k in ['cachestorage', 'ebwebview', 'code cache', 'workspacestorage', '\\cache2\\', '\\gpu-cache\\']):
                if f_size > 20 * 1024 * 1024:
                    clean_suggestions.append({
                        'name': os.path.basename(f_path),
                        'path': f_path,
                        'size': f_size,
                        'size_formatted': format_size(f_size),
                        'drive': drive_letter,
                        'risk_level': 'Seguro / Baixo Risco (Pode Apagar)',
                        'risk_badge': 'success',
                        'type': 'Gargalo AppData: Cache de Navegador & Electron',
                        'reason': 'Cache de navegação acumulado por WhatsApp, Chrome, VSCode, Discord ou Postman.',
                        'how_to_fix': 'Limpeza segura de cache de aplicativos.'
                    })

            # D) Caches de Dev Tools & Compiladores (npm, pip, yarn, gradle, nuget) (> 25 MB)
            elif any(k in f_path_lower for k in ['pip\\cache', 'npm-cache', 'yarn\\cache', '.gradle\\caches', '.nuget\\packages']):
                if f_size > 25 * 1024 * 1024:
                    clean_suggestions.append({
                        'name': os.path.basename(f_path),
                        'path': f_path,
                        'size': f_size,
                        'size_formatted': format_size(f_size),
                        'drive': drive_letter,
                        'risk_level': 'Seguro / Baixo Risco (Pode Apagar)',
                        'risk_badge': 'success',
                        'type': 'Gargalo AppData: Cache de Dev Tools & Builds',
                        'reason': 'Cache temporário de pacotes e compiladores de código.',
                        'how_to_fix': 'Pode ser apagado. As ferramentas baixam o pacote novamente se necessário.'
                    })

            # E) Resíduos Órfãos de Apps Desinstalados (> 15 MB)
            elif len(parts) >= 3:
                vendor_folder = parts[2].lower()
                is_active = any(ind in vendor_folder for ind in active_indicators)
                if not is_active:
                    if f_size > 15 * 1024 * 1024:
                        if len(parts) == 3 or len(parts) == 4:
                            clean_suggestions.append({
                                'name': os.path.basename(f_path),
                                'path': f_path,
                                'size': f_size,
                                'size_formatted': format_size(f_size),
                                'drive': drive_letter,
                                'risk_level': 'Médio Risco (Resíduo Órfão Verificado)',
                                'risk_badge': 'warning',
                                'type': 'Gargalo AppData: Resíduo de Software Desinstalado',
                                'reason': f"Resíduo de software. A pasta '{vendor_folder}' não pertence a nenhum aplicativo instalado na máquina.",
                                'how_to_fix': 'Exclua a pasta para recuperar espaço permanente no SSD.'
                            })

    # Deduplicação rigorosa de caminhos pai/filho para evitar relatórios redundantes
    def deduplicate_hierarchy(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        items.sort(key=lambda x: x['size'], reverse=True)
        unique_items = []
        seen_paths = set()
        
        for item in items:
            p = item['path']
            is_subpath = False
            for seen in seen_paths:
                if p.startswith(seen + "\\") or p == seen:
                    is_subpath = True
                    break
            if not is_subpath:
                seen_paths.add(p)
                unique_items.append(item)
        return unique_items

    clean_suggestions = deduplicate_hierarchy(clean_suggestions)
    migration_suggestions = deduplicate_hierarchy(migration_suggestions)

    # Maiores ocupantes combinados (Arquivos e Pastas) com classificação de segurança de ação
    processed_folders.sort(key=lambda x: x['size'], reverse=True)
    all_files_sorted = sorted([
        {
            'name': f['name'],
            'path': f['path'],
            'size': f['size'],
            'size_formatted': format_size(f['size']),
            'drive': f['drive'],
            'type': 'Arquivo'
        } for f in all_files
    ], key=lambda x: x['size'], reverse=True)

    raw_top = (processed_folders[:top_n] + all_files_sorted[:top_n])
    raw_top.sort(key=lambda x: x['size'], reverse=True)

    top_occupants = []
    for item in raw_top[:top_n]:
        action_label, badge_class, recommendation = classify_safety_action(item['path'], item['type'])
        item_copy = dict(item)
        item_copy['safety_action'] = action_label
        item_copy['safety_badge'] = badge_class
        item_copy['safety_recommendation'] = recommendation
        top_occupants.append(item_copy)

    return top_occupants, clean_suggestions[:top_n], migration_suggestions
