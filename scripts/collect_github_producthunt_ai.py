from __future__ import annotations

import csv
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shopping_intel.signals import SIGNAL_COLUMNS, enrich_record

DATA_DIR = ROOT / "data"
CONFIG_PATH = ROOT / "config.github-producthunt-ai.json"

KEYWORDS = [
    {
        "term": "ai agent",
        "expected_terms": ["ai", "agent"],
        "min_result_count": 10,
        "min_relevant_results": 3,
        "min_avg_relevance": 0.35,
    },
    {
        "term": "ai coding assistant",
        "expected_terms": ["ai", "coding", "assistant"],
        "min_result_count": 5,
        "min_relevant_results": 2,
        "min_avg_relevance": 0.35,
    },
    {
        "term": "ai search",
        "expected_terms": ["ai", "search"],
        "min_result_count": 10,
        "min_relevant_results": 3,
        "min_avg_relevance": 0.35,
    },
    {
        "term": "ai meeting notes",
        "expected_terms": ["ai", "meeting", "notes"],
        "min_result_count": 5,
        "min_relevant_results": 2,
        "min_avg_relevance": 0.35,
    },
    {
        "term": "ai voice recorder",
        "expected_terms": ["ai", "voice", "recorder"],
        "min_result_count": 5,
        "min_relevant_results": 2,
        "min_avg_relevance": 0.35,
    },
    {
        "term": "ai smart glasses",
        "expected_terms": ["ai", "smart", "glasses"],
        "min_result_count": 5,
        "min_relevant_results": 2,
        "min_avg_relevance": 0.35,
    },
    {
        "term": "ai translator",
        "expected_terms": ["ai", "translator"],
        "min_result_count": 5,
        "min_relevant_results": 2,
        "min_avg_relevance": 0.35,
    },
    {
        "term": "local llm",
        "expected_terms": ["local", "llm"],
        "min_result_count": 10,
        "min_relevant_results": 3,
        "min_avg_relevance": 0.35,
    },
]

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


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    collected_at = datetime.now(timezone.utc).date().isoformat()

    github_search_rows: list[dict[str, Any]] = []
    github_products: list[dict[str, Any]] = []
    producthunt_search_rows: list[dict[str, Any]] = []
    producthunt_products: list[dict[str, Any]] = []

    for index, keyword in enumerate(KEYWORDS):
        term = keyword["term"]
        github = fetch_github_repositories(term)
        github_search_rows.extend(to_github_search_rows(term, github, collected_at))
        github_products.extend(to_github_products(github, collected_at))

        producthunt = fetch_producthunt_posts(term)
        producthunt_search_rows.extend(to_producthunt_search_rows(term, producthunt, collected_at))
        producthunt_products.extend(to_producthunt_products(producthunt, collected_at))

        # GitHub unauthenticated search is limited; stay gentle and reproducible.
        if index < len(KEYWORDS) - 1:
            time.sleep(7)

    write_csv(DATA_DIR / "search_results.github-ai.csv", SEARCH_COLUMNS, github_search_rows)
    write_csv(DATA_DIR / "products.github-ai.csv", PRODUCT_COLUMNS, github_products)
    write_csv(DATA_DIR / "search_results.producthunt-ai.csv", SEARCH_COLUMNS, producthunt_search_rows)
    write_csv(DATA_DIR / "products.producthunt-ai.csv", PRODUCT_COLUMNS, producthunt_products)
    write_config()

    print("Collected GitHub + Product Hunt AI signals")
    print(f"GitHub search rows: {len(github_search_rows)}")
    print(f"GitHub products: {len(github_products)}")
    print(f"Product Hunt search rows: {len(producthunt_search_rows)}")
    print(f"Product Hunt products: {len(producthunt_products)}")
    print(f"Config: {CONFIG_PATH}")
    return 0


def fetch_github_repositories(term: str) -> dict[str, Any]:
    params = {
        "q": term,
        "sort": "stars",
        "order": "desc",
        "per_page": 5,
    }
    url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(params)
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "shopping-intel-monitor/0.1",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    return get_json(url, headers=headers)


def fetch_producthunt_posts(term: str) -> dict[str, Any]:
    params = {
        "query": term,
        "hitsPerPage": 5,
    }
    url = "https://0h4smabbsg-dsn.algolia.net/1/indexes/Post_production?" + urllib.parse.urlencode(params)
    headers = {
        "User-Agent": "shopping-intel-monitor/0.1",
        "X-Algolia-API-Key": "9670d2d619b9d07859448d7628eea5f3",
        "X-Algolia-Application-Id": "0H4SMABBSG",
    }
    return get_json(url, headers=headers)


