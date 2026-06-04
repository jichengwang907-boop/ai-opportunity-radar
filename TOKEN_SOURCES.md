# Token 来源清单

本项目不要收集平台登录密码，只使用 API Key、Bearer Token、OAuth Token、商家授权 Token，或后台导出的 CSV。

当前本机已初始化 `.env.local`，但 `scripts/check_credentials.py` 检测结果仍为 `0/14` 已配置。拿到 token 后，把对应变量填进去。

```powershell
Copy-Item .env.example .env.local
notepad .env.local
py -B scripts\check_credentials.py
```

也可以使用安全接入脚本，它只显示是否配置，不打印密钥：

```powershell
py -B scripts\setup_tokens.py --init --status
py -B scripts\setup_tokens.py --set GITHUB_TOKEN --verify github
py -B scripts\setup_tokens.py --set YOUTUBE_API_KEY --verify youtube
py -B scripts\setup_tokens.py --set X_BEARER_TOKEN --verify x
py -B scripts\setup_tokens.py --set PRODUCTHUNT_TOKEN --verify producthunt
```

如果本机安装并登录了 GitHub CLI，可以一键导入：

```powershell
connect_github_token.bat
```

## 优先获取

| 优先级 | 平台 | 项目变量 | 官方来源 | 推荐权限/口径 | 用途 |
|---:|---|---|---|---|---|
| 1 | GitHub | `GITHUB_TOKEN` | https://github.com/settings/personal-access-tokens | Fine-grained token；公共搜索只需最小权限，主要用于提高 API 限额 | 仓库、Issues、开发者热度 |
| 2 | YouTube Data API | `YOUTUBE_API_KEY` | https://console.cloud.google.com/apis/credentials | Google Cloud API key；启用 YouTube Data API v3，并限制到 YouTube Data API | 视频内容热度、教程/测评需求 |
| 3 | X / Twitter | `X_BEARER_TOKEN` 或 `TWITTER_BEARER_TOKEN` | https://developer.x.com/ | App-only Bearer Token；只读公开数据 | 近期社交讨论 |
| 4 | Product Hunt | `PRODUCTHUNT_TOKEN` | https://www.producthunt.com/v2/oauth/applications | Developer token 或 OAuth client token；注意官方 API 商业用途限制 | 官方 GraphQL 产品数据 |
| 5 | PatentsView | `PATENTSVIEW_API_KEY` | https://search.patentsview.org/docs/ | Search API key | 美国专利趋势 |
| 6 | DomainsDB | `DOMAINSDB_API_KEY` | https://domainsdb.info/ | Bearer/API key；当前 API 已要求 key | 注册域名和创业动向 |

## 购买意图数据

这些来源比泛社交/开源数据更接近商业化和购买意图，但多数需要付费、商务申请、商家账号，或用 CSV 导入替代。

| 平台 | 项目变量 | 官方/常用来源 | 建议 |
|---|---|---|---|
| Google Ads Keyword Planner | `GOOGLE_ADS_DEVELOPER_TOKEN`, `GOOGLE_ADS_CLIENT_ID`, `GOOGLE_ADS_CLIENT_SECRET`, `GOOGLE_ADS_REFRESH_TOKEN`, `GOOGLE_ADS_CUSTOMER_ID` | https://developers.google.com/google-ads/api | 优先用后台导出的关键词 CSV；API 接入需要 Google Ads 账号和 OAuth |
| Amazon Product Advertising API | `AMAZON_ACCESS_KEY`, `AMAZON_SECRET_KEY`, `AMAZON_PARTNER_TAG` | https://webservices.amazon.com/paapi5/documentation/ | 需要 Associates/Partner Tag；也可用卖家后台导出 |
| eBay Browse API | `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`, `EBAY_OAUTH_TOKEN` | https://developer.ebay.com/ | 官方开发者应用 |
| Etsy Open API | `ETSY_API_KEY` | https://developers.etsy.com/ | 官方开发者应用 |
| 淘宝开放平台 | `TAOBAO_APP_KEY`, `TAOBAO_APP_SECRET`, `TAOBAO_SESSION` | https://open.taobao.com/ | 需要开放平台/商家授权；优先导出 CSV |
| 京东开放平台 | `JD_APP_KEY`, `JD_APP_SECRET`, `JD_ACCESS_TOKEN` | https://jos.jd.com/ | 需要开放平台/商家授权；优先导出 CSV |
| Similarweb | `SIMILARWEB_API_KEY` | https://developer.similarweb.com/ | 付费 API 或后台导出 |
| Ahrefs | `AHREFS_API_KEY` | https://docs.ahrefs.com/ | 付费 API 或后台导出 |
| G2 | `G2_API_KEY` | https://www.g2.com/ | 多数情况走商务数据或公开列表整理 |
| Capterra | `CAPTERRA_API_KEY` | https://www.capterra.com/ | 多数情况走商务数据或公开列表整理 |

## 当前可无 token 继续跑的源

以下已经默认可用，无需 token：

- GitHub 公共搜索，未配置 `GITHUB_TOKEN` 时限额较低。
- GitHub Issues 公共搜索，未配置 `GITHUB_TOKEN` 时限额较低。
- Product Hunt 公开搜索索引。
- arXiv。
- Hugging Face Models / Spaces。
- Hacker News。
- Reddit 公开 JSON 搜索。
- Google News RSS。

## 填写位置

`.env.local` 示例：

```text
GITHUB_TOKEN=<github_token>
YOUTUBE_API_KEY=<youtube_api_key>
X_BEARER_TOKEN=<x_bearer_token>
PRODUCTHUNT_TOKEN=...
PATENTSVIEW_API_KEY=<patentsview_api_key>
DOMAINSDB_API_KEY=<domainsdb_api_key>
```

`run_ai_radar.bat` 会自动调用 `scripts/check_credentials.py`，报告输出到：

```text
reports/credentials/status.md
reports/credentials/status.json
```

## 安全建议

- 优先创建只读、短期、可撤销的 token。
- 不要把 token 发到聊天里，不要写进源码。
- `.env.local` 已在 `.gitignore` 中，不会进入项目提交。
- 获取 Google/YouTube API key 后，应在 Google Cloud 控制台限制 API 和调用来源。
- token 泄露或不再使用时，立即在对应平台后台撤销。
