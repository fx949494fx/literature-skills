---
name: paper-screening-score
description: 按用户可配置标准筛选和评分医学文献。用于读取 papers.jsonl 或 papers.csv，根据综述类型、纳入排除标准、医学证据等级、主题相关性、方法质量、时效性和用户权重输出筛选评分结果、简短 reason 和中文阶段性报告。
---

# 医学文献筛选评分

## 使用前

先读取 `../shared/workflow_contract.md`。本 Skill 只处理已完成检索的文献数据，不负责重新检索。

完成筛选评分后必须暂停，等待用户审查纳入、排除和待定文献。

筛选评分完成后，还必须让用户决定精读范围：用户可以在 `screening_scores.csv` 中增加或填写 `deep_reading_select` 标记列，也可以要求 AI 根据评分、主题覆盖和文献类型自选前 N 篇。未得到用户确认前，不得自动进入精读。

## 输入

接受：

- `papers.jsonl` 或 `papers.csv`
- 用户研究方向
- 综述类型
- 纳入标准
- 排除标准
- 评分权重

如果用户没有指定综述类型或评分标准，先给出医学默认配置并等待确认。

## Demo 脚本

第一版可使用规则评分脚本：

```bash
python scripts/screen_papers.py --input papers.jsonl --output-dir outputs --config scoring-config.json
```

如果没有配置文件，脚本使用系统综述/范围综述混合取向的默认权重。该脚本用于快速分流和测试，不替代正式系统综述中的双人独立筛选。

## 默认综述类型

支持：

- `systematic_review`：系统综述，强调可重复检索、明确纳排和证据等级。
- `scoping_review`：范围综述，强调广覆盖、主题聚类和研究空白。
- `narrative_review`：叙述综述，强调关键观点、代表性证据和逻辑框架。
- `mechanism_review`：机制综述，强调病理生理链条、实验模型和机制证据。
- `clinical_review`：临床综述，强调诊断、治疗、预后和指南相关性。
- `frontier_review`：前沿综述，强调近年进展、新技术和未解决问题。

## 医学默认评分

如果用户未配置，建议：

```json
{
  "topic_relevance": 0.35,
  "method_quality": 0.20,
  "evidence_level": 0.20,
  "recency": 0.15,
  "novelty_or_clinical_value": 0.10
}
```

系统综述可提高 `method_quality` 和 `evidence_level`；范围综述可提高 `topic_relevance` 和主题覆盖；机制综述可提高机制证据和实验设计质量。

## 输出字段

输出 `screening_scores.jsonl` 和 `screening_scores.csv`：

```json
{
  "paper_id": "",
  "title": "",
  "total_score": 0.0,
  "topic_relevance_score": 0,
  "method_quality_score": 0,
  "evidence_level_score": 0,
  "recency_score": 0,
  "novelty_or_clinical_value_score": 0,
  "include_decision": "include",
  "reason": "",
  "assigned_sections": []
}
```

`include_decision` 只能使用 `include`、`maybe`、`exclude`。

`reason` 必须只用 1-2 句话，与主题相关的利用价值；适合为综述写作提供指引，不要写成长段解释。

## 精读选择交接

阶段报告中应提示用户确认：

- 本轮需要精读多少篇文献。
- 使用人工标记还是 AI 自选。
- 如果人工标记，在 `screening_scores.csv` 中添加 `deep_reading_select` 列，并用 `yes`、`true`、`1`、`selected` 或 `精读` 标记。
- 如果 AI 自选，应说明选择逻辑，例如优先 include、高分、不同章节/研究设计覆盖均衡。



## 阶段报告

生成中文 `{{ stage }} stage_report.md`，包含：

- 当前综述类型
- 评分标准和权重
- 输入文献数量
- include / maybe / exclude 数量
- 高分文献列表
- 常见排除原因
- 不确定性
- 需要用户审查的决定

完成后询问用户是否调整评分标准、人工修改个别文献判断，或进入 Zotero/精读/Obsidian 后续阶段。
