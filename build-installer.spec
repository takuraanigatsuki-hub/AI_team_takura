# -*- mode: python ; coding: utf-8 -*-
"""Установщик AI Team Room — pyinstaller build-installer.spec"""

import os

ROOT = os.path.abspath(os.path.dirname(SPEC))  # noqa: F821
PORTABLE = os.path.join(ROOT, "dist", "AI_Team_Room.exe")

if not os.path.isfile(PORTABLE):
    raise SystemExit("Сначала соберите dist/AI_Team_Room.exe (build-client.spec)")

a = Analysis(  # noqa: F821
    [os.path.join(ROOT, "installer.py")],
    pathex=[ROOT],
    binaries=[],
    datas=[(PORTABLE, ".")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="AI_Team_Room_Setup",
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
)
