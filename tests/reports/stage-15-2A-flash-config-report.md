# Stage 15.2A — Flash 模型配置报告

## 执行时间
2026-05-28 15:50–16:10 UTC

## 1. 是否已切换默认模型为 deepseek-v4-flash
**✅ 是** — `DEEPSEEK_MODEL` 默认值改为 `deepseek-v4-flash`

## 2. Fallback 模型是否配置为 deepseek-v4-pro
**✅ 是** — `DEEPSEEK_FALLBACK_MODEL` 默认 `deepseek-v4-pro`

## 3. Fallback 是否启用
**✅ 是** — `DEEPSEEK_ENABLE_FALLBACK` 默认 `true`

## 4. 002 是否跑通
**✅ 通过** — 145.8s（之前 pro 313.9s，提速 2.15 倍）

## 5. 009 是否跑通
**✅ 通过** — 150.0s

## 6. 每个 case 是否出现 fallback
| Case | fallback_count |
|------|---------------|
| 002  | 0 |
| 009  | 0 |

## 7. 每个阶段实际使用模型
两个 case 六阶段全部使用 `deepseek-v4-flash`，无 fallback。

## 8. Schema 校验是否通过
| Case | classify | extract | plan | draft | review | rewrite |
|------|----------|---------|------|-------|--------|---------|
| 002  | ✅       | ✅      | ✅   | ✅    | ✅      | ✅      |
| 009  | ✅       | ✅      | ✅   | ✅    | ✅      | ✅      |

## 9. Sanitizer 是否触发
| Case | 总修复 | low | medium | high |
|------|-------|-----|--------|------|
| 002  | 待确认 | —   | —      | —    |
| 009  | 1      | 0   | 1      | 0    |

009 sanitizer 详情：review.manual_confirmation_fields[0].required_before_final（fill_missing_boolean）

## 10. RAG 是否成功
| Case | rag_status | style_references_count |
|------|-----------|----------------------|
| 002  | success   | 6                    |
| 009  | success   | 6                    |

## 11. 是否修改 prompts / schemas / references
**❌ 未修改**

## 12. 新增机制
- **enum 修复**：`_fix_enum_values()` 自动将非法 enum 值转为 "other"（low risk）
- **fallback 触发**：schema 校验失败时自动 fallback 到 pro 重试一次
- **model_meta 追踪**：每阶段记录实际使用模型、是否 fallback、fallback 原因
- **pipeline_report 增强**：新增 default_model/fallback_model/fallback_enabled/stage_model_usage/fallback_count

## 13. 成本对比
| 模型 | 002 耗时 | 009 耗时 |
|------|---------|---------|
| deepseek-v4-pro（之前） | 313.9s | ~330s |
| deepseek-v4-flash（现在） | 145.8s | 150.0s |
| **提速** | **2.15x** | **2.2x** |

## 14. 建议
**✅ 建议进入 15.2 全量 10 case** — flash 速度和合规性均验证通过，fallback 机制就绪。
