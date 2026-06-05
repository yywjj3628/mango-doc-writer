# NEXT_SESSION_PROMPT.md — 新会话接手提示词

> 直接复制以下内容粘贴给新 Codex/OpenClaw 会话

---

```
你好，你正在接手 mango-doc-writer 项目。

请按以下步骤操作：

1. 读取项目握手文件：
   cat PROJECT_HANDOFF.md

2. 检查当前状态：
   git branch --show-current
   git log -1 --oneline
   git status --short

3. 读取最新收口报告（按需）：
   - tests/reports/v0.2.0-stage-g3.1-gray-full-review-report.md
   - tests/reports/v0.2.0-stage-j2.9-jiuzhirun-docs-routing-and-capability-closure-report.md
   - tests/reports/v0.2.0-stage-l1-leadership-title-special-closure-report.md

4. 不要立即执行任何改造。

5. 先向用户复述：
   - 项目当前状态
   - 主要风险和遗留问题
   - 建议的下一阶段方向

6. 等用户确认后，再生成下一阶段的 OpenClaw 提示词。

注意事项：
- 不要修改 .env、正式规则库或 Qdrant
- 不要自动确认任何领导职务
- 所有正式变更必须有阶段号和阶段报告
- 历史语料不能作为当前事实
```

---

*本文件用于快速启动新会话，无需依赖历史聊天记录。*
