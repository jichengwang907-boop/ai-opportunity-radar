from __future__ import annotations

import re
from typing import Any


SIGNAL_COLUMNS = [
    "signal_type",
    "buyer_intent_score",
    "pain_score",
    "source_confidence",
    "commercial_relevance",
]


SOURCE_SIGNAL_PROFILES: dict[str, dict[str, int | str]] = {
    "github": {"signal_type": "tech_supply", "buyer": 12, "pain": 10, "confidence": 86, "commercial": 32},
    "github_issues": {"signal_type": "feedback", "buyer": 45, "pain": 82, "confidence": 82, "commercial": 65},
    "producthunt": {"signal_type": "product", "buyer": 58, "pain": 35, "confidence": 74, "commercial": 72},
    "arxiv": {"signal_type": "research", "buyer": 8, "pain": 8, "confidence": 80, "commercial": 22},
    "huggingface_models": {"signal_type": "tech_supply", "buyer": 10, "pain": 8, "confidence": 76, "commercial": 28},
    "huggingface_spaces": {"signal_type": "prototype", "buyer": 18, "pain": 15, "confidence": 70, "commercial": 34},
    "hackernews": {"signal_type": "discussion", "buyer": 35, "pain": 52, "confidence": 66, "commercial": 46},
    "reddit": {"signal_type": "feedback", "buyer": 42, "pain": 78, "confidence": 62, "commercial": 60},
    "google_news": {"signal_type": "news", "buyer": 26, "pain": 22, "confidence": 62, "commercial": 38},
    "oksurf_news": {"signal_type": "news", "buyer": 24, "pain": 20, "confidence": 52, "commercial": 34},
    "ai_dev_jobs": {"signal_type": "hiring", "buyer": 78, "pain": 45, "confidence": 78, "commercial": 74},
    "agentic_engineering_jobs": {"signal_type": "hiring", "buyer": 82, "pain": 48, "confidence": 76, "commercial": 78},
    "devitjobs": {"signal_type": "hiring", "buyer": 72, "pain": 40, "confidence": 68, "commercial": 68},
    "agentdeals": {"signal_type": "deal", "buyer": 70, "pain": 34, "confidence": 70, "commercial": 76},
    "api_status_check": {"signal_type": "reliability", "buyer": 44, "pain": 68, "confidence": 70, "commercial": 58},
    "nvd": {"signal_type": "security", "buyer": 50, "pain": 72, "confidence": 88, "commercial": 62},
    "patentsview": {"signal_type": "patent", "buyer": 18, "pain": 12, "confidence": 72, "commercial": 34},
    "domainsdb": {"signal_type": "startup_activity", "buyer": 42, "pain": 20, "confidence": 52, "commercial": 54},
    "internet_archive": {"signal_type": "historical_content", "buyer": 12, "pain": 10, "confidence": 56, "commercial": 24},
    "predscope": {"signal_type": "market_expectation", "buyer": 55, "pain": 25, "confidence": 54, "commercial": 60},
    "youtube": {"signal_type": "content_attention", "buyer": 36, "pain": 34, "confidence": 58, "commercial": 48},
    "x_recent": {"signal_type": "social_attention", "buyer": 34, "pain": 46, "confidence": 45, "commercial": 42},
    "google_trends": {"signal_type": "search_interest", "buyer": 68, "pain": 30, "confidence": 70, "commercial": 66},
    "google_ads": {"signal_type": "keyword_demand", "buyer": 86, "pain": 32, "confidence": 76, "commercial": 84},
    "g2": {"signal_type": "b2b_review", "buyer": 88, "pain": 78, "confidence": 84, "commercial": 90},
    "capterra": {"signal_type": "b2b_review", "buyer": 86, "pain": 76, "confidence": 82, "commercial": 88},
    "alternative_to": {"signal_type": "alternatives", "buyer": 72, "pain": 64, "confidence": 68, "commercial": 72},
    "chrome_web_store": {"signal_type": "marketplace_review", "buyer": 78, "pain": 64, "confidence": 76, "commercial": 80},
    "slack_marketplace": {"signal_type": "marketplace_review", "buyer": 80, "pain": 58, "confidence": 74, "commercial": 80},
    "shopify_marketplace": {"signal_type": "marketplace_review", "buyer": 84, "pain": 62, "confidence": 78, "commercial": 84},
    "app_store": {"signal_type": "app_review", "buyer": 78, "pain": 72, "confidence": 78, "commercial": 82},
    "google_play": {"signal_type": "app_review", "buyer": 76, "pain": 72, "confidence": 76, "commercial": 80},
    "amazon": {"signal_type": "ecommerce", "buyer": 90, "pain": 58, "confidence": 78, "commercial": 92},
    "taobao": {"signal_type": "ecommerce", "buyer": 88, "pain": 54, "confidence": 72, "commercial": 90},
    "tmall": {"signal_type": "ecommerce", "buyer": 88, "pain": 54, "confidence": 74, "commercial": 90},
    "jd": {"signal_type": "ecommerce", "buyer": 88, "pain": 54, "confidence": 74, "commercial": 90},
    "jingdong": {"signal_type": "ecommerce", "buyer": 88, "pain": 54, "confidence": 74, "commercial": 90},
}


