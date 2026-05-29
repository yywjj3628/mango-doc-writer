# hunan_mango Collection Ingest / Metadata 质量审计报告

> **检查时间**: 2026-05-29 00:35 UTC (北京时间 08:35)
> **审计方式**: Qdrant API 直接查询，纯只读，未修改任何数据
> **报告路径**: `tests/reports/hunan-mango-ingest-audit-report.md`

---

## 1. Collection 基础信息

| 字段 | 值 |
|------|-----|
| collection 名称 | `hunan_mango` |
| points_count | 60 |
| vectors_count | 60（1 point = 1 vector） |
| vector_size | 1024 |
| distance | Cosine |
| status | 🟢 green |
| optimizer_status | ok |
| segments | 4 |
| on_disk_payload | true |
| HNSW m | 16 |
| HNSW ef_construct | 100 |
| indexed_vectors_count | 0（未触发索引优化，<10000 threshold） |
| embedding 模型 | BAAI/bge-m3 (CPU) |
| chunk_size 配置 | 1000 chars |
| chunk_overlap 配置 | 150 chars |
| 可 scroll | ✅ 是 |
| 可 search | ✅ 是 |

**注意**：虽然 RAG 服务配置了 `CHUNK_SIZE=1000`，但实际入库的 60 条 chunk 平均仅 266 字符，说明入库前已经做过摘要/精简处理，并非原始文章切片。

---

## 2. 抽样检查（20 条）

| # | point_id | source | title | date | url | chunk_index | text_length | metadata_keys |
|---|---|---|---|---|---|---:|---:|---|
| 1 | 181613037… | 湖南广播电视台办公室 | 集团（台）党委开展理论学习中心组（扩大）2026年第四次集体学习 | 2026-05-19 | mp.weixin… | null | 360 | filename, filepath, filetype, created_time |
| 2 | 630786512… | 湖南广播电视台办公室 | 中国新媒体大会 莫高义谈系统性变革 | 2025-11-12 | mp.weixin… | null | 237 | filename, filepath, filetype, created_time |
| 3 | 427822427… | 湖南广播电视台办公室 | 集团（台）党委开展理论学习中心组（扩大）2025年第十一次集体学习 | 2025-11-11 | mp.weixin… | null | 265 | filename, filepath, filetype, created_time |
| 4 | 635505207… | 湖南广播电视台办公室 | 龚政文 在变革创新中推动精品创制和传播 | 2025-10-28 | mp.weixin… | null | 243 | filename, filepath, filetype, created_time |
| 5 | 120711978… | 湖南广播电视台办公室 | 这就是芒果青年该有的样子 湖南广电举办迎五四致青春青年座谈会 | 2026-05-01 | mp.weixin… | null | 290 | filename, filepath, filetype, created_time |
| 6 | 126832716… | 湖南广播电视台办公室 | 骏业骉骉 前程骎骎 潇影集团电广传媒广播传媒中心2025年度总结表彰大会举行 | 2026-02-11 | mp.weixin… | null | 279 | filename, filepath, filetype, created_time, doc_type |
| 7 | 127079334… | 湖南广播电视台办公室 | 电广传媒三湘星光行动第九颗星榆树湾青春广场正式开业 | 2025-09-16 | mp.weixin… | null | 241 | filename, filepath, filetype, created_time, doc_type |
| 8 | 141813920… | 湖南广播电视台办公室 | 办了12年的湖南卫视中秋之夜 如何打破次元壁创新 | 2025-10-07 | mp.weixin… | null | 246 | filename, filepath, filetype, created_time |
| 9 | 150974178… | 湖南广播电视台办公室 | 新年第一课 意识形态典型案例剖析会入脑入心 | 2026-03-12 | mp.weixin… | null | 258 | filename, filepath, filetype, created_time |
| 10 | 156091442… | 湖南广播电视台办公室 | 2025年马栏山文创产业园部省共建推进会举行 毛伟明曹淑敏出席 | 2025-10-14 | mp.weixin… | null | 271 | filename, filepath, filetype, created_time |
| 11 | 169230628… | 湖南广播电视台办公室 | 集团（台）开展树立和践行正确政绩观学习教育读书班第三次集中研讨暨党委理论学习中心组集体学习 | 2026-04-08 | mp.weixin… | null | 318 | filename, filepath, filetype, created_time |
| 12 | 174132962… | 湖南广播电视台办公室 | 集团（台）2026年党风廉政建设工作会议召开 | 2026-02-28 | mp.weixin… | null | 270 | filename, filepath, filetype, created_time, doc_type |
| 13 | 181328428… | 湖南广播电视台办公室 | 蔡怀军：无限探索，先干为敬 | 2026-02-24 | mp.weixin… | null | 245 | filename, filepath, filetype, created_time |
| 14 | 183777588… | 湖南广播电视台办公室 | 国庆中秋山河同乐 芒果与你共赴向往 | 2025-09-30 | mp.weixin… | null | 238 | filename, filepath, filetype, created_time |
| 15 | 209324988… | 湖南广播电视台办公室 | 湖南省人大常委会副主任省总工会主席周农到湖南广电开展元旦春节送温暖慰问活动 | 2026-01-22 | mp.weixin… | null | 269 | filename, filepath, filetype, created_time |
| 16 | 215963847… | 湖南广播电视台办公室 | 龚政文：跃马扬鞭赴新程 | 2026-02-13 | mp.weixin… | null | 237 | filename, filepath, filetype, created_time |
| 17 | 219326544… | 湖南广播电视台办公室 | 双平台召开2026年党风廉政建设工作会议 | 2026-03-26 | mp.weixin… | null | 274 | filename, filepath, filetype, created_time, doc_type |
| 18 | 230358650… | 湖南广播电视台办公室 | 共筑跨山越海的媒介桥梁 赋能中国故事全球传播 2025中国新媒体大会国际传播论坛在长沙启幕 | 2025-11-13 | mp.weixin… | null | 292 | filename, filepath, filetype, created_time |
| 19 | 242725068… | 湖南广播电视台办公室 | 湖南广电集团（台）2025年度纪检监察干部能力提升班开班 | 2025-12-12 | mp.weixin… | null | 263 | filename, filepath, filetype, created_time |
| 20 | 252441988… | 湖南广播电视台办公室 | 第六届马栏山杯国际音视频算法大赛圆满收官 | 2025-09-27 | mp.weixin… | null | 252 | filename, filepath, filetype, created_time |

