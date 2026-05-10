---
name: paper-deep-reading
description: 医学文献精读 Skill。用于根据用户确认的核心文献、paper_evidence_packets.jsonl、PubMed 摘要或全文材料，生成中文精读笔记、批判性评价、综述写作用途、可引用观点和阶段性报告；适用于进入 Zotero 管理和元数据抽取之后，对高分 include 文献进行人工可审查精读。
---

# 医学文献精读

## 使用前

先读取 `../shared/workflow_contract.md`。本 Skill 只精读用户确认的核心文献，不应自动精读全部检索结果。

如果只有摘要，没有全文，必须在笔记中标明“基于摘要的初步精读”，并把方法细节、偏倚风险和局限性标为需全文核验。

进入本 Skill 前，必须先让用户确认精读数量和选择方式。选择方式包括：

- 用户在 `screening_scores.csv` 中标记 `deep_reading_select` 列。
- AI 根据筛选分数、纳入判断、主题覆盖、研究设计和章节覆盖自选前 N 篇。

未确认精读数量前，不得默认读取全部文献。

## 输入

接受：

- `paper_evidence_packets.jsonl`
- 可选 `screening_scores.csv`，用于读取用户人工标记的精读文献
- 指定 PMID、DOI 或前 N 篇高分文献
- PubMed 摘要
- 可选 PDF 全文文本
- 用户指定精读问题，例如“关注预测性能”“关注临床应用价值”“关注高危人群定义”

## 输出

生成：

- `reading_notes/`：每篇文献一个 Markdown 精读笔记
- `deep_reading_evidence_packets.jsonl`：精读后强化的 evidence packets，后续写作应优先使用
- `evidence_claims.csv`：每条可用于正文的观点、引用占位和全文核验状态
- `deep_reading_summary.md`：本批文献综合精读摘要
- `deep-reading-stage_report.md`：阶段性工作报告

## 精读笔记结构

```markdown
# 文献题名

## 基本信息
## 一句话贡献
## 对本次综述写作的具体贡献
## 可直接转化为正文观点的证据句
## 研究问题
## 人群和高危背景
## 暴露/指标
## 结局
## 方法和预测性能
## 主要发现
## 临床或综述应用价值
## 局限性和需全文核验点
## 可用于综述的写法
## 标签
```
`一句话贡献` 的内容，尽量包含来自摘要的具体结果和结论，避免笼统的描述，例如“有关”、“相关”等。比较好的选择比如“发现了 A 指标与 B 指标之间的正向关联关系”等类似具体的描述。

## 精读原则

- 区分“文献明确报告的信息”和“基于摘要的推断”。
- 每篇文献必须明确写出对本次综述的具体贡献，避免只写“与主题相关”。
- 每条可转化为正文观点的证据句必须附带引用占位符，例如 `[PMID:xxxx]`。
- 精读完成后必须输出强化后的 `deep_reading_evidence_packets.jsonl`，并保留 `review_contribution`、`contribution_points` 和 `usable_claims` 字段。
- 对医学研究，优先关注人群定义、研究设计、指标测量、结局定义、预测性能、校准/判别、混杂调整和外部验证。
- 对系统综述方向，记录是否适合进入证据表和是否需要全文评估偏倚风险。
- 对范围综述方向，记录该文献适合放入哪个主题簇。

## Demo 脚本

```bash
python scripts/build_reading_notes.py --packets paper_evidence_packets.jsonl --output-dir outputs --top-n 20
```

读取用户在 `screening_scores.csv` 中的精读标记：

```bash
python scripts/build_reading_notes.py --packets paper_evidence_packets.jsonl --output-dir outputs --top-n 20 --selection-csv screening_scores.csv --selection-column deep_reading_select
```

如果使用全文精读结果：

```bash
python scripts/build_reading_notes.py --packets paper_evidence_packets.jsonl --output-dir outputs --top-n 20 --evidence-basis full_text
```

脚本生成基于摘要和 evidence packet 的初步精读笔记。正式精读应在获得全文后补充。

## 阶段暂停

完成后暂停，询问用户：

- 是否接受这批精读文献？
- 是否需要补充全文重新精读？
- 是否进入 Obsidian 笔记保存或综述框架生成？
