# render 模块

## 定位

render 模块是 mango-doc-writer 六阶段文本管线的可选排版扩展。

输入：`rewrite_result.final_markdown`（六阶段管线最终输出的 Markdown 正文）
输出：DOCX / PDF / Markdown 文件

## 职责边界

**typeset-engine 可以：**
- 调整版式（页边距、行距、字体）
- 调整标题样式（字号、加粗）
- 调整段落样式
- 生成 DOCX / PDF

**typeset-engine 不可以：**
- 新增事实
- 修改正文含义
- 修正文种
- 替代 review / rewrite
- 调用 RAG
- 参与六阶段流程

## 文种映射

`doc_type_mapping.yaml` 定义了每种文种对应的排版模板和主题：

| 文种 | 模板 | 主题 |
|------|------|------|
| 请示/报告/通知/函/通报 | official_document | cms |
| 会议纪要 | meeting_minutes | ms |
| 新闻稿 | news_article | cicc |
| 领导讲话 | speech | ms |
| 总结/汇报材料 | work_summary/work_report | cms |

## 使用方式

### 输出策略（Markdown-first）

- **所有文种**：必须输出 `final_markdown.md`（主交付格式）
- **公文类**（请示/报告/通知/函/通报）：默认同时生成 DOCX
- **非公文类**（新闻稿/讲话稿/总结/汇报材料/会议纪要）：默认只生成 Markdown，用户明确 `--format docx` 时才生成 DOCX

### 单 case 排版

```bash
cd skills/mango-doc-writer

# 生成 DOCX
python scripts/render_case.py tests/reports/002-fake-report-real-request --format docx

# 生成 DOCX + PDF
python scripts/render_case.py tests/reports/001-news --format docx pdf

# 默认生成 DOCX
python scripts/render_case.py tests/reports/005-meeting-minutes
```

### 输出目录

排版结果保存在 `tests/reports/<case_id>/render/`：

```
render/
├── final.md              # final_markdown 副本
├── final.docx            # DOCX 输出（如请求）
├── final.pdf             # PDF 输出（如请求）
├── typeset_input.json    # typeset-engine 输入 JSON（调试用）
└── render_report.json    # 渲染报告
```

### render_report.json 解读

```json
{
  "template_used": "official_document",
  "theme": "cms",
  "body_modified": false,
  "facts_added": false,
  "warnings": []
}
```

- `body_modified`: 排版过程中是否修改了正文（应始终为 false）
- `facts_added`: 排版过程中是否新增了事实（应始终为 false）
- `warnings`: 排版警告（如 DOCX 生成失败）

## 排版失败处理

如果 typeset-engine 调用失败：

1. `final_markdown.md` 不受影响（原始文件保留）
2. 返回 `status: "failed"` 或 `status: "partial"`
3. 错误信息记录在 `render_report.json` 的 `warnings` 中
4. 六阶段文本管线不受影响

## 后续扩展

- 增加更多排版模板（在 doc_type_mapping.yaml 中配置）
- 支持自定义主题
- 支持 PDF 生成
- 批量排版脚本
