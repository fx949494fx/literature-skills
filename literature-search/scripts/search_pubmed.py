#!/usr/bin/env python
"""Search PubMed and export papers.jsonl, papers.csv, and review reports."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import http.client
import json
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
USER_AGENT = "codex-literature-search/0.1 (+https://www.ncbi.nlm.nih.gov/books/NBK25497/)"


def tls_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    if hasattr(ssl, "TLSVersion"):
        context.minimum_version = ssl.TLSVersion.TLSv1_2
    return context


def fetch(url: str, *, timeout: int, retries: int, delay: float) -> bytes:
    last_error: Exception | None = None
    context = tls_context()
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, retries + 2):
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code in {429, 500, 502, 503, 504} and attempt <= retries:
                retry_after = error.headers.get("Retry-After")
                wait = float(retry_after) if retry_after and retry_after.isdigit() else delay * attempt
                time.sleep(wait)
                continue
            raise
        except (
            urllib.error.URLError,
            TimeoutError,
            socket.timeout,
            ConnectionResetError,
            http.client.IncompleteRead,
            http.client.RemoteDisconnected,
            ssl.SSLError,
        ) as error:
            last_error = error
            if attempt <= retries:
                time.sleep(delay * attempt)
                continue
            raise RuntimeError(f"NCBI request failed after {retries + 1} attempts: {last_error}") from error
    raise RuntimeError(f"NCBI request failed: {last_error}")


def build_url(endpoint: str, params: dict[str, str | int]) -> str:
    return f"{BASE}/{endpoint}?{urllib.parse.urlencode(params)}"


def text_of(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return "".join(node.itertext()).strip()


def article_year(article: ET.Element) -> str:
    for path in [
        ".//ArticleDate/Year",
        ".//JournalIssue/PubDate/Year",
        ".//PubMedPubDate[@PubStatus='pubmed']/Year",
    ]:
        value = text_of(article.find(path))
        if value:
            return value
    medline_date = text_of(article.find(".//JournalIssue/PubDate/MedlineDate"))
    return medline_date[:4] if medline_date else ""


def article_doi(article: ET.Element) -> str:
    for item in article.findall(".//ArticleId"):
        if item.attrib.get("IdType") == "doi" and item.text:
            return item.text.strip()
    for item in article.findall(".//ELocationID"):
        if item.attrib.get("EIdType") == "doi" and item.text:
            return item.text.strip()
    return ""


def article_authors(article: ET.Element) -> list[str]:
    authors = []
    for author in article.findall(".//AuthorList/Author"):
        collective = text_of(author.find("CollectiveName"))
        if collective:
            authors.append(collective)
            continue
        last = text_of(author.find("LastName"))
        initials = text_of(author.find("Initials"))
        if last:
            authors.append(f"{last} {initials}".strip())
    return authors


def parse_articles(xml_bytes: bytes) -> list[dict[str, object]]:
    root = ET.fromstring(xml_bytes)
    papers = []
    for article in root.findall(".//PubmedArticle"):
        pmid = text_of(article.find(".//PMID"))
        abstract_parts = [text_of(node) for node in article.findall(".//Abstract/AbstractText")]
        keywords = [text_of(node) for node in article.findall(".//KeywordList/Keyword")]
        publication_types = [text_of(node) for node in article.findall(".//PublicationTypeList/PublicationType")]
        papers.append(
            {
                "paper_id": f"PMID:{pmid}" if pmid else "",
                "title": text_of(article.find(".//ArticleTitle")),
                "authors": article_authors(article),
                "year": article_year(article),
                "journal": text_of(article.find(".//Journal/Title")),
                "doi": article_doi(article),
                "pmid": pmid,
                "abstract": " ".join(part for part in abstract_parts if part),
                "publication_types": publication_types,
                "keywords": keywords,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
                "source": "PubMed",
            }
        )
    return papers


def write_jsonl(path: Path, papers: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for paper in papers:
            handle.write(json.dumps(paper, ensure_ascii=False) + "\n")


def write_csv(path: Path, papers: list[dict[str, object]]) -> None:
    fields = [
        "paper_id",
        "title",
        "authors",
        "year",
        "journal",
        "doi",
        "pmid",
        "abstract",
        "publication_types",
        "keywords",
        "url",
        "source",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for paper in papers:
            row = dict(paper)
            row["authors"] = "; ".join(row.get("authors", []))
            row["publication_types"] = "; ".join(row.get("publication_types", []))
            row["keywords"] = "; ".join(row.get("keywords", []))
            writer.writerow(row)


def write_reports(output_dir: Path, args: argparse.Namespace, found: int, papers: list[dict[str, object]]) -> None:
    now = dt.datetime.now().isoformat(timespec="seconds")
    log = f"""# PubMed 检索日志

