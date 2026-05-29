# Stage 15 — DeepSeek API 自动化接入报告

## 执行时间
2026-05-28 14:38–15:45 UTC

## 1. 是否成功接入 DeepSeek API
**✅ 成功** — 使用 OpenAI-compatible SDK，`response_format={"type": "json_object"}`

## 2. API key 是否只来自环境变量
**✅ 是** — 通过 `DEEPSEEK_API_KEY` 环境变量读取，不写死、不提交、不记录日志

## 3. model_client.py 实现方式
- 延迟初始化 OpenAI client（避免 import 时要求 key）
- 支持 response_format json_object
- 内置 JSON 清洗：剥离代码块 → 截取 { } → json.loads
- 失败时保存原始输出到 `tests/reports/debug/<stage>-raw-output.txt`
- 最多重试 `DEEPSEEK_MAX_RETRIES` 次（默认 2）

## 4. rag_client.py 实现方式
- 调用 VPS RAG 端点 `localhost:8000/search`
- 10 种文种各有查询模板（2 条 query / 文种）
- 返回符合 04-draft.md 预期的 style_references 结构
- RAG 失败 → 返回空数组，不阻塞 pipeline
- **实际验证**：rag_status=success, rag_count=6

## 5. call_stage() 实现方式
- 加载 Prompt 文件 + 注入上下文（前序阶段结果）
- draft 阶段注入 style_rag 风格参考
- system prompt 注入 schema 约束（schema_prompt.py 自动生成）
- 调用 model_client.call_llm_json()
- 返回后执行 sanitizer（strip_extra + fill_missing + fix_const + fix_null）
- 再执行 jsonschema.validate
- 每次修复记录到 sanitizer_report.json

## 6. schema_prompt.py 实现方式
- 从 schema JSON 自动提取 enum、required、string 字段
- 递归处理嵌套对象和数组项
- 输出注入 system prompt，提醒模型遵守约束

## 7. Sanitizer 三件套
| 函数 | 功能 | 风险级别 |
|------|------|---------|
| `_strip_extra_fields()` | 递归移除 additionalProperties=false 不允许的字段 | low |
| `_fill_missing_required()` | 递归填充缺失的 required 字段（按类型给默认值） | medium |
| `_fix_const_fields()` | 递归修复 const 约束字段 | medium/high |
| `_fix_null_strings()` | null string → "" | low |

每次修复记录：path, before, after, fix_type, risk, reason

## 8. 002 自动跑通结果
**✅ 通过**（313.9s）
- classify：请示（检测到与"报告"冲突）
- 六阶段 schema 全部通过
- final_markdown：无"特此报告"
- RAG：rag_status=success, style_references_count=6
- sanitizer：8 个 medium 修复（fill_missing_boolean/number），0 high
- 人工确认项：11，剩余风险：5

## 9. 009 自动跑通结果
**✅ 通过**（约 330s，进程输出后被 SIGKILL 但文件完整）
- classify：新闻稿
- review：pass=true, rewrite_required=false（无 RAG 污染，直接通过）
- final_markdown：无"领导高度肯定"、无"广泛影响"
- rewrite_policy：全 true
- RAG：rag_status=success, style_references_count=6
- sanitizer：0 个修复（模型输出完全合规）

## 10. 每阶段 schema 校验
| Case | classify | extract | plan | draft | review | rewrite |
|------|----------|---------|------|-------|--------|---------|
| 002  | ✅       | ✅      | ✅   | ✅    | ✅      | ✅      |
| 009  | ✅       | ✅      | ✅   | ✅    | ✅      | ✅      |

## 11. 是否出现 invalid_json
**是** — 002 第二轮 extract 首次 JSON 解析失败（Expecting ',' delimiter），自动重试成功
**不是致命问题** — model_client 内置重试机制处理

## 12. 是否出现 schema_validation_error
**否** — schema_guard + sanitizer 双重保障后，所有 12 次阶段调用均通过 schema 校验

## 13. 是否出现 RAG 污染
**否** — 009 final_markdown 不含"领导高度肯定""广泛影响"

## 14. 是否修改 prompts / schemas / references
**❌ 未修改** — 均未被触碰

## 15. Sanitizer 风险分布
| Case | total | low | medium | high |
|------|-------|-----|--------|------|
| 002  | 8     | 0   | 8      | 0    |
| 009  | 0     | 0   | 0      | 0    |

## 16. 回归测试
**✅ 10/10 通过**（OpenClaw 手动模式不受影响）

## 17. 文件清单
### 新增
| 文件 | 用途 |
|------|------|
| `pipeline/model_client.py` | DeepSeek API 客户端 |
| `pipeline/rag_client.py` | VPS style_rag 检索客户端 |
| `pipeline/schema_prompt.py` | Schema 约束自动提取 |
| `.env.example` | 环境变量模板 |

### 修改
| 文件 | 修改内容 |
|------|----------|
| `pipeline/run_pipeline.py` | DeepSeek API 调用 + sanitizer + sanitizer_report |
| `pipeline/pipeline_types.py` | 新增 rag_status/sanitizer 字段 |
| `pipeline/README.md` | API 自动化说明 |
| `README.md` | API 自动化运行入口 |
| `SKILL.md` | 阶段 15 标记完成 |

### 未修改
- prompts/*（0 处修改）
- schemas/*（0 处修改）
- references/*（0 处修改）
- tests/cases/*（0 处修改）
- render/*（0 处修改）

## 18. 建议
- **是否建议跑全量 10 case**：✅ 建议跑一次全量验证 sanitizer 稳定性
- **是否建议部署 VPS**：✅ 代码已就绪，002/009 验证通过
