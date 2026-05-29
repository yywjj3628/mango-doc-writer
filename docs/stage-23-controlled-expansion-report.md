# Stage 23 — Controlled Expansion 实现报告

**日期**: 2026-05-29
**版本**: v0.1.4

---

## 1. 设计目标

芒果系文案生产系统在 v0.1.3 质量门禁确保了事实安全，但代价是"少量素材 + 自动生成"场景下输出过于保守，只能围绕已有事实生成极短文本。

v0.1.4 的目标是：**在事实安全红线不放松的前提下，恢复 AI 的自主草拟能力。**

具体方式：引入 `generation_mode` 参数，将写作行为分为三种模式，让用户根据使用场景选择不同的扩写宽松度。

---

## 2. 实现范围

### Prompt 变更

| 文件 | 变更 |
|------|------|
| `prompts/03-plan.md` | 新增 expansion_directives（扩写策略指令） |
| `prompts/04-draft.md` | 新增三模式行为规则 + expansion_report + draft_disclaimer + v0.1.4 强制字段提醒 |
| `prompts/05-review.md` | 新增扩写安全审查 + expansion_review + unsafe_fabrication / confirmation_required 分类 |
| `prompts/06-rewrite.md` | 新增模式感知修订策略 |
| `prompts/07-quality-score.md` | 新增模式感知阈值 + mode_adjusted_threshold 注入 + overall_pass 严格规则 |

### Schema 变更

| 文件 | 变更 |
|------|------|
| `schemas/draft.schema.json` | 新增 generation_mode / official_use_allowed / expansion_report / draft_disclaimer / expansion_policy；expansion_report type 改为 `["object", "array"]` |
| `schemas/review.schema.json` | 新增 expansion_review 字段 |
| `schemas/plan.schema.json` | 新增 expansion_directives 字段 |
| `schemas/quality_score.schema.json` | 新增 generation_mode / mode_adjusted_threshold / expansion_quality_check / draft_disclaimer_check |

### Pipeline 变更

| 文件 | 变更 |
|------|------|
| `pipeline/pipeline_types.py` | 新增 MODE_DEFAULT_THRESHOLDS / STRICT_DIMENSION_MIN / GENERATION_MODE_FLAGS / VALID_GENERATION_MODES；PipelineInput 新增 generation_mode；PipelineReport 新增 7 个扩写追踪字段 |
| `pipeline/run_pipeline.py` | 模式感知阈值注入；quality gate None fallback；expansion 字段 fallback；official_use_allowed 防覆盖；mode_adjusted_threshold 注入 prompt |
| `pipeline/output_formatter.py` | 三模式差异化 advisory 信息 |
| `pipeline/input_parser.py` | 支持 generation_mode JSON 输入解析 |

---

## 3. 端到端验收结论

### 测试规模

- 单元测试：80/80 通过（13 新 + 18 阶段2 + 27 阶段1 + 22 回归）
- 端到端测试：4 输入 × 2-3 模式 = 10 次真实 pipeline 调用（130-217 秒/次）

### 核心验证结果

| 验证项 | 结果 |
|--------|:----:|
| 模式阈值分流（8/7/6） | ✅ |
| official_use_allowed 区分（True/requires/false） | ✅ |
| fact_safety / risk_control 严格底线 8.0 | ✅ |
| 不编造具体事实（包括风险诱导场景） | ✅ |
| creative_mimic 边界（不可正式发布） | ✅ |
| creative_mimic quality_gate_pass 不再 false negative | ✅（阶段 4.1 修复） |
| expansion 字段 fallback 标记缺失 | ✅（阶段 4.1 修复） |
| review 识别 unsafe_fabrication | ✅ |
| v0.1.3 向后兼容 | ✅ |

### assisted_expansion 主观评价

以下为 OpenClaw 自动主观评价（非人工评分），仅供参考：

| 维度 | 评价 |
|------|:----:|
| autonomous_drafting_score（自主草拟能力） | 7/10 |
| mango_style_score（芒果风格） | 6/10 |
| factual_safety_score（事实安全） | 9/10 |
| usability_score（实际可用性） | 7/10 |

assisted_expansion 比 safe_official 更丰富（+30%~40% 字数），但扩写主要在结构和表达层面，未大幅增加实质内容。

---

## 4. P0/P1/P2 问题处理

| 级别 | 问题 | 状态 |
|:----:|------|:----:|
| P1 | creative_mimic quality_gate_pass false negative | ✅ 修复（4.1） |
| P1 | expansion 字段缺失 | ✅ 修复（prompt + fallback） |
| P1 | official_use_allowed 被覆盖 | ✅ 修复（代码层） |
| P2 | draft schema 不接受空数组 | ✅ 修复 |
| P2 | 模型忽略 generation_mode 变量 | ⚠️ 已缓解（代码层修正，理想需模型改进） |
| P2 | expansion_report 模型未稳定生成 | ⚠️ 已缓解（fallback 机制有效） |

**无 P0 问题。**

---

## 5. 为什么 v0.1.4 不等于"允许乱编"

v0.1.4 的扩写机制有严格的边界控制：

1. **事实红线不变**：所有模式都不允许编造具体领导、数据、时间、地点、荣誉、政策依据
2. **扩写范围明确**：仅允许结构句、过渡句、泛化战略表达、领导讲话句式风格、芒果系修辞
3. **追踪机制完整**：所有非用户明确提供的内容必须进入 expansion_report
4. **review 审查**：扩写内容被分为 acceptable / unsafe / confirmation_required 三类
5. **强制人审**：assisted_expansion 标记 requires_human_confirmation；creative_mimic 强制 human_review + 不可正式发布
6. **strict 维度不降**：fact_safety 和 risk_control 始终 8.0 最低阈值
7. **fallback 保障**：模型未输出扩写追踪信息时，pipeline 自动标记 manual_review_required

v0.1.4 做的是**在安全范围内释放合理的表达扩写**，不是放松安全。

---

## 6. 仍需人工复核的场景

1. **assisted_expansion 全部输出**：system 扩写的结构和表达需确认
2. **creative_mimic 全部输出**：只能作灵感参考，任何使用需人工重写
3. **fact_safety < 8**：存在疑似新增事实
4. **risk_control < 8**：存在风险控制隐患
5. **confirmation_required 列表**：系统推断但需核实的内容
6. **quality_gate_pass = false + warn_and_output**：质量不达标但仍输出的稿子
