"""review.py 的自动化测试。"""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import review


REVIEW_SCRIPT = Path(__file__).with_name("review.py")


def run_review(text, markdown_path=None, json_path=None, use_ai=False, environment=None):
    """实际运行 review.py，并返回它的输出和退出状态。"""
    child_environment = os.environ.copy()
    child_environment["PYTHONIOENCODING"] = "utf-8"
    if environment:
        child_environment.update(environment)
    command = [sys.executable, str(REVIEW_SCRIPT), text]
    if use_ai:
        command.append("--ai")
    if markdown_path:
        command.extend(["--output", str(markdown_path)])
    if json_path:
        command.extend(["--json", str(json_path)])

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=child_environment,
    )


def successful_ai_payload():
    """提供一份用于 mock 的稳定 AI 返回结果。"""
    return {
        "clarity": {"score": 90, "issues": ["个别表达可更具体。"]},
        "grammar": {"score": 95, "issues": []},
        "logic": {"score": 80, "issues": ["因果关系可补充说明。"]},
        "structure": {"score": 85, "issues": []},
        "redundancy": {"score": 70, "issues": ["存在重复表达。"]},
        "suggestions": ["补充因果关系说明。"],
        "summary": "整体表达基本清楚，但可进一步精简。",
    }


class TestReview(unittest.TestCase):
    def test_empty_text(self):
        result = run_review("")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("审核失败：请输入需要审核的文本。", result.stdout)

    def test_short_text(self):
        result = run_review("你好")

        self.assertEqual(result.returncode, 0)
        self.assertIn("输入检查：通过", result.stdout)
        self.assertIn("长度检查：文本过短", result.stdout)

    def test_normal_text(self):
        result = run_review("今天天气很好。我准备出去散步。")

        self.assertEqual(result.returncode, 0)
        self.assertIn("长度检查：正常", result.stdout)
        self.assertIn("冗余检查：未发现明显重复", result.stdout)

    def test_duplicate_sentence(self):
        result = run_review("今天下雨了。今天下雨了。我带了雨伞。")

        self.assertEqual(result.returncode, 0)
        self.assertIn("冗余检查：发现重复句子", result.stdout)
        self.assertIn("重复内容：今天下雨了", result.stdout)

    def test_markdown_report_is_created(self):
        text = "今天下雨了。今天下雨了。我带了雨伞。"
        with tempfile.TemporaryDirectory() as temporary_directory:
            report_path = Path(temporary_directory) / "report.md"
            result = run_review(text, markdown_path=report_path)

            self.assertEqual(result.returncode, 0)
            self.assertTrue(report_path.is_file())
            report = report_path.read_text(encoding="utf-8")
            self.assertIn("# Text Review Report", report)
            self.assertIn("## 综合结果", report)
            self.assertIn("## 规则审核", report)
            self.assertIn("AI 语义审核：未执行", report)
            self.assertIn("## 修改建议", report)

    def test_json_report_is_created(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            json_path = Path(temporary_directory) / "result.json"
            result = run_review("今天天气很好。", json_path=json_path)

            self.assertEqual(result.returncode, 0)
            self.assertTrue(json_path.is_file())

    def test_json_report_has_correct_structure(self):
        text = "今天下雨了。今天下雨了。我带了雨伞。"
        with tempfile.TemporaryDirectory() as temporary_directory:
            json_path = Path(temporary_directory) / "result.json"
            result = run_review(text, json_path=json_path)

            self.assertEqual(result.returncode, 0)
            data = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(data["version"], "2.0")
            self.assertEqual(data["status"], "warning")
            self.assertEqual(data["overall_score"], 75)
            self.assertEqual(data["rule_review"]["text_length"], len(text))
            self.assertEqual(data["rule_review"]["duplicate_sentences"], ["今天下雨了"])
            self.assertEqual(data["ai_review"]["status"], "skipped")
            self.assertIn("冗余问题：重复内容：今天下雨了", data["issues"])

    def test_without_ai_does_not_call_ai_review(self):
        with mock.patch("review.run_ai_review") as ai_function:
            result = review.run_workflow("今天天气很好。我准备出去散步。", use_ai=False)

        ai_function.assert_not_called()
        self.assertEqual(result["ai_review"]["status"], "skipped")

    def test_ai_without_api_key_does_not_crash(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            json_path = Path(temporary_directory) / "result.json"
            result = run_review(
                "今天天气很好。我准备出去散步。",
                json_path=json_path,
                use_ai=True,
                environment={"DEEPSEEK_API_KEY": ""},
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn("AI 审核未执行：未配置 DEEPSEEK_API_KEY", result.stdout)
            data = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(data["ai_review"]["status"], "skipped")

    def test_ai_review_uses_mocked_responses_api(self):
        response = mock.Mock(output_text=json.dumps(successful_ai_payload(), ensure_ascii=False))
        client = mock.Mock()
        client.responses.create.return_value = response
        client_factory = mock.Mock(return_value=client)

        ai_review = review.run_ai_review(
            "需要审核的文本。",
            api_key="test-key",
            model="test-model",
            client_factory=client_factory,
        )

        self.assertEqual(ai_review["status"], "success")
        self.assertEqual(ai_review["model"], "test-model")
        self.assertEqual(ai_review["clarity"]["score"], 90)
        self.assertEqual(review.DEFAULT_MODEL, "deepseek-v4-flash")
        client_factory.assert_called_once_with(
            api_key="test-key", base_url="https://api.deepseek.com"
        )
        client.responses.create.assert_called_once()
        self.assertEqual(client.responses.create.call_args.kwargs["model"], "test-model")

    def test_ai_result_merge_logic(self):
        rule_review = review.review_text("今天天气很好。我准备出去散步。")
        ai_review = review.normalize_ai_review(successful_ai_payload(), "test-model")

        result = review.merge_reviews("今天天气很好。我准备出去散步。", rule_review, ai_review)

        self.assertEqual(result["overall_score"], 92)
        self.assertEqual(result["status"], "pass")
        self.assertIn("表达清晰度：个别表达可更具体。", result["issues"])
        self.assertIn("补充因果关系说明。", result["suggestions"])

    def test_overall_score_calculation(self):
        rule_review = review.review_text("今天下雨了。今天下雨了。我带了雨伞。")
        ai_payload = successful_ai_payload()
        for category in review.AI_CATEGORIES:
            ai_payload[category]["score"] = 60
        ai_review = review.normalize_ai_review(ai_payload, "test-model")

        self.assertEqual(rule_review["score"], 75)
        self.assertEqual(review.calculate_overall_score(rule_review, ai_review), 68)
        self.assertEqual(review.status_from_score(68), "warning")

    def test_v2_markdown_contains_ai_sections(self):
        rule_review = review.review_text("今天天气很好。我准备出去散步。")
        ai_review = review.normalize_ai_review(successful_ai_payload(), "test-model")
        markdown = review.build_markdown_report(
            review.merge_reviews("今天天气很好。我准备出去散步。", rule_review, ai_review)
        )

        self.assertIn("## AI 语义审核", markdown)
        self.assertIn("### 表达清晰度", markdown)
        self.assertIn("### 语病", markdown)
        self.assertIn("### 逻辑", markdown)
        self.assertIn("### 结构", markdown)
        self.assertIn("### 冗余", markdown)
        self.assertIn("## 总结", markdown)


if __name__ == "__main__":
    unittest.main()
