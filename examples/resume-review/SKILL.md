---
name: Resume Review
description: Review a resume without inventing facts and provide actionable improvements.
---

# Resume Review

## 目标

帮助求职者审核简历文本，发现表达和结构问题，并给出可执行的修改建议。

## 输入

一份简历文本，可能包含个人简介、经历、技能、教育背景和项目。

## 输出

- 总体评价
- 优势
- 问题
- 修改建议

## 约束

- 必须分点输出。
- 必须给出明确修改建议。
- 最多给出 5 条核心问题。

## 明确禁止项

- 不允许虚构简历中不存在的经历、成果或技能。

## 示例

输入：我有三年 Python 后端开发经验，负责过订单系统。

输出：列出已有优势，并建议补充订单系统的规模、指标和个人贡献。
