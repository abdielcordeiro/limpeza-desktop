# -*- coding: utf-8 -*-
"""Gerenciamento de recursos estáticos e catálogos para execução normal e PyInstaller standalone."""
import os
import sys
from typing import Optional


def get_resource_path(relative_path: str) -> str:
    """
    Retorna o caminho absoluto de um recurso, compatível com:
    1. Execução empacotada em binário único (PyInstaller com sys._MEIPASS).
    2. Execução normal em modo script Python a partir do repositório.
    """
    # 1. Modo PyInstaller (--onefile)
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidate = os.path.join(meipass, relative_path)
        if os.path.exists(candidate):
            return os.path.abspath(candidate)
        # Tenta também apenas com o basename da subpasta se tiver sido adicionado direto
        flat_candidate = os.path.join(meipass, os.path.basename(relative_path))
        if os.path.exists(flat_candidate):
            return os.path.abspath(flat_candidate)

    # 2. Modo Desenvolvimento Normal
    # Raiz do projeto (2 níveis acima de src/infrastructure)
    infra_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(infra_dir))

    candidate_repo = os.path.join(project_root, relative_path)
    if os.path.exists(candidate_repo):
        return os.path.abspath(candidate_repo)

    # Fallback relativo direto
    return os.path.abspath(relative_path)


def get_catalog_path(catalog_filename: str) -> str:
    """Localiza um catálogo JSON dentro de src/infrastructure/catalogs/."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        # Se empacotado via --add-data "src/infrastructure/catalogs:src/infrastructure/catalogs"
        c1 = os.path.join(meipass, "src", "infrastructure", "catalogs", catalog_filename)
        if os.path.exists(c1):
            return os.path.abspath(c1)
        # Se empacotado via --add-data "src/infrastructure/catalogs:catalogs"
        c2 = os.path.join(meipass, "catalogs", catalog_filename)
        if os.path.exists(c2):
            return os.path.abspath(c2)
        # Se na raiz temporária
        c3 = os.path.join(meipass, catalog_filename)
        if os.path.exists(c3):
            return os.path.abspath(c3)

    # Modo script normal
    infra_dir = os.path.dirname(os.path.abspath(__file__))
    local_catalog = os.path.join(infra_dir, "catalogs", catalog_filename)
    return os.path.abspath(local_catalog)
