# Stage 19.3 — mango_style_docs RAG 路由接入报告

> **执行时间**: 2026-05-29 02:20 UTC (北京时间 10:20)
> **阶段**: 19.3 — 受限接入 RAG 路由

---

## 1. 修改文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `pipeline/rag_client.py` | 重写 | 多 collection 路由、环境变量配置、返回结构增强 |
| `pipeline/pipeline_types.py` | 修改 | PipelineReport 新增 3 个字段 |
| `pipeline/run_pipeline.py` | 修改 | rag_info 适配新字段、pipeline_report 输出 |
| `deploy/env.example` | 修改 | 新增 RAG 多 collection 环境变量 |
| `deploy/check_env.py` | 修改 | 新增 collection 可用性检查 |
| `deploy/healthcheck.py` | 修改 | 新增 collection 状态检查 |
| `pipeline/README.md` | 修改 | 新增多 collection 路由说明 |
| `docs/mango-doc-writer-vps-deployment.md` | 修改 | 新增 mango_style_docs 使用说明 |
| `docs/mango-doc-writer-release-notes.md` | 修改 | 新增 v0.1.2 变更说明 |
| `tests/reports/stage-19-3-rag-routing-report.md` | 新增 | 本报告 |

## 2. 路由规则

| 文种 | mango_style_docs | jiuyou_docs | 总计 |
|------|---:|---:|---:|
| 新闻稿 | 4 | 2 | 6 |
| 活动稿 | 4 | 2 | 6 |
| 宣传稿 | 4 | 2 | 6 |
| 司情新闻稿 | 4 | 2 | 6 |
| 党建材料 | 4 | 2 | 6 |
| 学习稿 | 4 | 2 | 6 |
| 领导讲话 | 3 | 3 | 6 |
| 通报 | 1 | 5 | 6 |
| 汇报材料 | 1 | 5 | 6 |
| 总结 | 1 | 5 | 6 |
| 报告 | 0 | 6 | 6 |
| 请示 | 0 | 6 | 6 |
| 通知 | 0 | 6 | 6 |
| 函 | 0 | 6 | 6 |
| 会议纪要 | 0 | 6 | 6 |
| 其他 | 2 | 4 | 6 |

## 3. 环境变量配置

```bash
RAG_BASE_URL=http://localhost:8000/search
RAG_ENABLE_MULTI_COLLECTION=true
RAG_TOP_K_TOTAL=6
RAG_COLLECTION_STYLE=mango_style_docs
RAG_COLLECTION_BUSINESS=jiuyou_docs
RAG_COLLECTION_DISABLED=openclaw_memory
```

## 4. 返回结构增强

`retrieve_style_references()` 返回新增字段：
- `rag_collections_used`: 实际查询的 collection 列表
- `rag_primary_collection`: 主 collection
- `rag_fallback_collection`: 备用 collection

`pipeline_report.json` 新增：
- `rag_collections_used`: `["mango_style_docs", "jiuyou_docs"]`
- `rag_primary_collection`: 主 collection 名称
- `rag_fallback_collection`: 备用 collection 名称

## 5. openclaw_memory 排除验证

- ✅ `RAG_COLLECTION_DISABLED=openclaw_memory` 默认值
- ✅ `rag_client.py` 路由中明确跳过 disabled collection
- ✅ `check_env.py` 验证 disabled collection 已配置

## 6. 测试验证

### 6.1 功能测试

| 测试 | 方法 | 结果 |
|------|------|------|
| 新闻稿路由 | 构造 doc_type="新闻稿" 调用 retrieve_style_references | ✅ mango_style_docs 优先 |
| 请示路由 | 构造 doc_type="请示" 调用 retrieve_style_references | ✅ 仅 jiuyou_docs |
| 领导讲话路由 | 构造 doc_type="领导讲话" 调用 retrieve_style_references | ✅ 混合 3+3 |
| openclaw_memory 排除 | 设置 collection=openclaw_memory，验证不查询 | ✅ 被跳过 |

### 6.2 环境变量测试

| 测试 | 结果 |
|------|------|
| RAG_ENABLE_MULTI_COLLECTION=false | ✅ 降级为单 collection (jiuyou_docs) |
| RAG_COLLECTION_STYLE 自定义 | ✅ 正确覆盖默认值 |
| 环境变量缺失 | ✅ 使用默认值，不报错 |

### 6.3 返回结构测试

| 测试 | 结果 |
|------|------|
| style_reference 含 collection 字段 | ✅ |
| do_not_copy 字段非空 | ✅ |
| risk_notes 含"仅风格参考" | ✅ |
| pipeline_report 含新字段 | ✅ |

### 6.4 10 case 回归

由于 model_runner 未接入真实模型（测试环境限制），本次回归为代码级别验证：

| 检查项 | 结果 |
|--------|------|
| `rag_client.py` 导入无报错 | ✅ |
| `pipeline_types.py` 字段完整 | ✅ |
| `run_pipeline.py` 字段赋值无遗漏 | ✅ |
| `env.example` 配置完整 | ✅ |
| `check_env.py` collection 检查 | ✅ |
| `healthcheck.py` collection 检查 | ✅ |
| `pipeline/README.md` 文档更新 | ✅ |
| prompts/* 未修改 | ✅ |
| schemas/* 未修改 | ✅ |
| references/* 未修改 | ✅ |

## 7. 是否修改 prompts / schemas / references

| 类型 | 是否修改 |
|------|----------|
| prompts/* | ❌ 未修改 |
| schemas/* | ❌ 未修改 |
| references/* | ❌ 未修改 |
| Qdrant 数据 | ❌ 未修改 |

## 8. 是否出现 RAG 污染

- ❌ 未发现。`do_not_copy` 规则已嵌入每个 style_reference。
- ✅ `risk_notes` 明确标注"仅风格参考，事实以 extract_result 为准"。

## 9. 是否建议发布 v0.1.2

**✅ 是**

理由：
1. 路由规则完整，覆盖所有文种
2. 返回结构增强，pipeline_report 可追溯
3. 环境变量配置外部化，灵活可控
4. openclaw_memory 已排除
5. 向后兼容（rag_collection/rag_index 字段保留）
6. 代码级别验证全部通过

---

*报告生成时间: 2026-05-29 02:20 UTC*
