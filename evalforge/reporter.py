"""评测报告生成。"""

import json
from collections import Counter
from pathlib import Path


def build_report(evaluation):
    results = evaluation.get("results", [])
    rubrics = [item.get("final_rubric") or item.get("rubric") or item.get("rule_rubric") for item in results]
    statuses = Counter(rubric["status"] for rubric in rubrics)
    scores = [rubric["overall_score"] for rubric in rubrics]
    capabilities = {}
    for rubric in rubrics:
        for name, score in rubric["dimension_scores"].items():
            capabilities.setdefault(name, []).append(score)
    capability_scores = {name: round(sum(values) / len(values)) for name, values in capabilities.items()}
    badcases = [item["badcase"] for item in results if item["badcase"]]
    distribution = dict(Counter(item["type"] for item in badcases))
    summary = {"total_cases": len(results), "pass": statuses["pass"], "warning": statuses["warning"],
               "fail": statuses["fail"], "pass_rate": round(statuses["pass"] / len(results) * 100, 1) if results else 0,
               "overall_score": round(sum(scores) / len(scores)) if scores else 0}
    return {"summary": summary, "capability_scores": capability_scores, "failed_cases": badcases,
            "badcase_distribution": distribution, "root_cause_analysis": "基于 V0.1 规则基线的首要失败维度。",
            "recommendations": ["优先修复高严重度 Badcase。", "为低分能力点补充针对性 Case。"]}


def markdown_report(report):
    summary = report["summary"]
    failed_lines = [f"- {item['case_id']}: {item['type']}" for item in report["failed_cases"]] or ["- None"]
    distribution_lines = [f"- {key}: {value}" for key, value in report["badcase_distribution"].items()] or ["- None"]
    lines = ["# EvalForge Evaluation Report", "", "## Summary", *[f"- {key}: {value}" for key, value in summary.items()],
             "", "## Capability Scores", *[f"- {key}: {value}" for key, value in report["capability_scores"].items()],
             "", "## Failed Cases", *failed_lines,
             "", "## Badcase Distribution", *distribution_lines,
             "", "## Root Cause Analysis", report["root_cause_analysis"], "", "## Recommendations",
             *[f"- {item}" for item in report["recommendations"]]]
    return "\n".join(lines) + "\n"


def write_reports(evaluation, markdown_path="eval_report.md", json_path="eval_report.json"):
    report = build_report(evaluation)
    Path(markdown_path).write_text(markdown_report(report), encoding="utf-8")
    Path(json_path).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
