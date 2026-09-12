"""从 Skill 说明提取可评测能力点。"""

from .ai import ai_json


CAPABILITY_DEFINITIONS = {
    "instruction_following": "遵循 Skill 的目标和执行步骤。",
    "input_understanding": "正确理解用户提供的输入信息。",
    "constraint_following": "遵守明确限制和禁止项。",
    "output_format": "按要求的格式组织输出。",
    "completeness": "覆盖要求的输出组成部分。",
    "accuracy": "不虚构、不过度推断，并保持事实准确。",
    "robustness": "面对边界、缺失和冲突信息时保持稳定。",
}


def extract_capabilities(skill, use_ai=False):
    """返回基础能力点；AI 仅作为可选的补充状态。"""
    evidence = {
        "instruction_following": skill.target or skill.description,
        "input_understanding": skill.inputs,
        "constraint_following": skill.constraints or skill.prohibitions,
        "output_format": skill.outputs,
        "completeness": skill.outputs,
        "accuracy": skill.prohibitions or skill.rules,
        "robustness": skill.constraints,
    }
    capabilities = []
    for capability_id, description in CAPABILITY_DEFINITIONS.items():
        priority = "high" if capability_id in {"constraint_following", "accuracy"} else "medium"
        capabilities.append(
            {"id": capability_id, "name": capability_id.replace("_", " ").title(),
             "description": description, "evidence": evidence[capability_id], "priority": priority}
        )
    ai_status = {"status": "skipped"}
    if use_ai:
        ai_status = ai_json(f"仅返回 JSON 数组，补充以下 Skill 的评测能力点：{skill.to_dict()}")
    return {"capabilities": capabilities, "ai": ai_status}
