# 医学文献综述 Skills 共享工作契约

## 适用范围

本契约适用于第一版医学文献综述工具集：

- `literature-orchestrator`
- `literature-query-builder`
- `literature-search`
- `paper-screening-score`
- `zotero-manager`
- `paper-metadata-extractor`
- `paper-deep-reading`
- `review-framework-builder`
- `review-draft-writer`

## 语言和用户背景

默认用户是中文用户和医学研究者。所有阶段性报告、审查问题和关键说明优先使用中文。必要的数据库字段、脚本参数和 JSON 键名可使用英文。

## 人机协作原则

每个 Skill 只能完成当前阶段，不得自动连续运行后续阶段。阶段结束后必须等待用户审查。

阶段结束时，向用户提供三个选择：

- 重新运行当前步骤
- 微调当前结果
- 进入下一步

只有用户明确同意后，才能进入下一阶段。

## 阶段性工作报告

每个阶段必须生成当前阶段的 `{{ stage }} stage_report.md`。建议结构：

```markdown
# {{ stage }} 阶段性工作报告

## 当前阶段
## 用户研究方向
## 使用的输入
## 已完成的操作
## 主要输出文件
## 主要发现
## 不确定性和潜在偏倚
## 需要用户审查的决定
## 建议下一步
```

报告必须简洁、可审查、可追溯。

## 数据库选择

如果用户没有主动提供数据库信息，必须先给出医学数据库建议并询问用户纳入哪些数据库。

医学优先数据库包括 PubMed/MEDLINE、Embase、Cochrane Library、ClinicalTrials.gov、WHO ICTRP、Web of Science、Scopus、CINAHL、PsycINFO。

Demo 版本只实际执行 PubMed 检索；其他数据库可作为建议列出，不得虚构检索结果。

## 文献检索输出

在检索开始前应询问用户对检索结果数量max-results的设置，默认值为 200。

`literature-search` 必须同时输出：

- `papers.jsonl`
- `papers.csv`

两个文件应包含相同文献集合。JSONL 用于自动处理，CSV 用于人工审查。

## 筛选评分

评分标准和综述类型必须允许用户配置。

`paper-screening-score` 的 `reason` 字段必须为 1-2 句话，只说明最主要判断依据。

所有筛选结果必须保留 `paper_id`，确保可追溯。

筛选评分完成后必须暂停，让用户确认精读数量和选择方式。用户可以：

- 在 `screening_scores.csv` 中人工标记 `deep_reading_select` 列。
- 要求 AI 按评分、纳入判断、主题覆盖、研究设计和章节覆盖自选指定数量的文献。

未确认精读数量前，不得自动进入 `paper-deep-reading`，也不得默认精读全部检索结果。

## 第二阶段：Zotero、元数据和精读

第二阶段必须建立在用户已审查的筛选结果上，不得自动处理全部检索结果。

`zotero-manager` 默认只生成 Zotero 导入计划和标签方案。除非用户提供 Zotero API 配置并明确授权，否则不得宣称已写入 Zotero。

`paper-metadata-extractor` 只能抽取可追溯信息。无法从题名、摘要、关键词或全文中确认的字段，应写 `unclear`。

`paper-deep-reading` 必须标明精读依据。如果只使用摘要或 evidence packet，应写明“基于摘要的初步精读”，并提示全文核验点。

无论精读依据是摘要还是全文，精读完成后都必须输出强化后的 `deep_reading_evidence_packets.jsonl`。每篇文献必须包括：

- `review_contribution`：该文献对本次综述写作的一句话贡献。
- `contribution_points`：可支持综述章节的具体信息点。
- `usable_claims`：可转化为正文观点的证据句，每条必须带引用占位符和全文核验状态。

后续综述框架和写作应优先使用完成精读后的 evidence packets。如果尚未精读，只能使用摘要级 evidence packets，并在写作输出中保留全文核验提示。

## 第三阶段：综述框架和初稿写作

第三阶段必须建立在用户已审查的 evidence packets、精读笔记或 Zotero 管理结果上。

`review-framework-builder` 只负责生成和修订综述框架，不直接写完整正文。框架必须包含中心问题、中心论点、章节结构、证据分配、研究空白和需全文核验点。

`review-framework-builder` 完成后，必须询问用户希望纳入初稿写作的文献数量，以及综述正文目标字数。目标字数不含参考文献。

`review-draft-writer` 只能在用户确认综述框架、目标文献数量和目标正文字数后运行。所有基于摘要级证据的段落必须保留引用占位和全文核验提示，不得编造定量结果、统计值或指南结论。

综述写作时，每个基于文献的观点后必须立即添加对应引用占位符，例如 `[PMID:xxxx]`。不得在整段结束后一次性列出本段所有参考文献。

当用户确认 `review_draft.md` 的结构后，`review-draft-writer` 可以进入正文写作模式，输出 `review_body.md`。正文仍必须保留引用占位和全文核验清单，除非用户已经提供全文证据和核验结果。

`review_body.md` 只能包含投稿正文表述。写作建议、核验提醒、流程说明和批注必须放入单独文件，例如 `body_notes.md`、`fact_check_todo.md` 或阶段报告。

所有第三阶段脚本必须保持主题无关。不得将测试主题、疾病、指标、人群或具体结论硬编码进脚本；这些内容必须来自用户输入、框架文件和 evidence packets。
