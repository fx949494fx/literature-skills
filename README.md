# 医学文献综述 Skills 工具集

这是一套面向中文医学研究者的 Codex Skills 工具集，用于按阶段完成医学文献综述前期工作：明确研究方向、建议数据库、生成 PubMed 检索式、执行 PubMed demo 检索、自动筛选评分，并输出可审查的阶段性报告。

## 当前版本范围

当前包含 9 个 Skills 和 1 个共享工作契约：

```text
literature-orchestrator/
literature-query-builder/
literature-search/
paper-screening-score/
zotero-manager/
paper-metadata-extractor/
paper-deep-reading/
review-framework-builder/
review-draft-writer/
shared/workflow_contract.md
```

当前 demo 版本主要支持 PubMed/MEDLINE 检索。Embase、Cochrane Library、Web of Science/Scopus、ClinicalTrials.gov/WHO ICTRP 等数据库只作为后续扩展建议，不在本版中实际检索。

## 设计原则

- 中文优先：阶段报告、审查问题和关键说明尽量使用中文。
- 医学优先：数据库建议、评分标准和检索策略偏向医学、临床、公卫和循证医学场景。
- 阶段审查：每个阶段完成后必须暂停，等待用户决定重新运行、微调或进入下一步。
- 可追溯：检索式、输入文件、输出文件、评分结果和 `paper_id` 均保留。
- 可配置：综述类型、评分权重、纳排标准和 `max-results` 可由用户调整。

## 工作流

```text
用户给定医学研究方向
        ↓
literature-orchestrator
        ↓
数据库建议与确认
        ↓
literature-query-builder
        ↓
PubMed 检索式生成与审查
        ↓
literature-search
        ↓
papers.jsonl / papers.csv
        ↓
paper-screening-score
        ↓
screening_scores.jsonl / screening_scores.csv
        ↓
用户审查并确认精读数量与选择方式
        ↓
zotero-manager / paper-metadata-extractor / paper-deep-reading
        ↓
Zotero 导入计划 / evidence packets / 强化 evidence packets / 中文精读笔记
        ↓
review-framework-builder
        ↓
综述框架 / 证据分配表 / 图表计划
        ↓
review-draft-writer
        ↓
综述初稿 / 引用占位 / 全文核验清单
```

## Skills 说明

### `literature-orchestrator`

总控 Skill。负责理解用户研究方向、组织阶段流程、在用户未指定数据库时给出医学数据库建议，并确保每个阶段结束后等待用户审查。

适用场景：

- 用户给出一个医学综述方向，希望启动完整文献管理流程。
- 用户尚未确定数据库、综述类型或检索范围。
- 需要按阶段推进，而不是一次性自动跑完整流程。

### `literature-query-builder`

检索式生成 Skill。负责将中文医学研究方向转化为 PubMed 检索策略，包括关键词、MeSH 词、同义词、布尔检索式和检索风险。

主要输出：

```text
query_plan.md
query-builder-stage_report.md
```

### `literature-search`

PubMed 检索 Skill。Demo 版本调用 NCBI E-utilities 执行 PubMed 检索，并同时输出 JSONL 和 CSV。

主要脚本：

```text
literature-search/scripts/search_pubmed.py
```

推荐使用 `--query-file` 运行长检索式：

```bash
python literature-search/scripts/search_pubmed.py \
  --query-file pubmed_query.txt \
  --output-dir outputs \
  --max-results 500
```

如果测试环境网络不稳定、NCBI 关闭连接，或出现类似 `RemoteDisconnected`、`IncompleteRead`、`network error` 的问题，使用更小批次和更多重试：

```bash
python literature-search/scripts/search_pubmed.py \
  --query-file pubmed_query.txt \
  --output-dir outputs \
  --max-results 500 \
  --batch-size 50 \
  --retries 8 \
  --timeout 90
```

脚本会分批抓取 PubMed 记录，并对临时网络错误、HTTP 429/5xx、连接重置和远端关闭进行重试。

主要输出：

```text
papers.jsonl
papers.csv
search_log.md
stage_report.md
```

### `paper-screening-score`

