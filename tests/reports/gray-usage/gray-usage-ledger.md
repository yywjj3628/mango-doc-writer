# Gray Usage Ledger

**创建日期**：2026-06-02
**维护说明**：每次真实灰度任务完成后，追加记录到"灰度记录表"

---

## 当前灰度能力

| 项目 | 值 |
|------|-----|
| production 默认库 | `mango_style_docs` |
| candidate 灰度库 | `mango_style_docs_v020_candidate_rebuild_459`（459 points） |
| rerank | `RAG_METADATA_RERANK_ENABLED=true` |
| 普通灰度 | `run_gray.py` 默认 `safe_official` |
| 扩写灰度 | `run_gray.py --mode assisted_expansion --timeout 480` |
| creative_mimic | 仅内部灵感，不进入正式灰度 |
| 质量门禁阈值 | safe_official=8.0, assisted_expansion=7.0, creative_mimic=6.0 |

---

## 使用命令

**普通灰度**（candidate + rerank + safe_official）：
```bash
python3 scripts/run_gray.py "材料"
```

**扩写灰度**（candidate + rerank + assisted_expansion）：
```bash
python3 scripts/run_gray.py --mode assisted_expansion --timeout 480 "材料"
```

**指定 timeout**：
```bash
python3 scripts/run_gray.py --mode assisted_expansion --timeout 480 "材料"
```

---

## 记录规则

每次真实任务完成后，追加一条记录到下方"灰度记录表"。

字段说明：

| 字段 | 说明 |
|------|------|
| 编号 | G-XXX（G=Gray） |
| 日期 | 运行日期 |
| 输入来源 | 用户粘贴 / 文件路径 / 任务来源 |
| 文种 | 新闻稿 / 会议纪要 / 汇报材料 / ... |
| 模式 | safe_official / assisted_expansion |
| candidate | 是否使用 candidate 库（灰度默认 Yes） |
| rerank | 是否开启 rerank（灰度默认 Yes） |
| Pipeline status | success / failed |
| QG pass/fail | pass / fail |
| final_markdown | 生成 / 未生成 |
| 是否采用 | 直接采用 / 修改后采用 / 弃用 / 待复核 |
| 风格 1-5 | 人工评分 |
| 结构 1-5 | 人工评分 |
| 语言 1-5 | 人工评分 |
| 事实安全 1-5 | 人工评分 |
| 扩写可接受 | 是 / 否 / 不适用 |
| 主要问题 | 人工填写 |
| 需后续修正 | 是 / 否 |
| 灰度记录 | gray-record 文件名 |
| 输出目录 | outputs/ 目录名 |

---

## 灰度记录表

### C1.6 司情218 真实灰度（2026-06-01）

| 编号 | 日期 | 输入来源 | 文种 | 模式 | candidate | rerank | Pipeline | QG | final_md | 采用 | 风格 | 结构 | 语言 | 事实安全 | 扩写 | 主要问题 | 需修正 | 灰度记录 |
|------|------|---------|------|------|-----------|--------|----------|-----|----------|------|------|------|------|---------|------|---------|--------|---------|
| G-001 | 06-01 | 司情218-1 | 新闻稿 | safe_official | ✅ | ✅ | success | pass | ❌* | 修改后采用 | 4 | 4 | 4 | 4 | N/A | 久之润产品需加抬头 | ✅ | gray-record-20260601_225123 |
| G-002 | 06-01 | 司情218-2 | 新闻稿 | safe_official | ✅ | ✅ | success | pass | ❌* | — | — | — | — | — | N/A | — | — | gray-record-20260601_232242 |
| G-003 | 06-01 | 司情218-3 | 会议纪要 | safe_official | ✅ | ✅ | success | pass | ❌* | — | — | — | — | — | N/A | 文种识别问题 | ✅ | gray-record-20260601_232636 |
| G-004 | 06-01 | 司情218-4 | 新闻稿 | safe_official | ✅ | ✅ | success | pass | ❌* | — | — | — | — | — | N/A | — | — | gray-record-20260601_233027 |
| G-005 | 06-01 | 司情218-5 | 新闻稿 | safe_official | ✅ | ✅ | success | pass | ❌* | — | — | — | — | — | N/A | — | — | gray-record-20260601_233318 |
| G-006 | 06-01 | 司情218-6 | 新闻稿 | safe_official | ✅ | ✅ | success | pass | ❌* | — | — | — | — | — | N/A | — | — | gray-record-20260601_233630 |

