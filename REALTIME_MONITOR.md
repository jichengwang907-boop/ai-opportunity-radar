# AI realtime platform monitor

This monitor pulls public AI signals from multiple platforms and converts them
into the same search/product CSV schema used by the existing report pipeline.

## Supported sources

| Source | Signal |
|---|---|
| GitHub | Repository search count, stars, forks, pushed date |
| GitHub Issues | Filtered public issue search, comments, updated date |
| Product Hunt | Product search count, votes, comments, post date |
| arXiv | Paper search count, latest papers, authors, update date |
| Hugging Face Models | Model search page, likes, downloads, update date |
| Hugging Face Spaces | Demo/app search page, likes, update date |
| Hacker News | Story search count, points, comments, post date |
| Reddit | Public post search, score, comments, post date |
| Google News | News RSS search, publisher, publish date |
| AI Dev Jobs | Public AI/ML job search, salary, tags, publish date |
| Agentic Engineering Jobs | Public Agent/RAG/LLM job search, salary, stack, publish date |
| AgentDeals | Public developer deal and price/credit signal search |
| OkSurf News | Public news feed used as a Google News backup/enrichment source |
| API Status Check | Public API/cloud/AI service status |
| NVD | Public recent CVE feed for AI toolchain/security opportunity signals |
| YouTube | Optional official API search, video metadata |
| X/Twitter | Optional official recent search, engagement |
| PatentsView | Optional Search API patent data |
| DomainsDB | Optional registered-domain search |
| Internet Archive | Optional public advanced search for historical content signals |
| DevITjobs | Optional public software job feed |
| PredScope | Optional public prediction-market feed |

Product Hunt currently uses the public search index visible to the website. If
you later get an official Product Hunt API token, replace that collector with
the official GraphQL endpoint.

YouTube and X/Twitter are available as optional official API collectors. They
are not enabled by default because they require API credentials.

## Run once

```powershell
cd path\to\ai-opportunity-radar
py -B scripts\realtime_ai_platform_monitor.py --once --config config.realtime-ai-platforms.json --report-out reports/realtime-ai
```

Outputs:

```text
data/search_results.realtime-ai.csv
data/products.realtime-ai.csv
data/raw/realtime-ai/
reports/realtime-ai/summary.md
reports/realtime-ai/anomalies.csv
reports/realtime-ai/analysis.json
reports/realtime-ai/source_health.md
```

## Keep it running

Poll every 15 minutes:

```powershell
py -B scripts\realtime_ai_platform_monitor.py --watch --interval-seconds 900 --config config.realtime-ai-platforms.json --report-out reports/realtime-ai
```

Optional GitHub token for higher API limits:

```powershell
$env:GITHUB_TOKEN="<github_token>"
py -B scripts\realtime_ai_platform_monitor.py --watch --interval-seconds 900 --config config.realtime-ai-platforms.json
```

Optional YouTube and X/Twitter keys:

```powershell
$env:YOUTUBE_API_KEY="your-youtube-data-api-key"
$env:X_BEARER_TOKEN="your-x-api-bearer-token"
$env:PATENTSVIEW_API_KEY="your-patentsview-api-key"
$env:DOMAINSDB_API_KEY="your-domainsdb-api-key"
```

Then add `youtube` or `x_recent` to `collector.enabled_sources` and to the
`sources` list in `config.realtime-ai-platforms.json`.

Test watch mode for one cycle:

```powershell
py -B scripts\realtime_ai_platform_monitor.py --watch --max-cycles 1 --interval-seconds 5 --config config.realtime-ai-platforms.json
```

## Configure keywords

Edit `config.realtime-ai-platforms.json` and change the `queries` list.

The default keywords are split into two practical groups:

| Group | Purpose | Examples |
|---|---|---|
| AI product categories | Track existing AI-native product markets | `ai agent`, `local llm`, `ai search`, `ai coding assistant` |
| Manual-work replacement | Track workflows that are still human-heavy and may be replaced or compressed by AI | `ai customer support`, `ai data entry`, `ai invoice processing`, `ai contract review`, `ai recruiting assistant` |

Keep the list focused. Each new keyword is searched across every enabled source,
so doubling keyword count roughly doubles full-run time and network exposure.

## Commercial signal fields

Realtime rows and external imports now include the same commercial signal
fields:

