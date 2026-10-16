# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

datas = [
    ('src/infrastructure/catalogs/windows_tweaks.json', 'src/infrastructure/catalogs'),
    ('src/infrastructure/catalogs/macos_tweaks.json', 'src/infrastructure/catalogs'),
    ('src/infrastructure/catalogs/safe_cleanup_rules.json', 'src/infrastructure/catalogs'),
]

hiddenimports = [
    'src.domain.entities',
    'src.domain.value_objects',
    'src.domain.ports',
    'src.application.orchestrator',
    'src.application.dtos',
    'src.infrastructure.resources',
    'src.infrastructure.tweaks_adapter',
    'src.infrastructure.persistence.snapshot_repository',
    'src.infrastructure.filesystem.disk_scanner',
    'src.infrastructure.filesystem.autonomous_cleaner',
    'src.infrastructure.windows.platform_adapter',
    'src.infrastructure.macos.platform_adapter',
    'src.presentation.reporters.html_reporter',
    'src.presentation.window.local_server',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='limpeza',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