---

## 3. Metadata 完整性统计（全量 60 条）

### payload.metadata 字段覆盖率

| 字段 | 覆盖数量 | 覆盖率 |
|---|---:|---:|
| filename | 60 | 100% |
| filepath | 60 | 100% |
| filetype | 60 | 100% |
| created_time | 60 | 100% |
| doc_type | 6 | 10% |

### 正文内嵌 front matter 覆盖率

| 字段 | 覆盖数量 | 覆盖率 |
|---|---:|---:|
| title | 60 | 100% |
| date | 60 | 100% |
| source | 60 | 100% |
| url | 60 | 100% |
| record_id | 60 | 100% |

### ⚠️ 发现的问题

1. **metadata.doc_type 仅 10%（6/60）**：只有 6 条标记了 doc_type（上级报告4条，纪检2条），其余 54 条为 null
2. **chunk_index 全部为 null**：没有分片索引，每条是独立 chunk
3. **无 category / tags 字段**：metadata 中完全缺失分类标签
4. **关键信息嵌在正文中**：title、date、source、url 全部以 YAML front matter 形式嵌入 text 字段，而非 metadata 字段

### Source 分布

| source | 数量 |
|---|---:|
| 湖南广播电视台办公室 | 55 (92%) |
| 电广传媒917 | 2 (3%) |
| 湖南广电党建 | 2 (3%) |
| 清风芒果 | 1 (2%) |

---

## 4. 切片质量检查

### 文本长度统计

| 指标 | 值 |
|---|---|
| 最短 | 228 字符 |
| 最长 | 360 字符 |
| 平均 | 266 字符 |
| 中位数 | 261 字符 |
| <200 字符（过短） | 0 |
| 200-2000 字符（适中） | 60 |
| ≥2000 字符（过长） | 0 |

### 切片结构分析

| 指标 | 结果 |
|---|---|
| 是否过短 | ❌ 无（最短 228 字符，足够） |
| 是否过长 | ❌ 无（最长 360 字符，偏短但合适） |
| 标题与正文是否断裂 | ❌ 无断裂（front matter + markdown 结构完整） |
| 是否一条 point 放整篇文章 | ⚠️ **全部为摘要式**（非完整文章，每条仅包含"概述"段落） |
| 是否存在乱码 | ❌ 无（0 条乱码） |
| 是否存在重复 chunk | ❌ 无（60 条全部唯一） |
| 是否保留段落结构 | ⚠️ 保留但极简（每条仅 1-2 个段落） |
| 所有 section headers | 仅 `## 概述`（60/60） |
| 无 `## 详细内容` | 60/60 均无详细段落 |
| 无 `## 要点` | 60/60 均无要点列表 |

