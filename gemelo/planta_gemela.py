#!/usr/bin/env python3
"""Gemelo digital del AE3: simula SOLO la planta (sin control).

Uso:  python3 planta_gemela.py --planta 1
      python3 planta_gemela.py --planta 2 --mqtt localhost

Node-RED lo lee y le escribe por Modbus TCP (puerto 5020, Unit ID 1):
  HR0..HR6    sensores analogicos, valor crudo 0..4095 (como un ADC)
  HR7         contador de ciclos del gemelo (sube 1 por ciclo; sirve de marca de tiempo)
  HR8..HR15   entradas digitales, 0 o 1
  HR16..HR23  ordenes del coordinador (Node-RED las escribe con FC6)
"""
import argparse
import json
import math
import random
import socketserver
import struct
import threading
import time

NREG = 64
BASE_AN, BASE_DIG, BASE_CMD = 0, 8, 16


def limitar(v, lo, hi):
    return max(lo, min(hi, v))


class Planta:
    nombre = ""
    analogicas = []   # (nombre, minimo, maximo, unidad)
    digitales = []    # nombre
    ordenes = []      # (nombre, descripcion)

    def __init__(self, rng, dia=240.0):
        self.rng = rng
        self.dia = dia
        self.t = 0.0

    def paso(self, dt, c):
        raise NotImplementedError

    def leer(self, dt, c):
        an, dig = self.paso(dt, c)
        return {n: limitar(an[n], lo, hi) for n, lo, hi, _ in self.analogicas}, dig


class BandaCNC(Planta):
    nombre = "Banda y CNC"
    analogicas = [("pos_pieza_pct", 0, 100, "%"), ("temp_husillo_C", 0, 120, "C"),
                  ("vibracion_mm_s", 0, 10, "mm/s"), ("corriente_banda_A", 0, 5, "A")]
    digitales = ["sensor_entrada", "sensor_cnc", "pieza_terminada"]
    ordenes = [("motor_banda", "0/1"), ("cnc_on", "0/1"), ("refrigeracion", "0/1")]

    def __init__(self, rng, dia=240.0):
        super().__init__(rng, dia)
        self.pieza, self.pos, self.trabajo = False, 0.0, 0.0
        self.espera, self.pulso, self.cnc_prev = 2.0, 0.0, False
        self.temp = 25.0

    def paso(self, dt, c):
        r = self.rng
        if not self.pieza:
            self.espera -= dt
            if self.espera <= 0:
                self.pieza, self.pos, self.trabajo = True, 0.0, 0.0
        mueve = bool(self.pieza and c["motor_banda"] and self.pos < 100)
        if mueve:
            self.pos = min(100.0, self.pos + 20.0 * dt)
        en_cnc = self.pieza and self.pos >= 100
        cnc = bool(c["cnc_on"] and en_cnc)
        if cnc:
            self.trabajo += dt
        self.pulso = max(0.0, self.pulso - dt)
        if self.pieza and en_cnc and self.cnc_prev and not cnc and self.trabajo > 0:
            self.pieza, self.pulso = False, 2.0
            self.espera = r.uniform(3, 8)
        self.cnc_prev = cnc
        enfria = 0.12 if c["refrigeracion"] else 0.04
        self.temp += ((2.0 if cnc else 0.0) - enfria * (self.temp - 25.0)) * dt
        vib = 0.4 + (3.5 if cnc else 0) + (1.0 if mueve else 0) + r.gauss(0, 0.1)
        amp = 0.3 + (1.8 if mueve else 0) + r.gauss(0, 0.05)
        return ({"pos_pieza_pct": self.pos if self.pieza else 0.0, "temp_husillo_C": self.temp,
                 "vibracion_mm_s": vib, "corriente_banda_A": amp},
                {"sensor_entrada": int(self.pieza and self.pos < 10), "sensor_cnc": int(en_cnc),
                 "pieza_terminada": int(self.pulso > 0)})


