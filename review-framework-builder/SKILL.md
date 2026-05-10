---
name: review-framework-builder
description: 医学综述框架构建 Skill。用于根据 paper_evidence_packets.jsonl、筛选评分、精读笔记和用户指定综述类型，提出可审查的综述中心论点、章节结构、证据分配表、研究空白、图表建议和阶段性报告；适用于从文献管理成果进入综述设计阶段。
---

# 医学综述框架构建

## 使用前

先读取 `../shared/workflow_contract.md`。本 Skill 只负责提出和修订综述框架，不直接写完整综述正文。完成后必须暂停等待用户审查框架。

如果只有摘要级 evidence packets，应在报告中说明框架是“基于摘要和元数据的初步框架”，正式写作前需要全文核验关键文献。

如果已经完成 `paper-deep-reading`，应优先使用 `deep_reading_evidence_packets.jsonl`，因为该文件包含每篇文献对本次综述写作的具体贡献。

## 输入

接受：

- `paper_evidence_packets.jsonl`
- 可选 `deep_reading_evidence_packets.jsonl`，完成精读后优先使用
- `screening_scores.jsonl`
- `deep_reading_summary.md`
- `reading_notes/`
- 用户指定综述类型：`systematic_review`、`scoping_review`、`clinical_review`、`narrative_review` 等
- 用户指定目标期刊、读者、篇幅或中文/英文写作要求

## 输出

生成：

- `review_framework.md`
- `evidence_allocation_matrix.csv`
- `figure_table_plan.md`
- `framework-stage_report.md`

## 框架内容

`review_framework.md` 至少包含：

- 综述题目候选
- 综述类型
- 中心问题
- 中心论点
- 目标读者
- 章节结构
- 每章核心论点
- 支撑证据
- 相反或不确定证据
- 证据缺口
- 需要全文核验的关键点

## 证据分配原则

- 优先把文献分配到能支撑具体论点的章节，而不是只按指标名称堆放。
- 对 `systematic_review`，强调纳排流程、证据表、偏倚风险和定量合成可能性。
- 对 `scoping_review`，强调主题图谱、指标谱系、应用场景、研究空白和未来方向。
- 对医学临床主题，必须单独考虑人群定义、指标测量、结局定义、预测性能和临床可实施性。

## Demo 脚本

```bash
python scripts/build_review_framework.py --packets paper_evidence_packets.jsonl --output-dir outputs --review-type "systematic_review + scoping_review" --topic "用户确认的医学综述主题"
```

脚本必须保持主题无关。不得把某个测试主题的题目、章节、指标、疾病或结论硬编码进 Python 脚本。所有主题信息必须来自 `--topic`、`--title` 和 evidence packets。

## 阶段暂停

完成后询问用户：

- 是否接受中心问题和中心论点？
- 是否调整综述类型或章节顺序？
- 是否需要合并、拆分或删除某些章节？
- 希望纳入多少篇文献进入初稿写作？例如 30、50、100 篇，或全部 include 文献。
- 综述目标字数是多少？仅计算正文，不含参考文献。
- 是否进入 `review-draft-writer` 分章节写作？
