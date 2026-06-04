# 数据源接入说明

## 已接入并默认启用

| 数据源 | 类型 | 作用 | 说明 |
|---|---|---|---|
| GitHub | 官方公开 API | 开发者热度、开源供给 | 返回仓库命中量、stars、forks、更新时间 |
| GitHub Issues | 官方公开 API | 用户需求、bug、抱怨和功能请求 | 返回过滤后的公开 issue 有效命中量、comments、更新时间 |
| Product Hunt | 公开搜索索引 | 产品化热度 | 返回产品命中量、votes、comments、发布时间 |
| arXiv | 官方公开 API | 学术前沿、研究热度 | 返回论文命中量、作者、更新时间 |
| Hugging Face Models | 公开 API | 模型生态 | 返回模型搜索页、likes、downloads |
| Hugging Face Spaces | 公开 API | Demo / 原型生态 | 返回可体验应用和 demo |
| Hacker News | Algolia 公开 API | 工程师讨论 | 返回帖子命中量、points、comments |
| Reddit | 公开 JSON 搜索 | 用户讨论、抱怨、真实问题 | 返回帖子、score、comments |
| Google News | RSS 搜索 | 新闻关注、公司动态、媒体热度 | 返回新闻条目和发布源 |
| AI Dev Jobs | 官方公开 API | 招聘需求、企业真实 AI 用人方向 | 返回职位命中量、公司、薪资、岗位标签 |
| Agentic Engineering Jobs | 官方公开 API | Agent/RAG/LLM 垂直招聘需求 | 返回职位命中量、公司、技术栈、薪资 |
| AgentDeals | 官方公开 API | 开发者工具优惠、免费额度、价格变化 | 返回供应商、分类、风险和验证日期 |
| OkSurf News | 公开新闻 API | Google News 的备份/增强新闻源 | 返回新闻标题、来源、OG 信息 |
| API Status Check | 公开状态 API | AI/云/API 服务稳定性和故障机会 | 返回服务状态、类别、状态页链接 |
| NVD | 官方公开 feed | 安全漏洞、AI 工具链风险 | 返回近期 CVE、CVSS、引用数量 |

## 已实现但默认不启用

| 数据源 | 启用条件 | 用途 |
|---|---|---|
| YouTube | 设置 `YOUTUBE_API_KEY` | 视频内容热度、教程需求、测评内容 |
| X/Twitter | 设置 `X_BEARER_TOKEN` | 早期传播、意见领袖讨论、社交热度 |
| PatentsView | 设置 `PATENTSVIEW_API_KEY` | 美国专利趋势、技术商业化信号 |
| DomainsDB | 设置 `DOMAINSDB_API_KEY` | 注册域名、创业项目和产品命名动向 |
| Internet Archive | 无需 token，手动加入配置 | 历史内容供给和长期趋势资料 |
| DevITjobs | 无需 token，手动加入配置 | 通用软件招聘需求补充 |
| PredScope | 无需 token，手动加入配置 | 预测市场和市场预期弱信号 |

启用示例：

```powershell
$env:YOUTUBE_API_KEY="your-youtube-data-api-key"
$env:X_BEARER_TOKEN="your-x-api-bearer-token"
```

然后把 `youtube` 或 `x_recent` 加到 `config.realtime-ai-platforms.json` 的：

```json
"enabled_sources": ["youtube", "x_recent"]
```

并在 `sources` 列表里加入对应 CSV 过滤配置。

## 通过导入模板接入

这些平台不建议绕过登录或风控抓取，应优先使用官方 API、后台导出或手工整理后的 CSV。

| 数据源 | 推荐方式 | 用途 |
|---|---|---|
| Google Trends | 导出 CSV | 搜索兴趣趋势 |
| G2 | 官方/公开导出 | B2B 评论、竞品满意度 |
| Capterra | 官方/公开导出 | B2B 评论、软件品类 |
| Amazon | Product Advertising API / 卖家后台导出 | 商品供给、评论、价格 |
| 淘宝 | 开放平台 / 商家后台导出 | 商品供给、销量、价格 |
| 京东 | 开放平台 / 商家后台导出 | 商品供给、销量、价格 |

模板文件：

```text
data/external_sources.template.csv
```

外部导入模板也支持商业信号字段：`signal_type`、`buyer_intent_score`、
`pain_score`、`source_confidence`、`commercial_relevance`。如果这些分数留空，
导入脚本会根据来源、类型、价格、评分、销量、评论等字段自动补一版基础分。

## 数据有效性判断

单个平台只能说明一个侧面：

- GitHub 仓库热：说明开发者供给强。
- GitHub Issues 热：说明真实使用问题、功能请求或抱怨多；默认会过滤机器人、依赖升级、CI、自动化 agent 任务等噪声。
- Reddit 热：说明用户讨论或抱怨多。
- AI Dev Jobs 热：说明企业招聘和落地需求强。
- Agentic Engineering Jobs 热：说明企业正在招聘 Agent/RAG/LLM 落地岗位。
- AgentDeals 热：说明开发者工具、优惠、价格和供应商生态有变化。
- API Status Check / NVD 热：说明稳定性或安全痛点可能带来替代方案、监控、合规工具机会。
- PatentsView 热：说明技术商业化和专利布局升温。
- DomainsDB 热：说明相关域名注册和创业活动多。
- Google News 热：说明媒体和公司动态多。
- Product Hunt 热：说明产品化尝试多。
- G2/Capterra 热：更接近 B2B 购买和满意度。
- 电商平台热：更接近商品化和消费购买意图。

更可信的机会通常满足：

```text
开发者供给强 + 用户讨论强 + 市场关注上升 + 产品化不太拥挤 + 个人可执行
```
