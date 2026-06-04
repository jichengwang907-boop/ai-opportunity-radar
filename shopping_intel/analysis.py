from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from shopping_intel.config import source_names
from shopping_intel.models import Product, SearchResult


def analyze(
    config: dict[str, Any],
    search_results: list[SearchResult],
    products: list[Product],
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    analysis_config = config.get("analysis") or {}
    stale_product_days = int(analysis_config.get("stale_product_days") or 90)
    stale_search_days = int(analysis_config.get("stale_search_days") or 14)
    require_price = bool(analysis_config.get("require_price", True))
    top_n = int(analysis_config.get("top_n") or 20)
    source_quality = analysis_config.get("source_quality") or {}

    queries = config.get("queries") or []
    configured_query_terms = {str(query.get("term") or "").strip() for query in queries}
    observed_query_terms = {result.query for result in search_results if result.query}
    query_count = len({term for term in configured_query_terms | observed_query_terms if term})
    expected_sources = source_names(config)

    search_summary, search_anomalies = _analyze_search(
        queries=queries,
        expected_sources=expected_sources,
        results=search_results,
        now=now,
        stale_search_days=stale_search_days,
        top_n=top_n,
        source_quality=source_quality,
    )
    product_summary, product_anomalies = _analyze_products(
        products=products,
        now=now,
        stale_product_days=stale_product_days,
        require_price=require_price,
    )

    anomalies = search_anomalies + product_anomalies
    severity_counts = defaultdict(int)
    for anomaly in anomalies:
        severity_counts[anomaly["severity"]] += 1

    return {
        "generated_at": now.isoformat(),
        "summary": {
            "sources": expected_sources,
            "query_count": query_count,
            "search_result_rows": len(search_results),
            "product_rows": len(products),
            "anomaly_count": len(anomalies),
            "severity_counts": dict(sorted(severity_counts.items())),
        },
        "search_summary": search_summary,
        "product_summary": product_summary,
        "anomalies": anomalies,
    }


def _analyze_search(
    queries: list[dict[str, Any]],
    expected_sources: list[str],
    results: list[SearchResult],
    now: datetime,
    stale_search_days: int,
    top_n: int,
    source_quality: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[SearchResult]] = defaultdict(list)
    for result in results:
        grouped[(result.query, result.source)].append(result)

    summary: list[dict[str, Any]] = []
    anomalies: list[dict[str, Any]] = []
    configured_terms = {str(query.get("term") or "").strip() for query in queries}
    observed_terms = {term for (term, _) in grouped if term}
    all_queries = list(queries) + [{"term": term} for term in sorted(observed_terms - configured_terms)]

    for query_config in all_queries:
        query = str(query_config.get("term") or "").strip()
        if not query:
            continue
        observed_sources = sorted({source for (term, source) in grouped if term == query})
        sources = sorted(set(expected_sources) | set(observed_sources))
        if not sources:
            sources = ["unconfigured"]

        for source in sources:
            rows = sorted(
                grouped.get((query, source), []),
                key=lambda item: item.rank if item.rank is not None else 999999,
            )
            metrics = _search_metrics(query_config, rows, now, stale_search_days, top_n)
            summary.append({"query": query, "source": source, **metrics})
            anomalies.extend(_search_anomalies(query_config, source, metrics, source_quality or {}))

    return summary, anomalies


def _search_metrics(
    query_config: dict[str, Any],
    rows: list[SearchResult],
    now: datetime,
    stale_search_days: int,
    top_n: int,
) -> dict[str, Any]:
    expected_terms = _terms(query_config.get("expected_terms")) or [str(query_config.get("term") or "")]
    forbidden_terms = _terms(query_config.get("forbidden_terms"))
    min_item_relevance = float(query_config.get("min_item_relevance") or 0.34)
    top_rows = rows[:top_n]

    relevance_scores = [_relevance_score(row, expected_terms) for row in top_rows]
    relevant_count = sum(1 for score in relevance_scores if score >= min_item_relevance)
    avg_relevance = round(sum(relevance_scores) / len(relevance_scores), 4) if relevance_scores else 0
    result_count = max((row.result_count or 0 for row in rows), default=0)
    if result_count == 0:
        result_count = len(rows)
    search_volume = query_config.get("search_volume")
    if search_volume in (None, ""):
        search_volume = max((row.search_volume or 0 for row in rows), default=0)

    forbidden_hits = [
        {
            "title": row.title,
            "rank": row.rank,
            "terms": _matched_terms(f"{row.title} {row.snippet}", forbidden_terms),
        }
        for row in top_rows
        if _matched_terms(f"{row.title} {row.snippet}", forbidden_terms)
    ]

    oldest_collected_at = min((row.collected_at for row in rows if row.collected_at), default=None)
    newest_collected_at = max((row.collected_at for row in rows if row.collected_at), default=None)
    data_age_days = _age_days(newest_collected_at, now) if newest_collected_at else None
    signal_metrics = _search_signal_metrics(top_rows)

    return {
        "observed_rows": len(rows),
        "result_count": result_count,
        "search_volume": int(search_volume or 0),
        "top_n": top_n,
        "relevant_top_results": relevant_count,
        "avg_relevance": avg_relevance,
        "forbidden_hit_count": len(forbidden_hits),
        "forbidden_hits": forbidden_hits[:5],
        "oldest_collected_at": oldest_collected_at.isoformat() if oldest_collected_at else "",
        "newest_collected_at": newest_collected_at.isoformat() if newest_collected_at else "",
        "data_age_days": data_age_days,
        "stale_search_days": stale_search_days,
        **signal_metrics,
    }


def _search_anomalies(
    query_config: dict[str, Any],
    source: str,
    metrics: dict[str, Any],
    source_quality: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    query = str(query_config.get("term") or "").strip()
    quality = _source_quality(source, source_quality or {})
    if metrics["observed_rows"] == 0 and quality.get("ignore_empty", False):
        return []

    min_result_count = _quality_int(quality, "min_result_count", int(query_config.get("min_result_count") or 1))
    min_relevant_results = _quality_int(quality, "min_relevant_results", int(query_config.get("min_relevant_results") or 1))
    min_avg_relevance = _quality_float(quality, "min_avg_relevance", float(query_config.get("min_avg_relevance") or 0.35))

    failures: list[str] = []
    if metrics["observed_rows"] == 0:
        failures.append("没有采集到该关键词的搜索结果")
    if metrics["result_count"] < min_result_count:
        failures.append(f"结果量 {metrics['result_count']} 低于预期 {min_result_count}")
    if metrics["relevant_top_results"] < min_relevant_results:
        failures.append(f"Top 结果相关数 {metrics['relevant_top_results']} 低于预期 {min_relevant_results}")
    if metrics["avg_relevance"] < min_avg_relevance:
        failures.append(f"平均相关度 {metrics['avg_relevance']} 低于阈值 {min_avg_relevance}")
    if metrics["forbidden_hit_count"]:
        failures.append(f"出现 {metrics['forbidden_hit_count']} 条排除词命中")
    if metrics["data_age_days"] is None:
        failures.append("没有采集时间，无法判断搜索数据新鲜度")
    elif metrics["data_age_days"] > metrics["stale_search_days"]:
        failures.append(f"搜索数据已 {metrics['data_age_days']} 天未刷新")

    if not failures:
        return []

    if metrics["observed_rows"] == 0:
        severity = str(quality.get("empty_severity") or "high")
    else:
        severity = "high" if len(failures) >= 3 else "medium"
    return [
        {
            "type": "search_underperforming",
            "severity": severity,
            "source": source,
            "query": query,
            "product_id": "",
            "title": "",
            "message": "；".join(failures),
            "metrics": metrics,
        }
    ]


def _source_quality(source: str, source_quality: dict[str, Any]) -> dict[str, Any]:
    by_source = source_quality.get("by_source") or {}
    defaults = source_quality.get("default") or {}
    quality = dict(defaults)
    quality.update(by_source.get(source) or {})
    return quality


def _quality_int(quality: dict[str, Any], key: str, fallback: int) -> int:
    value = quality.get(key)
    if value in (None, ""):
        return fallback
    return int(value)


def _quality_float(quality: dict[str, Any], key: str, fallback: float) -> float:
    value = quality.get(key)
    if value in (None, ""):
        return fallback
    return float(value)


def _analyze_products(
    products: list[Product],
    now: datetime,
    stale_product_days: int,
    require_price: bool = True,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    by_source: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    anomalies: list[dict[str, Any]] = []

    for product in products:
        by_source[product.source]["total"] += 1
        issues = _product_issues(product, now, stale_product_days, require_price=require_price)
        if issues:
            by_source[product.source]["with_issues"] += 1
            if any(issue["code"] == "stale_product" for issue in issues):
                by_source[product.source]["stale"] += 1
            severity = _product_severity(issues)
            anomalies.append(
                {
                    "type": "product_stale_or_incomplete",
                    "severity": severity,
                    "source": product.source,
                    "query": "",
                    "product_id": product.product_id,
                    "title": product.title,
                    "message": "；".join(issue["message"] for issue in issues),
                    "metrics": {
                        "last_updated": product.last_updated.isoformat() if product.last_updated else "",
                        "collected_at": product.collected_at.isoformat() if product.collected_at else "",
                        "stale_product_days": stale_product_days,
                        "price": product.price,
                        "stock_status": product.stock_status,
                    },
                }
            )

    return {source: dict(counts) for source, counts in by_source.items()}, anomalies


def _product_issues(
    product: Product,
    now: datetime,
    stale_product_days: int,
    require_price: bool = True,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if not product.product_id:
        issues.append({"code": "missing_id", "message": "缺少商品 ID"})
    if not product.title:
        issues.append({"code": "missing_title", "message": "缺少商品标题"})
    if not product.url:
        issues.append({"code": "missing_url", "message": "缺少商品链接"})
    if require_price and product.price is None:
        issues.append({"code": "missing_price", "message": "缺少价格"})

    if product.last_updated is None:
        issues.append({"code": "missing_last_updated", "message": "缺少最后更新时间"})
    else:
        age = _age_days(product.last_updated, now)
        if age > stale_product_days:
            issues.append({"code": "stale_product", "message": f"商品已 {age} 天未更新"})

    stock = product.stock_status.lower()
    if any(word in stock for word in ("out of stock", "sold out", "unavailable", "下架", "无货", "售罄")):
        issues.append({"code": "unavailable", "message": f"库存状态异常：{product.stock_status}"})

    return issues


def _product_severity(issues: list[dict[str, str]]) -> str:
    codes = {issue["code"] for issue in issues}
    if "stale_product" in codes or "missing_title" in codes or "missing_url" in codes:
        return "high"
    if "missing_last_updated" in codes or "missing_price" in codes:
        return "medium"
    return "low"


def _terms(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    return [str(item).strip() for item in value if str(item).strip()]


def _relevance_score(result: SearchResult, expected_terms: list[str]) -> float:
    haystack = f"{result.title} {result.snippet}".lower()
    if not expected_terms:
        return 0
    matches = sum(1 for term in expected_terms if term.lower() in haystack)
    return matches / len(expected_terms)


def _matched_terms(text: str, terms: list[str]) -> list[str]:
    lowered = text.lower()
    return [term for term in terms if term.lower() in lowered]


def _search_signal_metrics(rows: list[SearchResult]) -> dict[str, Any]:
    signal_type_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        if row.signal_type:
            signal_type_counts[row.signal_type] += 1

    return {
        "signal_type": _dominant_signal_type(signal_type_counts),
        "signal_type_counts": dict(sorted(signal_type_counts.items())),
        "buyer_intent_score": _average_optional_int(row.buyer_intent_score for row in rows),
        "pain_score": _average_optional_int(row.pain_score for row in rows),
        "source_confidence": _average_optional_int(row.source_confidence for row in rows),
        "commercial_relevance": _average_optional_int(row.commercial_relevance for row in rows),
    }


def _dominant_signal_type(counts: dict[str, int]) -> str:
    if not counts:
        return ""
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _average_optional_int(values: Any) -> float:
    present = [int(value) for value in values if value is not None]
    return round(sum(present) / len(present), 1) if present else 0.0


def _age_days(value: datetime, now: datetime) -> int:
    value = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return max(0, (now - value).days)
