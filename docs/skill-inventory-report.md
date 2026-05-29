# Stage 20 — Skill 治理与清理报告

> **执行时间**: 2026-05-29 03:20 UTC
> **范围**: 全量 Skill 盘点、功能重叠分析、状态建议

---

## 1. 全量 Skill 清单

### 1.1 工作区 Skills（~/.openclaw/workspace/skills/）

| # | Skill 名称 | 触发条件 | 建议状态 | 说明 |
|---|---|---|---|---|
| 1 | **mango-doc-writer** | 「写新闻稿」「写请示」「领导讲话」「公文」「芒果系文案」 | **ACTIVE** | 芒果系文案生产统一入口，v0.1.2 |
| 2 | mango-writer | 「芒果风格」「官方稿」「芒果日志」 | **LEGACY** | 被 mango-doc-writer 取代（两阶段管线→六阶段） |
| 3 | jiuyou-writer | 「写月报」「经营报告」「久游报告」 | **ACTIVE** | 久游网专用，月报/季报/年度报告 |
| 4 | jiuyou-weekly-writer | 「写周报」「经营动态」「填报表」 | **ACTIVE** | 周报撰写 v3.0 |
| 5 | jiuyou-weekly-report | 「写周报」「经营动态」 | **LEGACY** | 被 jiuyou-weekly-writer 取代（v1→v3） |
| 6 | typeset-engine | 「生成报告」「做PPT」「PDF排版」「文档渲染」 | **ACTIVE** | 统一渲染引擎（Docker 端口9090） |
| 7 | feishu-cloud-sync | 「同步飞书云盘」「云文档入库」 | **ACTIVE** | 飞书→RAG+Wiki 自动化 |
| 8 | feishu-to-rag-ingest | 飞书文档入库 RAG | **ACTIVE** | RAG 入库工具 |
| 9 | rag_system_manager | RAG 系统管理 | **ACTIVE** | 向量库管理 |
| 10 | wiki-master | 「wiki」「知识库」「ingest」 | **ACTIVE** | Obsidian Wiki 管理 |
| 11 | daily-news-report | 「新闻日报」「AI新闻」 | **ACTIVE** | 每日 AI+游戏行业新闻 |
| 12 | cninfo-report | 「年报」「季报」「巨潮」 | **ACTIVE** | 上市公司财报 PDF 下载 |
| 13 | 9you-oversight-manager | 纪检监督 | **ACTIVE** | 九游纪检业务 |
| 14 | browser-automation | 浏览器自动化操作 | **ACTIVE** | 微博/小红书/X 自动化 |
| 15 | weibo-search | 「搜微博」「微博热搜」 | **ACTIVE** | 微博搜索 |
| 16 | weibo-news-publisher | 微博新闻发布 | **ACTIVE** | 微博自动发帖 |
| 17 | wx-article-fetcher | 微信公众号文章链接 | **ACTIVE** | 公众号文章抓取 |
| 18 | translator | 「翻译」「translate」 | **ACTIVE** | 翻译助手 |
| 19 | ebook-translator | 「翻译电子书」「翻译epub」 | **ACTIVE** | 电子书翻译（Docker 9091） |
| 20 | zbook | 「下载书」「Z-Library」 | **ACTIVE** | 电子书下载 |
| 21 | yao-tutorial-skill | 「做教程」「入门指南」 | **ACTIVE** | 教程生成 |
| 22 | nuwa-skill | 「造skill」「蒸馏」 | **ACTIVE** | Skill 蒸馏工具 |
| 23 | skill-creator | 创建 Skill | **ACTIVE** | Skill 创建模板 |
| 24 | skill-security-review | Skill 安全审查 | **ACTIVE** | 安全审计 |
| 25 | skill-vetter | Skill 验证 | **ACTIVE** | Skill 质量检查 |
| 26 | opencli | 「opencli」「用opencli搜」 | **ACTIVE** | 命令行资料获取 |
| 27 | filemanager | Telegram 文件接收 | **ACTIVE** | 文件归档 |
| 28 | oss-sync | 「同步OSS」「同步Obsidian」 | **ACTIVE** | Obsidian↔OSS 同步 |
| 29 | local-evolver | 自动经验提取 | **ACTIVE** | 本地经验胶囊 |
| 30 | garmin-sync | 「同步佳明」「Garmin」 | **ACTIVE** | 佳明锻炼数据同步 |
| 31 | gu-yi-perspective | 「顾总怎么看」 | **ACTIVE** | 思维视角模拟 |
| 32 | steve-jobs-skill | 「乔布斯视角」 | **ACTIVE** | 思维视角模拟 |
| 33 | imap-smtp-email | 邮件收发 | **ACTIVE** | 邮件自动化 |
| 34 | dazhong-dianping-review | 大众点评 | **ACTIVE** | 点评抓取 |
| 35 | github-trending-hunter | GitHub 热门 | **ACTIVE** | GitHub 趋势 |
| 36 | fitness-bitable | 健身数据记录 | **ACTIVE** | 飞书健身表 |
| 37 | openclaw-backup | 系统备份 | **ACTIVE** | OpenClaw 备份 |
| 38 | midnight-review | 深夜复盘 | **ACTIVE** | 定时复盘任务 |
| 39 | workspace-test | 工作区测试 | **ACTIVE** | 系统测试 |
| 40 | deer-flow | DeerFlow 调用 | **DISABLED** | DeerFlow 服务可能不再可用 |
| 41 | deerflow-dispatcher | DeerFlow 派发 | **DISABLED** | 同上 |
| 42 | telegram-file-pusher | 文件推送 | **ACTIVE** | Telegram 文件发送 |
| 43 | telegram-vps-sender | VPS 通知 | **ACTIVE** | VPS 状态通知 |
| 44 | anthropic-docx | Word 文档处理 | **LEGACY** | 被 typeset-engine 覆盖 |
| 45 | anthropic-pdf | PDF 处理 | **LEGACY** | 被 typeset-engine 覆盖 |
| 46 | anthropic-pptx | PPT 处理 | **LEGACY** | 被 typeset-engine 覆盖 |
| 47 | anthropic-xlsx | Excel 处理 | **LEGACY** | 被 typeset-engine 覆盖 |

