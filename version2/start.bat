@echo off
setlocal enabledelayedexpansion
title MLPMP Full Suite v2.0.4

cd /d "%~dp0"

where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python was not found in your system PATH.
    echo Please install Python 3.8+ and ensure "Add Python to PATH" is checked during setup.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

python run.py %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [NOTICE] Suite terminated with exit code %ERRORLEVEL%.
    pause
)
