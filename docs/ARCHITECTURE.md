# Architecture

## Core Flow

```text
Config
  -> Sources / Collectors
  -> Standard SearchResult and Product rows
  -> Analysis
  -> Reports
```

## Main Components

- `shopping_intel.config`: loads JSON config and resolves paths.
- `shopping_intel.models`: normalized data models and parsing helpers.
- `shopping_intel.adapters`: CSV and HTTP JSON source adapters.
- `shopping_intel.analysis`: search quality and product freshness analysis.
- `shopping_intel.opportunity`: AI opportunity scoring and ranking.
- `shopping_intel.report`: Markdown, CSV, and JSON report writers.
- `scripts/realtime_ai_platform_monitor.py`: public signal collector for AI opportunity radar.
- `scripts/import_external_sources.py`: converts manual research exports to normalized rows.
- `scripts/desktop_app.py`: Tkinter desktop wrapper around the pipeline.

## Data Contracts

Search result rows use:

```text
source,query,title,url,rank,result_count,search_volume,snippet,price,currency,seller,rating,review_count,collected_at,signal_type,buyer_intent_score,pain_score,source_confidence,commercial_relevance
```

Product rows use:

```text
source,product_id,title,url,price,currency,seller,category,stock_status,rating,review_count,sales_volume,last_updated,collected_at,signal_type,buyer_intent_score,pain_score,source_confidence,commercial_relevance
```

## Privacy Model

The repository is designed to keep raw data and generated reports local. Public repositories should include sample/template data only.
