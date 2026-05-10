#!/usr/bin/env python
"""Build a reusable medical review framework from evidence packets."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


DEFAULT_SECTIONS = [
    ("background", "研究背景与问题界定"),
    ("concepts", "核心概念、暴露或干预因素"),
    ("populations", "目标人群与应用场景"),
    ("outcomes", "主要结局与评价指标"),
    ("evidence", "现有证据类型与主要发现"),
    ("methods", "方法学质量、异质性与证据限制"),
    ("translation", "应用价值、研究空白与未来方向"),
]


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def as_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip() and value.strip() != "unclear":
        return [part.strip() for part in value.split(";") if part.strip()]
    return []


def cite(packet: dict) -> str:
    pmid = packet.get("pmid", "")
    citation = packet.get("citation", "")
    return f"{citation} PMID:{pmid}" if pmid else citation or packet.get("paper_id", "")


def packet_score(packet: dict) -> float:
    try:
        return float(packet.get("screening_score", 0))
    except (TypeError, ValueError):
        return 0.0


def collect_terms(packets: list[dict], key: str, limit: int = 10) -> list[str]:
    counter: Counter[str] = Counter()
    for packet in packets:
        counter.update(as_list(packet.get(key)))
    return [f"{term}({count})" for term, count in counter.most_common(limit)]


def assign_sections(packet: dict) -> list[str]:
    sections = {"background", "evidence", "methods", "translation"}
    if as_list(packet.get("key_concepts")) or as_list(packet.get("exposures")) or as_list(packet.get("interventions")):
        sections.add("concepts")
    if packet.get("population") not in {"", "unclear", None} or packet.get("population_context") not in {"", "unclear", None}:
        sections.add("populations")
    if as_list(packet.get("outcomes")) or as_list(packet.get("evaluation_metrics")):
        sections.add("outcomes")
    return [section_id for section_id, _ in DEFAULT_SECTIONS if section_id in sections]


def section_argument(section_id: str, topic: str) -> str:
    arguments = {
        "background": f"界定“{topic}”的研究背景、临床或公共卫生意义，以及现有证据为何需要被系统整理。",
        "concepts": "梳理本综述涉及的核心概念、暴露因素、干预措施、指标或分类方式，明确不同概念之间的边界。",
        "populations": "比较不同研究对象、疾病阶段、风险水平或应用场景下证据的适用性。",
        "outcomes": "整理主要结局、替代结局、预测性能指标或评价指标，区分关联证据和应用价值证据。",
        "evidence": "概述现有研究设计、主要发现和证据强度，识别一致证据与不确定证据。",
        "methods": "讨论研究设计、测量方法、模型构建、混杂控制、偏倚风险和异质性来源。",
        "translation": "综合临床或实践应用价值，提出证据缺口、未来研究方向和转化路径。",
    }
    return arguments[section_id]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a reusable medical review framework from evidence packets.")
    parser.add_argument("--packets", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--review-type", default="scoping_review")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--title", default="", help="Optional preferred review title.")
    parser.add_argument("--max-papers-per-section", type=int, default=12)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    packets = load_jsonl(Path(args.packets))
    title = args.title or args.topic

    section_packets: dict[str, list[dict]] = defaultdict(list)
    matrix_rows = []
    section_titles = dict(DEFAULT_SECTIONS)
    for packet in sorted(packets, key=packet_score, reverse=True):
        for section_id in assign_sections(packet):
            section_packets[section_id].append(packet)
            matrix_rows.append(
                {
                    "section_id": section_id,
                    "section_title": section_titles[section_id],
                    "paper_id": packet.get("paper_id", ""),
                    "citation": cite(packet),
                    "title": packet.get("title", ""),
                    "study_design": packet.get("study_design", "unclear"),
                    "population": packet.get("population", "unclear"),
                    "population_context": packet.get("population_context", "unclear"),
                    "key_concepts": "; ".join(as_list(packet.get("key_concepts")) or as_list(packet.get("exposures")) or as_list(packet.get("interventions"))),
                    "outcomes": "; ".join(as_list(packet.get("outcomes"))),
                    "evaluation_metrics": "; ".join(as_list(packet.get("evaluation_metrics")) or as_list(packet.get("effect_measures"))),
                    "review_contribution": packet.get("review_contribution", "unclear"),
                    "screening_score": packet.get("screening_score", ""),
                }
            )

    with (output_dir / "evidence_allocation_matrix.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fields = [
            "section_id",
            "section_title",
            "paper_id",
            "citation",
            "title",
            "study_design",
            "population",
            "population_context",
            "key_concepts",
            "outcomes",
            "evaluation_metrics",
            "review_contribution",
            "screening_score",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(matrix_rows)

    concept_terms = collect_terms(packets, "key_concepts") or collect_terms(packets, "exposures") or collect_terms(packets, "interventions")
    outcome_terms = collect_terms(packets, "outcomes")
    metric_terms = collect_terms(packets, "evaluation_metrics") or collect_terms(packets, "effect_measures")
    design_terms = collect_terms(packets, "study_design")

    section_blocks = []
    for section_id, section_title in DEFAULT_SECTIONS:
        papers = section_packets.get(section_id, [])
        paper_lines = "\n".join(f"- {cite(packet)}: {packet.get('title', '')}" for packet in papers[: args.max_papers_per_section])
        section_blocks.append(
            f"""### {section_title}