class TanqueNivel(Planta):
    nombre = "Tanque con bomba y consumo"
    analogicas = [("nivel_pct", 0, 100, "%"), ("caudal_entrada_L_min", 0, 200, "L/min"),
                  ("temp_motor_C", 0, 120, "C"), ("presion_descarga_bar", 0, 5, "bar")]
    digitales = ["nivel_alto_sw", "nivel_bajo_sw", "falla_termica"]
    ordenes = [("bomba", "0/1"), ("valvula_drenaje", "0/1"), ("consumo_pct", "0-100")]

    def __init__(self, rng, dia=240.0):
        super().__init__(rng, dia)
        self.nivel, self.temp, self.disparo = 50.0, 30.0, False

    def paso(self, dt, c):
        r = self.rng
        if self.temp >= 95:
            self.disparo = True
        elif self.temp < 60:
            self.disparo = False
        bomba = bool(c["bomba"]) and not self.disparo
        entra = 2.0 if bomba else 0.0
        sale = limitar(c["consumo_pct"], 0, 100) / 100.0 * 2.0 + (1.5 if c["valvula_drenaje"] else 0.0)
        self.nivel = limitar(self.nivel + (entra - sale) * dt, 0, 100)
        self.temp += ((1.6 if bomba else 0.0) - 0.02 * (self.temp - 25.0)) * dt
        presion = 0.1 + 0.01 * self.nivel + (2.0 if bomba else 0.0) + r.gauss(0, 0.02)
        caudal = (120.0 if bomba else 0.0) + r.gauss(0, 1.0)
        return ({"nivel_pct": self.nivel, "caudal_entrada_L_min": caudal,
                 "temp_motor_C": self.temp, "presion_descarga_bar": presion},
                {"nivel_alto_sw": int(self.nivel >= 95), "nivel_bajo_sw": int(self.nivel <= 5),
                 "falla_termica": int(self.disparo)})


class InspeccionLuz(Planta):
    nombre = "Inspeccion por luz con clasificacion"
    analogicas = [("luz_estacion_pct", 0, 100, "%"), ("brillo_pieza_pct", 0, 100, "%"),
                  ("velocidad_banda_pct", 0, 100, "%"), ("temp_motor_C", 0, 120, "C")]
    digitales = ["pieza_presente", "fin_carrera_ok", "fin_carrera_rech"]
    ordenes = [("banda_on", "0/1"), ("compuerta_ok", "0/1"), ("compuerta_rech", "0/1"),
               ("velocidad_set", "0-100")]

    def __init__(self, rng, dia=240.0):
        super().__init__(rng, dia)
        self.pieza, self.avance, self.luz, self.brillo = False, 0.0, 90.0, 0.0
        self.espera, self.vel, self.temp = 2.0, 0.0, 25.0
        self.pulso_ok = self.pulso_rech = 0.0

    def paso(self, dt, c):
        r = self.rng
        meta = limitar(c["velocidad_set"], 0, 100) if c["banda_on"] else 0.0
        self.vel += (meta - self.vel) * min(1.0, dt / 2.0)
        if not self.pieza:
            if c["banda_on"]:
                self.espera -= dt
            if self.espera <= 0:
                self.pieza, self.avance = True, 0.0
                self.luz = r.uniform(15, 45)
                self.brillo = limitar(r.gauss(60, 22), 0, 100)
        self.pulso_ok = max(0.0, self.pulso_ok - dt)
        self.pulso_rech = max(0.0, self.pulso_rech - dt)
        if self.pieza:
            self.avance += dt * self.vel / 50.0
            if self.avance >= 3.0:
                self.pieza = False
                self.espera = r.uniform(2, 5)
                if c["compuerta_ok"]:
                    self.pulso_ok = 2.0
                elif c["compuerta_rech"]:
                    self.pulso_rech = 2.0
        self.temp += ((0.5 * self.vel / 100.0) - 0.02 * (self.temp - 25.0)) * dt
        return ({"luz_estacion_pct": (self.luz if self.pieza else 90.0) + r.gauss(0, 0.8),
                 "brillo_pieza_pct": self.brillo if self.pieza else 0.0,
                 "velocidad_banda_pct": self.vel, "temp_motor_C": self.temp},
                {"pieza_presente": int(self.pieza), "fin_carrera_ok": int(self.pulso_ok > 0),
                 "fin_carrera_rech": int(self.pulso_rech > 0)})


