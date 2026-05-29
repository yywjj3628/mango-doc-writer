# 测试编号：003-report

## 测试目标

验证正式报告不得夹带请示事项：

1. classify 识别为报告；
2. extract 不抽取请求事项（内容无请求信号）；
3. draft 按报告格式生成；
4. **不得出现请示结尾**（"妥否，请批示""请批复""请批准"）；
5. **不得出现请示事项**（"请给予支持""请予保障"）；
6. review 能检出报告夹带请示的违规；
7. rewrite 能修正。

## 用户需求

请整理成向集团汇报的正式报告。

## 用户初稿

今年以来，相关工作围绕重点任务推进，完成了前期梳理、资源协调和阶段性复盘。下一步将继续加强统筹，推动重点任务落地。

## 预期 classify

- doc_type: 报告
- direction: 上行文
- style_level: 2
- risk_level: low
- 是否应 conflict_detected: false
- 判断理由: 用户明确"汇报"，内容为工作进展和下一步计划，无请求批准/批复/拨款信号，符合报告特征

## 预期 extract

必须抽取：

- time: ["今年以来"]
- location: []
- organizations: ["集团"]
- leaders: []
- products: []
- projects: ["重点任务"]
- events: []
- data: []
- achievements: ["完成了前期梳理", "资源协调", "阶段性复盘"]
- problems: []
- requests: []（无请求信号）

必须进入 missing_fields：

- 具体项目/任务名称
- 汇报单位名称
- 具体数据（完成了多少项任务等）

必须进入 cannot_infer：

- 具体项目名称
- 具体数据
- 具体成果

必须进入 risk_flags：

- 内容较为笼统，缺少具体数据支撑

## 预期 plan

应采用结构：

- 第一部分：工作概述/背景
- 第二部分：已完成工作（前期梳理、资源协调、阶段性复盘）
- 第三部分：下一步工作计划
- 结尾：特此报告

必须 blocked_items：

- 不得编造具体数据
- 不得编造项目名称
- 不得添加请示事项
- 不得使用"妥否，请批示"结尾
- 不得使用"请批复""请批准"

必须 manual_confirmation_fields：

- 具体项目/任务全称
- 汇报单位名称
- 主送单位全称

## 预期 draft

允许出现：

- 报告标准结构
- "特此报告"结尾
- 前期梳理、资源协调、阶段性复盘
- 加强统筹、推动重点任务落地
- 芒果系正式公文表达

不得出现：

- 妥否，请批示
- 请批复、请批准、请予支持
- 请集团给予经费保障
- 具体编造的数据
- 取得显著成效（无依据）
- 奋楫扬帆等过度表达（style_level=2 应克制）

必须 warnings：

- 具体项目名称缺失
- 缺少数据支撑

## 预期 review

必须发现的问题（如 draft 违规）：

- issue type: doc_type_error / level: critical / detail: 如果 draft 出现"请批复""请批准""妥否，请批示"等请示结尾
- issue type: fact_not_grounded / level: medium / detail: 如果 draft 出现用户未提供的具体数据
- issue type: style_overdone / level: low / detail: 如果 draft 出现过度宣传表达

## 预期 rewrite

应修复：

- 删除任何请示结尾和请示事项
- 删除编造的具体数据
- 修正过度宣传表达

应保留：

- 报告结构
- 用户提供的所有事实
- "特此报告"结尾

最终稿仍需人工确认：

- 具体项目/任务全称
- 汇报单位名称

## 验收标准

1. classify 输出 doc_type=报告，direction=上行文
2. extract requests 为空数组
3. draft 结尾为"特此报告"，不含请示表达
4. review 能检出报告夹带请示违规（如有）
5. rewrite 删除所有请示事项
6. final_checks.doc_type_fixed = true
7. rewrite_policy 七项均为 true
