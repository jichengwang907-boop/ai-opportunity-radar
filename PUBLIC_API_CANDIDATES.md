# Public API 候选接入清单

扫描来源：

- https://github.com/public-api-lists/public-api-lists
- https://github.com/APIs-guru/graphql-apis

筛选口径：优先选择能补强 AI 商机雷达的数据源，包括招聘需求、新闻/趋势、商品价格、商标/专利、开发者生态、服务状态、政策/采购、安全漏洞。不优先接入玩具 API、纯演示 API、与 AI 商机弱相关的娱乐数据。

## 建议优先接入

| 优先级 | API | 来源仓库 | Auth | 信号类型 | 接入价值 |
|---:|---|---|---|---|---|
| 1 | Agentic Engineering Jobs | public-api-lists | No | AI agent/RAG/LLM 招聘需求 | 已接入并默认启用；和当前 `ai_dev_jobs` 互补，更垂直，能直接反映企业落地岗位 |
| 2 | AgentDeals | public-api-lists | No | 开发者免费额度、startup credits、价格变化 | 已接入并默认启用；适合发现开发者工具商业机会、竞品价格变化和创业资源趋势 |
| 3 | Markbase | public-api-lists | No | USPTO 商标搜索 | 可捕捉新品牌/产品命名和商标注册趋势，补创业动向 |
| 4 | OkSurf | public-api-lists | No | Google News 风格新闻 feed | 已接入并默认启用；当前 Google News RSS 的备选/增强源，带 OG 图片和 source 信息 |
| 5 | API Status Check | public-api-lists | No | 270+ API/云服务状态 | 已接入并默认启用；可监控 AI/云服务故障，发现“替代方案/稳定性工具”机会 |
| 6 | Internet Archive Advanced Search | public-api-lists | No | 内容/资料/网页资料库 | 已实现为可选 collector；可用于长期历史趋势、资料量和内容供给信号 |
| 7 | NVD | public-api-lists | No | CVE 漏洞 | 已接入并默认启用；AI 工具链安全、依赖漏洞、企业采购风险信号 |
| 8 | DevITjobs | public-api-lists | No | 软件开发招聘 | 已实现为可选 collector；可过滤 AI/LLM/RAG/agent 关键词，补通用工程岗位需求 |
| 9 | Search.gov Jobs | public-api-lists | No | 美国政府岗位 | 可补政府/公共部门 AI 需求 |
| 10 | PredScope | public-api-lists | No | 预测市场 odds | 已实现为可选 collector；可监控 AI 相关预测市场，作为市场预期弱信号 |

## 实测接入方式

| API | 可用入口 | 认证 | 实测/注意事项 |
|---|---|---|---|
| Agentic Engineering Jobs | `GET https://agentic-engineering-jobs.com/api/v1/jobs?sort=newest&limit=50` | No | 实测可返回岗位 JSON。官方文档标注每 IP 60 秒 30 次请求，建议按关键词本地过滤 `agent`、`RAG`、`LLM`、`AI` |
| AgentDeals | `GET https://agentdeals.dev/api/offers`、`GET https://agentdeals.dev/api/changes`、`GET https://agentdeals.dev/api/newest` | No | OpenAPI 可访问，适合抓优惠、价格变化、startup credit 和供应商风险 |
| OkSurf | `GET https://ok.surf/api/v1/cors/news-feed` | No | 实测可返回新闻 JSON，可作为 Google News RSS 的备份和增强 |
| API Status Check | `GET https://apistatuscheck.com/api/status` | No | 实测返回 270+ 服务状态，可过滤 ChatGPT、OpenAI、Anthropic、AWS、Cloudflare、GitHub 等服务 |
| Internet Archive Advanced Search | `GET https://archive.org/advancedsearch.php?q=artificial%20intelligence&fl[]=identifier&fl[]=title&rows=50&output=json` | No | 实测可返回搜索结果，适合做长期历史内容趋势 |
| NVD | `GET https://nvd.nist.gov/feeds/json/cve/2.0/nvdcve-2.0-recent.json.gz` | No | 实测可下载 gzip feed，collector 需要解压 JSON |
| DevITjobs | `GET https://devitjobs.us/api/jobsLight` | No | 实测可返回岗位 JSON，可按 AI/LLM/RAG/agent 关键词过滤 |
| PredScope | `GET https://predscope.com/api/markets.json` | No | 实测可返回预测市场数据，作为市场预期弱信号 |

暂不建议直接接入的实测结果：

- `https://jobicy.com/jobs-rss-feed`：实测返回 403。
- `https://himalayas.app/api/jobs`：实测返回 404。
- `https://api.graphql.jobs`：实测连接不稳定，先放候选，不进入默认配置。

## 已接入或已有近似能力

