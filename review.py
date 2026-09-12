"""Text Review Workflow：输入检查、长度检查、重复句子检查和报告生成。"""

import argparse
from pathlib import Path
import re


def find_duplicate_sentences(text):
    """找出文本中完全相同的重复句子。"""
    # 按中英文常见句末标点拆分文本。
    sentences = re.split(r"[。！？；.!?;]", text)
    seen_sentences = set()
    duplicate_sentences = []

    for sentence in sentences:
        # 去掉句子前后的空格，并跳过标点之间产生的空内容。
        sentence = sentence.strip()
        if not sentence:
            continue

        # 已出现过的句子就是重复句子；每个重复内容只记录一次。
        if sentence in seen_sentences:
            if sentence not in duplicate_sentences:
                duplicate_sentences.append(sentence)
        else:
            seen_sentences.add(sentence)

    return duplicate_sentences


def build_report(text, length_result, redundancy_result, issues):
    """把审核结果整理成可保存的文本报告。"""
    return "\n".join(
        [
            "Text Review Report",
            "",
            "审核文本：",
            text,
            "",
            "输入检查：",
            "通过",
            "",
            "长度检查：",
            length_result,
            "",
            "冗余检查：",
            redundancy_result,
            "",
            "发现的问题：",
            *issues,
        ]
    ) + "\n"


def main():
    parser = argparse.ArgumentParser(description="审核一段文本。")
    parser.add_argument("text", nargs="?", default="", help="需要审核的文本")
    parser.add_argument("--output", help="保存审核报告的文件路径")
    args = parser.parse_args()
    text = args.text

    # strip() 会去除首尾空格和换行，用于判断文本是否真的有内容。
    if not text.strip():
        print("审核失败：请输入需要审核的文本。")
        return 1

    print("输入检查：通过")

    # 根据用户输入的字符数量，给出最简单的长度检查结果。
    if len(text) < 10:
        length_result = "文本过短"
    elif len(text) <= 100:
        length_result = "正常"
    else:
        length_result = "文本较长，可能需要检查是否存在冗余"
    print(f"长度检查：{length_result}")

    duplicate_sentences = find_duplicate_sentences(text)
    if duplicate_sentences:
        redundancy_result = "发现重复句子"
        duplicate_content = "；".join(duplicate_sentences)
        issues = [f"- 冗余问题：重复内容：{duplicate_content}"]
    else:
        redundancy_result = "未发现明显重复"
        duplicate_content = None
        issues = ["- 未发现明显问题"]
    print(f"冗余检查：{redundancy_result}")
    if duplicate_content:
        print(f"重复内容：{duplicate_content}")

    print(f"待审核文本：{text}")

    if args.output:
        report = build_report(text, length_result, redundancy_result, issues)
        Path(args.output).write_text(report, encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
