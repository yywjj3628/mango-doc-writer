# Mango Doc Writer — OpenClaw Skill 使用指南

## 1. Skill 目标

在 OpenClaw 对话中，用户提交文案需求和初稿，Skill 自动调用六阶段管线，返回芒果系公文成稿。

## 2. 适用场景

- 生成/改写芒果系新闻稿
- 撰写公文（请示/报告/通知/函/通报）
- 整理会议纪要
- 起草领导讲话
- 撰写总结、汇报材料
- 将初稿优化为芒果系风格

## 3. 不适用场景

- 普通聊天
- 翻译
- 排版
- 法律/医疗/金融专业内容

## 4. 用户输入示例

### 示例 1：新闻稿
```
请把下面素材写成芒果系新闻稿，正式、有传播感：
5月20日，文化科技融合创新活动在马栏山举行。活动现场发布三项创新成果。
```

### 示例 2：请示
```
请写成向集团申请专项预算支持的请示：
目前项目已完成前期筹备，但后续推广需要专项预算支持。
```

### 示例 3：会议纪要
```
请整理成会议纪要：
会议研究了项目推进、责任分工和下阶段时间节点。
```

## 5. OpenClaw 调用流程

```
用户消息 → 触发 mango-doc-writer Skill
→ 构造 JSON 输入（requirement + draft）
→ python scripts/run_input.py --stdin
→ 六阶段管线执行
→ 输出 final_markdown + 待确认项 + 风险
```

## 6. 输出示例

```
# 文化科技融合创新活动在马栏山举行

5月20日，文化科技融合创新活动在马栏山举行。...

---
📋 **待确认项**
- 主送单位正式称谓: 需确认单位全称
- 具体日期: 5月20日需核实

⚠️ **剩余风险**
🟡 部分事实来源待确认

文种: 新闻稿 | 风险: low | RAG: success | 模型: deepseek-v4-flash
```

## 7. 如何指定文种

用户可在需求中明确指定："请写成**请示**"、"写成**会议纪要**"。
如果不指定，classify 阶段自动判断。

## 8. 如何要求 DOCX

用户说"生成 Word 文档"时，OpenClaw 设置 `output_formats: ["markdown", "docx"]`。
默认只输出 Markdown。

## 9. 如何理解【待确认】

待确认项是模型标记为"需要人工确认"的内容：
- 缺失的领导姓名/职务
- 缺失的单位全称
- 需核实的事实数据
- 不确定的称谓用法

## 10. 常见失败原因

### missing_api_key
DEEPSEEK_API_KEY 未配置 → 检查 .env

### schema_validation_error
模型输出格式异常 → 系统自动 sanitizer + fallback 处理

### RAG unavailable
RAG 服务不可达 → draft 跳过风格参考，不影响核心生成

### high-risk sanitizer
body_rewritten 等字段被强制修正 → 建议人工复核

## 11. 如何查看 reports

每个运行的详细结果保存在 `outputs/<timestamp>/`

## 12. 如何查看 outputs

```bash
ls -lt outputs/
```

## 13. 人工复核建议

如果出现以下标记，建议人工复核：
- 🔴 critical 级别 remaining_risks
- ⚠️ high-risk sanitizer
- 3 个以上 manual_confirmation_fields

---

*文档版本: 阶段 17 | 2026-05-28*
