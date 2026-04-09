# MEMORY.md - 具身智能研究助手记忆

## 飞书文档访问策略

**记录时间**: 2026-03-30  
**来源**: 用户指导

### 访问流程
1. 从飞书 URL 提取 doc_token
   - 格式：`https://xxx.feishu.cn/docx/ABC123def` → `doc_token = ABC123def`
   - Wiki 格式：`https://xxx.feishu.cn/wiki/ABC123def` → `doc_token = ABC123def`

2. 使用飞书凭证获取 tenant_access_token
   ```bash
   curl -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
     -H "Content-Type: application/json" \
     -d '{"app_id":"CLI_APP_ID","app_secret":"APP_SECRET"}'
   ```

3. 读取文档内容
   ```bash
   # 获取文档元数据
   curl -X GET "https://open.feishu.cn/open-apis/docx/v1/documents/DOC_TOKEN" \
     -H "Authorization: Bearer TENANT_ACCESS_TOKEN"
   
   # 获取文档原始内容
   curl -X GET "https://open.feishu.cn/open-apis/docx/v1/documents/DOC_TOKEN/raw_content" \
     -H "Authorization: Bearer TENANT_ACCESS_TOKEN"
   ```

### 飞书应用凭证
| 应用名称 | app_id | app_secret | 用途 |
|---------|--------|------------|------|
| fox-avatar | cli_a92d483ece78dbcc | l1rhhwFoWwtMXAPa9yhx1dtOLQoQGXoL | 狐狸虚拟助手，默认用于文档读取 |
| fox-smarthome | cli_a93fa0d94b225bdb | I6fUqPMBMQvN8Be9j08tte5OlaoknAO7 | 智能家居管家 |

### 注意事项
- tenant_access_token 有效期约 3225 秒（~53 分钟），过期需重新获取
- 优先使用 fox-avatar 凭证读取文档
- 404 错误可能是 token 类型不对（wiki vs docx），尝试不同 API 端点

---

## 用户信息
- **名称**: 小王子
- **时间区**: Asia/Shanghai (GMT+8)
- **Feishu open_id**: ou_45ca8d7feaddef8a7a182779a434c8bc

## 项目背景
- 公司与韶关当地政府合作建设具身智能训练场
- 核心产出：具身训练数据
- 技术方向：具身智能、机械臂算法、VLA 模型、World 模型
