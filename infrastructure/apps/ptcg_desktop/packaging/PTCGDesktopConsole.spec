# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


packaging_dir = Path(SPECPATH).resolve()
app_dir = packaging_dir.parent
source_dir = app_dir / "src"
package_dir = source_dir / "ptcg_desktop"

hiddenimports = collect_submodules("PySide6.QtQml")
hiddenimports += [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickControls2",
    "multiprocessing.popen_spawn_win32",
]

a = Analysis(
    [str(package_dir / "launcher.py")],
    pathex=[str(source_dir)],
    binaries=[],
    datas=[(str(package_dir / "qml"), "ptcg_desktop/qml")],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PySide6.QtWebEngineCore", "PySide6.QtWebEngineQuick", "PySide6.QtWebEngineWidgets"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PTCGHumanClientDebug",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="PTCGHumanClientDebug")
