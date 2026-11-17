#!/usr/bin/env python3
"""Prueba de puesta en marcha de un ESP32 (A o B) por Modbus TCP, desde el PC.

Uso:
  python probar_esp32.py A 192.168.1.57        # ESP32 A: LDR, LED banda, paro
  python probar_esp32.py B 192.168.1.58        # ESP32 B: potenciometro, LED CNC
  python probar_esp32.py A 127.0.0.1 --puerto 5021   # contra el simulador

Lee los registros cada segundo y hace parpadear el LED (HR1) para comprobar el cableado.
Cierre Node-RED antes de usarlo: el ESP32 acepta una sola conexion Modbus a la vez.
"""
import argparse
import socket
import struct
import time


def mb(sock, fc, payload):
    sock.sendall(struct.pack(">HHHB", 1, 0, len(payload) + 2, 1) + bytes([fc]) + payload)
    cab = sock.recv(9)
    if len(cab) < 9:
        raise ConnectionError("sin respuesta")
    resto = sock.recv(max(0, struct.unpack(">H", cab[4:6])[0] - 3))
    if cab[7] & 0x80:
        raise RuntimeError("excepcion Modbus %d" % resto[0] if resto else cab[8])
    return cab[8:9] + resto


def leer(sock, adr, n):
    r = mb(sock, 3, struct.pack(">HH", adr, n))
    return list(struct.unpack(">%dH" % n, r[1:1 + 2 * n]))


def escribir(sock, adr, val):
    mb(sock, 6, struct.pack(">HH", adr, val))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("placa", choices=["A", "B"])
    ap.add_argument("ip")
    ap.add_argument("--puerto", type=int, default=502)
    a = ap.parse_args()

    n = 3 if a.placa == "A" else 2
    nombres = (["LDR %", "LED banda", "PARO (1=activo)"] if a.placa == "A" else ["Avance % (potenciometro)", "LED CNC"])
    print(f"Conectando a ESP32 {a.placa} en {a.ip}:{a.puerto} ...")
    s = socket.create_connection((a.ip, a.puerto), timeout=3)
    print("Conectado. Gire el potenciometro / tape el LDR / pulse el paro. Ctrl+C para salir.\n")
    led = 0
    try:
        while True:
            led ^= 1
            escribir(s, 1, led)                      # parpadeo del LED (HR1)
            vals = leer(s, 0, n)
            print("  ".join(f"{nom}={v}" for nom, v in zip(nombres, vals)))
            time.sleep(1)
    except KeyboardInterrupt:
        escribir(s, 1, 0)
        print("\nLED apagado. Fin.")


if __name__ == "__main__":
    main()
