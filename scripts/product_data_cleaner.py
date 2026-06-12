from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

CLEANED_COLUMNS = [
    "source_row",
    "review_status",
    "readiness_score",
    "product_name",
    "listing_title",
    "sku",
    "price",
    "currency",
    "stock",
    "category",
    "image_url",
    "specs",
    "description",
    "source_url",
    "selling_points",
    "issues",
]

ISSUE_COLUMNS = [
    "source_row",
    "severity",
    "code",
    "field",
    "message",
    "value",
]

FIELD_ALIASES = {
    "product_name": (
        "product_name",
        "product title",
        "listing_title",
        "item_name",
        "title",
        "name",
        "商品名",
        "商品名称",
        "商品标题",
        "宝贝标题",
        "产品名称",
        "标题",
    ),
    "sku": (
        "sku",
        "product_id",
        "item_id",
        "seller_sku",
        "商品编码",
        "商家编码",
        "产品编码",
        "商品id",
        "货号",
        "编码",
    ),
    "price": (
        "price",
        "sale_price",
        "amount",
        "商品价格",
        "销售价",
        "售价",
        "价格",
        "现价",
        "人民币",
    ),
    "stock": (
        "stock",
        "stock_quantity",
        "quantity",
        "qty",
        "inventory",
        "库存",
        "数量",
        "可售库存",
    ),
    "category": (
        "category",
        "category_name",
        "product_category",
        "类目",
        "分类",
        "商品分类",
        "产品分类",
    ),
    "image_url": (
        "image_url",
        "main_image",
        "image",
        "img",
        "picture",
        "pic",
        "图片链接",
        "主图链接",
        "图片地址",
        "主图",
        "图片",
    ),
    "specs": (
        "specs",
        "specification",
        "variant",
        "option",
        "attributes",
        "规格",
        "规格属性",
        "属性",
        "型号",
        "颜色",
        "尺码",
    ),
    "description": (
        "description",
        "short_description",
        "details",
        "body",
        "copy",
        "商品描述",
        "短描述",
        "描述",
        "详情",
        "卖点",
        "文案",
    ),
    "source_url": (
        "url",
        "link",
        "product_url",
        "item_url",
        "source_url",
        "商品链接",
        "详情页",
        "链接",
        "地址",
    ),
}

HIGH_ISSUES = {"missing_product_name", "invalid_price", "duplicate_sku"}
MEDIUM_ISSUES = {"missing_price", "missing_sku", "missing_image_url", "invalid_stock"}
ISSUE_WEIGHTS = {
    "missing_product_name": 30,
    "invalid_price": 25,
    "duplicate_sku": 22,
    "missing_price": 18,
    "missing_sku": 12,
    "missing_image_url": 10,
    "invalid_image_url": 8,
    "invalid_stock": 8,
    "missing_category": 5,
}


