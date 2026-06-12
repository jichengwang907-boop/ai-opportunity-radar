# Project Status

AI Opportunity Radar started as a local shopping/search intelligence monitor and has evolved into a local-first AI product opportunity radar.

## Completed

- Core CSV and HTTP JSON adapter pipeline
- Public AI market signal collector
- External CSV/XLSX import support
- Google Trends CSV import support
- Opportunity scoring report
- Product feedback report
- Demand source catalog report
- Credential status checker
- Windows desktop app
- PyInstaller build script
- DPI-aware desktop UI
- Product data cleanup MVP module

## Current Best Opportunity Areas

- AI product data cleanup / product listing assistant
- AI invoice, receipt, and bank statement organizer
- AI document processing
- AI customer support
- AI lead generation

## Current Gaps

- First standalone MVP exists, but still needs validation with real merchant spreadsheets
- More real user pain evidence is needed
- Some sources require API keys or are rate-limited
- Generated reports and local research data should remain private

## Recommended Next Step

Validate and harden the product data cleanup tool:

1. Upload Excel/CSV product sheets.
2. Detect product name, price, SKU, stock, image URL, category, and specs.
3. Clean duplicate rows and invalid values.
4. Generate missing-field and anomaly reports.
5. Export a standardized CSV for upload or manual review.
6. Compare the output against real Taobao/1688/ERP workflows and collect user feedback.
