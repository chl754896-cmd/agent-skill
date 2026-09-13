"""唯一的 DeepSeek AI 调用入口。"""

import json
import os


DEFAULT_MODEL = "deepseek-v4-flash"
BASE_URL = "https://api.deepseek.com"


def ai_json(prompt, client_factory=None):
    """请求 JSON；缺少 Key 或请求失败时安全返回状态，不暴露异常。"""
    model = os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL)
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return {"status": "skipped", "model": model, "data": None}
    try:
        if client_factory is None:
            from openai import OpenAI

            client_factory = OpenAI
        client = client_factory(api_key=api_key, base_url=BASE_URL)
        response = client.responses.create(model=model, input=prompt)
        return {"status": "success", "model": model, "data": json.loads(response.output_text)}
    except Exception:
        return {"status": "error", "model": model, "data": None}


def ai_skill_analysis(skill, client_factory=None):
    """Request a single validated, structured static audit from DeepSeek.

    A single request keeps the optional enhancement inexpensive while assigning
    the model the Capability Analyst, Strength/Weakness Analyst, Instruction
    Auditor, Edge-case Analyst, Root Cause Analyst, and Recommendation
    Generator roles.  Consumers still validate the payload before using it.
    """
    prompt = (
        "You are an Agent Skill capability analyst, instruction auditor, edge-case analyst, "
        "root-cause analyst, and recommendation generator. Return JSON only with: "
        "profile, dimensions, strengths, weaknesses, instruction_issues, edge_case_issues, "
        "recommendations (P0/P1/P2), overall_assessment. Profile must use name, purpose, "
        "target_scenarios, inputs, outputs, tools, constraints, prohibitions, workflow_steps, "
        "failure_handling, dependencies. Dimensions must include goal_clarity, capability_coverage, "
        "instruction_quality, input_definition, output_contract, constraint_design, boundary_handling, "
        "tool_workflow_design, robustness, maintainability. Every dimension must include score 0-100, "
        "rating, summary, evidence, strengths, weaknesses, recommendations. Findings must explain "
        "conclusion, evidence, impact, and recommendation. Do not invent content absent from the Skill.\n"
        f"Skill: {skill.to_dict()}"
    )
    return ai_json(prompt, client_factory=client_factory)
