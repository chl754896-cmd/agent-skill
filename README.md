# EvalForge V0.2.0

EvalForge is an **Automated Agent Skill Analysis, Evaluation & Badcase Intelligence** toolkit. It turns a `SKILL.md` specification and genuine model responses into an evidence-based assessment of what an Agent Skill does well, what is unclear or risky, and what to improve next.

## Why EvalForge

Agent Skills are typically prose. Omitted input rules, output contracts, and fallback behavior can lead to inconsistent Agent behavior. EvalForge makes those decisions visible, testable, and reportable without requiring an API key.

```text
SKILL.md
  ↓ Static Skill Analysis
Capability Extraction → Test Case Generation → Model Responses
  ↓                                      ↓
Profile, strengths, risks                   Dynamic Evaluation → Rubric → Badcases
  └──────────────────────────────→ Bilingual reports and prioritized recommendations
```

## Static Analysis and Dynamic Evaluation

| Layer | Question | Input |
| --- | --- | --- |
| Static Skill Analysis | Is the specification clear, complete, safe, and maintainable? | `SKILL.md` |
| Dynamic Evaluation | Does a model response satisfy generated Skill Cases? | Cases plus `responses.json` |

Static analysis assesses ten dimensions: goal clarity, capability coverage, instruction quality, input definition, output contract, constraint design, boundary handling, tool/workflow design, robustness, and maintainability. Findings use **Conclusion → Evidence → Impact → Recommendation**.

## V0.2 Scoring Model

Reports keep static and dynamic evidence separate, then publish one consistent composite score:

```text
Composite score = static score × 55% + dynamic score × 45%
```

The scorecard always exposes `static_score`, `dynamic_score`, `composite_score`, rating, maturity level, and production readiness. A strong dynamic result does not hide unresolved static design risks. If static analysis is unavailable for a legacy result file, EvalForge uses the dynamic score alone and records that fallback in the scorecard weights.

## Offline Rule Baseline

EvalForge works offline by default. The deterministic baseline parses a Skill, extracts seven core capabilities, creates six case categories, applies a transparent Rubric, classifies Badcases, and produces bilingual Markdown, DOCX, and JSON reports. No network access is required.

## DeepSeek Enhanced Mode

Set `DEEPSEEK_API_KEY` and pass `--use-ai` to optionally enhance capability extraction, Case generation, static auditing, and dynamic AI judging. DeepSeek output is validated before use. Missing keys, failed requests, or malformed AI payloads automatically fall back to the offline baseline.

```bash
# Set DEEPSEEK_API_KEY in your shell with your own secret value.
export DEEPSEEK_MODEL="deepseek-v4-flash"  # optional
evalforge analyze examples/resume-review --use-ai
```

Never commit keys. EvalForge reads only `DEEPSEEK_API_KEY` from the environment.

## Run Locally

```bash
python -m pip install -e .
evalforge analyze examples/resume-review
evalforge generate examples/resume-review
evalforge evaluate eval_cases.json --responses examples/resume-review/responses.json
evalforge report eval_results.json
```

For a real Skill, point `analyze` and `generate` to the directory containing its `SKILL.md`, then provide actual model outputs to `evaluate`.

## How responses.json Works

`responses.json` maps every generated Case ID to the model output being assessed:

```json
{
  "case_001": "Model response for the normal case",
  "case_002": "Model response for the boundary case"
}
```

The built-in `examples/resume-review/responses.json` covers six baseline Cases. EvalForge does not invent model responses.

## CLI

```text
evalforge analyze <skill_path> [--use-ai]
evalforge generate <skill_path> [--use-ai] [--output eval_cases.json]
evalforge evaluate <cases_path> [--responses responses.json] [--use-ai] [--output eval_results.json]
evalforge report <results_path>
```

Existing V0.1 report options remain supported. V0.2 automatically produces:

```text
eval_report_zh-CN.md
eval_report_en-US.md
eval_report_zh-CN.docx
eval_report_en-US.docx
eval_report.json
```

The JSON report contains the Skill profile, static analysis, dynamic evaluation, root-cause analysis, P0/P1/P2 recommendations, and final assessment. Each localized report uses its own headings rather than mixing languages.

## GitHub Actions

Push and pull-request runs install EvalForge and run offline tests. A manual run accepts `skill_path`, `responses_path`, and `use_ai`.

- With responses, it produces cases, results, and bilingual reports.
- Without responses, it uploads `eval_cases.json` and explicitly skips evaluation/reporting instead of manufacturing failures.
- AI-enabled runs read `${{ secrets.DEEPSEEK_API_KEY }}`. Secrets are never printed or uploaded.

The `evalforge-result` Artifact contains cases, results, JSON, both Markdown reports, and both DOCX reports when evaluation runs.

## Architecture

```text
parser.py          parse SKILL.md
skill_analyzer.py  profile extraction, ten-dimension analysis, audits
capability.py      baseline capabilities plus validated AI additions
generator.py       six baseline Cases plus validated AI additions
evaluator.py       rule Rubric, optional AI Judge, final Rubric, Badcases
reporter.py        unified data model and bilingual Markdown/DOCX/JSON reports
cli.py             backward-compatible command-line interface
```

## Current Limitations

- Offline scoring is a transparent rule baseline, not a semantic or fact-checking Judge.
- Rule-based static analysis detects explicit content and common omissions; it cannot prove prose is semantically correct.
- Dynamic evaluation needs genuine model responses in `responses.json`.
- DeepSeek is optional and schema-validated, but high-stakes decisions still need human review.
- V0.2 offers a portable professional DOCX layout, not a custom corporate-template system.

## Roadmap

- V0.2: static Skill audit, dynamic evaluation, Badcase intelligence, bilingual reports.
- Future: configurable Rubrics, provider integrations, calibration datasets, and comparative dashboards.

## License

MIT. See [LICENSE](LICENSE).
