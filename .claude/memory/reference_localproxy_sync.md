---
name: localproxy 同步 openclaw.json 配置
description: model_proxy.py 从 openclaw.json 加载 API key 和 baseUrl 的同步逻辑
type: reference
---

## 配置同步流程

### 数据流

```
openclaw.json (models.providers)
    ↓ 读取
proxy_config.json (model_port_mapping)
    ↓ 匹配
model_proxy.py (port XXXX)
    ↓ 转发
后端 API (DashScope/vLLM/...)
```

### 配置文件

**openclaw.json** - 模型配置源
```json
{
  "models": {
    "providers": {
      "custom-dashscope-aliyuncs-com": {
        "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "apiKey": "sk-a2675c4123764e46880426a87bff42de",
        "models": [{"id": "qwen3.5-plus", ...}]
      },
      "localproxy-8890": {
        "baseUrl": "http://localhost:8890/v1",
        "apiKey": "sk-a2675c4123764e46880426a87bff42de",
        "models": [{"id": "qwen3.5-plus", ...}]
      }
    }
  }
}
```

**proxy_config.json** - 端口映射
```json
{
  "model_port_mapping": {
    "custom-dashscope-aliyuncs-com/qwen3.5-plus": 8890,
    "vllm-5555/qwen3.5-27b": 8888,
    "vllm-5557/gemma-4-31b-it": 8889
  }
}
```

### 同步代码 (model_proxy.py:362-400)

```python
def _load_models_from_openclaw(self, config: dict, port: int = None):
    """从 openclaw.json 加载模型配置，只加载当前端口对应的模型"""
    openclaw_path = Path.home() / ".openclaw" / "openclaw.json"
    with open(openclaw_path, "r", encoding="utf-8") as f:
        openclaw = json.load(f)

    providers = openclaw.get("models", {}).get("providers", {})
    model_port_mapping = config.get("model_port_mapping", {})

    # 只加载当前端口对应的模型
    for model_key, model_port in model_port_mapping.items():
        if port is not None and model_port != port:
            continue

        # 检查 model_key 是否存在于 providers 中
        if model_key in [f"{p}/{m['id']}" for p in providers for m in providers[p].get("models", [])]:
            for provider_name, provider_config in providers.items():
                base_url = provider_config.get("baseUrl", "")
                api_key = provider_config.get("apiKey", "")
                for model in provider_config.get("models", []):
                    full_key = f"{provider_name}/{model.get('id', '')}"
                    if full_key == model_key:
                        self.models[model_key] = {
                            "url": base_url,
                            "name": model.get("name", ...),
                            "provider": provider_name,
                            "model_id": model.get("id", ""),
                            "api_key": api_key  # 保存 API 密钥
                        }
                        break
```

### 请求转发流程

1. **客户端请求**: OpenClaw → `http://localhost:8890/v1/chat/completions`
   - 带 `Authorization: Bearer <api_key>` (从 openclaw.json 的 localproxy-8890 读取)

2. **model_proxy 处理** (`handle_request`):
   - 从请求体获取 `model` 字段
   - 调用 `get_backend_url(model)` 查找后端 URL
   - 调用 `self.models[model_key]["api_key"]` 获取 API key
   - 构建转发请求头：`Authorization: Bearer <api_key>`

3. **转发到后端**: model_proxy → `https://dashscope.aliyuncs.com/compatible-mode/v1/...`
   - 使用从 openclaw.json 加载的 API key

### 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 401 Invalid API key | localproxy-XXX 的 apiKey 配置错误 | 在 openclaw.json 中更新为正确的 API key |
| 模型未配置 | model_port_mapping 中的 key 不在 providers 中 | 确保 openclaw.json 中存在对应的 provider 和 model |
| 端口被占用 | model_proxy 实例冲突 | 检查并清理已有进程 |

### 故障排查命令

```bash
# 检查端口状态
netstat -tlnp | grep 8890

# 检查进程
ps aux | grep "port 8890"

# 测试 API key
curl -H "Authorization: Bearer sk-xxx" http://localhost:8890/v1/models

# 重启代理
pkill -f "port 8890"
cd /home/zhangyanbo/.openclaw/skills/model-log-viewer/scripts
nohup python model_proxy.py --port 8890 --config proxy_config.json > /tmp/proxy_8890.log 2>&1 &
```

### 关键注意事项

1. **API key 必须正确配置** - `localproxy-XXX` 的 `apiKey` 不能是 `"not-needed"`，必须是有效的后端 API key
2. **model_key 格式必须匹配** - `model_port_mapping` 中的 key 必须是 `provider_name/model_id` 格式
3. **每个端口独立加载** - 每个 model_proxy 实例只加载自己端口对应的模型配置