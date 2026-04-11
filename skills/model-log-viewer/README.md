# 模型日志查看器系统

## 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              用户界面层 (Browser)                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  http://localhost:9003                                                  │    │
│  │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────┐   │    │
│  │  │  代理配置管理   │ │   日志查看器    │ │     会话时间轴          │   │    │
│  │  │  - 启用/关闭    │ │   - 按日期筛选  │ │     - 对话详情          │   │    │
│  │  │  - 同步配置     │ │   - 请求/响应   │ │     - Token 统计        │   │    │
│  │  │  - 状态监控     │ │   - Excel 导出   │ │     - 运行时间          │   │    │
│  │  └─────────────────┘ └─────────────────┘ └─────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           日志查看器服务器 (server.py)                           │
│                        Port: 9003 | env: model_proxy                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  API 路由层                                                              │    │
│  │  ├── GET  /                              → 首页 (index.html)             │    │
│  │  ├── GET  /api/proxy/status              → 获取代理状态                  │    │
│  │  ├── GET  /api/proxy/config              → 获取代理配置                  │    │
│  │  ├── POST /api/proxy/start               → 启动代理 (检查 API 密钥 + 测试)   │    │
│  │  ├── POST /api/proxy/stop                → 停止代理                      │    │
│  │  ├── POST /api/proxy/save_config         → 保存代理配置                  │    │
│  │  ├── POST /api/sync                      → 同步配置到 openclaw.json       │    │
│  │  ├── GET  /api/openclaw/models           → 获取模型列表                  │    │
│  │  ├── GET  /api/conversations?date=xxx    → 获取会话列表                  │    │
│  │  └── GET  /api/logs/detail?id=xxx        → 获取会话详情                  │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  核心逻辑层                                                              │    │
│  │  ├── start_proxy()     → ①检查 API 密钥 ②启动进程 ③测试验证              │    │
│  │  ├── test_proxy()      → 发送测试请求验证代理可用性                      │    │
│  │  ├── sync_to_openclaw() → 同步配置并重启 Gateway                         │    │
│  │  └── render_detail_page() → 渲染会话时间轴 HTML                          │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
                    │                              │
         ┌──────────┘                              └──────────
         ▼                                                     ▼
┌─────────────────────────────────┐          ┌─────────────────────────────────┐
│      模型代理服务集群            │          │        OpenClaw Gateway          │
│      (model_proxy.py)           │          │                                  │
│  ┌─────────────────────────┐    │          │  ┌────────────────────────────┐  │
│  │ Port 8888               │    │          │  │  Port: 内置                │  │
│  │ - qwen3.5-27b (vllm)    │    │          │  │  功能：智能体调度          │  │
│  │ - API Key: 自动转发      │    │          │  │  配置：读取 openclaw.json   │  │
│  └─────────────────────────┘    │          │  └────────────────────────────┘  │
│  ┌─────────────────────────┐    │          └─────────────────────────────────┘
│  │ Port 8889               │    │                            │
│  │ - gemma-4-31b-it (vllm) │    │                            ▼
│  │ - API Key: 自动转发      │    │          ┌─────────────────────────────────┐
│  └─────────────────────────┘    │          │      智能体 Agents               │
│  ┌─────────────────────────┐    │          │  - main (主智能体)              │
│  │ Port 8890               │    │          │  - fox-feishu (飞书集成)        │
│  │ - qwen3.5-plus (阿里云)  │    │          │  - fox-avatar (角色扮相)        │
│  │ - API Key: 自动转发      │    │          └─────────────────────────────────┘
│  └─────────────────────────┘    │
└─────────────────────────────────┘
         │                                    │
         ▼                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              配置文件层                                         │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────────────┐  │
