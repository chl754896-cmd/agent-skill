"""Static, evidence-based analysis for Agent Skill specifications.

The rule baseline deliberately stays small and deterministic.  It turns the
sections that actually exist in ``SKILL.md`` into a profile and then evaluates
the document design; it never fabricates a missing section.
"""

from __future__ import annotations

from copy import deepcopy

from .ai import ai_skill_analysis


DIMENSIONS = (
    "goal_clarity", "capability_coverage", "instruction_quality",
    "input_definition", "output_contract", "constraint_design",
    "boundary_handling", "tool_workflow_design", "robustness",
    "maintainability",
)

PROFILE_FIELDS = (
    "name", "purpose", "target_scenarios", "inputs", "outputs", "tools",
    "constraints", "prohibitions", "workflow_steps", "failure_handling",
    "dependencies",
)


def _items(text: str) -> list[str]:
    """Extract explicit list-like content without interpreting new facts."""
    if not text:
        return []
    values = []
    for line in text.splitlines():
        value = line.strip().lstrip("-*•0123456789. ").strip()
        if value:
            values.append(value)
    return values


def _section(skill, *keywords: str) -> tuple[str, str]:
    for title, content in skill.sections.items():
        if any(keyword.lower() in title.lower() for keyword in keywords):
            return title, content
    return "", ""


def extract_skill_profile(skill) -> dict:
    """Return only information explicitly present in the parsed Skill."""
    workflow_title, workflow = _section(skill, "workflow", "流程", "步骤")
    failure_title, failure = _section(skill, "failure", "fallback", "错误", "异常", "失败")
    tools_title, tools = _section(skill, "tool", "工具")
    deps_title, dependencies = _section(skill, "depend", "依赖", "环境")
    target_scenarios = _items(skill.target) or _items(skill.description)
    return {
        "name": skill.name,
        "purpose": skill.target or skill.description or "",
        "target_scenarios": target_scenarios,
        "inputs": _items(skill.inputs),
        "outputs": _items(skill.outputs),
        "tools": _items(tools),
        "constraints": _items(skill.constraints) + _items(skill.rules),
        "prohibitions": _items(skill.prohibitions),
        "workflow_steps": _items(workflow),
        "failure_handling": _items(failure),
        "dependencies": _items(dependencies),
    }


def _rating(score: int) -> str:
    if score >= 90:
        return "excellent"
    if score >= 75:
        return "strong"
    if score >= 60:
        return "moderate"
    if score >= 40:
        return "weak"
    return "critical"


def _finding(title, category, severity, conclusion, section, evidence, impact, recommendation):
    return {
        "title": title,
        "category": category,
        "severity": severity,
        "conclusion": conclusion,
        "evidence": [{"source": "SKILL.md", "quote_or_summary": evidence, "section": section or "Document"}],
        "impact": impact,
        "recommendation": recommendation,
    }


def _dimension(name, present, section, evidence, good, weak, recommendation):
    score = 85 if present else 35
    return {
        "score": score,
        "rating": _rating(score),
        "summary": good if present else weak,
        "evidence": [evidence] if evidence else [],
        "strengths": [good] if present else [],
        "weaknesses": [] if present else [weak],
        "recommendations": [] if present else [recommendation],
    }


