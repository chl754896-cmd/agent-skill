# EvalForge V0.1 Workflow

## Flow

```text
SKILL.md → parser → capability extraction → case generation → evaluator → rubric → badcase analyzer → reporter
```

## Offline baseline

EvalForge always supports static parsing, seven baseline capabilities, six deterministic case types, rule-based scoring, and report generation without an API key.

## Scoring

The Rubric scores instruction following, constraint following, completeness, output format, accuracy, and robustness from 0 to 100. The overall score is their arithmetic mean.

- 80–100: `pass`
- 60–79: `warning`
- 0–59: `fail`

V0.1 uses transparent heuristics: missing responses score zero; format, missing-information, and constraint cases inspect simple observable response signals. This is a baseline, not a semantic judge.

## DeepSeek mode

`--use-ai` enables optional AI assistance. All calls live in `evalforge/ai.py`, use `DEEPSEEK_API_KEY`, `https://api.deepseek.com`, and default to `deepseek-v4-flash` unless `DEEPSEEK_MODEL` overrides it. Missing keys or failed calls yield `skipped` or `error` states and preserve offline operation.

## Outputs

- `eval_cases.json`: generated test cases.
- `eval_results.json`: per-case response, Rubric, and Badcase result.
- `eval_report.md` and `eval_report.json`: summarized evaluation reports.
