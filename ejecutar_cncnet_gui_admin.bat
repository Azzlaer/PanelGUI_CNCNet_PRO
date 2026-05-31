@echo off
title CnCNet Tunnel Server GUI - Ejecutar como Administrador
color 0A

REM ============================================================
REM  CnCNet Tunnel Server GUI - Run as Admin
REM  Creditos: ChatGPT OpenAI y Azzlaer para LatinBattle.com
REM ============================================================

set "SCRIPT_NAME=cncnet_server_gui_final_tray.py"
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_PATH=%SCRIPT_DIR%%SCRIPT_NAME%"

echo.
echo ============================================================
echo  CnCNet Tunnel Server GUI - Ejecutar como Administrador
echo ============================================================
echo.

REM Verificar si el script existe
if not exist "%SCRIPT_PATH%" (
    echo [ERROR] No se encontro el archivo:
    echo "%SCRIPT_PATH%"
    echo.
    echo Coloca este BAT en la misma carpeta que:
    echo %SCRIPT_NAME%
    echo.
    pause
    exit /b 1
)

REM Verificar permisos de administrador
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Solicitando permisos de administrador...
    echo.

    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "Start-Process -FilePath '%~f0' -Verb RunAs"

    exit /b
)

echo [OK] Ejecutando con permisos de administrador.
echo.

REM Buscar Python usando py launcher primero
where py >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] Usando Python Launcher: py
    cd /d "%SCRIPT_DIR%"
    py -3 "%SCRIPT_PATH%"
    goto END
)

REM Si no existe py, buscar python
where python >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] Usando python desde PATH
    cd /d "%SCRIPT_DIR%"
    python "%SCRIPT_PATH%"
    goto END
)

echo [ERROR] No se encontro Python instalado o no esta en PATH.
echo.
echo Instala Python desde:
echo https://www.python.org/downloads/
echo.
echo Durante la instalacion marca:
echo [x] Add python.exe to PATH
echo.
pause
exit /b 1

:END
echo.
echo [INFO] El panel se cerro.
pause