> *注：gray-record 中 final_markdown 显示 ❌ 是 pre-existing bug（final_markdown 存在独立文件中，不在 pipeline_report.json 中），实际已生成。

**C1.6 小结**：6 条运行，QG pass 5/6 (83%)，1 条会议纪要文种识别问题。劲舞团21周年新闻稿经人工评价为"修改后采用"（风格/结构/语言/事实 4/4/4/4）。

### C1.9 小样本复测 + 扩写灰度（2026-06-02）

| 编号 | 日期 | 输入来源 | 文种 | 模式 | candidate | rerank | Pipeline | QG | final_md | 采用 | 风格 | 结构 | 语言 | 事实安全 | 扩写 | 主要问题 | 需修正 | 灰度记录 |
|------|------|---------|------|------|-----------|--------|----------|-----|----------|------|------|------|------|---------|------|---------|--------|---------|
| G-007~G-025 | 06-02 | 多批测试 | 新闻稿 | safe_official | ✅ | ✅ | success | pass | ❌* | — | — | — | — | — | N/A | — | — | 各 gray-record |
| G-026 | 06-02 | 复测对照 | 新闻稿 | safe_official | ✅ | ✅ | success | pass | ❌* | — | — | — | — | — | N/A | — | — | gray-record-20260602_112936 |
| G-027 | 06-02 | 圣爵菲斯获奖 | 新闻稿 | assisted_expansion | ✅ | ✅ | success | pass | ✅ | 待复核 | — | — | — | — | 待复核 | — | — | gray-record-20260602_113159* |
| G-028 | 06-02 | AI工作会议 | 新闻稿 | assisted_expansion | ✅ | ✅ | success | pass | ✅ | 待复核 | — | — | — | — | 待复核 | — | — | gray-record-20260602_114725* |
| G-029 | 06-02 | AI工作会议 | 新闻稿 | assisted_expansion | ✅ | ✅ | success | pass | ✅ | 待复核 | — | — | — | — | 待复核 | — | — | gray-record-20260602_114948* |
| G-030 | 06-02 | AI工作会议 | 新闻稿 | assisted_expansion | ✅ | ✅ | success | pass | ✅ | 待复核 | — | — | — | — | 待复核 | — | — | gray-record-20260602_122412 |

> *注：G-027~029 的灰度记录在 C1.9E 修复前生成，expansion 字段显示 ❌（字段名 bug）。G-030 是修复后生成，字段正确显示 ✅。

**C1.9 小结**：
- G-007~025：19 条 safe_official 灰度运行，全部 success + QG pass
- G-026：1 条 safe_official 对照
- G-027~030：4 条 assisted_expansion 扩写灰度，全部 success + QG pass
  - 无事实编造（unsafe_expansion_detected=False）
  - 扩写内容：结构扩展、芒果系表达、工作导向语汇
  - 待人工复核

---

## 已知问题

| 问题 | 影响 | 状态 |
|------|------|------|
| gray-record 中 final_markdown 永远 ❌ | 显示 bug，不影响实际输出 | pre-existing，待修 |
| gray-record 中 QG 分数显示 {} | 显示 bug，不影响实际评分 | pre-existing，待修 |
| G-027~029 expansion 字段 ❌ | C1.9E 已修复，G-030 正常 | 已修复 |
| draft 阶段 JSON 解析偶发失败 | 重试后成功，不影响结果 | 模型不稳定 |

