FROM nodered/node-red:latest

USER root
# Herramientas de compilación para módulos nativos (sqlite3 / serialport en Alpine)
RUN apk add --no-cache python3 make g++ linux-headers sqlite

USER node-red
WORKDIR /usr/src/node-red

# Instalar los 3 paquetes requeridos por el curso (Modbus, Dashboard 2.0 y SQLite)
COPY --chown=node-red:node-red package.json /data_defaults/package.json
RUN npm install --unsafe-perm --no-update-notifier --no-fund --only=production \
    @flowfuse/node-red-dashboard \
    node-red-contrib-modbus \
    node-red-node-sqlite

COPY --chown=node-red:node-red data/flows.json /data_defaults/flows.json
COPY --chown=node-red:node-red entrypoint.sh /entrypoint_custom.sh

USER root
RUN sed -i 's/\r$//' /entrypoint_custom.sh && chmod +x /entrypoint_custom.sh
USER node-red

ENTRYPOINT ["/entrypoint_custom.sh"]
