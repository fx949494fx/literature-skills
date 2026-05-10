#!/usr/bin/env python
"""Extract reusable evidence packets from literature records and screening scores."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


DEFAULT_STUDY_DESIGNS = [
    ("systematic review/meta-analysis", ["systematic review", "meta-analysis"]),
    ("prospective cohort", ["prospective cohort", "prospective"]),
    ("cohort", ["cohort", "longitudinal"]),
    ("cross-sectional", ["cross-sectional", "cross sectional"]),
    ("case-control", ["case-control", "case control"]),
    ("prediction model", ["prediction model", "machine learning", "logistic regression"]),
    ("clinical trial", ["randomized", "trial"]),
]

DEFAULT_EVALUATION_TERMS = {
    "AUC": ["auc", "area under the curve"],
    "ROC": ["roc", "receiver operating"],
    "effect estimate": ["hazard ratio", "odds ratio", "relative risk", "risk ratio"],
    "calibration": ["calibration"],
    "sensitivity/specificity": ["sensitivity", "specificity"],
}


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_config(path: str) -> dict:
    if not path:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def find_terms(text: str, mapping: dict[str, list[str]]) -> list[str]:
    found = []
    lower = text.lower()
    for label, terms in mapping.items():
        if any(re.search(rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])", lower) for term in terms):
            found.append(label)
    return found


def study_design(text: str, config: dict) -> str:
    lower = text.lower()
    for label, terms in config.get("study_design_terms", DEFAULT_STUDY_DESIGNS):
        if any(term.lower() in lower for term in terms):
            return label
    return "unclear"


def first_sentence_with(text: str, terms: list[str]) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    lower_terms = [term.lower() for term in terms]
    for sentence in sentences:
        s = sentence.lower()
        if any(term in s for term in lower_terms):
            return sentence.strip()
    return "unclear"


def citation(paper: dict) -> str:
    authors = paper.get("authors", [])
    first = authors[0] if authors else "Unknown"
    year = paper.get("year", "")
    return f"{first} et al., {year}" if year else f"{first} et al."


def citation_placeholder(paper: dict, score: dict) -> str:
    pmid = paper.get("pmid") or str(score.get("paper_id", "")).replace("PMID:", "")
    if pmid:
        return f"[PMID:{pmid}]"
    doi = paper.get("doi", "")
    if doi:
        return f"[DOI:{doi}]"
    paper_id = score.get("paper_id", "")
    return f"[{paper_id}]" if paper_id else ""


def configured_terms(config: dict, key: str) -> dict[str, list[str]]:
    return config.get(key, {})


def fallback_key_concepts(score: dict) -> list[str]:
    sections = score.get("assigned_sections", [])
    matched = score.get("matched_terms", [])
    if isinstance(sections, str):
        sections = [item.strip() for item in sections.split(";") if item.strip()]
    if isinstance(matched, str):
        matched = [item.strip() for item in matched.split(";") if item.strip()]
    return list(dict.fromkeys([*sections, *matched]))


def contribution_points(packet_like: dict) -> list[str]:
    points = []
    concepts = packet_like.get("key_concepts") or []
    outcomes = packet_like.get("outcomes") or []
    metrics = packet_like.get("evaluation_metrics") or []
    design = packet_like.get("study_design", "unclear")
    population = packet_like.get("population_context") or packet_like.get("population") or "unclear"
    finding = packet_like.get("main_finding_signal", "unclear")
    review_use = packet_like.get("review_use", "unclear")
    if concepts or outcomes:
        points.append(
            "可用于说明"
            + ("、".join(concepts[:4]) if concepts else "本主题核心概念")
            + "与"
            + ("、".join(outcomes[:4]) if outcomes else "相关结局或评价对象")
            + "之间的证据关系。"
        )
    if design != "unclear" or population != "unclear":
        points.append(f"可用于描述{design}研究在{population}中的证据来源和适用场景。")
    if metrics:
        points.append(f"可用于整理{ '、'.join(metrics[:4]) }等评价指标的报告情况。")
    if review_use != "unclear":
        points.append(review_use.rstrip("。") + "。")
    if finding != "unclear":
        points.append(f"摘要层面的主要发现线索为：{finding}")
    return points[:4] or ["可作为用户定义综述主题下的候选证据，需结合全文确认具体贡献。"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract reusable evidence packets from workflow outputs.")
    parser.add_argument("--papers", required=True)
    parser.add_argument("--scores", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--include-decisions", nargs="+", default=["include"])
    parser.add_argument("--top-n", type=int, default=100)
    parser.add_argument("--config", default="", help="Optional extraction config with term dictionaries.")
    args = parser.parse_args()

    config = load_config(args.config)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    papers = {paper.get("paper_id"): paper for paper in load_jsonl(Path(args.papers))}
    scores = load_jsonl(Path(args.scores))
    selected = [s for s in scores if s.get("include_decision") in set(args.include_decisions)]
    selected.sort(key=lambda item: float(item.get("total_score", 0)), reverse=True)
    selected = selected[: args.top_n]

    concept_terms = configured_terms(config, "key_concept_terms")
    population_terms = configured_terms(config, "population_terms")
    outcome_terms = configured_terms(config, "outcome_terms")
    evaluation_terms = configured_terms(config, "evaluation_terms") or DEFAULT_EVALUATION_TERMS

    packets = []
    for score in selected:
        paper = papers.get(score.get("paper_id"), {})
        text = f"{paper.get('title', '')}. {paper.get('abstract', '')}"
        key_concepts = find_terms(text, concept_terms) if concept_terms else fallback_key_concepts(score)
        populations = find_terms(text, population_terms) if population_terms else []
        outcomes = find_terms(text, outcome_terms) if outcome_terms else []
        placeholder = citation_placeholder(paper, score)
        packet = {
            "paper_id": score.get("paper_id", ""),
            "title": paper.get("title", score.get("title", "")),
            "citation": citation(paper),
            "citation_placeholder": placeholder,
            "year": paper.get("year", ""),
            "doi": paper.get("doi", ""),
            "pmid": paper.get("pmid", ""),
            "study_design": study_design(text, config),
            "population": first_sentence_with(text, ["participants", "patients", "adults", "cohort", "sample"]),
            "population_context": "; ".join(populations) if populations else "unclear",
            "key_concepts": key_concepts,
            "outcomes": outcomes,
            "evaluation_metrics": find_terms(text, evaluation_terms),
            "main_finding_signal": first_sentence_with(text, ["associated", "predict", "risk", "increase", "decrease", "improve"]),
            "limitations_signal": first_sentence_with(text, ["limitation", "caution", "further studies", "uncertain"]),
            "review_use": "用于支持用户定义综述主题下的证据整理、章节分配和后续精读。",
            "review_contribution": "",
            "contribution_points": [],
            "usable_claims": [],
            "screening_decision": score.get("include_decision", ""),
            "screening_score": score.get("total_score", 0),
            "source_trace": {"abstract_available": bool(paper.get("abstract")), "source": paper.get("source", "PubMed")},
        }
        points = contribution_points(packet)
        packet["review_contribution"] = points[0]
        packet["contribution_points"] = points
        packet["usable_claims"] = [
            {
                "claim": point,
                "citation": placeholder,
                "evidence_basis": "abstract_or_metadata",
                "needs_full_text_check": True,
            }
            for point in points
        ]
        packets.append(packet)

    with (output_dir / "paper_evidence_packets.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for packet in packets:
            handle.write(json.dumps(packet, ensure_ascii=False) + "\n")

    fields = list(packets[0].keys()) if packets else []
    with (output_dir / "paper_evidence_matrix.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for packet in packets:
            row = dict(packet)
            for key, value in row.items():
                if isinstance(value, list):
                    row[key] = "; ".join(value)
                elif isinstance(value, dict):
                    row[key] = json.dumps(value, ensure_ascii=False)
            writer.writerow(row)

    (output_dir / "metadata-extraction-stage_report.md").write_text(
        f"""# 元数据抽取 阶段性工作报告

## 当前阶段
文献元数据和 evidence packet 抽取。

## 已完成的操作
- 读取文献记录和筛选评分。
- 按纳入状态和分数选取文献。
- 抽取研究设计、人群、核心概念、结局、评价指标和综述用途。

## 主要输出文件
- `paper_evidence_packets.jsonl`
- `paper_evidence_matrix.csv`

## 主要发现
- 抽取文献数：{len(packets)}
- 导出范围：{", ".join(args.include_decisions)}
- Top N：{args.top_n}

## 不确定性和潜在偏倚
- 本阶段主要基于题名、摘要和关键词，全文中的方法细节和局限性可能未被捕获。
- `unclear` 表示当前元数据不足，不代表文献没有相关信息。
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