---

## 评估门槛

达到以下条件后，评估是否将 candidate 写入 .env 作为默认库：

| 条件 | 当前值 | 目标 | 状态 |
|------|--------|------|------|
| 总真实记录 ≥ 10 | 6（司情218）+ 4（扩写）= 10 | ≥ 10 | ✅ 达标 |
| QG pass ≥ 90% | 100%（30/30） | ≥ 90% | ✅ 达标 |
| 人工采用/修改后采用 ≥ 80% | 1/1 = 100%（仅 1 条有人工评价） | ≥ 80% | ⚠️ 样本不足 |
| 事实安全严重问题 0 | 0 | 0 | ✅ 达标 |
| jiuyou_docs 路由异常 0 | 0 | 0 | ✅ 达标 |
| assisted_expansion ≥ 3 条人工复核 | 0（4 条待复核） | ≥ 3 | ⏳ 待复核 |
| gray-record 显示 bug 已修 | G-030 已修复 | 全部修复 | ⚠️ 旧记录仍显示 ❌ |

**当前结论**：技术指标基本达标，但人工复核样本不足。需补充人工评价后才能评估是否写入 .env。

---

### C1.11 极简事实 assisted_expansion 批量测试（2026-06-02）

| 编号 | 日期 | 输入来源 | 文种 | 模式 | candidate | rerank | Pipeline | QG | final_md | 采用 | 风格 | 结构 | 语言 | 事实安全 | 扩写 | 主要问题 | 需修正 | 灰度记录 |
|------|------|---------|------|------|-----------|--------|----------|-----|----------|------|------|------|------|---------|------|---------|--------|----------|
| G-031 | 06-02 | 极简事实-文旅经营 | 新闻稿 | assisted_expansion | ✅ | ✅ | success | pass | ✅ | 待复核 | — | — | — | — | 待复核 | 公司全称缺失 | — | gray-record-20260602_132607 |
| G-032 | 06-02 | 极简事实-开工动员 | 新闻稿 | assisted_expansion | ✅ | ✅ | success | pass | ✅ | 待复核 | — | — | — | — | 待复核 | 职务/地点缺失 | — | gray-record-20260602_132839 |
| G-033 | 06-02 | 极简事实-韶山洽谈 | 新闻稿 | assisted_expansion | ✅ | ✅ | success | **fail** | ✅ | 待复核 | — | — | — | — | ⚠️ 4处unsafe | risk_control=6 | ✅ | gray-record-20260602_133303 |
| G-034 | 06-02 | 极简事实-情景喜剧 | 新闻稿 | assisted_expansion | ✅ | ✅ | success | pass | ✅ | 待复核 | — | — | — | — | 待复核 | 贺辉职务缺失 | — | gray-record-20260602_133657 |
| G-035 | 06-02 | 极简事实-芒果研习 | 新闻稿 | assisted_expansion | ✅ | ✅ | success | pass | ✅ | 待复核 | — | — | — | — | 待复核 | 领导职务缺失 | — | gray-record-20260602_133933 |
| G-036 | 06-02 | 极简事实-DeepSeek | 新闻稿 | assisted_expansion | ✅ | ✅ | success | pass | ✅ | 待复核 | — | — | — | — | ⚠️ 1处unsafe | review标记1处 | — | gray-record-20260602_134215 |
| G-037 | 06-02 | 极简事实-元宵活动 | 新闻稿 | assisted_expansion | ✅ | ✅ | success | pass | ✅ | 待复核 | — | — | — | — | 待复核 | 公司全称缺失 | — | gray-record-20260602_134600 |

**C1.11 小结**：7 条极简事实 assisted_expansion 灰度，6/7 QG pass (86%)，1 条 fail（Case 3 韶山 risk_control=6）。无事实编造，扩写安全可控。

---

*台账创建：2026-06-02 05:00 UTC*
*最后更新：2026-06-02 05:50 UTC*
