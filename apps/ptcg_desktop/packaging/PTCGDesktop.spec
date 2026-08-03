# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

packaging_dir = Path(SPECPATH).resolve()
app_dir = packaging_dir.parent
source_dir = app_dir / "src"
package_dir = source_dir / "ptcg_desktop"

hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickControls2",
    "PySide6.QtNetwork",
    "multiprocessing.popen_spawn_win32",
    "multiprocessing.popen_spawn_posix",
]

a = Analysis(
    [str(package_dir / "launcher.py")],
    pathex=[str(source_dir)],
    binaries=[],
    datas=[
        (str(package_dir / "qml"), "ptcg_desktop/qml"),
        (str(package_dir / "assets"), "ptcg_desktop/assets"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineQuick",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtNetworkAuth",
        "PySide6.QtWebChannel",
        "PySide6.QtWebSockets",
    ],
    noarchive=False,
    optimize=1,
)

# QtQml's generic hook discovers every installed QML plugin. The application
# imports only local QtQuick/Controls modules, so remove network-capable modules
# that the generic scan would otherwise carry into the one-folder bundle.
blocked_bundle_markers = (
    "qtwebengine",
    "qt6webengine",
    "qtwebsockets",
    "qt6websockets",
    "qtwebchannel",
    "qt6webchannel",
    "qtwebview",
    "qt6webview",
    "qml/qtnetwork",
    "qml\\qtnetwork",
    "qmlnetworkplugin",
)
a.binaries = [
    entry for entry in a.binaries
    if not any(marker in " ".join(str(part) for part in entry).lower() for marker in blocked_bundle_markers)
]
a.datas = [
    entry for entry in a.datas
    if not any(marker in " ".join(str(part) for part in entry).lower() for marker in blocked_bundle_markers)
]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PTCGHumanClient",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="PTCGHumanClient",
)
