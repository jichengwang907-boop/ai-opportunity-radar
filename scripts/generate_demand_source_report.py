from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a product demand source catalog report.")
    parser.add_argument("--config", default="config.product-demand-sources.json")
    parser.add_argument("--out", default="reports/product-demand-sources")
    args = parser.parse_args()

    config_path = Path(args.config)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    sources = config.get("sources") or []

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    markdown_path = out / "sources.md"
    csv_path = out / "sources.csv"
    json_path = out / "sources.json"

    json_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(sources, csv_path)
    markdown_path.write_text(markdown(config), encoding="utf-8")

    print("Product demand source report generated")
    print(f"Sources: {len(sources)}")
    print(f"Markdown: {markdown_path}")
    print(f"CSV: {csv_path}")
    print(f"JSON: {json_path}")
    return 0


def write_csv(sources: list[dict[str, Any]], path: Path) -> None:
    columns = [
        "name",
        "category",
        "website",
        "api_or_docs",
        "demand_signal",
        "access_method",
        "auth_required",
        "project_status",
        "priority",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for source in sources:
            writer.writerow({column: source.get(column, "") for column in columns})


def markdown(config: dict[str, Any]) -> str:
    sources = config.get("sources") or []
    lines = [
        "# 产品需求数据源目录",
        "",
        "这个目录回答两个问题：去哪些网站获取产品需求数据，以及每个网站能证明什么。",
        "",
        f"- 更新时间：{config.get('updated_at', '')}",
        f"- 数据源数量：{len(sources)}",
        "",
        "## 数据源清单",
        "",
        "| 数据源 | 类别 | 当前状态 | 优先级 | 网站 | 获取方式 | 需求信号 |",
        "|---|---|---|---|---|---|---|",
    ]
    for source in sources:
        lines.append(
            "| {name} | {category} | {project_status} | {priority} | "
            "[网站]({website}) | {access_method} | {demand_signal} |".format(**source)
        )

    lines.extend(
        [
            "",
            "## 当前已自动拉取",
            "",
            "- Product Hunt",
            "- Reddit",
            "- Google News",
            "- Hacker News",
            "- GitHub",
            "- arXiv",
            "- Hugging Face Models",
            "- Hugging Face Spaces",
            "",
            "## 需要账号或导出的来源",
            "",
            "- YouTube：设置 `YOUTUBE_API_KEY` 后可启用。",
            "- X/Twitter：设置 `X_BEARER_TOKEN` 后可启用。",
            "- Google Trends、Google Ads、G2、Capterra、Amazon、淘宝、京东：优先用官方 API 或后台导出，再按 `data/external_sources.template.csv` 导入。",
            "",
            "## 判断口径",
            "",
            "单一网站不能证明需求真实。更可靠的判断来自组合信号：",
            "",
            "```text",
            "搜索兴趣 + 用户讨论 + 产品发布 + 评论/销量 + 竞品流量 + 技术供给",
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
