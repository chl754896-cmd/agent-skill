# Text Review Demo

这是 EvalForge 的第一个 Workflow 示例，保留原有规则审核、可选 DeepSeek 审核、Markdown 和 JSON 输出能力。

```bash
python review.py "今天下雨了。今天下雨了。我带了雨伞。" --output report.md --json result.json
python -m unittest test_review.py -v
```
