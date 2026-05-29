# 测试编号：005-meeting-minutes

## 测试目标

验证会议纪要缺失基本信息时用占位符，不虚构：

1. classify 识别为会议纪要；
2. extract 正确识别缺失字段；
3. draft 使用【待确认】占位；
4. **不得虚构会议时间、地点、参会人员**；
5. review 能检出虚构信息；
6. rewrite 删除虚构信息并使用占位符。

## 用户需求

请整理成会议纪要。

## 用户初稿

会议研究了项目推进、责任分工和下阶段时间节点。会议要求业务部门牵头推进，技术部门配合完成系统联调。

## 预期 classify

- doc_type: 会议纪要
- direction: 内部材料
- style_level: 1
- risk_level: high
- 是否应 conflict_detected: false
- 判断理由: 用户明确"会议纪要"，内容为会议研究事项和要求，但缺少时间、地点、参会人员等关键信息

## 预期 extract

必须抽取：

- time: []
- location: []
- organizations: ["业务部门", "技术部门"]
- leaders: []
- products: []
- projects: ["项目推进", "系统联调"]
- events: []
- data: []
- achievements: []
- problems: []
- requests: []

必须进入 missing_fields：

- 会议时间（用户未提供）
- 会议地点（用户未提供）
- 参会人员（用户未提供）
- 会议名称/主题（用户未提供完整名称）

必须进入 cannot_infer：

- 会议时间
- 会议地点
- 参会人员
- 会议名称

必须进入 risk_flags：

- 缺少会议基本信息（时间、地点、参会人员）: critical
- 缺少会议名称: high

## 预期 plan

应采用结构：

- 会议基本信息（时间/地点/参会人员 → 占位符）
- 会议议题
- 会议研究事项（项目推进、责任分工、下阶段时间节点）
- 会议要求/决议（业务部门牵头、技术部门配合）
- 下一步工作安排

必须 blocked_items：

- 不得虚构会议时间
- 不得虚构会议地点
- 不得虚构参会人员
- 不得虚构会议名称
- 不得编造会议决议外的内容

必须 manual_confirmation_fields：

- 会议时间
- 会议地点
- 参会人员
- 会议名称/主题
- 会议主持人

## 预期 draft

允许出现：

- 会议纪要标准格式
- 【会议时间待确认】
- 【会议地点待确认】
- 【参会人员待确认】
- 项目推进、责任分工、下阶段时间节点
- 业务部门牵头推进、技术部门配合完成系统联调
- 会议研究事项和会议要求

不得出现：

- 具体会议时间（如"2026年5月20日"——用户未提供）
- 具体会议地点（如"公司会议室"——用户未提供）
- 具体参会人员名单
- 具体会议名称
- 编造的会议决议

必须 warnings：

- 会议时间缺失（critical）
- 会议地点缺失（critical）
- 参会人员缺失（critical）
- 会议名称缺失（high）

## 预期 review

必须发现的问题：

- issue type: fact_not_grounded / level: critical / detail: 如果 draft 出现虚构的会议时间、地点或参会人员
- issue type: format_error / level: medium / detail: 如果 draft 缺少占位符而直接写了编造的信息

## 预期 rewrite

应修复：

- 删除所有虚构的会议时间、地点、参会人员
- 替换为【待确认】占位符

应保留：

- 用户提供的会议研究事项
- 会议要求（业务部门牵头、技术部门配合）
- 会议纪要格式

最终稿仍需人工确认：

- 会议时间
- 会议地点
- 参会人员
- 会议名称/主题
- 会议主持人

## 验收标准

1. classify 输出 doc_type=会议纪要，direction=内部材料
2. extract missing_fields 包含会议时间、地点、参会人员
3. draft 对缺失信息使用【待确认】占位符
4. draft 不包含虚构的会议时间、地点、参会人员
5. review 能检出虚构信息（如有）
6. rewrite 删除虚构信息，保留占位符
7. remaining_risks 记录缺失字段
8. rewrite_policy.no_new_facts = true
