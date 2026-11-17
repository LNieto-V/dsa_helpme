// ============================================================================
// ESP32 A - Banda y paro de emergencia (Planta 1, Grupo A)
// Libreria: "modbus-esp8266" (emelianov)  |  Placa: ESP32 Dev Module  |  115200 baudios
//
// CABLEADO (todo a 3,3 V, nunca 5 V en los pines analogicos; GND comun):
//   GPIO34 : LDR  -> 3,3V ---[LDR]---+--- GPIO34      (divisor con 10 kOhm a GND)
//                                    +---[10k]--- GND
//   GPIO26 : LED banda -> GPIO26 ---[220 Ohm]---[LED ->]--- GND
//   GPIO25 : Pulsador de PARO -> un lado a GPIO25, el otro a GND (pull-up interno)
//
// REGISTROS (Unit ID 1, puerto 502):  HR0 = LDR %   HR1 = orden LED banda   HR2 = PARO (1 = activo)
//
// !! PARO_NC = 1 (contacto normalmente cerrado): con el pulsador SIN conectar, GPIO25 queda en
// !! alto y el firmware reporta PARO ACTIVO. Para probar sin pulsador: ponga un puente
// !! GPIO25 -> GND, o cambie PARO_NC a 0 si su pulsador es normalmente abierto.
// ============================================================================
#include <WiFi.h>
#include <ModbusIP_ESP8266.h>

const char* ssid = "TU_RED_WIFI";
const char* password = "TU_CONTRASEÑA";

ModbusIP mb;

#define PIN_LDR 34
#define HR_LDR 0
#define PIN_LED_BANDA 26
#define HR_LED_BANDA 1
#define PIN_PARO 25
#define HR_PARO 2
#define PARO_NC 1           // 1 = normalmente cerrado (recomendado: un cable suelto tambien da paro)

unsigned long ultimoWifi = 0;

void conectarWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  Serial.print("Conectando a Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LED_BANDA, OUTPUT);
  pinMode(PIN_PARO, INPUT_PULLUP);
  digitalWrite(PIN_LED_BANDA, LOW);

  conectarWifi();

  mb.server();
  mb.addHreg(HR_LDR);
  mb.addHreg(HR_LED_BANDA);
  mb.addHreg(HR_PARO);
}

void loop() {
  mb.task();

  // reconexion Wi-Fi si se cae la red (sin reiniciar la placa)
  if (WiFi.status() != WL_CONNECTED && millis() - ultimoWifi > 5000) {
    ultimoWifi = millis();
    Serial.println("Wi-Fi perdido, reconectando...");
    WiFi.disconnect();
    WiFi.begin(ssid, password);
  }

  static unsigned long ultimaLectura = 0;
  if (millis() - ultimaLectura > 500) {
    ultimaLectura = millis();
    int crudo = analogRead(PIN_LDR);                 // 0 a 4095
    mb.Hreg(HR_LDR, map(crudo, 0, 4095, 0, 100));    // 0 = oscuro, 100 = claro
  }

  // INPUT_PULLUP: el pin lee LOW cuando el pulsador conecta a GND
  bool conectadoAGnd = (digitalRead(PIN_PARO) == LOW);
  bool paro = PARO_NC ? !conectadoAGnd : conectadoAGnd;
  mb.Hreg(HR_PARO, paro ? 1 : 0);

  // seguridad local: con el paro activo el LED de la banda se apaga siempre, aunque Node-RED lo ordene
  digitalWrite(PIN_LED_BANDA, (!paro && mb.Hreg(HR_LED_BANDA)) ? HIGH : LOW);

  static unsigned long ultimoLog = 0;
  if (millis() - ultimoLog > 2000) {
    ultimoLog = millis();
    Serial.printf("LDR=%d%%  LED=%d  PARO=%d  WiFi=%s\n", mb.Hreg(HR_LDR), mb.Hreg(HR_LED_BANDA), paro,
                  WiFi.status() == WL_CONNECTED ? "ok" : "caido");
  }
}
