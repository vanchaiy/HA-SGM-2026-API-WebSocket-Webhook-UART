#!/usr/bin/env bash
# HA-SGM-2026 — REST API Examples (curl)
# แก้ค่า IP และ TOKEN ให้ตรงกับอุปกรณ์ของคุณ

IP="192.168.1.100"
TOKEN="your_token_here"   # ว่างได้ถ้าไม่ได้ตั้ง token

# ─────────────────────────────────────────
# GET /api/info — ข้อมูลอุปกรณ์
# ─────────────────────────────────────────
echo "=== Device Info ==="
curl -s "http://$IP/api/info" | python3 -m json.tool

# ─────────────────────────────────────────
# GET /api/sensor — สถานะ sensor ปัจจุบัน
# ─────────────────────────────────────────
echo -e "\n=== Sensor State ==="
curl -s "http://$IP/api/sensor?token=$TOKEN" | python3 -m json.tool

# ─────────────────────────────────────────
# POST /api/press — สั่งควบคุมประตู
# ─────────────────────────────────────────
echo -e "\n=== Press: OPEN ==="
curl -s -X POST "http://$IP/api/press?button=open" \
     -H "TOKEN: $TOKEN" | python3 -m json.tool

echo -e "\n=== Press: CLOSE ==="
curl -s -X POST "http://$IP/api/press?button=closed" \
     -H "TOKEN: $TOKEN" | python3 -m json.tool

echo -e "\n=== Press: STOP ==="
curl -s -X POST "http://$IP/api/press?button=stop" \
     -H "TOKEN: $TOKEN" | python3 -m json.tool

# ─────────────────────────────────────────
# GET /api/token — ดึง token ด้วย secret
# ─────────────────────────────────────────
echo -e "\n=== Get Token ==="
curl -s "http://$IP/api/token?secret=your_secret_here" | python3 -m json.tool

# ─────────────────────────────────────────
# WebSocket — ทดสอบด้วย wscat (npm i -g wscat)
# ─────────────────────────────────────────
# wscat -c "ws://$IP:81/?token=$TOKEN"
