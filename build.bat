@echo off
:: Build the vibe4d Blender addon ZIP.
:: Requirements: Python 3 on PATH (the python.exe that ships with Blender works too)
::
:: Usage:
::   build.bat
::
:: Output: build\vibe4d-blender-<version>.zip

setlocal enabledelayedexpansion

cd /d "%~dp0"

:: Prefer 'python', fall back to 'py' launcher
where python >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON=python
) else (
    where py >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON=py
    ) else (
        echo ERROR: Python not found. Install Python 3 or add Blender's Python to PATH.
        exit /b 1
    )
)

for /f "tokens=*" %%V in ('%PYTHON% --version 2^>^&1') do echo Using: %%V
%PYTHON% build.py

if %errorlevel% neq 0 (
    echo.
    echo Build failed.
    exit /b %errorlevel%
)
