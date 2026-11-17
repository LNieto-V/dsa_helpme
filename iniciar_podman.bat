@echo off
chcp 65001 >nul
title DSA AE3 - Iniciando con Podman (Modo Simulación ESP32 + Gemelo)
echo ============================================================================
echo   PROYECTO INTEGRADOR AE3 - DISEÑO DE SISTEMAS AUTOMÁTICOS (GRUPO A)
echo   Planta 1: Banda Transportadora y CNC (Contenedores Podman + Simulación ESP32)
echo ============================================================================
echo.

where podman >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [AVISO] No se detectó "podman" instalado en este PC ^(ni WSL2 activo^).
    echo         Activando automáticamente el MODO SIMULACIÓN LOCAL PORTÁTIL
    echo         ^(Gemelo Python :5020 + Simulador ESP32 A :5021 + ESP32 B :5022 + Node-RED :1880^)...
    echo.
    call "%~dp0iniciar_local.bat"
    exit /b %ERRORLEVEL%
)

echo [1/4] Verificando máquina virtual de Podman...
podman machine inspect >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Inicializando podman machine por primera vez...
    podman machine init --now
) else (
    podman machine start >nul 2>nul
)

echo [2/4] Construyendo imágenes con Podman...
podman build -t dsa-ae3-nodered ./nodered
podman build -t dsa-ae3-gemelo ./gemelo

echo [3/4] Creando Pod compartido "dsa-ae3-pod" ^(comparte 127.0.0.1 entre Node-RED, Gemelo y ESP32 Sim^)...
podman pod rm -f dsa-ae3-pod >nul 2>nul
podman pod create --name dsa-ae3-pod -p 1880:1880 -p 5020:5020 -p 5021:5021 -p 5022:5022

echo [4/4] Iniciando los 3 contenedores dentro del Pod...
podman run -d --name dsa_ae3_nodered --pod dsa-ae3-pod -v "%CD%\nodered\data:/data:Z" dsa-ae3-nodered
podman run -d --name dsa_ae3_gemelo --pod dsa-ae3-pod dsa-ae3-gemelo python -u planta_gemela.py --planta 1 --puerto 5020 --dt 0.25 --vel 1.0
podman run -d --name dsa_ae3_esp32_sim --pod dsa-ae3-pod dsa-ae3-gemelo python -u simulador_esp32.py --puerto-a 5021 --puerto-b 5022

timeout /t 4 /nobreak >nul
start http://localhost:1880
start http://localhost:1880/dashboard

echo.
echo ============================================================================
echo   PODMAN EN LÍNEA (MODO SIMULACIÓN COMPLETA SIN ESP32 FÍSICOS)
echo   - Editor Node-RED:   http://localhost:1880
echo   - Dashboard SCADA:   http://localhost:1880/dashboard
echo   - Gemelo Digital:    127.0.0.1:5020 (Modbus TCP)
echo   - Simulador ESP32 A: 127.0.0.1:5021 (HR0=LDR%, HR1=LED Banda, HR2=Paro)
echo   - Simulador ESP32 B: 127.0.0.1:5022 (HR0=Avance%, HR1=LED CNC)
echo ============================================================================
pause
