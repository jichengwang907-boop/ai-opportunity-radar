from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from typing import Any


def parse_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def parse_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(str(value).replace(",", "").strip()))
    except ValueError:
        return None


def parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=timezone.utc)

    text = str(value).strip()
    if not text:
        return None

    for candidate in (text, text.replace("Z", "+00:00")):
        try:
            parsed = datetime.fromisoformat(candidate)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    return None


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


@dataclass(slots=True)
class SearchResult:
    source: str
    query: str
    title: str
    url: str = ""
    rank: int | None = None
    result_count: int | None = None
    search_volume: int | None = None
    snippet: str = ""
    price: float | None = None
    currency: str = ""
    seller: str = ""
    rating: float | None = None
    review_count: int | None = None
    collected_at: datetime | None = None
    signal_type: str = ""
    buyer_intent_score: int | None = None
    pain_score: int | None = None
    source_confidence: int | None = None
    commercial_relevance: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_record(cls, record: dict[str, Any], default_source: str = "") -> "SearchResult":
        return cls(
            source=clean_text(record.get("source") or default_source),
            query=clean_text(record.get("query")),
            title=clean_text(record.get("title") or record.get("name")),
            url=clean_text(record.get("url") or record.get("link")),
            rank=parse_int(record.get("rank") or record.get("position")),
            result_count=parse_int(record.get("result_count") or record.get("total_results")),
            search_volume=parse_int(record.get("search_volume") or record.get("keyword_volume")),
            snippet=clean_text(record.get("snippet") or record.get("description")),
            price=parse_float(record.get("price")),
            currency=clean_text(record.get("currency")),
            seller=clean_text(record.get("seller") or record.get("shop")),
            rating=parse_float(record.get("rating")),
            review_count=parse_int(record.get("review_count") or record.get("reviews")),
            collected_at=parse_datetime(record.get("collected_at") or record.get("date_found")),
            signal_type=clean_text(record.get("signal_type")),
            buyer_intent_score=parse_int(record.get("buyer_intent_score") or record.get("buyer_intent")),
            pain_score=parse_int(record.get("pain_score")),
            source_confidence=parse_int(record.get("source_confidence")),
            commercial_relevance=parse_int(record.get("commercial_relevance")),
            raw=dict(record),
        )


@dataclass(slots=True)
class Product:
    source: str
    product_id: str
    title: str
    url: str = ""
    price: float | None = None
    currency: str = ""
    seller: str = ""
    category: str = ""
    stock_status: str = ""
    rating: float | None = None
    review_count: int | None = None
    sales_volume: int | None = None
    last_updated: datetime | None = None
    collected_at: datetime | None = None
    signal_type: str = ""
    buyer_intent_score: int | None = None
    pain_score: int | None = None
    source_confidence: int | None = None
    commercial_relevance: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_record(cls, record: dict[str, Any], default_source: str = "") -> "Product":
        return cls(
            source=clean_text(record.get("source") or default_source),
            product_id=clean_text(record.get("product_id") or record.get("id") or record.get("sku")),
            title=clean_text(record.get("title") or record.get("name")),
            url=clean_text(record.get("url") or record.get("link")),
            price=parse_float(record.get("price")),
            currency=clean_text(record.get("currency")),
            seller=clean_text(record.get("seller") or record.get("shop")),
            category=clean_text(record.get("category")),
            stock_status=clean_text(record.get("stock_status") or record.get("availability")),
            rating=parse_float(record.get("rating")),
            review_count=parse_int(record.get("review_count") or record.get("reviews")),
            sales_volume=parse_int(record.get("sales_volume") or record.get("sold_count")),
            last_updated=parse_datetime(record.get("last_updated") or record.get("updated_at")),
            collected_at=parse_datetime(record.get("collected_at") or record.get("date_found")),
            signal_type=clean_text(record.get("signal_type")),
            buyer_intent_score=parse_int(record.get("buyer_intent_score") or record.get("buyer_intent")),
            pain_score=parse_int(record.get("pain_score")),
            source_confidence=parse_int(record.get("source_confidence")),
            commercial_relevance=parse_int(record.get("commercial_relevance")),
            raw=dict(record),
        )
