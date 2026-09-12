# Text Review Workflow

一个面向学习和实践的文本审核项目。它先使用可解释的 Python 规则检查文本，再可选地使用 DeepSeek AI 语义审核，最后生成 Markdown 报告和 JSON 结果。

## Workflow 架构

```text
用户文本
  ↓
输入校验
  ↓
Python 规则审核
  ↓
DeepSeek AI 语义审核（可选）
  ↓
合并审核结果与综合评分
  ↓
Markdown 报告 / JSON 结果
  ↓
GitHub Actions / Artifact
```

## 当前功能

- 空文本检查、文本长度检查、重复句子检查。
- 结构化规则审核结果。
- 可选 AI 语义审核：表达清晰度、语病、逻辑、结构、冗余和修改建议。
- `0-100` 综合评分与 `pass`、`warning`、`fail` 状态。
- Markdown 报告和 UTF-8 JSON 结果。
- GitHub Actions 自动测试，以及手动生成报告 Artifact。

## 本地运行

安装依赖：

```bash
python -m pip install -r requirements.txt
```

仅运行规则审核：

```bash
python review.py "今天下雨了。今天下雨了。我带了雨伞。" --output report.md --json result.json
```

## AI 模式

AI 模式使用 OpenAI Python SDK 连接 DeepSeek 的 Responses API。默认模型为 `deepseek-v4-flash`，也可通过 `DEEPSEEK_MODEL` 修改模型。

```bash
export DEEPSEEK_API_KEY="你的 DeepSeek API Key"
python review.py "需要审核的文本" --ai --output report.md --json result.json
```

Windows PowerShell：

```powershell
$env:DEEPSEEK_API_KEY = "你的 DeepSeek API Key"
python review.py "需要审核的文本" --ai --output report.md --json result.json
```

API Key 只从环境变量 `DEEPSEEK_API_KEY` 读取；请勿写入代码、提交到 Git，或记录到日志。没有 API Key 时，`--ai` 会跳过 AI 审核并继续保留规则审核结果。

## 测试

```bash
python -m unittest test_review.py -v
```

测试使用 mock 模拟 DeepSeek Responses API 调用，不会调用真实 API，也不会产生 API 费用。

## GitHub Actions 与 Artifact

- `push` 和 `pull_request`：安装依赖并只运行自动测试。
- 手动运行 `Text Review Tests`：填写 `text`，可选择 `use_ai`。
- 勾选 `use_ai` 时，Workflow 从 GitHub Secret `DEEPSEEK_API_KEY` 读取密钥。
- 完成后，在运行记录的 **Artifacts** 区域下载 `text-review-result`，其中包含 `report.md` 和 `result.json`。

## 项目路线图

- V1：规则审核、结构化结果和 GitHub Actions。
- V2：可选 DeepSeek AI 语义审核、综合评分和双格式报告。
- 后续：优化提示词、增加人工反馈、扩展规则与报告展示。
