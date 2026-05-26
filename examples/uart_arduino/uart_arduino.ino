/*
 * HA-SGM-2026 — UART Client (Arduino)
 *
 * เชื่อม Arduino หรืออุปกรณ์อื่นเข้า SGM HA-SGM-2026 ผ่าน UART
 * ใช้ Serial1 (หรือ SoftwareSerial) คุย กับ SGM, Serial (USB) แสดงผล
 *
 * การต่อสาย:
 *   SGM TX (GPIO1) ──► Arduino RX1
 *   SGM RX (GPIO3) ◄── Arduino TX1
 *   GND ────────────── GND
 *
 * บอด: 115200
 */

// ---------- เลือก Serial สำหรับ SGM ----------
// Arduino Mega / Arduino Due มี Serial1 ในตัว
#define SGM Serial1

// Arduino Uno/Nano — ใช้ SoftwareSerial แทน
// #include <SoftwareSerial.h>
// SoftwareSerial SGM(10, 11);  // RX=10, TX=11
// ---------------------------------------------

// ---- State ที่รับจาก SGM ----
struct GateState {
  bool gate_open   = false;
  bool gate_closed = false;
  bool opening     = false;
  bool closing     = false;
  bool car_open    = false;
  bool car_closed  = false;
  char status[12]  = "unknown";
};

GateState gate;
String    rxBuf = "";

// ---- ส่งคำสั่งไปยัง SGM ----
void sgmOpen()         { SGM.println("open");           }
void sgmClose()        { SGM.println("close");          }
void sgmStop()         { SGM.println("stop");           }
void sgmCarAdd()       { SGM.println("carlink_add");    }
void sgmCarRemove()    { SGM.println("carlink_remove"); }
void sgmReadSensor()   { SGM.println("sensor");         }

// ---- Parse JSON จาก SGM (minimal, ไม่ใช้ library) ----
bool parseBool(const String& json, const char* key) {
  String search = String("\"") + key + "\":";
  int idx = json.indexOf(search);
  if (idx < 0) return false;
  idx += search.length();
  return json.substring(idx, idx + 4) == "true";
}

void parseStatus(const String& json, char* out, size_t outLen) {
  int i = json.indexOf("\"status\":\"");
  if (i < 0) { strlcpy(out, "unknown", outLen); return; }
  i += 10;
  int j = json.indexOf('"', i);
  if (j < 0) { strlcpy(out, "unknown", outLen); return; }
  String val = json.substring(i, j);
  strlcpy(out, val.c_str(), outLen);
}

void handleSgmLine(const String& line) {
  if (line.startsWith("{")) {
    // JSON sensor state
    gate.gate_open   = parseBool(line, "open");
    gate.gate_closed = parseBool(line, "closed");
    gate.opening     = parseBool(line, "opening");
    gate.closing     = parseBool(line, "closing");
    gate.car_open    = parseBool(line, "car_open");
    gate.car_closed  = parseBool(line, "car_closed");
    parseStatus(line, gate.status, sizeof(gate.status));

    Serial.print("[SGM] status="); Serial.print(gate.status);
    Serial.print(" open=");        Serial.print(gate.gate_open);
    Serial.print(" closed=");      Serial.print(gate.gate_closed);
    Serial.print(" car_open=");    Serial.println(gate.car_open);

    onGateStateChanged();

  } else if (line.startsWith("READY")) {
    Serial.print("[SGM] "); Serial.println(line);
    sgmReadSensor();   // ขอสถานะทันทีหลัง SGM พร้อม

  } else if (line.startsWith("OK:") || line.startsWith("ERR:")) {
    Serial.print("[SGM] "); Serial.println(line);
  }
}

// ---- Callback เมื่อ sensor เปลี่ยน — ใส่ logic ของคุณที่นี่ ----
void onGateStateChanged() {
  // ตัวอย่าง: ติด LED ตามสถานะประตู
  // digitalWrite(LED_PIN, gate.gate_open ? HIGH : LOW);

  // ตัวอย่าง: ถ้าประตูเปิด → ทำบางอย่าง
  // if (gate.gate_open) { ... }
}

// ---- อ่านจาก SGM ทีละ char จนเจอ newline ----
void readSgm() {
  while (SGM.available()) {
    char c = (char)SGM.read();
    if (c == '\n' || c == '\r') {
      rxBuf.trim();
      if (rxBuf.length() > 0) {
        handleSgmLine(rxBuf);
        rxBuf = "";
      }
    } else if (rxBuf.length() < 256) {
      rxBuf += c;
    }
  }
}

// ---- รับคำสั่งจาก Serial Monitor (USB) ----
String usbBuf = "";
void readUsb() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      usbBuf.trim();
      usbBuf.toLowerCase();
      if      (usbBuf == "open")           sgmOpen();
      else if (usbBuf == "close")          sgmClose();
      else if (usbBuf == "stop")           sgmStop();
      else if (usbBuf == "carlink_add")    sgmCarAdd();
      else if (usbBuf == "carlink_remove") sgmCarRemove();
      else if (usbBuf == "sensor")         sgmReadSensor();
      else if (usbBuf.length() > 0)
        Serial.println("คำสั่ง: open | close | stop | carlink_add | carlink_remove | sensor");
      usbBuf = "";
    } else if (usbBuf.length() < 32) {
      usbBuf += c;
    }
  }
}

void setup() {
  Serial.begin(115200);
  SGM.begin(115200);
  Serial.println("=== HA-SGM-2026 UART Client ===");
  Serial.println("รอ SGM READY...");
}

void loop() {
  readSgm();
  readUsb();
}
