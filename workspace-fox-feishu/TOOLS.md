# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

## Web Search Strategy

**优先使用代理访问，失败时降级到多引擎搜索**

1. **优先**：调用 `web_search` 工具（通过代理访问 Brave Search API）
2. **降级**：如果 `web_search` 返回 `fetch failed` 或其他错误，则调用 `multi-search-engine` 技能进行搜索

```
web_search → 成功 → 返回结果
         ↓ 失败
multi-search-engine → 备用搜索结果
```

**代理配置**：
- HTTP_PROXY/HTTPS_PROXY: `http://127.0.0.1:7897`（已在 .env 中配置）
- 仅用于 web_search，其他请求不使用代理
