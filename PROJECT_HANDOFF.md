# PROJECT_HANDOFF.md — mango-doc-writer 项目接手入口

> 最后更新：2026-06-05 | Commit: 3c16b63e | 分支: checkpoint/v0.2.0-j2-l1-closure-20260605

---

## 一、项目目标

mango-doc-writer 是一个公文/企业文稿写作辅助系统，基于 RAG 检索 + LLM 生成，为湖南广电/电广传媒/久之润等主体生成符合风格规范的文稿。

当前阶段：**v0.2.0 灰度开发**（candidate 语料库 + metadata rerank + 多文种规则）

---

## 二、当前架构

```
用户输入 → input_parser → classify → retrieve → draft → rewrite → 输出
```

- **正式规则库**：`references/` 目录（doc-type-rules.md, org-title-dictionary.yaml, style-rag-policy.md）
- **Prompt**：`prompts/` 目录（01-classify → 06-rewrite）
- **RAG**：Qdrant (localhost:6333) + 自建 RAG server (localhost:8000)
- **Pipeline**：`pipeline/` 目录（rag_client.py, input_parser.py, run_pipeline.py）

---

## 三、当前 Collection 状态

| Collection | 用途 | 默认启用 |
|------------|------|---------|
| mango_style_docs | 芒果风格文档（148 points） | ✅ |
| mango_style_docs_v020_candidate_rebuild_459 | 统一候选库（459 points） | 灰度 |
| jiuyou_docs | 久游网文档（3135 points） | ✅ |
| jiuzhirun_docs_v020_candidate | 久之润专项（86 points） | ❌ 默认关闭 |

路由边界：
- `RAG_JIUZHIRUN_ENABLED=false`（production 默认关闭）
- `style_domain=dianguang_siqing/mango_official_account` 时强制阻止 jiuzhirun_docs

---

## 四、已完成阶段

| 阶段 | 内容 | 状态 |
|------|------|------|
| C2 | 规则学习机制（78 候选，23 正式规则） | ✅ |
| C3 | 文种规则（10→16 种） | ✅ |
| G2/G3 | 灰度测试（44 篇，采用率 86%） | ✅ |
| J2 | 久之润专项库（32 篇，86 向量）+ 路由 | ✅ |
| L1 | 核心领导称谓（6 人确认，7 人暂缓） | ✅ |
| G4.0 | Git checkpoint | ✅ |

---

## 五、当前关键决策

1. **不写 .env**：candidate 库通过 env 灰度，不默认切换 production
2. **历史语料 ≠ 当前事实**：所有历史材料 `is_fact_safe=false`
3. **正式规则必须人工确认**：候选 → 去重 → 人工确认 → dry-run → 正式应用
4. **经营月报 Lite**：experimental/prototype/gray_only，不默认调用
5. **理论学习发言**：已收口，暂不继续 Prompt 调优，后续接入 Skill
6. **暂缓领导**：谷良、罗迎春、秦好、宋点、路颖、朱皓峰

---

## 六、当前遗留问题

- **篇幅偏短**：27% 灰度稿偏短，需优化
- **复杂讲话稿**：需要 Skill 工作流支持
- **久之润司情**：真实司情稿尚待补充
- **领导称谓**：不是实时人事信息源，需定期更新

---

## 七、下一阶段建议

| 优先级 | 方向 | 说明 |
|--------|------|------|
| P0 | 理论学习发言 Skill 接入 | 审计现有 Skill 可行性 |
| P1 | 补充久之润真实司情语料 | 用户有真实稿时入库 |
| P2 | 篇幅偏短专项优化 | 调整 Prompt 或分段生成 |
| 暂缓 | 经营月报复杂模板 | 等用户真实需求 |
| 暂缓 | 默认 RAG 切换 | 不动 .env |

---

## 八、操作红线

- ❌ 不自动修改 .env
- ❌ 不自动更新正式规则
- ❌ 不自动写入或删除 Qdrant
- ❌ 不提交内部原始语料、密钥和敏感资料
- ✅ 所有正式变更必须有阶段号和阶段报告

---

## 九、关键文件索引

| 文件 | 用途 |
|------|------|
| tests/reports/v0.2.0-stage-g3.1-gray-full-review-report.md | 灰度总复盘 |
| tests/reports/v0.2.0-stage-j2.9-jiuzhirun-docs-routing-and-capability-closure-report.md | J2 综合收口 |
| tests/reports/v0.2.0-stage-l1-leadership-title-special-closure-report.md | L1 收口 |
| tests/reports/v0.2.0-stage-g4.0-j2-l1-git-checkpoint-report.md | Git checkpoint |
| PROJECT-HANDOFF-LATEST.md | 最新握手状态 |

---

## 十、Git 状态

```bash
# 当前分支
git branch --show-current

# 最新 commit
git log -1 --oneline

# 检查变更
git status --short

# GitHub checkpoint
# checkpoint/v0.2.0-j2-l1-closure-20260605
# commit: 3c16b63e9dcdaae897cae391531116f0115dc0f5
```

---

*本文件是项目唯一主入口。接手者请先读此文件，再检查 git status 和最新报告。*