| Field | Meaning |
|---|---|
| `signal_type` | What kind of evidence the row represents: product, feedback, hiring, news, tech supply, security, deal, marketplace review, ecommerce, and so on |
| `buyer_intent_score` | How close the row is to budget, hiring, purchase, pricing, marketplace, or vendor-selection behavior |
| `pain_score` | How strongly the row suggests user pain, bugs, complaints, manual work, reliability problems, or feature requests |
| `source_confidence` | How reliable the source is for this kind of signal |
| `commercial_relevance` | A combined commercial-usefulness score derived from buyer intent, pain, source confidence, and price/review/sales fields |

This keeps technical heat separate from business evidence. For example, GitHub
stars are useful technical supply, while G2/App Store/ecommerce exports or job
postings carry stronger buying-intent weight.

Each query supports:

```json
{
  "term": "ai agent",
  "expected_terms": ["ai", "agent"],
  "forbidden_terms": ["template-only"],
  "min_result_count": 10,
  "min_relevant_results": 3,
  "min_avg_relevance": 0.35,
  "min_item_relevance": 0.34
}
```

## Request pacing

The monitor uses a small default delay plus per-source overrides:

```json
"request_delay_seconds": 0.25,
"request_delay_by_source": {
  "arxiv": 12,
  "reddit": 1,
  "github_issues": 0.75
}
```

This keeps slower or more sensitive sources polite while avoiding a fixed
multi-second pause after every public API call.

For sources that can temporarily rate-limit or close TLS connections, the
collector can also use per-source failure handling:

```json
"max_failures_by_source": {
  "arxiv": 1
},
"failure_cooldown_by_source": {
  "arxiv": 0
}
```

arXiv can return temporary `429` responses from the public API. The default
strategy is therefore conservative: use a longer per-request delay, but stop
asking arXiv for the rest of the current run after the first failure. This keeps
the main business-signal run moving while the source health report still records
the rate-limit event.

## Source quality thresholds

Some sources are sparse by design. For example, NVD only appears when there is a
security issue, API Status Check only appears for service reliability matches,
and Product Hunt/AgentDeals may legitimately have no product for a niche
workflow. These are useful absence signals, not always collection failures.

`analysis.source_quality.by_source` can mark those sources with
`ignore_empty: true` and relaxed relevance thresholds. The source health report
still records real failed/skipped collectors; this only reduces noisy
underperforming-search anomalies in `summary.md` and `analysis.json`.

## GitHub Issues noise filter

GitHub Issues is useful for user pain, feature requests, and bug signals, but
recent issue search can contain a lot of bot or agent task noise. The monitor
therefore overfetches a small sample, removes likely noise, and reports an
effective issue count based on the kept ratio.

The defaults live in `collector.github_issues_filter`:

```json
{
  "enabled": true,
  "overfetch_factor": 10,
  "max_fetch_per_query": 50,
  "keep_if_comments_at_least": 3,
  "effective_total_strategy": "sample_ratio",
  "require_demand_hint": true
}
```

Set `effective_total_strategy` to `observed` for the strictest scoring, or to
`api_total` if you want to ignore filtering for total counts while still
filtering displayed rows.

## Data reliability notes

- GitHub repositories, GitHub Issues, arXiv, Hugging Face, and Hacker News are fetched from public APIs.
- AI Dev Jobs is fetched from its public REST endpoint.
- Agentic Engineering Jobs, AgentDeals, OkSurf, API Status Check, and NVD are fetched from public endpoints and are enabled by default.
- Internet Archive, DevITjobs, and PredScope collectors are implemented as no-token optional sources; add them to `collector.enabled_sources` and the `sources` list if you want broader but noisier coverage.
- Reddit and Google News are fetched from public web endpoints.
- GitHub, arXiv, Product Hunt, Hacker News, Reddit, and Google News expose
  search hit counts or observed result counts.
- Hugging Face lightweight search returns a page of results, not a guaranteed
  full hit count, so the monitor stores page size as the observed count.
- YouTube and X/Twitter use official APIs only when API keys are configured.
- PatentsView and DomainsDB collectors are implemented but disabled by default because current API access requires keys.
- G2, Capterra, Amazon, Taobao, and JD are best connected through official APIs
  or export files. Use `data/external_sources.template.csv` as the import
  mapping template.
- Raw responses are saved under `data/raw/realtime-ai/` for auditability.
- GitHub Issues raw responses include `filter_summary` with inspected, kept,
  skipped, and effective total counts.
- Source health is saved to `reports/realtime-ai/source_health.md` so failed or rate-limited collectors are visible.
- The monitor does not bypass login, captcha, paywalls, or platform controls.
