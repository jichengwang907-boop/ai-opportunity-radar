from __future__ import annotations

from pathlib import Path
from typing import Any

from shopping_intel.adapters.csv_source import CSVSource
from shopping_intel.adapters.http_json import HTTPJSONSource


def build_sources(config: dict[str, Any]) -> list[Any]:
    base_dir = Path(config.get("_base_dir") or ".")
    sources = []
    for source_config in config.get("sources", []):
        source_type = str(source_config.get("type") or "").strip().lower()
        if source_type == "csv":
            sources.append(CSVSource(source_config, base_dir))
        elif source_type == "http_json":
            sources.append(HTTPJSONSource(source_config, base_dir))
        else:
            raise ValueError(f"Unsupported source type: {source_type!r}")
    return sources
