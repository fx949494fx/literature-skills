---
name: obsidian-literature-notes
description: 将 literature-skills 的检索、筛选、Zotero 计划、evidence packets 和精读结果转换为 Obsidian vault 可用的文献笔记、frontmatter、wikilink、MOC 交接清单和增量纳入计划；用于把医学综述流水线输出交给 fx949494fx/obsidian-skills 继续维护。
---

# Obsidian 文献笔记交接

本 Skill 负责把 `literature-skills` 的结构化综述输出转换为 Obsidian 可消费的知识库输入。它不替代 `paper-metadata-extractor`、`paper-deep-reading` 或 `zotero-manager`，而是把这些技能的结果整理为 Obsidian 笔记、属性和后续综合任务。

## 使用前

先读取：

- `../shared/workflow_contract.md`
- `../shared/obsidian_contract.md`

本 Skill 只能处理用户已经审查过的筛选结果、Zotero 导入计划或 evidence packets。不得默认把全部检索结果写入 `01 Papers`。

## 输入

接受以下文件：

- `papers.jsonl` 或 `papers.csv`
- `screening_scores.jsonl` 或 `screening_scores.csv`
- `zotero_items.jsonl`
- `paper_evidence_packets.jsonl`
- `deep_reading_evidence_packets.jsonl`
- `evidence_claims.csv`
- `review_framework.md`
- `evidence_allocation_matrix.csv`
- 用户指定的 Obsidian vault 目录和主题名

如果已经完成 `paper-deep-reading`，优先使用 `deep_reading_evidence_packets.jsonl`。如果只有摘要级 evidence packets，笔记必须保留 `needs_full_text_check: true`。

## 输出

生成 Obsidian vault 相对路径下的文件建议或实际文件：

```text
00 Inbox/*.md
01 Papers/*.md
03 Synthesis/<主题> MOC.md
03 Synthesis/<主题> 证据矩阵.md
03 Synthesis/<主题> 论文讨论可用论点.md
03 Synthesis/<主题> 新增文献纳入计划.md
Bases/<主题> literature.base
Canvas/<主题> 知识地图.canvas
obsidian-export-stage_report.md
```

如果用户只要求“生成交接包”，也可以先输出到普通 `outputs/obsidian_export/`，再由用户或 `obsidian-cli` 写入 vault。

## 分流规则

- `Include` 且已有精读或全文依据：写入 `01 Papers/`，`status: read`。
- `Include` 但只有摘要级证据：写入 `00 Inbox/`，`status: to-read`，`needs_full_text_check: true`。
- `Maybe`：写入 `00 Inbox/`，等待用户审查。
- `Need Full Text`：写入 `00 Inbox/`，突出全文获取任务。
- `Exclude`：写入 `Other/` 或只保留在 CSV，不默认创建长笔记。

## 笔记原则

- 文献笔记只承载单篇文献事实、精读、贡献和可用观点，不承担综合综述。
- `concepts`、`review_sections` 和关键词应转为 Obsidian wikilink，但不要过度创建概念页。
- 摘要级内容必须写明 `evidence_basis: abstract_or_metadata`。
- 全文未核验的观点必须保留 `needs_full_text_check: true`。
- Zotero 和 PDF 信息只在存在时写入；不得虚构 `zotero_item_key`、`zotero_attachment_key` 或 PDF 路径。

## 文献笔记结构

使用 `../shared/obsidian_contract.md` 中的模板。标题建议：

```text
<year> - <first-author or PMID> - <short-title>.md
```

当标题过长或含有非法路径字符时，应保留 `paper_id` 或 PMID 作为稳定后缀。

## 与 obsidian-skills 的交接

生成文献笔记后，下一步交给 `fx949494fx/obsidian-skills`：

- 用 `obsidian-markdown` 校验 frontmatter、wikilink、callout 和 PDF embed。
- 用 `obsidian-literature-synthesis` 从 `01 Papers` 提炼 MOC、概念页、证据矩阵和论文论点。
- 用 `obsidian-bases` 创建文献库视图。
- 用 `json-canvas` 创建主题知识地图。
- 用 `obsidian-cli` 或用户指定方式写入、移动、搜索和增量更新 vault 文件。

## 增量纳入

当用户已有 Obsidian 文献库时，不重建全部文件。处理新增文献时：

1. 对比 `paper_id`、PMID、DOI 和文件名，识别新增、已存在和疑似重复文献。
2. 只为新增文献创建或更新单篇笔记。
3. 为 `obsidian-literature-synthesis` 输出新增文献清单和建议更新的概念页。
4. 更新证据矩阵和论文论点页时保留人工已写内容，只追加可追溯的新证据。
5. 阶段报告中列出断链、缺失 PDF、缺失 Zotero key 和仍需全文核验的文献。

## 阶段报告

完成后生成 `obsidian-export-stage_report.md`，至少包含：

- 当前主题和目标 vault
- 使用的输入文件
- 创建或建议创建的笔记数量
- `00 Inbox`、`01 Papers`、`Other` 分流数量
- 缺失 Zotero/PDF/全文核验信息
- 建议交给 `obsidian-literature-synthesis` 的下一步
- 需要用户审查的决定