### 1.2 飞书扩展 Skills（~/.openclaw/extensions/openclaw-lark/skills/）

| # | Skill 名称 | 状态 | 说明 |
|---|---|---|---|
| 1 | feishu-bitable | **ACTIVE** | 多维表格管理 |
| 2 | feishu-calendar | **ACTIVE** | 日历管理 |
| 3 | feishu-channel-rules | **ACTIVE** | 渠道隐私规则 |
| 4 | feishu-create-doc | **ACTIVE** | 创建文档 |
| 5 | feishu-fetch-doc | **ACTIVE** | 获取文档 |
| 6 | feishu-im-read | **ACTIVE** | IM 消息读取 |
| 7 | feishu-task | **ACTIVE** | 任务管理 |
| 8 | feishu-troubleshoot | **ACTIVE** | 飞书故障排查 |
| 9 | feishu-update-doc | **ACTIVE** | 更新文档 |

### 1.3 Lark CLI Skills（~/.agents/skills/）

| # | Skill 名称 | 状态 | 说明 |
|---|---|---|---|
| 1-18 | lark-base/calendar/contact/doc/drive/im/mail/minutes/sheets/task/wiki 等 | **ACTIVE** | 飞书能力底层实现 |

### 1.4 系统级 Skills（OpenClaw 内置）

共 50+ 个，包括 coding-agent、github、weather、tmux、node-connect 等。全部保持系统默认状态，不修改。

---

## 2. 功能重叠分析

### 2.1 🔴 核心重叠：mango-writer vs mango-doc-writer

| 维度 | mango-writer（旧） | mango-doc-writer（新） |
|------|---|---|
| 管线 | 两阶段（清理→风格化） | 六阶段（classify→rewrite） |
| RAG | 单库 jiuyou_docs | 多库路由（mango_style_docs + jiuyou_docs） |
| 文种 | 仅新闻稿 | 新闻/公文/讲话/汇报/会议纪要 |
| Schema | 无 JSON Schema 校验 | 全链路 Schema 校验 |
| Sanitizer | 无 | 事实污染/称谓/安全检查 |
| 风格 | 芒果日志风格（60篇） | 芒果系（同语料，更深集成） |

**结论：mango-writer 已被 mango-doc-writer 完全取代。**

### 2.2 🟡 轻度重叠：jiuyou-weekly-report vs jiuyou-weekly-writer

| 维度 | jiuyou-weekly-report（旧 v1） | jiuyou-weekly-writer（新 v3） |
|------|---|---|
| 版本 | v1.0.0 | v3.0.0 |
| 历史周报 | 5 份（2025.9-10） | 更多历史数据 |

**结论：jiuyou-weekly-report 被 jiuyou-weekly-writer 取代。**

### 2.3 🟡 轻度重叠：anthropic-docx/pdf/pptx/xlsx vs typeset-engine

| 维度 | anthropic-* | typeset-engine |
|------|---|---|
| 方式 | Python 直接生成 | Docker HTTP API |
| 格式 | 单一 | PDF/DOCX/PPTX/图表/视频 |
| 可靠性 | 依赖 Python 库版本 | 容器化隔离 |

**结论：typeset-engine 是统一入口，anthropic-* 系列 LEGACY。**

---

## 3. 状态汇总

| 状态 | 数量 | 说明 |
|------|---:|---|
| **ACTIVE** | 39 | 正常使用 |
| **LEGACY** | 6 | 被新 Skill 取代，可归档 |
| **DISABLED** | 2 | 服务不可用 |

## 4. 建议操作

### 4.1 建议保留（ACTIVE）— 39 个
全部保持现状，无需操作。

### 4.2 建议降级（LEGACY）— 6 个

| Skill | 取代者 | 建议 |
|------|---|---|
| mango-writer | mango-doc-writer | 降级，不删除 |
| jiuyou-weekly-report | jiuyou-weekly-writer | 降级，不删除 |
| anthropic-docx | typeset-engine | 降级，不删除 |
| anthropic-pdf | typeset-engine | 降级，不删除 |
| anthropic-pptx | typeset-engine | 降级，不删除 |
| anthropic-xlsx | typeset-engine | 降级，不删除 |

**降级方式**：在 SKILL.md 头部 frontmatter 添加 `deprecated: true`，保留代码供参考。

### 4.3 建议停用（DISABLED）— 2 个

| Skill | 原因 |
|------|---|
| deer-flow | DeerFlow 服务状态未知 |
| deerflow-dispatcher | 同上 |

---

## 5. 禁止事项确认

本阶段仅做盘点和报告，**未修改**：
- prompts/* ❌
- schemas/* ❌
- references/* ❌
- pipeline/* ❌
- Qdrant 数据 ❌
- RAG 配置 ❌
- 任何 Skill 代码 ❌

---

*报告时间: 2026-05-29 03:22 UTC*
*报告路径: docs/skill-inventory-report.md*
