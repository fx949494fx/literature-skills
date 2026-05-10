#!/usr/bin/env python
"""Write reusable medical review drafts and body text from framework outputs."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_matrix(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def cite(row: dict) -> str:
    paper_id = row.get("paper_id", "")
    if paper_id.startswith("PMID:"):
        return f"[PMID:{paper_id.replace('PMID:', '')}]"
    return f"[{paper_id}]" if paper_id else ""


def representative_rows(rows: list[dict], limit: int = 8) -> list[dict]:
    def score(row: dict) -> float:
        try:
            return float(row.get("screening_score") or 0)
        except ValueError:
            return 0.0

    return sorted(rows, key=score, reverse=True)[:limit]


def clean_title(topic: str) -> str:
    return topic.strip().strip("《》") or "医学综述"


def parse_framework_title(framework: str, fallback: str) -> str:
    match = re.search(r"## 题目候选\s+1\.\s+(.+)", framework)
    return match.group(1).strip() if match else clean_title(fallback)


def build_common_inputs(args: argparse.Namespace) -> tuple[str, list[dict], list[dict], dict[str, list[dict]], set[str], dict[str, dict]]:
    framework = Path(args.framework).read_text(encoding="utf-8")
    rows = load_matrix(Path(args.matrix))
    packets = load_jsonl(Path(args.packets))
    packet_by_id = {packet.get("paper_id", ""): packet for packet in packets}
    selected = []
    for packet in sorted(packets, key=lambda p: float(p.get("screening_score", 0) or 0), reverse=True):
        paper_id = packet.get("paper_id", "")
        if paper_id and paper_id not in selected:
            selected.append(paper_id)
        if len(selected) >= args.target_paper_count:
            break
    selected_set = set(selected)
    if selected_set:
        rows = [row for row in rows if row.get("paper_id") in selected_set]
    by_section: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_section[row.get("section_id", "evidence")].append(row)
    return framework, packets, rows, by_section, selected_set, packet_by_id


def claim_sentences(row: dict, packet: dict) -> list[str]:
    citation = packet.get("citation_placeholder") or cite(row)
    claims = packet.get("usable_claims") or []
    sentences = []
    for item in claims[:2]:
        claim = str(item.get("claim", "")).strip()
        item_citation = item.get("citation") or citation
        if claim:
            sentences.append(f"{claim.rstrip('。.;；')}。{item_citation}")
    if sentences:
        return sentences
    title = row.get("title", "该研究")
    design = row.get("study_design", "unclear")
    concepts = row.get("key_concepts", "") or "相关核心概念"
    outcomes = row.get("outcomes", "") or "主要结局或评价对象"
    return [f"{title}提供了关于{concepts}与{outcomes}的{design}证据线索。{citation}"]


def section_sentence(section_title: str, rows: list[dict], topic: str, packet_by_id: dict[str, dict]) -> str:
    reps = representative_rows(rows, limit=8)
    concepts = sorted({item for row in reps for item in (row.get("key_concepts", "") or "").split("; ") if item})
    outcomes = sorted({item for row in reps for item in (row.get("outcomes", "") or "").split("; ") if item})
    metrics = sorted({item for row in reps for item in (row.get("evaluation_metrics", "") or "").split("; ") if item})
    concept_text = "、".join(concepts[:6]) if concepts else "相关核心概念"
    outcome_text = "、".join(outcomes[:6]) if outcomes else "主要结局或评价对象"
    metric_text = "、".join(metrics[:6]) if metrics else "研究报告的评价指标"

    opening = (
        f"{section_title}是理解“{topic}”证据结构的重要组成部分。现有研究主要围绕{concept_text}展开，"
        f"并以{outcome_text}作为观察对象，同时报告{metric_text}等证据线索。"
    )
    evidence_lines = []
    for row in reps:
        packet = packet_by_id.get(row.get("paper_id", ""), {})
        evidence_lines.extend(claim_sentences(row, packet))
    interpretation = (
        "综合这些研究时，需要同时考虑研究对象、核心变量定义、结局测量和研究设计差异，"
        "并在全文核验后判断不同研究结果的一致性、应用价值和方法学限制。"
    )
    return "\n\n".join([opening, "\n".join(evidence_lines), interpretation])


def write_supporting_files(output_dir: Path, rows: list[dict], packets: list[dict], args: argparse.Namespace, selected_count: int) -> None:
    with (output_dir / "citation_placeholders.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["section_id", "section_title", "paper_id", "citation_placeholder", "title", "needs_full_text_check"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "section_id": row.get("section_id", ""),
                    "section_title": row.get("section_title", ""),
                    "paper_id": row.get("paper_id", ""),
                    "citation_placeholder": cite(row),
                    "title": row.get("title", ""),
                    "needs_full_text_check": "yes",
                }
            )

    (output_dir / "fact_check_todo.md").write_text(
        f"""# 待全文核验清单

