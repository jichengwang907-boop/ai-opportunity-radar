from __future__ import annotations

from collections import defaultdict
import csv
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from shopping_intel.models import parse_datetime, parse_float, parse_int


SOURCE_WEIGHTS = {
    "github": "developer_supply",
    "github_issues": "user_feedback",
    "arxiv": "research_momentum",
    "huggingface_models": "model_supply",
    "huggingface_spaces": "prototype_supply",
    "hackernews": "developer_discussion",
    "reddit": "user_discussion",
    "google_news": "market_attention",
    "ai_dev_jobs": "hiring_demand",
    "agentic_engineering_jobs": "hiring_demand",
    "agentdeals": "developer_tool_market",
    "oksurf_news": "market_attention",
    "api_status_check": "service_reliability",
    "internet_archive": "historical_content",
    "nvd": "security_risk",
    "devitjobs": "hiring_demand",
    "predscope": "market_expectation",
    "patentsview": "patent_momentum",
    "domainsdb": "startup_activity",
    "youtube": "content_attention",
    "x_recent": "social_attention",
    "producthunt": "product_supply",
    "google_trends": "search_interest",
    "google_ads": "keyword_demand",
    "g2": "b2b_review",
    "capterra": "b2b_review",
    "alternative_to": "alternatives",
    "chrome_web_store": "marketplace_review",
    "slack_marketplace": "marketplace_review",
    "shopify_marketplace": "marketplace_review",
    "app_store": "app_review",
    "google_play": "app_review",
    "amazon": "ecommerce",
    "taobao": "ecommerce",
    "tmall": "ecommerce",
    "jd": "ecommerce",
    "jingdong": "ecommerce",
}

CORE_CONFIDENCE_SOURCES = (
    "github",
    "github_issues",
    "producthunt",
    "arxiv",
    "huggingface_models",
    "huggingface_spaces",
    "hackernews",
    "reddit",
    "google_news",
    "ai_dev_jobs",
    "agentic_engineering_jobs",
    "agentdeals",
    "oksurf_news",
    "google_trends",
    "google_ads",
    "g2",
    "capterra",
    "chrome_web_store",
    "shopify_marketplace",
    "app_store",
    "google_play",
    "amazon",
)

HARDWARE_TERMS = ("glasses", "recorder", "earbuds", "camera", "device", "hardware")
ENTERPRISE_TERMS = ("agent", "local llm", "search", "coding", "meeting")
TREND_WINDOWS = (7, 30)
PAID_PROOF_SOURCES = (
    "google_ads",
    "g2",
    "capterra",
    "app_store",
    "google_play",
    "amazon",
    "taobao",
    "tmall",
    "jd",
    "jingdong",
)
COMMERCIAL_PROXY_SOURCES = PAID_PROOF_SOURCES + (
    "producthunt",
    "agentdeals",
    "ai_dev_jobs",
    "agentic_engineering_jobs",
    "youtube",
    "x_recent",
)

HISTORY_COLUMNS = [
    "snapshot_date",
    "query",
    "rank",
    "score",
    "grade",
    "buyer_intent",
    "pain_signal",
    "commercial_relevance",
    "market_size_growth",
    "competition_attractiveness",
    "execution_feasibility",
    "commercial_gap",
    "confidence",
    "decision_score",
    "decision_tier",
    "evidence_level",
    "result_total",
    "top_sources",
]


