---
name: paper-metadata-extractor
description: 医学文献元数据和证据包抽取 Skill。用于从 papers.jsonl、screening_scores.jsonl、PubMed 摘要或后续全文信息中提取研究问题、对象、人群、指标、结局、方法、主要结果线索、局限性线索和综述用途，生成可追溯 evidence packets、证据矩阵和阶段性报告。
---

# 文献元数据和证据包抽取

## 使用前

先读取 `../shared/workflow_contract.md`。本 Skill 不做深度解读全文，只抽取可追溯的结构化信息，为 Zotero、精读和 Obsidian 笔记做准备。

不要凭空补全文献中没有的信息。无法从题名、摘要、关键词或元数据判断的字段，写 `unclear`。

## 输入

接受：

- `papers.jsonl`
- `screening_scores.jsonl`
- 用户指定的导出范围，例如 `include`、`include + maybe` 或 top N
- 可选全文文本或 PDF 抽取结果
- 后续精读选择信息可来自 `screening_scores.csv` 的人工标记，或由 `paper-deep-reading` 按用户确认的数量自选

## 输出

生成：

- `paper_evidence_packets.jsonl`
- `paper_evidence_matrix.csv`
- `metadata-extraction-stage_report.md`

## Evidence Packet 字段

```json
{
  "paper_id": "",
  "title": "",
  "citation": "",
  "year": "",
  "doi": "",
  "pmid": "",
  "study_design": "",
  "population": "",
  "high_risk_context": "",
  "key_concepts": [],
  "outcomes": [],
  "evaluation_metrics": [],
  "main_finding_signal": "",
  "limitations_signal": "",
  "review_use": "",
  "review_contribution": "",
  "contribution_points": [],
  "usable_claims": [
    {
      "claim": "",
      "citation": "[PMID:xxxx]",
      "evidence_basis": "abstract_or_metadata",
      "needs_full_text_check": true
    }
  ],
  "screening_decision": "",
  "screening_score": 0,
  "source_trace": {
    "abstract_available": true,
    "source": "PubMed"
  }
}
```

## 抽取原则

- 研究设计：优先识别 systematic review、meta-analysis、prospective cohort、cohort、cross-sectional、case-control、prediction model、machine learning。
- 人群：从摘要中抽取研究对象、疾病背景、风险状态或应用场景。
- 核心概念：根据用户配置抽取暴露、干预、指标、机制、方法或分类方式。
- 结局：根据用户配置抽取主要结局、替代结局或评价对象。
- 评价指标：抽取效应量、预测性能、诊断性能或其他用户指定评价指标。
- 综述贡献：每篇文献必须生成 `review_contribution` 和 `contribution_points`，说明该文献对本次综述写作能贡献什么信息。
- 可用观点：`usable_claims` 中的每条观点都必须带 `citation` 占位符，并标明依据是摘要/元数据还是全文；摘要级观点必须保留 `needs_full_text_check=true`。

## Demo 脚本

```bash
python scripts/extract_metadata.py --papers papers.jsonl --scores screening_scores.jsonl --output-dir outputs --include-decisions include maybe --top-n 100
```

## 阶段暂停

完成后暂停，询问用户：

- 是否接受 evidence packet 字段？
- 是否需要人工补充全文信息？
- 是否进入 `paper-deep-reading` 精读高优先级文献？
