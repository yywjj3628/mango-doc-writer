# 测试编号：006-leader-speech

## 测试目标

验证领导讲话稿不编造领导个人表态：

1. classify 识别为领导讲话；
2. extract 不补充领导个人信息；
3. draft 不编造"我强调""我要求"等第一人称个人表态（除非用户要求）；
4. **不编造领导姓名、职务**；
5. **不补充政策判断**；
6. review 能检出编造的领导表态；
7. rewrite 删除编造内容。

## 用户需求

请根据以下素材整理一份领导在工作推进会上的讲话稿。

## 用户初稿

会议围绕年度重点任务推进进行部署，要求各部门强化责任意识，加快重点项目落地。

## 预期 classify

- doc_type: 领导讲话
- direction: 内部材料
- style_level: 2
- risk_level: high
- 是否应 conflict_detected: false
- 判断理由: 用户明确"领导讲话稿"，内容为工作部署，但缺少讲话领导信息

## 预期 extract

必须抽取：

- time: []
- location: []
- organizations: ["各部门"]
- leaders: []（用户未提供讲话领导信息）
- products: []
- projects: ["年度重点任务", "重点项目"]
- events: ["工作推进会"]
- data: []
- achievements: []
- problems: []
- requests: []

必须进入 missing_fields：

- 讲话领导姓名
- 讲话领导职务
- 会议时间
- 会议地点
- 具体部门名称
- 重点任务具体内容

必须进入 cannot_infer：

- 讲话领导姓名
- 讲话领导职务
- 具体重点任务内容

必须进入 risk_flags：

- 缺少讲话领导信息: critical
- 缺少会议基本信息: high

## 预期 plan

应采用结构：

- 开头（会议背景、意义）
- 第一部分：形势分析（基于用户素材有限，需克制）
- 第二部分：工作部署（强化责任意识、加快重点项目落地）
- 第三部分：要求/号召
- 结尾

必须 blocked_items：

- 不得编造讲话领导姓名
- 不得编造讲话领导职务
- 不得编造"我强调""我要求"等个人表态（用户未要求第一人称）
- 不得编造政策判断
- 不得编造具体部门名称

必须 manual_confirmation_fields：

- 讲话领导姓名
- 讲话领导职务
- 会议时间
- 会议地点

## 预期 draft

允许出现：

- 领导讲话稿格式
- 【讲话领导待确认】
- 工作推进会背景
- 强化责任意识、加快重点项目落地
- 部署性表达
- 芒果系正式公文风（style_level=2）

不得出现：

- 编造的领导姓名（如"张三同志"）
- 编造的领导职务（如"公司党委书记"）
- "我强调""我要求""我指出"等第一人称个人表态
- 具体政策判断（如"当前正处于关键期"——无依据）
- 编造的具体部门名称
- 新闻稿风格的标题

必须 warnings：

- 讲话领导信息缺失（critical）
- 会议基本信息缺失（high）
- 具体任务内容模糊（medium）

## 预期 review

必须发现的问题：

- issue type: fact_not_grounded / level: critical / detail: 如果 draft 出现编造的领导姓名或职务
- issue type: fact_not_grounded / level: high / detail: 如果 draft 出现"我强调""我要求"等编造的个人表态
- issue type: terminology_error / level: high / detail: 如果 draft 出现编造的领导职务

## 预期 rewrite

应修复：

- 删除编造的领导姓名和职务
- 删除编造的个人表态
- 替换为占位符或中性表达

应保留：

- 工作部署内容
- 强化责任意识、加快重点项目落地
- 讲话稿格式

最终稿仍需人工确认：

- 讲话领导姓名
- 讲话领导职务
- 会议时间
- 会议地点

## 验收标准

1. classify 输出 doc_type=领导讲话
2. extract leaders 为空（用户未提供）
3. draft 不包含编造的领导姓名、职务
4. draft 不包含"我强调""我要求"等编造表态
5. review 能检出编造的领导信息（如有）
6. rewrite 删除编造的领导信息
7. rewrite_policy.no_new_facts = true
