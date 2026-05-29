# OpenClaw 入口

## 调用方式

OpenClaw 在识别到芒果系文案需求后，应调用：

```bash
python scripts/run_input.py --stdin
```

或：

```bash
python scripts/run_input.py inputs/example.json --stdout
```

## 输入构造

OpenClaw 应将用户对话整理为 JSON 并通过 stdin 传递：

```json
{
  "requirement": "请写成芒果系新闻稿",
  "draft": "用户素材内容...",
  "specified_doc_type": "新闻稿",
  "target_unit": null,
  "scene": "对外发布",
  "output_formats": ["markdown"]
}
```

## 输出读取

- `final_markdown`: 主输出，直接展示给用户
- `manual_confirmation_fields`: 待确认项，必须展示
- `remaining_risks`: 剩余风险，必须展示
- 六阶段 JSON 不默认展示

## DOCX 请求

当用户明确要求 DOCX 时，设置 `output_formats: ["markdown", "docx"]`。

## 失败处理

失败时输出包含 `failed_stage`、`error_type`、`error_message`、`suggestion`。

## 查看 debug 报告

`tests/reports/debug/` 目录下保留最近的 debug 文件（7 天轮转）。
