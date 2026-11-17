// ============================================================================
// ESP32 B - CNC y consigna de avance (Planta 1, Grupo A)
// Libreria: "modbus-esp8266" (emelianov)  |  Placa: ESP32 Dev Module  |  115200 baudios
//
// CABLEADO (todo a 3,3 V; GND comun):
//   GPIO35 : Potenciometro 10k -> extremos a 3,3V y GND, cursor (pin central) a GPIO35
//   GPIO27 : LED CNC -> GPIO27 ---[220 Ohm]---[LED ->]--- GND
//
// REGISTROS (Unit ID 1, puerto 502):  HR0 = avance % (0..100)   HR1 = orden LED CNC
// Tiempo de mecanizado en Node-RED = 2 s + avance / 10
// ============================================================================
#include <WiFi.h>
#include <ModbusIP_ESP8266.h>

const char* ssid = "TU_RED_WIFI";
const char* password = "TU_CONTRASEÑA";

ModbusIP mb;

#define PIN_POT 35
#define HR_POT 0
#define PIN_LED_CNC 27
#define HR_LED_CNC 1

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
  pinMode(PIN_LED_CNC, OUTPUT);
  digitalWrite(PIN_LED_CNC, LOW);

  conectarWifi();

  mb.server();
  mb.addHreg(HR_POT);
  mb.addHreg(HR_LED_CNC);
}

void loop() {
  mb.task();

  if (WiFi.status() != WL_CONNECTED && millis() - ultimoWifi > 5000) {
    ultimoWifi = millis();
    Serial.println("Wi-Fi perdido, reconectando...");
    WiFi.disconnect();
    WiFi.begin(ssid, password);
  }

  static unsigned long ultimaLectura = 0;
  if (millis() - ultimaLectura > 500) {
    ultimaLectura = millis();
    int crudo = analogRead(PIN_POT);                 // 0 a 4095
    mb.Hreg(HR_POT, map(crudo, 0, 4095, 0, 100));    // avance 0 a 100 %
  }

  digitalWrite(PIN_LED_CNC, mb.Hreg(HR_LED_CNC) ? HIGH : LOW);

  static unsigned long ultimoLog = 0;
  if (millis() - ultimoLog > 2000) {
    ultimoLog = millis();
    Serial.printf("Avance=%d%%  LED_CNC=%d  WiFi=%s\n", mb.Hreg(HR_POT), mb.Hreg(HR_LED_CNC),
                  WiFi.status() == WL_CONNECTED ? "ok" : "caido");
  }
}
