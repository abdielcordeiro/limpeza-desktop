# -*- coding: utf-8 -*-
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple

def scan_paths(target_paths: List[str]) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Varre os caminhos indicados (partições ou subpastas), medindo arquivos individuais
    e acumulando tamanhos de pastas agregadas.
    """
    all_files = []
    folder_sizes = {}
    
    # Diretórios do sistema que devem ser ignorados para evitar travamentos e falsos alertas
    excluded_keywords = [
        '$recycle.bin', 'system volume information', 
        'windows\\winsxs', 'windows\\servicing', 'windows\\installer'
    ]

    for target_path in target_paths:
        print(f" -> [Scanner] Analisando estrutura de: {target_path}")
        
        for root, dirs, files in os.walk(target_path, topdown=True):
            root_lower = root.lower()
            if any(ex in root_lower for ex in excluded_keywords):
                continue

            current_root_size = 0
            
            for f in files:
                fp = os.path.join(root, f)
                try:
                    if os.path.exists(fp) and not os.path.islink(fp):
                        size = os.path.getsize(fp)
                        current_root_size += size
                        
                        all_files.append({
                            'name': f,
                            'path': fp,
                            'size': size,
                            'drive': os.path.splitdrive(fp)[0].upper() + "\\"
                        })
                except (PermissionError, FileNotFoundError, OSError):
                    continue

            # Acumula o tamanho na pasta atual e nos seus pais
            path_obj = Path(root)
            try:
                folder_sizes[str(path_obj)] = folder_sizes.get(str(path_obj), 0) + current_root_size
                for parent in path_obj.parents:
                    p_str = str(parent)
                    if p_str.startswith(target_path):
                        folder_sizes[p_str] = folder_sizes.get(p_str, 0) + current_root_size
            except Exception:
                pass

    return all_files, folder_sizes
