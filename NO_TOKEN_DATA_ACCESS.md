# 无 token 数据接入方案

拿不到平台 token 时，不要把登录账号密码交给程序。这个项目现在支持三种不依赖 token 的方式：

1. 公开源实时抓取：GitHub 公开搜索、Product Hunt 公开搜索、arXiv、Hugging Face、Hacker News、Reddit、Google News。
2. 平台后台导出 CSV：Google Trends、Google Ads、淘宝、京东、亚马逊、eBay、Etsy、G2、Capterra、Similarweb、Ahrefs 等。
3. 手工整理公开页面数据：只要整理成统一 CSV 字段，也能进入同一套分析和机会评分。

## 使用方法

复制模板：

```powershell
cd path\to\ai-opportunity-radar
Copy-Item data\external_sources.template.csv data\external_sources.csv
notepad data\external_sources.csv
```

把平台导出的数据填入 `data/external_sources.csv`，然后运行：

```powershell
py -B scripts\validate_external_sources.py
py -B scripts\import_external_sources.py
```

它会生成：

```text
reports/data-quality/external_sources_quality.md
data/search_results.external-imports.csv
data/products.external-imports.csv
reports/external-imports/summary.md
```

之后运行一键脚本：

```powershell
run_ai_radar.bat
```

实时公开源数据和导入数据会合并进入：

```text
reports/realtime-ai/summary.md
reports/opportunity-radar/opportunities.md
```

## 推荐优先导出的字段

搜索需求类平台优先填：

- `source`
- `query`
- `title`
- `rank`
- `result_count`
- `search_volume`
- `collected_at`
- `notes`

商品/产品类平台优先填：

- `source`
- `query`
- `title`
- `url`
- `product_id`
- `price`
- `currency`
- `seller`
- `rating`
- `review_count`
- `sales_volume`
- `last_updated`
- `collected_at`

## 判断数据是否可信

每条导入数据最好保留来源和日期。后面判断机会时，优先相信同时出现在多个来源里的趋势，例如：

- Google Trends 有热度
- GitHub/Product Hunt 有新产品
- Reddit/Hacker News/Google News 有讨论
- 亚马逊/淘宝/京东有销量或评论
- G2/Capterra 有 B2B 评论需求

单一来源只能算线索，多个来源交叉验证后才算机会。
