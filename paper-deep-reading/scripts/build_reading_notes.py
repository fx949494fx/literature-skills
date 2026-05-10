#!/usr/bin/env python
"""Build preliminary Chinese deep-reading notes from reusable evidence packets."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def slug(text: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]+", "-", text).strip("-")
    return cleaned[:80] or fallback


def list_text(values: list[str]) -> str:
    return "、".join(values) if values else "unclear"


def packet_list(packet: dict, key: str) -> list[str]:
    value = packet.get(key)
    return value if isinstance(value, list) else []


def citation_placeholder(packet: dict) -> str:
    if packet.get("citation_placeholder"):
        return packet["citation_placeholder"]
    if packet.get("pmid"):
        return f"[PMID:{packet['pmid']}]"
    if packet.get("doi"):
        return f"[DOI:{packet['doi']}]"
    return f"[{packet.get('paper_id', '')}]" if packet.get("paper_id") else ""


def contribution_points(packet: dict) -> list[str]:
    existing = packet.get("contribution_points")
    if isinstance(existing, list) and existing:
        return [str(item) for item in existing if str(item).strip()]
    concepts = list_text(packet_list(packet, "key_concepts"))
    outcomes = list_text(packet_list(packet, "outcomes"))
    metrics = list_text(packet_list(packet, "evaluation_metrics"))
    finding = packet.get("main_finding_signal", "unclear")
    review_use = packet.get("review_use", "unclear")
    points = []
    if concepts != "unclear" or outcomes != "unclear":
        points.append(f"该文献可用于说明{concepts}与{outcomes}之间的证据关系。")
    if metrics != "unclear":
        points.append(f"该文献可为综述中的方法学或评价指标讨论提供{metrics}相关信息。")
    if review_use != "unclear":
        points.append(review_use.rstrip("。") + "。")
    if finding != "unclear":
        points.append(f"该文献报告的主要发现线索为：{finding}")
    return points or ["该文献可作为本次综述的候选证据，具体贡献需结合全文和人工审查确认。"]


def enrich_packet(packet: dict, evidence_basis: str) -> dict:
    enriched = dict(packet)
    citation = citation_placeholder(packet)
    points = contribution_points(packet)
    enriched["citation_placeholder"] = citation
    enriched["deep_reading_status"] = "completed"
    enriched["deep_reading_basis"] = evidence_basis
    enriched["review_contribution"] = points[0] if points else "unclear"
    enriched["contribution_points"] = points
    enriched["usable_claims"] = [
        {
            "claim": point,
            "citation": citation,
            "evidence_basis": evidence_basis,
            "needs_full_text_check": evidence_basis != "full_text",
        }
        for point in points
    ]
    return enriched


def truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "yes", "y", "true", "include", "selected", "精读", "是"}


def selected_ids_from_csv(path: str, column: str) -> set[str]:
    if not path:
        return set()
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        selected = set()
        for row in reader:
            marker = row.get(column, "")
            if truthy(marker):
                paper_id = row.get("paper_id") or row.get("pmid") or row.get("PMID")
                if paper_id:
                    selected.add(paper_id if str(paper_id).startswith("PMID:") else f"PMID:{paper_id}" if str(paper_id).isdigit() else str(paper_id))
        return selected


def select_packets(packets: list[dict], args: argparse.Namespace) -> list[dict]:
    selected_ids = selected_ids_from_csv(args.selection_csv, args.selection_column)
    if selected_ids:
        picked = [packet for packet in packets if packet.get("paper_id") in selected_ids or f"PMID:{packet.get('pmid', '')}" in selected_ids]
        return picked[: args.top_n]
    return packets[: args.top_n]


def note_for(packet: dict) -> str:
    title = packet.get("title", "Untitled")
    concepts = list_text(packet_list(packet, "key_concepts"))
    outcomes = list_text(packet_list(packet, "outcomes"))
    metrics = list_text(packet_list(packet, "evaluation_metrics"))
    contribution = packet.get("review_contribution") or f"该文献为“{concepts}”与“{outcomes}”之间的证据关系提供了线索。"
    claims = "\n".join(f"- {claim.get('claim', '')} {claim.get('citation', '')}" for claim in packet.get("usable_claims", []) if claim.get("claim"))
    return f"""# {title}

## 基本信息

- PMID: {packet.get("pmid", "")}
- DOI: {packet.get("doi", "")}
- 年份: {packet.get("year", "")}
- 引文: {packet.get("citation", "")}
- 引用占位: {packet.get("citation_placeholder", "")}
- 筛选判断: {packet.get("screening_decision", "")}
- 筛选分数: {packet.get("screening_score", "")}
- 精读层级: {packet.get("deep_reading_basis", "abstract_or_metadata")}

