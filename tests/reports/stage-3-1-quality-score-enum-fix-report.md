# Stage 3.1 — Quality Score 枚举修复报告

**日期**: 2026-05-29
**版本**: mango-doc-writer v0.1.3
**范围**: 修复测试 fixtures 中与 quality_score.schema.json 不一致的枚举值

---

## 1. 修改文件清单

| 文件 | 修改类型 |
|------|----------|
| `tests/fixtures/quality_score_pass.json` | 枚举值修复 |
| `tests/fixtures/quality_score_warn.json` | 枚举值 + 结构修复 |
| `tests/fixtures/quality_score_rewrite.json` | 枚举值 + 结构修复 |
| `tests/fixtures/quality_score_fact_risk.json` | 枚举值 + 结构修复 |
| `prompts/07-quality-score.md` | **无需修改**（已正确） |

## 2. 发现的不一致字段

### 2.1 枚举值不一致

| 字段 | Schema 枚举 | 修复前（Fixture） | 修复后 |
|------|------------|-------------------|--------|
| `no_new_facts_check.status` | `pass / warning / fail` | `clean` (pass/fact_risk) | `pass` |
| `no_new_facts_check.status` | `pass / warning / fail` | `suspected` (warn/fact_risk) | `warning` |
| `doc_type_check.status` | `pass / warning / fail` | `matched` (全部4个) | `pass` |
| `style_check.status` | `pass / warning / fail` | `matched` (pass/fact_risk) | `pass` |
| `style_check.status` | `pass / warning / fail` | `mismatch` (warn/rewrite) | `fail` |

### 2.2 结构不一致（额外发现）

| 文件 | 字段 | 问题 | 修复 |
|------|------|------|------|
| `quality_score_fact_risk.json` | `quality_rewrite_instructions[0].suggested_action` | 值为描述文字 `"删除第3段未在素材中出现的数据"` | 改为 `"delete"`，补 `current_text`/`suggested_text` |
| `quality_score_rewrite.json` | `quality_rewrite_instructions[0].suggested_action` | 值为描述文字 `"第2段增加芒果系口语化表达"` | 改为 `"replace"`，补 `current_text`/`suggested_text` |
| `quality_score_warn.json` | `no_new_facts_check.suspected_new_facts[0]` | 字符串 `"测试新增事实"` | 改为对象 `{"text":..., "location":..., "reason":...}` |
| `quality_score_fact_risk.json` | `no_new_facts_check.suspected_new_facts[0]` | 同上 | 同上 |

## 3. 修复前后枚举值对照

### no_new_facts_check.status
| 场景 | 修复前 | 修复后 |
|------|--------|--------|
| pass (无新增事实) | `clean` | `pass` |
| warn/fact_risk (疑似新增) | `suspected` | `warning` |
| fail (确认新增) | — | `fail`（Schema 已定义，Prompt 示例已正确） |

### doc_type_check.status
| 场景 | 修复前 | 修复后 |
|------|--------|--------|
| 匹配 | `matched` | `pass` |
| 不匹配 | `mismatch` | `fail` |

### style_check.status
| 场景 | 修复前 | 修复后 |
|------|--------|--------|
| 匹配 | `matched` | `pass` |
| 不匹配 | `mismatch` | `fail` |

## 4. Prompt / Schema 枚举一致性检查

**结论：`prompts/07-quality-score.md` 中所有 JSON 示例的枚举值与 Schema 完全一致，无需修改。**

Prompt 中共 6 个 JSON 示例块：
- 示例 1（quality_rewrite_instructions 结构）：非 quality_score 结果，跳过
- 示例 2（首次评估全部通过）：✅ schema OK
- 示例 3（语言质量不达标）：✅ schema OK
- 示例 4（发现疑似新增事实）：✅ schema OK
- 示例 5（quality_gate_policy 固定输出）：非 quality_score 结果，跳过

不一致仅存在于 **测试 fixtures** 中，不在 Prompt 中。

**其他 Prompt（01-06）的 Schema 枚举检查**：不在本次修复范围，各 Schema 枚举体系独立。

## 5. 实际运行的验证命令

```bash
# 1. Schema 校验（4个 fixtures）
cd /home/ywj/.openclaw/workspace/skills/mango-doc-writer
python3 -c "
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path('pipeline')))
from schema_loader import validate_result
for f in sorted(Path('tests/fixtures').glob('quality_score_*.json')):
    data = json.loads(f.read_text())
    validate_result('quality_score', data)
    print(f'✅ {f.name}')
"

# 2. 阶段 3 测试套件
python3 -m pytest tests/regression/test_quality_gate.py -v

# 3. Prompt 示例校验
python3 -c "
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path('pipeline')))
from schema_loader import validate_result
prompt = Path('prompts/07-quality-score.md').read_text()
json_blocks = re.findall(r'\`\`\`json\s*\n(.*?)\n\`\`\`', prompt, re.DOTALL)
for i, block in enumerate(json_blocks):
    data = json.loads(block)
    if 'quality_summary' in data:
        validate_result('quality_score', data)
        print(f'✅ 示例 {i+1}')
"

# 4. 残留非 Schema 枚举值扫描
grep -rn '"clean"\|"suspected"\|"matched"\|"mismatch"' prompts/ tests/fixtures/ --include="*.json" --include="*.md"
```

## 6. 测试结果

| 测试项 | 结果 |
|--------|------|
| `quality_score_pass.json` schema 校验 | ✅ 通过 |
| `quality_score_warn.json` schema 校验 | ✅ 通过 |
| `quality_score_rewrite.json` schema 校验 | ✅ 通过 |
| `quality_score_fact_risk.json` schema 校验 | ✅ 通过 |
| Prompt 6 个 JSON 示例校验 | ✅ 4个 quality_score 示例全部通过 |
| 阶段 3 测试套件（22项） | ✅ 22 passed, 0 failed |
| 残留非 Schema 枚举值扫描 | ✅ 无残留 |
| Pipeline 代码改动 | ✅ 无改动 |

## 7. 是否建议进入阶段 4

**✅ 建议进入阶段 4。**

理由：
1. 所有测试 fixtures 的枚举值已与 Schema 完全对齐
2. Prompt 示例本身无需修改（已正确）
3. 22 项阶段 3 测试全部通过
4. 未改动任何 Pipeline 逻辑
5. 发现的额外问题（`suggested_action` 值为描述文字、`suspected_new_facts` 结构错误）已一并修复
6. 无残留非 Schema 枚举值

**注意**：本次修复暴露了 fixtures 编写时缺乏 schema 校验自动化的问题。建议阶段 4 在 CI 中加入 fixtures → schema 自动校验步骤。
