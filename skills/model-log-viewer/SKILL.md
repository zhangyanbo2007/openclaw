---
name: model-log-viewer
description: 模型日志查看器 - 启动 Web 界面管理模型代理、查看调用历史和会话详情
when: "当用户提到'模型日志'、'日志查看'、'执行模型日志查看'、'查看模型调用'、'打开日志界面'或任何查看模型调用历史的需求"
examples:
  - "执行模型日志查看"
  - "查看模型调用历史"
  - "打开模型日志界面"
  - "看看模型日志"
  - "启动日志查看器"
  - "查看会话历史"
metadata:
 {
   "openclaw": {
     "requires": { "bins": ["bash", "python3"] },
     "emoji": "📋",
     "primaryEnv": "model_proxy"
   }
 }
---

# Model Log Viewer - 模型日志查看器

启动 Web 界面管理模型代理、查看调用历史和会话详情。

## 功能

- **模型代理管理**: 一键启用/关闭任意模型的本地代理，自动分配端口（从 8888 开始）
- **实时日志查看**: 查看代理服务的实时日志输出
- **历史会话浏览**: 按日期查看历史会话记录
- **会话详情**: 查看每个会话的请求和响应详情
- **同步配置**: 将代理配置同步到 openclaw.json 并重启 gateway

## 使用方法

当用户触发此 skill 时，会自动执行以下操作：

### 1. 启动日志查看服务

```bash
cd /home/zhangyanbo/.openclaw/skills/model-log-viewer/scripts
bash start.sh 9001
```

### 2. 提供服务访问地址

启动成功后，服务会在 http://localhost:9001 提供 Web 界面，用户可以在浏览器中：

- 勾选/取消勾选模型来启用/关闭代理
- 点击"全部启用"一键启动所有模型代理
- 点击"全部关闭"停止所有代理
- 点击"同步到 openclaw.json"将配置写入并重启 gateway
- 查看实时日志和历史会话

### 3. 状态检查

检查服务是否已在运行：

```bash
pgrep -f "server.py.*9001"
```

如果服务已在运行，直接返回访问地址即可。

## 配置文件

- **位置**: `/home/zhangyanbo/.openclaw/skills/model-log-viewer/scripts/proxy_config.json`
- **模型来源**: 自动从 `~/.openclaw/openclaw.json` 读取所有 provider 配置
- **过滤规则**: 自动过滤名称包含"本地转发测试"的模型
- **代理端口**: 从 8888 开始自动分配

## 日志目录

- **位置**: `/code/project/deploy_model/logs/`
- **结构**: `logs/YYYY-MM-DD/conv_<session_id>/`

## 注意事项

1. 服务使用 `model_proxy` conda 环境
2. 服务默认监听 9001 端口
3. 如果端口被占用，可指定其他端口：`start.sh 9002`

## 相关命令

| 命令 | 说明 |
|------|------|
| `start.sh [PORT]` | 启动日志查看服务 |
| `pkill -f "server.py"` | 停止服务 |
| `curl http://localhost:9001/api/proxy/status` | 检查代理状态 |
| `curl http://localhost:9001/api/logs/conversations?date=YYYY-MM-DD` | 获取会话列表 |
