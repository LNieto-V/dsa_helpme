@echo off
chcp 65001 >nul
title DSA AE3 - Modo Simulación Local (Sin ESP32 físicos)
echo ============================================================================
echo   PROYECTO INTEGRADOR AE3 - DISEÑO DE SISTEMAS AUTOMÁTICOS (GRUPO A)
echo   Planta 1: Banda Transportadora y CNC (Modo Simulación Completa sin ESP32)
echo ============================================================================
echo.

set PYTHON_CMD=python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    set PYTHON_CMD=py
)

if not exist "nodered\data\node_modules\@flowfuse\node-red-dashboard" (
    echo [1/4] Instalando nodos de Node-RED en nodered\data...
    copy /Y "nodered\package.json" "nodered\data\package.json" >nul
    pushd "nodered\data"
    call npm.cmd install --no-audit --no-fund @flowfuse/node-red-dashboard node-red-contrib-modbus node-red-node-sqlite
    popd
) else (
    echo [1/4] Nodos de Node-RED listos en nodered\data.
)

echo [2/4] Iniciando Gemelo Digital Planta 1 ^(Puerto 5020^)...
start "Gemelo Digital - Planta 1 (5020)" /MIN %PYTHON_CMD% gemelo\planta_gemela.py --planta 1 --puerto 5020 --dt 0.25 --vel 1.0

echo [3/4] Iniciando Simulador Virtual de ESP32 A y B ^(Puertos 5021 y 5022^)...
start "Simulador ESP32 A/B (5021/5022)" /MIN %PYTHON_CMD% gemelo\simulador_esp32.py --puerto-a 5021 --puerto-b 5022

echo [4/4] Iniciando Node-RED en http://localhost:1880 y Dashboard en http://localhost:1880/dashboard ...
timeout /t 3 /nobreak >nul
start http://localhost:1880/dashboard
call "%APPDATA%\npm\node-red.cmd" -u "%~dp0nodered\data" flows.json