│  │  proxy_config.json              │  │  openclaw.json                      │  │
│  │  - enabled_models               │  │  - models.providers                 │  │
│  │  - model_port_mapping           │  │  - auth.profiles                    │  │
│  │  - logs_dir                     │  │  - agents.defaults                  │  │
│  │  - session config               │  │  - agents.list                      │  │
│  └─────────────────────────────────┘  └─────────────────────────────────────┘  │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────────────┐  │
│  │  agents/main/agent/models.json  │  │  auth-state.json                    │  │
│  │  - providers 定义               │  │  - API 密钥状态                      │  │
│  │  - API Keys                     │  │  - 认证 token                        │  │
│  │  - 模型参数                     │  │                                     │  │
│  └─────────────────────────────────┘  └─────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              外部模型 API                                        │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐              │
│  │ 阿里云 DashScope  │  │ vLLM 本地部署     │  │ MiniMax          │              │
│  │ qwen3.5-plus     │  │ qwen3.5-27b      │  │ MiniMax-M2.5     │              │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐              │
│  │ Moonshot         │  │ ZAI (智谱)        │  │ 其他 Provider     │              │
│  │ kimi-k2.5        │  │ glm-5/glm-4.7    │  │ ...              │              │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘              │
└─────────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              日志存储层                                         │
│  /home/zhangyanbo/.openclaw/model-logs/                                        │
│  └── YYYY-MM-DD/                                                               │
│      └── conv_<session_id>/                                                    │
│          ├── index.json          (会话元信息：user_id, started_at, etc.)       │
│          ├── request_001.json    (请求 #1: messages + response + usage)        │
│          ├── request_002.json    (请求 #2: messages + response + usage)        │
│          └── ...                                                                   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 数据流

### 1. 代理启动流程

```
用户点击"启用" 
    │
    ▼
前端发送 POST /api/proxy/start { port: 8890 }
    │
    ▼
server.py: start_proxy(8890)
    │
    ├── ① 读取 proxy_config.json 获取 model_key
    │
    ├── ② 检查 API 密钥
    │     ├── 从 openclaw.json 读取
    │     └── 如果没有，从 agents/main/agent/models.json 读取
    │     └── 没有密钥 → 返回错误，拒绝启动
    │
    ├── ③ 启动 model_proxy.py 进程
    │
    ├── ④ 等待 2 秒
    │
    └── ⑤ 发送测试请求验证
          ├── 成功 → 返回"启动成功！模型：xxx"
          └── 失败 → 返回"启动成功但测试失败：错误信息"
```

### 2. 请求转发流程

```
OpenClaw 智能体
    │
    ▼
发送请求到 localproxy-8890 (http://localhost:8890/v1/chat/completions)
    │
    ▼
model_proxy.py: handle_request()
    │
    ├── ① 解析请求，获取 model_name
    │
    ├── ② 查找后端 URL (从 openclaw.json)
    │
    ├── ③ 获取 API 密钥
    │
    ├── ④ 转发请求到后端
    │     └── 添加 Authorization: Bearer {api_key}
    │
    ├── ⑤ 记录日志到 model-logs/
    │
    └── ⑥ 返回响应给智能体
```

### 3. 配置同步流程

```
用户点击"同步到 openclaw.json"
    │
    ▼
前端发送 POST /api/sync
    │
    ▼
server.py: sync_to_openclaw_post()
    │
    ├── ① 读取 proxy_config.json 获取 model_port_mapping
    │
    ├── ② 读取 openclaw.json
    │
    ├── ③ 删除失效的 localproxy-* 配置
    │     ├── models.providers
    │     ├── auth.profiles
    │     └── agents.defaults.models
    │
    ├── ④ 添加/更新有效的 localproxy-* 配置
    │     └── alias 格式：{模型名称} ({端口号})
    │
    ├── ⑤ 写回 openclaw.json
    │
    ├── ⑥ 重启 Gateway (等待 11 秒)
    │
    └── ⑦ 返回同步结果
```

## 核心文件

| 文件 | 说明 |
|------|------|
| `server.py` | 日志查看器服务器（aiohttp，Port 9003） |
| `model_proxy.py` | 模型代理脚本（多实例，Port 8888-8890+） |
| `index.html` | 前端界面（模型管理 + 日志查看） |
| `proxy_config.json` | 代理配置（启用的模型、端口映射） |
| `~/.openclaw/openclaw.json` | OpenClaw 主配置 |
| `~/.openclaw/model-logs/` | 日志存储目录 |

## 端口分配

| 组件 | 端口 | 说明 |
|------|------|------|
| 日志查看器 | 9003 | Web 界面 |
| 代理 8888 | 8888 | vllm-5555/qwen3.5-27b |
| 代理 8889 | 8889 | vllm-5557/gemma-4-31b-it |
| 代理 8890 | 8890 | custom-dashscope-aliyuncs-com/qwen3.5-plus |

## 版本

当前版本：v1.3.0

## 附录：会话管理策略

### 会话 ID 生成规则

**会话维度优先级：agent_id > chat_type > chat_id > /new 标记**

| 场景 | 会话 ID 格式 | 说明 |
|------|-------------|------|
| main agent + 飞书用户首次 | `conv_agent_main_user_ou_xxxxx_20260410_182030` | agent + 用户 ID + 时间戳 |
| main agent + 飞书用户普通消息 | 复用最近的 `conv_agent_main_user_ou_xxxxx_*` | 按 `started_at` 排序取最新 |
| main agent + 飞书用户 `/new` 触发 | `conv_agent_main_user_ou_xxxxx_20260410_183000` | 新时间戳的新会话 |
| fox-feishu agent + 群聊首次 | `conv_agent_fox-feishu_group_oc_xxxxx_20260410_182030` | agent + 群 ID + 时间戳 |
| control-ui 无用户 ID | `conv_agent_main_20260410_182030` | 仅按 agent 区分 |

**说明：**
- `agent_id` 从 `openclaw.json` 的 `bindings` 配置中查找
- 消息中 `Sender metadata` 的 `accountId` 字段用于匹配 bindings
- 如果没有 `accountId` 字段，`openclaw-control-ui` 默认对应 `main` agent
- `/new` 触发新会话（新时间戳），但 ID 格式与普通消息一致

### 会话复用逻辑

```
收到请求
    │
    ▼
① 提取 agent 信息（channel, account_id, agent_id）
    │  - 优先读取 Sender metadata 中的 accountId 字段
    │  - 通过 bindings 配置查找对应的 agentId
    │  - 无 accountId 时：openclaw-control-ui → main agent
    │
    ▼
② 检测聊天类型和用户/群 ID
    │  - 使用 user_id_patterns / group_id_patterns 匹配
    │  - 支持多个 pattern（如 ou_xxx 和 openclaw-control-ui）
    │
    ▼
③ 构建基础会话 ID
    │  - 有 agent_id + 用户 ID：conv_agent_{agent}_user_{ou_xxx}
    │  - 有 agent_id + 群 ID：conv_agent_{agent}_group_{oc_xxx}
    │  - 只有 agent_id：conv_agent_{agent}
    │
    ▼
④ 检测是否包含 /new 或 /reset 标记
    │
    ├── 包含标记
    │     └── 创建新会话：{base}_new_{timestamp}
    │
    └── 无标记（普通消息）
          │
          ▼
          查找匹配的会话（同 agent + 同用户/群）
          │
          ├── 找到匹配
          │     └── 复用最近的会话（started_at 最新）
          │
          └── 无匹配
                └── 创建新会话：{base}_{timestamp}
```

### 配置方式

**1. proxy_config.json - 配置用户 ID patterns 和会话标记**

```json
{
  "agents": {
    "openclaw": {
      "enabled": true,
      "user_id_patterns": [
        "ou_[a-z0-9]+",
        "openclaw-control-ui"
      ],
      "group_id_patterns": [
        "oc_[a-z0-9]+",
        "openclaw-control-ui"
      ],
      "new_session_markers": [
        "A new session was started via /new or /reset",
        "/new",
        "/reset"
      ]
    }
  }
}
```

**2. openclaw.json - 配置 bindings（智能体路由）**

```json
{
  "bindings": [
    {
      "agentId": "main",
      "match": {
        "channel": "feishu",
        "accountId": "main"
      }
    },
    {
      "agentId": "fox-feishu",
      "match": {
        "channel": "feishu",
        "accountId": "fox-feishu"
      }
    }
  ]
}
```

**3. 消息格式 - Sender metadata**

```json
{
  "label": "openclaw-control-ui",
  "id": "openclaw-control-ui",
  "accountId": "main"
}
```

`accountId` 字段用于匹配 bindings 配置，查找对应的 `agentId`。

### 版本

当前版本：v1.3.0
