# Text Review Workflow V2

## 1. 目标

Text Review Workflow 用规则和可选 AI 审核一段用户文本，并输出可阅读的 Markdown 报告与可处理的 JSON 结果。

## 2. V2 流程

```text
用户文本
  ↓
输入校验
  ↓
Python 规则审核
  ↓
DeepSeek AI 语义审核（可选）
  ↓
合并审核结果
  ↓
综合状态
  ↓
Markdown 报告
  ↓
JSON 结果
  ↓
GitHub Actions
  ↓
Artifact
```

## 3. 规则审核

规则审核不需要网络、API Key 或第三方服务，包含：

- 空文本检查：空文本的规则评分为 `0`。
- 长度检查：少于 10 个字符为“文本过短”；超过 100 个字符提示可能冗余。
- 重复句子检查：识别中英文常见句末标点分隔后的完全重复句子。

规则审核会输出 `status`、`score`、长度检查、重复检查、问题和建议。

## 4. AI 语义审核

传入 `--ai` 时，程序使用 OpenAI Python SDK 连接 DeepSeek 的 Responses API 运行 AI 审核。默认模型为 `deepseek-v4-flash`，可用 `DEEPSEEK_MODEL` 环境变量覆盖。

AI 返回结构化结果，检查：

- 表达清晰度
- 语病
- 逻辑问题
- 结构问题
- 内容冗余
- 修改建议与总结

API Key 仅从 `DEEPSEEK_API_KEY` 环境变量读取。未设置 Key 时，终端会显示“AI 审核未执行：未配置 DEEPSEEK_API_KEY”，规则审核仍会完成。调用失败时不会输出底层异常或敏感信息，JSON 的 `ai_review.status` 为 `error`。

## 5. 综合评分与状态

第一版评分规则保持简单且可解释：

1. 规则评分从 100 开始；文本过短、文本过长、发现重复句子各扣 25 分；空文本为 0 分。
2. 如果 AI 审核成功，先计算五项 AI 评分的平均值，再与规则评分取平均值并四舍五入。
3. 如果 AI 未执行或出错，综合评分直接使用规则评分，保证 V1 功能可独立运行。
4. 综合评分 `80-100` 为 `pass`，`60-79` 为 `warning`，`0-59` 为 `fail`。

## 6. 输出

`--output report.md` 会生成 Markdown 报告，包含综合结果、原始文本、规则审核、AI 语义审核、问题、建议和总结。

`--json result.json` 会生成 UTF-8 JSON，中文不会转换为 Unicode 转义。核心结构为：

```json
{
  "version": "2.0",
  "status": "warning",
  "overall_score": 75,
  "rule_review": {},
  "ai_review": {
    "status": "success",
    "model": "deepseek-v4-flash"
  },
  "issues": [],
  "suggestions": []
}
```

不使用 `--ai` 时，`ai_review.status` 为 `skipped`，Markdown 会显示“AI 语义审核：未执行”。

## 7. 自动化

GitHub Actions 的行为如下：

- `push` 与 `pull_request`：安装 `requirements.txt` 中的依赖后，仅运行单元测试；不会调用真实 DeepSeek API。
- `workflow_dispatch`：输入 `text` 和 `use_ai`。当 `use_ai` 为 `true` 时，通过 GitHub Secret `DEEPSEEK_API_KEY` 传递密钥；否则仅执行规则审核。
- 手动任务在测试成功后生成 `report.md`、`result.json`，并上传名为 `text-review-result` 的 Artifact。

## 8. 测试策略

普通单元测试不依赖真实 API。测试用 `unittest.mock` 模拟 Responses API，覆盖 AI 调用、缺少 API Key、合并逻辑、综合评分和 V2 报告结构；临时报告文件会自动清理。
