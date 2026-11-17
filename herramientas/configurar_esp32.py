#!/usr/bin/env python3
"""Cambia el flujo de Node-RED entre SIMULACION y HARDWARE REAL (ESP32 fisicos).

  python configurar_esp32.py --ip-a 192.168.1.57 --ip-b 192.168.1.58   # usar los 2 ESP32 reales
  python configurar_esp32.py --sim                                      # volver a los simuladores

Modifica nodered/data/flows.json y proyecto_final/NODE-RED/flujo.json:
  - Host/Puerto de los clientes Modbus "ESP32 A" y "ESP32 B"
  - El estado inicial del interruptor "Simulacion ESP32" del tablero
Reinicie Node-RED despues de ejecutarlo.
"""
import argparse
import json
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVOS = [os.path.join(RAIZ, "nodered", "data", "flows.json"),
            os.path.join(RAIZ, "proyecto_final", "NODE-RED", "flujo.json")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ip-a")
    ap.add_argument("--ip-b")
    ap.add_argument("--sim", action="store_true", help="volver a simuladores 127.0.0.1:5021/5022")
    a = ap.parse_args()
    if not a.sim and not (a.ip_a and a.ip_b):
        ap.error("indique --ip-a y --ip-b, o use --sim")

    for ruta in ARCHIVOS:
        if not os.path.exists(ruta):
            continue
        nodos = json.load(open(ruta, encoding="utf-8"))
        for n in nodos:
            if n["id"] == "esp32_a_cli":
                n.update(tcpHost="127.0.0.1" if a.sim else a.ip_a, tcpPort="5021" if a.sim else "502",
                         name="ESP32 A (Simulado :5021)" if a.sim else f"ESP32 A ({a.ip_a}:502)")
            elif n["id"] == "esp32_b_cli":
                n.update(tcpHost="127.0.0.1" if a.sim else a.ip_b, tcpPort="5022" if a.sim else "502",
                         name="ESP32 B (Simulado :5022)" if a.sim else f"ESP32 B ({a.ip_b}:502)")
            elif n["id"] == "ae3_fn_init":
                n["func"] = re.sub(r"const SIMULACION = (true|false);", f"const SIMULACION = {'true' if a.sim else 'false'};", n["func"])
        json.dump(nodos, open(ruta, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print("actualizado:", os.path.relpath(ruta, RAIZ))
    print("Modo:", "SIMULACION" if a.sim else f"HARDWARE REAL  A={a.ip_a}  B={a.ip_b}")
    print("Reinicie Node-RED para aplicar los cambios.")


if __name__ == "__main__":
    main()
