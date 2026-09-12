"""Case、模型响应、Rubric 和 Badcase 的编排。"""

from .ai import ai_json
from .analyzer import classify_badcase
from .rubric import score_response


def evaluate_cases(cases, responses=None, use_ai=False):
    """评测 responses.json 中按 case_id 保存的响应；未提供响应会产生可分析的失败。"""
    responses = responses or {}
    results = []
    for case in cases:
        response = responses.get(case["id"], "")
        rubric = score_response(case, response)
        judge = {"status": "skipped"}
        if use_ai:
            judge = ai_json(
                "作为独立评测 Judge，请返回 JSON，评估以下 Case、预期行为和模型响应。"
                f"Case: {case}\nResponse: {response}"
            )
        results.append({"case": case, "response": response, "rubric": rubric, "judge": judge,
                        "badcase": classify_badcase(case, response, rubric)})
    return {"results": results, "judge": {"status": "skipped" if not use_ai else "requested"}}
