"""Badcase 分类。"""

TAXONOMY = ("instruction_following", "constraint_violation", "missing_information", "format_error", "accuracy_error", "hallucination", "logic_error", "incomplete_answer", "redundancy", "robustness_failure", "other")


def classify_badcase(case, response, rubric_result):
    """基于 Rubric 的最低维度给出一个首要 Badcase。"""
    if rubric_result["status"] == "pass":
        return None
    scores = rubric_result["dimension_scores"]
    weakest = min(scores, key=scores.get)
    mapping = {
        "constraint_following": "constraint_violation", "output_format": "format_error",
        "completeness": "incomplete_answer", "accuracy": "accuracy_error",
        "robustness": "robustness_failure", "instruction_following": "instruction_following",
    }
    badcase_type = "missing_information" if not (response or "").strip() else mapping.get(weakest, "other")
    return {
        "case_id": case["id"], "type": badcase_type, "severity": case["severity"],
        "reason": f"{weakest} 得分为 {scores[weakest]}。", "root_cause": "当前 V0.1 的规则基线发现响应未满足预期。",
        "recommendation": "补充响应内容，并逐项核对 Skill 的输入、约束和输出格式。",
    }
