# -*- mode: python ; coding: utf-8 -*-
"""Тонкий десктоп-клиент (pywebview) — сборка: pyinstaller build-client.spec"""

import os

ROOT = os.path.abspath(os.path.dirname(SPEC))  # noqa: F821

a = Analysis(  # noqa: F821
    [os.path.join(ROOT, "desktop.py")],
    pathex=[ROOT],
    binaries=[],
    datas=[],
    hiddenimports=["webview"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "pandas", "fastapi", "uvicorn"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)  # noqa: F821

icon_path = os.path.join(ROOT, "static", "icons", "icon.ico")
if not os.path.isfile(icon_path):
    icon_path = None

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="AI_Team_Room",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)
