---
name: literature-query-builder
description: 面向医学研究方向生成可审查的数据库检索策略。用于将中文医学研究问题转化为 PubMed/MEDLINE 优先的关键词、MeSH 词、同义词、布尔检索式、纳排边界和阶段性报告；适用于系统综述、范围综述、叙述综述、机制综述和医学前沿综述的检索准备。
---

# 医学检索式生成

## 使用前

先读取 `../shared/workflow_contract.md`。本 Skill 只负责生成和修订检索策略，不执行数据库检索。完成后必须暂停等待用户审查。

## 输入

接受以下任意信息：

- 中文或英文研究方向
- 疾病、人群、干预、暴露、结局、机制、技术或诊断方法
- 综述类型
- 目标数据库
- 年份、语言、研究设计限制
- 用户已有关键词或示例文献

如果用户没有指定数据库，提示先由 `literature-orchestrator` 给出医学数据库建议。

## 医学问题拆解

根据主题选择框架：

- PICO：临床干预、诊断、预后、治疗效果。
- PECO：暴露和结局关系。
- PICo：质性研究。
- PCC：范围综述，尤其是概念、领域和研究版图。
- 机制链条：基础医学、转化医学、病理机制。

## 输出内容

生成 `query_plan.md`，包含：

- 研究问题重述
- 推荐问题框架
- 核心概念
- 中文关键词
- 英文关键词
- MeSH/主题词候选
- 同义词和拼写变体
- 排除词
- PubMed 检索式
- 其他医学数据库检索策略建议
- 年份、语言、研究类型建议
- 检索风险和可能遗漏

同时生成 `{{ stage }} stage_report.md`，用中文说明本阶段做了什么、哪些地方需要用户确认。

## PubMed 检索式要求

优先组合 MeSH Terms、Title/Abstract 和自由词：

```text
("Disease"[Mesh] OR disease[Title/Abstract] OR synonym[Title/Abstract])
AND
("Intervention"[Mesh] OR intervention[Title/Abstract])
AND
("Outcome"[Mesh] OR outcome[Title/Abstract])
```

不要过早加入过多限制。医学综述初筛阶段宁可略宽，后续由筛选评分处理。

## 用户审查点

完成后询问用户：
- 提醒用户可以先用检索词自行检索进行测试，了解符合条件文献的数量。
- 是否接受当前检索式？
- 是否需要扩大或收窄主题？
- 是否调整年份、语言或研究类型？
- 是否进入 `literature-search` 执行 PubMed demo 检索？
