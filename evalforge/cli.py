"""EvalForge 命令行接口。"""

import argparse
import json
from pathlib import Path

from .capability import extract_capabilities
from .evaluator import evaluate_cases
from .generator import generate_cases
from .parser import SkillNotFoundError, parse_skill
from .reporter import write_reports
from .skill_analyzer import analyze_skill


def _write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def command_analyze(args):
    skill = parse_skill(args.skill_path)
    result = {
        "skill": skill.to_dict(),
        "capability_result": extract_capabilities(skill, args.use_ai),
        **analyze_skill(skill, args.use_ai),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_generate(args):
    skill = parse_skill(args.skill_path)
    capability_result = extract_capabilities(skill, args.use_ai)
    result = generate_cases(skill, capability_result, args.use_ai)
    result.update({"skill_path": str(args.skill_path), **analyze_skill(skill, args.use_ai)})
    _write_json(args.output, result)
    print(f"已生成 {len(result['cases'])} 个测试 Case：{args.output}")
    return 0


def command_evaluate(args):
    case_data = json.loads(Path(args.cases_path).read_text(encoding="utf-8"))
    cases = case_data["cases"] if isinstance(case_data, dict) else case_data
    responses = {}
    if args.responses:
        responses = json.loads(Path(args.responses).read_text(encoding="utf-8"))
    evaluation = evaluate_cases(cases, responses, args.use_ai)
    for key in ("skill", "skill_path", "skill_profile", "static_analysis"):
        if isinstance(case_data, dict) and key in case_data:
            evaluation[key] = case_data[key]
    _write_json(args.output, evaluation)
    print(f"已完成 {len(cases)} 个 Case 的评测：{args.output}")
    return 0


def command_report(args):
    evaluation = json.loads(Path(args.results_path).read_text(encoding="utf-8"))
    write_reports(evaluation, args.markdown_output, args.json_output, args.docx_output)
    print("已生成报告：eval_report_zh-CN.md、eval_report_en-US.md、eval_report_zh-CN.docx、eval_report_en-US.docx，以及兼容旧版的输出文件。")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="evalforge", description="Agent Skill 自动评测工具")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("analyze", "generate"):
        subparser = subparsers.add_parser(name)
        subparser.add_argument("skill_path")
        subparser.add_argument("--use-ai", action="store_true")
        if name == "generate":
            subparser.add_argument("--output", default="eval_cases.json")
            subparser.set_defaults(handler=command_generate)
        else:
            subparser.set_defaults(handler=command_analyze)
    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument("cases_path")
    evaluate.add_argument("--responses")
    evaluate.add_argument("--output", default="eval_results.json")
    evaluate.add_argument("--use-ai", action="store_true")
    evaluate.set_defaults(handler=command_evaluate)
    report = subparsers.add_parser("report")
    report.add_argument("results_path")
    report.add_argument("--markdown-output", default="eval_report.md")
    report.add_argument("--json-output", default="eval_report.json")
    report.add_argument("--docx-output", default="eval_report.docx")
    report.set_defaults(handler=command_report)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except SkillNotFoundError as error:
        parser.error(str(error))
    except FileNotFoundError as error:
        parser.error(f"未找到文件：{error.filename or error}")


if __name__ == "__main__":
    raise SystemExit(main())
