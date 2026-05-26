# HA-SGM-2026 — API Examples

ตัวอย่างการใช้งาน **REST API · WebSocket · Webhook** สำหรับ [HA-SGM-2026 Smart Gate Module](https://github.com/wanchaidiy/ha_sgm_2026_esp32)

---

## ไฟล์ในโปรเจกต์นี้

| ไฟล์ | ประเภท | คำอธิบาย |
|------|--------|---------|
| [`examples/ws_client.html`](examples/ws_client.html) | WebSocket | Browser client — ดูสถานะ sensor แบบ real-time |
| [`examples/webhook_receiver.py`](examples/webhook_receiver.py) | Webhook | Python server รับ POST จาก ESP32 |
| [`examples/api_examples.sh`](examples/api_examples.sh) | REST API | curl commands ครบทุก endpoint |
| [`webhook_line.example.php`](webhook_line.example.php) | Webhook + LINE | รับ webhook แล้วส่ง LINE Notify |

---

## ภาพรวม API ของ ESP32

```
http://<ESP32-IP>/          ← REST API (port 80)
ws://<ESP32-IP>:81/         ← WebSocket (port 81)
```

---

## 1 · WebSocket Client (Browser)

**ไฟล์:** [`examples/ws_client.html`](examples/ws_client.html)

เปิดไฟล์ในเบราว์เซอร์โดยตรง ไม่ต้องติดตั้งอะไร

![ws_client screenshot](https://raw.githubusercontent.com/wanchaidiy/ha-sgm-2026-examples/main/docs/ws_screenshot.png)

**วิธีใช้**

1. เปิดไฟล์ `examples/ws_client.html` ในเบราว์เซอร์
2. กรอก IP ของ ESP32 และ Token (ถ้าตั้งไว้)
3. กด **เชื่อมต่อ** — sensor state อัพเดตอัตโนมัติทุกครั้งที่เปลี่ยน

**Protocol**

```
URL: ws://<IP>:81/
URL (มี token): ws://<IP>:81/?token=<TOKEN>
```

Message ที่ได้รับ:

```json
{
  "open":       false,
  "closed":     true,
  "opening":    false,
  "closing":    false,
  "car_open":   false,
  "car_closed": false
}
```

ทดสอบด้วย terminal:

```bash
npm install -g wscat
wscat -c "ws://192.168.1.100:81/?token=your_token"
```

---

## 2 · Webhook Receiver (Python)

**ไฟล์:** [`examples/webhook_receiver.py`](examples/webhook_receiver.py)

รับ HTTP POST จาก ESP32 ทุกครั้งที่ sensor เปลี่ยนสถานะ

**ติดตั้งและรัน**

```bash
pip install flask
# ตั้ง token ให้ตรงกับ ESP32 (หรือไม่ตั้งก็ได้)
WEBHOOK_TOKEN=your_token python examples/webhook_receiver.py
```

Endpoint: `http://your-server:5000/webhook`

**Payload ที่รับ**

```json
{
  "device": "HA-SGM-2026",
  "sensor": "open",
  "state":  "ON",
  "ip":     "192.168.1.100"
}
```

| ค่า `sensor` | ความหมาย |
|-------------|---------|
| `open`       | ประตูเปิดแล้ว |
| `closed`     | ประตูปิดสนิท |
| `opening`    | กำลังเปิด |
| `closing`    | กำลังปิด |
| `car_open`   | รถผ่านฝั่งเปิด |
| `car_closed` | รถผ่านฝั่งปิด |

**ตั้งค่า Webhook URL ใน ESP32**

ผ่าน WiFiManager Config Portal → กรอก Webhook URL เป็น `http://your-server:5000/webhook`

หรือถ้าใช้ ngrok เพื่อรับจาก internet:

```bash
ngrok http 5000
# แล้วใช้ URL จาก ngrok เช่น https://xxxx.ngrok-free.app/webhook
```

---

## 3 · REST API (curl)

**ไฟล์:** [`examples/api_examples.sh`](examples/api_examples.sh)

```bash
# แก้ค่า IP และ TOKEN ในไฟล์ก่อน แล้วรัน
bash examples/api_examples.sh
```

**Endpoints สรุป**

| Method | Path | Auth | คำอธิบาย |
|--------|------|------|---------|
| `GET`  | `/api/info`   | ไม่ต้อง | ข้อมูลอุปกรณ์ |
| `GET`  | `/api/sensor` | `?token=` | สถานะ sensor ปัจจุบัน |
| `POST` | `/api/press`  | Header `TOKEN` | สั่งเปิด/ปิด/หยุด |
| `GET`  | `/api/token`  | `?secret=` | ดึง token จาก secret |

**ตัวอย่าง**

```bash
IP="192.168.1.100"
TOKEN="your_token"

# ดูสถานะ
curl "http://$IP/api/sensor?token=$TOKEN"

# เปิดประตู
curl -X POST "http://$IP/api/press?button=open" -H "TOKEN: $TOKEN"

# ปิดประตู
curl -X POST "http://$IP/api/press?button=closed" -H "TOKEN: $TOKEN"

# หยุด
curl -X POST "http://$IP/api/press?button=stop" -H "TOKEN: $TOKEN"
```

---

## 4 · LINE Notify Webhook (PHP)

**ไฟล์:** [`webhook_line.example.php`](webhook_line.example.php)

**วิธีใช้**

```bash
cp webhook_line.example.php webhook_line.php
# แก้ไขค่า config ในไฟล์ webhook_line.php
```

แก้ค่าในไฟล์:

```php
define('WEBHOOK_TOKEN',  'token จาก ESP32');
define('LINE_TOKEN',     'LINE Channel Access Token');
define('LINE_SECRET',    'LINE Channel Secret');
define('LINE_GROUP_ID',  'Group ID ที่จะแจ้งเตือน');
define('ESP32_API_URL',  'https://your-esp32-ngrok-url');
```

ฟีเจอร์:
- ESP32 ส่ง webhook → PHP ส่งข้อความเข้ากลุ่ม LINE
- พิมพ์ "เปิดประตู" ในกลุ่ม LINE → PHP สั่ง ESP32 เปิดประตู

---

## การได้ Token

Token สร้างจาก `SHA256(secret + MAC address)` ของ ESP32

```bash
# วิธีที่ 1: ผ่าน API
curl "http://192.168.1.100/api/token?secret=your_secret"

# วิธีที่ 2: ผ่าน WiFiManager Config Portal
# กรอก "API & Webhook Secret" แล้ว Save
```

---

## Firmware

ดู firmware ของ ESP32 ได้ที่ → [ha_sgm_2026_esp32](https://github.com/wanchaidiy/ha_sgm_2026_esp32)

---

## License

MIT