- 检索时间：{now}
- 数据库：PubMed
- 检索式：`{args.query}`
- 年份范围：{args.start_year or "未限制"} - {args.end_year or "未限制"}
- 最大结果数：{args.max_results}
- 抓取批大小：{args.batch_size}
- 网络重试次数：{args.retries}
- PubMed 返回数量：{found}
- 成功解析数量：{len(papers)}
"""
    (output_dir / "search_log.md").write_text(log, encoding="utf-8")

    report = f"""# 阶段性工作报告

## 当前阶段
PubMed 文献检索

## 用户研究方向
请结合上游 `query_plan.md` 或用户输入审查。

## 使用的输入
- 检索式：`{args.query}`
- 数据库：PubMed
- 年份范围：{args.start_year or "未限制"} - {args.end_year or "未限制"}
- 最大结果数：{args.max_results}
- 抓取批大小：{args.batch_size}
- 网络重试次数：{args.retries}

## 已完成的操作
调用 NCBI E-utilities 完成 PubMed 检索，分批抓取 efetch 结果，并解析题名、作者、年份、期刊、DOI、PMID、摘要、文献类型和关键词。

## 主要输出文件
- `papers.jsonl`
- `papers.csv`
- `search_log.md`

## 主要发现
- PubMed 返回记录数：{found}
- 成功解析记录数：{len(papers)}

## 不确定性和潜在偏倚
- Demo 版本只检索 PubMed，可能遗漏 Embase、Cochrane Library、ClinicalTrials.gov、Web of Science/Scopus 等来源。
- 如果检索式过窄，可能遗漏同义词、MeSH 词尚未标引的新近文献或跨学科研究。

## 需要用户审查的决定
- 是否接受当前检索结果？
- 是否扩大或收窄检索式？
- 是否调整年份范围或文献类型？

## 建议下一步
用户确认后，进入 `paper-screening-score` 进行自动筛选和评分；也可以先微调检索式并重新运行当前步骤。
"""
    (output_dir / "stage_report.md").write_text(report, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Search PubMed and export JSONL/CSV results.")
    parser.add_argument("--query", default="", help="Confirmed PubMed query.")
    parser.add_argument("--query-file", default="", help="Text file containing the confirmed PubMed query.")
    parser.add_argument("--output-dir", default="outputs", help="Directory for output files.")
    parser.add_argument("--max-results", type=int, default=200, help="Maximum PubMed records to fetch.")
    parser.add_argument("--start-year", default="", help="Optional start year.")
    parser.add_argument("--end-year", default="", help="Optional end year.")
    parser.add_argument("--email", default="", help="Optional email for NCBI.")
    parser.add_argument("--api-key", default="", help="Optional NCBI API key.")
    parser.add_argument("--batch-size", type=int, default=100, help="Number of PubMed records per efetch request.")
    parser.add_argument("--request-delay", type=float, default=0.34, help="Delay between NCBI requests in seconds.")
    parser.add_argument("--timeout", type=int, default=60, help="Per-request timeout in seconds.")
    parser.add_argument("--retries", type=int, default=5, help="Retry count for transient NCBI/network failures.")
    args = parser.parse_args()
    if args.query_file:
        args.query = Path(args.query_file).read_text(encoding="utf-8").strip()
    if not args.query:
        parser.error("--query or --query-file is required.")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    query = args.query
    if args.start_year or args.end_year:
        start = args.start_year or "1800"
        end = args.end_year or str(dt.datetime.now().year)
        query = f"({query}) AND ({start}:{end}[dp])"

    common = {"db": "pubmed", "retmode": "xml", "tool": "codex-literature-search"}
    if args.email:
        common["email"] = args.email
    if args.api_key:
        common["api_key"] = args.api_key

    search_params = {
        **common,
        "term": query,
        "retmax": args.max_results,
        "usehistory": "y",
    }
    search_xml = fetch(build_url("esearch.fcgi", search_params), timeout=args.timeout, retries=args.retries, delay=args.request_delay)
    search_root = ET.fromstring(search_xml)
    found = int(text_of(search_root.find(".//Count")) or 0)
    webenv = text_of(search_root.find(".//WebEnv"))
    query_key = text_of(search_root.find(".//QueryKey"))

    papers: list[dict[str, object]] = []
    if found and webenv and query_key:
        target = min(args.max_results, found)
        batch_size = max(1, min(args.batch_size, target))
        for retstart in range(0, target, batch_size):
            time.sleep(args.request_delay)
            retmax = min(batch_size, target - retstart)
            fetch_params = {
                **common,
                "query_key": query_key,
                "WebEnv": webenv,
                "retstart": retstart,
                "retmax": retmax,
            }
            xml = fetch(build_url("efetch.fcgi", fetch_params), timeout=args.timeout, retries=args.retries, delay=args.request_delay)
            papers.extend(parse_articles(xml))

    write_jsonl(output_dir / "papers.jsonl", papers)
    write_csv(output_dir / "papers.csv", papers)
    write_reports(output_dir, args, found, papers)


if __name__ == "__main__":
    main()
