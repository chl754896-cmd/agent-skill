# EvalForge

EvalForge is a lightweight evaluation toolkit for Agent Skills: parse a `SKILL.md`, extract capabilities, generate test cases, score responses, classify badcases, and produce reports.

## What is EvalForge?

EvalForge turns a written Skill specification into an executable V0.1 evaluation workflow. It works offline by default and can optionally use DeepSeek to enrich analysis and case generation.

## Why EvalForge?

Agent Skills often describe requirements in prose. EvalForge makes those requirements testable, traceable, and reportable without a large agent platform.

## Workflow

```text
Skill → Parse → Capabilities → Test Cases → Evaluation → Badcases → Report
```

## Features

- Parse skill name, description, inputs, outputs, rules, constraints, prohibitions, and examples.
- Extract seven baseline evaluation capabilities.
- Generate normal, boundary, constraint, conflict, missing-information, and format cases.
- Score six rubric dimensions on a 0–100 scale.
- Classify failures with a clear Badcase taxonomy.
- Generate Markdown and JSON reports.
- Use optional DeepSeek AI assistance through one centralized integration point.

## Quick Start

```bash
pip install -e .
evalforge analyze examples/resume-review
evalforge generate examples/resume-review
evalforge evaluate eval_cases.json
evalforge report eval_results.json
```

## CLI

```text
evalforge analyze <skill_path> [--use-ai]
evalforge generate <skill_path> [--use-ai] [--output eval_cases.json]
evalforge evaluate <cases_path> [--responses responses.json] [--output eval_results.json]
evalforge report <results_path> [--markdown-output eval_report.md] [--json-output eval_report.json]
```

## Example

`examples/resume-review/` is a simple resume-review Skill. `examples/text-review/` preserves the earlier Text Review Demo as the first runnable workflow example.

## Badcase Taxonomy

`instruction_following`, `constraint_violation`, `missing_information`, `format_error`, `accuracy_error`, `hallucination`, `logic_error`, `incomplete_answer`, `redundancy`, `robustness_failure`, and `other`.

## DeepSeek AI Mode

The baseline works without any API key. To enable optional AI assistance:

```bash
export DEEPSEEK_API_KEY="your-key"
export DEEPSEEK_MODEL="deepseek-v4-flash"  # optional override
evalforge generate examples/resume-review --use-ai
```

EvalForge uses the OpenAI Python SDK with the DeepSeek endpoint. Keys are read only from `DEEPSEEK_API_KEY`; never commit them.

## GitHub Actions

Push and pull-request runs install the package and execute offline unit tests. Manual runs accept `skill_path` and `use_ai`; when AI is enabled, the workflow reads the `DEEPSEEK_API_KEY` repository secret and uploads an `evalforge-result` Artifact.

## Project Structure

```text
evalforge/       core parser, generator, evaluator, rubric, analyzer, reporter, CLI
examples/        runnable example Skills and workflows
tests/           offline unit tests
evals/           self-evaluation configuration
```

## Roadmap

- V0.1: deterministic Skill evaluation baseline.
- Next: richer AI-generated cases, judge calibration, and configurable Rubrics.

## License

MIT. See [LICENSE](LICENSE).
