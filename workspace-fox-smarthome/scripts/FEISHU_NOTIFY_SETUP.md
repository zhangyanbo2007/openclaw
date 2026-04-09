# 飞书通知配置指南

## 📋 功能说明

进出门时自动发送飞书消息通知：
- **进门**：发送"小王子回家了" + 时间 + 猫眼抓图
- **出门**：发送"小王子出门了" + 时间

---

## 🔧 配置步骤

### 步骤 1：授权飞书用户身份

首次使用需要用户授权：

```bash
# 在飞书中发送授权命令
/feishu_auth
```

或者在 OpenClaw 中：
```bash
openclaw feishu-oauth
```

### 步骤 2：测试通知

```bash
cd /home/zhangyanbo/.openclaw/workspace-fox-smarthome/scripts
python3 send_feishu_notify.py enter  # 测试进门通知
python3 send_feishu_notify.py leave  # 测试出门通知
```

### 步骤 3：查看日志

```bash
tail -f /tmp/door_event.log | grep "飞书"
```

---

## 📁 相关文件

| 文件 | 作用 |
|------|------|
| `send_feishu_notify.py` | 飞书通知脚本 |
| `door_handler_v2.sh` | 进出门处理脚本（已集成通知） |

---

## 🎯 通知内容

### 进门通知
```
🏠 小王子回家了！

时间：2026-03-17 22:40:00
🎵 已播放：欢迎啵啵小王子回家！
```

### 出门通知
```
👋 小王子出门了

时间：2026-03-17 22:30:00
```

---

## ⚠️ 常见问题

### Q: 消息发送失败
A: 需要先授权飞书用户身份，运行 `/feishu_auth` 或 `openclaw feishu-oauth`

### Q: 收不到通知
A: 检查：
1. 飞书授权是否有效
2. 事件触发器是否运行：`ps aux | grep door_event_trigger`
3. 查看日志：`tail -f /tmp/door_event.log`

---

## 🔍 手动测试

```bash
# 测试进门通知
python3 /home/zhangyanbo/.openclaw/workspace-fox-smarthome/scripts/send_feishu_notify.py enter

# 测试出门通知
python3 /home/zhangyanbo/.openclaw/workspace-fox-smarthome/scripts/send_feishu_notify.py leave
```

---

## 📞 技术支持

遇到问题可以：
1. 查看脚本日志：`tail -f /tmp/door_event.log`
2. 检查飞书授权状态
3. 重新授权：`openclaw feishu-oauth revoke` 然后重新授权
