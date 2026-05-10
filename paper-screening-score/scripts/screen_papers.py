#!/usr/bin/env python
"""Config-driven screening and scoring for literature records."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
from collections import Counter
from pathlib import Path


DEFAULT_WEIGHTS = {
    "topic_relevance": 0.40,
    "method_quality": 0.20,
    "evidence_level": 0.20,
    "recency": 0.10,
    "novelty_or_clinical_value": 0.10,
}

DEFAULT_METHOD_TERMS = [
    "prospective",
    "cohort",
    "longitudinal",
    "validation",
    "external validation",
    "machine learning",
    "logistic regression",
    "hazard ratio",
    "odds ratio",
    "receiver operating",
    "meta-analysis",
    "systematic review",
]


def load_config(path: str) -> dict:
    if not path:
        return {
            "review_type": "scoping_review",
            "research_topic": "未提供研究方向",
            "scoring_criteria": DEFAULT_WEIGHTS,
            "term_groups": [],
            "exclude_terms": [],
        }
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_papers(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def contains_any(text: str, terms: list[str]) -> list[str]:
    found = []
    for term in terms:
        if term and re.search(rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])", text):
            found.append(term)
    return found


def clamp_score(value: float) -> int:
    return max(0, min(5, round(value)))


def evidence_score(text: str, publication_types: list[str]) -> int:
    pub = " ".join(publication_types).lower()
    if "meta-analysis" in text or "meta-analysis" in pub:
        return 5
    if "systematic review" in text or "review" in pub:
        return 4
    if "prospective" in text or "cohort" in text or "longitudinal" in text:
        return 4
    if "case-control" in text or "cross-sectional" in text:
        return 3
    if "journal article" in pub:
        return 2
    return 1


def recency_score(year: str) -> int:
    try:
        y = int(str(year)[:4])
    except ValueError:
        return 2
    current = dt.datetime.now().year
    if y >= current - 2:
        return 5
    if y >= current - 5:
        return 4
    if y >= current - 10:
        return 3
    if y >= current - 15:
        return 2
    return 1


def score_paper(paper: dict, config: dict) -> dict:
    weights = config.get("scoring_criteria", DEFAULT_WEIGHTS)
    term_groups = config.get("term_groups", [])
    exclude_terms = config.get("exclude_terms", [])
    method_terms = config.get("method_terms", DEFAULT_METHOD_TERMS)

    title = paper.get("title", "")
    abstract = paper.get("abstract", "")
    keywords = " ".join(paper.get("keywords", []))
    text = f"{title} {abstract} {keywords}".lower()

    matched_groups = []
    matched_terms = []
    for group in term_groups:
        hits = contains_any(text, group.get("terms", []))
        if hits:
            matched_groups.append(group.get("name", "topic"))
            matched_terms.extend(hits)

    exclude_hits = contains_any(text, exclude_terms)
    method_hits = contains_any(text, method_terms)
    required_groups = [group.get("name") for group in term_groups if group.get("required")]
    matched_required = [name for name in required_groups if name in matched_groups]

    if term_groups:
        topic_score = clamp_score((len(set(matched_groups)) / max(len(term_groups), 1)) * 5)
        if required_groups and len(matched_required) < len(required_groups):
            topic_score = min(topic_score, 2)
    else:
        topic_score = 2

    if exclude_hits and topic_score < 5:
        topic_score = max(0, topic_score - 1)

    method_score = clamp_score(min(5, len(set(method_hits)) * 0.8))
    evidence = evidence_score(text, paper.get("publication_types", []))
    recent = recency_score(paper.get("year", ""))
    novelty = clamp_score(1 + min(4, len(set(matched_terms)) / 3))

    total = (
        topic_score * weights.get("topic_relevance", 0.40)
        + method_score * weights.get("method_quality", 0.20)
        + evidence * weights.get("evidence_level", 0.20)
        + recent * weights.get("recency", 0.10)
        + novelty * weights.get("novelty_or_clinical_value", 0.10)
    )

    include_threshold = config.get("include_threshold", 3.6)
    maybe_threshold = config.get("maybe_threshold", 2.5)
    if total >= include_threshold and topic_score >= 3:
        decision = "include"
    elif total >= maybe_threshold and topic_score >= 2:
        decision = "maybe"
    else:
        decision = "exclude"

    if decision == "include":
        reason = "与用户定义主题和关键概念匹配度较高，适合优先纳入人工审查。"
    elif decision == "maybe":
        reason = "与主题部分相关，但研究对象、结局或方法信息需要人工复核。"
    elif exclude_hits:
        reason = "命中排除线索或主题相关性不足，建议暂不优先纳入。"
    else:
        reason = "未充分匹配用户定义的核心概念组合。"

    return {
        "paper_id": paper.get("paper_id", ""),
        "title": title,
        "year": paper.get("year", ""),
        "journal": paper.get("journal", ""),
        "doi": paper.get("doi", ""),
        "pmid": paper.get("pmid", ""),
        "total_score": round(total, 2),
        "topic_relevance_score": topic_score,
        "method_quality_score": method_score,
        "evidence_level_score": evidence,
        "recency_score": recent,
        "novelty_or_clinical_value_score": novelty,
        "include_decision": decision,
        "reason": reason,
        "assigned_sections": sorted(set(matched_groups)),
        "matched_terms": sorted(set(matched_terms)),
    }


def write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_csv(path: Path, records: list[dict]) -> None:
    fields = [
        "paper_id",
        "title",
        "year",
        "journal",
        "doi",
        "pmid",
        "total_score",
        "topic_relevance_score",
        "method_quality_score",
        "evidence_level_score",
        "recency_score",
        "novelty_or_clinical_value_score",
        "include_decision",
        "reason",
        "assigned_sections",
        "matched_terms",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            row = dict(record)
            row["assigned_sections"] = "; ".join(row["assigned_sections"])
            row["matched_terms"] = "; ".join(row["matched_terms"])
            writer.writerow(row)


def write_report(path: Path, config: dict, input_count: int, records: list[dict], source: str) -> None:
    counts = Counter(record["include_decision"] for record in records)
    top = sorted(records, key=lambda r: r["total_score"], reverse=True)[:15]
    top_lines = "\n".join(f"- {item['total_score']}: {item['title']} ({item['paper_id']}, {item['year']})" for item in top)
    weights = json.dumps(config.get("scoring_criteria", DEFAULT_WEIGHTS), ensure_ascii=False, indent=2)
    groups = ", ".join(group.get("name", "topic") for group in config.get("term_groups", [])) or "未配置，使用弱主题评分"
    report = f"""# 筛选评分 阶段性工作报告

