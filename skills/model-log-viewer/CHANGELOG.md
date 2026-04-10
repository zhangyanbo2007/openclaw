# 模型日志查看器 变更日志

## v1.3.0 (2026-04-10)

### 修复问题
- **阿里云代理 Token 计数**：修复了阿里云 DashScope 代理（8890 端口）Token 计数显示为 0 的问题
  - 根因：代理重启后未正确加载 API 密钥，导致请求失败无法获取 usage 信息
  - 修复：重启代理后正确从 openclaw.json 加载 API 密钥并转发到上游
  - 验证：现在阿里云代理和本地 vLLM 代理都能正确记录 Token 使用情况

### 技术细节
- DashScope API 在流式响应的最后一个 chunk 返回 usage，格式为：
  ```json
  {"choices":[],"usage":{"prompt_tokens":11,"completion_tokens":359,"total_tokens":370}}
  ```
- `parse_sse_stream` 已正确处理此格式

---

## v1.2.0 (2026-04-09)

### 新增功能
- **同步配置到 openclaw.json**：新增"同步到 openclaw.json"按钮
  - 将当前启用的代理配置同步到 `~/.openclaw/openclaw.json`
  - 自动更新 `models.providers`、`auth.profiles`、`agents.defaults.models`
  - 同步后自动重启 OpenClaw Gateway

### 修复问题
- **配置清理逻辑**：同步时自动删除已停止代理的配置
  - 删除 `models.providers` 中不再使用的 `localproxy-*` 提供者
  - 删除 `auth.profiles` 中对应的认证配置
  - 删除 `agents.defaults.models` 中无效的模型引用
- **模型命名格式**：代理配置的 model.name 和 alias 现在包含端口号标识
  - 格式：`{模型名称} ({端口号})`，如 `Qwen3.5-Plus (8890)`
  - 便于在 OpenClaw UI 中区分不同端口的代理
- **Gateway 重启等待时间**：从 1 秒增加到 11 秒
  - 3 秒等待进程完全退出
  - 8 秒等待服务完全启动

### 技术改进
- 修复同步逻辑中 `model_key` 生成格式（使用 `localproxy-{port}/{model-id}`）
- 优化配置同步流程：先清理无效配置，再添加新配置

---

## v1.1.0 (2026-04-09)

### 新增功能
- **Token 统计**：流式响应现在正确记录 `usage` 字段
  - 代理服务器自动添加 `stream_options: {include_usage: true}`
  - 修复 `parse_sse_stream` 优先检查 chunk 的 `usage` 字段
- **运行时间**：每条日志记录 `duration`（请求耗时）
  - 显示每次模型调用的实际运行时间（如 `0.1s`）

### 修复问题
- **Thinking 显示顺序**：推理过程现在显示在回复内容前面
  - 符合模型实际执行顺序：先思考 → 再回答 → 最后调用工具
- **列对齐**：修复 Token 和间隔列被挤压的问题
  - 移除表格中的 `colspan="2"`
- **Token 显示**：优化 Token 列显示样式

### 配置变更
- 代理服务器日志目录改为 `/home/zhangyanbo/.openclaw/model-logs`
- 新日志包含 `usage` 和 `duration` 字段

---

## v1.0.0 (2026-04-08)

### 首次发布
- 基于 aiohttp 的异步 Web 服务器
- 按日期筛选日志
- 单一"模型"角色时间轴显示
- 现代化渐变 UI 设计
- Excel 导出功能

### 显示内容
- 序号、时间、角色、模型信息、输入/输出、Token、间隔
- 支持查看对话详情
- 支持导出 Excel

---

## 已知问题
- 旧日志（v1.1.0 之前）的 `usage` 字段为空，Token 显示为 `0/0`（无法恢复）
- 旧日志的 `duration` 字段为空，间隔显示为 `-`（无法恢复）