def get_json(url: str, headers: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code in (403, 429):
            reset = error.headers.get("X-RateLimit-Reset")
            if reset:
                wait_seconds = max(1, int(reset) - int(time.time()) + 2)
                time.sleep(min(wait_seconds, 90))
                with urllib.request.urlopen(request, timeout=30) as response:
                    return json.loads(response.read().decode("utf-8"))
        raise


def to_github_search_rows(term: str, payload: dict[str, Any], collected_at: str) -> list[dict[str, Any]]:
    total_count = payload.get("total_count") or 0
    rows = []
    for rank, item in enumerate(payload.get("items") or [], start=1):
        rows.append(
            enrich_record(
                {
                "source": "github",
                "query": term,
                "title": item.get("full_name") or item.get("name") or "",
                "url": item.get("html_url") or "",
                "rank": rank,
                "result_count": total_count,
                "search_volume": total_count,
                "snippet": item.get("description") or "",
                "price": "",
                "currency": "",
                "seller": (item.get("owner") or {}).get("login") or "",
                "rating": "",
                "review_count": item.get("stargazers_count") or "",
                "collected_at": collected_at,
                }
            )
        )
    return rows


def to_github_products(payload: dict[str, Any], collected_at: str) -> list[dict[str, Any]]:
    rows = []
    for item in payload.get("items") or []:
        rows.append(
            enrich_record(
                {
                "source": "github",
                "product_id": item.get("full_name") or str(item.get("id") or ""),
                "title": item.get("full_name") or item.get("name") or "",
                "url": item.get("html_url") or "",
                "price": "",
                "currency": "",
                "seller": (item.get("owner") or {}).get("login") or "",
                "category": "GitHub repository",
                "stock_status": "public",
                "rating": "",
                "review_count": item.get("stargazers_count") or "",
                "sales_volume": item.get("forks_count") or "",
                "last_updated": item.get("pushed_at") or item.get("updated_at") or "",
                "collected_at": collected_at,
                }
            )
        )
    return rows


def to_producthunt_search_rows(term: str, payload: dict[str, Any], collected_at: str) -> list[dict[str, Any]]:
    total_count = payload.get("nbHits") or 0
    rows = []
    for rank, item in enumerate(payload.get("hits") or [], start=1):
        rows.append(
            enrich_record(
                {
                "source": "producthunt",
                "query": term,
                "title": item.get("name") or "",
                "url": producthunt_url(item),
                "rank": rank,
                "result_count": total_count,
                "search_volume": total_count,
                "snippet": item.get("tagline") or "",
                "price": "",
                "currency": "",
                "seller": ((item.get("user") or {}).get("username") or ""),
                "rating": "",
                "review_count": item.get("vote_count") or "",
                "collected_at": collected_at,
                }
            )
        )
    return rows


def to_producthunt_products(payload: dict[str, Any], collected_at: str) -> list[dict[str, Any]]:
    rows = []
    for item in payload.get("hits") or []:
        rows.append(
            enrich_record(
                {
                "source": "producthunt",
                "product_id": item.get("objectID") or str(item.get("id") or ""),
                "title": item.get("name") or "",
                "url": producthunt_url(item),
                "price": "",
                "currency": "",
                "seller": ((item.get("user") or {}).get("username") or ""),
                "category": "Product Hunt post",
                "stock_status": item.get("product_state") or "listed",
                "rating": "",
                "review_count": item.get("vote_count") or "",
                "sales_volume": item.get("comments_count") or "",
                "last_updated": item.get("featured_at") or item.get("created_at") or "",
                "collected_at": collected_at,
                }
            )
        )
    return rows


def producthunt_url(item: dict[str, Any]) -> str:
    path = item.get("url") or ""
    if not path:
        slug = item.get("slug")
        path = f"/posts/{slug}" if slug else ""
    return f"https://www.producthunt.com{path}" if path.startswith("/") else path


def write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def write_config() -> None:
    config = {
        "analysis": {
            "top_n": 5,
            "stale_search_days": 3,
            "stale_product_days": 10000,
            "require_price": False,
        },
        "queries": [
            {
                "term": keyword["term"],
                "search_volume": 0,
                "expected_terms": keyword["expected_terms"],
                "forbidden_terms": ["template", "awesome-list-only"],
                "min_result_count": keyword["min_result_count"],
                "min_relevant_results": keyword["min_relevant_results"],
                "min_avg_relevance": keyword["min_avg_relevance"],
                "min_item_relevance": 0.34,
            }
            for keyword in KEYWORDS
        ],
        "sources": [
            {
                "name": "github",
                "type": "csv",
                "search_results_path": "data/search_results.github-ai.csv",
                "products_path": "data/products.github-ai.csv",
            },
            {
                "name": "producthunt",
                "type": "csv",
                "search_results_path": "data/search_results.producthunt-ai.csv",
                "products_path": "data/products.producthunt-ai.csv",
            },
        ],
    }
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
