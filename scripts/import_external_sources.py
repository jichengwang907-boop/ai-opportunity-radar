from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shopping_intel.signals import SIGNAL_COLUMNS, enrich_record

SEARCH_COLUMNS = [
    "source",
    "query",
    "title",
    "url",
    "rank",
    "result_count",
    "search_volume",
    "snippet",
    "price",
    "currency",
    "seller",
    "rating",
    "review_count",
    "collected_at",
    *SIGNAL_COLUMNS,
]

PRODUCT_COLUMNS = [
    "source",
    "product_id",
    "title",
    "url",
    "price",
    "currency",
    "seller",
    "category",
    "stock_status",
    "rating",
    "review_count",
    "sales_volume",
    "last_updated",
    "collected_at",
    *SIGNAL_COLUMNS,
]

PRODUCTISH_SOURCES = {
    "amazon",
    "taobao",
    "tmall",
    "jd",
    "jingdong",
    "ebay",
    "etsy",
    "aliexpress",
    "shopify",
    "g2",
    "capterra",
}

PRODUCTISH_SIGNALS = {"ecommerce", "b2b_review", "product", "listing", "marketplace"}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize no-token platform exports into AI radar CSV inputs."
    )
    parser.add_argument("--input", default="data/external_sources.csv")
    parser.add_argument("--search-out", default="data/search_results.external-imports.csv")
    parser.add_argument("--products-out", default="data/products.external-imports.csv")
    parser.add_argument("--report-out", default="reports/external-imports")
    parser.add_argument("--config", default="config.realtime-ai-platforms.json")
    parser.add_argument("--google-trends-dir", default="data/external/google_trends/raw")
    parser.add_argument("--disable-google-trends", action="store_true")
    args = parser.parse_args()

    input_path = resolve(args.input)
    search_out = resolve(args.search_out)
    products_out = resolve(args.products_out)
    report_out = resolve(args.report_out)
    config_path = resolve(args.config)
    google_trends_dir = resolve(args.google_trends_dir)
    report_out.mkdir(parents=True, exist_ok=True)
    collected_at = datetime.now(timezone.utc).date().isoformat()
    known_queries = load_known_queries(config_path)
    google_trends_rows = (
        []
        if args.disable_google_trends
        else read_google_trends_exports(google_trends_dir, known_queries, collected_at)
    )

    if not input_path.exists() and not google_trends_rows:
        write_csv(search_out, SEARCH_COLUMNS, [])
        write_csv(products_out, PRODUCT_COLUMNS, [])
        report = {
            "generated_at": now_iso(),
            "input": str(input_path),
            "status": "missing_input",
            "google_trends_dir": str(google_trends_dir),
            "google_trends_files": 0,
            "google_trends_rows": 0,
            "search_rows": 0,
            "product_rows": 0,
            "message": "Copy data/external_sources.template.csv to data/external_sources.csv and replace sample rows with platform exports.",
        }
        write_report(report_out, report)
        print("No external import file found; wrote empty import CSVs.")
        print("Create data\\external_sources.csv from data\\external_sources.template.csv when token access is unavailable.")
        return 0

    rows = read_rows(input_path) if input_path.exists() else []
    search_rows: list[dict[str, Any]] = []
    product_rows: list[dict[str, Any]] = []

    for index, row in enumerate(rows, start=1):
        normalized_search, normalized_product = normalize_row(row, index, collected_at)
        if normalized_search:
            search_rows.append(normalized_search)
        if normalized_product:
            product_rows.append(normalized_product)

    search_rows.extend(google_trends_rows)
    search_rows = dedupe(search_rows, ["source", "query", "title", "url", "rank"])
    product_rows = dedupe(product_rows, ["source", "product_id", "title", "url"])

    write_csv(search_out, SEARCH_COLUMNS, search_rows)
    write_csv(products_out, PRODUCT_COLUMNS, product_rows)

    report = {
        "generated_at": now_iso(),
        "input": str(input_path),
        "status": "ok",
        "input_status": "found" if input_path.exists() else "missing_input",
        "input_rows": len(rows),
        "google_trends_dir": str(google_trends_dir),
        "google_trends_files": len(google_trends_files(google_trends_dir)),
        "google_trends_rows": len(google_trends_rows),
        "search_rows": len(search_rows),
        "product_rows": len(product_rows),
        "sources": sorted({row.get("source", "") for row in search_rows + product_rows if row.get("source")}),
    }
    if not input_path.exists():
        report["message"] = "No data/external_sources.csv found; imported available Google Trends raw CSVs."
    write_report(report_out, report)
    print("External import generated")
    print(f"Input rows: {len(rows)}")
    print(f"Google Trends rows: {len(google_trends_rows)}")
    print(f"Search rows: {len(search_rows)}")
    print(f"Product rows: {len(product_rows)}")
    return 0