自动筛选评分 Skill。读取 `papers.jsonl` 或 `papers.csv`，根据用户配置的综述类型、评分权重和纳排标准，为每篇文献输出评分、纳入判断和简短 reason。

主要脚本：

```text
paper-screening-score/scripts/screen_papers.py
```

示例运行：

```bash
python paper-screening-score/scripts/screen_papers.py \
  --input papers.jsonl \
  --output-dir outputs \
  --config screening-config.json
```

主要输出：

```text
screening_scores.jsonl
screening_scores.csv
screening-config.json
screening-stage_report.md
```

`reason` 字段必须保持 1-2 句话，便于人工快速审查。

筛选评分完成后需要先让用户决定精读数量和选择方式。用户可以在 `screening_scores.csv` 中增加 `deep_reading_select` 列进行人工标记，也可以让 AI 根据评分、纳入判断、主题覆盖、研究设计和章节覆盖自选前 N 篇。

### `zotero-manager`

Zotero 管理 Skill。读取筛选结果和文献元数据，按用户确认的保存范围生成 Zotero 可导入 BibTeX、CSV、结构化 JSONL、标签方案和阶段报告。手工导入 Zotero 时优先使用 `zotero_import.bib`。

主要脚本：

```text
zotero-manager/scripts/prepare_zotero_import.py
```

示例运行：

```bash
python zotero-manager/scripts/prepare_zotero_import.py \
  --papers papers.jsonl \
  --scores screening_scores.jsonl \
  --output-dir outputs \
  --include-decisions include maybe \
  --collection "My review collection"
```

本版默认生成导入计划，不直接写入 Zotero。只有用户提供 Zotero API 配置并明确授权后，才可扩展为真实写入。

### `paper-metadata-extractor`

文献元数据和 evidence packet 抽取 Skill。读取 `papers.jsonl` 和 `screening_scores.jsonl`，抽取研究设计、人群、核心概念、结局、评价指标和综述用途。

主要脚本：

```text
paper-metadata-extractor/scripts/extract_metadata.py
```

示例运行：

```bash
python paper-metadata-extractor/scripts/extract_metadata.py \
  --papers papers.jsonl \
  --scores screening_scores.jsonl \
  --output-dir outputs \
  --include-decisions include maybe \
  --top-n 100
```

主要输出：

```text
paper_evidence_packets.jsonl
paper_evidence_matrix.csv
metadata-extraction-stage_report.md
```

每篇 evidence packet 都包含 `review_contribution`、`contribution_points` 和 `usable_claims`，用于说明该文献对本次综述写作能贡献什么信息。摘要级观点会保留全文核验标记。

### `paper-deep-reading`

医学文献精读 Skill。基于 evidence packets、摘要或全文材料生成中文精读笔记和批次摘要。

主要脚本：

```text
paper-deep-reading/scripts/build_reading_notes.py
```

示例运行：

```bash
python paper-deep-reading/scripts/build_reading_notes.py \
  --packets paper_evidence_packets.jsonl \
  --output-dir outputs \
  --top-n 20
```

如果没有全文，笔记会标明“基于摘要和 evidence packet 的初步精读”，并列出需全文核验点。

主要输出：

```text
reading_notes/
deep_reading_evidence_packets.jsonl
evidence_claims.csv
deep_reading_summary.md
deep-reading-stage_report.md
```

读取用户在 `screening_scores.csv` 中的人工标记：

```bash
python paper-deep-reading/scripts/build_reading_notes.py \
  --packets paper_evidence_packets.jsonl \
  --output-dir outputs \
  --top-n 20 \
  --selection-csv screening_scores.csv \
  --selection-column deep_reading_select
```

完成精读后，后续框架和写作建议优先使用 `deep_reading_evidence_packets.jsonl`。

### `review-framework-builder`

综述框架构建 Skill。根据 evidence packets、筛选评分和精读笔记生成中心问题、中心论点、章节结构、证据分配矩阵、图表计划和阶段报告。

主要脚本：

```text
review-framework-builder/scripts/build_review_framework.py
```

示例运行：

