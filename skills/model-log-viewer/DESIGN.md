# 模型日志查看器 - 设计文档

## 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     用户界面 (index.html)                        │
│  - 模型列表展示                                                  │
│  - 启用/禁用开关                                                 │
│  - 同步配置按钮                                                  │
│  - 日志查看界面                                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↕ HTTP (port 9001)
┌─────────────────────────────────────────────────────────────────┐
│                    Web 服务 (server.py)                          │
│  - API 端点：/api/proxy/start, /api/proxy/stop, /api/sync       │
│  - 代理状态检测                                                  │
│  - 配置文件同步                                                  │
│  - Gateway 重启控制                                              │
└─────────────────────────────────────────────────────────────────┘
                              ↕ 启动/停止
┌─────────────────────────────────────────────────────────────────┐
│                 代理进程 (model_proxy.py)                        │
│  - 监听端口 8888-8899                                           │
│  - 转发请求到后端 API                                            │
│  - 记录会话日志到 model-logs/                                    │
└─────────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. server.py - Web 服务主进程

**职责**：
- 提供 Web 界面（9001 端口）
- 代理进程管理（启动/停止/状态检测）
- 配置同步（proxy_config.json ↔ openclaw.json）
- 健康检查

**关键函数**：

| 函数 | 功能 | 说明 |
|------|------|------|
| `start_proxy()` | 启动代理进程 | 检查 API 密钥→启动进程→健康测试 |
| `test_proxy()` | 测试代理 | 发送请求到本地代理端口验证转发 |
| `sync_to_openclaw_post()` | 同步配置 | 更新 openclaw.json 并重启 gateway |
| `restart_gateway()` | 重启 gateway | 带健康检查，最多等待 30 秒 |
| `get_proxy_status()` | 获取状态 | 检查端口占用情况 |

### 2. model_proxy.py - 代理转发服务

**职责**：
- 接收 OpenClaw/ClaudeCode 的请求
- 根据模型配置转发到后端 API
- 记录完整会话日志（请求 + 响应）

**日志格式**：
```
model-logs/
├── 2026-04-16/
│   └── conv_<session_id>/
│       ├── index.json        # 会话元数据
│       └── <timestamp>.json  # 对话记录
```

**模型路由逻辑**：
1. 完整匹配：`custom-dashscope-aliyuncs-com/qwen3.6-plus`
2. localproxy 格式：`localproxy-8889/qwen3.6-plus`
3. 简化后缀匹配：`qwen3.6-plus` → 匹配 `*/qwen3.6-plus`

### 3. index.html - 前端界面

**核心功能**：
- 智能体类型自动检测（OpenClaw/Claude Code）
- 模型列表渲染（按 provider 分组）
- 代理状态实时刷新
- 配置同步确认

**状态检测流程**：
```
页面加载 → detectAgentType() → loadAgentModels() → checkStatus() → renderModelList()
```

### 4. proxy_config.json - 代理配置文件

**结构**：
```json
{
  "enabled_models": [
    "vllm-5555/qwen3.5-27b",
    "custom-dashscope-aliyuncs-com/qwen3.6-plus"
  ],
  "model_port_mapping": {
    "vllm-5555/qwen3.5-27b": 8893,
    "custom-dashscope-aliyuncs-com/qwen3.6-plus": 8889
  },
  "logs_dir": "/home/zhangyanbo/.openclaw/model-logs",
  "session": {
    "time_window_seconds": 60,
    "similarity_threshold": 0.8
  }
}
```

## 关键流程

### 代理启动流程

```
用户勾选模型
    ↓
前端调用 /api/proxy/start
    ↓
后端检查 API 密钥（openclaw.json 或 agents/main/agent/models.json）
    ↓
启动 model_proxy.py 进程
    ↓
等待 2 秒
    ↓
检查进程是否存活
    ↓
发送测试请求到本地代理端口
    ↓
代理转发到后端 API
    ↓
返回测试结果
```

### 配置同步流程

```
用户点击"同步到智能体配置"
    ↓
读取 proxy_config.json 获取 enabled_models
    ↓
过滤 model_port_mapping（只保留已启用的）
    ↓
读取 openclaw.json
    ↓
备份原文件（带时间戳）
    ↓
计算需要删除的 localproxy-* 配置
    ↓
删除旧配置（models.providers, auth.profiles, agents.defaults.models）
    ↓
添加新配置
    ↓
写回 openclaw.json
    ↓
重启 gateway（带健康检查，最多 30 秒）
```

## 重要修复记录

### 2026-04-16 修复

1. **端口检测逻辑修复**（start.sh）
   - 问题：只检查进程 PID，不检查端口是否监听
   - 修复：使用 `ss`/`netstat` 检查端口状态

2. **代理测试逻辑修复**（server.py - test_proxy）
   - 问题：测试请求直接发送到后端 API，绕过代理
   - 修复：发送请求到本地代理端口，由代理转发

3. **同步配置清理逻辑修复**（server.py - sync_to_openclaw_post）
   - 问题：未启用端口的配置不会被删除
   - 修复：基于 `enabled_models` 列表过滤配置

4. **Gateway 重启健康检查**（server.py - restart_gateway）
   - 问题：等待时间固定 8 秒，无健康检查
   - 修复：动态轮询，最多 30 秒，检查端口响应

5. **前端状态同步修复**（index.html - onModelToggle）
   - 问题：启动失败时复选框保持勾选
   - 修复：所有分支调用 checkStatus() 刷新状态

## 配置项说明

### proxy_config.json

| 字段 | 说明 |
|------|------|
| `enabled_models` | 已启用的模型列表（完整 key 格式） |
| `model_port_mapping` | 模型→端口映射 |
| `logs_dir` | 日志存储目录 |
| `session.time_window_seconds` | 会话关联时间窗口（秒） |
| `session.similarity_threshold` | 会话关联相似度阈值 |

### server.py 端口分配

- 日志查看器：9001
- 代理服务：8888-8899（自动分配）

## 调试命令

```bash
# 检查服务状态
curl http://localhost:9001/api/proxy/status

# 检查代理日志
curl "http://localhost:9001/api/proxy/log?port=8889"

# 手动启动服务
cd ~/.openclaw/skills/model-log-viewer/scripts
bash start.sh 9001

# 停止服务
bash stop.sh

# 查看进程
pgrep -f "server.py.*9001"
pgrep -f "model_proxy"
```