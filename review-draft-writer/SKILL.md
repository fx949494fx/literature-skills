---
name: review-draft-writer
description: 医学综述初稿写作 Skill。用于根据 review_framework.md、evidence_allocation_matrix.csv、paper_evidence_packets.jsonl 和精读笔记分章节生成中文综述初稿、引用占位、待核验清单和阶段性报告；适用于用户确认综述框架后进入可审查写作阶段。
---

# 医学综述初稿写作

## 使用前

先读取 `../shared/workflow_contract.md`。本 Skill 只能在用户确认综述框架后运行。不要一次性把草稿视为终稿；每次输出后必须暂停等待用户审查。

运行前必须确认两个写作参数：

- 纳入初稿写作的文献数量，例如 30、50、100 篇，或全部已确认 include 文献。
- 综述正文目标字数，且该字数不含参考文献。

如果证据来自摘要或 evidence packets，必须在草稿中保留引用占位和“需全文核验”提示。不要编造定量结果、统计值或指南结论。

如果已经完成 `paper-deep-reading`，后续写作必须优先使用 `deep_reading_evidence_packets.jsonl`，因为其中包含每篇文献对本次综述的具体贡献和可转化为正文的观点。

## 输入

接受：

- `review_framework.md`
- `evidence_allocation_matrix.csv`
- `paper_evidence_packets.jsonl`
- 可选 `deep_reading_evidence_packets.jsonl`，完成精读后优先使用
- `reading_notes/`
- 用户指定语言、目标期刊、篇幅、章节或写作风格

## 输出

初稿阶段生成：

- `review_draft.md`
- `citation_placeholders.csv`
- `fact_check_todo.md`
- `draft-stage_report.md`

用户确认草稿后，正文写作阶段生成：

- `review_body.md`
- `body_notes.md`
- `body-stage_report.md`
- 更新后的 `citation_placeholders.csv`
- 更新后的 `fact_check_todo.md`

`review_body.md` 必须只包含投稿正文表述。不得出现“综述写作时应...”“在正式写作中...”“正文中应...”“需要核验...”等写作提示、批注、操作建议或元说明。此类内容必须写入 `body_notes.md`、`fact_check_todo.md` 或阶段报告。

脚本必须保持主题无关。不得把测试主题的疾病、指标、人群、章节标题或结论硬编码进 Python 脚本。正文主题应来自 `--topic`、已确认框架和 evidence packets。

## 写作原则

- 优先按章节逐步写，不默认一次完成终稿。
- 每个基于文献的观点后必须立即附 citation placeholder，如 `[PMID:xxxx]`；不要在整段末尾一次性罗列本段参考文献。
- 优先使用 evidence packet 中的 `review_contribution`、`contribution_points` 和 `usable_claims` 生成正文观点。
- 摘要级证据只写为“提示”“显示相关性”“可能具有价值”，避免过度因果化。
- 对系统综述方向，保留 PRISMA、纳排、偏倚风险和证据等级待补区域。
- 对范围综述方向，强调主题图谱、指标类型、应用场景和研究空白。

## 草稿结构

```markdown
# Title

## 摘要
## 引言
## 方法概述或检索与筛选说明
## 章节 1
## 章节 2
## 章节 3
## 临床应用价值
## 局限性
## 未来方向
## 结论
## 待全文核验清单
```

## Demo 脚本

```bash
python scripts/write_review_draft.py --framework review_framework.md --matrix evidence_allocation_matrix.csv --packets paper_evidence_packets.jsonl --output-dir outputs --language zh
```

如果已经完成精读，推荐传入强化后的 evidence packets：

```bash
python scripts/write_review_draft.py --framework review_framework.md --matrix evidence_allocation_matrix.csv --packets deep_reading_evidence_packets.jsonl --output-dir outputs --language zh
```

正式写作时应传入：

```bash
python scripts/write_review_draft.py --framework review_framework.md --matrix evidence_allocation_matrix.csv --packets paper_evidence_packets.jsonl --output-dir outputs --language zh --target-paper-count 50 --target-word-count 8000
```

用户确认草稿结构后，进入正文写作：

```bash
python scripts/write_review_draft.py --mode body --framework review_framework.md --matrix evidence_allocation_matrix.csv --packets paper_evidence_packets.jsonl --confirmed-draft review_draft.md --output-dir outputs --language zh --target-paper-count 50 --target-word-count 8000
```

## 阶段暂停

完成后询问用户：

- 是否接受章节草稿结构？
- 是否选择某一章进行精修？
- 是否补充全文后重写关键段落？
- 是否进入 Obsidian 或 Word/Markdown 整理阶段？

若用户已经确认草稿并要求写正文，应输出正文版综述，并再次暂停等待用户审查正文。
