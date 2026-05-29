"""
mango-doc-writer pipeline 类型定义
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# 六阶段顺序
STAGES = ["classify", "extract", "plan", "draft", "review", "rewrite"]

# 阶段 → Schema 文件映射
SCHEMA_MAP = {
    "classify": "classify.schema.json",
    "extract": "extract.schema.json",
    "plan": "plan.schema.json",
    "draft": "draft.schema.json",
    "review": "review.schema.json",
    "rewrite": "rewrite.schema.json",
    # quality_score 不是第七阶段，是后置门禁函数
    "quality_score": "quality_score.schema.json",
}


@dataclass
class PipelineInput:
    """Pipeline 输入"""
    requirement: str
    draft: str
    specified_doc_type: Optional[str] = None
    target_unit: Optional[str] = None
    scene: Optional[str] = None
    output_preference: Optional[str] = None

    def to_dict(self) -> dict:
        d = {"requirement": self.requirement, "draft": self.draft}
        if self.specified_doc_type:
            d["specified_doc_type"] = self.specified_doc_type
        if self.target_unit:
            d["target_unit"] = self.target_unit
        if self.scene:
            d["scene"] = self.scene
        if self.output_preference:
            d["output_preference"] = self.output_preference
        return d


@dataclass
class StageResult:
    """单阶段执行结果"""
    stage: str
    status: str  # "success" | "failed"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    validation_passed: Optional[bool] = None
    sanitizer_fixes: Optional[List[Dict]] = None
    sanitizer_high_risk: bool = False
    model_meta: Optional[Dict[str, Any]] = None


@dataclass
class SchemaValidationStatus:
    """Schema 校验状态"""
    classify: bool = False
    extract: bool = False
    plan: bool = False
    draft: bool = False
    review: bool = False
    rewrite: bool = False


@dataclass
class PipelineReport:
    """Pipeline 执行报告"""
    status: str = "pending"
    doc_type: Optional[str] = None
    risk_level: Optional[str] = None
    review_pass: Optional[bool] = None
    rewrite_required: Optional[bool] = None
    manual_confirmation_count: int = 0
    remaining_risk_count: int = 0
    schema_validation_status: Dict[str, bool] = field(default_factory=dict)
    rag_status: Optional[str] = None  # "success" | "empty" | "failed" | "not_called"
    style_references_count: int = 0
    rag_collection: Optional[str] = None  # 向后兼容：主 collection
    rag_index: Optional[str] = None  # 向后兼容
    rag_query: Optional[str] = None
    rag_sources: Optional[List[str]] = None
    rag_collections_used: Optional[List[str]] = None  # 19.3: 实际使用的 collections
    rag_primary_collection: Optional[str] = None  # 19.3: 主 collection
    rag_fallback_collection: Optional[str] = None  # 19.3: 备用 collection
    sanitizer_high_risk: bool = False
    stage_model_usage: Dict[str, Any] = field(default_factory=dict)
    fallback_count: int = 0
    default_model: Optional[str] = None
    fallback_model: Optional[str] = None
    fallback_enabled: Optional[bool] = None
    failed_stage: Optional[str] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    schema_path: Optional[str] = None
    output_files: List[str] = field(default_factory=list)

    # ─── 质量门禁字段（v0.1.3 后置质量门禁） ────────────────────
    quality_gate_enabled: bool = True
    quality_gate_pass: Optional[bool] = None
    quality_gate_threshold: float = 8.0
    quality_gate_rounds_used: int = 0
    quality_gate_max_rounds: int = 2
    final_quality_scores: Optional[Dict[str, Any]] = None
    failed_dimensions: List[str] = field(default_factory=list)
    quality_score_history: List[Dict[str, Any]] = field(default_factory=list)
    final_output_policy: Optional[str] = None
    human_review_required: bool = False
    quality_gate_error: Optional[str] = None
    quality_rewrite_applied: bool = False


@dataclass
class PipelineResult:
    """Pipeline 完整结果"""
    status: str  # "success" | "failed" | "skipped"
    final_markdown: Optional[str] = None
    pipeline_report: Optional[PipelineReport] = None
    partial_results: Dict[str, Any] = field(default_factory=dict)
    failed_stage: Optional[str] = None
    error: Optional[str] = None
    sanitizer_fixes: List[Dict] = field(default_factory=list)
