import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from evalforge import ai
from evalforge.analyzer import TAXONOMY, classify_badcase
from evalforge.capability import extract_capabilities
from evalforge.cli import main as cli_main
from evalforge.evaluator import evaluate_cases
from evalforge.generator import generate_cases
from evalforge.parser import SkillNotFoundError, parse_skill
from evalforge.reporter import build_report, markdown_report, write_reports
from evalforge.rubric import score_response, status_from_score


SKILL_TEXT = """---
name: Test Resume Review
description: Review resumes safely.
---
# Test Resume Review
## 目标
审核简历。
## 输入
简历文本。
## 输出
- 总体评价
- 修改建议
## 约束
- 必须分点。
## 明确禁止项
- 不允许虚构经历。
## 示例
输入：简历。输出：建议。
"""


class EvalForgeTest(unittest.TestCase):
    def make_skill(self, directory):
        skill_dir = Path(directory) / "skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(SKILL_TEXT, encoding="utf-8")
        return skill_dir

    def test_parse_skill(self):
        with tempfile.TemporaryDirectory() as directory:
            skill = parse_skill(self.make_skill(directory))
        self.assertEqual(skill.name, "Test Resume Review")
        self.assertIn("简历文本", skill.inputs)
        self.assertIn("不允许虚构", skill.prohibitions)

    def test_missing_skill(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(SkillNotFoundError):
                parse_skill(directory)

    def test_capability_extraction(self):
        with tempfile.TemporaryDirectory() as directory:
            skill = parse_skill(self.make_skill(directory))
            result = extract_capabilities(skill)
        self.assertEqual(len(result["capabilities"]), 7)
        self.assertIn("constraint_following", [item["id"] for item in result["capabilities"]])

    def test_case_generation_has_all_categories(self):
        with tempfile.TemporaryDirectory() as directory:
            skill = parse_skill(self.make_skill(directory))
            cases = generate_cases(skill, extract_capabilities(skill))["cases"]
        self.assertEqual(len(cases), 6)
        self.assertEqual({item["category"] for item in cases}, {"normal", "boundary", "constraint", "conflicting_instruction", "missing_information", "format_requirement"})

    def test_case_json_structure(self):
        with tempfile.TemporaryDirectory() as directory:
            skill_dir = self.make_skill(directory)
            path = Path(directory) / "cases.json"
            self.assertEqual(cli_main(["generate", str(skill_dir), "--output", str(path)]), 0)
            case = json.loads(path.read_text(encoding="utf-8"))["cases"][0]
        self.assertEqual(set(case), {"id", "category", "input", "expected_behavior", "capabilities", "severity"})

    def test_rubric_full_score(self):
        case = {"id": "case_001", "category": "normal", "severity": "low"}
        result = score_response(case, "- 完整且足够长的回答，包含需要的解释和建议。")
        self.assertEqual(result["overall_score"], 100)
        self.assertEqual(result["status"], "pass")

    def test_rubric_status_ranges(self):
        self.assertEqual(status_from_score(80), "pass")
        self.assertEqual(status_from_score(60), "warning")
        self.assertEqual(status_from_score(59), "fail")

    def test_badcase_classification(self):
        case = {"id": "case_001", "category": "normal", "severity": "high"}
        rubric = score_response(case, "")
        badcase = classify_badcase(case, "", rubric)
        self.assertEqual(badcase["type"], "missing_information")
        self.assertIn(badcase["type"], TAXONOMY)

    def test_markdown_report(self):
        case = {"id": "case_001", "category": "normal", "severity": "low"}
        report = build_report(evaluate_cases([case], {"case_001": "完整的回答内容，包含足够说明。"}))
        text = markdown_report(report)
        self.assertIn("# EvalForge Evaluation Report", text)
        self.assertIn("## Capability Scores", text)

    def test_json_report(self):
        with tempfile.TemporaryDirectory() as directory:
            evaluation = evaluate_cases([], {})
            markdown_path = Path(directory) / "report.md"
            json_path = Path(directory) / "report.json"
            write_reports(evaluation, markdown_path, json_path)
            data = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertIn("summary", data)
        self.assertIn("badcase_distribution", data)

    def test_cli_analyze(self):
        with tempfile.TemporaryDirectory() as directory:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = cli_main(["analyze", str(self.make_skill(directory))])
        self.assertEqual(exit_code, 0)
        self.assertIn("capability_result", output.getvalue())

    def test_cli_generate(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "eval_cases.json"
            exit_code = cli_main(["generate", str(self.make_skill(directory)), "--output", str(output_path)])
            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.is_file())

    def test_cli_report(self):
        with tempfile.TemporaryDirectory() as directory:
            results_path = Path(directory) / "results.json"
            results_path.write_text(json.dumps(evaluate_cases([], {})), encoding="utf-8")
            markdown_path = Path(directory) / "eval_report.md"
            json_path = Path(directory) / "eval_report.json"
            exit_code = cli_main(["report", str(results_path), "--markdown-output", str(markdown_path), "--json-output", str(json_path)])
            self.assertEqual(exit_code, 0)
            self.assertTrue(markdown_path.is_file())
            self.assertTrue(json_path.is_file())

    def test_without_deepseek_key_runs_baseline(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}):
            skill = parse_skill(self.make_skill(directory))
            result = generate_cases(skill, extract_capabilities(skill, use_ai=True), use_ai=True)
            evaluation = evaluate_cases(result["cases"][:1], use_ai=True)
        self.assertEqual(result["ai"]["status"], "skipped")
        self.assertEqual(evaluation["results"][0]["judge"]["status"], "skipped")

    def test_deepseek_call_is_mocked(self):
        response = mock.Mock(output_text='{"extra": "case"}')
        client = mock.Mock()
        client.responses.create.return_value = response
        factory = mock.Mock(return_value=client)
        with mock.patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}):
            result = ai.ai_json("return json", client_factory=factory)
        self.assertEqual(result["status"], "success")
        factory.assert_called_once_with(api_key="test-key", base_url="https://api.deepseek.com")
        client.responses.create.assert_called_once()
