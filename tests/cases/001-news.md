# 测试编号：001-news

## 测试目标

验证新闻稿场景下六阶段闭环：

1. classify 能识别新闻稿（对外宣传，style_level=3）；
2. extract 能准确抽取时间、地点、事件、机构、成果；
3. draft 能写出有传播感的新闻稿正文；
4. **不编造领导出席**；
5. **不编造领导评价**；
6. **不编造具体成果名称**（用户未提供）；
7. RAG 只用于风格参考，不作为事实来源；
8. review 能发现事实溯源问题；
9. rewrite 不新增事实。

## 用户需求

请把下面素材写成芒果系新闻稿，风格正式、有传播感。

## 用户初稿

5月20日，文化科技融合创新活动在马栏山举行。活动现场发布了三项创新成果，来自湖南广电集团、芒果超媒等单位的代表参加交流。

## 预期 classify

- doc_type: 新闻稿
- direction: 对外宣传
- style_level: 3
- risk_level: low
- 是否应 conflict_detected: false
- 判断理由: 用户明确要求"新闻稿"，素材包含时间、地点、事件、机构等新闻要素，无文种冲突信号

## 预期 extract

必须抽取：

- time: ["5月20日"]
- location: ["马栏山"]
- organizations: ["湖南广电集团", "芒果超媒"]
- leaders: []（用户未提供任何领导信息）
- products: []
- projects: []
- events: ["文化科技融合创新活动"]
- data: []
- achievements: ["活动现场发布了三项创新成果"]
- problems: []
- requests: []

必须进入 missing_fields：

- 三项创新成果的具体名称（用户未提供）
- 参会具体人员名单
- 活动主办单位

必须进入 cannot_infer：

- 三项创新成果的具体名称
- 具体参会人员
- 活动影响范围

必须进入 risk_flags：

- 如果 draft 阶段出现"领导出席""领导高度肯定"等用户未提供的信息，应为 critical

## 预期 plan

应采用结构：

- 标题：新闻稿标题（含事件关键词）
- 导语：时间+地点+事件概述
- 主体：活动内容+成果发布+交流情况
- 结尾：活动背景/意义（不得编造）

必须 blocked_items：

- 不得编造领导出席
- 不得编造领导评价
- 不得编造成果具体名称
- 不得编造活动影响范围
- 不得编造参会人员名单

必须 manual_confirmation_fields：

- 活动主办单位全称
- 三项创新成果的正式名称

## 预期 draft

允许出现：

- 5月20日、马栏山、文化科技融合创新活动
- 湖南广电集团、芒果超媒
- 三项创新成果
- 新闻稿导语句式
- 芒果系新闻风格表达

不得出现：

- 领导高度肯定
- 领导出席并讲话
- 取得重大突破
- 产生广泛社会影响
- 具体成果名称（用户未提供）
- 奋楫扬帆、澎湃动能等过度宣传腔
- 任何用户初稿中不存在的事实

必须 warnings：

- 缺少具体成果名称
- 缺少主办单位
- 缺少领导信息（如 draft 补充了则应触发 critical 警告）

## 预期 review

必须发现的问题（如果 draft 未违规则无问题，但以下为常见违规场景）：

- issue type: fact_not_grounded / level: high / detail: 如果 draft 出现"领导高度肯定"等用户未提供的事实
- issue type: fact_not_grounded / level: high / detail: 如果 draft 出现具体成果名称
- issue type: style_overdone / level: medium / detail: 如果出现过度宣传腔

## 预期 rewrite

应修复：

- 删除所有用户未提供的事实（领导评价、具体成果名称等）
- 修正过度宣传腔

应保留：

- 5月20日、马栏山、文化科技融合创新活动
- 湖南广电集团、芒果超媒
- 三项创新成果

最终稿仍需人工确认：

- 活动主办单位全称
- 三项创新成果的正式名称

## 验收标准

1. classify 输出 doc_type=新闻稿，style_level=3
2. extract 不补充任何用户未提供的事实
3. draft 正文包含用户提供的所有要素
4. draft 不包含"领导出席""领导评价"等编造事实
5. review 能检出事实溯源问题（如有违规）
6. rewrite 删除所有编造事实
7. fact_usage_report 中每个事实可追溯到 extract_result
8. rewrite_policy.no_new_facts = true
9. rewrite_policy.no_rag_call = true
