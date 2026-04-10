---
name: 智能体类型自适应
description: model-log-viewer 技能支持 OpenClaw 和 Claude Code 两种智能体类型的配置加载与同步
type: reference
---

## 功能概述

model-log-viewer 技能现已支持自适应检测智能体环境，可在 OpenClaw 和 Claude Code 两种模式下工作。

### 运行模式

| 模式 | 配置文件路径 | 配置格式 |
|------|-------------|---------|
| OpenClaw | `~/.openclaw/openclaw.json` | 完整模型配置（providers + agents + auth） |
| Claude Code | `~/.claude/settings.json` | 简化模型配置（providers） |

### 检测逻辑

1. **自动检测**：页面加载时调用 `/api/detect_agent` API
   - 优先检查 `~/.openclaw/openclaw.json` 是否存在
   - 若不存在则检查 `~/.claude/settings.json`
   - 默认 fallback 到 OpenClaw 模式

2. **手动切换**：用户可通过页面选择器强制指定智能体类型

## API 端点

### GET /api/detect_agent
检测当前环境的智能体类型

**响应示例：**
```json
{
  "success": true,
  "agentType": "openclaw",
  "configPath": "/home/zhangyanbo/.openclaw/openclaw.json",
  "autoDetected": true
}
```

### POST /api/agent/models
根据智能体类型加载模型配置

**请求体：**
```json
{
  "agentType": "openclaw"
}
```

**响应示例：**
```json
{
  "success": true,
  "models": {
    "custom-dashscope-aliyuncs-com/qwen3.5-plus": {
      "url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "name": "Qwen3.5-Plus",
      "provider": "custom-dashscope-aliyuncs-com",
      "model_id": "qwen3.5-plus"
    }
  },
  "agentType": "openclaw",
  "configPath": "/home/zhangyanbo/.openclaw/openclaw.json"
}
```

### POST /api/sync
同步代理配置到智能体配置文件

**请求体：**
```json
{
  "agentType": "openclaw"  // 或 "claudecode"
}
```

## 前端实现

### 智能体类型选择器
```html
<div class="agent-type-selector">
    <label for="agentTypeSelect">🤖 智能体类型：</label>
    <select id="agentTypeSelect" onchange="onAgentTypeChange()">
        <option value="openclaw">OpenClaw</option>
        <option value="claudecode">Claude Code</option>
    </select>
    <span id="agentTypeStatus" class="agent-type-status"></span>
</div>
```

### 核心 JavaScript 函数
```javascript
// 检测智能体类型
async function detectAgentType() {
    const response = await fetch('/api/detect_agent');
    const result = await response.json();
    agentType = result.agentType;
    agentConfigPath = result.configPath;
}

// 加载模型配置
async function loadAgentModels() {
    const response = await fetch(`/api/agent/models?t=${Date.now()}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agentType })
    });
}

// 同步配置
async function syncToAgent() {
    const response = await fetch('/api/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agentType })
    });
}
```

## 后端实现

### detect_agent()
检测智能体环境，返回类型和配置路径

### get_agent_models_post()
根据 agentType 读取对应配置文件：
- OpenClaw: 从 `models.providers` 读取
- Claude Code: 从 `models.providers` 或 `mcpServers` 读取

### sync_to_openclaw_post() / sync_to_claudecode_post()
根据 agentType 调用不同的同步函数：
- OpenClaw: 更新 providers + auth + agents 三个区块
- Claude Code: 仅更新 providers 区块

## 使用场景

1. **OpenClaw 用户**：自动检测，无缝使用
2. **Claude Code 用户**：自动检测或手动选择，配置同步到 settings.json
3. **双环境用户**：可通过选择器快速切换

## 注意事项

1. Claude Code 模式的 settings.json 格式可能与 OpenClaw 不同，需要根据实际格式调整 `get_agent_models_post()` 函数
2. 同步到 Claude Code 时不会重启服务（与 OpenClaw 的 gateway 重启不同）
3. 自动检测结果会显示在状态栏，手动切换时状态变更为"手动"