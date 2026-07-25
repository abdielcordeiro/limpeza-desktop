# -*- coding: utf-8 -*-
import os
from typing import Dict, Any
from .partitions import format_size

def analyze_onedrive_impact() -> Dict[str, Any]:
    """
    Analisa a presença do OneDrive no sistema, medindo o consumo real de espaço físico
    em disco e fornecendo recomendações para desvinculação / liberação de espaço local.
    """
    user_profile = os.environ.get("USERPROFILE", os.path.expanduser("~"))
    
    # Locais comuns da pasta do OneDrive no Windows
    possible_onedrive_paths = [
        os.path.join(user_profile, "OneDrive"),
        os.path.join(user_profile, "OneDrive - Personal"),
    ]
    
    # Busca também por subpastas corporativas no OneDrive
    if os.path.exists(user_profile):
        try:
            for item in os.listdir(user_profile):
                if item.lower().startswith("onedrive") and os.path.isdir(os.path.join(user_profile, item)):
                    full_p = os.path.join(user_profile, item)
                    if full_p not in possible_onedrive_paths:
                        possible_onedrive_paths.append(full_p)
        except Exception:
            pass

    found_path = None
    total_consumed_bytes = 0
    file_count = 0

    for path in possible_onedrive_paths:
        if os.path.exists(path):
            found_path = path
            # Calcula o espaço físico ocupado
            try:
                for root, dirs, files in os.walk(path):
                    for f in files:
                        fp = os.path.join(root, f)
                        try:
                            if os.path.exists(fp) and not os.path.islink(fp):
                                size = os.path.getsize(fp)
                                total_consumed_bytes += size
                                file_count += 1
                        except (PermissionError, FileNotFoundError):
                            continue
            except Exception:
                pass
            break  # Foca no primeiro OneDrive principal encontrado

    is_installed = found_path is not None
    is_consuming_heavy_space = total_consumed_bytes > 500 * 1024 * 1024  # > 500 MB

    return {
        'is_installed': is_installed,
        'path': found_path or "Não detectado ou não configurado no perfil padrão",
        'consumed_bytes': total_consumed_bytes,
        'consumed_formatted': format_size(total_consumed_bytes),
        'file_count': file_count,
        'is_consuming_heavy_space': is_consuming_heavy_space,
        'recommendations': [
            {
                'step': '1. Liberar Espaço sem Apagar da Nuvem (Arquivos sob Demanda)',
                'action': 'Abra o Explorador de Arquivos, clique com o botão direito na pasta "OneDrive", e selecione "Liberar espaço" (Free up space).',
                'effect': 'O Windows remove os arquivos físicos do seu SSD mantendo os ícones com a nuvem azul. Os arquivos ficam 100% salvos na nuvem e só baixam quando você clicar.'
            },
            {
                'step': '2. Desvincular a Conta do OneDrive deste Computador',
                'action': 'Abra as Configurações do OneDrive (ícone da nuvem na barra de tarefas ao lado do relógio) -> ícone da engrenagem -> "Configurações" -> Aba "Conta" -> Clicar em "Desvincular este computador" (Unlink this PC).',
                'effect': 'Interrompe a sincronização local. Seus arquivos permanecem seguros em onedrive.live.com e a pasta local para de consumir seu SSD.'
            },
            {
                'step': '3. Desativar a Inicialização Automática',
                'action': 'Pressione Ctrl + Shift + Esc para abrir o Gerenciador de Tarefas -> Aba "Aplicativos de Inicialização" -> Clique com o botão direito no Microsoft OneDrive e selecione "Desabilitar".',
                'effect': 'Impede que o serviço do OneDrive seja carregado na memória RAM ao ligar o computador.'
            }
        ]
    }
