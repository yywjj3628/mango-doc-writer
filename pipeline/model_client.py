"""
model_client.py — DeepSeek API 模型调用客户端

使用 OpenAI-compatible API 调用 DeepSeek。
API key 通过环境变量读取，不得写死。

环境变量：
  DEEPSEEK_API_KEY          (必需)
  DEEPSEEK_BASE_URL         (默认 https://api.deepseek.com)
  DEEPSEEK_MODEL            (默认 deepseek-v4-flash，用于全量回归)
  DEEPSEEK_FALLBACK_MODEL   (默认 deepseek-v4-pro，仅在失败重试时使用)
  DEEPSEEK_ENABLE_FALLBACK  (默认 true)
  DEEPSEEK_TIMEOUT          (默认 120)
  DEEPSEEK_MAX_RETRIES      (默认 2)
"""

import json
import os
import re
import time
from typing import Any, Dict, Optional


def _get_client():
    """创建 OpenAI client（延迟初始化，避免 import 时就要求 key）"""
    from openai import OpenAI

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "未检测到 DEEPSEEK_API_KEY 环境变量。"
            "请在 .env 文件或系统环境变量中设置。"
        )

    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    return OpenAI(api_key=api_key, base_url=base_url)


def extract_json_text(text: str) -> str:
    """从模型输出中提取 JSON 文本"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text.strip())
        text = re.sub(r"\s*```$", "", text.strip())
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model output")
    return text[start:end + 1]


def _call_model(
    client,
    model: str,
    system_prompt: str,
    user_prompt: str,
    stage_name: str,
    temperature: float,
    max_tokens: int,
    timeout: int,
) -> str:
    """单次调用 DeepSeek API，返回原始文本"""
    start = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
        timeout=timeout,
    )
    elapsed = time.time() - start
    raw_text = response.choices[0].message.content
    print(f"  📥 DeepSeek [{model.split('-v')[0]}] ({stage_name}, {elapsed:.1f}s, {len(raw_text)} 字符)")
    return raw_text


def call_llm_json(
    system_prompt: str,
    user_prompt: str,
    stage_name: str,
    temperature: float = 0.2,
    max_tokens: int = 8192,
    use_fallback: bool = False,
) -> Dict[str, Any]:
    """
    调用 DeepSeek API 并返回解析后的 JSON + 模型元信息。

    Returns:
        {
            "result": {...},  # JSON 内容
            "_model_meta": {
                "provider": "deepseek",
                "model": "deepseek-v4-flash",
                "fallback_used": false,
                "fallback_model": null,
                "fallback_reason": null
            }
        }

    Raises:
        EnvironmentError: 缺少 API key
        ValueError: JSON 解析失败
        RuntimeError: API 调用失败
    """
    client = _get_client()
    default_model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    fallback_model = os.getenv("DEEPSEEK_FALLBACK_MODEL", "deepseek-v4-pro")
    enable_fallback = os.getenv("DEEPSEEK_ENABLE_FALLBACK", "true").lower() == "true"
    timeout = int(os.getenv("DEEPSEEK_TIMEOUT", "120"))
    max_retries = int(os.getenv("DEEPSEEK_MAX_RETRIES", "2"))

    # 确定 fallback 是否可用
    can_fallback = enable_fallback and fallback_model and fallback_model != default_model

    # 确保 system_prompt 要求 JSON 输出
    json_instruction = (
        "\n\n【重要】只输出严格 JSON，不得输出 Markdown 代码块，"
        "不得输出解释性文字，不得输出任何非 JSON 内容。"
    )
    if "只输出严格 JSON" not in system_prompt:
        system_prompt += json_instruction

    meta = {
        "provider": "deepseek",
        "model": default_model,
        "fallback_used": False,
        "fallback_model": None,
        "fallback_reason": None,
    }

    # ─── 阶段 1：用默认模型重试 ────────────────────────────────────
    raw_text = None
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            raw_text = _call_model(
                client, default_model, system_prompt, user_prompt,
                stage_name, temperature, max_tokens, timeout,
            )
            json_str = extract_json_text(raw_text)
            result = json.loads(json_str)
            return {"result": result, "_model_meta": meta}

        except (json.JSONDecodeError, ValueError) as e:
            last_error = e
            if attempt < max_retries:
                print(f"  ⚠️ JSON 解析失败，重试 ({attempt + 1}/{max_retries}): {e}")
                time.sleep(1)
                continue
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                print(f"  ⚠️ API 调用失败，重试 ({attempt + 1}/{max_retries}): {e}")
                time.sleep(2)
                continue

    # 默认模型重试耗尽 → 尝试 fallback（JSON/API 错误始终允许 fallback）
    if can_fallback:
        meta["fallback_used"] = True
        meta["fallback_model"] = fallback_model
        meta["fallback_reason"] = f"default_model_retries_exhausted: {type(last_error).__name__}: {last_error}"
        meta["model"] = fallback_model

        print(f"  🔄 Fallback → {fallback_model} ({stage_name})")

        try:
            raw_text = _call_model(
                client, fallback_model, system_prompt, user_prompt,
                stage_name, temperature, max_tokens, timeout,
            )
            json_str = extract_json_text(raw_text)
            result = json.loads(json_str)
            return {"result": result, "_model_meta": meta}

        except (json.JSONDecodeError, ValueError) as e:
            # fallback 也失败 → 保存 debug
            debug_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "tests", "reports", "debug",
            )
            os.makedirs(debug_dir, exist_ok=True)
            debug_path = os.path.join(debug_dir, f"{stage_name}-raw-output.txt")
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(f"Stage: {stage_name}\n")
                f.write(f"Default Model: {default_model}\n")
                f.write(f"Fallback Model: {fallback_model}\n")
                f.write(f"Error: {e}\n")
                f.write(f"---RAW OUTPUT (fallback)---\n")
                f.write(raw_text if raw_text else "(no output)")
            raise ValueError(
                f"模型输出无法解析为 JSON ({stage_name}, fallback={fallback_model})。"
                f"原始输出已保存到: {debug_path}"
            )

        except Exception as e:
            raise RuntimeError(
                f"DeepSeek API 调用失败 ({stage_name}, fallback={fallback_model}): {e}"
            )

    # 无 fallback 或 fallback 关闭 → 保存 debug 并报错
    debug_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "tests", "reports", "debug",
    )
    os.makedirs(debug_dir, exist_ok=True)
    debug_path = os.path.join(debug_dir, f"{stage_name}-raw-output.txt")
    with open(debug_path, "w", encoding="utf-8") as f:
        f.write(f"Stage: {stage_name}\n")
        f.write(f"Model: {default_model}\n")
        f.write(f"Error: {last_error}\n")
        f.write(f"---RAW OUTPUT---\n")
        f.write(raw_text if raw_text else "(no output)")

    raise ValueError(
        f"模型输出无法解析为 JSON ({stage_name})。"
        f"原始输出已保存到: {debug_path}"
    )


def trigger_fallback_call(
    system_prompt: str,
    user_prompt: str,
    stage_name: str,
    fallback_reason: str,
    temperature: float = 0.2,
    max_tokens: int = 8192,
) -> Dict[str, Any]:
    """
    在 run_pipeline 中因 schema 校验失败时主动触发 fallback。

    Returns:
        {"result": {...}, "_model_meta": {...}}
    """
    client = _get_client()
    fallback_model = os.getenv("DEEPSEEK_FALLBACK_MODEL", "deepseek-v4-pro")
    enable_fallback = os.getenv("DEEPSEEK_ENABLE_FALLBACK", "true").lower() == "true"
    timeout = int(os.getenv("DEEPSEEK_TIMEOUT", "120"))

    if not enable_fallback or not fallback_model:
        raise RuntimeError(f"Fallback 未启用或未配置 ({stage_name})")

    meta = {
        "provider": "deepseek",
        "model": fallback_model,
        "fallback_used": True,
        "fallback_model": fallback_model,
        "fallback_reason": fallback_reason,
    }

    print(f"  🔄 Fallback ({fallback_reason}) → {fallback_model} ({stage_name})")

    raw_text = _call_model(
        client, fallback_model, system_prompt, user_prompt,
        stage_name, temperature, max_tokens, timeout,
    )

    json_str = extract_json_text(raw_text)
    result = json.loads(json_str)
    return {"result": result, "_model_meta": meta}
