# Literature Skills 与 Obsidian Skills 交接契约

## 目标

本契约定义 `literature-skills` 的结构化综述输出如何进入 `fx949494fx/obsidian-skills` 的长期知识库流程。

`literature-skills` 负责检索、筛选、Zotero 导入计划、evidence packet、精读强化、综述框架和初稿。`obsidian-skills` 负责把这些结果沉淀到 Obsidian vault 中，形成 `00 Inbox`、`01 Papers`、`02 Concepts`、`03 Synthesis`、`Canvas` 和 `Bases`。

## 不重复造轮子的边界

- 不用 `obsidian-skills` 替代 `paper-metadata-extractor`。后者生成 `paper_evidence_packets.jsonl`，是综述框架和正文写作的数据层。
- 不用 `obsidian-skills` 替代 `paper-deep-reading` 的强化 evidence packet。Obsidian 笔记只是呈现层，`deep_reading_evidence_packets.jsonl` 仍是后续写作的优先输入。
- 不用 `obsidian-skills` 替代 `zotero-manager` 的导入计划。`zotero-manager` 继续生成 BibTeX、CSV、JSONL、collection 和标签方案；真实写入 Zotero 应交给 Zotero 插件或用户授权后的 Zotero API。
- `obsidian-skills` 可以接管 Obsidian Markdown、wikilink、MOC、概念页、证据矩阵、Canvas 和 Bases 的生成与维护。

## 推荐文件流

```text
papers.jsonl
  + screening_scores.jsonl
  -> zotero_items.jsonl / zotero_import.bib
  -> paper_evidence_packets.jsonl
  -> deep_reading_evidence_packets.jsonl
  -> review_framework.md / evidence_allocation_matrix.csv
  -> review_draft.md or review_body.md
  -> Obsidian vault
```

进入 Obsidian vault 后：

```text
00 Inbox/              初筛后待处理文献
01 Papers/             已精读并纳入的文献
02 Concepts/           可复用概念页
03 Synthesis/          MOC、证据矩阵、论文论点、流程页
Attachments/PDFs/      PDF 附件
Bases/                 文献库视图
Canvas/                知识地图
Other/                 非 Include 文献
```

## 字段映射

| literature-skills 字段 | Obsidian 属性 | 说明 |
|---|---|---|
| `paper_id` | `paper_id` | 全流程追踪主键，优先保留 `PMID:xxxx` |
| `pmid` | `pmid` | PubMed ID |
| `doi` | `doi` | DOI |
| `title` | `title` | 文献题名 |
| `journal` | `journal` | 期刊 |
| `year` | `year` | 发表年份 |
| `include_decision` / `screening_decision` | `decision` | 映射为 `Include`、`Maybe`、`Exclude`、`Need Full Text` |
| `total_score` / `screening_score` | `screening_score` | 0-100 初筛或规则评分 |
| `assigned_sections` | `review_sections` | 拟进入的综述章节 |
| `key_concepts` | `concepts` | 建议转为 wikilink 的概念 |
| `review_contribution` | `review_contribution` | 一句话综述贡献 |
| `contribution_points` | `contribution_points` | 支撑综述章节的信息点 |
| `usable_claims` | `usable_claims` | 可转写为正文观点的证据句 |
| `citation_placeholder` | `citation_placeholder` | 如 `[PMID:xxxx]` |
| `needs_full_text_check` | `needs_full_text_check` | 是否仍需全文核验 |
| `deep_reading_basis` | `evidence_basis` | `abstract_or_metadata` 或 `full_text` |
| `zotero_item_key` | `zotero_item_key` | Zotero 条目 key |
| `zotero_attachment_key` | `zotero_attachment_key` | Zotero 附件 key |
| `pdf_path` | `pdf` | Obsidian PDF embed 路径 |

## decision 映射规则

| `paper-screening-score` | Obsidian `decision` | 初始 `status` |
|---|---|---|
| `include` | `Include` | `to-read` |
| `maybe` | `Maybe` | `to-read` |
| `exclude` | `Exclude` | `archived` |
| 缺少摘要但疑似重要 | `Need Full Text` | `to-read` |

完成全文或结构化精读后，将 `status` 改为 `read`；进入 MOC、概念页、证据矩阵和论文论点页后，将 `status` 改为 `synthesized`。

## Obsidian 文献笔记模板

```markdown
---
title: "{{title}}"
paper_id: "{{paper_id}}"
pmid: "{{pmid}}"
doi: "{{doi}}"
journal: "{{journal}}"
year: "{{year}}"
decision: "{{decision}}"
status: "{{status}}"
screening_score: {{screening_score}}
evidence_basis: "{{evidence_basis}}"
needs_full_text_check: {{needs_full_text_check}}
zotero_item_key: "{{zotero_item_key}}"
zotero_attachment_key: "{{zotero_attachment_key}}"
pdf: "{{pdf_path}}"
concepts:
  - "{{concept}}"
review_sections:
  - "{{section}}"
tags:
  - literature
  - literature/review
---

# {{title}}

> [!summary] 一句话综述贡献
> {{review_contribution}}

## 基本信息

- PMID: {{pmid}}
- DOI: {{doi}}
- Journal: {{journal}}
- Year: {{year}}
- Citation: {{citation_placeholder}}

## 关键词与概念

{{concept_wikilinks}}

## 筛选结论

- Decision: {{decision}}
- Score: {{screening_score}}
- Reason: {{screening_reason}}

## 全文精读（YYYY-MM-DD）

![[{{pdf_path}}]]

- Zotero item key: `{{zotero_item_key}}`
- Zotero attachment key: `{{zotero_attachment_key}}`
- Evidence basis: `{{evidence_basis}}`

### 一句话结论

{{review_contribution}}

### 对本次综述写作的具体贡献

{{contribution_points}}

### 可直接转化为正文观点的证据句

{{usable_claims}}

### 局限性和需全文核验点

{{full_text_checks}}
```

## 阶段审查

生成 Obsidian 输出后仍必须暂停，让用户审查：

- 是否接受文献分流到 `00 Inbox`、`01 Papers`、`Other`。
- 是否接受字段映射和 frontmatter。
- 是否将 `Include` 文献继续纳入 MOC、概念页、证据矩阵和 Canvas。
- 是否只做增量更新，还是重建某个主题的综合页面。
