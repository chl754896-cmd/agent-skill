"""Text Review Workflow V2：规则审核、AI 语义审核与报告生成。"""

import argparse
import json
import os
from pathlib import Path
import re


DEFAULT_MODEL = "deepseek-v4-flash"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
AI_CATEGORIES = ("clarity", "grammar", "logic", "structure", "redundancy")
CATEGORY_LABELS = {
    "clarity": "表达清晰度",
    "grammar": "语病",
    "logic": "逻辑",
    "structure": "结构",
    "redundancy": "冗余",
}

AI_REVIEW_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [*AI_CATEGORIES, "suggestions", "summary"],
    "properties": {
        category: {
            "type": "object",
            "additionalProperties": False,
            "required": ["score", "issues"],
            "properties": {
                "score": {"type": "integer", "minimum": 0, "maximum": 100},
                "issues": {"type": "array", "items": {"type": "string"}},
            },
        }
        for category in AI_CATEGORIES
    }
    | {
        "suggestions": {"type": "array", "items": {"type": "string"}},
        "summary": {"type": "string"},
    },
}


def find_duplicate_sentences(text):
    """找出文本中完全相同的重复句子。"""
    sentences = re.split(r"[。！？；.!?;]", text)
    seen_sentences = set()
    duplicate_sentences = []

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if sentence in seen_sentences:
            if sentence not in duplicate_sentences:
                duplicate_sentences.append(sentence)
        else:
            seen_sentences.add(sentence)

    return duplicate_sentences


def review_text(text):
    """执行不依赖网络或 API 的基础规则审核。"""
    result = {
        "status": "pass",
        "score": 100,
        "text_length": len(text),
        "length_check": "",
        "duplicate_check": "",
        "duplicate_sentences": [],
        "issues": [],
        "suggestions": [],
    }

    if not text.strip():
        result.update(
            {
                "status": "fail",
                "score": 0,
                "length_check": "输入为空",
                "duplicate_check": "未执行",
                "issues": ["请输入需要审核的文本。"],
                "suggestions": ["请提供需要审核的文本。"],
            }
        )
        return result

    if result["text_length"] < 10:
        result["status"] = "warning"
        result["score"] -= 25
        result["length_check"] = "文本过短"
        result["issues"].append("文本长度少于 10 个字符。")
        result["suggestions"].append("建议补充更多文本内容。")
    elif result["text_length"] <= 100:
        result["length_check"] = "正常"
    else:
        result["status"] = "warning"
        result["score"] -= 25
        result["length_check"] = "文本较长，可能需要检查是否存在冗余"
        result["suggestions"].append("建议检查并精简过长的内容。")

    duplicate_sentences = find_duplicate_sentences(text)
    result["duplicate_sentences"] = duplicate_sentences
    if duplicate_sentences:
        result["status"] = "warning"
        result["score"] -= 25
        result["duplicate_check"] = "发现重复句子"
        duplicate_content = "；".join(duplicate_sentences)
        result["issues"].append(f"冗余问题：重复内容：{duplicate_content}")
        result["suggestions"].append("建议删除或合并重复句子。")
    else:
        result["duplicate_check"] = "未发现明显重复"

    result["score"] = max(result["score"], 0)
    return result


def empty_ai_review(status, model, summary):
    """创建未执行或失败时也保持完整字段的 AI 审核结果。"""
    review = {"status": status, "model": model, "suggestions": [], "summary": summary}
    for category in AI_CATEGORIES:
        review[category] = {"score": None, "issues": []}
    return review


def normalize_ai_review(payload, model):
    """验证并整理 AI 返回的 JSON，防止异常数据进入最终报告。"""
    review = empty_ai_review("success", model, "")
    for category in AI_CATEGORIES:
        category_data = payload[category]
        score = category_data["score"]
        if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 100:
            raise ValueError("AI 返回了无效评分")
        issues = category_data["issues"]
        if not isinstance(issues, list) or not all(isinstance(issue, str) for issue in issues):
            raise ValueError("AI 返回了无效问题列表")
        review[category] = {"score": score, "issues": issues}

    suggestions = payload["suggestions"]
    summary = payload["summary"]
    if not isinstance(suggestions, list) or not all(isinstance(item, str) for item in suggestions):
        raise ValueError("AI 返回了无效建议列表")
    if not isinstance(summary, str):
        raise ValueError("AI 返回了无效总结")
    review["suggestions"] = suggestions
    review["summary"] = summary
    return review


def run_ai_review(text, api_key=None, model=None, client_factory=None):
    """使用 Responses API 进行 AI 语义审核；所有失败都会安全降级。"""
    model = model or os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL)
    api_key = api_key if api_key is not None else os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return empty_ai_review("skipped", model, "AI 审核未执行：未配置 DEEPSEEK_API_KEY")

    try:
        if client_factory is None:
            # 延迟导入：不用 --ai 时不需要安装或加载 OpenAI SDK。
            from openai import OpenAI

            client_factory = OpenAI

        client = client_factory(api_key=api_key, base_url=DEEPSEEK_BASE_URL)
        response = client.responses.create(
            model=model,
            instructions=(
                "你是中文文本审核助手。请审核用户文本的表达清晰度、语病、逻辑、结构和冗余。"
                "对每项给出 0 到 100 的评分和具体问题；没有问题时 issues 使用空数组。"
                "建议必须可执行，总结保持简洁。"
            ),
            input=text,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "text_review_ai_result",
                    "strict": True,
                    "schema": AI_REVIEW_SCHEMA,
                }
            },
        )
        return normalize_ai_review(json.loads(response.output_text), model)
    except ImportError:
        return empty_ai_review("error", model, "AI 审核未执行：OpenAI SDK 不可用")
    except Exception:
        # 不输出异常对象，避免把可能包含敏感信息的内容写入日志。
        return empty_ai_review("error", model, "AI 审核未执行：调用失败")


