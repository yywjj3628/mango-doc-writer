# OpenClaw 入口调用说明

## 1. 触发条件

OpenClaw 在以下对话场景触发 mango-doc-writer Skill：

- "请写成新闻稿/请示/报告/通知/函/通报"
- "请把素材整理成芒果系文案"
- "写一份领导讲话/会议纪要/汇报材料/总结"
- "把这段初稿改写成芒果风格"

## 2. 调用流程

```
用户对话
  → OpenClaw 识别需求
  → 构造 JSON
  → echo '<JSON>' | python scripts/run_input.py --stdin
  → 读取 stdout
  → 展示 final_markdown + 待确认项 + 风险
```

## 3. 构造输入

从用户对话中提取：

| 字段 | 来源 | 示例 |
|------|------|------|
| requirement | 用户描述 | "请写成芒果系新闻稿" |
| draft | 素材/初稿 | 用户粘贴的内容 |
| specified_doc_type | 显式指定 | "新闻稿" |
| target_unit | 主送单位 | "集团" |
| scene | 使用场景 | "对外发布" |
| output_formats | 默认 markdown | ["markdown"] |

## 4. 展示输出

### 必须展示
- final_markdown（正文）
- 待确认项（manual_confirmation_fields）
- 剩余风险（remaining_risks）

### 不展示
- 六阶段完整 JSON
- sanitizer_report 详情（除非有 high-risk）

### 可选展示
- pipeline 摘要（文种/风险/RAG/模型）
- DOCX 文件路径（如果生成）

## 5. 失败处理

展示：
- 失败阶段
- 错误类型
- 错误描述
- 建议处理方式

## 6. DOCX 请求

当用户说"生成 Word"或"输出 docx"时：
```json
{"output_formats": ["markdown", "docx"]}
```

## 7. 查看 outputs

所有输出保存在 `outputs/<timestamp>/`

## 8. 查看 debug

Schema 校验失败时，debug 文件在 `tests/reports/debug/`

## 9. 完整示例

用户："请把下面素材写成芒果系新闻稿，正式有传播感。5月20日，文化科技融合创新活动在马栏山举行..."

OpenClaw 构造：
```json
{
  "requirement": "请写成芒果系新闻稿，正式、有传播感",
  "draft": "5月20日，文化科技融合创新活动在马栏山举行。",
  "specified_doc_type": "新闻稿",
  "target_unit": null,
  "scene": "对外发布",
  "output_formats": ["markdown"]
}
```

调用并展示结果。
