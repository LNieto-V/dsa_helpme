@echo off
chcp 65001 >nul
title DSA AE3 - Iniciando con Docker (Planta 1: Banda y CNC)
echo ============================================================================
echo   PROYECTO INTEGRADOR AE3 - DISEÑO DE SISTEMAS AUTOMÁTICOS (GRUPO A)
echo   Planta 1: Banda Transportadora y CNC (Modo Docker)
echo ============================================================================
echo.

where docker >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker no está instalado o no está en el PATH de este PC.
    echo.
    echo Tienes dos opciones:
    echo   1. Instalar Docker Desktop desde https://www.docker.com/products/docker-desktop/
    echo   2. Ejecutar "iniciar_local.bat" para correr todo sin Docker usando Python + Node.js.
    echo.
    pause
    exit /b 1
)

echo [1/3] Construyendo e iniciando contenedores (Node-RED + Gemelo Python + Simulador ESP32)...
docker compose up -d --build
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] No se pudo levantar Docker Compose. Asegúrate de que Docker Desktop esté abierto.
    pause
    exit /b 1
)

echo.
echo [2/3] Esperando 5 segundos a que Node-RED y el Gemelo inicien...
timeout /t 5 /nobreak >nul

echo [3/3] Abriendo navegador en el Editor y Dashboard...
start http://localhost:1880
start http://localhost:1880/dashboard

echo.
echo ============================================================================
echo   SISTEMA EN LÍNEA
echo   - Editor Node-RED:   http://localhost:1880
echo   - Dashboard SCADA:   http://localhost:1880/dashboard
echo   - Gemelo Digital:    127.0.0.1:5020 (Modbus TCP)
echo   - Simulador ESP32 A: 127.0.0.1:5021 (HR0=LDR, HR1=LED Banda, HR2=Paro)
echo   - Simulador ESP32 B: 127.0.0.1:5022 (HR0=Avance, HR1=LED CNC)
echo.
echo   Para ver logs en vivo: docker compose logs -f
echo   Para detener todo:     ejecuta detener_docker.bat
echo ============================================================================
pause
