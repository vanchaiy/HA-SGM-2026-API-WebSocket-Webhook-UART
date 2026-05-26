<?php
// ============================================================
//  HA-SGM-2026  —  Webhook → LINE Group Notification
//  สำเนาไฟล์นี้เป็น webhook_line.php แล้วกรอกค่าจริง
// ============================================================

// ==================== CONFIG ====================
define('WEBHOOK_TOKEN',  'YOUR_WEBHOOK_TOKEN_HERE');   // token จาก ESP32 /api/token
define('LINE_TOKEN',     'YOUR_LINE_CHANNEL_ACCESS_TOKEN');
define('LINE_SECRET',    'YOUR_LINE_CHANNEL_SECRET');
define('LINE_GROUP_ID',  'YOUR_LINE_GROUP_ID');
define('NOTIFY_ON_ONLY', true);     // true = แจ้งเฉพาะตอน ON
define('ESP32_API_URL',  'https://your-ngrok-or-ddns-url.example.com');
// ================================================

header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'method not allowed']);
    exit;
}

$raw  = file_get_contents('php://input');
$data = json_decode($raw, true);

if (isset($data['events'])) {
    handleLineEvents($data['events'], $raw);
} else {
    handleEsp32Webhook($data);
}

// ============================================================
//  LINE Messaging API Events
// ============================================================
function handleLineEvents(array $events, string $rawBody): void {
    if (LINE_SECRET !== '') {
        $sig      = $_SERVER['HTTP_X_LINE_SIGNATURE'] ?? '';
        $expected = base64_encode(hash_hmac('sha256', $rawBody, LINE_SECRET, true));
        if (!hash_equals($expected, $sig)) {
            http_response_code(401);
            echo json_encode(['error' => 'invalid signature']);
            exit;
        }
    }

    foreach ($events as $event) {
        $type       = $event['type']         ?? '';
        $source     = $event['source']       ?? [];
        $srcType    = $source['type']        ?? '';
        $groupId    = $source['groupId']     ?? '';
        $userId     = $source['userId']      ?? '';
        $replyToken = $event['replyToken']   ?? '';

        if ($type === 'join' && $srcType === 'group' && $groupId !== '') {
            lineReply($replyToken, "✅ บอทเข้ากลุ่มแล้ว\n📋 Group ID:\n{$groupId}");
        }

        if ($type === 'message'
            && ($event['message']['type'] ?? '') === 'text'
            && trim($event['message']['text'] ?? '') === 'เปิดประตู'
            && $srcType === 'group'
        ) {
            $name = lineGetGroupMemberName($groupId, $userId);
            $now  = (new DateTime('now', new DateTimeZone('Asia/Bangkok')))->format('d/m/Y H:i:s');
            lineReply($replyToken, "🔓 สั่งเปิดประตู\n👤 โดย: {$name}\n🕐 เวลา: {$now}");
            esp32Press('open');
        }
    }

    echo json_encode(['ok' => true]);
}

// ============================================================
//  ESP32 Sensor Webhook
// ============================================================
function handleEsp32Webhook(?array $data): void {
    if (WEBHOOK_TOKEN !== '') {
        $incoming = $_SERVER['HTTP_X_WEBHOOK_TOKEN'] ?? '';
        if ($incoming !== WEBHOOK_TOKEN) {
            http_response_code(401);
            echo json_encode(['error' => 'unauthorized']);
            exit;
        }
    }

    if (!$data || !isset($data['sensor'], $data['state'])) {
        http_response_code(400);
        echo json_encode(['error' => 'invalid payload']);
        exit;
    }

    $sensor = $data['sensor'];
    $state  = $data['state'];
    $device = $data['device'] ?? 'SmartGate';

    if (NOTIFY_ON_ONLY && $state !== 'ON') {
        echo json_encode(['ok' => true, 'skipped' => true]);
        exit;
    }

    $labels = [
        'open'       => ['ON' => '🟢 ประตูเปิดแล้ว',      'OFF' => ''],
        'closed'     => ['ON' => '🔒 ประตูปิดสนิท',        'OFF' => ''],
        'opening'    => ['ON' => '🔄 ประตูกำลังเปิด...',   'OFF' => ''],
        'closing'    => ['ON' => '🔄 ประตูกำลังปิด...',    'OFF' => ''],
        'car_open'   => ['ON' => '🚗 รถผ่านจากฝั่งเปิด',  'OFF' => ''],
        'car_closed' => ['ON' => '🚗 รถผ่านจากฝั่งปิด',   'OFF' => ''],
    ];

    $label = $labels[$sensor][$state] ?? "{$sensor} = {$state}";
    if ($label === '') {
        echo json_encode(['ok' => true, 'skipped' => true]);
        exit;
    }

    $now  = (new DateTime('now', new DateTimeZone('Asia/Bangkok')))->format('d/m/Y H:i:s');
    $text = "{$label}\n---------------\nDevice : {$device}\nTime   : {$now}";
    $result = linePush(LINE_GROUP_ID, $text);
    echo json_encode(['ok' => $result]);
}

// ============================================================
//  LINE Helpers
// ============================================================
function lineReply(string $replyToken, string $text): void {
    if (LINE_TOKEN === '' || $replyToken === '') return;
    lineCurl('https://api.line.me/v2/bot/message/reply', json_encode([
        'replyToken' => $replyToken,
        'messages'   => [['type' => 'text', 'text' => $text]],
    ]));
}

function linePush(string $to, string $text): bool {
    if (LINE_TOKEN === '' || $to === '') return false;
    return lineCurl('https://api.line.me/v2/bot/message/push', json_encode([
        'to'       => $to,
        'messages' => [['type' => 'text', 'text' => $text]],
    ]));
}

function lineGetGroupMemberName(string $groupId, string $userId): string {
    if (LINE_TOKEN === '' || $groupId === '' || $userId === '') return 'ไม่ทราบชื่อ';
    $ch = curl_init("https://api.line.me/v2/bot/group/{$groupId}/member/{$userId}");
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER     => ['Authorization: Bearer ' . LINE_TOKEN],
        CURLOPT_TIMEOUT        => 5,
    ]);
    $res  = curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    if ($code !== 200) return 'ไม่ทราบชื่อ';
    return json_decode($res, true)['displayName'] ?? 'ไม่ทราบชื่อ';
}

function esp32Press(string $button): bool {
    $ch = curl_init(ESP32_API_URL . '/api/press?button=' . urlencode($button));
    curl_setopt_array($ch, [
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => '',
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER     => [
            'Content-Type: application/json',
            'TOKEN: ' . WEBHOOK_TOKEN,
            'ngrok-skip-browser-warning: 1',
        ],
        CURLOPT_TIMEOUT => 8,
    ]);
    $res  = curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    return $code === 200;
}

function lineCurl(string $url, string $payload): bool {
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => $payload,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER     => [
            'Content-Type: application/json',
            'Authorization: Bearer ' . LINE_TOKEN,
        ],
        CURLOPT_TIMEOUT => 10,
    ]);
    $res  = curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    if ($code !== 200) error_log("[LINE] HTTP {$code}: {$res}");
    return $code === 200;
}
