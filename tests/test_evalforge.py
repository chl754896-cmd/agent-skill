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
            docx_path = Path(directory) / "report.docx"
            write_reports(evaluation, markdown_path, json_path, docx_path)
            data = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertTrue(docx_path.is_file())
        self.assertIn("summary", data)
        self.assertIn("badcase_distribution", data)

    def test_docx_report_has_delivery_sections(self):
        with tempfile.TemporaryDirectory() as directory:
            evaluation = evaluate_cases([], {})
            docx_path = Path(directory) / "eval_report.docx"
            write_reports(evaluation, Path(directory) / "eval_report.md", Path(directory) / "eval_report.json", docx_path)
            from docx import Document
            text = "\n".join(paragraph.text for paragraph in Document(docx_path).paragraphs)
        self.assertIn("EvalForge Evaluation Report", text)
        self.assertIn("Evaluation Conclusion", text)

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
            docx_path = Path(directory) / "eval_report.docx"
            exit_code = cli_main(["report", str(results_path), "--markdown-output", str(markdown_path), "--json-output", str(json_path), "--docx-output", str(docx_path)])
            self.assertEqual(exit_code, 0)
            self.assertTrue(markdown_path.is_file())
            self.assertTrue(json_path.is_file())
            self.assertTrue(docx_path.is_file())

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

    def test_cli_evaluate(self):
        with tempfile.TemporaryDirectory() as directory:
            cases_path = Path(directory) / "cases.json"
            responses_path = Path(directory) / "responses.json"
            results_path = Path(directory) / "results.json"
            cases_path.write_text(json.dumps({"cases": [{"id": "case_001", "category": "normal", "severity": "low"}]}), encoding="utf-8")
            responses_path.write_text(json.dumps({"case_001": "这是一个足够完整的模型响应，用于通过基础评测。"}), encoding="utf-8")
            exit_code = cli_main(["evaluate", str(cases_path), "--responses", str(responses_path), "--output", str(results_path)])
            data = json.loads(results_path.read_text(encoding="utf-8"))
        self.assertEqual(exit_code, 0)
        self.assertEqual(data["results"][0]["final_rubric"]["status"], "pass")

    def test_ai_capability_merge(self):
        ai_data = {"status": "success", "model": "mock", "data": {"capabilities": [
            {"id": "accuracy", "name": "Accuracy", "description": "duplicate", "evidence": "x", "priority": "high"},
            {"id": "safety", "name": "Safety", "description": "avoid harm", "evidence": "constraint", "priority": "high"},
        ]}}
        with tempfile.TemporaryDirectory() as directory, mock.patch("evalforge.capability.ai_json", return_value=ai_data):
            skill = parse_skill(self.make_skill(directory))
            result = extract_capabilities(skill, use_ai=True)
        ids = [item["id"] for item in result["capabilities"]]
        self.assertEqual(result["ai"]["status"], "success")
        self.assertEqual(ids.count("accuracy"), 1)
        self.assertIn("safety", ids)

    def test_invalid_ai_capability_falls_back(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch("evalforge.capability.ai_json", return_value={"status": "success", "model": "mock", "data": {"capabilities": [{"id": "bad"}]}}):
            result = extract_capabilities(parse_skill(self.make_skill(directory)), use_ai=True)
        self.assertEqual(len(result["capabilities"]), 7)
        self.assertEqual(result["ai"]["status"], "error")

    def test_ai_case_merge(self):
        ai_data = {"status": "success", "model": "mock", "data": {"cases": [
            {"id": "case_001", "category": "normal", "input": "duplicate", "expected_behavior": "x", "capabilities": [], "severity": "low"},
            {"id": "case_ai_001", "category": "adversarial", "input": "edge", "expected_behavior": "refuse conflict", "capabilities": ["constraint_following"], "severity": "high"},
        ]}}
        with tempfile.TemporaryDirectory() as directory, mock.patch("evalforge.generator.ai_json", return_value=ai_data):
            skill = parse_skill(self.make_skill(directory))
            result = generate_cases(skill, extract_capabilities(skill), use_ai=True)
        self.assertEqual(len(result["cases"]), 7)
        self.assertEqual(len({case["id"] for case in result["cases"]}), 7)
        self.assertEqual(result["ai"]["status"], "success")

    def test_invalid_ai_case_falls_back(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch("evalforge.generator.ai_json", return_value={"status": "success", "model": "mock", "data": {"cases": [{"id": "bad"}]}}):
            skill = parse_skill(self.make_skill(directory))
            result = generate_cases(skill, extract_capabilities(skill), use_ai=True)
        self.assertEqual(len(result["cases"]), 6)
        self.assertEqual(result["ai"]["status"], "error")

    def test_ai_judge_final_rubric(self):
        judge = {"status": "success", "model": "mock", "data": {
            "dimension_scores": {"instruction_following": 85, "constraint_following": 85, "completeness": 85, "output_format": 85, "accuracy": 85, "robustness": 85},
            "overall_score": 85, "status": "pass", "reasoning_summary": "Judge 认为符合要求。", "badcase_type": "other", "recommendation": "保持质量。",
        }}
        case = {"id": "case_001", "category": "normal", "severity": "low"}
        with mock.patch("evalforge.evaluator.ai_json", return_value=judge):
            result = evaluate_cases([case], {"case_001": ""}, use_ai=True)["results"][0]
        self.assertEqual(result["rule_rubric"]["status"], "fail")
        self.assertEqual(result["final_rubric"]["overall_score"], 85)
        self.assertEqual(result["ai_judge"]["status"], "success")

    def test_ai_badcase_type_is_used(self):
        judge = {"status": "success", "model": "mock", "data": {
            "dimension_scores": {"instruction_following": 70, "constraint_following": 70, "completeness": 70, "output_format": 70, "accuracy": 70, "robustness": 70},
            "overall_score": 70, "status": "warning", "reasoning_summary": "逻辑链条不足。", "badcase_type": "logic_error", "recommendation": "补充推理过程。",
        }}
        case = {"id": "case_001", "category": "normal", "severity": "medium"}
        with mock.patch("evalforge.evaluator.ai_json", return_value=judge):
            result = evaluate_cases([case], {"case_001": "简短回答"}, use_ai=True)["results"][0]
        self.assertEqual(result["badcase"]["type"], "logic_error")
        self.assertEqual(result["badcase"]["recommendation"], "补充推理过程。")

    def test_sample_responses_complete_chain(self):
        root = Path(__file__).resolve().parents[1]
        skill = parse_skill(root / "examples" / "resume-review")
        cases = generate_cases(skill, extract_capabilities(skill))["cases"]
        responses = json.loads((root / "examples" / "resume-review" / "responses.json").read_text(encoding="utf-8"))
        report = build_report(evaluate_cases(cases, responses))
        self.assertEqual(report["summary"]["total_cases"], 6)
        self.assertEqual(report["summary"]["fail"], 0)
        self.assertEqual(report["summary"]["status"] if "status" in report["summary"] else "pass", "pass")

    def test_reporter_prefers_final_rubric(self):
        evaluation = {"results": [{
            "rule_rubric": {"dimension_scores": {"accuracy": 0}, "overall_score": 0, "status": "fail"},
            "rubric": {"dimension_scores": {"accuracy": 0}, "overall_score": 0, "status": "fail"},
            "final_rubric": {"dimension_scores": {"accuracy": 100}, "overall_score": 100, "status": "pass"},
            "badcase": None,
        }]}
        report = build_report(evaluation)
        self.assertEqual(report["summary"]["overall_score"], 100)
        self.assertEqual(report["summary"]["pass"], 1)
