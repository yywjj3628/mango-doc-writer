# 规则候选目录

> 用途：存放从语料中萃取的规则候选，等待人工确认后导入正式规则库

---

## 目录结构

```
rule-candidates/
├── README.md                           # 本文件
├── c2.1-rule-candidate-schema.json     # JSON Schema 定义
├── c2.1-rule-candidate-schema.md       # Schema 说明文档
├── c2.1-human-review-template.md       # 人工确认模板（Markdown）
├── c2.1-human-review-template.csv      # 人工确认模板（CSV）
├── c2.2-leader-organization-candidates.jsonl  # C2.2 萃取的领导/组织候选（待生成）
└── c2.3-reviewed-candidates.jsonl      # C2.3 人工确认后的候选（待生成）
```

---

## 工作流程

```
1. C2.1 Schema 设计 ✅
   ↓
2. C2.2 语料萃取 → 生成 *-candidates.jsonl
   ↓
3. C2.3 人工确认 → 使用 review template
   ↓
4. 确认通过 → 导入正式规则库（references/）
```

---

## 候选类型

| 类型 | 说明 | 优先级 |
|------|------|--------|
| leader_title | 领导姓名职务 | 高 |
| subsidiary_affiliation | 子公司归属 | 高 |
| company_alias | 公司简称 | 高 |
| doc_type_rule | 文种规则 | 中 |
| style_phrase | 风格表达 | 中 |
| risk_rule | 风险规则 | 中 |
| field_hint_rule | 字段提示规则 | 低 |

---

## 正式规则库路径

- `references/doc-type-rules.md` — 文种规则
- `references/org-title-dictionary.yaml` — 组织/领导/称谓
- `references/style-rag-policy.md` — RAG 策略

---

*目录创建时间：2026-06-02 14:34 UTC*