@dataclass
class Issue:
    source_row: int
    severity: str
    code: str
    field: str
    message: str
    value: str = ""

    def as_row(self) -> dict[str, Any]:
        return {
            "source_row": self.source_row,
            "severity": self.severity,
            "code": self.code,
            "field": self.field,
            "message": self.message,
            "value": self.value,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean and standardize product listing spreadsheets.")
    parser.add_argument("--input", required=True, help="Input CSV or XLSX product sheet.")
    parser.add_argument("--out", default="reports/product-data-cleanup", help="Output directory.")
    parser.add_argument("--sheet", default="", help="Optional XLSX sheet name.")
    args = parser.parse_args()

    summary = clean_product_file(Path(args.input), Path(args.out), sheet_name=args.sheet)
    print("Product data cleanup generated")
    print(f"Input rows: {summary['input_rows']}")
    print(f"Cleaned rows: {summary['cleaned_rows']}")
    print(f"Ready rows: {summary['ready_rows']}")
    print(f"Needs review: {summary['needs_review_rows']}")
    print(f"Summary: {summary['summary_path']}")
    print(f"Cleaned CSV: {summary['cleaned_csv_path']}")
    print(f"Issues CSV: {summary['issues_csv_path']}")
    return 0


def clean_product_file(input_path: Path, out_dir: Path, sheet_name: str = "") -> dict[str, Any]:
    input_path = input_path.resolve()
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    out_dir = resolve_out_dir(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    records = read_records(input_path, sheet_name=sheet_name)
    field_mapping = detect_field_mapping(records)
    cleaned_rows, issues = clean_records(records, field_mapping)

    cleaned_csv = out_dir / "cleaned_products.csv"
    issues_csv = out_dir / "issues.csv"
    summary_md = out_dir / "summary.md"
    summary_json = out_dir / "summary.json"
    mapping_json = out_dir / "field_mapping.json"

    write_csv(cleaned_csv, CLEANED_COLUMNS, cleaned_rows)
    write_csv(issues_csv, ISSUE_COLUMNS, [issue.as_row() for issue in issues])

    summary = build_summary(input_path, records, cleaned_rows, issues, field_mapping)
    summary.update(
        {
            "summary_path": str(summary_md),
            "summary_json_path": str(summary_json),
            "cleaned_csv_path": str(cleaned_csv),
            "issues_csv_path": str(issues_csv),
            "field_mapping_path": str(mapping_json),
        }
    )

    summary_md.write_text(render_summary(summary, field_mapping), encoding="utf-8")
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    mapping_json.write_text(json.dumps(field_mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def resolve_out_dir(out_dir: Path) -> Path:
    return out_dir if out_dir.is_absolute() else ROOT / out_dir


def read_records(path: Path, sheet_name: str = "") -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return read_csv_records(path)
    if suffix == ".xlsx":
        return read_xlsx_records(path, preferred_sheet=sheet_name)
    raise ValueError("Only .csv and .xlsx files are supported.")


def read_csv_records(path: Path) -> list[dict[str, Any]]:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "gb18030", "utf-16"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                return [dict(row) for row in csv.DictReader(handle)]
        except UnicodeError as exc:
            last_error = exc
    if last_error:
        raise last_error
    return []


def read_xlsx_records(path: Path, preferred_sheet: str = "") -> list[dict[str, Any]]:
    with zipfile.ZipFile(path) as archive:
        shared_strings = read_shared_strings(archive)
        workbook_root = ET.fromstring(archive.read("xl/workbook.xml"))
        rels_root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rels = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels_root
            if rel.attrib.get("Id") and rel.attrib.get("Target")
        }
        ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
        sheets = workbook_root.findall(f".//{ns}sheet")
        selected = None
        for sheet in sheets:
            if preferred_sheet and sheet.attrib.get("name") == preferred_sheet:
                selected = sheet
                break
        if selected is None:
            selected = sheets[0] if sheets else None
        if selected is None:
            return []
        rel_id = selected.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        target = rels.get(rel_id or "", "")
        if not target:
            return []
        matrix = read_sheet_matrix(archive, workbook_target_path(target), shared_strings)
    if not matrix:
        return []
    headers = [clean_text(value) for value in matrix[0]]
    return [
        dict(zip(headers, row))
        for row in matrix[1:]
        if any(clean_text(value) for value in row)
    ]


def workbook_target_path(target: str) -> str:
    normalized = target.replace("\\", "/").lstrip("/")
    return normalized if normalized.startswith("xl/") else f"xl/{normalized}"


def read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    values: list[str] = []
    for item in root.findall(f"{ns}si"):
        values.append("".join(node.text or "" for node in item.findall(f".//{ns}t")))
    return values


def read_sheet_matrix(archive: zipfile.ZipFile, sheet_path: str, shared_strings: list[str]) -> list[list[Any]]:
    root = ET.fromstring(archive.read(sheet_path))
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    rows: list[list[Any]] = []
    for row_node in root.findall(f".//{ns}row"):
        row_values: list[Any] = []
        for cell in row_node.findall(f"{ns}c"):
            column = column_index(cell.attrib.get("r", ""))
            while len(row_values) < column:
                row_values.append("")
            row_values[column - 1] = cell_value(cell, shared_strings)
        rows.append(row_values)
    width = max((len(row) for row in rows), default=0)
    for row in rows:
        row.extend([""] * (width - len(row)))
    return rows


def cell_value(cell: ET.Element, shared_strings: list[str]) -> Any:
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    cell_type = cell.attrib.get("t", "")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(f".//{ns}t"))
    value = cell.find(f"{ns}v")
    text = value.text if value is not None else ""
    if cell_type == "s":
        try:
            return shared_strings[int(text)]
        except (ValueError, IndexError):
            return ""
    return text or ""


def column_index(cell_ref: str) -> int:
    match = re.match(r"([A-Z]+)", cell_ref.upper())
    if not match:
        return 1
    result = 0
    for char in match.group(1):
        result = result * 26 + (ord(char) - ord("A") + 1)
    return result


def detect_field_mapping(records: list[dict[str, Any]]) -> dict[str, str]:
    headers = list(records[0].keys()) if records else []
    mapping: dict[str, str] = {}
    used: set[str] = set()
    candidates: list[tuple[int, str, str]] = []
    for canonical, aliases in FIELD_ALIASES.items():
        normalized_aliases = [clean_key(alias) for alias in aliases]
        for header in headers:
            score = field_match_score(clean_key(header), normalized_aliases)
            if score:
                candidates.append((score, canonical, header))

    for score, canonical, header in sorted(candidates, reverse=True):
        if canonical not in mapping and header not in used:
            mapping[canonical] = header
            used.add(header)
    return mapping


def field_match_score(header_key: str, aliases: list[str]) -> int:
    if not header_key:
        return 0
    if header_key in aliases:
        return 100
    for alias in aliases:
        if alias and alias in header_key:
            return 75
    for alias in aliases:
        if header_key and header_key in alias and len(header_key) >= 3:
            return 55
    return 0


def clean_records(records: list[dict[str, Any]], mapping: dict[str, str]) -> tuple[list[dict[str, Any]], list[Issue]]:
    sku_counts = Counter(
        clean_text(row.get(mapping.get("sku", ""), ""))
        for row in records
        if mapping.get("sku") and clean_text(row.get(mapping.get("sku", ""), ""))
    )
    title_counts = Counter(
        clean_text(row.get(mapping.get("product_name", ""), ""))
        for row in records
        if mapping.get("product_name") and clean_text(row.get(mapping.get("product_name", ""), ""))
    )

    cleaned_rows: list[dict[str, Any]] = []
    all_issues: list[Issue] = []
    for row_number, row in enumerate(records, start=2):
        cleaned, issues = clean_one_record(row, row_number, mapping, sku_counts, title_counts)
        cleaned_rows.append(cleaned)
        all_issues.extend(issues)
    return cleaned_rows, all_issues


def clean_one_record(
    row: dict[str, Any],
    row_number: int,
    mapping: dict[str, str],
    sku_counts: Counter[str],
    title_counts: Counter[str],
) -> tuple[dict[str, Any], list[Issue]]:
    product_name = get_mapped(row, mapping, "product_name")
    sku = get_mapped(row, mapping, "sku")
    raw_price = get_mapped(row, mapping, "price")
    raw_stock = get_mapped(row, mapping, "stock")
    category = get_mapped(row, mapping, "category")
    image_url = get_mapped(row, mapping, "image_url")
    specs = get_mapped(row, mapping, "specs")
    description = get_mapped(row, mapping, "description")
    source_url = get_mapped(row, mapping, "source_url")

    price, currency, price_valid = parse_price(raw_price)
    stock, stock_valid = parse_stock(raw_stock)
    issues: list[Issue] = []

    if not product_name:
        issues.append(issue(row_number, "missing_product_name", "product_name", "缺少商品标题或商品名称。"))
    if not sku:
        issues.append(issue(row_number, "missing_sku", "sku", "缺少 SKU/商家编码，后续去重和导入会变弱。"))
    elif sku_counts[sku] > 1:
        issues.append(issue(row_number, "duplicate_sku", "sku", "SKU/商家编码重复。", sku))
    if product_name and title_counts[product_name] > 1:
        issues.append(issue(row_number, "duplicate_title", "product_name", "商品标题重复，建议人工确认是否为不同 SKU。", product_name))
    if not raw_price:
        issues.append(issue(row_number, "missing_price", "price", "缺少价格。"))
    elif not price_valid:
        issues.append(issue(row_number, "invalid_price", "price", "价格无法解析或小于 0。", raw_price))
    if raw_stock and not stock_valid:
        issues.append(issue(row_number, "invalid_stock", "stock", "库存无法解析。", raw_stock))
    if not image_url:
        issues.append(issue(row_number, "missing_image_url", "image_url", "缺少主图或图片链接。"))
    elif not looks_like_image_url(image_url):
        issues.append(issue(row_number, "invalid_image_url", "image_url", "图片链接看起来不是有效 URL 或图片路径。", image_url))
    if not category:
        issues.append(issue(row_number, "missing_category", "category", "缺少商品分类/类目。"))

    score = readiness_score(issues)
    blocking_issues = {"high", "medium"}
    status = "ready" if score >= 85 and not any(item.severity in blocking_issues for item in issues) else "needs_review"
    issue_codes = ";".join(item.code for item in issues)
    listing_title = build_listing_title(product_name, specs, category)
    selling_points = build_selling_points(category, specs, price, currency)

    return (
        {
            "source_row": row_number,
            "review_status": status,
            "readiness_score": score,
            "product_name": product_name,
            "listing_title": listing_title,
            "sku": sku,
            "price": format_number(price) if price is not None else "",
            "currency": currency,
            "stock": stock if stock is not None else "",
            "category": category,
            "image_url": image_url,
            "specs": specs,
            "description": description,
            "source_url": source_url,
            "selling_points": selling_points,
            "issues": issue_codes,
        },
        issues,
    )


def issue(row_number: int, code: str, field: str, message: str, value: str = "") -> Issue:
    severity = "high" if code in HIGH_ISSUES else "medium" if code in MEDIUM_ISSUES else "low"
    return Issue(row_number, severity, code, field, message, value)


def get_mapped(row: dict[str, Any], mapping: dict[str, str], field: str) -> str:
    header = mapping.get(field)
    return clean_text(row.get(header, "")) if header else ""


def parse_price(value: str) -> tuple[float | None, str, bool]:
    text = clean_text(value)
    if not text:
        return None, "", True
    currency = detect_currency(text)
    match = re.search(r"-?\d+(?:,\d{3})*(?:\.\d+)?|-?\d+(?:\.\d+)?", text)
    if not match:
        return None, currency, False
    try:
        number = float(match.group(0).replace(",", ""))
    except ValueError:
        return None, currency, False
    if number < 0:
        return number, currency, False
    return number, currency, True


def parse_stock(value: str) -> tuple[int | None, bool]:
    text = clean_text(value)
    if not text:
        return None, True
    match = re.search(r"-?\d+", text.replace(",", ""))
    if not match:
        return None, False
    number = int(match.group(0))
    return number, number >= 0


def detect_currency(text: str) -> str:
    lowered = text.lower()
    if "usd" in lowered or "$" in text:
        return "USD"
    if "eur" in lowered or "€" in text:
        return "EUR"
    if "gbp" in lowered or "£" in text:
        return "GBP"
    if "cny" in lowered or "rmb" in lowered or "￥" in text or "¥" in text or "元" in text:
        return "CNY"
    return ""


def looks_like_image_url(value: str) -> bool:
    lowered = value.lower()
    if lowered.startswith(("http://", "https://")):
        return True
    return lowered.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif"))


def build_listing_title(product_name: str, specs: str, category: str) -> str:
    parts = [product_name]
    if specs and specs not in product_name:
        parts.append(specs)
    if not product_name and category:
        parts.append(category)
    title = clean_text(" ".join(part for part in parts if part))
    return title[:120]


def build_selling_points(category: str, specs: str, price: float | None, currency: str) -> str:
    points = []
    if category:
        points.append(f"类目清晰：{category}")
    if specs:
        points.append(f"规格明确：{specs}")
    if price is not None:
        label = f"{currency} {format_number(price)}".strip()
        points.append(f"价格已标准化：{label}")
    return "；".join(points[:3])


def readiness_score(issues: list[Issue]) -> int:
    penalty = sum(ISSUE_WEIGHTS.get(item.code, 3) for item in issues)
    return max(0, min(100, 100 - penalty))


def build_summary(
    input_path: Path,
    records: list[dict[str, Any]],
    cleaned_rows: list[dict[str, Any]],
    issues: list[Issue],
    field_mapping: dict[str, str],
) -> dict[str, Any]:
    severity_counts = Counter(item.severity for item in issues)
    issue_counts = Counter(item.code for item in issues)
    ready_rows = sum(1 for row in cleaned_rows if row["review_status"] == "ready")
    needs_review_rows = len(cleaned_rows) - ready_rows
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_path": str(input_path),
        "input_rows": len(records),
        "cleaned_rows": len(cleaned_rows),
        "ready_rows": ready_rows,
        "needs_review_rows": needs_review_rows,
        "issue_rows": len({item.source_row for item in issues}),
        "issue_count": len(issues),
        "severity_counts": dict(sorted(severity_counts.items())),
        "top_issue_codes": issue_counts.most_common(10),
        "field_mapping": field_mapping,
        "unmapped_fields": [
            field for field in FIELD_ALIASES if field not in field_mapping
        ],
    }


def render_summary(summary: dict[str, Any], field_mapping: dict[str, str]) -> str:
    lines = [
        "# 商品资料整理报告",
        "",
        f"- 生成时间：{summary['generated_at']}",
        f"- 输入文件：`{summary['input_path']}`",
        f"- 输入行数：{summary['input_rows']}",
        f"- 输出行数：{summary['cleaned_rows']}",
        f"- 可直接复核通过：{summary['ready_rows']}",
        f"- 需要人工复核：{summary['needs_review_rows']}",
        f"- 问题总数：{summary['issue_count']}",
        "",
        "## 字段识别",
        "",
    ]
    if field_mapping:
        for field, header in field_mapping.items():
            lines.append(f"- `{field}` <- `{header}`")
    else:
        lines.append("- 未识别到可用字段。")

    lines.extend(["", "## 主要问题", ""])
    if summary["top_issue_codes"]:
        for code, count in summary["top_issue_codes"]:
            lines.append(f"- `{code}`：{count}")
    else:
        lines.append("- 暂未发现明显问题。")

    lines.extend(
        [
            "",
            "## 输出文件",
            "",
            f"- 整理后商品表：`{summary['cleaned_csv_path']}`",
            f"- 问题明细：`{summary['issues_csv_path']}`",
            f"- 字段映射：`{summary['field_mapping_path']}`",
            "",
            "## 建议下一步",
            "",
            "- 先处理 high 和 medium 问题行。",
            "- 将 `cleaned_products.csv` 作为人工复核或平台导入前的中间表。",
            "- 如果某个字段识别错误，调整源表表头后重新运行。",
        ]
    )
    return "\n".join(lines) + "\n"


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    text = text.replace("\ufeff", "").replace("\u200b", "").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def clean_key(value: Any) -> str:
    text = clean_text(value).lower()
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", text)


def format_number(value: float) -> str:
    return str(int(value)) if value.is_integer() else f"{value:.2f}".rstrip("0").rstrip(".")


def write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


if __name__ == "__main__":
    raise SystemExit(main())