| API | 状态 | 备注 |
|---|---|---|
| AI Dev Jobs | 已默认启用 | 已加入 `ai_dev_jobs` collector |
| Agentic Engineering Jobs | 已默认启用 | 已加入 `agentic_engineering_jobs` collector |
| AgentDeals | 已默认启用 | 已加入 `agentdeals` collector |
| OkSurf News | 已默认启用 | 已加入 `oksurf_news` collector |
| API Status Check | 已默认启用 | 已加入 `api_status_check` collector |
| NVD | 已默认启用 | 已加入 `nvd` collector |
| Internet Archive | 已实现，默认不启用 | 已加入 `internet_archive` collector，可手动启用 |
| DevITjobs | 已实现，默认不启用 | 已加入 `devitjobs` collector，可手动启用 |
| PredScope | 已实现，默认不启用 | 已加入 `predscope` collector，可手动启用 |
| HackerNews | 已默认启用 | 当前通过 Algolia HN 搜索 |
| Reddit | 已默认启用 | 当前用公开 JSON 搜索；OAuth 可后续增强 |
| YouTube | 已实现，需 key 启用 | `YOUTUBE_API_KEY` |
| DomainsDB | 已实现，需 key 启用 | 列表标 No auth，但实测当前 API 返回 401，需 `DOMAINSDB_API_KEY` |
| PatentsView | 已实现，需 key 启用 | 新 Search API 按 key 接入，需 `PATENTSVIEW_API_KEY` |

## 需要 token 后再接

| API | 来源仓库 | Auth | 价值 | 变量建议 |
|---|---|---|---|---|
| NewsAPI | public-api-lists | apiKey | 结构化新闻搜索 | `NEWSAPI_KEY` |
| Currents | public-api-lists | apiKey | 新闻、博客、论坛聚合 | `CURRENTS_API_KEY` |
| The Guardian | public-api-lists | apiKey | 高质量新闻内容 | `GUARDIAN_API_KEY` |
| CORE | public-api-lists | apiKey | 开放论文，补 arXiv 覆盖 | `CORE_API_KEY` |
| Best Buy | public-api-lists | apiKey | 商品、价格、类别、推荐 | `BESTBUY_API_KEY` |
| ShopSavvy | public-api-lists | apiKey | 商品价格和历史价格 | `SHOPSAVVY_API_KEY` |
| EAN-Search GraphQL | graphql-apis | apiKey | 条码/商品搜索 | `EAN_SEARCH_API_KEY` |
| Canopy GraphQL | graphql-apis | apiKey/服务账号 | Amazon 商品数据 | `CANOPY_API_KEY` |
| Yelp GraphQL | graphql-apis | apiKey/OAuth | 评论/本地服务需求 | `YELP_API_KEY` |
| Bitquery GraphQL | graphql-apis | apiKey | 链上/crypto 商业信号 | `BITQUERY_API_KEY` |
| Buildkite GraphQL | graphql-apis | apiKey | CI/CD 生态和开发者工具信号 | `BUILDKITE_TOKEN` |

## GraphQL 仓库中较有用的候选

| API | Auth | 接入建议 |
|---|---|---|
| GitLab GraphQL | 可公开查询部分数据，完整能力需 token | 可作为 GitHub 之外的开源项目补充源 |
| GraphQL Jobs | No/不稳定 | 适合岗位需求，但实测连接不稳定；可先不接 |
| EAN-Search | apiKey | 商品条码/产品库，适合电商化阶段 |
| Canopy | apiKey/服务 | Amazon 商品数据，价值高但合规和费用需确认 |
| Shopify Storefront/Admin | token | 只有在你有店铺或客户店铺授权时有价值 |
| Saleor | demo/open-source | 更适合样例，不适合作为外部市场数据源 |
| Yelp | apiKey/OAuth | 评论需求信号，但不适合 AI 垂直早期优先级 |

## 不建议优先接

- 娱乐/动漫/电影/游戏类：AniList、TCGdex、PokeAPI、TMDB、Rick and Morty 等，与 AI 商机雷达弱相关。
- 纯演示 GraphQL：Northwind、TODO、FakeQL、A-Maze 等，只适合测试 GraphQL 客户端。
- 强 OAuth 且数据闭环在用户账号内的平台：Gmail、Buffer、Facebook、Instagram、Monday、Pipefy。除非未来做企业账号授权，否则不适合先接。
- 高风控或明显商业数据服务：Shodan、SecurityTrails、Whoisfreaks、ShopSavvy、Amazon Scraper API。价值高，但应先确认费用和条款。

## 推荐下一批落地顺序

1. `agentic_engineering_jobs`：无 token，强相关，和 `ai_dev_jobs` 互补。
2. `agentdeals`：无 token，能补开发者工具价格/优惠/商业化信号。
3. `markbase`：无 token，补商标/品牌注册趋势。
4. `oksurf_news`：无 token，作为 Google News RSS 的备份和增强。
5. `api_status_check`：无 token，补 AI/云服务稳定性和故障机会。
6. `nvd`：无 token，补 AI 工具链安全机会。

这些源接入后，机会评分可以新增三类分数：

- `hiring_demand`：招聘需求。
- `brand_startup_activity`：商标/品牌/域名活动。
- `developer_tool_market`：开发者工具优惠、价格、服务状态和安全漏洞。
