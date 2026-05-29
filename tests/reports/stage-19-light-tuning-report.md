# Stage 19 — 轻量微调报告

## 执行时间
2026-05-28 17:32–17:40 UTC

## 1. 修改文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| references/org-title-dictionary.yaml | 修改 | 补充"久游网"产品条目 |
| prompts/02-extract.md | 修改 | 增加"后续工作事项抽取规则" |

## 2. org-title-dictionary.yaml 补充了什么

在 products 段新增 `jiuyou_platform` 条目：

```yaml
jiuyou_platform:
  official_name: "久游网"
  accepted_names: ["久游网"]
  aliases: ["久游网平台", "久游"]
  source: ["阶段18真实文章试跑反馈", "RAG语料"]
  needs_manual_confirmation: true
  center_role: false
  inheritance_allowed: true
  notes: "上海久之润信息技术有限公司运营的游戏平台。仅作为业务平台称谓补充，不作为本系统中心主体。"
```

## 3. 02-extract.md 补强了什么

在 fact_items 处理规则末尾新增"后续工作事项抽取规则"：
- 12 种表达模式必须抽取（做好…准备工作、推进…工作、完成…准备 等）
- 示例：半年报准备工作 → type=event/project
- 禁止补充内容/数据/责任部门/时间节点

## 4. YAML 是否解析通过
**✅ 通过** — yaml.safe_load 验证成功，jiuyou_platform.center_role=False

## 5. 10 case 回归是否通过
**✅ 10/10 ALL PASS**（schema校验 + markdown claims 检查不受 prompts 文本变更影响）

## 6. 真实文章重跑结果

002 汇报材料（久游网 + 半年报准备工作）重跑：

| 维度 | 修改前 | 修改后 |
|------|--------|--------|
| "半年报准备工作" | ❌ 遗漏 | ✅ 出现在 final_markdown 第5节 |
| extract fact_items | 未捕获 | ✅ type=project, confidence=0.95 |
| "久游网"称谓 | 标记"未在称谓库中确认正式名称" | 提示"称谓库提示该名称需确认是否为上海久之润信息技术有限公司" |
| 耗时 | 225.6s | 196.7s |
| RAG | success, 6refs | success, 6refs |
| 新增事实 | 无 | 无 |

## 7. "久游网"称谓风险是否降低
**✅ 降低** — 从"未在称谓库中"变为"称谓库提示需确认是否为上海久之润"，信息更精确

## 8. "半年报准备工作"是否被抽取
**✅ 被抽取** — extract_result.fact_items 中 type=project, value="半年报准备工作"

## 9. 是否修改 schemas
**❌ 未修改**

## 10. 是否修改 pipeline
**❌ 未修改**

## 11. 是否影响主链路
**❌ 无影响** — 仅修改了 references（数据层）和 prompts/02-extract.md（抽取规则文本）

## 12. 是否建议发布 v0.1.1
**✅ 建议发布 v0.1.1**

微调内容轻量、可控、可回归：
- 称谓库补充不改变系统定位
- extract 规则补强不改变"只抽取不创作"原则
- 10 case 回归无退化
- 真实文章遗漏问题已修复

---
*报告生成时间: 2026-05-28 17:40 UTC*
