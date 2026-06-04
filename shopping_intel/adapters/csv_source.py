from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from shopping_intel.config import resolve_path
from shopping_intel.models import Product, SearchResult


class CSVSource:
    """Reads normalized search and product snapshots from CSV exports."""

    def __init__(self, source_config: dict[str, Any], base_dir: str | Path):
        self.config = source_config
        self.name = str(source_config.get("name") or "csv").strip()
        self.source_filter = str(source_config.get("source_filter") or "").strip()
        self.base_dir = Path(base_dir)

    def collect_search_results(self, queries: list[dict[str, Any]]) -> list[SearchResult]:
        path = resolve_path(self.base_dir, self.config.get("search_results_path"))
        rows = [
            SearchResult.from_record(row, default_source=self.name)
            for row in self._read_rows(path)
        ]
        if self.source_filter:
            rows = [row for row in rows if row.source == self.source_filter]
        return rows

    def collect_products(self) -> list[Product]:
        path = resolve_path(self.base_dir, self.config.get("products_path"))
        rows = [
            Product.from_record(row, default_source=self.name)
            for row in self._read_rows(path)
        ]
        if self.source_filter:
            rows = [row for row in rows if row.source == self.source_filter]
        return rows

    @staticmethod
    def _read_rows(path: Path | None) -> list[dict[str, str]]:
        if path is None or not path.exists():
            return []
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