CATEGORY_SIGNAL_OVERRIDES: tuple[tuple[str, dict[str, int | str]], ...] = (
    ("github_issue", {"signal_type": "feedback", "buyer": 45, "pain": 82, "confidence": 82, "commercial": 65}),
    ("producthunt", {"signal_type": "product", "buyer": 58, "pain": 35, "confidence": 74, "commercial": 72}),
    ("job", {"signal_type": "hiring", "buyer": 76, "pain": 44, "confidence": 72, "commercial": 72}),
    ("developer_deal", {"signal_type": "deal", "buyer": 70, "pain": 34, "confidence": 70, "commercial": 76}),
    ("api_status", {"signal_type": "reliability", "buyer": 44, "pain": 68, "confidence": 70, "commercial": 58}),
    ("cve", {"signal_type": "security", "buyer": 50, "pain": 72, "confidence": 88, "commercial": 62}),
    ("news_article", {"signal_type": "news", "buyer": 25, "pain": 20, "confidence": 58, "commercial": 36}),
    ("research_paper", {"signal_type": "research", "buyer": 8, "pain": 8, "confidence": 80, "commercial": 22}),
    ("repository", {"signal_type": "tech_supply", "buyer": 12, "pain": 10, "confidence": 86, "commercial": 32}),
    ("hf_model", {"signal_type": "tech_supply", "buyer": 10, "pain": 8, "confidence": 76, "commercial": 28}),
    ("hf_space", {"signal_type": "prototype", "buyer": 18, "pain": 15, "confidence": 70, "commercial": 34}),
    ("b2b_review", {"signal_type": "b2b_review", "buyer": 88, "pain": 78, "confidence": 84, "commercial": 90}),
    ("marketplace_review", {"signal_type": "marketplace_review", "buyer": 80, "pain": 64, "confidence": 76, "commercial": 82}),
    ("app_review", {"signal_type": "app_review", "buyer": 78, "pain": 72, "confidence": 78, "commercial": 82}),
    ("ecommerce", {"signal_type": "ecommerce", "buyer": 88, "pain": 56, "confidence": 76, "commercial": 90}),
    ("search_interest", {"signal_type": "search_interest", "buyer": 68, "pain": 30, "confidence": 70, "commercial": 66}),
    ("keyword_demand", {"signal_type": "keyword_demand", "buyer": 86, "pain": 32, "confidence": 76, "commercial": 84}),
)


PAIN_PATTERNS = (
    r"\bbug\b",
    r"\berror\b",
    r"\bcrash",
    r"\bbroken\b",
    r"\bnot working\b",
    r"\bcannot\b",
    r"\bcan't\b",
    r"\bmissing\b",
    r"\bmanual\b",
    r"\btedious\b",
    r"\brepetitive\b",
    r"\bcomplain",
    r"\bfrustrat",
    r"\bfeature request\b",
    r"\bplease add\b",
    r"\bneed\b",
    r"\bpain\b",
    r"\btoo expensive\b",
)


BUYER_PATTERNS = (
    r"\bprice\b",
    r"\bpricing\b",
    r"\bpaid\b",
    r"\bsubscription\b",
    r"\bvendor\b",
    r"\bprocurement\b",
    r"\bbudget\b",
    r"\bspend\b",
    r"\bquote\b",
    r"\bbuy\b",
    r"\bpurchase\b",
    r"\balternative\b",
    r"\bvs\b",
    r"\bcompare\b",
    r"\bmarketplace\b",
    r"\bapp store\b",
    r"\bextension\b",
    r"\bplugin\b",
)


