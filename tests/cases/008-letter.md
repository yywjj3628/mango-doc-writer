# 测试编号：008-letter

## 测试目标

验证函用于平级或不相隶属单位，不得写成请示：

1. classify 识别为函（平行文）；
2. extract 抽取往来单位和商洽事项；
3. draft 按函格式生成；
4. **不得出现"妥否，请批示"**；
5. **不得写成上行请示**；
6. 称谓不确定时标记待确认。

## 用户需求

请写一份给合作单位的函，商请对方协助提供活动场地支持。

## 用户初稿

拟商请对方单位协助提供活动场地，并就现场保障、设备支持等事项进行沟通。

## 预期 classify

- doc_type: 函
- direction: 平行文
- style_level: 1
- risk_level: medium
- 是否应 conflict_detected: false
- 判断理由: 用户明确"函"，用于商洽事项，往来单位为平行/不相隶属关系，符合函特征

## 预期 extract

必须抽取：

- time: []
- location: []
- organizations: ["合作单位", "对方单位"]
- leaders: []
- products: []
- projects: ["活动场地"]
- events: []
- data: []
- achievements: []
- problems: []
- requests: ["协助提供活动场地", "现场保障、设备支持等事项进行沟通"]

必须进入 missing_fields：

- 发函单位全称
- 收函单位全称
- 活动名称
- 活动时间
- 活动规模
- 联系人信息

必须进入 cannot_infer：

- 发函单位全称
- 收函单位全称
- 活动具体信息

必须进入 risk_flags：

- "合作单位""对方单位"称谓不规范，需确认正式名称: medium

## 预期 plan

应采用结构：

- 标题：关于商请协助提供活动场地的函
- 主送单位
- 正文第一部分：事由（拟举办活动，需场地支持）
- 正文第二部分：具体商洽事项（场地、现场保障、设备支持）
- 正文第三部分：沟通安排/联系方式
- 结尾：函的规范结尾（"请予协助为盼"等，不得是"妥否，请批示"）

必须 blocked_items：

- 不得使用"妥否，请批示"结尾
- 不得写成上行请示
- 不得编造发函单位全称
- 不得编造收函单位全称
- 不得编造活动具体信息
- 不得编造联系人信息

必须 manual_confirmation_fields：

- 发函单位全称
- 收函单位全称
- 活动名称
- 活动时间

## 预期 draft

允许出现：

- 函的标准格式
- 关于商请协助提供活动场地的函
- 协助提供活动场地
- 现场保障、设备支持
- 【发函单位待确认】
- 【收函单位待确认】
- "请予协助为盼"等函结尾

不得出现：

- 妥否，请批示
- 请批准、请批复
- 编造的发函/收函单位全称
- 编造的活动名称或时间
- 编造的联系人信息
- 请示/报告结尾

必须 warnings：

- 收函单位全称缺失
- 发函单位全称缺失
- 活动信息不完整

## 预期 review

必须发现的问题：

- issue type: doc_type_error / level: critical / detail: 如果 draft 出现"妥否，请批示"等请示结尾
- issue type: terminology_error / level: medium / detail: 如果使用了不规范的单位称谓且未标记确认
- issue type: format_error / level: medium / detail: 如果函格式不标准

## 预期 rewrite

应修复：

- 删除请示结尾（如有），改为函结尾
- 修正不规范的称谓
- 修正格式问题

应保留：

- 函的结构和语气
- 商洽事项
- 【待确认】占位符

最终稿仍需人工确认：

- 发函单位全称
- 收函单位全称
- 活动名称
- 活动时间

## 验收标准

1. classify 输出 doc_type=函，direction=平行文
2. draft 不含"妥否，请批示"
3. draft 不含请示/报告结尾
4. terminology_usage_report 标记不规范称谓为待确认
5. review 能检出体裁错误（如有）
6. rewrite 修正体裁问题
7. rewrite_policy 七项均为 true
