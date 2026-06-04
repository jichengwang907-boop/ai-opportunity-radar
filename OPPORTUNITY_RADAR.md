# 机会评分说明

## 运行命令

先拉取实时数据：

```powershell
cd path\to\ai-opportunity-radar
py -B scripts\realtime_ai_platform_monitor.py --once --config config.realtime-ai-platforms.json --report-out reports/realtime-ai
```

再生成机会排行：

```powershell
py -B scripts\generate_opportunity_report.py --analysis reports\realtime-ai\analysis.json --out reports/opportunity-radar
```

输出文件：

```text
reports/opportunity-radar/opportunities.md
reports/opportunity-radar/opportunities.csv
reports/opportunity-radar/opportunities.json
```

## 新评分模型

机会分现在采用组合框架：Porter 五力、TAM/SAM/SOM、RICE，以及项目内的购买意图和痛点信号。

| 维度 | 权重 | 参考框架 | 含义 |
|---|---:|---|---|
| 购买意图 | 25% | Willingness to Pay / RICE Impact | 招聘、价格、交易、评论、应用市场、广告/搜索量等是否接近真实付费行为 |
| 痛点强度 | 20% | Problem urgency | 用户是否在抱怨、提 bug、要功能、手工流程是否明显低效 |
| 市场规模/增长 | 15% | TAM/SAM/SOM | 搜索趋势、关键词量、新闻关注、社区讨论、招聘需求是否足够大或在增长 |
| 竞争吸引力 | 15% | Porter Five Forces | 产品是否拥挤、替代品是否多、是否仍存在差异化切口 |
| 可信度 | 10% | RICE Confidence | 多源覆盖、来源可信度、结果相关度是否足够 |
| 执行可行性 | 10% | RICE Effort | 个人/小团队是否能做，是否偏软件/服务/模板，技术供给是否足够 |
| 商业缺口 | 5% | GE/McKinsey market attractiveness | 技术/讨论热，但产品化相对不足时加分 |

最终公式：

```text
score =
  buyer_intent * 25%
+ pain_signal * 20%
+ market_size_growth * 15%
+ competition_attractiveness * 15%
+ confidence * 10%
+ execution_feasibility * 10%
+ commercial_gap * 5%
```

## 分数解释

| 等级 | 分数 | 含义 |
|---|---:|---|
| A | 78+ | 优先验证，但仍要找垂直切口 |
| B | 66-77 | 值得做轻量 MVP 和用户访谈 |
| C | 52-65 | 可以做内容、模板、小工具或小样例测试 |
| D | 低于 52 | 先观察，不建议马上投入开发 |

## 重要原则

高分不等于能赚钱，低分也不等于永远没机会。高分只说明：

- 多平台信号相对更强。
- 当前数据下更值得优先验证。
- 更适合进入访谈、落地页或小 MVP。

低分可能意味着：

- 真实购买意图不足。
- 市场还没有显性化。
- 关键词表达不准。
- 方向偏硬件、供应链或强巨头赛道。
- 当前数据源不适配这个方向。

## 下一步验证动作

每个高分方向都要走这个流程：

1. 写一句明确定位：我帮谁解决什么问题。
2. 找 10 个潜在用户访谈。
3. 做 1 页落地页。
4. 做 1 个可交付样例。
5. 先收 1 笔小钱，再决定是否开发完整产品。

判断标准：

```text
有人愿意付钱 > 有人说感兴趣
能复购 > 一次性好奇
能节省时间/赚钱/避险 > 只是好玩
```
