# 数据表格导出与有效性检查

这套项目不要求你一定拿到 API token。拿不到 token 时，优先从平台后台导出 CSV，再导入项目。

## 总流程

1. 从平台后台导出 CSV / Excel。
2. 把关键字段整理进 `data/external_sources.csv`。
3. 运行数据质量检查。
4. 检查通过后再导入雷达。

```powershell
cd path\to\ai-opportunity-radar
Copy-Item data\external_sources.template.csv data\external_sources.csv
notepad data\external_sources.csv
py -B scripts\validate_external_sources.py
py -B scripts\import_external_sources.py
run_ai_radar.bat
```

质量报告会生成在：

```text
reports/data-quality/external_sources_quality.md
reports/data-quality/external_sources_quality.json
```

## 各平台怎么导出

| 平台 | 推荐导出方式 | 放进模板的核心字段 |
|---|---|---|
| Google Trends | 打开 Trends 搜索词，点击图表右上角下载 CSV；Trending now 页面可 Export -> Download CSV | `source=google_trends`, `query`, `search_volume` 或 `metric_value`, `collected_at` |
| Google Ads | 关键词/广告/广告组表格调整好字段后，点击表格上方下载按钮，选择 CSV 或 Google Sheets | `source=google_ads`, `query`, `search_volume`, `result_count`, `collected_at` |
| Amazon Seller Central | 优先导出 Business Reports、Sales and Traffic、Inventory、Orders 等报告 | `source=amazon`, `title`, `product_id`, `price`, `review_count`, `sales_volume`, `last_updated` |
| 淘宝/天猫/京东 | 商家后台导出商品、订单、搜索词、生意参谋/流量数据；没有导出时先手工整理公开页 | `source=taobao/jd`, `query`, `title`, `product_id`, `price`, `sales_volume`, `review_count`, `last_updated` |
| eBay | Seller Hub 里下载 Orders report 或 Reports 文件 | `source=ebay`, `title`, `product_id`, `price`, `sales_volume`, `last_updated` |
| Etsy | Shop Manager -> Settings -> Options -> Download Data -> Download CSV | `source=etsy`, `title`, `product_id`, `price`, `sales_volume`, `review_count` |
| G2 / Capterra | 若无官方导出，就整理公开榜单/评论页 | `source=g2/capterra`, `title`, `url`, `rating`, `review_count`, `category` |

## 什么数据才算有效

最少要满足：

- 有来源：`source` 不能空。
- 有对象：`query` 或 `title` 至少一个不能空。
- 有时间：优先填 `collected_at` 和 `last_updated`。
- 有量化指标：搜索类填 `search_volume/result_count/metric_value`，商品类填 `review_count/sales_volume/rating/price`。
- 有可追溯链接：能填 `url` 就填。
- 不只看一个来源：至少 2-3 个来源交叉验证。

项目里的验证脚本会检查：

- 缺字段
- 空行
- 重复行
- 日期无法识别
- 数据过期
- 数字字段非法
- URL 格式异常
- 来源太少
- 样本太少

## 我的判断标准

可以用于决策的数据：

- `quality_score >= 80`
- 状态为 `usable`
- 至少 2 个数据来源
- 关键数据 30 天内更新
- 同一机会同时有需求信号和供给信号

只能作为线索的数据：

- 状态为 `needs_review`
- 只有一个来源
- 样本少于 5 行
- 只有热度，没有产品/评论/销量支撑

暂时不要下结论的数据：

- 状态为 `blocked` 或 `weak`
- 大量缺失来源、标题、关键词
- 数字和日期明显异常
- 无法追溯来源