def score_opportunities(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    rows = analysis.get("search_summary") or []
    by_query = _group_by_query(rows)
    source_max = _source_maxima(rows)

    scored = []
    for query, source_rows in sorted(by_query.items()):
        counts = {
            source: int((source_rows.get(source) or {}).get("result_count") or 0)
            for source in SOURCE_WEIGHTS
        }
        relevance = _average_relevance(source_rows)
        normalized = {
            source: _log_norm(count, source_max.get(source, 0))
            for source, count in counts.items()
        }

        technical_supply = _clamp(
            normalized["github"] * 0.40
            + normalized["huggingface_models"] * 0.16
            + normalized["huggingface_spaces"] * 0.15
            + normalized["arxiv"] * 0.15
            + normalized["patentsview"] * 0.10
            + normalized["nvd"] * 0.04
        )
        community_demand = _clamp(
            normalized["hackernews"] * 0.17
            + normalized["reddit"] * 0.14
            + normalized["github_issues"] * 0.14
            + normalized["ai_dev_jobs"] * 0.12
            + normalized["agentic_engineering_jobs"] * 0.13
            + normalized["devitjobs"] * 0.06
            + normalized["x_recent"] * 0.07
            + normalized["producthunt"] * 0.07
            + normalized["github"] * 0.10
        )
        market_attention = _clamp(
            normalized["google_news"] * 0.26
            + normalized["oksurf_news"] * 0.16
            + normalized["youtube"] * 0.12
            + normalized["producthunt"] * 0.14
            + normalized["domainsdb"] * 0.12
            + normalized["agentdeals"] * 0.10
            + normalized["internet_archive"] * 0.05
            + normalized["predscope"] * 0.05
        )
        product_crowding = _clamp(
            normalized["producthunt"] * 0.38
            + normalized["g2"] * 0.10
            + normalized["capterra"] * 0.10
            + normalized["alternative_to"] * 0.07
            + normalized["chrome_web_store"] * 0.07
            + normalized["slack_marketplace"] * 0.05
            + normalized["shopify_marketplace"] * 0.06
            + normalized["app_store"] * 0.06
            + normalized["google_play"] * 0.06
            + normalized["amazon"] * 0.03
            + max(normalized["taobao"], normalized["tmall"], normalized["jd"], normalized["jingdong"]) * 0.02
        )
        research_momentum = _clamp(normalized["arxiv"] * 0.75 + normalized["patentsview"] * 0.25)
        developer_tool_market = _clamp(normalized["agentdeals"] * 0.55 + normalized["api_status_check"] * 0.25 + normalized["nvd"] * 0.20)
        buyer_intent = _average_signal_score(source_rows, "buyer_intent_score")
        if buyer_intent == 0:
            buyer_intent = _clamp(
                normalized["ai_dev_jobs"] * 0.30
                + normalized["agentic_engineering_jobs"] * 0.30
                + normalized["google_ads"] * 0.14
                + normalized["producthunt"] * 0.10
                + normalized["agentdeals"] * 0.08
                + normalized["g2"] * 0.04
                + normalized["capterra"] * 0.04
            )
        pain_signal = _average_signal_score(source_rows, "pain_score")
        if pain_signal == 0:
            pain_signal = _clamp(
                normalized["github_issues"] * 0.34
                + normalized["reddit"] * 0.24
                + normalized["hackernews"] * 0.14
                + normalized["api_status_check"] * 0.14
                + normalized["nvd"] * 0.14
            )
        commercial_relevance = _average_signal_score(source_rows, "commercial_relevance")
        if commercial_relevance == 0:
            commercial_relevance = _clamp(
                buyer_intent * 0.45
                + pain_signal * 0.20
                + normalized["producthunt"] * 0.16
                + normalized["agentdeals"] * 0.10
                + normalized["domainsdb"] * 0.09
            )
        signal_confidence = _average_signal_score(source_rows, "source_confidence")
        commercial_gap = _clamp(
            ((technical_supply + community_demand) / 2)
            + developer_tool_market * 0.12
            - product_crowding * 0.55
        )
        personal_fit = _personal_fit(query)
        confidence = _clamp(max(_confidence(counts, relevance), signal_confidence))
        search_demand = _clamp(
            normalized["google_trends"] * 0.45
            + normalized["google_ads"] * 0.45
            + normalized["youtube"] * 0.10
        )
        if search_demand > 0:
            market_size_growth = _clamp(
                search_demand * 0.55
                + market_attention * 0.20
                + community_demand * 0.15
                + buyer_intent * 0.10
            )
        else:
            market_size_growth = _clamp(
                market_attention * 0.35
                + community_demand * 0.35
                + buyer_intent * 0.20
                + research_momentum * 0.10
            )
        competition_attractiveness = _clamp(
            1
            - product_crowding * 0.65
            - market_attention * 0.10
            + commercial_gap * 0.18
            + pain_signal * 0.07
        )
        execution_feasibility = _clamp(
            personal_fit * 0.55
            + technical_supply * 0.22
            + confidence * 0.13
            + commercial_gap * 0.10
        )

        score = round(
            100
            * _clamp(
                buyer_intent * 0.25
                + pain_signal * 0.20
                + market_size_growth * 0.15
                + competition_attractiveness * 0.15
                + confidence * 0.10
                + execution_feasibility * 0.10
                + commercial_gap * 0.05
            ),
            1,
        )
        commercial_proof = _commercial_proof(normalized)
        user_pain_evidence = _user_pain_evidence(normalized)
        decision_score = _decision_score(
            buyer_intent=buyer_intent,
            pain_signal=pain_signal,
            commercial_relevance=commercial_relevance,
            confidence=confidence,
            execution_feasibility=execution_feasibility,
            commercial_gap=commercial_gap,
            commercial_proof=commercial_proof,
            user_pain_evidence=user_pain_evidence,
        )
        decision_tier = _decision_tier(
            decision_score=decision_score,
            buyer_intent=buyer_intent,
            pain_signal=pain_signal,
            confidence=confidence,
            commercial_proof=commercial_proof,
            personal_fit=personal_fit,
        )
        evidence_level = _evidence_level(counts, commercial_proof, confidence)
        validation_gaps = _validation_gaps(
            query=query,
            counts=counts,
            buyer_intent=buyer_intent,
            pain_signal=pain_signal,
            confidence=confidence,
            commercial_proof=commercial_proof,
            personal_fit=personal_fit,
            product_crowding=product_crowding,
        )

        scored.append(
            {
                "query": query,
                "score": score,
                "grade": _grade(score),
                "decision_score": decision_score,
                "decision_tier": decision_tier,
                "evidence_level": evidence_level,
                "commercial_proof": round(commercial_proof, 3),
                "user_pain_evidence": round(user_pain_evidence, 3),
                "technical_supply": round(technical_supply, 3),
                "community_demand": round(community_demand, 3),
                "market_attention": round(market_attention, 3),
                "product_crowding": round(product_crowding, 3),
                "commercial_gap": round(commercial_gap, 3),
                "buyer_intent": round(buyer_intent, 3),
                "pain_signal": round(pain_signal, 3),
                "commercial_relevance": round(commercial_relevance, 3),
                "market_size_growth": round(market_size_growth, 3),
                "competition_attractiveness": round(competition_attractiveness, 3),
                "execution_feasibility": round(execution_feasibility, 3),
                "research_momentum": round(research_momentum, 3),
                "personal_fit": round(personal_fit, 3),
                "confidence": round(confidence, 3),
                "counts": counts,
                "recommendation": _recommendation(query, score, product_crowding, commercial_gap, personal_fit),
                "why": _why(
                    query,
                    counts,
                    technical_supply,
                    community_demand,
                    market_attention,
                    product_crowding,
                    commercial_gap,
                    personal_fit,
                    buyer_intent,
                    pain_signal,
                    commercial_relevance,
                    market_size_growth,
                    competition_attractiveness,
                    execution_feasibility,
                ),
                "risks": _risks(query, counts, product_crowding, personal_fit, confidence, buyer_intent),
                "next_action": _next_action(query, score, product_crowding, commercial_gap, personal_fit),
                "validation_gaps": validation_gaps,
                "validation_test": _validation_test(query, decision_tier, validation_gaps),
            }
        )

    ranked = sorted(scored, key=lambda item: item["score"], reverse=True)
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return ranked


def write_opportunity_reports(opportunities: list[dict[str, Any]], output_dir: str | Path) -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "opportunities.json"
    csv_path = out / "opportunities.csv"
    markdown_path = out / "opportunities.md"

    json_path.write_text(json.dumps(opportunities, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_csv(opportunities, csv_path)
    markdown_path.write_text(_markdown(opportunities), encoding="utf-8")

    return {"json": json_path, "csv": csv_path, "markdown": markdown_path}


def snapshot_date_from_analysis(analysis: dict[str, Any]) -> str:
    generated_at = parse_datetime(analysis.get("generated_at"))
    snapshot = generated_at or datetime.now(timezone.utc)
    return snapshot.date().isoformat()


def read_opportunity_history(path: str | Path) -> list[dict[str, str]]:
    history_path = Path(path)
    if not history_path.exists():
        return []
    with history_path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def apply_opportunity_trends(
    opportunities: list[dict[str, Any]],
    history: list[dict[str, str]],
    snapshot_date: str,
) -> list[dict[str, Any]]:
    current_date = _parse_snapshot_date(snapshot_date) or datetime.now(timezone.utc).date()
    history_by_query = _history_by_query(history)

    for index, item in enumerate(opportunities, start=1):
        item["rank"] = int(item.get("rank") or index)
        query_history = history_by_query.get(str(item.get("query") or ""), [])
        for days in TREND_WINDOWS:
            baseline = _baseline_for_window(query_history, current_date, days)
            _attach_trend_window(item, baseline, days)
        item["trend_status"] = _trend_status(item)

    return opportunities


def update_opportunity_history(
    path: str | Path,
    history: list[dict[str, str]],
    opportunities: list[dict[str, Any]],
    snapshot_date: str,
) -> None:
    history_path = Path(path)
    current_records = [_history_record(item, snapshot_date) for item in opportunities]
    current_keys = {(row["snapshot_date"], row["query"]) for row in current_records}
    kept = [
        row for row in history
        if (row.get("snapshot_date", ""), row.get("query", "")) not in current_keys
    ]
    _write_history_csv(history_path, kept + current_records)


def _group_by_query(rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    for row in rows:
        query = str(row.get("query") or "").strip()
        source = str(row.get("source") or "").strip()
        if not query or not source:
            continue
        grouped.setdefault(query, {})[source] = row
    return grouped


def _source_maxima(rows: list[dict[str, Any]]) -> dict[str, int]:
    maxima = {source: 0 for source in SOURCE_WEIGHTS}
    for row in rows:
        source = str(row.get("source") or "")
        if source in maxima:
            maxima[source] = max(maxima[source], int(row.get("result_count") or 0))
    return maxima


def _average_relevance(source_rows: dict[str, dict[str, Any]]) -> float:
    values = [
        float(row.get("avg_relevance") or 0)
        for row in source_rows.values()
        if row.get("observed_rows")
    ]
    return sum(values) / len(values) if values else 0


def _average_signal_score(source_rows: dict[str, dict[str, Any]], field: str) -> float:
    values = [
        float(row.get(field) or 0) / 100
        for row in source_rows.values()
        if row.get("observed_rows") and row.get(field) not in (None, "")
    ]
    return _clamp(sum(values) / len(values)) if values else 0


def _log_norm(value: int, maximum: int) -> float:
    if value <= 0 or maximum <= 0:
        return 0
    return _clamp(math.log10(value + 1) / math.log10(maximum + 1))


def _personal_fit(query: str) -> float:
    lowered = query.lower()
    fit = 0.72
    if any(term in lowered for term in ENTERPRISE_TERMS):
        fit += 0.14
    if any(term in lowered for term in HARDWARE_TERMS):
        fit -= 0.28
    if "coding assistant" in lowered:
        fit -= 0.10
    if "local llm" in lowered:
        fit += 0.08
    return _clamp(fit)


def _confidence(counts: dict[str, int], relevance: float) -> float:
    non_zero_sources = sum(1 for source in CORE_CONFIDENCE_SOURCES if counts.get(source, 0) > 0)
    source_coverage = non_zero_sources / len(CORE_CONFIDENCE_SOURCES)
    return _clamp(source_coverage * 0.65 + relevance * 0.35)


def _grade(score: float) -> str:
    if score >= 78:
        return "A"
    if score >= 66:
        return "B"
    if score >= 52:
        return "C"
    return "D"


def _commercial_proof(normalized: dict[str, float]) -> float:
    paid_market = max(normalized[source] for source in PAID_PROOF_SOURCES)
    hiring = max(normalized["ai_dev_jobs"], normalized["agentic_engineering_jobs"])
    social_content = max(normalized["youtube"], normalized["x_recent"])
    return _clamp(
        paid_market * 0.42
        + normalized["producthunt"] * 0.16
        + normalized["agentdeals"] * 0.14
        + hiring * 0.22
        + social_content * 0.06
    )


def _user_pain_evidence(normalized: dict[str, float]) -> float:
    return _clamp(
        normalized["github_issues"] * 0.35
        + normalized["reddit"] * 0.22
        + normalized["hackernews"] * 0.20
        + normalized["api_status_check"] * 0.11
        + normalized["nvd"] * 0.12
    )


def _decision_score(
    *,
    buyer_intent: float,
    pain_signal: float,
    commercial_relevance: float,
    confidence: float,
    execution_feasibility: float,
    commercial_gap: float,
    commercial_proof: float,
    user_pain_evidence: float,
) -> float:
    return round(
        100
        * _clamp(
            buyer_intent * 0.22
            + pain_signal * 0.18
            + commercial_relevance * 0.16
            + confidence * 0.14
            + execution_feasibility * 0.12
            + commercial_gap * 0.08
            + commercial_proof * 0.06
            + user_pain_evidence * 0.04
        ),
        1,
    )


def _decision_tier(
    *,
    decision_score: float,
    buyer_intent: float,
    pain_signal: float,
    confidence: float,
    commercial_proof: float,
    personal_fit: float,
) -> str:
    if personal_fit < 0.55:
        return "暂缓投入"
    if (
        decision_score >= 68
        and buyer_intent >= 0.58
        and pain_signal >= 0.52
        and confidence >= 0.70
        and commercial_proof >= 0.25
    ):
        return "优先付费验证"
    if (
        decision_score >= 60
        and buyer_intent >= 0.50
        and confidence >= 0.68
        and (pain_signal >= 0.48 or commercial_proof >= 0.35)
    ):
        return "轻量付费验证"
    if decision_score >= 54 and confidence >= 0.60:
        return "补证据后验证"
    return "继续观察"


def _evidence_level(counts: dict[str, int], commercial_proof: float, confidence: float) -> str:
    if any(counts.get(source, 0) > 0 for source in PAID_PROOF_SOURCES):
        return "付费代理证据"
    if commercial_proof >= 0.35:
        return "商业代理证据"
    if confidence >= 0.70:
        return "多源公开信号"
    return "弱代理信号"


def _validation_gaps(
    *,
    query: str,
    counts: dict[str, int],
    buyer_intent: float,
    pain_signal: float,
    confidence: float,
    commercial_proof: float,
    personal_fit: float,
    product_crowding: float,
) -> list[str]:
    gaps = []
    if not any(counts.get(source, 0) > 0 for source in PAID_PROOF_SOURCES):
        gaps.append("缺少关键词广告、B2B 评论、应用市场或电商成交类数据。")
    if commercial_proof < 0.25:
        gaps.append("商业代理证据偏弱，需要补价格、评论、竞品或内容需求信号。")
    if buyer_intent < 0.55:
        gaps.append("购买意图未过强验证线，不能只靠热度判断。")
    if pain_signal < 0.50:
        gaps.append("痛点信号不足，需要用户访谈、差评或 issue 样本确认。")
    if confidence < 0.70:
        gaps.append("多源可信度不足，建议补 Google Trends/Ads、G2/Capterra 或垂直社区。")
    if counts["producthunt"] <= 2:
        gaps.append("产品化样本少，可能是机会，也可能是需求尚未成立。")
    if product_crowding >= 0.70:
        gaps.append("产品拥挤度高，需要先切垂直场景再验证。")
    if personal_fit < 0.55:
        gaps.append("个人或小团队执行门槛偏高。")
    if "coding assistant" in query.lower():
        gaps.append("通用代码助手竞争强，验证必须避开大厂正面战场。")
    return gaps or ["暂无硬性证据缺口；下一步要验证真实付费，而不是继续堆代理信号。"]


def _validation_test(query: str, decision_tier: str, validation_gaps: list[str]) -> str:
    lowered = query.lower()
    if decision_tier == "优先付费验证":
        return "7 天内做付费落地页、明确价格和一个可交付样例，目标是拿到 2 个预约或预付费信号。"
    if decision_tier == "轻量付费验证":
        return "先做 1 页落地页和 5 次目标用户访谈，把价格问题提前问出来。"
    if decision_tier == "补证据后验证":
        if validation_gaps:
            return f"先补最关键证据：{validation_gaps[0]}"
        return "先补真实需求证据，再决定是否做付费验证。"
    if "glasses" in lowered or "recorder" in lowered:
        return "先做市场跟踪或内容页，不建议进入硬件/供应链验证。"
    return "保留在监控列表，等待趋势、付费或痛点信号增强。"


def _recommendation(
    query: str,
    score: float,
    product_crowding: float,
    commercial_gap: float,
    personal_fit: float,
) -> str:
    if personal_fit < 0.55:
        return "谨慎：更适合做情报跟踪或内容选题，不建议个人直接重资产切入。"
    if score >= 72 and commercial_gap >= 0.35:
        return "优先验证：技术、讨论和市场关注都足够，产品化空间仍在。"
    if product_crowding >= 0.75:
        return "做细分：市场已有产品，避开通用方案，找行业垂直切口。"
    if score >= 58:
        return "轻量测试：适合做模板、报告、插件或服务型 MVP。"
    return "观察：先持续监控，不急着投入开发。"


def _why(
    query: str,
    counts: dict[str, int],
    technical_supply: float,
    community_demand: float,
    market_attention: float,
    product_crowding: float,
    commercial_gap: float,
    personal_fit: float,
    buyer_intent: float,
    pain_signal: float,
    commercial_relevance: float,
    market_size_growth: float,
    competition_attractiveness: float,
    execution_feasibility: float,
) -> list[str]:
    reasons = [
        f"GitHub 命中 {counts['github']}，PatentsView 命中 {counts['patentsview']}，NVD 命中 {counts['nvd']}，开发者/专利/安全供给信号为 {technical_supply:.2f}。",
        f"Hacker News 命中 {counts['hackernews']}，Reddit 命中 {counts['reddit']}，GitHub Issues 命中 {counts['github_issues']}，AI Dev Jobs 命中 {counts['ai_dev_jobs']}，Agentic Engineering Jobs 命中 {counts['agentic_engineering_jobs']}，社区/招聘需求信号为 {community_demand:.2f}。",
        f"Google News 命中 {counts['google_news']}，OkSurf 命中 {counts['oksurf_news']}，AgentDeals 命中 {counts['agentdeals']}，API Status Check 命中 {counts['api_status_check']}，市场关注和工具生态信号为 {market_attention:.2f}。",
        f"Product Hunt 命中 {counts['producthunt']}，产品拥挤度为 {product_crowding:.2f}。",
        f"购买意图为 {buyer_intent:.2f}，痛点信号为 {pain_signal:.2f}，商业相关性为 {commercial_relevance:.2f}。",
        f"Google Trends 指数 {counts['google_trends']}，Google Ads 命中 {counts['google_ads']}，市场规模/增长代理分为 {market_size_growth:.2f}，竞争吸引力为 {competition_attractiveness:.2f}，执行可行性为 {execution_feasibility:.2f}。",
    ]
    if commercial_gap >= 0.35:
        reasons.append("技术/讨论热度高于产品化拥挤度，存在商业化缺口。")
    if personal_fit >= 0.75:
        reasons.append("更偏软件、服务或模板，个人和小团队可执行性较好。")
    if any(term in query.lower() for term in HARDWARE_TERMS):
        reasons.append("包含硬件/设备属性，供应链和售后会拉高执行难度。")
    return reasons


def _risks(
    query: str,
    counts: dict[str, int],
    product_crowding: float,
    personal_fit: float,
    confidence: float,
    buyer_intent: float,
) -> list[str]:
    risks = []
    if buyer_intent < 0.35:
        risks.append("购买意图信号偏弱，需要补 G2/Capterra、应用商店、关键词广告或真实价格/评论数据再判断。")
    if product_crowding >= 0.7:
        risks.append("Product Hunt 产品信号较强，通用产品可能已经拥挤。")
    if counts["producthunt"] <= 2:
        risks.append("Product Hunt 产品少，可能是机会，也可能是付费需求弱。")
    if counts["reddit"] <= 2 and counts["hackernews"] <= 10:
        risks.append("真实用户讨论信号偏弱，需要补用户访谈。")
    if personal_fit < 0.55:
        risks.append("个人执行难度偏高，需要供应链、渠道或行业资源。")
    if confidence < 0.55:
        risks.append("多源覆盖不足，需要补 Google Trends、广告后台或真实用户访谈。")
    if "coding assistant" in query.lower():
        risks.append("代码助手赛道强敌多，避免与 Cursor、Copilot、Claude Code 正面对打。")
    return risks or ["主要风险是数据只能说明信号强弱，不能直接证明收入。"]


def _next_action(
    query: str,
    score: float,
    product_crowding: float,
    commercial_gap: float,
    personal_fit: float,
) -> str:
    lowered = query.lower()
    if personal_fit < 0.55:
        return "先做市场跟踪页和案例内容，不建议马上做实体产品。"
    if "local llm" in lowered:
        return "做一个本地 LLM 私有部署/知识库/自动化模板包，先找 5 个小团队访谈。"
    if "agent" in lowered:
        return "选一个具体行业场景做 Agent 模板，例如电商选品、销售线索或客服质检。"
    if "search" in lowered:
        return "做垂直搜索，不做通用搜索；优先切 AI 工具、竞品、论文或供应商搜索。"
    if "meeting" in lowered:
        return "避开通用会议纪要，切行业工作流：销售复盘、招聘面试、法务会议。"
    if score >= 60 and commercial_gap >= 0.25:
        return "做 1 页落地页 + 1 个可交付样例，用 7 天验证是否有人愿意付费。"
    if product_crowding >= 0.7:
        return "先拆前 10 个竞品差评，找一个痛点做微创新。"
    return "继续监控 2-4 周，等待更明确的用户需求信号。"


def _write_csv(opportunities: list[dict[str, Any]], path: Path) -> None:
    columns = [
        "rank",
        "query",
        "score",
        "grade",
        "decision_score",
        "decision_tier",
        "evidence_level",
        "trend_status",
        "score_7d_ago",
        "score_delta_7d",
        "rank_7d_ago",
        "rank_delta_7d",
        "comparison_date_7d",
        "score_30d_ago",
        "score_delta_30d",
        "rank_30d_ago",
        "rank_delta_30d",
        "comparison_date_30d",
        "technical_supply",
        "community_demand",
        "market_attention",
        "product_crowding",
        "commercial_gap",
        "commercial_proof",
        "user_pain_evidence",
        "buyer_intent",
        "pain_signal",
        "commercial_relevance",
        "market_size_growth",
        "competition_attractiveness",
        "execution_feasibility",
        "research_momentum",
        "personal_fit",
        "confidence",
        "recommendation",
        "next_action",
        "validation_test",
        "validation_gaps",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for item in opportunities:
            row = {column: item.get(column, "") for column in columns}
            row["validation_gaps"] = "；".join(item.get("validation_gaps") or [])
            writer.writerow(row)


def _markdown(opportunities: list[dict[str, Any]]) -> str:
    lines = [
        "# AI 商机雷达机会排行",
        "",
        "这个报告不是预测“必赚钱”，而是用 Porter 五力、TAM/SAM/SOM、RICE 和痛点/购买意图信号做机会优先级评分。",
        "",
        "## 排行表",
        "",
        "| 排名 | 方向 | 分数 | 决策 | 验证分 | 证据 | 趋势 | 7天分数 | 7天排名 | 30天分数 | 30天排名 | 购买意图 | 痛点 | 可信度 | 执行可行性 | 商业缺口 |",
        "|---:|---|---:|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for index, item in enumerate(opportunities, start=1):
        lines.append(
            "| {rank} | {query} | {score} | {decision_tier} | {decision_score} | {evidence_level} | "
            "{trend_status} | {score_7d} | {rank_7d} | {score_30d} | {rank_30d} | "
            "{buyer_intent} | {pain_signal} | {confidence} | {execution_feasibility} | {commercial_gap} |".format(
                rank=item.get("rank") or index,
                query=item["query"],
                score=item["score"],
                decision_tier=item.get("decision_tier", ""),
                decision_score=item.get("decision_score", ""),
                evidence_level=item.get("evidence_level", ""),
                trend_status=item.get("trend_status", ""),
                score_7d=_format_delta(item.get("score_delta_7d")),
                rank_7d=_format_delta(item.get("rank_delta_7d")),
                score_30d=_format_delta(item.get("score_delta_30d")),
                rank_30d=_format_delta(item.get("rank_delta_30d")),
                buyer_intent=item["buyer_intent"],
                pain_signal=item["pain_signal"],
                confidence=item["confidence"],
                execution_feasibility=item["execution_feasibility"],
                commercial_gap=item["commercial_gap"],
            )
        )

    lines.extend(_decision_markdown(opportunities))
    lines.extend(_trend_markdown(opportunities))
    lines.extend(["", "## 逐项判断", ""])
    for item in opportunities:
        lines.extend(
            [
                f"### {item['query']}：{item['score']} 分，{item['grade']} 级",
                "",
                f"- 决策：{item.get('decision_tier', '')}，验证分 {item.get('decision_score', '')}，证据层级：{item.get('evidence_level', '')}",
                f"- 建议：{item['recommendation']}",
                f"- 下一步：{item['next_action']}",
                f"- 验证动作：{item.get('validation_test', '')}",
                f"- 证据缺口：{'；'.join(item.get('validation_gaps') or [])}",
                "- 理由：",
            ]
        )
        lines.extend(f"  - {reason}" for reason in item["why"])
        lines.append("- 风险：")
        lines.extend(f"  - {risk}" for risk in item["risks"])
        lines.append("")

    lines.extend(
        [
            "## 评分口径",
            "",
            "- 购买意图 25%：招聘、交易/价格、产品评论、搜索/广告导入、应用市场等更接近付费行为的信号。",
            "- 痛点强度 20%：GitHub Issues、Reddit、状态页、NVD、差评/评论导入中的 bug、抱怨、手工流程和功能请求。",
            "- 市场规模/增长 15%：Google Trends、Keyword Planner、新闻/内容关注、社区讨论和招聘需求的综合代理分。",
            "- 竞争吸引力 15%：参考 Porter 五力，把产品拥挤、市场噪音、差异化缺口和痛点强度合成，越高表示越值得切入。",
            "- 可信度 10%：多源覆盖、来源可信度和结果相关度。",
            "- 执行可行性 10%：参考 RICE 的 Effort 反向代理，结合个人/小团队适配、技术供给、可信度和商业缺口。",
            "- 商业缺口 5%：技术/讨论热度高，但产品化相对少时得分更高。",
            "- 决策层级：验证分不等于机会总分，它会额外门控购买意图、痛点、可信度、商业代理证据和个人/小团队执行可行性。",
            "- 证据层级：`付费代理证据` 优于 `商业代理证据`，再优于 `多源公开信号`；没有真实销售数据时仍必须做付费验证。",
            "- 辅助解释项：技术供给、社区需求、市场关注、产品拥挤和商业相关会保留在 JSON/CSV 中用于复核。",
            "- 趋势对比：从 `data/history/opportunity_history.csv` 读取历史快照；7/30 天使用目标日期附近且不晚于目标日的最近快照。",
        ]
    )
    return "\n".join(lines) + "\n"


def _history_by_query(history: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in history:
        query = str(row.get("query") or "").strip()
        if query:
            grouped[query].append(row)
    for rows in grouped.values():
        rows.sort(key=lambda row: row.get("snapshot_date", ""))
    return grouped


def _baseline_for_window(rows: list[dict[str, str]], current_date: date, days: int) -> dict[str, str] | None:
    target = current_date - timedelta(days=days)
    earliest = current_date - timedelta(days=days * 2)
    candidates = []
    for row in rows:
        snapshot = _parse_snapshot_date(row.get("snapshot_date", ""))
        if snapshot is None:
            continue
        if earliest <= snapshot <= target:
            candidates.append((snapshot, row))
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item[0])[-1][1]


def _attach_trend_window(item: dict[str, Any], baseline: dict[str, str] | None, days: int) -> None:
    for key in (
        f"score_{days}d_ago",
        f"score_delta_{days}d",
        f"rank_{days}d_ago",
        f"rank_delta_{days}d",
        f"comparison_date_{days}d",
    ):
        item[key] = ""

    if baseline is None:
        return

    previous_score = parse_float(baseline.get("score"))
    previous_rank = parse_int(baseline.get("rank"))
    current_score = parse_float(item.get("score"))
    current_rank = parse_int(item.get("rank"))

    item[f"comparison_date_{days}d"] = baseline.get("snapshot_date", "")
    if previous_score is not None and current_score is not None:
        item[f"score_{days}d_ago"] = round(previous_score, 1)
        item[f"score_delta_{days}d"] = round(current_score - previous_score, 1)
    if previous_rank is not None and current_rank is not None:
        item[f"rank_{days}d_ago"] = previous_rank
        item[f"rank_delta_{days}d"] = previous_rank - current_rank


def _trend_status(item: dict[str, Any]) -> str:
    for days in TREND_WINDOWS:
        score_delta = parse_float(item.get(f"score_delta_{days}d"))
        rank_delta = parse_int(item.get(f"rank_delta_{days}d"))
        if score_delta is None and rank_delta is None:
            continue
        if (score_delta is not None and score_delta >= 2.0) or (rank_delta is not None and rank_delta >= 2):
            return "rising"
        if (score_delta is not None and score_delta <= -2.0) or (rank_delta is not None and rank_delta <= -2):
            return "falling"
        return "stable"
    return "baseline"


def _history_record(item: dict[str, Any], snapshot_date: str) -> dict[str, Any]:
    counts = item.get("counts") or {}
    top_sources = sorted(
        ((source, int(value or 0)) for source, value in counts.items()),
        key=lambda source_count: source_count[1],
        reverse=True,
    )
    return {
        "snapshot_date": snapshot_date,
        "query": item.get("query", ""),
        "rank": item.get("rank", ""),
        "score": item.get("score", ""),
        "grade": item.get("grade", ""),
        "buyer_intent": item.get("buyer_intent", ""),
        "pain_signal": item.get("pain_signal", ""),
        "commercial_relevance": item.get("commercial_relevance", ""),
        "market_size_growth": item.get("market_size_growth", ""),
        "competition_attractiveness": item.get("competition_attractiveness", ""),
        "execution_feasibility": item.get("execution_feasibility", ""),
        "commercial_gap": item.get("commercial_gap", ""),
        "confidence": item.get("confidence", ""),
        "decision_score": item.get("decision_score", ""),
        "decision_tier": item.get("decision_tier", ""),
        "evidence_level": item.get("evidence_level", ""),
        "result_total": sum(count for _, count in top_sources),
        "top_sources": ", ".join(f"{source}:{count}" for source, count in top_sources[:5] if count > 0),
    }


def _write_history_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(rows, key=lambda row: (row.get("snapshot_date", ""), row.get("query", "")))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HISTORY_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in HISTORY_COLUMNS})


def _decision_markdown(opportunities: list[dict[str, Any]]) -> list[str]:
    tier_counts: dict[str, int] = defaultdict(int)
    for item in opportunities:
        tier_counts[str(item.get("decision_tier") or "未分层")] += 1

    lines = [
        "",
        "## 决策分层",
        "",
        f"- 分层分布：{dict(sorted(tier_counts.items()))}",
        "- `优先付费验证` 和 `轻量付费验证` 才建议进入明确价格/预约/预付费测试；`补证据后验证` 先补需求证据。",
        "",
        "| 方向 | 决策 | 验证分 | 证据层级 | 主要证据缺口 | 验证动作 |",
        "|---|---|---:|---|---|---|",
    ]
    ranked = sorted(opportunities, key=lambda item: float(item.get("decision_score") or 0), reverse=True)
    for item in ranked[:10]:
        gaps = item.get("validation_gaps") or []
        lines.append(
            "| {query} | {decision_tier} | {decision_score} | {evidence_level} | {gap} | {validation_test} |".format(
                query=item.get("query", ""),
                decision_tier=item.get("decision_tier", ""),
                decision_score=item.get("decision_score", ""),
                evidence_level=item.get("evidence_level", ""),
                gap=str(gaps[0] if gaps else "").replace("|", "/"),
                validation_test=str(item.get("validation_test", "")).replace("|", "/"),
            )
        )
    return lines


def _trend_markdown(opportunities: list[dict[str, Any]]) -> list[str]:
    compared = [
        item for item in opportunities
        if any(item.get(f"score_delta_{days}d") not in ("", None) for days in TREND_WINDOWS)
    ]
    lines = [
        "",
        "## 趋势对比",
        "",
        "- 历史文件：`data/history/opportunity_history.csv`",
        "- 7 天和 30 天对比会在对应历史快照存在后自动显示；同一天重复运行会覆盖当天快照，避免重复计数。",
    ]
    if not compared:
        lines.append("- 当前暂无足够历史快照，本次运行会先建立机会排行基线。")
        return lines

    movers = sorted(
        compared,
        key=lambda item: (
            parse_float(item.get("score_delta_7d")) or parse_float(item.get("score_delta_30d")) or 0,
            parse_int(item.get("rank_delta_7d")) or parse_int(item.get("rank_delta_30d")) or 0,
        ),
        reverse=True,
    )
    lines.extend(
        [
            "",
            "| 方向 | 趋势 | 当前分 | 7天分数 | 7天排名 | 30天分数 | 30天排名 |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for item in movers[:10]:
        lines.append(
            "| {query} | {trend_status} | {score} | {score_7d} | {rank_7d} | {score_30d} | {rank_30d} |".format(
                query=item.get("query", ""),
                trend_status=item.get("trend_status", ""),
                score=item.get("score", ""),
                score_7d=_format_delta(item.get("score_delta_7d")),
                rank_7d=_format_delta(item.get("rank_delta_7d")),
                score_30d=_format_delta(item.get("score_delta_30d")),
                rank_30d=_format_delta(item.get("rank_delta_30d")),
            )
        )
    return lines


def _format_delta(value: Any) -> str:
    parsed = parse_float(value)
    if parsed is None:
        return ""
    if parsed > 0:
        return f"+{parsed:g}"
    return f"{parsed:g}"


def _parse_snapshot_date(value: Any) -> date | None:
    parsed = parse_datetime(value)
    return parsed.date() if parsed else None


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))