class DosificacionLotes(Planta):
    nombre = "Dosificacion por lotes con receta"
    analogicas = [("nivel_litros", 0, 12, "L"), ("concentracion_A_pct", 0, 100, "%"),
                  ("temp_mezcla_C", 0, 60, "C"), ("corriente_mezclador_A", 0, 5, "A")]
    digitales = ["nivel_alto_sw", "tanque_vacio_sw", "descarga_abierta_fb"]
    ordenes = [("valvula_A", "0/1"), ("valvula_B", "0/1"), ("mezclador", "0/1"), ("descarga", "0/1")]

    def __init__(self, rng, dia=240.0):
        super().__init__(rng, dia)
        self.va, self.vb, self.homog, self.temp = 0.0, 0.0, 1.0, 25.0

    def paso(self, dt, c):
        r = self.rng
        antes = self.va + self.vb
        if c["valvula_A"]:
            self.va += 0.5 * dt
        if c["valvula_B"]:
            self.vb += 0.5 * dt
        total = self.va + self.vb
        if total > 12.0:
            k = 12.0 / total
            self.va, self.vb, total = self.va * k, self.vb * k, 12.0
        if c["descarga"] and total > 0:
            sacar = min(total, 1.0 * dt)
            k = (total - sacar) / total
            self.va, self.vb = self.va * k, self.vb * k
            total = self.va + self.vb
        if total > antes:
            self.homog *= antes / total if total > 0 else 1.0
        if c["mezclador"]:
            self.homog = min(1.0, self.homog + dt / 4.0)
        else:
            self.homog = max(0.0, self.homog - dt * 0.01)
        real = 100.0 * self.va / total if total > 0.05 else 0.0
        medida = limitar(real + r.gauss(0, (1 - self.homog) * 15.0), 0, 100)
        self.temp += ((0.15 if c["mezclador"] else 0.0) - 0.02 * (self.temp - 25.0)) * dt
        amp = (0.2 + 2.2 * (0.5 + total / 24.0) if c["mezclador"] else 0.0) + r.gauss(0, 0.03)
        return ({"nivel_litros": total, "concentracion_A_pct": medida,
                 "temp_mezcla_C": self.temp, "corriente_mezclador_A": max(0.0, amp)},
                {"nivel_alto_sw": int(total >= 10), "tanque_vacio_sw": int(total <= 0.2),
                 "descarga_abierta_fb": int(bool(c["descarga"]))})


