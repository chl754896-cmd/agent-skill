"""Text Review Workflow：输入检查、长度检查和重复句子检查。"""

import re
import sys


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


def main():
    # 命令行第一个参数是用户要审核的文本；未提供时使用空字符串。
    text = sys.argv[1] if len(sys.argv) > 1 else ""

    # strip() 会去除首尾空格和换行，用于判断文本是否真的有内容。
    if not text.strip():
        print("审核失败：请输入需要审核的文本。")
        sys.exit(1)

    print("输入检查：通过")

    # 根据用户输入的字符数量，给出最简单的长度检查结果。
    if len(text) < 10:
        print("长度检查：文本过短")
    elif len(text) <= 100:
        print("长度检查：正常")
    else:
        print("长度检查：文本较长，可能需要检查是否存在冗余")

    duplicate_sentences = find_duplicate_sentences(text)
    if duplicate_sentences:
        print("冗余检查：发现重复句子")
        print(f"重复内容：{'；'.join(duplicate_sentences)}")
    else:
        print("冗余检查：未发现明显重复")

    print(f"待审核文本：{text}")


if __name__ == "__main__":
    main()
