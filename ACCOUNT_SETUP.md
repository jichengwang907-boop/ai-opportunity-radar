# 账号和 API Key 接入口

不要把平台登录密码写进项目，也不要把密码发到聊天里。这个项目只接收：

- API Key
- Bearer Token
- OAuth Token
- 商家授权 Token
- 后台导出的 CSV

## 1. 创建本地密钥文件

先看 token 官方来源清单：

```text
TOKEN_SOURCES.md
```

推荐用接入脚本写入和验证 token，脚本不会打印密钥内容：

```powershell
py -B scripts\setup_tokens.py --set GITHUB_TOKEN --verify github
```

如果已安装并登录 GitHub CLI，也可以直接运行：

```powershell
connect_github_token.bat
```

```powershell
cd path\to\ai-opportunity-radar
Copy-Item .env.example .env.local
notepad .env.local
```

把你已有的平台 Key 填到 `.env.local`。这个文件已经加入 `.gitignore`，不会进入源码和报告。

## 2. 检查哪些账号已接通

```powershell
py -B scripts\check_credentials.py
```

报告会生成在：

```text
reports/credentials/status.md
reports/credentials/status.json
```

## 3. 当前可直接启用的账号接口

| 平台 | 变量 | 用途 |
|---|---|---|
| GitHub | `GITHUB_TOKEN` | 提高 API 限额 |
| YouTube | `YOUTUBE_API_KEY` | 拉取视频搜索和内容需求 |
| X/Twitter | `X_BEARER_TOKEN` | 拉取近期社交讨论 |
| PatentsView | `PATENTSVIEW_API_KEY` | 拉取美国专利趋势 |
| DomainsDB | `DOMAINSDB_API_KEY` | 拉取注册域名和创业动向 |

YouTube 和 X 默认不启用。填好 Key 后，还需要在 `config.realtime-ai-platforms.json` 里把 `youtube` 或 `x_recent` 加到 `collector.enabled_sources` 和 `sources`。

## 4. 需要进一步适配的账号接口

这些平台的授权流程更复杂，通常需要 OAuth、商家授权或付费 API。项目已经预留变量和导入模板：

| 平台 | 接入方式 |
|---|---|
| Google Ads Keyword Planner | Google Ads API 或后台导出 |
| Amazon | Product Advertising API 或卖家后台导出 |
| eBay | Browse API |
| Etsy | Open API |
| 淘宝 | 淘宝开放平台或商家后台导出 |
| 京东 | 京东开放平台或商家后台导出 |
| Similarweb | 付费 API 或导出 |
| Ahrefs | 付费 API 或导出 |
| G2 / Capterra | 付费/商务数据或公开列表整理 |

外部导入模板：

```text
data/external_sources.template.csv
```

## 5. 最安全的交付方式

如果你要给我账号，不建议给登录密码。建议给：

1. 临时 API Key。
2. 只读权限 Token。
3. 单独创建的开发者应用。
4. 可随时撤销的商家授权。
5. 导出的 CSV 文件。

这样即使后续不继续合作，也可以随时关闭权限。

## 6. 如果 token 获取不了

直接走无 token 模式。把平台后台或公开页面数据导出成 CSV，按这个模板填写：

```text
data/external_sources.template.csv
```

然后保存为：

```text
data/external_sources.csv
```

运行：

```powershell
py -B scripts\import_external_sources.py
```

详细说明见：

```text
NO_TOKEN_DATA_ACCESS.md
```
