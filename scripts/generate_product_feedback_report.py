from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shopping_intel.models import parse_datetime, parse_float, parse_int


SOURCE_METRICS = {
    "github": ("stars", "forks"),
    "github_issues": ("issue_comments", "issue_mentions"),
    "producthunt": ("votes", "comments"),
    "huggingface_models": ("likes", "downloads"),
    "huggingface_spaces": ("likes", "downloads"),
    "hackernews": ("points", "comments"),
    "reddit": ("score", "comments"),
    "google_news": ("coverage", "mentions"),
    "ai_dev_jobs": ("quality_score", "salary_signal"),
    "agentic_engineering_jobs": ("views_clicks", "salary_signal"),
    "agentdeals": ("deal_signal", "freshness"),
    "oksurf_news": ("coverage", "mentions"),
    "api_status_check": ("incident_weight", "service_count"),
    "internet_archive": ("downloads", "downloads"),
    "nvd": ("cvss_score_x10", "references"),
    "devitjobs": ("job_signal", "salary_signal"),
    "predscope": ("volume", "liquidity"),
    "patentsview": ("citations", "patents"),
    "domainsdb": ("domains", "records"),
    "arxiv": ("citations_proxy", "papers"),
    "youtube": ("engagement", "videos"),
    "x_recent": ("engagement", "posts"),
}

REPORT_COLUMNS = [
    "source",
    "product_id",
    "title",
    "url",
    "matched_queries",
    "signal_type",
    "buyer_intent_score",
    "pain_score",
    "source_confidence",
    "commercial_relevance",
    "category",
    "seller",
    "rating",
    "feedback_metric",
    "feedback_count",
    "engagement_metric",
    "engagement_count",
    "feedback_score",
    "evaluation_level",
    "trend_status",
    "trend_delta",
    "trend_percent",
    "recency_status",
    "last_updated",
    "collected_at",
    "summary",
]

