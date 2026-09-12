"""Case、模型响应、Rubric 和 Badcase 的编排。"""

from .ai import ai_json
from .analyzer import TAXONOMY, classify_badcase
from .rubric import DIMENSIONS, score_response, status_from_score


def evaluate_cases(cases, responses=None, use_ai=False):
    """评测 responses.json 中按 case_id 保存的响应；未提供响应会产生可分析的失败。"""
    responses = responses or {}
    results = []
    for case in cases:
        response = responses.get(case["id"], "")
        rule_rubric = score_response(case, response)
        ai_judge = {"status": "skipped"}
        final_rubric = rule_rubric
        if use_ai:
            judge_result = ai_json(
                "作为独立评测 Judge，返回 JSON，必须包含 dimension_scores、overall_score、status、"
                "reasoning_summary、badcase_type、recommendation。dimension_scores 必须含 "
                "instruction_following、constraint_following、completeness、output_format、accuracy、robustness，"
                "所有分数为 0-100，status 为 pass/warning/fail。"
                "评估以下 Case、预期行为和模型响应。"
                f"Case: {case}\nResponse: {response}"
            )
            ai_judge = _normalize_judge(judge_result)
            if ai_judge["status"] == "success":
                final_rubric = {key: ai_judge[key] for key in ("dimension_scores", "overall_score", "status")}
        badcase = classify_badcase(case, response, final_rubric)
        if ai_judge["status"] == "success" and ai_judge["badcase_type"] in TAXONOMY and final_rubric["status"] != "pass":
            badcase = badcase or classify_badcase(case, response, rule_rubric)
            badcase["type"] = ai_judge["badcase_type"]
            badcase["reason"] = ai_judge["reasoning_summary"] or badcase["reason"]
            badcase["root_cause"] = "DeepSeek Judge 的独立评测结论。"
            badcase["recommendation"] = ai_judge["recommendation"] or badcase["recommendation"]
        results.append({
            "case": case, "response": response, "rule_rubric": rule_rubric,
            "ai_judge": ai_judge, "final_rubric": final_rubric,
            "rubric": final_rubric, "judge": ai_judge, "badcase": badcase,
        })
    return {"results": results, "judge": {"status": "skipped" if not use_ai else "requested"}}


def _normalize_judge(judge_result):
    """只接受完整、可解释且分数合法的 AI Judge 输出。"""
    if judge_result["status"] != "success" or not isinstance(judge_result["data"], dict):
        return judge_result
    data = judge_result["data"]
    required = {"dimension_scores", "overall_score", "status", "reasoning_summary", "badcase_type", "recommendation"}
    scores = data.get("dimension_scores")
    if (
        not required.issubset(data)
        or not isinstance(scores, dict)
        or set(DIMENSIONS) - set(scores)
        or any(isinstance(scores[name], bool) or not isinstance(scores[name], (int, float)) or not 0 <= scores[name] <= 100 for name in DIMENSIONS)
        or isinstance(data["overall_score"], bool) or not isinstance(data["overall_score"], (int, float)) or not 0 <= data["overall_score"] <= 100
        or data["status"] not in {"pass", "warning", "fail"}
        or data["status"] != status_from_score(round(data["overall_score"]))
        or not all(isinstance(data[key], str) for key in ("reasoning_summary", "badcase_type", "recommendation"))
    ):
        return {"status": "error", "model": judge_result.get("model"), "data": None}
    return {**{key: data[key] for key in required}, "status": "success", "model": judge_result.get("model")}
