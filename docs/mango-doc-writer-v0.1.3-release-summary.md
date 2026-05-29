# mango-doc-writer v0.1.3 发布摘要

**发布日期**: 2026-05-29
**版本主题**: Quality Gate — AI 成稿质量评分门禁 + 自动返修闭环

---

## 一句话说明

mango-doc-writer v0.1.3 在六阶段 Pipeline 基础上新增后置质量门禁，对 rewrite 输出的 final_markdown 进行六维度评分，低分自动返修，不达标则提示人工复核。

## 新增功能

1. **后置质量门禁**：rewrite 完成后对 final_markdown 进行六维度评分
2. **六大评分维度**：事实安全、文种匹配、芒果风格、逻辑完整、语言质量、风险控制
3. **自动返修闭环**：低于阈值时自动生成返修指令，交给 rewrite 执行定点改进
4. **warn_and_output 机制**：达到最大返修轮次仍不通过时，保留稿件但标记风险，提示人工复核
5. **可配置开关**：QUALITY_GATE_ENABLED / QUALITY_GATE_THRESHOLD / QUALITY_GATE_MAX_ROUNDS
6. **v0.1.2 兼容**：QUALITY_GATE_ENABLED=false 时完全回退旧流程

## 最终流程

```
classify → extract → plan → draft → review → rewrite
                                                ↓
                                      [quality gate 后置门禁]
                                          ↓         ↓
                                        pass    rewrite → 再评分
                                                  ↓
                                            warn_and_output
```

## 六大评分维度

| 维度 | 评估内容 | 评分范围 |
|------|----------|----------|
| fact_safety | 是否新增了用户未提供的事实 | 0-10 |
| doc_type_fit | 标题、结构、格式是否符合文种规范 | 0-10 |
| mango_style_fit | 表达是否符合芒果系气质 | 0-10 |
| logic_completeness | 结构是否完整、信息是否交代清楚 | 0-10 |
| language_quality | 用词是否准确、凝练、正式 | 0-10 |
| risk_control | 称谓、机构、数据、敏感表达是否稳妥 | 0-10 |

## 配置项

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| QUALITY_GATE_ENABLED | true | 开关，false 时回退 v0.1.2 旧流程 |
| QUALITY_GATE_THRESHOLD | 8 | 达标阈值（0-10） |
| QUALITY_GATE_MAX_ROUNDS | 2 | 最大返修轮次 |

## 测试验收结果

| 测试 | 结果 |
|------|------|
| 质量门禁测试（22 项） | 22/22 通过 |
| 旧 10 Case 回归测试 | 10/10 通过（真实端到端） |
| Fixtures Schema 校验 | 4/4 通过 |
| Prompt JSON 示例校验 | 4/4 通过 |
| Pipeline 模块导入 | 9/9 通过 |
| Prompt/Schema 枚举一致性 | 8/8 通过 |
| 功能一致性检查 | 10/10 通过 |
| pipeline_report 字段 | 12/12 存在 |

## 安全检查结果

- ✅ .env 在 .gitignore 中，不会进入版本控制
- ✅ .env 权限 600，仅 owner 可读
- ✅ deploy/env.example 使用占位符，无真实 key
- ✅ 日志和报告中无 API Key 泄露
- ✅ 无临时文件或调试残留

## 人工复核边界

以下情况系统会标记 `human_review_required=true`：

- fact_safety < 8：存在疑似新增事实
- risk_control < 8：存在风险控制隐患
- 达到最大返修轮次后仍存在低于阈值的维度

**重要**：
- 系统不能无人值守正式发稿
- 质量分不等于事实真伪保证
- 涉及领导职务、机构名称、日期、金额、数据、政策表述等仍需人工核对
- quality gate 不调用 RAG、不补充外部事实

## 是否建议发布

**✅ 建议发布。** 全部验收标准满足，无 P0/P1 阻塞项。

## 后续建议

1. **监控 quality gate 评分分布**：收集实际使用中的评分数据，评估阈值 8 是否合适
2. **扩展测试覆盖**：增加 quality gate 真实 LLM 评分的端到端测试
3. **优化 Prompt**：根据实际评分结果迭代 07-quality-score.md
4. **考虑阈值动态调整**：不同文种可能需要不同阈值
5. **收集用户反馈**：在实际使用中收集 quality gate 的有效性数据
