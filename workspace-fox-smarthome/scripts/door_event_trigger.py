#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
门状态事件触发器 - HA WebSocket 事件监听
零轮询，事件触发，低延迟
"""

import json
import websocket
import subprocess
import sys
import time
from datetime import datetime

HA_URL = "ws://192.168.28.77:8123/api/websocket"
HA_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI2NzBjNDQzZjdmNTY0YzY3ODAxODkxZThkNjllZGY2YyIsImlhdCI6MTc3MzExNTYwNCwiZXhwIjoyMDg4NDc1NjA0fQ.XnQZK61FYmnLyZZttk8bC4ycDpVj567qqC_458VMtTw"
DOOR_SENSOR = "binary_sensor.lumi_cn_719859620_acn001_contact_state_p_2_1"
DOOR_HANDLER = "/home/zhangyanbo/.openclaw/workspace-fox-smarthome/scripts/door_handler_v2.sh"

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def trigger_door_handler():
    """触发进出门处理脚本"""
    log("🚪 触发进出门处理...")
    try:
        result = subprocess.run(
            ["bash", DOOR_HANDLER],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                log(f"  {line}")
    except subprocess.TimeoutExpired:
        log("❌ 脚本执行超时")
    except Exception as e:
        log(f"❌ 执行失败：{e}")

def on_message(ws, message):
    try:
        data = json.loads(message)
        
        # 处理认证响应
        if data.get('type') in ['auth_required', 'auth_ok']:
            return
        
        # 处理 ping 响应
        if data.get('type') == 'pong':
            return
        
        # 处理事件
        if data.get('type') == 'event':
            event = data.get('event', {})
            if event.get('event_type') == 'state_changed':
                entity_id = event.get('data', {}).get('entity_id', '')
                
                # 只处理门传感器
                if entity_id == DOOR_SENSOR:
                    old_state = event.get('data', {}).get('old_state', {}).get('state', 'unknown')
                    new_state = event.get('data', {}).get('new_state', {}).get('state', 'unknown')
                    
                    log(f"🚪 门状态：{old_state} → {new_state}")
                    
                    # 只在门打开时触发
                    if new_state == 'on' and old_state == 'off':
                        trigger_door_handler()
    except Exception as e:
        log(f"❌ 消息处理错误：{e}")

def on_error(ws, error):
    log(f"❌ WebSocket 错误：{error}")

def on_close(ws, close_status_code, close_msg):
    log(f"🔌 WebSocket 关闭：{close_status_code} {close_msg}")
    # 5 秒后重连
    time.sleep(5)
    connect()

def on_open(ws):
    log("✅ WebSocket 连接成功")
    
    # 发送认证
    auth_msg = {
        "type": "auth",
        "access_token": HA_TOKEN
    }
    ws.send(json.dumps(auth_msg))
    
    # 等待认证完成
    time.sleep(1)
    
    # 订阅状态变化事件
    log(f"📍 订阅门传感器：{DOOR_SENSOR}")
    sub_msg = {
        "id": 2,
        "type": "subscribe_events",
        "event_type": "state_changed"
    }
    ws.send(json.dumps(sub_msg))
    log("✅ 订阅成功，等待事件触发...")
    
    # 定时 ping 保持连接
    def ping_thread():
        while True:
            time.sleep(30)
            try:
                ws.send(json.dumps({"type": "ping"}))
            except:
                break
    
    import threading
    threading.Thread(target=ping_thread, daemon=True).start()

def connect():
    """连接 WebSocket"""
    log("🔍 连接 HA WebSocket...")
    ws = websocket.WebSocketApp(
        HA_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever(ping_interval=0)  # 禁用自动 ping，我们自己控制

if __name__ == "__main__":
    log("🚀 启动门状态事件触发器")
    log("📊 事件触发模式，零轮询，低延迟")
    connect()