## 一句话贡献

{contribution}

## 研究问题

该研究与用户定义综述主题相关。具体研究问题需结合全文核验。

## 人群和应用背景

- 人群线索: {packet.get("population", "unclear")}
- 背景线索: {packet.get("population_context", packet.get("high_risk_context", "unclear"))}

## 核心概念、暴露或干预

{concepts}

## 结局或评价对象

{outcomes}

## 方法和评价指标

- 研究设计: {packet.get("study_design", "unclear")}
- 评价指标: {metrics}

## 主要发现

{packet.get("main_finding_signal", "unclear")}

## 综述应用价值

{packet.get("review_use", "unclear")}

## 对本次综述写作的具体贡献

{contribution}

## 可直接转化为正文观点的证据句

{claims or "- unclear"}

## 局限性和需全文核验点

- 摘要中局限性线索: {packet.get("limitations_signal", "unclear")}
- 需要全文核验：人群纳排标准、核心变量定义、结局定义、混杂调整、模型验证、偏倚风险。

## 可用于综述的写法

可作为用户定义综述主题下的证据候选。正式写入综述前应核验全文数据和偏倚风险。

## 标签

- literature
- status/{packet.get("screening_decision", "unknown")}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Build preliminary reading notes from evidence packets.")
    parser.add_argument("--packets", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--selection-csv", default="", help="Optional user-marked screening_scores.csv.")
    parser.add_argument("--selection-column", default="deep_reading_select", help="Column used for user-marked deep-reading selection.")
    parser.add_argument("--evidence-basis", choices=["abstract_or_metadata", "full_text"], default="abstract_or_metadata")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    notes_dir = output_dir / "reading_notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    packets = select_packets(load_jsonl(Path(args.packets)), args)
    created = []
    enriched_packets = []
    for idx, packet in enumerate(packets, start=1):
        packet = enrich_packet(packet, args.evidence_basis)
        enriched_packets.append(packet)
        filename = f"{idx:03d}-{packet.get('year', 'unknown')}-{slug(packet.get('title', ''), packet.get('paper_id', str(idx)))}.md"
        path = notes_dir / filename
        path.write_text(note_for(packet), encoding="utf-8")
        created.append((path.name, packet))

    with (output_dir / "deep_reading_evidence_packets.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for packet in enriched_packets:
            handle.write(json.dumps(packet, ensure_ascii=False) + "\n")

    with (output_dir / "evidence_claims.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["paper_id", "citation", "claim", "evidence_basis", "needs_full_text_check", "title"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for packet in enriched_packets:
            for claim in packet.get("usable_claims", []):
                writer.writerow(
                    {
                        "paper_id": packet.get("paper_id", ""),
                        "citation": claim.get("citation", ""),
                        "claim": claim.get("claim", ""),
                        "evidence_basis": claim.get("evidence_basis", ""),
                        "needs_full_text_check": claim.get("needs_full_text_check", ""),
                        "title": packet.get("title", ""),
                    }
                )

    summary_lines = "\n".join(f"- {packet.get('screening_score', '')}: {packet.get('title', '')} ({packet.get('paper_id', '')})" for _, packet in created)
    (output_dir / "deep_reading_summary.md").write_text(
        f"""# 精读批次摘要

## 精读范围
基于 evidence packet 生成前 {len(created)} 篇文献的初步中文精读笔记。

## 文献列表
{summary_lines}

## 使用限制
本批笔记主要基于摘要和结构化 evidence packet。用于正式综述前，应补充全文并核验方法、结果和偏倚风险。
""",
        encoding="utf-8",
    )
    (output_dir / "deep-reading-stage_report.md").write_text(
        f"""# 文献精读 阶段性工作报告

## 当前阶段
核心文献初步精读。

## 已完成的操作
- 读取 evidence packets。
- 生成每篇文献的中文精读笔记。
- 汇总本批高优先级文献。

## 主要输出文件
- `reading_notes/`
- `deep_reading_evidence_packets.jsonl`
- `evidence_claims.csv`
- `deep_reading_summary.md`

## 主要发现
- 生成精读笔记数：{len(created)}
- 精读选择方式：{"用户在 CSV 中标记" if args.selection_csv else "AI 按当前排序自选前 N 篇"}
- 精读依据：{args.evidence_basis}
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
