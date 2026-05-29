# RAG 向量集盘点报告

> **检查时间**: 2026-05-29 00:25 UTC (北京时间 08:25)
> **执行方式**: Qdrant API 直接查询，未修改任何数据
> **报告路径**: `tests/reports/rag-collections-inventory-report.md`

---

## 1. 服务状态

| 服务 | 地址 | 状态 | 容器 |
|------|------|------|------|
| RAG 搜索服务 | `http://localhost:8000` | ✅ healthy | `rag-server` (Docker) |
| Qdrant 向量数据库 | `http://localhost:6333` | ✅ ok | `rag-qdrant` (Docker) |
| RAG HTTP | `http://localhost:6333` (gRPC: 6334) | ✅ ok | — |

两个服务均运行在 Docker 容器中，状态正常。

---

## 2. 所有 Collection 列表

| collection_name | points_count | status | vector_size | distance | on_disk_payload | segments | 备注 |
|---|---:|---|---:|---|---|---:|---|
| **jiuyou_docs** | 3,106 | 🟢 green | 1024 | Cosine | true | 4 | 久游企业文档（主 collection） |
| **hunan_mango** | 60 | 🟢 green | 1024 | Cosine | true | 4 | 湖南广电/芒果系微信公众号文章 |
| **openclaw_memory** | 618 | 🟢 green | 1024 | Cosine | true | 4 | OpenClaw 日志/记忆文件 |

**共性配置**：
- 向量维度：1024（BGE-M3 模型）
- 距离度量：Cosine
- HNSW m=16, ef_construct=100
- 优化阈值：10000 points（均未触发索引优化）

---

## 3. 每个 Collection 抽样

### 3.1 jiuyou_docs（抽样 5 条）

| # | text_preview | filename | doc_type | filetype | year |
|---|---|---|---|---|---|
| 1 | 入当期损益或冲减相关成本。与公司日常经营活动相关的政府补助，按照经济业务实质… | 电广传媒2024年度年报.pdf | 上级报告 | pdf | 2024 |
| 2 | 其中：银行承兑汇票 1,200,000.00 1.51%… | 芒果超媒2025年度年报.pdf | 上级报告 | pdf | 2025 |
| 3 | 集团，成为其全资子公司，并将湖南台所属事业资产全部剥离转制注入影视集团… | 芒果超媒2025年度年报.pdf | 上级报告 | pdf | 2025 |
| 4 | # Midnight Review - 2026-04-25 Daily Notes 01:03 [系统管理] 执行每日会议提醒自动化… | 2026-04-25.md | N/A | md | N/A |
| 5 | 会议记录 党支部 上海久之润信息技术有限公司党支部 会议主题 集中研讨学习会… | 主题党日-集中研讨学习会.pdf | 党建 | pdf | N/A |

**doc_type 分布（抽样 100 条）**：

| doc_type | 数量 |
|---|---:|
| 上级报告 | 42 |
| N/A | 19 |
| 会议纪要 | 13 |
| 党建 | 10 |
| 月报素材 | 7 |
| 经营总结 | 6 |
| 绩效承诺 | 3 |

**filetype 分布**：pdf(53) / txt(26) / docx(19) / md(2)

**metadata 结构**：`{filename, filepath, filetype, created_time, doc_type?, year?}`

### 3.2 hunan_mango（抽样 5 条，总计 60 条）

| # | text_preview | filename | source |
|---|---|---|---|
| 1 | 集团（台）党委开展理论学习中心组（扩大）2026年第四次集体学习… | 集团台党委开展理论学习中心组扩大2026_pRbHu6.md | 湖南广播电视台办公室 |
| 2 | 中国新媒体大会 莫高义谈系统性变革… | 中国新媒体大会_莫高义谈系统性变革_Sp51tn.md | 湖南广播电视台办公室 |
| 3 | 集团（台）党委开展理论学习中心组（扩大）2025年第十一次集体学习… | 集团台党委开展理论学习中心组扩大2025_VdFpDm.md | 湖南广播电视台办公室 |
| 4 | 龚政文 在变革创新中推动精品创制和传播… | 龚政文_在变革创新中推动精品创制和传播_qMwPn9.md | 湖南广播电视台办公室 |
| 5 | 这就是芒果青年该有的样子 湖南广电举办迎五四致青春青年座谈会… | 这就是芒果青年该有的样子_湖南广电举办迎_DILsG7.md | 湖南广播电视台办公室 |

**metadata 结构**：`{filename, filepath, filetype, created_time}` + 正文内嵌 `title`, `date`, `source`, `url`, `record_id`

**内容特征**：全部来自湖南广播电视台微信公众号文章，包含标题/日期/来源/URL，结构化 markdown 格式。

### 3.3 openclaw_memory（抽样 5 条，总计 618 条）

| # | text_preview | filename |
|---|---|---|
| 1 | db4ac5555] Conversation info (untrusted metadata)… | 2026-03-07-rag-query-result.md |
| 2 | 延长有效期 [限流应对] 冷却时间5-10分钟… | 2026-03-08.md |
| 3 | 第一条 会议定位 总经理办公会（暨经营班子决策会议）是上海久之润经营的沟通中枢… | 2026-03-02.md |
| 4 | 十大新闻；当前需确认的关键细节包括新闻的具体分类… | 2026-03-17.md |
| 5 | 2026/03/04 每日复盘… | 2026-03-04.md |

