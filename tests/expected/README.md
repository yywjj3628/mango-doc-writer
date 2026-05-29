# tests/expected/ README

## 目录用途

存放各测试样例的预期输出 JSON 文件。

## 阶段 11 说明

本目录在阶段 11 **不要求**一开始就写完整的六阶段 JSON 黄金输出。

阶段 11 先在 `tests/cases/*.md` 中建立**预期行为清单**。每个 case 的 Markdown 中已写清楚每个阶段的预期输入输出。

## 后续可逐步补充

1. `expected/classify/*.json` — classify 阶段预期输出
2. `expected/extract/*.json` — extract 阶段预期输出
3. `expected/plan/*.json` — plan 阶段预期输出
4. `expected/draft/*.json` — draft 阶段预期输出
5. `expected/review/*.json` — review 阶段预期输出
6. `expected/rewrite/*.json` — rewrite 阶段预期输出

## 预期输出格式

每个 expected JSON 只标注关键字段和约束，不需要完整覆盖所有字段。

关键标注方式：

- `must_contain` — 必须出现的字段/内容
- `not_contains` — 不得出现的内容
- `must_be_true` — 必须为 true 的布尔字段（如 rewrite_policy 七项）
- `min_count` — 数组最小长度（如 manual_confirmation_fields 至少 N 项）

## 当前状态

第一版预期行为清单已在 `tests/cases/*.md` 中完成。JSON 预期输出文件将在阶段 12（最小调用入口）完成后，基于实际运行结果逐步填充。
