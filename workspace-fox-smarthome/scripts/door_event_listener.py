#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
门状态事件监听器 - 通过 HA WebSocket 监听门状态变化
事件触发，无轮询，零性能开销
"""

import json
import websocket
import subprocess
import sys

HA_URL = "ws://192.168.28.77:8123/api/websocket"
HA_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI2NzBjNDQzZjdmNTY0YzY3ODAxODkxZThkNjllZGY2YyIsImlhdCI6MTc3MzExNTYwNCwiZXhwIjoyMDg4NDc1NjA0fQ.XnQZK61FYmnLyZZttk8bC4ycDpVj567qqC_458VMtTw"
DOOR_SENSOR = "binary_sensor.lumi_cn_719859620_acn001_contact_state_p_2_1"
DOOR_HANDLER = "/home/zhangyanbo/.openclaw/workspace-fox-smarthome/scripts/door_handler.sh"

def log(msg):
    from datetime import datetime
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def on_message(ws, message):
    data = json.loads(message)
    
    # 处理事件
    if data.get("type") == "event":
        event = data.get("event", {})
        if event.get("event_type") == "state_changed":
            entity_id = event.get("data", {}).get("entity_id")
            if entity_id == DOOR_SENSOR:
                new_state = event.get("data", {}).get("new_state", {}).get("state")
                old_state = event.get("data", {}).get("old_state", {}).get("state")
                
                log(f"🚪 门状态变化：{old_state} → {new_state}")
                
                if new_state == "on" and old_state == "off":
                    log("🚪 门打开了！触发进出门处理...")
                    subprocess.run(["bash", DOOR_HANDLER], capture_output=True, text=True)

def on_error(ws, error):
    log(f"❌ 错误：{error}")

def on_close(ws, close_status_code, close_msg):
    log(f"🔌 WebSocket 关闭：{close_status_code} {close_msg}")

def on_open(ws):
    log("✅ WebSocket 连接成功")
    
    # 认证
    auth_msg = {
        "type": "auth",
        "access_token": HA_TOKEN
    }
    ws.send(json.dumps(auth_msg))

def subscribe(ws):
    log(f"📍 订阅门传感器：{DOOR_SENSOR}")
    
    # 订阅状态变化事件（不过滤 entity_id，在代码中过滤）
    sub_msg = {
        "id": 2,
        "type": "subscribe_events",
        "event_type": "state_changed"
    }
    ws.send(json.dumps(sub_msg))
    log("✅ 订阅成功，等待门状态变化...")
    
    # 发送 ping 保持连接
    ping_msg = {
        "id": 3,
        "type": "ping"
    }
    ws.send(json.dumps(ping_msg))

if __name__ == "__main__":
    log("🔍 启动门状态事件监听器...")
    log("📊 事件触发模式，无轮询，零性能开销")
    
    ws = websocket.WebSocketApp(
        HA_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    # 连接成功后订阅
    ws.run_forever(ping_interval=30, ping_timeout=10)
