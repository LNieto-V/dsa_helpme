#include <WiFi.h>
#include <ModbusIP_ESP8266.h>

const char* ssid = "TU_RED_WIFI";
const char* password = "TU_CONTRASEÑA";

ModbusIP mb;

// ESP32 A - Banda (Versión básica AE2)
#define PIN_LDR 34          // luz del LDR, 0=oscuro 100=claro
#define HR_LDR 0
#define PIN_LED_BANDA 26    // LED motor de banda
#define HR_LED_BANDA 1

void setup() {
  Serial.begin(115200);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());

  mb.server();
  mb.addHreg(HR_LDR);
  mb.addHreg(HR_LED_BANDA);

  pinMode(PIN_LED_BANDA, OUTPUT);
}

void loop() {
  mb.task();

  static unsigned long ultimaLectura = 0;
  if (millis() - ultimaLectura > 500) {
    ultimaLectura = millis();
    int crudo = analogRead(PIN_LDR);                 // 0 a 4095
    mb.Hreg(HR_LDR, map(crudo, 0, 4095, 0, 100));    // luz del LDR, 0=oscuro 100=claro
  }

  digitalWrite(PIN_LED_BANDA, mb.Hreg(HR_LED_BANDA) ? HIGH : LOW);   // LED motor de banda
}