## 当前阶段
自动筛选和评分。

## 用户研究方向
{config.get("research_topic", "未提供研究方向")}

## 使用的输入
- 输入文件：`{source}`
- 综述类型：{config.get("review_type", "scoping_review")}
- 主题词组：{groups}
- 评分权重：

```json
{weights}
```

## 已完成的操作
- 读取文献记录。
- 根据用户配置的主题词组、排除词、研究设计线索和证据类型进行规则评分。
- 输出 `screening_scores.jsonl` 和 `screening_scores.csv`，并保留每篇文献的 `paper_id`。

## 主要发现
- 输入文献数量：{input_count}
- include：{counts.get("include", 0)}
- maybe：{counts.get("maybe", 0)}
- exclude：{counts.get("exclude", 0)}

## 高分文献列表
{top_lines}

## 不确定性和潜在偏倚
- 本轮为配置驱动的 demo 规则评分，适合快速分流，不等同于正式系统综述的双人独立筛选。
- 如果主题词组配置过窄或过宽，评分结果会受到明显影响。

## 需要用户审查的决定
- 是否接受当前评分阈值、词组和权重？
- 是否人工复核 include 和高分 maybe 文献？
- 是否调整主题词组或排除词后重新评分？
"""
    path.write_text(report, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Config-driven screening score for JSONL literature records.")
    parser.add_argument("--input", required=True, help="Input papers.jsonl.")
    parser.add_argument("--output-dir", required=True, help="Output directory.")
    parser.add_argument("--config", default="", help="Scoring config JSON.")
    args = parser.parse_args()

    config = load_config(args.config)
    papers = load_papers(Path(args.input))
    records = [score_paper(paper, config) for paper in papers]

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "screening_scores.jsonl", records)
    write_csv(output_dir / "screening_scores.csv", records)
    (output_dir / "screening-config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(output_dir / "screening-stage_report.md", config, len(papers), records, Path(args.input).name)


if __name__ == "__main__":
    main()
