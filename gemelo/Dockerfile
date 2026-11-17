FROM python:3.11-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar paho-mqtt opcional por si el usuario activa --mqtt
RUN pip install --no-cache-dir paho-mqtt

COPY planta_gemela.py simulador_esp32.py ./

EXPOSE 5020 5021 5022

CMD ["sh", "-c", "python -u simulador_esp32.py --puerto-a 5021 --puerto-b 5022 & exec python -u planta_gemela.py --planta 1 --puerto 5020 --dt 0.25 --vel 1.0"]
