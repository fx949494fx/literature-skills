# Zotero 字段映射

## 推荐字段

| Zotero/导入字段 | 来源字段 |
|---|---|
| itemType | 默认为 `journalArticle` |
| title | `title` |
| creators | `authors` |
| publicationTitle | `journal` |
| date | `year` |
| DOI | `doi` |
| PMID | `pmid` |
| url | `url` |
| abstractNote | `abstract` |
| tags | 由评分状态、主题、指标和证据类型生成 |
| notes | 记录评分、纳排理由、assigned_sections |

## BibTeX 导入

手工导入 Zotero 时优先使用 `zotero_import.bib`。

BibTeX 字段建议：

| BibTeX 字段 | 来源字段 |
|---|---|
| title | `title` |
| author | `authors`，用 `and` 连接 |
| journal | `journal` |
| year | `year` |
| doi | `doi` |
| pmid | `pmid` |
| url | `url` |
| abstract | `abstract` |
| keywords | workflow tags |
| note | 评分、纳排状态、reason、assigned_sections |

## 保存原则

- 不要把 `exclude` 文献默认保存到 Zotero，除非用户要求保留排除记录。
- `maybe` 文献建议使用 `status/maybe` 标签，与 `include` 分开。
- 所有记录保留 `PMID` 或 `DOI`，用于去重和追溯。
