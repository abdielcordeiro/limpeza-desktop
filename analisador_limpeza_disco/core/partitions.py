# -*- coding: utf-8 -*-
import os
import string
import shutil
from typing import List, Dict, Any

def format_size(size_bytes: float) -> str:
    """Formata o tamanho em bytes para unidades legíveis (Bytes, KB, MB, GB, TB)."""
    if size_bytes < 0:
        return "0.00 Bytes"
    for unit in ['Bytes', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

def get_system_partitions() -> List[Dict[str, Any]]:
    """
    Detecta dinamicamente todas as partições ativas montadas no sistema (C:, D:, E:, etc.),
    obtendo métricas de uso de disco e avaliando o risco de capacidade.
    """
    partitions = []
    system_drive = os.environ.get("SystemDrive", "C:").upper()
    if not system_drive.endswith("\\"):
        system_drive += "\\"

    # Se a plataforma for Windows, iteramos de A a Z
    if os.name == 'nt':
        available_letters = [f"{letter}:\\" for letter in string.ascii_uppercase]
    else:
        available_letters = ['/']

    for mount_point in available_letters:
        if os.path.exists(mount_point):
            try:
                usage = shutil.disk_usage(mount_point)
                total = usage.total
                free = usage.free
                used = usage.used
                percent = (used / total * 100) if total > 0 else 0.0

                is_os_drive = mount_point.upper().startswith(system_drive)
                
                # Heurística de finalidade do disco
                if is_os_drive:
                    role = "Sistema Operacional & Aplicações Vitais"
                elif total > 300 * 1024 * 1024 * 1024:  # >300GB
                    role = "Armazenamento Principal, Jogos & Documentos"
                else:
                    role = "Armazenamento Secundário ou Removível"

                # Avaliação de risco de saúde do disco
                if is_os_drive and percent >= 90.0:
                    health_status = "Risco Crítico de Desempenho"
                    health_class = "danger"
                    health_desc = "O disco do Sistema Operacional está acima de 90% de ocupação. Isso causa lentidão séria no Windows, falhas de paginação e risco de travamentos."
                elif is_os_drive and percent >= 80.0:
                    health_status = "Atenção (Espaço Reduzido)"
                    health_class = "warning"
                    health_desc = "O disco do Sistema Operacional está acima de 80% de capacidade. Recomendável liberar espaço para manter a fluidez do sistema."
                elif percent >= 92.0:
                    health_status = "Partição Quase Cheia"
                    health_class = "warning"
                    health_desc = "Esta partição de dados está com mais de 92% de capacidade utilizada."
                else:
                    health_status = "Saudável"
                    health_class = "success"
                    health_desc = "Espaço em disco com boa margem disponível para uso normal."

                partitions.append({
                    'mount_point': mount_point,
                    'drive_letter': mount_point.rstrip('\\'),
                    'total_bytes': total,
                    'used_bytes': used,
                    'free_bytes': free,
                    'percent_used': round(percent, 1),
                    'total_formatted': format_size(total),
                    'used_formatted': format_size(used),
                    'free_formatted': format_size(free),
                    'is_os_drive': is_os_drive,
                    'role': role,
                    'health_status': health_status,
                    'health_class': health_class,
                    'health_desc': health_desc
                })
            except (PermissionError, OSError):
                continue

    return partitions
