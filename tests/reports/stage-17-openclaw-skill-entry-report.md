# Stage 17 — OpenClaw Skill 入口固化报告

## 执行时间
2026-05-28 17:00–17:25 UTC

## 1. 新增文件清单

| 文件 | 用途 |
|------|------|
| entry/README.md | 入口说明 |
| entry/openclaw_entry.md | OpenClaw 调用流程 |
| entry/input_template.json | 输入模板 |
| pipeline/input_parser.py | 用户输入解析（结构化+自然语言） |
| pipeline/output_formatter.py | 输出格式化（用户可读） |
| docs/mango-doc-writer-openclaw-skill-guide.md | Skill 使用指南 |

## 2. 修改文件清单

| 文件 | 改动 |
|------|------|
| SKILL.md | 重写，加入触发条件/调用流程/输出策略/开发阶段 |
| scripts/run_input.py | 重写，支持 --stdin/--stdout/--output-dir/--format |
| README.md | 无改动（阶段 16 已加链接） |

## 3. SKILL.md 修改了什么

- 明确触发条件（10+ 场景）和不触发条件（6 个排除）
- OpenClaw 调用流程（用户对话 → 构造 JSON → run_input.py → pipeline → 输出）
- 输入格式（requirement/draft/specified_doc_type/target_unit/scene/output_formats）
- 输出策略：默认展示 final_markdown + 待确认项 + 风险；不展示六阶段 JSON
- 输出格式策略表（公文类可选 DOCX，非公文类默认 Markdown）
- 风险提示策略（mc/risks/high-risk sanitizer 必须展示）
- 开发阶段表更新到 17

## 4. input_parser 如何工作

- **结构化 JSON**：直接映射字段
- **自然语言**：轻量正则解析，分离 requirement/draft，提取文种/主送单位/场景关键词
- 不补事实、不做文种判断（交给 classify 阶段）

## 5. output_formatter 如何工作

- `format_output()` → JSON 格式（包含所有字段）
- `format_user_text()` → 用户可读文本（用于 OpenClaw 对话）
- 默认展示 final_markdown + 待确认项 + 风险 + 摘要
- 失败时展示 failed_stage + error + suggestion
- 不暴露六阶段 JSON 全量

## 6. run_input.py 如何适配 OpenClaw

- `--stdin`：从 stdin 读取 JSON（OpenClaw 管道模式）
- `--stdout`：输出 JSON 到 stdout（脚本化调用）
- `--output-dir`：指定输出目录
- `--format`：markdown / docx / markdown,docx

## 7. 3 个真实输入测试结果

| # | 类型 | 状态 | 耗时 | RAG | 待确认 | 风险 | DOCX |
|---|------|------|------|-----|--------|------|------|
| 1 | 新闻稿 | ✅ success | 124s | success,6 | 0 | 3 | — |
| 2 | 请示 | ✅ success | 163s | success,6 | 4 | 4 | — |
| 3 | 会议纪要 | ✅ success | 135s | success,6 | 4 | 5 | — |

### Test 1 新闻稿输出亮点
- ✅ final_markdown 清晰展示
- ✅ 无"领导高度肯定"等污染
- ✅ 缺失信息用概括写法（不编造）
- ✅ 剩余风险正确标记（成果名称/领导出席/参与单位）

### Test 2 请示输出亮点
- ✅ 正确识别为请示（上行文）
- ✅ 无"特此报告"污染
- ✅ "妥否，请批示"保留（请示格式正确）
- ✅ 缺失项用【待确认】占位
- ✅ 4 个待确认项全部标记

### Test 3 会议纪要输出亮点
- ✅ 缺失会议时间/地点/人员用【待确认】
- ✅ 不虚构会议基本信息
- ✅ 责任分工正确提取
- ✅ 4 个待确认项全部标记

## 8. final_markdown 是否生成
✅ 3/3 全部生成

## 9. manual_confirmation_fields 是否展示
✅ 3/3 全部展示（test1=0合理, test2=4, test3=4）

## 10. DOCX 是否按需生成
默认不生成（Markdown-first）。用户请求 DOCX 时才调用 typeset-engine。

## 11. 是否修改 prompts/schemas/references
**❌ 未修改**

## 12. 是否影响 pipeline
**❌ 无影响** — 仅新增入口层和格式化层，未修改六阶段业务逻辑

## 13. 回归测试
✅ 10/10 ALL PASS（阶段 15.3 的结果未被影响）

## 14. API key 安全
✅ outputs/ 中 0 matches

## 15. 建议
**✅ 建议进入真实文章试跑**

Skill 入口已就绪：
- 触发条件明确
- 输入解析（结构化+自然语言）
- 输出格式化（用户可读）
- 待确认项和风险强制展示
- 失败处理完整
- 3 个真实场景验证通过

---
*报告生成时间: 2026-05-28 17:25 UTC*
