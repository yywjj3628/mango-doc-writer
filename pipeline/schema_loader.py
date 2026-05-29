"""
mango-doc-writer schema 加载与校验

所有阶段输出必须使用 jsonschema.validate 校验。
不得只使用 json.load。
"""

import json
import os
from typing import Dict

import jsonschema
from jsonschema import ValidationError

from pipeline_types import SCHEMA_MAP, STAGES

# Schema 目录相对于本文件的路径
_SCHEMAS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "schemas")

# 缓存已加载的 schema
_schema_cache: Dict[str, dict] = {}


def load_schema(stage: str) -> dict:
    """
    加载指定阶段的 JSON Schema。

    Args:
        stage: 阶段名称 (classify/extract/plan/draft/review/rewrite)

    Returns:
        schema dict

    Raises:
        ValueError: 未知的阶段名称
        FileNotFoundError: schema 文件不存在
        json.JSONDecodeError: schema 文件不是合法 JSON
    """
    if stage not in SCHEMA_MAP:
        raise ValueError(
            f"未知阶段 '{stage}'。支持的阶段: {list(SCHEMA_MAP.keys())}"
        )

    if stage in _schema_cache:
        return _schema_cache[stage]

    schema_path = os.path.join(_SCHEMAS_DIR, SCHEMA_MAP[stage])

    if not os.path.exists(schema_path):
        raise FileNotFoundError(
            f"Schema 文件不存在: {schema_path}"
        )

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    _schema_cache[stage] = schema
    return schema


def validate_result(stage: str, result: dict) -> None:
    """
    使用 jsonschema.validate 校验阶段输出。

    Args:
        stage: 阶段名称
        result: 阶段输出 dict

    Raises:
        ValueError: 未知的阶段名称
        ValidationError: schema 校验失败（包含 stage 和 schema_path 信息）
    """
    schema = load_schema(stage)
    schema_path = os.path.join(_SCHEMAS_DIR, SCHEMA_MAP[stage])

    try:
        jsonschema.validate(instance=result, schema=schema)
    except ValidationError as e:
        # 附加上下文信息到错误消息
        e.message = (
            f"[{stage}] Schema 校验失败 (schema: {schema_path}): {e.message}"
        )
        raise


def clear_cache() -> None:
    """清空 schema 缓存（测试用）"""
    _schema_cache.clear()
