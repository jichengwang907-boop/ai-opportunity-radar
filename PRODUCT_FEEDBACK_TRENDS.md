# 产品反馈、评价与最近趋势

项目现在会把不同平台的公开反馈统一成一份产品反馈报告：

```powershell
py -B scripts\generate_product_feedback_report.py
```

输出位置：

```text
reports/product-feedback/products.md
reports/product-feedback/products.csv
reports/product-feedback/products.json
```

## 反馈口径

| 来源 | 反馈指标 | 互动/趋势指标 |
|---|---|---|
| GitHub | stars | forks |
| GitHub Issues | issue comments | filtered issue mentions |
| Product Hunt | votes | comments |
| Hugging Face | likes | downloads |
| Hacker News | points | comments |
| Reddit | score | comments |
| Google News | coverage | mentions |
| AI Dev Jobs | quality score | salary signal |
| Agentic Engineering Jobs | views + clicks | salary signal |
| AgentDeals | deal signal | freshness |
| OkSurf News | coverage | mentions |
| API Status Check | incident weight | service count |
| Internet Archive | downloads | downloads |
| NVD | CVSS score x10 | references |
| DevITjobs | job signal | salary signal |
| PredScope | volume | liquidity |
| PatentsView | citations | patents |
| DomainsDB | domains | records |
| arXiv | papers/citations proxy | papers |

## 商业信号口径

产品反馈 CSV 和 Markdown 报告会同时展示：

| 字段 | 用途 |
|---|---|
| `signal_type` | 区分产品、用户反馈、招聘、新闻、技术供给、安全、交易/价格等信号 |
| `buyer_intent_score` | 越高越接近真实预算、购买、招聘、价格、市场上架或采购行为 |
| `pain_score` | 越高说明用户抱怨、bug、功能请求、手工流程或可靠性问题越明显 |
| `source_confidence` | 数据源可信度 |
| `commercial_relevance` | 用于机会排序的商业相关性综合分 |

读报告时优先看 `commercial_relevance` 和 `pain_score` 同时较高的项；这类信号通常比单纯 GitHub stars 或新闻热度更接近商机。

## 最近趋势怎么判断

脚本会把每次运行的产品反馈快照写入：

```text
data/history/product_feedback_history.csv
```

第一次运行只建立 `baseline`。第二次以后，相同产品会和上一次快照对比：

- `rising`：反馈/互动明显增加。
- `stable`：变化不大。
- `falling`：反馈/互动明显下降。
- `baseline`：还没有历史可比。

## 如何使用

一键运行：

```powershell
run_ai_radar.bat
```

它会依次生成：

```text
reports/realtime-ai/summary.md
reports/product-feedback/products.md
reports/opportunity-radar/opportunities.md
```

判断产品是否值得进一步研究时，优先看：

1. `feedback_score` 是否高。
2. `evaluation_level` 是否为 `strong` 或 `healthy`。
3. `trend_status` 是否为 `rising`。
4. `recency_status` 是否为 `fresh` 或 `recent`。
5. 是否同时命中多个关键词或多个平台。