**metadata 结构**：`{filename, filepath, filetype, created_time}`

**内容特征**：OpenClaw 助手的每日记忆文件、会话日志、技术笔记。

---

## 4. 每个 Collection 用途判断

| collection_name | 初步用途判断 | 是否适合 mango-doc-writer style_rag | 理由 |
|---|---|---|---|
| **jiuyou_docs** | 久游/电广传媒企业文档（上级报告、会议纪要、党建、月报素材） | ⚠️ 部分适合 | 包含会议纪要、经营总结等公文语料，但以电广传媒年报、党建记录为主，芒果系文案风格参考较少 |
| **hunan_mango** | 湖南广电/芒果体系微信公众号文章 | ✅ 是 | 纯芒果系新闻稿/活动稿/讲话稿，文风与广电体系高度匹配，是 mango-doc-writer style_rag 的理想来源 |
| **openclaw_memory** | OpenClaw 助手运行日志/记忆 | ❌ 否 | 技术日志、会话记录，非公文语料 |

---

## 5. 当前 mango-doc-writer 使用的 Collection

| 文件/配置 | RAG base_url | collection | top_k | 是否当前主链路使用 |
|---|---|---|---:|---|
| `pipeline/rag_client.py` | `http://localhost:8000/search` | `jiuyou_docs` | 3 | ✅ 主链路（`retrieve_style_references`） |
| `pipeline/model_runner.py` | `http://localhost:8000/search` | `jiuyou_docs` | 5 | ⚠️ 遗留代码（`_call_style_rag` 未被调用） |

**当前状态**：`rag_client.py` 硬编码使用 `jiuyou_docs`，无环境变量覆盖机制。

---

## 6. 是否发现更适合的 style_rag Collection

### 候选 Collection

| 优先级 | collection | 理由 | 风险 |
|---|---|---|---|
| 🥇 | **hunan_mango** | 纯芒果系微信公众号文章，包含新闻稿、活动报道、领导讲话等，文风与广电/芒果体系高度匹配，60条均为高质量文案语料 | 数据量少（仅60条），覆盖面有限 |
| 🥈 | **jiuyou_docs**（当前） | 包含会议纪要、经营总结、党建等公文语料，3106条数据量大 | 芒果系文案风格较少，电广年报/党建为主 |
| 🥉 | **混合查询** | 同时查 `hunan_mango` + `jiuyou_docs`，取并集 | 需修改 rag_client 逻辑 |

### 建议方案

**短期**：考虑将 style_rag collection 切换为 `hunan_mango`，或优先查 `hunan_mango`，回退到 `jiuyou_docs`。

**中期**：扩充 `hunan_mango` 语料（从微信公众号、芒果TV等渠道补充），使其达到 200+ 条。

**长期**：将 collection 从硬编码改为环境变量，支持按文种动态路由。

---

## 7. 建议

### 7.1 是否继续使用 jiuyou_docs
当前 `jiuyou_docs` 适合做**事实检索**（查询公司制度、经营数据、会议记录），但不一定是**风格参考**的最佳选择。芒果系文案风格在 `hunan_mango` 中更集中。

### 7.2 是否建议切换到 hunan_mango
**建议切换**，但需验证：
1. 先用 hunan_mango 做 3-5 次 pipeline 测试（新闻稿、报告、讲话稿），对比风格质量
2. 确认 60 条语料覆盖的文种范围是否足够
3. 如覆盖不全，可考虑混合查询

### 7.3 是否建议改为环境变量
**强烈建议**。当前 collection 硬编码在两处代码中，不利于灵活切换。建议：
- 新增 `STYLE_RAG_COLLECTION` 环境变量
- `rag_client.py` 优先读取环境变量，回退到默认值
- 不同文种可路由到不同 collection

### 7.4 是否建议 collection 重命名/拆分
暂不建议重命名（影响面大）。可考虑：
- 将 `jiuyou_docs` 中芒果系相关文档迁移到 `hunan_mango`
- 或新建 `jiuyou_internal` 专放久之润内部文档

### 7.5 是否建议 RAG 语料治理
**建议**：
1. `hunan_mango` 数据量偏少（60条），建议扩充到 200+
2. `jiuyou_docs` 中混入了 OpenClaw 记忆文件（如 `2026-04-25.md`），建议清理
3. 建立 doc_type 标准化体系，所有入库文档统一标记

---

## 8. 本次是否修改数据

| 操作 | 是否执行 |
|---|---|
| 删除 collection | ❌ 未执行 |
| 重建索引 | ❌ 未执行 |
| 写入新数据 | ❌ 未执行 |
| 修改 pipeline/rag_client.py | ❌ 未执行 |
| 修改 RAG/Qdrant 配置 | ❌ 未执行 |
| 修改 prompts/schemas/references | ❌ 未执行 |
| 修改 OpenClaw 配置 | ❌ 未执行 |

**本次仅为只读盘点，未做任何数据修改。**

---

*报告生成时间: 2026-05-29 00:25 UTC*
*生成工具: OpenClaw (卡乐比)*
