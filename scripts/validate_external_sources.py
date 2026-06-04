from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

NUMERIC_FIELDS = {
    "rank",
    "result_count",
    "search_volume",
    "price",
    "rating",
    "review_count",
    "sales_volume",
    "metric_value",
}

DATE_FIELDS = {"collected_at", "last_updated", "date_found", "updated_at"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate external CSV data before importing it.")
    parser.add_argument("--input", default="data/external_sources.csv")
    parser.add_argument("--report-out", default="reports/data-quality")
    parser.add_argument("--max-age-days", type=int, default=30)
    args = parser.parse_args()

    input_path = resolve(args.input)
    report_dir = resolve(args.report_out)
    report_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        report = {
            "status": "no_input",
            "generated_at": now_iso(),
            "input": str(input_path),
            "quality_score": 0,
            "errors": [],
            "warnings": [
                "未发现 data/external_sources.csv；如果不用外部导出数据，可以忽略此提示。"
            ],
            "summary": {"rows": 0, "sources": {}},
        }
        write_report(report_dir, report)
        print("No external_sources.csv found; data quality check skipped.")
        return 0

    rows, headers = read_rows(input_path)
    report = validate_rows(rows, headers, input_path, args.max_age_days)
    write_report(report_dir, report)

    print("External data quality report generated")
    print(f"Rows: {report['summary']['rows']}")
    print(f"Status: {report['status']}")
    print(f"Quality score: {report['quality_score']}")
    print(f"Errors: {len(report['errors'])}")
    print(f"Warnings: {len(report['warnings'])}")
    return 1 if report["errors"] else 0


def validate_rows(
    rows: list[dict[str, str]],
    headers: list[str],
    input_path: Path,
    max_age_days: int,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    normalized_headers = {clean_key(header) for header in headers}

    if not headers:
        errors.append("CSV 没有表头。")
    if not rows:
        errors.append("CSV 没有数据行。")

    for required in ("source",):
        if required not in normalized_headers:
            errors.append(f"缺少必要字段：{required}")

    if "query" not in normalized_headers and "keyword" not in normalized_headers:
        warnings.append("缺少 query/keyword 字段；搜索需求分析会变弱。")
    if "title" not in normalized_headers and "name" not in normalized_headers and "product_name" not in normalized_headers:
        warnings.append("缺少 title/name/product_name 字段；产品识别会变弱。")
    if not normalized_headers.intersection(DATE_FIELDS):
        warnings.append("缺少 collected_at/last_updated/date_found/updated_at 日期字段；无法判断数据新鲜度。")

    seen: Counter[tuple[str, str, str, str]] = Counter()
    source_counts: Counter[str] = Counter()
    numeric_checked = 0
    numeric_invalid = 0
    date_checked = 0
    stale_rows = 0
    complete_core_rows = 0

    today = datetime.now(timezone.utc)
    for index, raw_row in enumerate(rows, start=2):
        row = {clean_key(key): value for key, value in raw_row.items()}
        source = field(row, "source", "platform")
        query = field(row, "query", "keyword", "search_term")
        title = field(row, "title", "name", "product_name", "listing_title")
        url = field(row, "url", "link")

        if not source:
            errors.append(f"第 {index} 行缺少 source。")
        else:
            source_counts[source] += 1
        if not query and not title:
            errors.append(f"第 {index} 行 query 和 title 至少要有一个。")
        if source and (query or title):
            complete_core_rows += 1

        if url and not re.match(r"^https?://", url, flags=re.IGNORECASE):
            warnings.append(f"第 {index} 行 URL 格式不像网页链接：{url}")

        signature = (source.lower(), query.lower(), title.lower(), url.lower())
        seen[signature] += 1

        for key in NUMERIC_FIELDS:
            value = field(row, key)
            if not value:
                continue
            numeric_checked += 1
            if not is_number(value):
                numeric_invalid += 1
                warnings.append(f"第 {index} 行 {key} 不是有效数字：{value}")
                continue
            number = float(str(value).replace(",", "").strip())
            if number < 0:
                numeric_invalid += 1
                warnings.append(f"第 {index} 行 {key} 是负数：{value}")
            if key == "rating" and number > 5:
                warnings.append(f"第 {index} 行 rating 大于 5，请确认评分制：{value}")

        newest_date = None
        for key in DATE_FIELDS:
            value = field(row, key)
            if not value:
                continue
            date_checked += 1
            parsed = parse_datetime(value)
            if parsed is None:
                warnings.append(f"第 {index} 行 {key} 日期无法识别：{value}")
                continue
            newest_date = max(newest_date, parsed) if newest_date else parsed

        if newest_date:
            age = max(0, (today - newest_date).days)
            if age > max_age_days:
                stale_rows += 1
                warnings.append(f"第 {index} 行数据已 {age} 天未更新，超过 {max_age_days} 天。")

    duplicate_count = sum(count - 1 for count in seen.values() if count > 1)
    if duplicate_count:
        warnings.append(f"发现 {duplicate_count} 条重复数据，导入时会尽量去重。")
    if len(rows) < 5:
        warnings.append("样本少于 5 行，只适合做线索，不适合下结论。")
    if len(source_counts) < 2 and rows:
        warnings.append("只有 1 个数据来源，建议至少用 2-3 个来源交叉验证。")

    completeness = round(complete_core_rows / len(rows), 4) if rows else 0
    score = max(
        0,
        min(
            100,
            100
            - len(errors) * 18
            - len(warnings) * 3
            - numeric_invalid * 2
            - stale_rows * 2,
        ),
    )
    if errors:
        status = "blocked"
    elif score >= 80 and len(source_counts) >= 2:
        status = "usable"
    elif score >= 60:
        status = "needs_review"
    else:
        status = "weak"

    return {
        "status": status,
        "generated_at": now_iso(),
        "input": str(input_path),
        "quality_score": score,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "rows": len(rows),
            "headers": headers,
            "sources": dict(sorted(source_counts.items())),
            "source_count": len(source_counts),
            "core_completeness": completeness,
            "numeric_checked": numeric_checked,
            "numeric_invalid": numeric_invalid,
            "date_checked": date_checked,
            "stale_rows": stale_rows,
            "duplicate_rows": duplicate_count,
        },
    }


def read_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def write_report(out: Path, report: dict[str, Any]) -> None:
    json_path = out / "external_sources_quality.json"
    md_path = out / "external_sources_quality.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = report.get("summary") or {}
    lines = [
        "# 外部导入数据质量报告",
        "",
        f"- 状态：{report.get('status', '')}",
        f"- 质量分：{report.get('quality_score', 0)}",
        f"- 数据行：{summary.get('rows', 0)}",
        f"- 来源数：{summary.get('source_count', 0)}",
        f"- 核心字段完整率：{summary.get('core_completeness', 0)}",
        f"- 重复行：{summary.get('duplicate_rows', 0)}",
        f"- 过期行：{summary.get('stale_rows', 0)}",
        "",
        "## 来源分布",
        "",
    ]
    sources = summary.get("sources") or {}
    if sources:
        for source, count in sources.items():
            lines.append(f"- {source}: {count}")
    else:
        lines.append("- 无")

    lines.extend(["", "## 错误", ""])
    if report.get("errors"):
        lines.extend(f"- {item}" for item in report["errors"])
    else:
        lines.append("- 无")

    lines.extend(["", "## 警告", ""])
    if report.get("warnings"):
        lines.extend(f"- {item}" for item in report["warnings"][:80])
    else:
        lines.append("- 无")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def resolve(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


def clean_key(key: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(key or "").strip().lower()).strip("_")


def field(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = row.get(clean_key(key), "")
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def is_number(value: str) -> bool:
    try:
        float(str(value).replace(",", "").strip())
        return True
    except ValueError:
        return False


def parse_datetime(value: str) -> datetime | None:
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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
