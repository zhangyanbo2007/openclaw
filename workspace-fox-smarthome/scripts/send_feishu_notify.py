#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发送飞书进出门通知
用法：python3 send_feishu_notify.py <enter|leave> [image_path]
"""

import sys
import subprocess
import json
from datetime import datetime

def send_notification(event_type, image_path=None):
    """发送飞书通知"""
    
    if event_type == "enter":
        title = "🏠 小王子回家了！"
        content = f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n🎵 已播放：欢迎啵啵小王子回家！"
    else:
        title = "👋 小王子出门了"
        content = f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    message = f"{title}\n\n{content}"
    
    # 使用系统 message 工具发送通知
    try:
        result = subprocess.run(
            ["openclaw", "message", "send", 
             "--channel=feishu", 
             "--target=ou_0671c63ec5781695e9ca1ec20c78f94e",
             f"--message={message}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(f"✅ 飞书通知发送成功：{title}")
        else:
            print(f"⚠️  消息发送失败：{result.stderr[:100]}")
            print(f"   内容：{title}")
            
    except Exception as e:
        print(f"❌ 异常：{e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python3 send_feishu_notify.py <enter|leave> [image_path]")
        sys.exit(1)
    
    event_type = sys.argv[1]
    image_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    send_notification(event_type, image_path)
