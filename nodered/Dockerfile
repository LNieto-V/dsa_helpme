FROM nodered/node-red:latest-minimal

ENV NODE_OPTIONS="--max-old-space-size=192"

USER node-red
WORKDIR /usr/src/node-red

# Capas separadas por paquete (sin compilar C++: usa binarios precompilados)
RUN npm install --unsafe-perm --no-update-notifier --no-audit --no-fund --omit=dev @flowfuse/node-red-dashboard \
    && npm cache clean --force

RUN npm install --unsafe-perm --no-update-notifier --no-audit --no-fund --omit=dev node-red-contrib-modbus \
    && npm cache clean --force

RUN npm install --no-update-notifier --no-audit --no-fund --omit=dev node-red-node-sqlite \
    && (cd /usr/src/node-red/node_modules/sqlite3 && node ../prebuild-install/bin.js -r napi || true) \
    && npm cache clean --force

COPY --chown=node-red:node-red package.json /data_defaults/package.json
COPY --chown=node-red:node-red data/flows.json /data_defaults/flows.json
COPY --chown=node-red:node-red entrypoint.sh /entrypoint_custom.sh

USER root
RUN sed -i 's/\r$//' /entrypoint_custom.sh && chmod +x /entrypoint_custom.sh
USER node-red

ENTRYPOINT ["/entrypoint_custom.sh"]
