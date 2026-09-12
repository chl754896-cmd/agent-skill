"""确定性的 V0.1 Rubric 评分。"""

DIMENSIONS = ("instruction_following", "constraint_following", "completeness", "output_format", "accuracy", "robustness")


def status_from_score(score):
    return "pass" if score >= 80 else "warning" if score >= 60 else "fail"


def score_response(case, response):
    """通过是否回答、是否列点等简单信号生成可解释基线分数。"""
    scores = {dimension: 100 for dimension in DIMENSIONS}
    response = (response or "").strip()
    if not response:
        scores = {dimension: 0 for dimension in DIMENSIONS}
    else:
        if case["category"] == "missing_information" and "缺" not in response and "无法" not in response:
            scores["robustness"] = 60
        if case["category"] == "format_requirement" and "-" not in response and "•" not in response:
            scores["output_format"] = 60
        if case["category"] == "constraint" and "不能" not in response and "不" not in response:
            scores["constraint_following"] = 60
        if len(response) < 20:
            scores["completeness"] = min(scores["completeness"], 60)
    overall_score = round(sum(scores.values()) / len(scores))
    return {"dimension_scores": scores, "overall_score": overall_score, "status": status_from_score(overall_score)}
