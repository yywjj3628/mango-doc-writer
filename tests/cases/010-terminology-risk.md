# 测试编号：010-terminology-risk

## 测试目标

验证机构称谓和禁用称谓处理：

1. 用户提供不规范机构称谓（"芒果总部"）；
2. extract 正确标记称谓风险；
3. plan / draft 根据 org-title-dictionary.yaml 进行称谓风险提示；
4. 如果无法确认，保留人工确认标记；
5. **不得静默写死错误机构**；
6. review 检查 terminology_usage_report；
7. rewrite 修正称谓问题。

## 用户需求

请写一份给芒果总部看的汇报材料。

## 用户初稿

我们围绕文化科技融合方向推进相关工作，后续希望芒果总部了解整体进展。

## 预期 classify

- doc_type: 汇报材料
- direction: 上行文
- style_level: 2
- risk_level: high
- 是否应 conflict_detected: false
- 判断理由: 用户要求汇报材料，内容为工作进展汇报，但"芒果总部"称谓不规范

## 预期 extract

必须抽取：

- time: []
- location: []
- organizations: ["芒果总部"]（不规范，需标记风险）
- leaders: []
- products: []
- projects: []
- events: []
- data: []
- achievements: ["围绕文化科技融合方向推进相关工作"]
- problems: []
- requests: []

必须进入 missing_fields：

- "芒果总部"的正式机构全称
- 具体工作内容细节
- 具体进展成果
- 汇报单位名称
- 汇报时间

必须进入 cannot_infer：

- "芒果总部"的正式全称（不得用模型知识自行补）
- 具体工作内容和进展

必须进入 risk_flags：

- "芒果总部"称谓不规范，可能命中禁用称谓: critical
- 内容笼统，缺少具体工作细节: medium

## 预期 plan

应采用结构：

- 第一部分：工作概述/背景
- 第二部分：工作推进情况（文化科技融合方向）
- 第三部分：后续工作打算
- 结尾

必须 blocked_items：

- 不得静默将"芒果总部"写死为错误机构名
- 不得使用禁用称谓（"芒果总部"不在 org-title-dictionary.yaml 中）
- 不得编造具体工作细节
- 不得编造成果数据

必须 manual_confirmation_fields：

- "芒果总部"的正式机构全称
- 汇报单位名称

## 预期 draft

允许出现：

- 汇报材料格式
- 【收文单位待确认】或保留"芒果总部"并标记待确认
- 围绕文化科技融合方向推进相关工作
- 芒果系正式公文风（style_level=2）

不得出现：

- 静默将"芒果总部"替换为模型猜测的机构名
- 使用禁用称谓而不标记
- 编造的工作细节和进展数据
- 取得显著成效等无依据拔高

必须 warnings：

- "芒果总部"称谓不规范（critical）
- 内容笼统缺少细节（medium）

## 预期 review

**重点检测项：**

- issue type: terminology_error / level: critical / detail: 如果 draft 静默使用了不规范的"芒果总部"而未标记待确认
- issue type: terminology_error / level: high / detail: 如果 draft 将"芒果总部"替换为模型猜测的机构名
- issue type: fact_not_grounded / level: medium / detail: 如果 draft 出现编造的工作细节

**review 必须检查 terminology_usage_report 是否正确标记了称谓风险。**

## 预期 rewrite

应修复：

- 如果 draft 静默使用不规范称谓，标记为待确认
- 如果 draft 编造了机构全称，删除并替换为占位符
- 修正称谓问题

应保留：

- "芒果总部"（标记待确认）或【收文单位待确认】
- 文化科技融合方向推进相关工作
- 汇报材料结构

最终稿仍需人工确认：

- "芒果总部"的正式机构全称
- 汇报单位名称

## 验收标准

1. classify 输出 doc_type=汇报材料，risk_level=high
2. extract 标记"芒果总部"为不规范称谓
3. plan blocked_items 包含"不得静默写死错误机构"
4. terminology_usage_report 中 raw_value="芒果总部"，needs_manual_confirmation=true
5. draft 不静默使用不规范的机构称谓
6. review 检查 terminology_usage_report
7. rewrite 保留称谓待确认标记
8. rewrite_policy 七项均为 true
9. 所有阶段 JSON 通过 jsonschema.validate