## 必查项目

- 每篇文献的纳排标准和研究对象。
- 核心变量、暴露、干预、指标或分类方式的定义。
- 主要结局、评价指标、测量时间点和随访时间。
- 统计模型、混杂调整、缺失值处理和敏感性分析。
- 效应量、预测性能、校准、外部验证或证据等级。
- 偏倚风险和适用场景。

## 当前证据来源

- evidence packets：{len(packets)} 篇。
- 目标纳入文献：{args.target_paper_count} 篇。
- 实际可用文献：{selected_count} 篇。
- 目标正文字数：{args.target_word_count} 字，不含参考文献。
- 框架文件：`{Path(args.framework).name}`。
- 证据分配矩阵：`{Path(args.matrix).name}`。
""",
        encoding="utf-8",
    )


def write_body_notes(output_dir: Path, args: argparse.Namespace, packets: list[dict], selected_count: int) -> None:
    (output_dir / "body_notes.md").write_text(
        f"""# 正文写作说明和核验提示

## 说明

`review_body.md` 已移除写作提示、操作建议和元说明，仅保留正文表述与引用占位。

## 写作参数

- 目标纳入文献：{args.target_paper_count}
- 实际可用文献：{selected_count}
- 目标正文字数：{args.target_word_count}，不含参考文献
- evidence packets：{len(packets)}

## 仍需核验

- 当前正文基于 evidence packets 生成。
- 所有效应量、模型性能、外部验证、偏倚风险和证据等级需要全文核验。
- 引用占位应在正式写作时替换为期刊要求的引用格式。
""",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Write a reusable medical review draft or body text.")
    parser.add_argument("--mode", choices=["draft", "body"], default="draft")
    parser.add_argument("--framework", required=True)
    parser.add_argument("--matrix", required=True)
    parser.add_argument("--packets", required=True)
    parser.add_argument("--confirmed-draft", default="")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--topic", default="", help="Review topic. If omitted, inferred from framework title.")
    parser.add_argument("--language", default="zh")
    parser.add_argument("--target-paper-count", type=int, default=50)
    parser.add_argument("--target-word-count", type=int, default=8000)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    framework, packets, rows, by_section, selected_set, packet_by_id = build_common_inputs(args)
    topic = clean_title(args.topic) if args.topic else parse_framework_title(framework, "医学综述")
    section_titles = {
        row.get("section_id", "evidence"): row.get("section_title", row.get("section_id", "evidence"))
        for row in rows
    }

    if args.mode == "body":
        if not args.confirmed_draft:
            parser.error("--confirmed-draft is required in body mode.")
        Path(args.confirmed_draft).read_text(encoding="utf-8")
        body_parts = [f"# {topic}", ""]
        ordered_section_ids = [sid for sid in ["background", "concepts", "populations", "outcomes", "evidence", "methods", "translation"] if sid in by_section]
        ordered_section_ids += [sid for sid in by_section if sid not in ordered_section_ids]
        for section_id in ordered_section_ids:
            title = section_titles.get(section_id, section_id)
            body_parts.extend(["", f"## {title}", "", section_sentence(title, by_section[section_id], topic, packet_by_id)])
        body_parts.extend(
            [
                "",
                "## 小结",
                "",
                f"围绕“{topic}”的现有证据显示，该主题已经形成一定研究基础，但不同研究在人群、核心变量定义、结局测量和方法学质量上仍可能存在差异。"
                "后续定稿需要在全文核验基础上进一步确认关键结论、证据强度和实际应用价值。",
            ]
        )
        (output_dir / "review_body.md").write_text("\n".join(body_parts).strip() + "\n", encoding="utf-8")
        write_supporting_files(output_dir, rows, packets, args, len(selected_set))
        write_body_notes(output_dir, args, packets, len(selected_set))
        (output_dir / "body-stage_report.md").write_text(
            f"""# 综述正文 阶段性工作报告

