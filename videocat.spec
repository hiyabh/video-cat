# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for VideoCat — bundles FFmpeg, Whisper, CTranslate2, CustomTkinter."""

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

block_cipher = None
ROOT = Path(os.path.abspath(SPECPATH))

# Bundle FFmpeg binaries next to the EXE
FFMPEG_DIR = Path(os.environ.get(
    "FFMPEG_DIR",
    r"C:\Users\hiya\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin"
))

binaries = []
if FFMPEG_DIR.exists():
    for exe in ("ffmpeg.exe", "ffprobe.exe"):
        src = FFMPEG_DIR / exe
        if src.exists():
            binaries.append((str(src), "."))

# CTranslate2 DLLs (needed by faster-whisper)
binaries += collect_dynamic_libs("ctranslate2")
binaries += collect_dynamic_libs("tokenizers")
binaries += collect_dynamic_libs("onnxruntime")
binaries += collect_dynamic_libs("av")

# Data files
datas = []
datas += collect_data_files("customtkinter")
datas += collect_data_files("faster_whisper")

# Hidden imports
hiddenimports = [
    "anthropic",
    "openai",
    "customtkinter",
    "faster_whisper",
    "ctranslate2",
    "onnxruntime",
    "tokenizers",
    "av",
    "PIL",
    "PIL._tkinter_finder",
]
hiddenimports += collect_submodules("faster_whisper")
hiddenimports += collect_submodules("ctranslate2")

a = Analysis(
    ["run_gui.py"],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "scipy", "pandas", "notebook", "jupyter", "IPython"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VideoCat",
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
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="VideoCat",
)
