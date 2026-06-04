from __future__ import annotations

import argparse
from pathlib import Path

from shopping_intel.adapters.factory import build_sources
from shopping_intel.analysis import analyze
from shopping_intel.config import load_config
from shopping_intel.report import write_reports


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Monitor shopping search quality and product freshness."
    )
    parser.add_argument(
        "--config",
        default="config.example.json",
        help="Path to JSON config.",
    )
    parser.add_argument(
        "--out",
        default="reports/latest",
        help="Output directory for reports.",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    search_results = []
    products = []

    for source in build_sources(config):
        search_results.extend(source.collect_search_results(config.get("queries") or []))
        products.extend(source.collect_products())

    result = analyze(config, search_results, products)
    paths = write_reports(result, Path(args.out))

    summary = result["summary"]
    print("Shopping intelligence report generated")
    print(f"Sources: {', '.join(summary.get('sources') or [])}")
    print(f"Search rows: {summary['search_result_rows']}")
    print(f"Product rows: {summary['product_rows']}")
    print(f"Anomalies: {summary['anomaly_count']} {summary['severity_counts']}")
    print(f"Markdown: {paths['markdown']}")
    print(f"CSV: {paths['csv']}")
    print(f"JSON: {paths['json']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