class Parqueadero(Planta):
    nombre = "Parqueadero con conteo y cupo"
    analogicas = [("luz_entrada_pct", 0, 100, "%"), ("luz_salida_pct", 0, 100, "%"),
                  ("co_ppm", 0, 100, "ppm"), ("potencia_kW", 0, 5, "kW"),
                  ("ocupacion_real_carros", 0, 12, "carros")]
    digitales = ["vehiculo_entrada", "vehiculo_salida", "barrera_arriba_fb"]
    ordenes = [("barrera_entrada", "0/1"), ("led_verde", "0/1"), ("led_rojo", "0/1"), ("extractor", "0/1")]
    CAPACIDAD = 12

    def __init__(self, rng, dia=240.0):
        super().__init__(rng, dia)
        self.ocup, self.co = 0, 8.0
        self.t_entrada = self.t_salida = 0.0
        self.espera_in = self.espera_out = 0.0

    def paso(self, dt, c):
        r = self.rng
        if self.t_entrada <= 0 and r.random() < dt / 9.0:
            self.t_entrada = 6.0
        if self.t_entrada > 0:
            if c["barrera_entrada"]:
                if self.ocup < self.CAPACIDAD:
                    self.ocup += 1
                self.t_entrada = 0.0
            else:
                self.t_entrada -= dt
        if self.t_salida <= 0 and self.ocup > 0 and r.random() < dt / 14.0:
            self.t_salida = 2.5
        if self.t_salida > 0:
            self.t_salida -= dt
            if self.t_salida <= 0 and self.ocup > 0:
                self.ocup -= 1
        objetivo = 8.0 + (0.8 if c["extractor"] else 3.5) * self.ocup
        self.co += (objetivo - self.co) * min(1.0, 0.1 * dt)
        kw = 0.4 + 0.12 * self.ocup + (1.1 if c["extractor"] else 0.0) + (0.05 if c["barrera_entrada"] else 0.0)
        return ({"luz_entrada_pct": (10.0 if self.t_entrada > 0 else 95.0) + r.gauss(0, 1.5),
                 "luz_salida_pct": (10.0 if self.t_salida > 0 else 95.0) + r.gauss(0, 1.5),
                 "co_ppm": self.co + r.gauss(0, 0.3), "potencia_kW": kw + r.gauss(0, 0.02),
                 "ocupacion_real_carros": float(self.ocup)},
                {"vehiculo_entrada": int(self.t_entrada > 0), "vehiculo_salida": int(self.t_salida > 0),
                 "barrera_arriba_fb": int(bool(c["barrera_entrada"]))})


class Invernadero(Planta):
    nombre = "Invernadero con luz y ventilacion"
    analogicas = [("luz_pct", 0, 100, "%"), ("temperatura_C", 0, 60, "C"),
                  ("humedad_aire_pct", 0, 100, "%"), ("humedad_suelo_pct", 0, 100, "%")]
    digitales = ["lampara_fb", "ventilador_fb", "deposito_bajo_sw"]
    ordenes = [("lampara", "0/1"), ("ventilador", "0/1"), ("riego", "0/1")]

    def __init__(self, rng, dia=240.0):
        super().__init__(rng, dia)
        self.temp, self.hum, self.suelo, self.agua = 24.0, 65.0, 50.0, 100.0

    def paso(self, dt, c):
        r = self.rng
        self.t += dt
        sol = max(0.0, math.sin(2 * math.pi * (self.t / self.dia - 0.25)))
        t_ext = 20.0 + 10.0 * sol
        k = 0.04 + (0.12 if c["ventilador"] else 0.0)
        ganancia = 0.48 * sol + (0.16 if c["lampara"] else 0.0)
        self.temp += (ganancia - k * (self.temp - t_ext)) * dt
        regando = bool(c["riego"]) and self.agua > 0
        if regando:
            self.agua = max(0.0, self.agua - 0.8 * dt)
            self.suelo = min(100.0, self.suelo + 1.5 * dt)
        self.agua = min(100.0, self.agua + 0.2 * dt)
        self.suelo = max(0.0, self.suelo - (0.05 + 0.004 * max(0.0, self.temp - 20.0)) * dt)
        objetivo = 70.0 - 1.5 * (self.temp - 25.0) + (10.0 if regando else 0.0)
        self.hum = limitar(self.hum + (objetivo - self.hum) * min(1.0, 0.05 * dt), 0, 100)
        luz = limitar(sol * 85.0 + (35.0 if c["lampara"] else 0.0) + r.gauss(0, 1.0), 0, 100)
        return ({"luz_pct": luz, "temperatura_C": self.temp, "humedad_aire_pct": self.hum,
                 "humedad_suelo_pct": self.suelo},
                {"lampara_fb": int(bool(c["lampara"])), "ventilador_fb": int(bool(c["ventilador"])),
                 "deposito_bajo_sw": int(self.agua < 10)})


PLANTAS = {1: BandaCNC, 2: TanqueNivel, 3: InspeccionLuz, 4: DosificacionLotes,
           5: Parqueadero, 6: Invernadero}


def a_crudo(v, minimo, maximo):
    return int(round(limitar((v - minimo) / (maximo - minimo), 0.0, 1.0) * 4095))


