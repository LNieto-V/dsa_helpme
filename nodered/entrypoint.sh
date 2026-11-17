#!/bin/sh
set -e

if [ -f /data_defaults/flows.json ]; then
    cp -f /data_defaults/flows.json /data/flows.json
fi
if [ -f /data_defaults/settings.js ] && [ ! -f /data/settings.js ]; then
    cp /data_defaults/settings.js /data/settings.js
fi

exec /usr/src/node-red/entrypoint.sh "$@"
