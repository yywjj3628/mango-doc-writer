# Stage 15.3 — 部署前回归规则修正报告

## 执行时间
2026-05-28 16:48–16:55 UTC

## 1. 修改文件清单

| 文件 | 操作 |
|------|------|
| tests/regression/check_report.py | 重写 |
| tests/regression/run_regression.py | 增加汇总输出 |

**未修改**: prompts/* schemas/* references/* tests/cases/* render/* RAG/* typeset-engine/*

## 2. manual_confirmation_fields 检查规则调整

### 旧规则
mc=0 → 一律 fail

### 新规则
- **低风险文种**（新闻稿、通知）→ mc=0 可以通过
- extract.missing_fields 非空 → mc 不应清空
- review.issues 存在 high/critical → mc 不应清空
- review.risk_level 为 high/critical → mc 不应清空
- 其余非 low-risk 但无 high/critical → mc=0 可以通过

### 效果
001-news: fail → **pass** ✅

## 3. body_rewritten 处理规则

**保持不变**。现有 sanitizer 机制已覆盖：
- `_fix_const_fields()` 检测 const:True 字段为 False 时强制修正
- 修正记录入 sanitizer_report，风险标记为 high
- pipeline_report 中 sanitizer_high_risk=true
- 不得静默修正

**长期建议**: body_rewritten 属于 pipeline 可派生字段，不应完全依赖模型自报。可在 VPS 固化后考虑将此类 policy const 字段改为 pipeline 后置校验而非 schema 约束。

## 4. 010 称谓风险专项检查

### 实现方式
新增 `check_terminology_risk()` 函数，仅对 `terminology` in case_id 生效。

### 检测路径（满足任一即可）
1. extract.terminology_audit 非空
2. 任意阶段 terminology_usage_report 非空
3. warnings 中出现称谓/机构等关键词
4. manual_confirmation_fields 包含称谓/机构确认项
5. remaining_risks 包含称谓/机构风险

### 010 实际结果
- draft.warnings 包含"芒果总部称谓"
- manual_confirmation_fields 包含"主送单位正式称谓"
- terminology_usage_report 有 2 条记录
- **check: pass** ✅

## 5. High-Risk Sanitizer 汇总

### check_report.py 新增输出
- `high_risk_sanitizer_count`: 数量
- `high_risk_sanitizer_paths`: 字段路径列表
- `needs_manual_review`: 是否需要人工复核

### run_regression.py 新增输出
- 汇总行：`⚠️ High-Risk Sanitizer: N fixes in M cases`
- 列出涉及 case

### 当前状态
5/10 case 各 1 次 body_rewritten sanitizer（全部 rewrite 阶段）

## 6. 回归结果

| # | Case | Report | Markdown | HR Sanitizer | Terminology |
|---|------|--------|----------|-------------|-------------|
| 1 | 001-news | ✅ | ✅ | 1 | N/A |
| 2 | 002-fake-report | ✅ | ✅ | 0 | N/A |
| 3 | 003-report | ✅ | ✅ | 0 | N/A |
| 4 | 004-notice | ✅ | ✅ | 1 | N/A |
| 5 | 005-minutes | ✅ | ✅ | 1 | N/A |
| 6 | 006-speech | ✅ | ✅ | 1 | N/A |
| 7 | 007-summary | ✅ | ✅ | 0 | N/A |
| 8 | 008-letter | ✅ | ✅ | 1 | N/A |
| 9 | 009-pollution | ✅ | ✅ | 0 | N/A |
| 10 | 010-terminology | ✅ | ✅ | 0 | ✅ |

**总计: 10/10 ✅ ALL PASS**

## 7. 验收

| # | 验收项 | 状态 |
|---|--------|------|
| 1 | 不修改 prompts | ✅ |
| 2 | 不修改 schemas | ✅ |
| 3 | 不修改 references | ✅ |
| 4 | 不修改 RAG | ✅ |
| 5 | 001-news regression 不再因 mc=0 误失败 | ✅ |
| 6 | 010 terminology-risk 有专项检查 | ✅ |
| 7 | body_rewritten 修正被记录，不静默 | ✅ |
| 8 | high-risk sanitizer 可汇总 | ✅ |
| 9 | 10 case regression summary 可解释 | ✅ |
| 10 | 是否建议进入 VPS 固化部署 | ✅ |

## 8. 建议

**✅ 建议进入 VPS 固化部署**

条件已满足：
- 10/10 case 全部通过
- 60/60 schema 校验通过
- RAG 全部成功，0 fallback
- 回归规则已修正，误报已消除
- High-risk sanitizer 已有汇总和标记机制

---
*报告生成时间: 2026-05-28 16:55 UTC*
