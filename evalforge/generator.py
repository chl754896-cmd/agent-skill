"""基础测试 Case 生成。"""

from .ai import ai_json


CASE_TYPES = (
    ("normal", "提供完整、正常的输入。", "medium"),
    ("boundary", "提供最短但仍有效的输入。", "medium"),
    ("constraint", "请求违反明确约束的内容。", "high"),
    ("conflicting_instruction", "在输入中加入与 Skill 规则冲突的指令。", "high"),
    ("missing_information", "故意省略关键输入信息。", "high"),
    ("format_requirement", "要求严格遵循指定的输出格式。", "medium"),
)


def generate_cases(skill, capability_result, use_ai=False):
    """生成六类确定性 Case，保证没有 API Key 时可用。"""
    capability_ids = [item["id"] for item in capability_result["capabilities"]]
    cases = []
    for index, (category, input_text, severity) in enumerate(CASE_TYPES, start=1):
        cases.append({
            "id": f"case_{index:03d}", "category": category,
            "input": f"{input_text}\nSkill 输入说明：{skill.inputs or '未提供'}",
            "expected_behavior": f"遵循 Skill 目标、约束和输出要求：{skill.outputs or skill.description}",
            "capabilities": capability_ids, "severity": severity,
        })
    ai_status = {"status": "skipped"}
    if use_ai:
        ai_status = ai_json(f"为以下 Skill 补充 JSON 测试案例：{skill.to_dict()}")
    return {"skill": skill.name, "cases": cases, "ai": ai_status}
