# 测试编号：007-summary

## 测试目标

验证工作总结不编造数据和荣誉：

1. classify 识别为总结；
2. extract 不补充数据；
3. draft 不编造成果数据、荣誉、奖项；
4. **不编造"取得显著成效"等无依据拔高**；
5. review 能检出无依据拔高；
6. rewrite 修正。

## 用户需求

请整理成阶段性工作总结，体现芒果系正式公文风。

## 用户初稿

今年一季度，部门围绕年度目标推进各项工作，完成了制度修订、流程优化和团队培训。下阶段将继续深化内部管理，提升运营效率。

## 预期 classify

- doc_type: 总结
- direction: 内部材料
- style_level: 2
- risk_level: low
- 是否应 conflict_detected: false
- 判断理由: 用户明确"阶段性工作总结"，内容为已完成工作和下一步计划，符合总结特征

## 预期 extract

必须抽取：

- time: ["今年一季度"]
- location: []
- organizations: []
- leaders: []
- products: []
- projects: ["年度目标", "制度修订", "流程优化", "团队培训"]
- events: []
- data: []
- achievements: ["完成了制度修订", "流程优化", "团队培训"]
- problems: []
- requests: []

必须进入 missing_fields：

- 部门名称
- 具体制度修订内容
- 具体流程优化内容
- 具体团队培训内容
- 量化数据（完成多少项修订、多少人参加培训等）

必须进入 cannot_infer：

- 量化数据
- 具体制度名称
- 具体流程名称

必须进入 risk_flags：

- 内容较为笼统，缺少量化数据

## 预期 plan

应采用结构：

- 第一部分：总体概述
- 第二部分：已完成工作（制度修订、流程优化、团队培训）
- 第三部分：存在问题（如有，用户未提供则简略或省略）
- 第四部分：下阶段工作计划（深化内部管理、提升运营效率）
- 结尾

必须 blocked_items：

- 不得编造量化数据
- 不得编造成果荣誉
- 不得编造奖项
- 不得使用"取得显著成效"等无依据拔高
- 不得编造部门名称

必须 manual_confirmation_fields：

- 部门名称
- 具体工作内容细节

## 预期 draft

允许出现：

- 总结标准结构
- 今年一季度
- 制度修订、流程优化、团队培训
- 深化内部管理、提升运营效率
- 芒果系正式公文表达（style_level=2）

不得出现：

- "取得显著成效""取得重大突破"
- "荣获XX奖""被评为XX"
- 具体量化数据（如"完成12项制度修订"——用户未提供）
- 编造的部门名称
- 过度宣传腔（style_level=2 应克制）

必须 warnings：

- 部门名称缺失
- 缺少量化数据支撑

## 预期 review

必须发现的问题：

- issue type: fact_not_grounded / level: high / detail: 如果 draft 出现"取得显著成效"等无依据拔高
- issue type: fact_not_grounded / level: high / detail: 如果 draft 出现编造的量化数据
- issue type: fact_not_grounded / level: critical / detail: 如果 draft 出现编造的荣誉或奖项

## 预期 rewrite

应修复：

- 删除"取得显著成效"等无依据拔高
- 删除编造的量化数据
- 删除编造的荣誉/奖项
- 替换为用户提供的原始表述

应保留：

- 制度修订、流程优化、团队培训
- 深化内部管理、提升运营效率
- 总结结构和格式

最终稿仍需人工确认：

- 部门名称

## 验收标准

1. classify 输出 doc_type=总结
2. extract 不补充量化数据
3. draft 不包含"取得显著成效"等无依据拔高
4. draft 不包含编造的荣誉/奖项
5. review 能检出无依据拔高（如有）
6. rewrite 删除拔高表述
7. fact_usage_report 中无新增事实
