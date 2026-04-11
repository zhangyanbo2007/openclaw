# OpenClaw Gateway 远程安装指南

## 概述

本文档指导你在家里电脑上安装 OpenClaw Gateway，并连接到当前这台机器 (walle, 192.168.28.92) 的 OpenClaw 服务。

## 前提条件

- 家里电脑已安装 Node.js (v16+)
- 家里电脑能通过网络访问到你的 gateway (192.168.28.92:18789)

---

## 第一步：在家里电脑安装 Gateway

```bash
# 1. 确认 Node.js 已安装
node --version

# 2. 全局安装 OpenClaw
npm install -g openclaw

# 3. 验证安装
openclaw --version
```

---

## 第二步：配置网络连接

根据你的网络环境，选择一种方式：

### 方式 A: 局域网直连 (如果在同一网络)

如果家里电脑和 walle 在同一局域网，直接连接即可：

```bash
# 在家里电脑启动 gateway，指向 walle 的 IP
openclaw gateway --connect ws://192.168.28.92:18789
```

### 方式 B: Tailscale 组网 (推荐)

如果不在同一网络，使用 Tailscale 组建虚拟局域网：

#### 2.1 在 walle (本机) 启用 Tailscale

当前配置显示 Tailscale 是关闭的：
```json
"tailscale": {
  "mode": "off"
}
```

需要先配置 walle 的 Tailscale：
```bash
# 在 walle 上安装并启动 tailscale
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

#### 2.2 在家里电脑安装 Tailscale

```bash
# Linux
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Windows
# 下载安装：https://tailscale.com/download

# macOS
brew install --cask tailscale
tailscale up
```

#### 2.3 获取 Tailscale IP

```bash
# 在 walle 上执行
tailscale ip
# 输出类似：100.x.y.z

# 在家里电脑执行
tailscale ip
# 确认两台机器能互相 ping 通
ping <walle 的 tailscale ip>
```

#### 2.4 使用 Tailscale IP 连接

```bash
# 在家里电脑启动 gateway
openclaw gateway --connect ws://<walle 的 tailscale ip>:18789
```

### 方式 C: 公网 IP + 端口转发

如果你有公网 IP：

1. 在路由器配置端口转发：外部端口 → 192.168.28.92:18789
2. 在家里电脑用公网 IP 连接

---

## 第三步：配对设备

### 3.1 在家里电脑启动 Gateway

```bash
openclaw gateway --connect ws://192.168.28.92:18789
```

启动后会生成一个配对请求，输出类似：
```
Pending pairing request:
Device ID: xxxxxx...
Public Key: xxxxxx...
```

### 3.2 在 walle 批准配对

有 2 种方式：

**方式 1: 使用 Control UI (推荐)**
- 打开浏览器访问：http://192.168.28.92:18789 或使用飞书集成界面
- 在「实例」或「设备」页面看到待批准的配对请求
- 点击批准

**方式 2: 命令行批准**

查看待配对设备：
```bash
cat ~/.openclaw/devices/pending.json
```

编辑 `paired.json` 添加设备，或使用 API 批准。

---

## 第四步：验证连接

### 4.1 在家里电脑验证

```bash
# 检查 gateway 状态
curl http://localhost:18789/health
# 应该返回：{"ok":true,"status":"live"}
```

### 4.2 在 walle 验证

```bash
# 查看已配对设备
cat ~/.openclaw/devices/paired.json

# 查看运行状态
systemctl --user status openclaw-gateway
```

---

## 第五步：配置 systemd 服务 (可选)

如果希望在家里电脑开机自启动：

```bash
# 创建服务文件
nano ~/.config/systemd/user/openclaw-home-gateway.service
```

内容：
```ini
[Unit]
Description=OpenClaw Gateway (Home)
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/bin/node /home/<用户>/.npm-global/lib/node_modules/openclaw/dist/index.js gateway --connect ws://192.168.28.92:18789
Restart=always
RestartSec=5
Environment=HOME=/home/<用户>

[Install]
WantedBy=default.target
```

启用服务：
```bash
systemctl --user daemon-reload
systemctl --user enable openclaw-home-gateway
systemctl --user start openclaw-home-gateway
```

---

## 故障排查

### 问题 1: 连接超时

```bash
# 测试网络连通性
ping 192.168.28.92
telnet 192.168.28.92 18789
```

### 问题 2: 认证失败

检查 token 是否同步：
```bash
# 在 walle 查看当前 token
cat ~/.openclaw/identity/device-auth.json
```

### 问题 3: 防火墙阻止

```bash
# 在 walle 检查防火墙
sudo ufw status
# 如果需要，开放端口
sudo ufw allow 18789/tcp
```

---

## 快速参考

| 项目 | 值 |
|------|-----|
| Gateway 端口 | 18789 |
| Walle IP | 192.168.28.92 |
| 安装命令 | `npm install -g openclaw` |
| 启动命令 | `openclaw gateway --connect ws://<IP>:18789` |
| 健康检查 | `curl http://localhost:18789/health` |

---

## 附录：当前配置信息

### walle 的 Gateway 配置

```json
{
  "gateway": {
    "port": 18789,
    "mode": "local",
    "bind": "loopback",
    "auth": {
      "mode": "token",
      "token": "6d17c7a2b21b08aea7c71ace42a34fbc3bc54c8f27b8f44e"
    },
    "tailscale": {
      "mode": "off"
    }
  }
}
```

### 已配对设备

详见 `~/.openclaw/devices/paired.json`

---

文档生成时间：2026-04-10
OpenClaw 版本：2026.4.9
