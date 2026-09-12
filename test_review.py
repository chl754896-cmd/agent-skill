"""review.py 的自动化测试。"""

import os
from pathlib import Path
import subprocess
import sys
import unittest


REVIEW_SCRIPT = Path(__file__).with_name("review.py")


def run_review(text):
    """实际运行 review.py，并返回它的输出和退出状态。"""
    # 让子进程使用 UTF-8，确保测试可以正确读取中文输出。
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"

    return subprocess.run(
        [sys.executable, str(REVIEW_SCRIPT), text],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
    )


class TestReview(unittest.TestCase):
    def test_normal_text(self):
        result = run_review("今天天气很好。我准备出去散步。")

        self.assertEqual(result.returncode, 0)
        self.assertIn("输入检查：通过", result.stdout)
        self.assertIn("长度检查：正常", result.stdout)
        self.assertIn("冗余检查：未发现明显重复", result.stdout)

    def test_short_text(self):
        result = run_review("你好")

        self.assertEqual(result.returncode, 0)
        self.assertIn("输入检查：通过", result.stdout)
        self.assertIn("长度检查：文本过短", result.stdout)

    def test_duplicate_sentence(self):
        result = run_review("今天下雨了。今天下雨了。我带了雨伞。")

        self.assertEqual(result.returncode, 0)
        self.assertIn("冗余检查：发现重复句子", result.stdout)
        self.assertIn("重复内容：今天下雨了", result.stdout)

    def test_empty_text(self):
        result = run_review("")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("审核失败：请输入需要审核的文本。", result.stdout)


if __name__ == "__main__":
    unittest.main()