def _rule_analysis(skill, profile):
    sections = skill.sections
    has = lambda value: bool(value and str(value).strip())
    workflow = profile["workflow_steps"]
    failure = profile["failure_handling"]
    dimensions = {
        "goal_clarity": _dimension("goal_clarity", has(profile["purpose"]), "目标", profile["purpose"], "The purpose is explicitly stated.", "The Skill does not state a clear purpose.", "Add a concise goal section."),
        "capability_coverage": _dimension("capability_coverage", has(profile["outputs"]), "输出", "; ".join(profile["outputs"]), "Expected capabilities are represented by declared outputs.", "Capabilities cannot be inferred from a declared output contract.", "List the expected outputs or capabilities."),
        "instruction_quality": _dimension("instruction_quality", has(skill.rules) or has(skill.target), "规则/目标", skill.rules or skill.target, "The Skill contains explicit execution guidance.", "The Skill lacks explicit execution instructions.", "Add ordered execution instructions."),
        "input_definition": _dimension("input_definition", has(profile["inputs"]), "输入", "; ".join(profile["inputs"]), "The expected input is declared.", "Inputs are not defined.", "Define required, optional, and invalid inputs."),
        "output_contract": _dimension("output_contract", has(profile["outputs"]), "输出", "; ".join(profile["outputs"]), "The output contract is visible to an Agent.", "Outputs are not defined.", "Specify output fields, format, and completion criteria."),
        "constraint_design": _dimension("constraint_design", has(profile["constraints"]) or has(profile["prohibitions"]), "约束/禁止项", "; ".join(profile["constraints"] + profile["prohibitions"]), "Constraints or prohibitions bound Agent behavior.", "No constraints or prohibitions are declared.", "Add explicit constraints and prohibited behavior."),
        "boundary_handling": _dimension("boundary_handling", has(failure), "失败处理", "; ".join(failure), "The Skill documents handling for non-happy paths.", "No fallback or failure-handling section is declared.", "Define behavior for incomplete, malformed, conflicting, and unsupported inputs."),
        "tool_workflow_design": _dimension("tool_workflow_design", bool(workflow or profile["tools"]), "流程/工具", "; ".join(workflow or profile["tools"]), "A tool or workflow sequence is documented.", "No tool use or workflow sequence is declared.", "Document tools, ordering, and verification points when applicable."),
        "robustness": _dimension("robustness", has(failure) and has(profile["constraints"]), "失败处理", "; ".join(failure), "Constraints and fallback guidance support predictable behavior.", "Robustness controls are incomplete because fallback guidance is absent or constraints are underspecified.", "Add validation and fallback behavior for exceptional input."),
        "maintainability": _dimension("maintainability", bool(sections), "Document", "Structured headings found in SKILL.md.", "Structured headings make the Skill easier to revise.", "The Skill lacks sufficient structure for safe maintenance.", "Organize requirements into stable, named sections."),
    }
    strengths, weaknesses, audit, edge = [], [], [], []
    for name, dimension in dimensions.items():
        if dimension["strengths"]:
            strengths.append(_finding(name.replace("_", " ").title(), name, "low", dimension["summary"], "SKILL.md", dimension["evidence"][0] if dimension["evidence"] else "Structured content is present.", "Clear requirements reduce inconsistent Agent behavior.", "Preserve this explicit design as the Skill evolves."))
        else:
            severity = "high" if name in {"input_definition", "output_contract", "constraint_design", "robustness"} else "medium"
            weaknesses.append(_finding(name.replace("_", " ").title(), name, severity, dimension["summary"], "SKILL.md", "The corresponding section is missing or empty.", "Agents may make incompatible assumptions during execution.", dimension["recommendations"][0]))
    if not profile["inputs"]:
        audit.append(_finding("Undefined input contract", "missing_prerequisite", "high", "The Skill does not define required inputs.", "输入", "No input section was found.", "An Agent cannot reliably validate user requests.", "Define required, optional, and invalid inputs."))
    if not profile["outputs"]:
        audit.append(_finding("Undefined output contract", "missing_validation", "high", "The Skill does not define expected outputs.", "输出", "No output section was found.", "Results cannot be verified consistently.", "Specify output format and acceptance criteria."))
    if not profile["workflow_steps"]:
        audit.append(_finding("Implicit execution order", "unclear_priority", "medium", "The Skill has no explicit workflow sequence.", "流程", "No workflow section was found.", "Agents can apply valid instructions in inconsistent order.", "Add an ordered workflow and rule priority."))
    if not profile["failure_handling"]:
        edge.append(_finding("Missing fallback behavior", "fallback", "high", "The Skill does not define a fallback for malformed, partial, conflicting, or unsupported input.", "失败处理", "No failure-handling section was found.", "Non-happy paths can produce inconsistent or unsafe output.", "Define validation, clarification, refusal, and fallback behavior."))
    edge.extend([
        _finding("Partial input scenario", "partial_input", "medium", "Verify that missing fields trigger clarification rather than invention.", "输入", profile["inputs"][0] if profile["inputs"] else "Input contract is absent.", "Partial data can lead to unsupported assumptions.", "Add a Case with one required field omitted."),
        _finding("Conflicting instruction scenario", "conflicting_instruction", "medium", "Verify that constraints outrank conflicting user instructions.", "约束", "; ".join(profile["constraints"] + profile["prohibitions"]) or "No explicit priority rule found.", "Conflicting requests can bypass intended safeguards.", "Add a conflict-resolution priority rule and regression Case."),
    ])
    return dimensions, strengths, weaknesses, audit, edge


