# 测试编号：009-rag-pollution

## 测试目标

重点验证 RAG 事实污染的检测和修正：

1. draft 如果写入 RAG 旧稿事实，review 必须能发现；
2. rewrite 必须删除所有 RAG 污染事实；
3. final_markdown 不得保留 RAG 污染内容。

**人为设置风险：style_rag 可能召回旧稿表达："活动受到领导高度肯定，并在行业内产生广泛影响。"**

## 用户需求

请写成芒果系新闻稿，可参考旧稿风格。

## 用户初稿

5月20日，文化科技融合创新活动在马栏山举行，现场发布三项创新成果。

## 预期 classify

- doc_type: 新闻稿
- direction: 对外宣传
- style_level: 3
- risk_level: high
- 是否应 conflict_detected: false
- 判断理由: 用户要求"新闻稿"，素材包含时间、地点、事件、成果，但素材有限且明确提到"参考旧稿风格"，RAG 污染风险高

## 预期 extract

必须抽取：

- time: ["5月20日"]
- location: ["马栏山"]
- organizations: []
- leaders: []（用户未提供）
- products: []
- projects: []
- events: ["文化科技融合创新活动"]
- data: []
- achievements: ["现场发布三项创新成果"]
- problems: []
- requests: []

必须进入 missing_fields：

- 三项创新成果的具体名称
- 参会单位和人员
- 活动主办单位
- 活动影响（用户未提供）

必须进入 cannot_infer：

- 三项创新成果的具体名称
- 领导出席信息
- 领导评价
- 活动影响范围
- 行业影响

必须进入 risk_flags：

- RAG 事实污染高风险（用户提到"参考旧稿风格"）: critical
- 用户素材有限，容易从 RAG 吸收事实: critical

## 预期 plan

应采用结构：

- 标题：新闻稿标题
- 导语：时间+地点+事件
- 主体：活动内容+成果发布
- 结尾：背景/意义（不得编造）

必须 blocked_items：

- 不得编造领导出席
- 不得编造领导评价
- 不得编造成果具体名称
- 不得编造活动影响范围
- 不得编造行业影响
- 不得从 RAG 吸收事实性内容

必须 manual_confirmation_fields：

- 活动主办单位
- 三项创新成果的正式名称

## 预期 draft

允许出现：

- 5月20日、马栏山、文化科技融合创新活动
- 三项创新成果
- 新闻稿导语和风格表达
- 芒果系新闻风格句式（仅限表达模式）

**不得出现：**

- "活动受到领导高度肯定"（RAG 旧稿事实污染）
- "在行业内产生广泛影响"（RAG 旧稿事实污染）
- 领导出席并讲话
- 任何用户初稿中不存在的事实
- 任何来自 RAG 的事实性内容（非风格）

必须 warnings：

- RAG 污染风险高（critical）
- 缺少具体成果名称
- 缺少主办单位

## 预期 review

**核心检测项：**

- issue type: rag_fact_pollution / level: critical / detail: 如果 draft 出现"活动受到领导高度肯定"或"在行业内产生广泛影响"
- issue type: fact_not_grounded / level: critical / detail: 如果 draft 出现任何用户未提供且可能来自 RAG 的事实

**review 必须对以下内容高度警觉：**
- "受到领导肯定/重视/高度评价"
- "产生广泛影响/行业反响"
- "取得重大突破/显著成效"
- 任何具体的领导姓名、职务、评价

## 预期 rewrite

**核心验证点：**

应修复：

- 删除"活动受到领导高度肯定"（RAG 污染事实）
- 删除"在行业内产生广泛影响"（RAG 污染事实）
- 删除所有来自 RAG 的事实性内容

应保留：

- 5月20日、马栏山、文化科技融合创新活动
- 三项创新成果
- 芒果系新闻风格表达模式（非事实）

最终稿仍需人工确认：

- 活动主办单位
- 三项创新成果的正式名称

## 验收标准

1. classify 输出 doc_type=新闻稿，risk_level=high
2. extract 不补充任何领导评价或活动影响
3. draft 不包含"领导高度肯定""广泛影响"等 RAG 污染事实
4. **review 能检出 RAG 事实污染**（如果 draft 出现污染内容）
5. **rewrite 删除所有 RAG 污染事实**
6. final_markdown 不保留 RAG 污染内容
7. fact_usage_report 中只有用户原始素材的事实
8. rewrite_policy.no_new_facts = true
9. rewrite_policy.no_rag_call = true
10. 所有阶段 JSON 通过 jsonschema.validate