## 当前阶段
用户确认草稿后的正文写作。

## 已完成的操作
- 读取已确认草稿、综述框架、证据分配矩阵和 evidence packets。
- 按目标文献数量和目标正文词数生成正文版综述。
- 将写作说明和核验提示放入独立文件，正文仅保留正文表述。

## 主要输出文件
- `review_body.md`
- `body_notes.md`
- `citation_placeholders.csv`
- `fact_check_todo.md`

## 主要发现
- 目标纳入文献：{args.target_paper_count}
- 实际可用文献：{len(selected_set)}
- 目标正文字数：{args.target_word_count}

## 不确定性和潜在偏倚
- 正文仍基于 evidence packets，不应替代全文核验后的投稿稿。
- 具体效应量、模型性能和证据等级需要从全文补齐。

## 需要用户审查的决定
- 是否接受正文整体结构？
- 是否选择某一节继续精修？
- 是否补充全文后进行定稿级改写？
""",
            encoding="utf-8",
        )
        return

    draft_parts = [
        f"# {topic}",
        "",
        "## 写作状态说明",
        "",
        "本稿为基于综述框架、evidence packets 和精读贡献信息生成的初步草稿。所有定量结果、方法细节、偏倚风险和可引用结论均需全文核验。",
        "",
        f"写作参数：目标纳入文献 {args.target_paper_count} 篇；目标正文 {args.target_word_count} 字，不含参考文献。当前可用 evidence packets {len(packets)} 篇，实际进入草稿证据分配 {len(selected_set)} 篇。",
        "",
        "## 摘要",
        "",
        f"本综述围绕“{topic}”展开，旨在系统整理现有证据、主要研究对象、关键结局、评价指标和应用价值，并识别仍需进一步研究或全文核验的证据缺口。",
    ]
    for section_id, section_rows in by_section.items():
        title = section_titles.get(section_id, section_id)
        draft_parts.extend(["", f"## {title}", "", section_sentence(title, section_rows, topic, packet_by_id), "", "代表性证据："])
        for row in representative_rows(section_rows, limit=8):
            draft_parts.append(f"- {row.get('title', '')} {cite(row)}")
    draft_parts.extend(["", "## 结论", "", f"当前证据为“{topic}”提供了初步综述基础，但仍需通过全文核验、偏倚风险评价和证据等级评估形成投稿级结论。"])

    (output_dir / "review_draft.md").write_text("\n".join(draft_parts) + "\n", encoding="utf-8")
    write_supporting_files(output_dir, rows, packets, args, len(selected_set))
    (output_dir / "draft-stage_report.md").write_text(
        f"""# 综述初稿 阶段性工作报告

## 当前阶段
综述初稿写作。

## 已完成的操作
- 读取综述框架、证据分配矩阵和 evidence packets。
- 按目标文献数量和目标正文词数设置写作约束。
- 按章节生成中文初步草稿。

## 主要输出文件
- `review_draft.md`
- `citation_placeholders.csv`
- `fact_check_todo.md`

## 需要用户审查的决定
- 是否接受草稿章节结构？
- 是否进入正文写作模式？
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
