#!/usr/bin/env python3
"""Simulador Modbus TCP de los dos ESP32 (Panel del Operador - Planta 1).

Permite probar el sistema completo en cualquier PC (con o sin Docker) incluso
cuando no se tienen las placas ESP32 físicas conectadas a la red Wi-Fi.

- ESP32 A (Banda + Paro de emergencia): Puerto 5021 (por defecto)
    HR0: Luz del LDR en % (0..100, por defecto 80%)
    HR1: Orden del LED de la banda (0 o 1, escrito por Node-RED)
    HR2: Pulsador de paro de emergencia (0=normal, 1=paro activo)

- ESP32 B (CNC + Potenciómetro de avance): Puerto 5022 (por defecto)
    HR0: Avance del potenciómetro en % (0..100, por defecto 50%)
    HR1: Orden del LED de la CNC (0 o 1, escrito por Node-RED)
"""
import argparse
import socketserver
import struct
import threading
import time

NREG = 16


class MemoriaESP32:
    def __init__(self, nombre, valores_iniciales):
        self.nombre = nombre
        self.hr = [0] * NREG
        for idx, val in valores_iniciales.items():
            self.hr[idx] = val
        self.lock = threading.Lock()


class ManejadorModbus(socketserver.BaseRequestHandler):
    def _leer(self, n):
        buf = b""
        while len(buf) < n:
            parte = self.request.recv(n - len(buf))
            if not parte:
                return None
            buf += parte
        return buf

    def handle(self):
        mem = self.server.memoria
        while True:
            cab = self._leer(7)
            if cab is None:
                return
            tid, pid, largo, unit = struct.unpack(">HHHB", cab)
            pdu = self._leer(largo - 1)
            if pdu is None or not pdu:
                return
            fc = pdu[0]
            try:
                if fc in (3, 4):
                    dir_, cant = struct.unpack(">HH", pdu[1:5])
                    if not (1 <= cant <= NREG) or dir_ + cant > NREG:
                        resp = bytes([fc | 0x80, 2])
                    else:
                        with mem.lock:
                            vals = mem.hr[dir_:dir_ + cant]
                        resp = bytes([fc, 2 * cant]) + struct.pack(">%dH" % cant, *vals)
                elif fc == 6:
                    dir_, val = struct.unpack(">HH", pdu[1:5])
                    if dir_ >= NREG:
                        resp = bytes([fc | 0x80, 2])
                    else:
                        with mem.lock:
                            mem.hr[dir_] = val & 0xFFFF
                        resp = pdu[:5]
                elif fc == 16:
                    dir_, cant, nb = struct.unpack(">HHB", pdu[1:6])
                    if not (1 <= cant <= NREG) or dir_ + cant > NREG or nb != 2 * cant:
                        resp = bytes([fc | 0x80, 2])
                    else:
                        vals = struct.unpack(">%dH" % cant, pdu[6:6 + nb])
                        with mem.lock:
                            mem.hr[dir_:dir_ + cant] = list(vals)
                        resp = pdu[:5]
                else:
                    resp = bytes([fc | 0x80, 1])
            except struct.error:
                resp = bytes([fc | 0x80, 3])
            self.request.sendall(struct.pack(">HHHB", tid, 0, len(resp) + 1, unit) + resp)


class ServidorTCP(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def iniciar_servidor(puerto, memoria):
    srv = ServidorTCP(("0.0.0.0", puerto), ManejadorModbus)
    srv.memoria = memoria
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv


def main():
    ap = argparse.ArgumentParser(description="Simulador Modbus TCP para ESP32 A y ESP32 B")
    ap.add_argument("--puerto-a", type=int, default=5021, help="Puerto Modbus para ESP32 A (defecto: 5021)")
    ap.add_argument("--puerto-b", type=int, default=5022, help="Puerto Modbus para ESP32 B (defecto: 5022)")
    ap.add_argument("--silencio", action="store_true", help="No imprimir estado cada 5 segundos")
    args = ap.parse_args()

    # ESP32 A: HR0=LDR (80%), HR1=LED Banda (0), HR2=Paro Emergencia (0)
    mem_a = MemoriaESP32("ESP32_A_Banda", {0: 80, 1: 0, 2: 0})
    # ESP32 B: HR0=Potenciómetro Avance (50%), HR1=LED CNC (0)
    mem_b = MemoriaESP32("ESP32_B_CNC", {0: 50, 1: 0})

    srv_a = iniciar_servidor(args.puerto_a, mem_a)
    srv_b = iniciar_servidor(args.puerto_b, mem_b)

    print(f"Simulador ESP32 A (Banda+Paro) escuchando en 0.0.0.0:{args.puerto_a} [HR0=LDR%, HR1=LED_Banda, HR2=Paro]")
    print(f"Simulador ESP32 B (CNC+Avance) escuchando en 0.0.0.0:{args.puerto_b} [HR0=Avance%, HR1=LED_CNC]")

    try:
        while True:
            if not args.silencio:
                with mem_a.lock:
                    a0, a1, a2 = mem_a.hr[0], mem_a.hr[1], mem_a.hr[2]
                with mem_b.lock:
                    b0, b1 = mem_b.hr[0], mem_b.hr[1]
                print(
                    f"[ESP32-A :{args.puerto_a}] LDR={a0}% LED_Banda={a1} Paro={a2} | "
                    f"[ESP32-B :{args.puerto_b}] Avance={b0}% LED_CNC={b1}",
                    flush=True,
                )
            time.sleep(5.0)
    except KeyboardInterrupt:
        pass
    finally:
        srv_a.shutdown()
        srv_b.shutdown()


if __name__ == "__main__":
    main()