HISTORY_COLUMNS = [
    "snapshot_date",
    "source",
    "product_id",
    "title",
    "url",
    "feedback_count",
    "engagement_count",
    "rating",
    "last_updated",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate product feedback, evaluation, and trend report.")
    parser.add_argument("--products", default="data/products.realtime-ai.csv")
    parser.add_argument("--search", default="data/search_results.realtime-ai.csv")
    parser.add_argument("--history", default="data/history/product_feedback_history.csv")
    parser.add_argument("--out", default="reports/product-feedback")
    parser.add_argument("--top", type=int, default=30)
    args = parser.parse_args()

    products_path = resolve(args.products)
    search_path = resolve(args.search)
    history_path = resolve(args.history)
    output_dir = resolve(args.out)
    output_dir.mkdir(parents=True, exist_ok=True)

    products = dedupe_products(read_rows(products_path))
    search_rows = read_rows(search_path)
    query_map = build_query_map(search_rows)
    history = read_rows(history_path)

    now = datetime.now(timezone.utc)
    source_max = source_maxima(products)
    report_rows = [
        enrich_product(row, query_map, history, source_max, now)
        for row in products
    ]
    report_rows.sort(
        key=lambda row: (
            float(row.get("feedback_score") or 0),
            int(row.get("trend_delta") or 0),
            int(row.get("feedback_count") or 0),
        ),
        reverse=True,
    )

    write_outputs(report_rows, output_dir, args.top)
    update_history(history_path, history, products)

    print("Product feedback report generated")
    print(f"Products: {len(report_rows)}")
    print(f"Markdown: {output_dir / 'products.md'}")
    print(f"CSV: {output_dir / 'products.csv'}")
    print(f"JSON: {output_dir / 'products.json'}")
    return 0


def enrich_product(
    row: dict[str, str],
    query_map: dict[tuple[str, str, str], set[str]],
    history: list[dict[str, str]],
    source_max: dict[str, int],
    now: datetime,
) -> dict[str, Any]:
    source = row.get("source", "")
    product_id = row.get("product_id", "")
    title = row.get("title", "")
    url = row.get("url", "")
    feedback_count = parse_int(row.get("review_count")) or 0
    engagement_count = parse_int(row.get("sales_volume")) or 0
    rating = parse_float(row.get("rating"))
    metric_names = SOURCE_METRICS.get(source, ("feedback", "engagement"))
    total_signal = max(0, feedback_count) + max(0, engagement_count)
    feedback_score = round(log_norm(total_signal, source_max.get(source, 0)) * 100, 1)
    prior = latest_prior(history, row)
    prior_total = None
    if prior:
        prior_total = (parse_int(prior.get("feedback_count")) or 0) + (parse_int(prior.get("engagement_count")) or 0)
    trend_delta, trend_percent, trend_status = trend(total_signal, prior_total)
    recency_status = recency(row.get("last_updated"), now)
    matched_queries = sorted(
        query_map.get(query_key(source, product_id, url), set())
        | query_map.get(query_key(source, title, url), set())
        | query_map.get(query_key(source, "", url), set())
    )
    evaluation_level = evaluate(feedback_score, rating, trend_status, recency_status)

    return {
        "source": source,
        "product_id": product_id,
        "title": title,
        "url": url,
        "matched_queries": ", ".join(matched_queries),
        "signal_type": row.get("signal_type", ""),
        "buyer_intent_score": row.get("buyer_intent_score", ""),
        "pain_score": row.get("pain_score", ""),
        "source_confidence": row.get("source_confidence", ""),
        "commercial_relevance": row.get("commercial_relevance", ""),
        "category": row.get("category", ""),
        "seller": row.get("seller", ""),
        "rating": "" if rating is None else rating,
        "feedback_metric": metric_names[0],
        "feedback_count": feedback_count,
        "engagement_metric": metric_names[1],
        "engagement_count": engagement_count,
        "feedback_score": feedback_score,
        "evaluation_level": evaluation_level,
        "trend_status": trend_status,
        "trend_delta": trend_delta,
        "trend_percent": trend_percent,
        "recency_status": recency_status,
        "last_updated": row.get("last_updated", ""),
        "collected_at": row.get("collected_at", ""),
        "summary": summarize(source, feedback_score, trend_status, recency_status, metric_names, feedback_count, engagement_count),
    }


def build_query_map(rows: list[dict[str, str]]) -> dict[tuple[str, str, str], set[str]]:
    mapping: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for row in rows:
        query = row.get("query", "")
        if not query:
            continue
        source = row.get("source", "")
        title = row.get("title", "")
        url = row.get("url", "")
        mapping[query_key(source, title, url)].add(query)
        mapping[query_key(source, "", url)].add(query)
    return mapping


def source_maxima(products: list[dict[str, str]]) -> dict[str, int]:
    maxima: dict[str, int] = defaultdict(int)
    for row in products:
        source = row.get("source", "")
        total = (parse_int(row.get("review_count")) or 0) + (parse_int(row.get("sales_volume")) or 0)
        maxima[source] = max(maxima[source], total)
    return dict(maxima)


def dedupe_products(products: list[dict[str, str]]) -> list[dict[str, str]]:
    merged: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for row in products:
        key = product_key(row)
        if key not in merged:
            merged[key] = dict(row)
            continue
        current = merged[key]
        if numeric_total(row) > numeric_total(current):
            for metric in ("review_count", "sales_volume", "rating"):
                if row.get(metric):
                    current[metric] = row[metric]
        if newer(row.get("last_updated", ""), current.get("last_updated", "")):
            current["last_updated"] = row.get("last_updated", "")
        if newer(row.get("collected_at", ""), current.get("collected_at", "")):
            current["collected_at"] = row.get("collected_at", "")
        for field in (
            "title",
            "url",
            "seller",
            "category",
            "stock_status",
            "signal_type",
            "buyer_intent_score",
            "pain_score",
            "source_confidence",
            "commercial_relevance",
        ):
            if not current.get(field) and row.get(field):
                current[field] = row[field]
    return list(merged.values())


def product_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    source = row.get("source", "").strip().lower()
    product_id = row.get("product_id", "").strip().lower()
    url = row.get("url", "").strip().lower()
    title = row.get("title", "").strip().lower()
    return (source, product_id, url, title if not product_id and not url else "")


def numeric_total(row: dict[str, str]) -> int:
    return (parse_int(row.get("review_count")) or 0) + (parse_int(row.get("sales_volume")) or 0)


def newer(left: str, right: str) -> bool:
    left_date = parse_datetime(left)
    right_date = parse_datetime(right)
    if left_date is None:
        return False
    if right_date is None:
        return True
    return left_date > right_date


def latest_prior(history: list[dict[str, str]], current: dict[str, str]) -> dict[str, str] | None:
    current_date = current.get("collected_at", "")
    candidates = []
    for row in history:
        if not same_product(row, current):
            continue
        if current_date and row.get("snapshot_date") == current_date:
            continue
        candidates.append(row)
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item.get("snapshot_date", ""))[-1]