def normalize_row(
    row: dict[str, str],
    index: int,
    fallback_collected_at: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    lowered = {clean_key(key): value for key, value in row.items()}
    source = field_value(lowered, "source", "platform")
    query = field_value(lowered, "query", "keyword", "search_term")
    title = field_value(lowered, "title", "name", "product_name", "listing_title") or query
    if not source or not title:
        return None, None

    record_type = field_value(lowered, "record_type", "type").lower()
    signal_type = field_value(lowered, "signal_type").lower()
    collected_at = field_value(lowered, "collected_at", "date_found") or fallback_collected_at
    metric_name = field_value(lowered, "metric_name").lower()
    metric_value = field_value(lowered, "metric_value", "value")

    should_make_product = (
        record_type in {"product", "listing", "sku"}
        or source.lower() in PRODUCTISH_SOURCES
        or signal_type in PRODUCTISH_SIGNALS
    )
    should_make_search = record_type not in {"product_only"}

    search_row = None
    if should_make_search:
        result_count = first_present(
            field_value(lowered, "result_count", "total_results"),
            metric_value if metric_name == "result_count" else "",
            field_value(lowered, "review_count", "reviews"),
            "1",
        )
        search_volume = first_present(
            field_value(lowered, "search_volume", "keyword_volume", "monthly_searches"),
            metric_value if metric_name in {"search_volume", "keyword_volume", "interest_over_time", "interest"} else "",
            result_count,
        )
        search_row = {
            "source": source,
            "query": query,
            "title": title,
            "url": field_value(lowered, "url", "link"),
            "rank": field_value(lowered, "rank", "position") or index,
            "result_count": result_count,
            "search_volume": search_volume,
            "snippet": field_value(lowered, "snippet", "description", "notes"),
            "price": field_value(lowered, "price"),
            "currency": field_value(lowered, "currency"),
            "seller": field_value(lowered, "seller", "shop", "vendor"),
            "rating": field_value(lowered, "rating", "score"),
            "review_count": first_present(
                field_value(lowered, "review_count", "reviews"),
                metric_value if metric_name == "review_count" else "",
            ),
            "collected_at": collected_at,
            "signal_type": signal_type,
            "buyer_intent_score": field_value(lowered, "buyer_intent_score", "buyer_intent"),
            "pain_score": field_value(lowered, "pain_score"),
            "source_confidence": field_value(lowered, "source_confidence"),
            "commercial_relevance": field_value(lowered, "commercial_relevance"),
        }
        search_row = enrich_record(search_row)

    product_row = None
    if should_make_product:
        product_row = {
            "source": source,
            "product_id": first_present(
                field_value(lowered, "product_id", "sku", "id", "asin", "item_id"),
                stable_id(source, title, field_value(lowered, "url", "link")),
            ),
            "title": title,
            "url": field_value(lowered, "url", "link"),
            "price": field_value(lowered, "price"),
            "currency": field_value(lowered, "currency"),
            "seller": field_value(lowered, "seller", "shop", "vendor"),
            "category": field_value(lowered, "category") or signal_type,
            "stock_status": field_value(lowered, "stock_status", "availability") or "imported",
            "rating": field_value(lowered, "rating", "score"),
            "review_count": first_present(
                field_value(lowered, "review_count", "reviews"),
                metric_value if metric_name == "review_count" else "",
            ),
            "sales_volume": first_present(
                field_value(lowered, "sales_volume", "sold_count", "sales"),
                metric_value if metric_name == "sales_volume" else "",
            ),
            "last_updated": field_value(lowered, "last_updated", "updated_at") or collected_at,
            "collected_at": collected_at,
            "signal_type": signal_type,
            "buyer_intent_score": field_value(lowered, "buyer_intent_score", "buyer_intent"),
            "pain_score": field_value(lowered, "pain_score"),
            "source_confidence": field_value(lowered, "source_confidence"),
            "commercial_relevance": field_value(lowered, "commercial_relevance"),
        }
        product_row = enrich_record(product_row)

    return search_row, product_row


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_known_queries(config_path: Path) -> dict[str, str]:
    if not config_path.exists():
        return {}
    config = json.loads(config_path.read_text(encoding="utf-8"))
    queries: dict[str, str] = {}
    for row in config.get("queries") or []:
        term = str(row.get("term") or "").strip()
        if term:
            queries[normalize_query(term)] = term
    return queries


def read_google_trends_exports(
    directory: Path,
    known_queries: dict[str, str] | None = None,
    fallback_collected_at: str = "",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in google_trends_files(directory):
        rows.extend(normalize_google_trends_file(path, known_queries or {}, fallback_collected_at))
    return rows


def google_trends_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(path for path in directory.glob("*.csv") if path.is_file())


def normalize_google_trends_file(
    path: Path,
    known_queries: dict[str, str],
    fallback_collected_at: str,
) -> list[dict[str, Any]]:
    matrix = read_csv_matrix(path)
    header_index = google_trends_header_index(matrix)
    if header_index is None:
        return []

    header = matrix[header_index]
    series: dict[str, list[tuple[str, float]]] = {}
    column_queries: dict[int, str] = {}
    for column_index, heading in enumerate(header[1:], start=1):
        query = google_trends_query_name(heading)
        normalized = normalize_query(query)
        if not normalized:
            continue
        if known_queries and normalized not in known_queries:
            continue
        column_queries[column_index] = known_queries.get(normalized, query)

    for row in matrix[header_index + 1:]:
        if not row:
            continue
        date_text = str(row[0] or "").strip()
        if not date_text:
            continue
        for column_index, query in column_queries.items():
            if column_index >= len(row):
                continue
            value = parse_google_trends_value(row[column_index])
            if value is None:
                continue
            series.setdefault(query, []).append((date_text, value))

    records = []
    for rank, (query, points) in enumerate(sorted(series.items()), start=1):
        record = google_trends_record(path, query, points, rank, fallback_collected_at)
        if record:
            records.append(record)
    return records


def read_csv_matrix(path: Path) -> list[list[str]]:
    for encoding in ("utf-8-sig", "utf-16", "gb18030"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                return [row for row in csv.reader(handle) if any(str(cell).strip() for cell in row)]
        except UnicodeError:
            continue
    return []


def google_trends_header_index(matrix: list[list[str]]) -> int | None:
    english_headers = {"time", "week", "date", "day"}
    localized_headers = {"周", "日期", "日"}
    for index, row in enumerate(matrix):
        if not row:
            continue
        first = str(row[0] or "").strip()
        if first.lower() in english_headers or first in localized_headers:
            return index
    return None


def google_trends_query_name(value: Any) -> str:
    text = str(value or "").strip()
    if ":" in text:
        text = text.split(":", 1)[0]
    return " ".join(text.split())


def normalize_query(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def parse_google_trends_value(value: Any) -> float | None:
    text = str(value or "").strip().replace(",", "")
    if not text:
        return None
    if text.startswith("<"):
        return 1.0
    try:
        return float(text)
    except ValueError:
        return None


def google_trends_record(
    path: Path,
    query: str,
    points: list[tuple[str, float]],
    rank: int,
    fallback_collected_at: str,
) -> dict[str, Any] | None:
    if not points:
        return None
    values = [value for _, value in points]
    recent_values = values[-4:] if len(values) >= 4 else values
    latest_date, latest_value = points[-1]
    recent_average = sum(recent_values) / len(recent_values)
    average = sum(values) / len(values)
    peak = max(values)
    delta = latest_value - values[0]
    row = {
        "source": "google_trends",
        "query": query,
        "title": f"Google Trends: {query}",
        "url": "",
        "rank": rank,
        "result_count": int(round(recent_average)),
        "search_volume": int(round(latest_value)),
        "snippet": (
            f"{path.name}; latest={latest_value:g}; recent_4w_avg={recent_average:.1f}; "
            f"avg={average:.1f}; peak={peak:g}; first_to_latest_delta={delta:+.1f}"
        ),
        "price": "",
        "currency": "",
        "seller": "",
        "rating": "",
        "review_count": "",
        "collected_at": latest_date or fallback_collected_at,
        "signal_type": "search_interest",
        "buyer_intent_score": "",
        "pain_score": "",
        "source_confidence": "",
        "commercial_relevance": "",
    }
    return enrich_record(row)


def write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def write_report(out: Path, report: dict[str, Any]) -> None:
    (out / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# No-token external import",
        "",
        f"- Generated at: {report.get('generated_at', '')}",
        f"- Status: {report.get('status', '')}",
        f"- Input: {report.get('input', '')}",
        f"- Google Trends dir: {report.get('google_trends_dir', '')}",
        f"- Google Trends files: {report.get('google_trends_files', 0)}",
        f"- Google Trends rows: {report.get('google_trends_rows', 0)}",
        f"- Search rows: {report.get('search_rows', 0)}",
        f"- Product rows: {report.get('product_rows', 0)}",
    ]
    if report.get("message"):
        lines.extend(["", report["message"]])
    if report.get("sources"):
        lines.extend(["", "Sources: " + ", ".join(report["sources"])])
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def dedupe(rows: list[dict[str, Any]], keys: list[str]) -> list[dict[str, Any]]:
    seen: set[tuple[str, ...]] = set()
    result: list[dict[str, Any]] = []
    for row in rows:
        signature = tuple(str(row.get(key, "")).strip().lower() for key in keys)
        if signature in seen:
            continue
        seen.add(signature)
        result.append(row)
    return result


def resolve(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


def clean_key(key: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(key or "").strip().lower()).strip("_")


def field_value(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        found = row.get(clean_key(key), "")
        if found is not None and str(found).strip():
            return str(found).strip()
    return ""


def first_present(*values: Any) -> Any:
    for item in values:
        if item is not None and str(item).strip():
            return item
    return ""


def stable_id(source: str, title: str, url: str) -> str:
    raw = f"{source}-{title}-{url}".lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return cleaned[:80] or "external-import"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