def calculate_overall_score(rule_review, ai_review):
    """计算第一版综合评分：有成功 AI 审核时取规则和 AI 平均分的平均值。"""
    rule_score = rule_review["score"]
    if ai_review["status"] != "success":
        return rule_score

    ai_score = round(sum(ai_review[category]["score"] for category in AI_CATEGORIES) / len(AI_CATEGORIES))
    return round((rule_score + ai_score) / 2)


def status_from_score(score):
    """按 V2 分档把综合评分转换为最终状态。"""
    if score >= 80:
        return "pass"
    if score >= 60:
        return "warning"
    return "fail"


def merge_reviews(text, rule_review, ai_review):
    """合并规则审核和 AI 审核，供终端、Markdown 与 JSON 共用。"""
    overall_score = calculate_overall_score(rule_review, ai_review)
    issues = list(rule_review["issues"])
    suggestions = list(rule_review["suggestions"])

    if ai_review["status"] == "success":
        for category in AI_CATEGORIES:
            label = CATEGORY_LABELS[category]
            issues.extend(f"{label}：{issue}" for issue in ai_review[category]["issues"])
        suggestions.extend(ai_review["suggestions"])

    return {
        "version": "2.0",
        "status": status_from_score(overall_score),
        "overall_score": overall_score,
        "rule_review": rule_review,
        "ai_review": ai_review,
        "issues": issues,
        "suggestions": suggestions,
        "text": text,
    }


def status_label(status):
    """把程序状态转换为便于阅读的中文。"""
    return {"pass": "通过", "warning": "建议修改", "fail": "审核失败"}[status]


def markdown_list(items, empty_message):
    """把字符串列表转换为 Markdown 项目列表。"""
    return [f"- {item}" for item in items] or [f"- {empty_message}"]


def build_markdown_report(result):
    """生成 V2 Markdown 审核报告。"""
    rule_review = result["rule_review"]
    ai_review = result["ai_review"]
    lines = [
        "# Text Review Report",
        "",
        "## 综合结果",
        f"- 综合评分：{result['overall_score']}",
        f"- 状态：{status_label(result['status'])}",
        "",
        "## 原始文本",
        result["text"],
        "",
        "## 规则审核",
        f"- 规则评分：{rule_review['score']}",
        f"- 长度检查：{rule_review['length_check']}",
        f"- 冗余检查：{rule_review['duplicate_check']}",
        "",
        "## AI 语义审核",
    ]

    if ai_review["status"] == "success":
        lines.append(f"- 使用模型：{ai_review['model']}")
        for category in AI_CATEGORIES:
            category_review = ai_review[category]
            lines.extend(
                [
                    "",
                    f"### {CATEGORY_LABELS[category]}",
                    f"- 评分：{category_review['score']}",
                    *markdown_list(category_review["issues"], "未发现明显问题"),
                ]
            )
    else:
        lines.append(ai_review["summary"])

    lines.extend(
        [
            "",
            "## 发现的问题",
            *markdown_list(result["issues"], "未发现明显问题"),
            "",
            "## 修改建议",
            *markdown_list(result["suggestions"], "暂无修改建议"),
            "",
            "## 总结",
            ai_review["summary"] if ai_review["status"] == "success" else "已完成规则审核。",
        ]
    )
    return "\n".join(lines) + "\n"


def print_terminal_result(result, ai_requested):
    """输出简洁终端结果，不显示密钥或底层异常。"""
    rule_review = result["rule_review"]
    if result["rule_review"]["status"] == "fail":
        print("审核失败：请输入需要审核的文本。")
        return

    print("输入检查：通过")
    print(f"长度检查：{rule_review['length_check']}")
    print(f"冗余检查：{rule_review['duplicate_check']}")
    if rule_review["duplicate_sentences"]:
        print(f"重复内容：{'；'.join(rule_review['duplicate_sentences'])}")
    print(f"综合评分：{result['overall_score']}，状态：{result['status']}")
    if ai_requested:
        print(result["ai_review"]["summary"])
    print(f"待审核文本：{result['text']}")


def run_workflow(text, use_ai=False):
    """运行完整审核流程；不开启 AI 时不会导入或调用 OpenAI SDK。"""
    rule_review = review_text(text)
    if rule_review["status"] == "fail":
        ai_review = empty_ai_review("skipped", os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL), "AI 语义审核：未执行")
    elif use_ai:
        ai_review = run_ai_review(text)
    else:
        ai_review = empty_ai_review("skipped", os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL), "AI 语义审核：未执行")
    return merge_reviews(text, rule_review, ai_review)


def main():
    parser = argparse.ArgumentParser(description="审核一段文本。")
    parser.add_argument("text", nargs="?", default="", help="需要审核的文本")
    parser.add_argument("--ai", action="store_true", help="启用 DeepSeek AI 语义审核")
    parser.add_argument("--output", help="保存 Markdown 审核报告的文件路径")
    parser.add_argument("--json", dest="json_output", help="保存 JSON 审核结果的文件路径")
    args = parser.parse_args()

    result = run_workflow(args.text, use_ai=args.ai)
    print_terminal_result(result, args.ai)

    if result["rule_review"]["status"] == "fail":
        return 1

    if args.output:
        Path(args.output).write_text(build_markdown_report(result), encoding="utf-8")
    if args.json_output:
        Path(args.json_output).write_text(
            f"{json.dumps(result, ensure_ascii=False, indent=2)}\n", encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