```bash
python review-framework-builder/scripts/build_review_framework.py \
  --packets paper_evidence_packets.jsonl \
  --output-dir outputs \
  --review-type "systematic_review + scoping_review" \
  --topic "用户确认的医学综述主题"
```

主要输出：

```text
review_framework.md
evidence_allocation_matrix.csv
figure_table_plan.md
framework-stage_report.md
```

框架阶段结束后必须先确认两个写作参数，再进入初稿：

- 希望纳入初稿写作的文献数量，例如 30、50、100 篇，或全部 include 文献。
- 综述正文目标字数，不含参考文献，例如 5000、8000 或 10000 字。

### `review-draft-writer`

综述初稿写作 Skill。只能在用户确认框架后使用。根据综述框架、证据分配矩阵和 evidence packets 生成中文初稿、引用占位和全文核验清单。

主要脚本：

```text
review-draft-writer/scripts/write_review_draft.py
```

示例运行：

```bash
python review-draft-writer/scripts/write_review_draft.py \
  --framework review_framework.md \
  --matrix evidence_allocation_matrix.csv \
  --packets paper_evidence_packets.jsonl \
  --output-dir outputs \
  --language zh \
  --target-paper-count 50 \
  --target-word-count 8000
```

主要输出：

```text
review_draft.md
citation_placeholders.csv
fact_check_todo.md
draft-stage_report.md
```

当前初稿写作会保留 `[PMID:xxxx]` 引用占位，并提醒全文核验，避免把摘要级证据包装为投稿级结论。

写作时必须做到“观点后引用”：每个基于文献的观点后立即添加对应引用占位符，不在段落末尾集中列出本段所有参考文献。如果已经完成精读，推荐将 `--packets` 指向 `deep_reading_evidence_packets.jsonl`。

用户确认草稿后，可进入正文写作模式：

```bash
python review-draft-writer/scripts/write_review_draft.py \
  --mode body \
  --framework review_framework.md \
  --matrix evidence_allocation_matrix.csv \
  --packets paper_evidence_packets.jsonl \
  --confirmed-draft review_draft.md \
  --output-dir outputs \
  --language zh \
  --target-paper-count 50 \
  --target-word-count 8000
```

正文阶段输出：

```text
review_body.md
body_notes.md
body-stage_report.md
citation_placeholders.csv
fact_check_todo.md
```

`review_body.md` 只保留正文表述；写作提示、核验说明和操作建议放入 `body_notes.md` 或 `fact_check_todo.md`。

第三阶段脚本必须保持主题无关：不要把测试主题的疾病、指标、人群、章节或结论写死在 Python 代码中。综述主题应由 `--topic`、`--title`、框架文件和 evidence packets 提供。

## 共享工作契约

共享契约位于：

```text
shared/workflow_contract.md
```

它规定：

- 每个阶段必须输出阶段性工作报告。
- 每个阶段完成后不得自动进入下一阶段。
- 检索前必须确认数据库和 `max-results`。
- `literature-search` 必须同时输出 `papers.jsonl` 和 `papers.csv`。
- 评分标准和综述类型必须允许用户配置。
- `paper-screening-score` 的 `reason` 必须为 1-2 句话。
- 筛选后必须由用户确认精读数量和选择方式。
- 精读后必须输出包含文献贡献信息的强化 evidence packets。
- 综述写作必须在每个基于文献的观点后立即添加引用占位符。

## 注意事项

当前评分脚本是规则模型，适合 demo、预筛和工作流测试，不替代正式系统综述中的双人独立筛选。

如果用于正式系统综述，建议下一步补充：

- 更严格的纳排标准。
- 成人/人类研究限制。
- 具体目标人群、疾病阶段、风险状态或应用场景定义。
- 更全面的主题相关核心概念、指标、暴露、干预、机制或评价对象。
- Zotero 保存、Obsidian 精读笔记和证据矩阵生成 Skills。

## 后续扩展方向

建议下一阶段新增：

```text
obsidian-literature-notes/
```

这些扩展应继续遵守 `shared/workflow_contract.md` 的阶段审查原则。