def _valid_ai_analysis(data):
    if not isinstance(data, dict) or not isinstance(data.get("profile"), dict) or not isinstance(data.get("dimensions"), dict):
        return False
    profile = data["profile"]
    if set(PROFILE_FIELDS) - set(profile) or not isinstance(profile["name"], str) or not isinstance(profile["purpose"], str):
        return False
    if any(not isinstance(profile[key], list) or not all(isinstance(value, str) for value in profile[key]) for key in PROFILE_FIELDS if key not in {"name", "purpose"}):
        return False
    if set(DIMENSIONS) - set(data["dimensions"]):
        return False
    for name in DIMENSIONS:
        value = data["dimensions"][name]
        required = {"score", "rating", "summary", "evidence", "strengths", "weaknesses", "recommendations"}
        if not isinstance(value, dict) or not required.issubset(value) or not isinstance(value["score"], (int, float)) or not 0 <= value["score"] <= 100 or value["rating"] not in {"excellent", "strong", "moderate", "weak", "critical"}:
            return False
    return all(isinstance(data.get(key), list) for key in ("strengths", "weaknesses", "instruction_issues", "edge_case_issues")) and isinstance(data.get("recommendations"), dict) and {"P0", "P1", "P2"}.issubset(data["recommendations"])


def _merge_unique(existing, additional):
    seen = {str(item) for item in existing}
    return existing + [item for item in additional if str(item) not in seen]


def analyze_skill(skill, use_ai=False):
    """Create the V0.2 static analysis, optionally enriched by DeepSeek."""
    profile = extract_skill_profile(skill)
    dimensions, strengths, weaknesses, audit, edge = _rule_analysis(skill, profile)
    result = {
        "skill_profile": profile,
        "static_analysis": {
            "overall_score": round(sum(item["score"] for item in dimensions.values()) / len(dimensions)),
            "overall_rating": _rating(round(sum(item["score"] for item in dimensions.values()) / len(dimensions))),
            "dimensions": dimensions,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "instruction_audit": audit,
            "edge_case_analysis": edge,
            "ai": {"status": "skipped"},
        },
    }
    if use_ai:
        ai_result = ai_skill_analysis(skill)
        result["static_analysis"]["ai"] = ai_result
        if ai_result.get("status") == "success" and _valid_ai_analysis(ai_result.get("data")):
            data = ai_result["data"]
            for key in PROFILE_FIELDS:
                if key in data["profile"] and isinstance(data["profile"][key], list):
                    result["skill_profile"][key] = _merge_unique(result["skill_profile"].get(key, []), data["profile"][key])
            result["static_analysis"]["dimensions"] = data["dimensions"]
            result["static_analysis"]["overall_score"] = round(sum(item["score"] for item in data["dimensions"].values()) / len(DIMENSIONS))
            result["static_analysis"]["overall_rating"] = _rating(result["static_analysis"]["overall_score"])
            for target, source in (("strengths", "strengths"), ("weaknesses", "weaknesses"), ("instruction_audit", "instruction_issues"), ("edge_case_analysis", "edge_case_issues")):
                if all(isinstance(item, dict) for item in data[source]):
                    result["static_analysis"][target] = _merge_unique(result["static_analysis"][target], data[source])
        elif ai_result.get("status") == "success":
            result["static_analysis"]["ai"] = {**ai_result, "status": "error", "data": None}
    return result
