@echo off
chcp 65001 >nul
title DSA AE3 - Deteniendo Podman
where podman >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Deteniendo y eliminando el Pod "dsa-ae3-pod"...
    podman pod rm -f dsa-ae3-pod
    echo Pod detenido. Los datos en nodered/data se conservan.
) else (
    echo Podman no está instalado. Deteniendo procesos locales si están activos...
    taskkill /F /IM python.exe /FI "WINDOWTITLE eq Gemelo*" >nul 2>nul
    taskkill /F /IM python.exe /FI "WINDOWTITLE eq Simulador*" >nul 2>nul
)
pause
