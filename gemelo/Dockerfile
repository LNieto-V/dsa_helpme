FROM python:3.11-slim

WORKDIR /app

# Instalar paho-mqtt opcional por si el usuario activa --mqtt
RUN pip install --no-cache-dir paho-mqtt

COPY planta_gemela.py simulador_esp32.py ./

EXPOSE 5020 5021 5022

CMD ["python", "-u", "planta_gemela.py", "--planta", "1", "--puerto", "5020"]
