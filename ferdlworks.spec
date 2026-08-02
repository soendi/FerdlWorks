# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets/ferdlworks_theme.json', 'assets'), ('assets/splashscreen.jpg', 'assets'), ('assets/signaturesound.wav', 'assets'), ('assets/signaturesound.ogg', 'assets'), ('assets/ferdlworks.ico', '.')],
    hiddenimports=['PIL._tkinter_finder', 'win32print', 'packaging', 'packaging.version'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FerdlWorks',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\ferdlworks.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FerdlWorks',
)
