@echo off
REM VideoCat build script — creates EXE + installer
REM Requires: Python, PyInstaller, Inno Setup 6

setlocal

echo ====================================
echo  VideoCat — Build Script
echo ====================================
echo.

REM Clean previous builds
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [1/3] Building EXE with PyInstaller...
python -m PyInstaller videocat.spec --noconfirm --clean
if errorlevel 1 (
    echo ERROR: PyInstaller failed
    exit /b 1
)
echo.

echo [2/3] EXE built: dist\VideoCat\VideoCat.exe
echo.

REM Check for Inno Setup
set INNO="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %INNO% (
    echo WARNING: Inno Setup not found at %INNO%
    echo Skipping installer build.
    echo Install from https://jrsoftware.org/isdl.php
    goto :end
)

echo [3/3] Building installer with Inno Setup...
%INNO% installer.iss
if errorlevel 1 (
    echo ERROR: Inno Setup failed
    exit /b 1
)

echo.
echo ====================================
echo  Build complete!
echo ====================================
echo  EXE:       dist\VideoCat\VideoCat.exe
echo  Installer: dist\VideoCat_Setup.exe
echo ====================================

:end
endlocal
