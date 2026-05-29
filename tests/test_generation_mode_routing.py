#!/usr/bin/env python3
"""
test_generation_mode_routing.py — v0.1.4 阶段 1 测试

测试 generation_mode 输入解析、默认值、非法值处理、Pipeline 传递。
"""

import json
import os
import sys
import unittest

# 将 pipeline 目录加入 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))

from pipeline_types import (
    PipelineInput,
    PipelineReport,
    VALID_GENERATION_MODES,
    GENERATION_MODE_FLAGS,
)
from input_parser import parse_input, _validate_generation_mode


class TestGenerationModeValidation(unittest.TestCase):
    """测试 generation_mode 校验逻辑"""

    def test_valid_safe_official(self):
        mode, valid, warnings = _validate_generation_mode("safe_official")
        self.assertEqual(mode, "safe_official")
        self.assertTrue(valid)
        self.assertEqual(warnings, [])

    def test_valid_assisted_expansion(self):
        mode, valid, warnings = _validate_generation_mode("assisted_expansion")
        self.assertEqual(mode, "assisted_expansion")
        self.assertTrue(valid)
        self.assertEqual(warnings, [])

    def test_valid_creative_mimic(self):
        mode, valid, warnings = _validate_generation_mode("creative_mimic")
        self.assertEqual(mode, "creative_mimic")
        self.assertTrue(valid)
        self.assertEqual(warnings, [])

    def test_none_defaults_to_safe_official(self):
        mode, valid, warnings = _validate_generation_mode(None)
        self.assertEqual(mode, "safe_official")
        self.assertTrue(valid)
        self.assertEqual(warnings, [])

    def test_invalid_string_falls_back(self):
        mode, valid, warnings = _validate_generation_mode("invalid_mode")
        self.assertEqual(mode, "safe_official")
        self.assertFalse(valid)
        self.assertTrue(len(warnings) > 0)
        self.assertIn("invalid_mode", warnings[0])

    def test_invalid_type_falls_back(self):
        mode, valid, warnings = _validate_generation_mode(123)
        self.assertEqual(mode, "safe_official")
        self.assertFalse(valid)
        self.assertTrue(len(warnings) > 0)

    def test_empty_string_falls_back(self):
        mode, valid, warnings = _validate_generation_mode("")
        self.assertEqual(mode, "safe_official")
        self.assertFalse(valid)
        self.assertTrue(len(warnings) > 0)


class TestPipelineInputGenerationMode(unittest.TestCase):
    """测试 PipelineInput generation_mode 字段"""

    def test_default_generation_mode(self):
        """A. 未提供 generation_mode → 默认 safe_official"""
        pi = PipelineInput(requirement="test", draft="test")
        self.assertEqual(pi.generation_mode, "safe_official")

    def test_explicit_safe_official(self):
        """B. 提供 safe_official → 行为与默认一致"""
        pi = PipelineInput(requirement="test", draft="test", generation_mode="safe_official")
        self.assertEqual(pi.generation_mode, "safe_official")
        d = pi.to_dict()
        self.assertEqual(d["generation_mode"], "safe_official")

    def test_explicit_assisted_expansion(self):
        """C. 提供 assisted_expansion → 正确解析"""
        pi = PipelineInput(requirement="test", draft="test", generation_mode="assisted_expansion")
        self.assertEqual(pi.generation_mode, "assisted_expansion")
        d = pi.to_dict()
        self.assertEqual(d["generation_mode"], "assisted_expansion")

    def test_explicit_creative_mimic(self):
        """D. 提供 creative_mimic → 正确解析"""
        pi = PipelineInput(requirement="test", draft="test", generation_mode="creative_mimic")
        self.assertEqual(pi.generation_mode, "creative_mimic")
        d = pi.to_dict()
        self.assertEqual(d["generation_mode"], "creative_mimic")

    def test_to_dict_always_includes_generation_mode(self):
        """to_dict 始终包含 generation_mode"""
        pi = PipelineInput(requirement="test", draft="test")
        d = pi.to_dict()
        self.assertIn("generation_mode", d)
        self.assertEqual(d["generation_mode"], "safe_official")


class TestGenerationModeFlags(unittest.TestCase):
    """测试 generation mode → flags 映射"""

    def test_safe_official_flags(self):
        flags = GENERATION_MODE_FLAGS["safe_official"]
        self.assertFalse(flags["expansion_enabled"])
        self.assertTrue(flags["official_use_allowed"])

    def test_assisted_expansion_flags(self):
        flags = GENERATION_MODE_FLAGS["assisted_expansion"]
        self.assertTrue(flags["expansion_enabled"])
        self.assertEqual(flags["official_use_allowed"], "requires_human_confirmation")

    def test_creative_mimic_flags(self):
        flags = GENERATION_MODE_FLAGS["creative_mimic"]
        self.assertTrue(flags["expansion_enabled"])
        self.assertFalse(flags["official_use_allowed"])


