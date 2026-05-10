#!/usr/bin/env python
"""Prepare Zotero import files from PubMed papers and screening scores."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def evidence_tags(publication_types: list[str], text: str) -> list[str]:
    joined = " ".join(publication_types).lower() + " " + text.lower()
    tags = []
    if "meta-analysis" in joined:
        tags.append("evidence/meta-analysis")
    if "systematic review" in joined:
        tags.append("evidence/systematic-review")
    if "cohort" in joined or "prospective" in joined:
        tags.append("evidence/cohort")
    if "cross-sectional" in joined:
        tags.append("evidence/cross-sectional")
    return tags


def normalize_tag(value: str, prefix: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]+", "-", value.strip()).strip("-").lower()
    return f"{prefix}/{cleaned}" if cleaned else ""


def list_from_score(score: dict, key: str) -> list[str]:
    value = score.get(key, [])
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(";") if item.strip()]
    return []


def bib_escape(value: object) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\\", "\\textbackslash{}")
    text = text.replace("{", "\\{").replace("}", "\\}")
    return text.replace("\n", " ").replace("\r", " ").strip()


def first_author_key(authors: list[str]) -> str:
    if not authors:
        return "Unknown"
    first = authors[0].strip()
    family = first.split()[0] if first else "Unknown"
    return re.sub(r"[^A-Za-z0-9]+", "", family) or "Unknown"


def citekey(item: dict) -> str:
    year = re.sub(r"[^0-9]+", "", str(item.get("date", "")))[:4] or "n.d."
    identifier = item.get("PMID") or item.get("DOI") or item["workflow"].get("paper_id", "")
    suffix = re.sub(r"[^A-Za-z0-9]+", "", str(identifier))[-6:]
    return f"{first_author_key(item.get('creators', []))}{year}{suffix}"


def bibtex_entry(item: dict) -> str:
    fields = {
        "title": item.get("title", ""),
        "author": " and ".join(item.get("creators", [])),
        "journal": item.get("publicationTitle", ""),
        "year": item.get("date", ""),
        "doi": item.get("DOI", ""),
        "pmid": item.get("PMID", ""),
        "url": item.get("url", ""),
        "abstract": item.get("abstractNote", ""),
        "keywords": ", ".join(item.get("tags", [])),
        "note": json.dumps(item.get("workflow", {}), ensure_ascii=False),
    }
    lines = [f"@article{{{citekey(item)},"]
    for key, value in fields.items():
        if value:
            lines.append(f"  {key} = {{{bib_escape(value)}}},")
    lines.append("}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare Zotero import plan from literature workflow outputs.")
    parser.add_argument("--papers", required=True, help="Input papers.jsonl.")
    parser.add_argument("--scores", required=True, help="Input screening_scores.jsonl.")
    parser.add_argument("--output-dir", required=True, help="Output directory.")
    parser.add_argument("--collection", default="Medical literature review", help="Target Zotero collection name.")
    parser.add_argument("--include-decisions", nargs="+", default=["include"], help="Decisions to export.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    papers = {paper.get("paper_id"): paper for paper in load_jsonl(Path(args.papers))}
    scores = load_jsonl(Path(args.scores))
    selected = [score for score in scores if score.get("include_decision") in set(args.include_decisions)]

    items = []
    for score in selected:
        paper = papers.get(score.get("paper_id"), {})
        text = f"{paper.get('title', '')} {paper.get('abstract', '')}"
        tags = [
            "source/pubmed",
            f"status/{score.get('include_decision', 'unknown')}",
        ]
        tags.extend(normalize_tag(section, "topic") for section in list_from_score(score, "assigned_sections"))
        tags.extend(normalize_tag(term, "term") for term in list_from_score(score, "matched_terms")[:12])
        tags.extend(evidence_tags(paper.get("publication_types", []), text))
        tags = sorted(tag for tag in set(tags) if tag)
        items.append(
            {
                "itemType": "journalArticle",
                "title": paper.get("title", score.get("title", "")),
                "creators": paper.get("authors", []),
                "publicationTitle": paper.get("journal", ""),
                "date": paper.get("year", ""),
                "DOI": paper.get("doi", ""),
                "PMID": paper.get("pmid", ""),
                "url": paper.get("url", ""),
                "abstractNote": paper.get("abstract", ""),
                "collection": args.collection,
                "tags": tags,
                "workflow": {
                    "paper_id": score.get("paper_id", ""),
                    "total_score": score.get("total_score", ""),
                    "include_decision": score.get("include_decision", ""),
                    "reason": score.get("reason", ""),
                    "assigned_sections": score.get("assigned_sections", []),
                },
            }
        )

    with (output_dir / "zotero_items.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for item in items:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    fields = ["itemType", "title", "creators", "publicationTitle", "date", "DOI", "PMID", "url", "abstractNote", "collection", "tags", "notes"]
    with (output_dir / "zotero_import.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in items:
            writer.writerow(
                {
                    "itemType": item["itemType"],
                    "title": item["title"],
                    "creators": "; ".join(item["creators"]),
                    "publicationTitle": item["publicationTitle"],
                    "date": item["date"],
                    "DOI": item["DOI"],
                    "PMID": item["PMID"],
                    "url": item["url"],
                    "abstractNote": item["abstractNote"],
                    "collection": item["collection"],
                    "tags": "; ".join(item["tags"]),
                    "notes": json.dumps(item["workflow"], ensure_ascii=False),
                }
            )

    (output_dir / "zotero_import.bib").write_text(
        "\n\n".join(bibtex_entry(item) for item in items) + ("\n" if items else ""),
        encoding="utf-8",
    )

    tag_counts: dict[str, int] = {}
    for item in items:
        for tag in item["tags"]:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    tag_lines = "\n".join(f"- {tag}: {count}" for tag, count in sorted(tag_counts.items()))
    (output_dir / "zotero_tag_plan.md").write_text(
        f"""# Zotero 标签和 Collection 方案

## Collection
{args.collection}

## 导出范围
{", ".join(args.include_decisions)}

## 标签统计
{tag_lines}
""",
        encoding="utf-8",
    )
    (output_dir / "zotero-stage_report.md").write_text(
        f"""# Zotero 管理 阶段性工作报告

## 当前阶段
Zotero 导入计划生成。

## 已完成的操作
- 读取文献元数据和筛选评分。
- 按用户确认的纳入状态导出 Zotero 计划。
- 生成 Zotero CSV、结构化 JSONL 和标签方案。

## 主要输出文件
- `zotero_import.csv`
- `zotero_import.bib`
- `zotero_items.jsonl`
- `zotero_tag_plan.md`

## 主要发现
- 选择导出文献数：{len(items)}
- 目标 collection：{args.collection}

## 需要用户审查的决定
- 是否接受 collection 名称？
- 是否调整标签体系？
- 是否提供 Zotero API 配置执行真实写入？
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
