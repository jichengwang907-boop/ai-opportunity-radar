# GitHub 数据获取工具调研

调研日期：2026-05-25

目标：为 AI 商机雷达寻找可复用的数据获取工具，优先考虑维护状态、数据可信度、接入成本和合规风险。

## 推荐优先接入

| 方向 | GitHub 项目 | 状态 | 用法判断 |
|---|---|---:|---|
| GitHub 数据 | [PyGithub/PyGithub](https://github.com/PyGithub/PyGithub) | 7.7k stars，2026-05 有更新 | 可接入。用于仓库搜索、stars、forks、更新时间等结构化数据。 |
| Hugging Face | [huggingface/huggingface_hub](https://github.com/huggingface/huggingface_hub) | 3.6k stars，2026-05 有更新 | 可接入。官方 Python 客户端，适合模型/Spaces 趋势。 |
| Hacker News | [HackerNews/API](https://github.com/HackerNews/API) | 13k stars，官方 API 文档 | 可接入。官方 API/样例，适合作为前沿讨论信号。 |
| Reddit | [praw-dev/praw](https://github.com/praw-dev/praw) | 4.1k stars，2026-05 有更新 | 可接入，但需要 Reddit API 凭证。比网页爬取更稳。 |
| 通用爬虫框架 | [apify/crawlee-python](https://github.com/apify/crawlee-python) | 9k stars，2026-05 有更新 | 可接入。适合需要 Playwright、代理、队列和重试的网页采集。 |

## 可用但要谨慎

| 方向 | GitHub 项目 | 状态 | 风险 |
|---|---|---:|---|
| Google Trends | [GeneralMills/pytrends](https://github.com/GeneralMills/pytrends) | 3.7k stars，但已 archived | 能用作参考，不建议作为唯一依赖。Google Trends 非正式 API，容易受限制。 |
| Google Trends CLI | [akvise/trends-checker](https://github.com/akvise/trends-checker) | 214 stars，2026-04 有更新 | 基于 pytrends，维护较新。适合试验趋势数据拉取。 |
| Reddit 无 token 抓取 | [JosephLai241/URS](https://github.com/JosephLai241/URS) | 994 stars，2026-03 有更新 | 可参考，但网页抓取比官方 API 不稳定，合规风险更高。 |
| 多平台数据 SDK | [justoneapi/justoneapi-python](https://github.com/justoneapi/justoneapi-python) | 156 stars，2026-05 有更新 | 覆盖平台多，但应先审查服务来源、价格、字段质量和合规性。 |
| Agent 多平台搜索 | [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach) | 20k stars，2026-05 有更新 | 很新、覆盖面广。可先做沙盒验证，不建议直接放入核心数据链路。 |

## 电商方向

| 平台 | GitHub 项目 | 状态 | 建议 |
|---|---|---:|---|
| Amazon | [oxylabs/amazon-scraper](https://github.com/oxylabs/amazon-scraper) | 2.9k stars，2026-04 有更新 | 商业 Scraper API，字段完整但可能收费。 |
| Amazon | [omkarcloud/amazon-scraper](https://github.com/omkarcloud/amazon-scraper) | 219 stars，2026-04 有更新 | 可试验，声称支持搜索、详情、评论、多市场。 |
| Amazon | [scrapehero-code/amazon-scraper](https://github.com/scrapehero-code/amazon-scraper) | 434 stars，2023 后未推送 | 只适合参考结构，不建议核心依赖。 |
| eBay | [timotheus/ebaysdk-python](https://github.com/timotheus/ebaysdk-python) | 850 stars，2023 后未推送 | 可参考，但维护偏旧；优先用 eBay 官方 API 或后台导出。 |
| Etsy | [mcfunley/etsy-python](https://github.com/mcfunley/etsy-python) | 66 stars，2011 后未推送 | 不建议接入；优先官方 Open API 或后台 CSV。 |
| 淘宝 | [bububa/pyTOP](https://github.com/bububa/pyTOP) | 42 stars，2018 后未推送 | 只适合参考淘宝开放平台签名方式。 |
| 京东 | [VeryCB/jos](https://github.com/VeryCB/jos) | 9 stars，2017 后未推送 | 不建议依赖；优先京东后台导出或官方开放平台。 |

## Product Hunt 方向

没有发现维护良好、足够成熟的 Product Hunt Python 采集库。当前项目已经使用 Product Hunt 公开 Algolia 搜索端点做无 token 抓取；如果后续能拿到 `PRODUCTHUNT_TOKEN`，再切换到官方 GraphQL API 会更稳。

## 接入优先级

1. 保持现有公开源：GitHub API、Product Hunt 公开搜索、arXiv、Hugging Face、Hacker News、Reddit JSON、Google News RSS。
2. 增强官方客户端：优先接 `PyGithub`、`huggingface_hub`、`HackerNews/API`、`PRAW`。
3. 趋势数据：先用 CSV 导入 Google Trends/Google Ads；若要自动化，再评估 `trends-checker`。
4. 电商数据：先后台导出 CSV，不优先接网页爬虫。
5. 通用网页采集：复杂页面再引入 `crawlee-python` 或 Playwright。

## 结论

已经有工具，但不能一把梭。

最适合直接接进 AI 商机雷达的是官方 API 客户端和公开 RSS/API；电商平台更适合先走后台导出 CSV，再用项目里的 `validate_external_sources.py` 做质量检查。网页爬虫工具可以作为补充，但不要作为商业判断的唯一数据来源。