### 切片质量评分

| 维度 | 评分 | 说明 |
|---|---:|---|
| 数据清洁度 | 95/100 | 无乱码、无重复、格式统一 |
| 结构完整性 | 70/100 | 有 front matter + 概述，但缺少详细段落 |
| Metadata 完整性 | 50/100 | doc_type 仅 10%，无 chunk_index、无 category、无 tags |
| 文种覆盖度 | 65/100 | 新闻稿为主（62%），讲话稿仅 3%，无汇报材料/请示/函 |
| 数据量 | 40/100 | 仅 60 条，覆盖面有限 |
| 风格参考适用性 | 80/100 | 概述段落精炼，适合抓取开头句式和表达风格 |

**综合评分：68/100 — 可用但建议优化**

> 评分含义：数据质量本身不错（清洁、唯一、结构化），但 metadata 覆盖率低、数据量偏少、文种覆盖不均衡，不建议直接作为唯一主库。

---

## 5. 文种分布判断（全量 60 条）

| 推测文种 | 数量 | 占比 | 判断依据 |
|---|---:|---:|---|
| 新闻稿 | 37 | 62% | 标题含活动报道、事件概述、人物报道等 |
| 会议/学习 | 6 | 10% | 标题含"党委""理论学习""研讨""政绩观""学习" |
| 活动稿 | 6 | 10% | 标题含"大会""表彰""开班""培训班""座谈会" |
| 活动/赛事报道 | 5 | 8% | 标题含"新媒体大会""大赛""活动" |
| 会议稿 | 3 | 5% | 标题含"会议""论坛""推进会" |
| 领导讲话/发言 | 2 | 3% | 标题含"谈""说"等讲话特征词 |
| 纪检/党建 | 1 | 2% | 标题含"纪检监察" |

**覆盖盲区**：
- ❌ 汇报材料（0 条）
- ❌ 请示/报告/通知/函（0 条）
- ❌ 领导讲话全文（仅概述级摘要）
- ❌ 月报/季报/年报（0 条）

---

## 6. 是否适合 mango-doc-writer

| 文种场景 | 是否适合 | 评级 | 理由 |
|---|---|---|---|
| **新闻稿** style_rag | ✅ 适合 | 🥇 最佳 | 37 条新闻稿，概述段落的新闻体写法是理想风格参考 |
| **领导讲话** style_rag | ⚠️ 部分适合 | 🥈 辅助 | 仅 2-3 条讲话类，且只有概述无全文 |
| **汇报材料** style_rag | ❌ 不适合 | — | 0 条汇报材料，无法提供风格参考 |
| **请示/报告/通知/函** | ❌ 不适合 | — | 0 条此类公文 |
| **会议纪要** style_rag | ⚠️ 辅助 | 🥉 有限 | 有会议类报道但非纪要格式 |
| **纪检/党建** style_rag | ⚠️ 辅助 | 🥉 有限 | 仅 1-3 条，覆盖面极窄 |
| **辅助风格库** | ✅ 适合 | 推荐使用 | 作为辅助库补充芒果系文风，效果明显 |

---

## 7. 与 jiuyou_docs 的对比

| 维度 | hunan_mango | jiuyou_docs |
|---|---|---|
| 数据量 | 60 | 3,106 |
| 来源 | 湖南广电微信公众号 | 久游/电广传媒企业文档 |
| 文风 | 芒果系新闻体 | 混合（年报/党建/纪要/经营） |
| 结构 | 统一 YAML front matter + 概述 | 混合格式 |
| 切片质量 | 高（清洁、唯一、结构化） | 中等（有 openclaw 日志混入） |
| metadata 覆盖 | front matter 100%，doc_type 10% | front matter 0%，doc_type ~81% |

### 各文种适合度对比

| 文种 | hunan_mango | jiuyou_docs | 建议主库 |
|---|---|---|---|
| 新闻稿 | ✅ 37 条 | ❌ 几乎无 | hunan_mango |
| 领导讲话 | ⚠️ 2-3 条 | ❌ 极少 | 混合查询 |
| 汇报材料 | ❌ 0 条 | ✅ 有经营总结/月报素材 | jiuyou_docs |
| 公文（请示/通知/函） | ❌ 0 条 | ⚠️ 有会议纪要/党建 | jiuyou_docs |
| 经营类材料 | ❌ 0 条 | ✅ 有年报/经营总结 | jiuyou_docs |
| 芒果系活动报道 | ✅ 37 条 | ❌ 无 | hunan_mango |

