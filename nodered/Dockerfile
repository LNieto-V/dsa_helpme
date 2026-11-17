FROM nodered/node-red:latest

ENV NODE_OPTIONS="--max-old-space-size=192"

USER root
WORKDIR /usr/src/node-red

COPY --chown=node-red:node-red package.json /data_defaults/package.json
COPY --chown=node-red:node-red data/flows.json /data_defaults/flows.json
COPY --chown=node-red:node-red entrypoint.sh /entrypoint_custom.sh

# Compilar paquetes nativos y borrar herramientas de build en la misma capa
RUN apk add --no-cache sqlite-libs \
    && apk add --no-cache --virtual .build-deps python3 make g++ linux-headers sqlite-dev \
    && su-exec node-red npm install --unsafe-perm --no-update-notifier --no-audit --no-fund --omit=dev \
       @flowfuse/node-red-dashboard \
       node-red-contrib-modbus \
       node-red-node-sqlite \
    && npm cache clean --force \
    && apk del .build-deps \
    && rm -rf /tmp/* /root/.npm /home/node-red/.npm \
    && sed -i 's/\r$//' /entrypoint_custom.sh \
    && chmod +x /entrypoint_custom.sh

USER node-red

ENTRYPOINT ["/entrypoint_custom.sh"]
