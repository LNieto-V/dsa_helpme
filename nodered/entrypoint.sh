#!/bin/sh
set -e

# Si la carpeta /data montada no tiene flows.json todavía, copiar el flujo por defecto
if [ ! -f /data/flows.json ] && [ -f /data_defaults/flows.json ]; then
    echo "[DSA-AE3] Inicializando /data/flows.json con el flujo preconfigurado..."
    cp /data_defaults/flows.json /data/flows.json
fi

exec /usr/src/node-red/entrypoint.sh "$@"
