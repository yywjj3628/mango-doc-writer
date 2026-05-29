# 测试编号：004-notice

## 测试目标

验证通知不能写成新闻稿：

1. classify 识别为通知（下行文）；
2. extract 抽取事项、时间、对象；
3. draft 生成通知格式（对象+事项+时间要求）；
4. **不得写成宣传稿**；
5. **不得出现新闻导语**；
6. **不得出现"活动取得成效"等评价性内容**。

## 用户需求

请写一份内部通知，要求各部门报送专项整治自查材料。

## 用户初稿

请各部门于本周五前提交专项整治自查情况，包括工作开展、问题排查、整改措施等内容。

## 预期 classify

- doc_type: 通知
- direction: 下行文
- style_level: 1
- risk_level: low
- 是否应 conflict_detected: false
- 判断理由: 用户明确"内部通知"，内容为布置工作、设定截止时间，符合通知特征

## 预期 extract

必须抽取：

- time: ["本周五前"]
- location: []
- organizations: ["各部门"]
- leaders: []
- products: []
- projects: ["专项整治"]
- events: []
- data: []
- achievements: []
- problems: []
- requests: ["提交专项整治自查情况"]

必须进入 missing_fields：

- 具体截止日期（"本周五"是相对时间）
- 通知下发单位
- 专项整治的具体名称/编号
- 材料提交方式（邮箱/系统/纸质）

必须进入 cannot_infer：

- 具体截止日期
- 专项整治全称
- 材料提交方式

必须进入 risk_flags：

- 时间表述模糊（"本周五"）: medium

## 预期 plan

应采用结构：

- 标题：关于报送专项整治自查材料的通知
- 主送对象：各部门
- 正文第一部分：背景/依据（如有）
- 正文第二部分：报送要求（内容、时间、方式）
- 正文第三部分：联系人/备注（如有）
- 结尾：标准通知结尾

必须 blocked_items：

- 不得写成新闻稿
- 不得添加宣传性评价
- 不得编造具体截止日期
- 不得编造专项整治全称
- 不得编造材料提交方式

必须 manual_confirmation_fields：

- 具体截止日期
- 专项整治全称
- 材料提交方式
- 通知下发单位

## 预期 draft

允许出现：

- 通知标题格式
- 各部门为主送对象
- 本周五前为时间要求
- 工作开展、问题排查、整改措施为报送内容
- 正式通知格式和语气

不得出现：

- 新闻导语（"为深入贯彻……近日……"等新闻开头）
- "活动取得成效""取得显著效果"等评价
- 新闻稿体裁的倒金字塔结构
- 编造的具体截止日期
- 编造的专项整治全称

必须 warnings：

- 截止日期模糊
- 专项整治全称缺失
- 材料提交方式缺失

## 预期 review

必须发现的问题：

- issue type: doc_type_error / level: critical / detail: 如果 draft 写成了新闻稿格式
- issue type: fact_not_grounded / level: medium / detail: 如果 draft 编造了具体截止日期或专项整治全称
- issue type: format_error / level: medium / detail: 如果 draft 缺少标准通知格式要素

## 预期 rewrite

应修复：

- 如果写成新闻稿，改为通知格式
- 删除编造的日期和名称
- 修正格式问题

应保留：

- 通知结构和语气
- "本周五前"（用占位符或保留原表述）
- 报送内容要求

最终稿仍需人工确认：

- 具体截止日期
- 专项整治全称
- 材料提交方式

## 验收标准

1. classify 输出 doc_type=通知，direction=下行文
2. draft 为通知格式，不是新闻稿
3. draft 不含新闻导语和宣传性评价
4. review 能检出体裁错误（如有）
5. rewrite 修正体裁问题
6. rewrite 不新增用户未提供的截止日期
7. final_checks.doc_type_fixed = true
