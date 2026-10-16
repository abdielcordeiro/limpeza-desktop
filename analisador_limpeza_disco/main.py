# -*- coding: utf-8 -*-
"""
Wrapper de retrocompatibilidade para analisador_limpeza_disco/main.py.
Redireciona para a nova arquitetura multiplataforma (Clean Architecture + Hexagonal) na raiz.
"""
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from main import main as root_main


def main() -> int:
    return root_main()


if __name__ == "__main__":
    sys.exit(main())