MANUAL_REPLACEMENT_TERMS = (
    "customer support",
    "sales",
    "lead generation",
    "email",
    "data entry",
    "document processing",
    "invoice",
    "contract",
    "bookkeeping",
    "recruiting",
    "qa testing",
    "social media",
    "web research",
    "spreadsheet",
    "meeting notes",
)


def enrich_record(record: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(record)
    profile = signal_profile(
        source=str(enriched.get("source") or ""),
        category=str(enriched.get("category") or ""),
        signal_type=str(enriched.get("signal_type") or ""),
    )
    text = " ".join(
        str(enriched.get(field) or "")
        for field in ("query", "title", "snippet", "category", "stock_status", "seller")
    )
    scores = score_signal(
        profile=profile,
        text=text,
        price=enriched.get("price"),
        rating=enriched.get("rating"),
        review_count=enriched.get("review_count"),
        sales_volume=enriched.get("sales_volume") or enriched.get("search_volume"),
        result_count=enriched.get("result_count"),
    )
    enriched["signal_type"] = str(profile["signal_type"])
    for column, value in scores.items():
        existing = _int_or_none(enriched.get(column))
        enriched[column] = existing if existing is not None else value
    return enriched


def signal_profile(source: str, category: str = "", signal_type: str = "") -> dict[str, int | str]:
    lowered_source = _normalize_key(source)
    lowered_category = _normalize_key(category)
    lowered_signal = _normalize_key(signal_type)

    for needle, profile in CATEGORY_SIGNAL_OVERRIDES:
        if needle in lowered_signal or needle in lowered_category:
            return dict(profile)

    if lowered_source in SOURCE_SIGNAL_PROFILES:
        return dict(SOURCE_SIGNAL_PROFILES[lowered_source])

    return {"signal_type": lowered_signal or "unknown", "buyer": 25, "pain": 25, "confidence": 45, "commercial": 35}


def score_signal(
    profile: dict[str, int | str],
    text: str,
    price: Any = "",
    rating: Any = "",
    review_count: Any = "",
    sales_volume: Any = "",
    result_count: Any = "",
) -> dict[str, int]:
    lowered = text.lower()
    buyer = int(profile.get("buyer") or 0)
    pain = int(profile.get("pain") or 0)
    confidence = int(profile.get("confidence") or 0)
    commercial = int(profile.get("commercial") or 0)

    buyer += min(18, _pattern_hits(lowered, BUYER_PATTERNS) * 4)
    pain += min(24, _pattern_hits(lowered, PAIN_PATTERNS) * 5)

    if any(term in lowered for term in MANUAL_REPLACEMENT_TERMS):
        buyer += 8
        pain += 8
        commercial += 6

    if _has_value(price):
        buyer += 15
        commercial += 16
        confidence += 5
    if _number_or_none(rating) is not None:
        buyer += 5
        commercial += 8
        confidence += 5
    if (_number_or_none(review_count) or 0) > 0:
        commercial += 8
        confidence += 4
    if (_number_or_none(sales_volume) or 0) > 0:
        buyer += 8
        commercial += 10
    if (_number_or_none(result_count) or 0) > 100:
        confidence += 3

    buyer = _clamp_int(buyer)
    pain = _clamp_int(pain)
    confidence = _clamp_int(confidence)
    commercial = _clamp_int(max(commercial, buyer * 0.50 + pain * 0.28 + confidence * 0.22))

    return {
        "buyer_intent_score": buyer,
        "pain_score": pain,
        "source_confidence": confidence,
        "commercial_relevance": commercial,
    }


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")


def _pattern_hits(text: str, patterns: tuple[str, ...]) -> int:
    return sum(1 for pattern in patterns if re.search(pattern, text))


def _has_value(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _number_or_none(value: Any) -> float | None:
    if not _has_value(value):
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def _int_or_none(value: Any) -> int | None:
    parsed = _number_or_none(value)
    if parsed is None:
        return None
    return _clamp_int(parsed)


def _clamp_int(value: float, lower: int = 0, upper: int = 100) -> int:
    return int(max(lower, min(upper, round(value))))
