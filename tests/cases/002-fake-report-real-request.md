# 测试编号：002-fake-report-real-request

## 测试目标

验证"用户指定报告，但内容信号指向请示"的经典冲突场景：

1. classify 能识别伪报告真请示；
2. conflict_detected = true；
3. 推荐修改为请示；
4. extract 正确抽取请求事项和缺失字段；
5. plan 按请示结构规划；
6. draft 按请示格式生成；
7. review 检查文种一致性；
8. rewrite 保留请示结构，不混用报告结尾。

## 用户需求

请写一份报告，向集团汇报项目情况，并请求集团给予专项预算支持。

## 用户初稿

目前项目已完成前期筹备，但后续推广需要专项预算支持，拟请集团给予经费保障。

## 预期 classify

- doc_type: 请示
- direction: 上行文
- style_level: 1
- risk_level: critical
- 是否应 conflict_detected: true
- 判断理由: 用户指定"报告"，但内容包含"请求预算支持""拟请集团给予经费保障"等请示信号，属于请示特征。存在文种冲突。

## 预期 extract

必须抽取：

- time: []
- location: []
- organizations: ["集团"]
- leaders: []
- products: []
- projects: ["项目"]（缺少正式名称）
- events: []
- data: []
- achievements: ["项目已完成前期筹备"]
- problems: ["后续推广需要专项预算支持"]
- requests: ["请求集团给予专项预算支持", "拟请集团给予经费保障"]

必须进入 missing_fields：

- 项目正式名称
- 预算金额（未提供具体数字）
- 主送单位全称
- 落款单位全称

必须进入 cannot_infer：

- 预算金额（用户未提供，绝对不能自动补充）
- 项目正式名称
- 主送单位全称

必须进入 risk_flags：

- request_without_amount（请求预算但无金额）: critical
- 伪报告真请示冲突: high

## 预期 plan

应采用结构（请示标准四段式）：

- 第一部分：请示缘由（项目已完成前期筹备）
- 第二部分：必要性与依据（后续推广需要专项预算支持）
- 第三部分：请示事项（拟请集团给予经费保障）
- 第四部分：期复语（妥否，请批示）

必须 blocked_items：

- 不得编造预算金额
- 不得编造项目正式名称
- 不得写成报告（结尾不能是"特此报告"）
- 不得一文多事

必须 manual_confirmation_fields：

- 文种确认（用户指定报告 vs 系统判断请示）
- 主送单位全称
- 落款单位全称
- 项目正式名称
- 预算金额

## 预期 draft

允许出现：

- 请示标题格式
- 妥否，请批示（请示标准结尾）
- 【主送单位待确认】
- 【落款单位待确认】
- 项目已完成前期筹备
- 后续推广需要专项预算支持
- 拟请集团给予经费保障

不得出现：

- 特此报告（报告结尾，不可混用）
- 具体预算金额
- 编造的项目正式名称
- "报告如下"然后"请批示"的混用结构
- 一文多事（除预算外不请示其他事项）

必须 warnings：

- 预算金额缺失（critical）
- 项目正式名称缺失（high）
- 文种冲突待确认（critical）

## 预期 review

必须发现的问题：

- issue type: doc_type_error / level: critical / detail: 如果 draft 写成了报告结构（如"特此报告"结尾），则文种错误
- issue type: fact_not_grounded / level: high / detail: 如果 draft 出现具体预算金额
- issue type: fact_not_grounded / level: high / detail: 如果 draft 出现编造的项目正式名称

## 预期 rewrite

应修复：

- 如果 draft 混用了报告结构，删除报告结尾，改为请示结尾
- 删除任何编造的预算金额和项目名称
- 确保结尾是"妥否，请批示"而非"特此报告"

应保留：

- 请示四段式结构
- 请求集团给予经费保障的核心请求
- 【主送单位待确认】等占位符
- 文种冲突标记

最终稿仍需人工确认：

- 文种确认（报告还是请示）
- 主送单位全称
- 落款单位全称
- 项目正式名称
- 预算金额

## 验收标准

1. classify 输出 doc_type=请示，conflict_detected=true
2. extract 不补充预算金额
3. plan 按请示四段式规划
4. draft 结尾为"妥否，请批示"，不含"特此报告"
5. draft 不含具体预算金额
6. review 能检出报告/请示混用问题
7. rewrite 修正文种混用，保留请示结构
8. manual_confirmation_fields 包含文种确认和预算金额
9. rewrite_policy 七项均为 true
10. fact_usage_report 中不含任何新增事实