核心论点：{section_argument(section_id, args.topic)}

支撑证据：
{paper_lines or "- 当前 evidence packets 中证据不足。"}

需核验点：全文中的研究对象、纳排标准、核心变量定义、结局定义、统计方法、偏倚风险和证据等级。
"""
        )

    framework = f"""# 综述框架建议

## 题目候选

1. {title}
2. {title}：证据图谱、应用价值与未来方向

## 综述类型

{args.review_type}

## 中心问题

围绕“{args.topic}”，现有研究提供了哪些证据，证据适用于哪些人群或场景，仍存在哪些方法学限制和应用缺口？

## 中心论点

本综述应以用户给定研究方向为主线，系统整理核心概念、目标人群、结局指标、证据类型和应用价值，并区分已被较充分支持的结论、仍需全文核验的证据和未来研究空白。

## 目标读者

相关临床、公共卫生、基础或转化医学研究者，以及需要理解该主题证据现状的实践人员。

## 章节结构

{chr(10).join(section_blocks)}

## 证据概览

- 文献数量：{len(packets)}
- 高频核心概念：{", ".join(concept_terms) or "unclear"}
- 高频结局或评价对象：{", ".join(outcome_terms) or "unclear"}
- 高频评价指标：{", ".join(metric_terms) or "unclear"}
- 研究设计线索：{", ".join(design_terms) or "unclear"}

## 研究空白

- 不同研究在人群定义、暴露/干预/指标定义、结局定义和随访时间上可能存在异质性。
- 部分证据可能停留在关联层面，尚缺少外部验证、机制解释、临床决策价值或真实世界应用评估。
- 关键结论需要通过全文核验、偏倚风险评价和证据等级评估后再写入投稿级稿件。

## 需要全文核验的关键点

- 纳排标准和目标人群定义
- 核心变量、暴露、干预、指标或分类方式
- 结局定义、测量时间点和随访时间
- 统计模型、混杂调整和缺失值处理
- 效应量、预测性能、敏感性分析或证据等级
- 偏倚风险、外部验证和应用场景

## 进入初稿前需用户确认

- 希望纳入初稿写作的文献数量：待确认。建议选项：30 篇、50 篇、100 篇，或全部已确认 include 文献。
- 综述正文目标字数：待确认。请提供不含参考文献的字数，例如 5000、8000 或 10000 字。
- 是否需要先扩展 evidence packets：当前 evidence packets 数量为 {len(packets)} 篇；若目标文献数大于该数量，应先返回 `paper-metadata-extractor` 扩展证据包。
"""
    (output_dir / "review_framework.md").write_text(framework, encoding="utf-8")

    figure_plan = f"""# 图表计划

## 推荐图

1. 主题证据地图：核心概念 × 目标人群 × 主要结局。
2. 研究流程图：检索、筛选、证据抽取、框架构建和正文写作。
3. 应用路径图：从证据发现到临床、公共卫生或机制研究应用。

## 推荐表

1. 纳入研究基本特征表。
2. 核心概念、指标、暴露或干预定义表。
3. 主要结局、评价指标和证据强度表。
4. 研究空白和未来研究方向表。
"""
    (output_dir / "figure_table_plan.md").write_text(figure_plan, encoding="utf-8")

    (output_dir / "framework-stage_report.md").write_text(
        f"""# 综述框架 阶段性工作报告

## 当前阶段
综述框架构建。

## 使用的输入
- evidence packets：{len(packets)} 篇
- 综述类型：{args.review_type}
- 研究方向：{args.topic}

## 已完成的操作
- 基于 evidence packets 动态生成通用医学综述框架。
- 按章节分配证据，并输出证据分配矩阵。
- 生成图表计划和进入初稿前的用户确认问题。

## 主要输出文件
- `review_framework.md`
- `evidence_allocation_matrix.csv`
- `figure_table_plan.md`

## 不确定性和潜在偏倚
- 当前框架主要基于 evidence packets，若 evidence packets 来源于摘要，则仍需全文核验。
- 章节证据分配为规则生成，用户应审查是否符合综述叙事逻辑。

## 需要用户审查的决定
- 是否接受中心论点？
- 是否调整章节顺序或合并章节？
- 希望纳入初稿写作的文献数量是多少？例如 30、50、100 篇，或全部 include 文献。
- 综述正文目标字数是多少？仅计算正文，不含参考文献。
- 如果目标文献数超过当前 evidence packets 数量，是否先返回 `paper-metadata-extractor` 扩展证据包？
- 上述写作参数确认后，是否进入综述初稿写作？
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
