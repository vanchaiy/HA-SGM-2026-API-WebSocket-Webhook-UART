"""
HA-SGM-2026 — UART Client (Python)

สื่อสารกับ SGM ผ่าน Serial (UART0) บอด 115200

โปรโตคอล:
  ส่ง : open | close | stop | carlink_add | carlink_remove | sensor  (+ newline)
  รับ : OK:<cmd> | ERR:unknown:<cmd> | JSON sensor state
  Auto: SGM ส่ง JSON ทุกครั้งที่ sensor เปลี่ยน (ไม่ต้องถาม)

ติดตั้ง: pip install pyserial
รัน    : python uart_client.py
         python uart_client.py --port COM3          (ระบุ port)
         python uart_client.py --port COM3 --listen  (ฟังอย่างเดียว)
"""

import serial
import serial.tools.list_ports
import threading
import json
import argparse
import time
import sys

BAUD = 115200

SENSOR_LABELS = {
    "open":       "ประตูเปิดแล้ว",
    "closed":     "ประตูปิดสนิท",
    "opening":    "กำลังเปิด",
    "closing":    "กำลังปิด",
    "car_open":   "รถผ่านฝั่งเปิด",
    "car_closed": "รถผ่านฝั่งปิด",
}

COMMANDS = {
    "1": "open",
    "2": "close",
    "3": "stop",
    "4": "carlink_add",
    "5": "carlink_remove",
    "6": "sensor",
}


def list_ports():
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("ไม่พบ Serial Port")
        return []
    print("\nSerial Ports ที่พบ:")
    for i, p in enumerate(ports):
        print(f"  [{i}] {p.device}  — {p.description}")
    return ports


def choose_port(arg_port):
    if arg_port:
        return arg_port
    ports = list_ports()
    if not ports:
        sys.exit(1)
    if len(ports) == 1:
        print(f"\nใช้ port: {ports[0].device}")
        return ports[0].device
    idx = input("\nเลือกหมายเลข port: ").strip()
    try:
        return ports[int(idx)].device
    except (ValueError, IndexError):
        print("ตัวเลือกไม่ถูกต้อง")
        sys.exit(1)


def format_sensor(data: dict) -> str:
    status = data.get("status", "unknown")
    lines = [f"  status  : {status}"]
    for key, label in SENSOR_LABELS.items():
        val = data.get(key)
        if val is None:
            continue
        mark = "ON " if val else "off"
        lines.append(f"  {key:<12}: {mark}  ({label})")
    return "\n".join(lines)


def reader_thread(ser: serial.Serial):
    """อ่านข้อมูลจาก ESP32 ตลอดเวลา (รันใน thread แยก)"""
    buf = b""
    while True:
        try:
            chunk = ser.read(ser.in_waiting or 1)
        except serial.SerialException:
            print("\n[!] Serial disconnected")
            break
        if not chunk:
            continue
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            text = line.decode("utf-8", errors="replace").strip()
            if not text:
                continue
            # JSON sensor state
            if text.startswith("{"):
                try:
                    data = json.loads(text)
                    ts = time.strftime("%H:%M:%S")
                    print(f"\n[{ts}] Sensor update:")
                    print(format_sensor(data))
                    print("> ", end="", flush=True)
                    continue
                except json.JSONDecodeError:
                    pass
            # READY / OK / ERR
            ts = time.strftime("%H:%M:%S")
            print(f"\n[{ts}] {text}")
            print("> ", end="", flush=True)


def send_cmd(ser: serial.Serial, cmd: str):
    ser.write((cmd + "\n").encode())
    print(f"  → ส่ง: {cmd}")


def interactive(ser: serial.Serial):
    print("\nคำสั่งที่ใช้ได้:")
    for k, v in COMMANDS.items():
        label = {
            "open": "เปิดประตู", "close": "ปิดประตู", "stop": "หยุด",
            "carlink_add": "Carlink เพิ่ม", "carlink_remove": "Carlink ลบ",
            "sensor": "อ่าน sensor ทันที",
        }.get(v, v)
        print(f"  {k}) {v:20} — {label}")
    print("  q) ออก")
    print("\n(พิมพ์หมายเลข หรือชื่อคำสั่งโดยตรง เช่น 'open')\n")

    while True:
        try:
            raw = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break
        if not raw:
            continue
        if raw in ("q", "quit", "exit"):
            break
        cmd = COMMANDS.get(raw, raw if raw in COMMANDS.values() else None)
        if cmd:
            send_cmd(ser, cmd)
        else:
            print(f"  ไม่รู้จักคำสั่ง '{raw}' — ลอง: {', '.join(COMMANDS.values())}")


def listen_only(ser: serial.Serial):
    print("โหมด Listen — กด Ctrl+C เพื่อออก\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


def main():
    parser = argparse.ArgumentParser(description="HA-SGM-2026 UART Client")
    parser.add_argument("--port",   help="Serial port เช่น COM3 หรือ /dev/ttyUSB0")
    parser.add_argument("--listen", action="store_true", help="ฟังอย่างเดียว ไม่ส่งคำสั่ง")
    args = parser.parse_args()

    port = choose_port(args.port)

    try:
        ser = serial.Serial(port, BAUD, timeout=0.1)
    except serial.SerialException as e:
        print(f"เปิด port ไม่ได้: {e}")
        sys.exit(1)

    print(f"\nเชื่อมต่อ {port} @ {BAUD} baud")
    print("รอ ESP32 ส่ง READY...\n")

    t = threading.Thread(target=reader_thread, args=(ser,), daemon=True)
    t.start()

    time.sleep(0.5)  # รอ READY message

    if args.listen:
        listen_only(ser)
    else:
        interactive(ser)

    ser.close()
    print("ปิดการเชื่อมต่อ")


if __name__ == "__main__":
    main()
