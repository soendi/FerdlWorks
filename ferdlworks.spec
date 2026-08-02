# -*- mode: python ; coding: utf-8 -*-
import sys, os, glob

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("assets/ferdlworks_theme.json", "assets"),
        ("assets/ferdlworks.ico", "."),
        ("assets/splashscreen.jpg", "assets"),
        ("assets/signaturesound.wav", "assets"),
        ("assets/signaturesound.ogg", "assets"),
    ],
    hiddenimports=[
        "customtkinter",
        "PIL._tkinter_finder",
        "win32print",
        "packaging",
        "packaging.version",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

# Python 3.x DLL automatisch finden und einbetten
prefix = getattr(sys, "real_prefix", getattr(sys, "base_prefix", sys.prefix))
dlls = glob.glob(os.path.join(prefix, "python3*.dll"))
if not dlls:
    dlls = glob.glob(os.path.join(prefix, "**", "python3*.dll"), recursive=True)
if dlls:
    dll_path = dlls[0]
    print(f"python DLL gefunden: {dll_path}")
    a.binaries += [("python3{}.dll".format(sys.version_info[0]), dll_path, "BINARY")]
else:
    print("Keine python3*.dll gefunden – hoffe PyInstaller findet sie selbst")

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="FerdlWorks",
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
    icon="assets/ferdlworks.ico",
)
