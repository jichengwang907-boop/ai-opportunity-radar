from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


CONNECTORS = [
    {
        "name": "GitHub",
        "status": "optional_enabled_if_present",
        "required": ["GITHUB_TOKEN"],
        "purpose": "Higher API limits for repository trend collection.",
    },
    {
        "name": "YouTube",
        "status": "optional_api",
        "required": ["YOUTUBE_API_KEY"],
        "purpose": "Video/content demand collection.",
    },
    {
        "name": "X / Twitter",
        "status": "optional_api",
        "required": ["X_BEARER_TOKEN"],
        "alternatives": ["TWITTER_BEARER_TOKEN"],
        "purpose": "Recent social discussion collection.",
    },
    {
        "name": "Product Hunt Official API",
        "status": "reserved",
        "required": ["PRODUCTHUNT_TOKEN"],
        "purpose": "Official GraphQL product data once token is available.",
    },
    {
        "name": "PatentsView Search API",
        "status": "optional_api",
        "required": ["PATENTSVIEW_API_KEY"],
        "purpose": "US patent trend and commercialization signal.",
    },
    {
        "name": "DomainsDB",
        "status": "optional_api",
        "required": ["DOMAINSDB_API_KEY"],
        "purpose": "Registered domain and startup activity signal.",
    },
    {
        "name": "Google Ads Keyword Planner",
        "status": "reserved_or_import",
        "required": [
            "GOOGLE_ADS_DEVELOPER_TOKEN",
            "GOOGLE_ADS_CLIENT_ID",
            "GOOGLE_ADS_CLIENT_SECRET",
            "GOOGLE_ADS_REFRESH_TOKEN",
            "GOOGLE_ADS_CUSTOMER_ID",
        ],
        "purpose": "Keyword volume and commercial intent.",
    },
    {
        "name": "Amazon Product Advertising API",
        "status": "reserved_or_import",
        "required": ["AMAZON_ACCESS_KEY", "AMAZON_SECRET_KEY", "AMAZON_PARTNER_TAG"],
        "purpose": "Product demand, reviews, price, ratings.",
    },
    {
        "name": "eBay Browse API",
        "status": "reserved",
        "required": ["EBAY_CLIENT_ID", "EBAY_CLIENT_SECRET"],
        "alternatives": ["EBAY_OAUTH_TOKEN"],
        "purpose": "Listings, price, availability.",
    },
    {
        "name": "Etsy Open API",
        "status": "reserved",
        "required": ["ETSY_API_KEY"],
        "purpose": "Niche listing demand.",
    },
    {
        "name": "Taobao Open Platform",
        "status": "reserved_or_import",
        "required": ["TAOBAO_APP_KEY", "TAOBAO_APP_SECRET"],
        "alternatives": ["TAOBAO_SESSION"],
        "purpose": "China ecommerce supply, price, sales proxies.",
    },
    {
        "name": "JD Open Platform",
        "status": "reserved_or_import",
        "required": ["JD_APP_KEY", "JD_APP_SECRET"],
        "alternatives": ["JD_ACCESS_TOKEN"],
        "purpose": "China ecommerce supply, price, comments.",
    },
    {
        "name": "Similarweb",
        "status": "reserved_or_import",
        "required": ["SIMILARWEB_API_KEY"],
        "purpose": "Competitor traffic intelligence.",
    },
    {
        "name": "Ahrefs",
        "status": "reserved_or_import",
        "required": ["AHREFS_API_KEY"],
        "purpose": "SEO and keyword intelligence.",
    },
    {
        "name": "G2",
        "status": "reserved_or_import",
        "required": ["G2_API_KEY"],
        "purpose": "B2B review demand.",
    },
    {
        "name": "Capterra",
        "status": "reserved_or_import",
        "required": ["CAPTERRA_API_KEY"],
        "purpose": "B2B software category demand.",
    },
]


def main() -> int:
    load_env_file(ROOT / ".env.local")
    rows = [credential_status(connector) for connector in CONNECTORS]
    out = ROOT / "reports" / "credentials"
    out.mkdir(parents=True, exist_ok=True)
    (out / "status.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "status.md").write_text(markdown(rows), encoding="utf-8")

    configured = sum(1 for row in rows if row["configured"])
    print("Credential status generated")
    print(f"Configured: {configured}/{len(rows)}")
    print(f"Markdown: {out / 'status.md'}")
    print(f"JSON: {out / 'status.json'}")
    return 0


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


def credential_status(connector: dict[str, object]) -> dict[str, object]:
    required = list(connector.get("required") or [])
    alternatives = list(connector.get("alternatives") or [])
    present_required = [key for key in required if bool(os.environ.get(key))]
    present_alternatives = [key for key in alternatives if bool(os.environ.get(key))]
    configured = bool(required and len(present_required) == len(required)) or bool(present_alternatives)
    missing = [key for key in required if key not in present_required]
    return {
        "name": connector["name"],
        "status": connector["status"],
        "configured": configured,
        "present": present_required + present_alternatives,
        "missing": [] if configured else missing,
        "purpose": connector["purpose"],
    }


def markdown(rows: list[dict[str, object]]) -> str:
    lines = [
        "# 账号/API Key 接入状态",
        "",
        "这个报告只显示变量是否配置，不显示密钥内容。",
        "",
        "| 平台 | 状态 | 已配置 | 缺少变量 | 用途 |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        configured = "yes" if row["configured"] else "no"
        missing = ", ".join(row["missing"]) if row["missing"] else ""
        lines.append(
            f"| {row['name']} | {row['status']} | {configured} | {missing} | {row['purpose']} |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