class TestPipelineReportGenerationMode(unittest.TestCase):
    """测试 PipelineReport generation mode 字段"""

    def test_default_values(self):
        """默认值正确"""
        report = PipelineReport()
        self.assertEqual(report.generation_mode, "safe_official")
        self.assertTrue(report.generation_mode_valid)
        self.assertEqual(report.generation_mode_warnings, [])
        self.assertTrue(report.official_use_allowed)
        self.assertFalse(report.expansion_enabled)

    def test_can_set_all_fields(self):
        """所有字段可正确赋值"""
        report = PipelineReport()
        report.generation_mode = "assisted_expansion"
        report.generation_mode_valid = True
        report.generation_mode_warnings = ["test warning"]
        report.official_use_allowed = "requires_human_confirmation"
        report.expansion_enabled = True
        self.assertEqual(report.generation_mode, "assisted_expansion")
        self.assertTrue(report.expansion_enabled)
        self.assertEqual(report.official_use_allowed, "requires_human_confirmation")


class TestParseInputStructured(unittest.TestCase):
    """测试 parse_input 结构化输入"""

    def test_default_generation_mode(self):
        """A. 未提供 generation_mode → 默认 safe_official"""
        result = parse_input({"requirement": "test", "draft": "test content"})
        self.assertEqual(result["generation_mode"], "safe_official")
        self.assertTrue(result["generation_mode_valid"])
        self.assertEqual(result["generation_mode_warnings"], [])

    def test_explicit_safe_official(self):
        """B. 提供 safe_official"""
        result = parse_input({"requirement": "test", "draft": "test", "generation_mode": "safe_official"})
        self.assertEqual(result["generation_mode"], "safe_official")
        self.assertTrue(result["generation_mode_valid"])

    def test_explicit_assisted_expansion(self):
        """C. 提供 assisted_expansion"""
        result = parse_input({"requirement": "test", "draft": "test", "generation_mode": "assisted_expansion"})
        self.assertEqual(result["generation_mode"], "assisted_expansion")
        self.assertTrue(result["generation_mode_valid"])

    def test_explicit_creative_mimic(self):
        """D. 提供 creative_mimic"""
        result = parse_input({"requirement": "test", "draft": "test", "generation_mode": "creative_mimic"})
        self.assertEqual(result["generation_mode"], "creative_mimic")
        self.assertTrue(result["generation_mode_valid"])

    def test_invalid_generation_mode(self):
        """E. 非法 generation_mode → 回退 safe_official + 记录警告"""
        result = parse_input({"requirement": "test", "draft": "test", "generation_mode": "bad_mode"})
        self.assertEqual(result["generation_mode"], "safe_official")
        self.assertFalse(result["generation_mode_valid"])
        self.assertTrue(len(result["generation_mode_warnings"]) > 0)


class TestParseInputNaturalLanguage(unittest.TestCase):
    """测试 parse_input 自然语言输入"""

    def test_natural_language_defaults(self):
        """自然语言输入默认 safe_official"""
        result = parse_input("5月20日，文化科技融合创新活动在马栏山举行。")
        self.assertEqual(result["generation_mode"], "safe_official")
        self.assertTrue(result["generation_mode_valid"])
        self.assertEqual(result["generation_mode_warnings"], [])


class TestParseInputJsonString(unittest.TestCase):
    """测试 parse_input JSON 字符串输入"""

    def test_json_string_with_generation_mode(self):
        """JSON 字符串包含 generation_mode"""
        data = {"requirement": "test", "draft": "test", "generation_mode": "creative_mimic"}
        result = parse_input(json.dumps(data))
        self.assertEqual(result["generation_mode"], "creative_mimic")

    def test_json_string_without_generation_mode(self):
        """JSON 字符串不包含 generation_mode → 默认 safe_official"""
        data = {"requirement": "test", "draft": "test"}
        result = parse_input(json.dumps(data))
        self.assertEqual(result["generation_mode"], "safe_official")


class TestValidGenerationModesConstant(unittest.TestCase):
    """测试常量定义"""

    def test_three_modes(self):
        self.assertEqual(len(VALID_GENERATION_MODES), 3)
        self.assertIn("safe_official", VALID_GENERATION_MODES)
        self.assertIn("assisted_expansion", VALID_GENERATION_MODES)
        self.assertIn("creative_mimic", VALID_GENERATION_MODES)

    def test_all_modes_have_flags(self):
        for mode in VALID_GENERATION_MODES:
            self.assertIn(mode, GENERATION_MODE_FLAGS)
            flags = GENERATION_MODE_FLAGS[mode]
            self.assertIn("expansion_enabled", flags)
            self.assertIn("official_use_allowed", flags)


if __name__ == "__main__":
    unittest.main()