def same_product(left: dict[str, str], right: dict[str, str]) -> bool:
    if left.get("source") != right.get("source"):
        return False
    if left.get("product_id") and right.get("product_id") and left.get("product_id") == right.get("product_id"):
        return True
    if left.get("url") and right.get("url") and left.get("url") == right.get("url"):
        return True
    return bool(left.get("title") and right.get("title") and left.get("title") == right.get("title"))


def trend(current_total: int, prior_total: int | None) -> tuple[int, str, str]:
    if prior_total is None:
        return 0, "", "baseline"
    delta = current_total - prior_total
    percent = "" if prior_total <= 0 else f"{round(delta / prior_total * 100, 1)}%"
    if delta >= 10 or (prior_total > 0 and delta / prior_total >= 0.15):
        status = "rising"
    elif delta <= -10 or (prior_total > 0 and delta / prior_total <= -0.15):
        status = "falling"
    else:
        status = "stable"
    return delta, percent, status


def recency(value: str, now: datetime) -> str:
    parsed = parse_datetime(value)
    if parsed is None:
        return "unknown"
    age = max(0, (now - parsed).days)
    if age <= 7:
        return "fresh"
    if age <= 30:
        return "recent"
    if age <= 90:
        return "aging"
    return "stale"


def evaluate(feedback_score: float, rating: float | None, trend_status: str, recency_status: str) -> str:
    score = feedback_score
    if rating is not None:
        score += max(0, min(20, (rating - 3.5) * 12))
    if trend_status == "rising":
        score += 12
    elif trend_status == "falling":
        score -= 10
    if recency_status in {"fresh", "recent"}:
        score += 8
    elif recency_status == "stale":
        score -= 14
    if score >= 82:
        return "strong"
    if score >= 58:
        return "healthy"
    if score >= 32:
        return "weak"
    return "thin"


def summarize(
    source: str,
    feedback_score: float,
    trend_status: str,
    recency_status: str,
    metric_names: tuple[str, str],
    feedback_count: int,
    engagement_count: int,
) -> str:
    return (
        f"{source} feedback score {feedback_score}; "
        f"{metric_names[0]}={feedback_count}, {metric_names[1]}={engagement_count}; "
        f"trend={trend_status}, recency={recency_status}."
    )