### 建议路由策略

| 文种 | 主 collection | 回退 collection |
|---|---|---|
| 新闻稿 | hunan_mango | jiuyou_docs |
| 活动稿 | hunan_mango | jiuyou_docs |
| 领导讲话 | hunan_mango | jiuyou_docs |
| 汇报材料 | jiuyou_docs | hunan_mango |
| 公文（请示/通知/函） | jiuyou_docs | — |
| 会议纪要 | jiuyou_docs | hunan_mango |
| 党建/纪检 | jiuyou_docs | hunan_mango |

---

## 8. 建议

### 8.1 是否建议重新 ingest hunan_mango
**不建议立即重建**。当前数据质量本身较好，问题在于：
1. 数据量太少（60 条），需要**扩充**而非重建
2. doc_type 标注不全（10%），建议**补标注**
3. 缺少详细段落（仅概述），建议**补充完整内容**

### 8.2 是否建议先用于新闻稿/讲话稿
**✅ 强烈建议**。hunan_mango 作为新闻稿 style_rag 主库效果优于 jiuyou_docs：
- 纯芒果系文风，与 mango-doc-writer 目标文风高度匹配
- 概述段落精炼，适合抓取开头句式
- 37 条新闻稿提供足够风格参考

讲话稿数量太少（2-3 条），建议仅作辅助。

### 8.3 是否建议混合路由
**✅ 建议实现按文种路由**：
- 新闻稿/活动稿/讲话稿 → `hunan_mango` 优先
- 汇报材料/公文/经营类 → `jiuyou_docs` 优先
- 默认 → 两库都查，取 top_k 合并

### 8.4 metadata 优化建议
1. **将 front matter 提取到 payload.metadata**：title、date、source、url 应作为独立 metadata 字段，而非嵌在 text 中
2. **补全 doc_type**：60 条全部可标注（新闻稿/活动稿/会议稿等）
3. **新增 category 字段**：如"学习会议""领导活动""赛事""表彰"等

### 8.5 数据扩充建议
- 从湖南广播电视台微信公众号补充更多文章（目标 200+ 条）
- 补充领导讲话全文（目前仅有概述级摘要）
- 补充汇报材料、工作总结等公文类型

---

## 9. 本次是否修改数据

| 操作 | 是否执行 |
|---|---|
| 删除 collection | ❌ 未执行 |
| 重建索引 | ❌ 未执行 |
| 写入新数据 | ❌ 未执行 |
| 修改 pipeline/rag_client.py | ❌ 未执行 |
| 修改 RAG/Qdrant 配置 | ❌ 未执行 |
| 修改 prompts/schemas/references | ❌ 未执行 |
| 修改 OpenClaw 配置 | ❌ 未执行 |
| 修改 hunan_mango 任何 point | ❌ 未执行 |

**本次为纯只读审计，零数据修改。**

---

## 10. 审计结论

### 核心发现

1. **hunan_mango 是芒果系文风的最佳 style_rag 来源**，但数据量仅 60 条，且全部为概述级摘要
2. **metadata 覆盖率低**：doc_type 仅 10%，chunk_index 全部缺失，关键信息嵌在正文 front matter 中
3. **文种覆盖不均衡**：新闻稿占 62%，讲话稿仅 3%，汇报材料/公文为零
4. **切片质量良好**：无乱码、无重复、格式统一，结构简洁

### 推荐行动

| 优先级 | 行动 | 预期效果 |
|---|---|---|
| P0 | 新闻稿 style_rag 切换到 hunan_mango | 立即提升新闻稿风格质量 |
| P1 | 实现按文种路由（新闻稿→hunan_mango，公文→jiuyou_docs） | 不同文种使用最佳 collection |
| P2 | 扩充 hunan_mango 语料到 200+ 条 | 提升覆盖面和召回质量 |
| P3 | metadata 优化（提取 front matter 到 payload） | 提升检索精度和过滤能力 |

---

*报告生成时间: 2026-05-29 00:35 UTC*
*生成工具: OpenClaw (卡乐比)*
*审计方式: Qdrant API 只读查询*
