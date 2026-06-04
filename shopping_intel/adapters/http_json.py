from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from shopping_intel.models import Product, SearchResult


class HTTPJSONSource:
    """Generic adapter for official APIs that return JSON.

    Configure item paths and field mappings in config.example.json. This adapter
    does not bypass logins, captchas, or platform anti-bot controls.
    """

    def __init__(self, source_config: dict[str, Any], base_dir: str | Path):
        self.config = source_config
        self.name = str(source_config.get("name") or "http_json").strip()
        self.timeout = float(source_config.get("timeout_seconds") or 20)
        self.headers = dict(source_config.get("headers") or {})

    def collect_search_results(self, queries: list[dict[str, Any]]) -> list[SearchResult]:
        url_template = self.config.get("search_url")
        if not url_template:
            return []

        results: list[SearchResult] = []
        for query_config in queries:
            query = str(query_config.get("term") or "").strip()
            if not query:
                continue
            url = url_template.format(query=urllib.parse.quote(query))
            payload = self._get_json(url)
            items = _select(payload, self.config.get("search_items_path") or "")
            if isinstance(items, dict):
                items = [items]
            if not isinstance(items, list):
                continue

            for index, item in enumerate(items, start=1):
                if not isinstance(item, dict):
                    continue
                record = _map_record(item, self.config.get("search_mapping") or {})
                record.setdefault("source", self.name)
                record.setdefault("query", query)
                record.setdefault("rank", index)
                if "result_count" not in record:
                    total = _select(payload, self.config.get("result_count_path") or "")
                    if total not in (None, ""):
                        record["result_count"] = total
                results.append(SearchResult.from_record(record, default_source=self.name))
        return results

    def collect_products(self) -> list[Product]:
        url = self.config.get("products_url")
        if not url:
            return []

        payload = self._get_json(url)
        items = _select(payload, self.config.get("product_items_path") or "")
        if isinstance(items, dict):
            items = [items]
        if not isinstance(items, list):
            return []

        products: list[Product] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            record = _map_record(item, self.config.get("product_mapping") or {})
            record.setdefault("source", self.name)
            products.append(Product.from_record(record, default_source=self.name))
        return products

    def _get_json(self, url: str) -> Any:
        request = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            body = response.read().decode("utf-8")
        return json.loads(body)


def _map_record(item: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
    if not mapping:
        return dict(item)
    return {field: _select(item, path) for field, path in mapping.items()}


def _select(payload: Any, path: str) -> Any:
    if not path:
        return payload
    current = payload
    for part in path.split("."):
        if current is None:
            return None
        if isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current
