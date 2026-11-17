@echo off
chcp 65001 >nul
title DSA AE3 - Deteniendo contenedores Docker
echo Deteniendo contenedores del proyecto AE3...
docker compose down
echo Contenedores detenidos correctamente. Los datos en nodered/data (flows.json y planta.db) se conservan.
pause
