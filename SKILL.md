---
name: EvalForge Agent Skill Evaluation
description: Parse Agent Skills, generate test cases, score responses, classify badcases, and produce evaluation reports.
---

# EvalForge Agent Skill Evaluation

## 目标

使用 EvalForge 对包含 `SKILL.md` 的 Agent Skill 执行静态分析、Case 生成、规则评分和报告生成。

## 使用方式

1. 运行 `evalforge analyze <skill_path>` 解析 Skill 与能力点。
2. 运行 `evalforge generate <skill_path>` 生成 `eval_cases.json`。
3. 准备按 Case ID 映射的 `responses.json`，运行 `evalforge evaluate`。
4. 运行 `evalforge report <results_path>` 生成 Markdown 与 JSON 报告。

## 约束

- 默认离线运行，不要求 DeepSeek API Key。
- 需要 AI 辅助时才使用 `--use-ai` 和 `DEEPSEEK_API_KEY`。
- 不在日志、代码或报告中输出 API Key。
