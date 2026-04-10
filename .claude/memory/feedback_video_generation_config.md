---
name: 视频生成配置方式
description: OpenClaw 视频生成模型的正确配置方式和错误尝试
type: feedback
---

**OpenClaw 视频生成模型配置规则**

视频生成模型必须在 `agents.defaults` 下使用 `videoGenerationModel` 字段配置：

```json
{
  "agents": {
    "defaults": {
      "videoGenerationModel": {
        "primary": "dashscope-wanx/wanx-video-v1",
        "fallbacks": []
      }
    }
  }
}
```

**Why:** 
- 错误的 `tools.video` 配置会导致 gateway 启动失败（Unrecognized key: "video"）
- video_generate 是内置工具，不经过 agent 模型选择，但需要正确的全局配置指定 provider

**How to apply:** 
- 配置视频生成时，使用 `agents.defaults.videoGenerationModel.primary` 指定首选模型
- 不要尝试在 `tools` 字段下添加 `video` 配置
- 确保 provider 的 `contextWindow` ≥ 16000（OpenClaw 最低要求）

---
