---
name: zotero-manager
description: 医学文献综述工作流中的 Zotero 管理 Skill。用于将用户审查后的 PubMed 检索结果、筛选评分结果或元数据包整理为 Zotero 可导入 CSV、标签方案、collection 计划和保存报告；适用于需要把已纳入或待定文献保存到 Zotero，并保留评分、纳排状态、综述章节和可追溯字段的阶段。
---

# Zotero 文献管理

## 使用前

先读取 `../shared/workflow_contract.md`。本 Skill 只处理用户已确认进入 Zotero 管理阶段的文献，不应擅自保存全部检索结果。

本版优先输出 Zotero 可导入文件和保存计划。手工导入 Zotero 时优先使用 BibTeX 文件。若用户提供 Zotero Web API key、library id 和 library type，可按用户授权进行 API 写入；没有 API 配置时，不要假装已写入 Zotero。

## 输入

接受：

- `screening_scores.jsonl` 或 `screening_scores.csv`
- `papers.jsonl` 或 `papers.csv`
- 用户确认的保存范围，例如 `include`、`include + maybe` 或指定 PMID 列表
- Zotero collection 名称
- 标签规则或用户自定义标签

## 输出

生成：

- `zotero_import.csv`：适合人工导入或后续转换的文献表
- `zotero_import.bib`：Zotero 手工导入优先使用的 BibTeX 文件
- `zotero_items.jsonl`：保留结构化字段的 Zotero item 计划
- `zotero_tag_plan.md`：标签和 collection 方案
- `zotero-stage_report.md`：阶段性工作报告

## 标签规则

推荐标签：

- `review/<review_type>`
- `status/include`
- `status/maybe`
- `status/exclude`
- `source/pubmed`
- `topic/<assigned_section>`
- `term/<matched_term>`
- `evidence/systematic-review`
- `evidence/meta-analysis`
- `evidence/cohort`
- `evidence/cross-sectional`

保留 Zotero 原始标签；新增标签应服务于检索、分组和综述写作，不要制造过细且无法复用的标签。

## Demo 脚本

```bash
python scripts/prepare_zotero_import.py --papers papers.jsonl --scores screening_scores.jsonl --output-dir outputs --include-decisions include maybe --collection "My review collection"
```

脚本会同时生成 BibTeX、CSV 和 JSONL。手工导入 Zotero 时使用 `zotero_import.bib`；CSV 和 JSONL 主要用于审查和追溯。脚本不直接写入 Zotero。

## 阶段暂停

完成后暂停，询问用户：

- 是否只保存 `include` 文献？
- 是否也保存 `maybe` 文献？
- 是否修改 collection 名称或标签体系？
- 是否提供 Zotero API 配置进行真实写入？
