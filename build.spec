# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec-файл для сборки AI Team Room в .exe
Запуск: pyinstaller build.spec
"""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Корень проекта
ROOT = os.path.abspath(os.path.dirname(SPEC))  # noqa: F821

# Данные — статика, знания, конфиги
datas = [
    (os.path.join(ROOT, 'static'),   'static'),
    (os.path.join(ROOT, 'knowledge'), 'knowledge'),
    (os.path.join(ROOT, 'config.json'), '.'),
]

# Подмодули агентов
hidden_imports = [
    'agents',
    'agents.base_agent',
    'agents.architect',
    'agents.backend_dev',
    'agents.frontend_dev',
    'agents.qa_tester',
    'agents.code_reviewer',
    'agents.doc_writer',
    'agents.devops',
    'agents.pm_orchestrator',
    'room',
    'room.room_manager',
    'uvicorn',
    'uvicorn.main',
    'uvicorn.config',
    'uvicorn.protocols.websockets.websockets_impl',
    'uvicorn.lifespan.on',
    'fastapi',
    'anyio',
    'anyio._backends._asyncio',
    'anyio._backends._trio',
    'starlette',
    'starlette.middleware.cors',
    'websockets',
    'httpx',
    'beautifulsoup4',
    'bs4',
    'aiofiles',
    'multipart',
    'webview',
]

a = Analysis(
    [os.path.join(ROOT, 'desktop.py')],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas', 'PIL'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AI_Team_Room',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,            # Без консольного окна (GUI-приложение)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, 'static', 'icons', 'icon.ico'),  # иконка .exe
    version_file=None,
)
