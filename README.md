# AI Opportunity Radar

AI Opportunity Radar is a local-first market research toolkit for indie hackers, small teams, and solo builders. It collects public market signals, imports manual research data, scores opportunity areas, and generates readable reports to help decide which AI product idea is worth validating next.

中文简介：AI 机会雷达是一个本地优先的 AI 产品机会分析工具。它可以采集公开市场信号、导入人工调研数据、生成机会评分和报告，帮助个人创业者和小团队判断下一个 AI 小产品方向是否值得验证。

## What It Does

- Collects public signals from sources such as GitHub, Product Hunt, Hacker News, Reddit, Google News, YouTube, Google Trends exports, and other optional APIs.
- Imports manually collected CSV/XLSX research data.
- Cleans product listing spreadsheets into a standardized review-ready CSV.
- Scores opportunity areas using demand, supply, commercial proof, buyer intent, execution feasibility, and evidence confidence.
- Generates Markdown, CSV, and JSON reports.
- Provides a Windows desktop app for non-technical use.
- Keeps secrets and raw research data local by default.

## Project Status

The project is usable as a local research assistant, desktop app, and first MVP utility for product data cleanup. It is not a revenue prediction engine and should not be treated as financial advice. Its job is to help you organize evidence and choose what to validate next.

Current validated directions from the local research run include:

- AI product data cleanup / product listing assistant
- AI invoice, receipt, and bank statement organizer
- AI document processing
- AI customer support
- AI lead generation

## Repository Layout

```text
shopping_intel/                 Core data models, adapters, analysis, reports
scripts/                        Collectors, importers, report generators, desktop app
tests/                          Unit tests
data/*.sample.csv               Small sample data safe for GitHub
data/*.template.csv             Manual import templates
config.example.json             Minimal sample config for the core CLI
config.realtime-ai-platforms.json
                                Larger public-signal config for the AI radar
config.product-demand-sources.json
                                Demand-source catalog config
run_ai_radar.bat                Full Windows pipeline
AI机会雷达桌面版.bat              Desktop app launcher
build_desktop_exe.bat           Optional PyInstaller build script
```

Generated files such as `reports/`, `data/raw/`, `data/tmp/`, `build/`, `dist/`, `.env.local`, and full local CSV outputs are intentionally ignored.

## Quick Start

Requirements:

- Python 3.11+
- Windows is recommended for the desktop app and batch scripts
- No required Python packages for the core pipeline

Run the sample CLI:

```powershell
py -m shopping_intel.cli --config config.example.json --out reports/latest
```

Run tests:

```powershell
py -m unittest discover -s tests
```

Run the product data cleanup MVP on sample data:

```powershell
py -B scripts\product_data_cleaner.py --input data\product_data_cleanup.sample.csv --out reports\product-data-cleanup
```

Launch the desktop app:

```powershell
.\AI机会雷达桌面版.bat
```

Run the full AI radar pipeline:

```powershell
.\run_ai_radar.bat
```

The full pipeline can run with public/no-token sources, but optional API keys improve coverage and rate limits.

## Desktop App

The desktop app is implemented with Tkinter and uses only the Python standard library. It supports:

- Import Excel or CSV manual research data
- Clean product listing Excel/CSV sheets and generate a review report
- Run the full analysis pipeline
- Rebuild reports without collecting new online data
- Open opportunity, product feedback, realtime signal, and project folders
- Fast mode that skips arXiv to avoid rate-limit stalls
- DPI-aware Windows rendering for clear fonts

Build a one-file Windows executable:

```powershell
py -m pip install pyinstaller
.\build_desktop_exe.bat
```

The executable is generated under `dist/`, which is ignored by Git.

## Optional API Keys

Copy `.env.example` to `.env.local` and fill only the services you want to enable:

```powershell
Copy-Item .env.example .env.local
py -B scripts\setup_tokens.py --status
```

Common optional keys:

- `GITHUB_TOKEN` for higher GitHub API limits
- `YOUTUBE_API_KEY` for YouTube Data API
- `X_BEARER_TOKEN` for X/Twitter recent search
- `PATENTSVIEW_API_KEY`
- `DOMAINSDB_API_KEY`
- `PRODUCTHUNT_TOKEN`

Do not commit `.env.local`.

## Data Import

Manual research can be imported through:

- `data/external_sources.template.csv`
- the desktop app's Excel/CSV import button
- `scripts/validate_external_sources.py`
- `scripts/import_external_sources.py`

The importer is designed for exported platform data, Google Trends CSVs, manually collected product research, and other no-token sources.

## Product Data Cleanup MVP

The first standalone MVP module targets a concrete workflow found during research: merchants and small teams often keep messy product listing data in Excel/CSV before uploading it to marketplaces, ERP systems, or service providers.

Use it to:

- Detect product name, SKU, price, stock, category, image URL, specs, description, and source URL columns.
- Normalize prices, currency labels, stock values, titles, and selling-point snippets.
- Flag duplicate SKU/title rows, missing required fields, invalid prices, invalid stock, and invalid image links.
- Export `cleaned_products.csv`, `issues.csv`, `field_mapping.json`, `summary.json`, and `summary.md`.

CLI:

```powershell
py -B scripts\product_data_cleaner.py --input path\to\products.xlsx --out reports\product-data-cleanup
```

Desktop:

```text
AI 机会雷达 -> 整理商品资料表（MVP）
```

## Reports

Typical outputs:

```text
reports/realtime-ai/summary.md
reports/realtime-ai/analysis.json
reports/product-feedback/products.md
reports/product-data-cleanup/summary.md
reports/opportunity-radar/opportunities.md
reports/product-demand-sources/sources.md
```

Reports are ignored because they may contain local research data.

## Limitations

- Public APIs can rate-limit or change behavior.
- Some sources require optional API keys.
- Scores are evidence summaries, not proof of demand or revenue.
- The project does not bypass platform login, anti-bot systems, or paid data restrictions.
- User interviews, public pain-point evidence, and paid tests are still required before building a product.

## Roadmap

- Validate the product data cleanup MVP with real merchant spreadsheets.
- Add an invoice/receipt/statement organizer MVP module.
- Improve source health tracking and retry policies.
- Add more sample datasets and screenshots.
- Package a cleaner desktop release workflow.

## License

MIT License. See [LICENSE](LICENSE).
