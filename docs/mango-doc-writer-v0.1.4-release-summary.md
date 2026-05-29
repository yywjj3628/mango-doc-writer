# mango-doc-writer v0.1.4 发布摘要

**版本主题**: Controlled Expansion / 增强草拟模式 / 可控自主扩写

**发布日期**: 2026-05-29

---

## 版本定位

v0.1.4 解决的核心问题：v0.1.3 的质量门禁虽然确保了事实安全，但在"少量素材 + 自动生成"场景下，系统只能输出极度保守的短文，无法发挥 AI 的草拟能力。

v0.1.4 在**不放松事实安全红线**的前提下，引入三种 generation_mode，恢复"会写"的能力。

---

## 三种 generation_mode

### safe_official — 正式安全模式

- **阈值**: 8.0
- **扩写**: 禁止
- **用途**: 正式公文生成
- **行为**: 保持 v0.1.3 完全一致，只围绕用户提供的素材成稿
- **official_use_allowed**: `true`
- **适用**: 外发公文、正式报告、对上报送

### assisted_expansion — 增强草拟模式

- **阈值**: 7.0
- **扩写**: 允许（仅结构和表达层面）
- **用途**: 内部草稿、快速搭架子
- **行为**: 在用户素材基础上，可扩展文章结构、战略表达、领导讲话句式等，但不补充具体事实
- **official_use_allowed**: `requires_human_confirmation`
- **适用**: 初稿草拟、内部讨论稿、汇报材料初稿

### creative_mimic — 风格仿写模式

- **阈值**: 6.0
- **扩写**: 允许（全风格仿写）
- **用途**: 内部灵感稿
- **行为**: 更强烈模仿芒果系文风和文章节奏，风格化程度更高
- **official_use_allowed**: `false`（永远不可直接正式发布）
- **human_review_required**: `true`（必须人工复核）
- **适用**: 创意灵感、风格参考、内部讨论

---

## 事实红线（不可突破）

以下行为在所有三种模式下均被严格禁止：

- ❌ 不编造领导姓名、职务
- ❌ 不编造具体数据、金额
- ❌ 不编造具体日期、地点（除非用户已提供）
- ❌ 不编造会议结论、政策依据
- ❌ 不编造荣誉、获奖情况
- ❌ 不把 RAG 检索结果当作事实来源
- ❌ 不编造项目名称（除非用户已提供）

---

## Quality Gate 最终规则

### 模式感知阈值

| 模式 | threshold | fact_safety 最低 | risk_control 最低 |
|------|:---------:|:----------------:|:-----------------:|
| safe_official | 8.0 | 8.0 | 8.0 |
| assisted_expansion | 7.0 | 8.0 | 8.0 |
| creative_mimic | 6.0 | 8.0 | 8.0 |

**fact_safety 和 risk_control 始终保持 8.0 最低阈值，不受模式降低。**

### creative_mimic 的关键语义

- `quality_gate_pass = true`：代表内部灵感稿质量达标，不代表可以正式发布
- `official_use_allowed = false`：代表永远不可直接正式发布
- `human_review_required = true`：代表必须由人工复核后才能使用任何内容
- `draft_disclaimer`：系统自动附加免责声明"本文为内部灵感稿，仅供参考"

**creative_mimic 的 quality_gate_pass=true 和 safe_official 的 quality_gate_pass=true 含义不同。**

---

## 阶段 4.1 修复摘要

| # | 问题 | 修复 |
|:-:|------|------|
| 1 | creative_mimic quality_gate_pass false negative | Prompt 注入 mode_adjusted_threshold + 代码 fallback |
| 2 | expansion_report / draft_disclaimer / expansion_review 缺失 | Prompt 强制提醒 + pipeline fallback 标记 |
| 3 | draft_result.official_use_allowed 覆盖 report 正确值 | 以 input_data.generation_mode 为准 |
| 4 | draft schema expansion_report 不接受空数组 | type 改为 `["object", "array"]` |

---

## 已知边界与人工复核建议

### 必须人工复核的场景

1. **assisted_expansion 输出**: `official_use_allowed = requires_human_confirmation`
   - 系统扩写的结构和表达需要人工确认
   - `confirmation_required` 列表中的内容需核实
   - 不应直接用于正式报送

2. **creative_mimic 输出**: `official_use_allowed = false`
   - 只能作为灵感参考，任何内容都不能直接使用
   - 必须人工逐句审核后重写

3. **任何模式的 fact_safety < 8**: 存在疑似新增事实风险

4. **任何模式的 risk_control < 8**: 存在风险控制隐患

### 模型行为局限

- DeepSeek 模型有时忽略 `generation_mode` 变量，代码层已修正（不信任 draft 模型的 generation_mode 输出）
- expansion_report 的生成稳定性依赖模型行为，pipeline 有 fallback 保障

---

## 验收结论

- 80/80 回归测试全部通过
- 端到端验收：4 输入 × 2-3 模式 = 10 次真实 pipeline 调用
- 无 P0 / P1 阻断项
- v0.1.3 完全向后兼容（safe_official 保持原行为）
- **建议发布 v0.1.4**

---

## 从 v0.1.3 升级指南

1. **无需任何修改即可使用**：默认 generation_mode 为 `safe_official`，行为与 v0.1.3 完全一致
2. **启用增强草拟**：在输入中指定 `"generation_mode": "assisted_expansion"`
3. **启用风格仿写**：在输入中指定 `"generation_mode": "creative_mimic"`
4. **环境变量不变**：QUALITY_GATE_ENABLED / QUALITY_GATE_THRESHOLD 仍有效
5. **新行为**：assisted_expansion 模式下 quality gate 阈值自动降为 7.0，但 fact_safety / risk_control 仍保持 8.0

---

## 输入示例

### safe_official（默认，v0.1.3 兼容）

```json
{
  "requirement": "请改成向集团汇报的正式报告，芒果系正式文风。",
  "draft": "上个月我们做了很多工作，劲舞团DAU稳定在XX万..."
}
```

### assisted_expansion（增强草拟）

```json
{
  "requirement": "请帮我写一篇芒果系新闻稿初稿。",
  "draft": "4月15日芒果超媒办了AI大赛，12个团队参加。",
  "generation_mode": "assisted_expansion"
}
```

### creative_mimic（风格仿写 / 灵感稿）

```json
{
  "requirement": "请模仿芒果系领导讲话风格写一篇稿子。",
  "draft": "会上讨论了明年的工作方向。",
  "generation_mode": "creative_mimic"
}
```
