from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def write_reports(analysis: dict[str, Any], output_dir: str | Path) -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    json_path = out / "analysis.json"
    csv_path = out / "anomalies.csv"
    markdown_path = out / "summary.md"

    json_path.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_anomaly_csv(analysis.get("anomalies") or [], csv_path)
    markdown_path.write_text(_markdown_summary(analysis), encoding="utf-8")

    return {
        "json": json_path,
        "csv": csv_path,
        "markdown": markdown_path,
    }


def _write_anomaly_csv(anomalies: list[dict[str, Any]], path: Path) -> None:
    columns = ["severity", "type", "source", "query", "product_id", "title", "message"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for anomaly in anomalies:
            writer.writerow({column: anomaly.get(column, "") for column in columns})


def _markdown_summary(analysis: dict[str, Any]) -> str:
    summary = analysis.get("summary") or {}
    severity_counts = summary.get("severity_counts") or {}
    lines = [
        "# 购物搜索与商品监控报告",
        "",
        f"- 生成时间：{analysis.get('generated_at', '')}",
        f"- 数据源：{', '.join(summary.get('sources') or [])}",
        f"- 关键词数：{summary.get('query_count', 0)}",
        f"- 搜索结果行数：{summary.get('search_result_rows', 0)}",
        f"- 商品行数：{summary.get('product_rows', 0)}",
        f"- 异常数：{summary.get('anomaly_count', 0)}",
        f"- 严重度：{severity_counts}",
        "",
        "## 搜索表现",
        "",
        "| 数据源 | 关键词 | 信号类型 | 搜索量 | 结果量 | Top 相关数 | 平均相关度 | 购买意图 | 痛点 | 商业相关 | 数据年龄 |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for row in analysis.get("search_summary") or []:
        lines.append(
            "| {source} | {query} | {signal_type} | {search_volume} | {result_count} | "
            "{relevant_top_results} | {avg_relevance} | {buyer_intent_score} | "
            "{pain_score} | {commercial_relevance} | {data_age_days} |".format(
                **{
                    key: row.get(key, "")
                    for key in (
                        "source",
                        "query",
                        "signal_type",
                        "search_volume",
                        "result_count",
                        "relevant_top_results",
                        "avg_relevance",
                        "buyer_intent_score",
                        "pain_score",
                        "commercial_relevance",
                        "data_age_days",
                    )
                }
            )
        )

    lines.extend(["", "## 重点异常", ""])
    anomalies = analysis.get("anomalies") or []
    if not anomalies:
        lines.append("没有发现异常。")
    else:
        for anomaly in anomalies[:50]:
            label = anomaly.get("query") or anomaly.get("product_id") or anomaly.get("title")
            lines.append(
                f"- [{anomaly.get('severity')}] {anomaly.get('source')} / "
                f"{label}: {anomaly.get('message')}"
            )

    return "\n".join(lines) + "\n"
