"""
HA-SGM-2026 — Simple Webhook Receiver (Python)

รับ POST จาก SGM เมื่อ sensor เปลี่ยนสถานะ
payload: { "device": "...", "sensor": "...", "state": "ON/OFF", "ip": "..." }

ติดตั้ง: pip install flask
รัน    : python webhook_receiver.py
"""

from flask import Flask, request, jsonify
import os, datetime

app = Flask(__name__)

# ใส่ token เดียวกับที่ตั้งใน SGM (หรือปล่อยว่างถ้าไม่ใช้ token)
WEBHOOK_TOKEN = os.environ.get("WEBHOOK_TOKEN", "")

SENSOR_LABELS = {
    "open":       "ประตูเปิดแล้ว",
    "closed":     "ประตูปิดสนิท",
    "opening":    "ประตูกำลังเปิด",
    "closing":    "ประตูกำลังปิด",
    "car_open":   "รถผ่านฝั่งเปิด",
    "car_closed": "รถผ่านฝั่งปิด",
}


@app.route("/webhook", methods=["POST"])
def webhook():
    # ตรวจ token (ถ้ากำหนด)
    if WEBHOOK_TOKEN:
        incoming = request.headers.get("X-Webhook-Token", "")
        if incoming != WEBHOOK_TOKEN:
            return jsonify(error="unauthorized"), 401

    data = request.get_json(silent=True)
    if not data or "sensor" not in data or "state" not in data:
        return jsonify(error="invalid payload"), 400

    sensor = data["sensor"]
    state  = data["state"]
    device = data.get("device", "SmartGate")
    ip     = data.get("ip", "?")
    now    = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    label  = SENSOR_LABELS.get(sensor, sensor)

    print(f"[{now}] {device} ({ip})  →  {label} = {state}")

    # ใส่ logic เพิ่มเติมได้ที่นี่
    # เช่น: ส่ง LINE, Discord, บันทึก DB, ฯลฯ
    if state == "ON":
        on_sensor_on(device, sensor, label, ip)

    return jsonify(ok=True)


def on_sensor_on(device, sensor, label, ip):
    """เรียกเมื่อ sensor เปลี่ยนเป็น ON — ใส่ logic แจ้งเตือนได้ที่นี่"""
    print(f"  ⚡  ALERT: {label}")
    # ตัวอย่างส่ง LINE Notify:
    # import requests
    # requests.post(
    #     "https://notify-api.line.me/api/notify",
    #     headers={"Authorization": "Bearer YOUR_LINE_NOTIFY_TOKEN"},
    #     data={"message": f"\n{label}\nDevice: {device}"},
    # )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Webhook receiver listening on http://0.0.0.0:{port}/webhook")
    if WEBHOOK_TOKEN:
        print(f"Token: {WEBHOOK_TOKEN[:8]}…")
    else:
        print("Token: (none — ไม่มีการตรวจสอบ)")
    app.run(host="0.0.0.0", port=port, debug=False)
