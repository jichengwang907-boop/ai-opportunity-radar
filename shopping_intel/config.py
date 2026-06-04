from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path).resolve()
    with config_path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    config["_config_path"] = str(config_path)
    config["_base_dir"] = str(config_path.parent)
    return config


def resolve_path(base_dir: str | Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return Path(base_dir) / path


def source_names(config: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for source in config.get("sources", []):
        name = str(source.get("name") or source.get("type") or "").strip()
        if name:
            names.append(name)
    return names