def write_outputs(rows: list[dict[str, Any]], output_dir: Path, top: int) -> None:
    (output_dir / "products.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(output_dir / "products.csv", REPORT_COLUMNS, rows)
    (output_dir / "products.md").write_text(markdown(rows, top), encoding="utf-8")


def markdown(rows: list[dict[str, Any]], top: int) -> str:
    source_counts: dict[str, int] = defaultdict(int)
    trend_counts: dict[str, int] = defaultdict(int)
    query_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"count": 0, "score": 0.0, "rising": 0, "fresh": 0})
    for row in rows:
        source_counts[row["source"]] += 1
        trend_counts[row["trend_status"]] += 1
        for query in [item.strip() for item in str(row.get("matched_queries", "")).split(",") if item.strip()]:
            query_stats[query]["count"] += 1
            query_stats[query]["score"] += float(row.get("feedback_score") or 0)
            if row.get("trend_status") == "rising":
                query_stats[query]["rising"] += 1
            if row.get("recency_status") in {"fresh", "recent"}:
                query_stats[query]["fresh"] += 1

    lines = [
        "# 产品反馈、评价与最近趋势",
        "",
        f"- 产品数：{len(rows)}",
        f"- 数据源：{', '.join(f'{source}({count})' for source, count in sorted(source_counts.items()))}",
        f"- 趋势分布：{dict(sorted(trend_counts.items()))}",
        "",
        "## 关键词趋势概览",
        "",
        "| 关键词 | 产品数 | 平均反馈分 | 上升产品 | 新鲜/近期产品 |",
        "|---|---:|---:|---:|---:|",
    ]
    for query, stat in sorted(query_stats.items(), key=lambda item: item[1]["score"], reverse=True):
        avg = round(stat["score"] / stat["count"], 1) if stat["count"] else 0
        lines.append(f"| {query} | {stat['count']} | {avg} | {stat['rising']} | {stat['fresh']} |")

    lines.extend(
        [
            "",
            "## 高反馈产品",
            "",
            "| 产品 | 来源 | 关键词 | 信号 | 购买意图 | 痛点 | 商业相关 | 反馈 | 互动 | 反馈分 | 评价 | 趋势 | 最近状态 |",
            "|---|---|---|---|---:|---:|---:|---:|---:|---:|---|---|---|",
        ]
    )
    for row in rows[:top]:
        lines.append(product_line(row))

    rising = [row for row in rows if row.get("trend_status") == "rising"]
    if rising:
        lines.extend(
            [
                "",
                "## 最近上升产品",
                "",
                "| 产品 | 来源 | 关键词 | 信号 | 商业相关 | 反馈 | 互动 | 增量 | 增幅 | 反馈分 |",
                "|---|---|---|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for row in rising[:top]:
            lines.append(
                "| {title} | {source} | {matched_queries} | {signal_type} | {commercial_relevance} | "
                "{feedback_count} | {engagement_count} | {trend_delta} | {trend_percent} | {feedback_score} |".format(**row)
            )

    weak = [row for row in rows if row.get("evaluation_level") in {"weak", "thin"}][:top]
    lines.extend(
        [
            "",
            "## 反馈较弱或需复核",
            "",
            "| 产品 | 来源 | 关键词 | 信号 | 商业相关 | 反馈分 | 评价 | 趋势 | 最近状态 |",
            "|---|---|---|---|---:|---:|---|---|---|",
        ]
    )
    for row in weak:
        lines.append(
            "| {title} | {source} | {matched_queries} | {signal_type} | {commercial_relevance} | {feedback_score} | "
            "{evaluation_level} | {trend_status} | {recency_status} |".format(**row)
        )

    lines.extend(
        [
            "",
            "## 口径",
            "",
            "- GitHub：反馈=stars，互动=forks。",
            "- Product Hunt：反馈=votes，互动=comments。",
            "- Hugging Face：反馈=likes，互动=downloads。",
            "- Hacker News：反馈=points，互动=comments。",
            "- Reddit：反馈=score，互动=comments。",
            "- 首次运行会建立 baseline；后续运行才会出现 rising/stable/falling。",
        ]
    )
    return "\n".join(lines) + "\n"


def product_line(row: dict[str, Any]) -> str:
    safe = dict(row)
    safe["title"] = str(row.get("title") or "").replace("|", "/")[:80]
    return (
        "| {title} | {source} | {matched_queries} | {signal_type} | {buyer_intent_score} | "
        "{pain_score} | {commercial_relevance} | {feedback_count} | {engagement_count} | "
        "{feedback_score} | {evaluation_level} | {trend_status} | {recency_status} |"
    ).format(**safe)


def update_history(history_path: Path, history: list[dict[str, str]], products: list[dict[str, str]]) -> None:
    current_records = [history_record(row) for row in products]
    current_keys = {(row["snapshot_date"], row["source"], row["product_id"], row["url"]) for row in current_records}
    kept = [
        row for row in history
        if (row.get("snapshot_date", ""), row.get("source", ""), row.get("product_id", ""), row.get("url", "")) not in current_keys
    ]
    write_csv(history_path, HISTORY_COLUMNS, kept + current_records)


def history_record(row: dict[str, str]) -> dict[str, Any]:
    return {
        "snapshot_date": row.get("collected_at", "") or datetime.now(timezone.utc).date().isoformat(),
        "source": row.get("source", ""),
        "product_id": row.get("product_id", ""),
        "title": row.get("title", ""),
        "url": row.get("url", ""),
        "feedback_count": parse_int(row.get("review_count")) or 0,
        "engagement_count": parse_int(row.get("sales_volume")) or 0,
        "rating": row.get("rating", ""),
        "last_updated": row.get("last_updated", ""),
    }


def query_key(source: str, identifier: str, url: str) -> tuple[str, str, str]:
    return (source.strip().lower(), identifier.strip().lower(), url.strip().lower())


def log_norm(value: int, maximum: int) -> float:
    if value <= 0 or maximum <= 0:
        return 0.0
    return max(0.0, min(1.0, math.log10(value + 1) / math.log10(maximum + 1)))


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def resolve(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


if __name__ == "__main__":
    raise SystemExit(main())
