---
name: 变更前先提交 Git
description: 每次配置变更前必须先提交并推送当前版本到 Git 仓库
type: feedback
---

每次变更前都要先 commit 当前版本并推送到 git 后方能变更。

**Why:** 用户要求确保每次修改都有完整的版本记录可追溯，防止配置丢失。

**How to apply:** 在进行任何配置修改、文件编辑或其他变更前，必须先执行完整 Git 提交流程：
1. `git add -A` 暂存所有变更
2. `git commit -m "描述变更内容"` 提交当前版本
3. `git push` 推送到远程仓库（https://github.com/zhangyanbo2007/openclaw）
4. 确认推送成功后，才能进行新的变更

