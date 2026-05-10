---
name: literature-search
description: 执行医学文献检索并输出可审查结果文件。Demo 版本用于根据已确认的 PubMed 检索式调用 NCBI E-utilities，生成 papers.jsonl、papers.csv、search_log.md 和中文阶段性报告；适用于医学文献综述工作流中的检索执行阶段。
---

# 医学文献检索

## 使用前

先读取 `../shared/workflow_contract.md`。本 Skill 只执行用户已确认的检索式；如果检索式未确认，先返回 `literature-query-builder`。

Demo 版本只实际执行 PubMed 检索。其他数据库可在报告中记录为“建议后续扩展”，不要伪造结果。

## 脚本

使用：

```bash
python scripts/search_pubmed.py --query "<PubMed query>" --output-dir outputs --max-results 200
```

如果检索式较长，尤其是在 Windows PowerShell 中运行，优先把检索式保存为文本文件并使用：

```bash
python scripts/search_pubmed.py --query-file query.txt --output-dir outputs --max-results 200
```

可选参数：

```bash
--start-year 2020
--end-year 2026
--email user@example.com
--api-key NCBI_API_KEY
--batch-size 100
--retries 5
--timeout 60
--request-delay 0.34
```

如果用户提供 email 或 API key，传入脚本；没有也可以运行，但应控制请求频率和结果数量。

网络不稳定或 NCBI 关闭连接时，优先降低批大小并增加重试：

```bash
python scripts/search_pubmed.py --query-file query.txt --output-dir outputs --max-results 500 --batch-size 50 --retries 8 --timeout 90
```

脚本会强制使用 TLS 1.2 或以上、设置 User-Agent、对 HTTP 429/5xx、连接重置、远端关闭、超时和不完整响应进行重试。不要依赖外层终端反复 reconnect 来恢复检索。


## 必须输出

检索完成后，输出目录必须包含：

- `papers.jsonl`
- `papers.csv`
- `search_log.md`
- `stage_report.md`

`papers.jsonl` 用于后续自动处理，`papers.csv` 用于用户人工审查。

## 字段规范

每篇文献至少包含：

```json
{
  "paper_id": "PMID:...",
  "title": "",
  "authors": [],
  "year": "",
  "journal": "",
  "doi": "",
  "pmid": "",
  "abstract": "",
  "publication_types": [],
  "keywords": [],
  "url": "",
  "source": "PubMed"
}
```

## 阶段报告

`{{ stage }} stage_report.md` 必须用中文，包括：

- 当前检索式
- 数据库：PubMed
- 检索时间
- 返回记录数
- 成功解析记录数
- 输出文件
- 可能偏倚或遗漏
- 需要用户审查的问题

完成后暂停，询问用户是否重新检索、微调检索式或进入筛选评分。