class Memoria:
    def __init__(self):
        self.hr = [0] * NREG
        self.lock = threading.Lock()


class Manejador(socketserver.BaseRequestHandler):
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
                    if not (1 <= cant <= 125) or dir_ + cant > NREG:
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
                            mem.hr[dir_] = val
                        resp = pdu[:5]
                elif fc == 16:
                    dir_, cant, nb = struct.unpack(">HHB", pdu[1:6])
                    if not (1 <= cant <= 123) or dir_ + cant > NREG or nb != 2 * cant:
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


class Servidor(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def principal():
    ap = argparse.ArgumentParser(description="Gemelo digital de la planta del AE3")
    ap.add_argument("--planta", type=int, choices=sorted(PLANTAS), required=True)
    ap.add_argument("--puerto", type=int, default=5020)
    ap.add_argument("--mqtt", default=None, help="direccion del broker MQTT (opcional)")
    ap.add_argument("--dt", type=float, default=1.0, help="segundos reales entre ciclos")
    ap.add_argument("--vel", type=float, default=1.0, help="segundos simulados por segundo real")
    ap.add_argument("--dia", type=float, default=240.0, help="duracion simulada de un dia (invernadero)")
    ap.add_argument("--semilla", type=int, default=None)
    ap.add_argument("--silencio", action="store_true")
    a = ap.parse_args()

    planta = PLANTAS[a.planta](random.Random(a.semilla), a.dia)
    nombres_cmd = [n for n, _ in planta.ordenes]
    mem = Memoria()
    srv = Servidor(("0.0.0.0", a.puerto), Manejador)
    srv.memoria = mem
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    cliente = None
    prefijo = "dsa/p%d" % a.planta
    if a.mqtt:
        import paho.mqtt.client as mqtt
        try:
            cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except AttributeError:
            cliente = mqtt.Client()

        def al_mensaje(cl, ud, msg):
            nombre = msg.topic.rsplit("/", 1)[-1]
            if nombre in nombres_cmd:
                try:
                    v = int(float(msg.payload.decode()))
                except ValueError:
                    return
                with mem.lock:
                    mem.hr[BASE_CMD + nombres_cmd.index(nombre)] = max(0, min(65535, v))

        cliente.on_message = al_mensaje
        cliente.connect(a.mqtt, 1883, 60)
        cliente.subscribe(prefijo + "/cmd/#")
        cliente.loop_start()

    print("Planta %d: %s | Modbus TCP en el puerto %d | Ctrl+C para salir" % (a.planta, planta.nombre, a.puerto))
    print("HR0..%d sensores (crudo 0-4095) | HR8..%d digitales | HR16..%d ordenes"
          % (len(planta.analogicas) - 1, 7 + len(planta.digitales), 15 + len(nombres_cmd)))
    ciclo = 0
    try:
        while True:
            with mem.lock:
                c = {n: mem.hr[BASE_CMD + i] for i, n in enumerate(nombres_cmd)}
            an, dig = planta.leer(a.dt * a.vel, c)
            with mem.lock:
                for i, (n, lo, hi, _) in enumerate(planta.analogicas):
                    mem.hr[BASE_AN + i] = a_crudo(an[n], lo, hi)
                for i, n in enumerate(planta.digitales):
                    mem.hr[BASE_DIG + i] = int(dig[n])
                mem.hr[BASE_AN + 7] = ciclo & 0xFFFF
            ciclo += 1
            if cliente:
                cliente.publish(prefijo + "/estado", json.dumps({**{k: round(v, 2) for k, v in an.items()}, **dig}))
            if not a.silencio:
                lin = " ".join("%s=%.1f" % (k, v) for k, v in an.items())
                print(lin + " | " + " ".join("%s=%d" % (k, v) for k, v in dig.items()), flush=True)
            time.sleep(a.dt)
    except KeyboardInterrupt:
        pass
    finally:
        srv.shutdown()


if __name__ == "__main__":
    principal()
