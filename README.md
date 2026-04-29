# 港股IPO智能打新评估工具

基于127只2025-2026年真实港股IPO数据回测校准的智能评分引擎。

## 功能特性

- **八维评分体系**（满分100分）：认购热度、行业赛道、保荐人、基石投资者、绿鞋、估值、市值、基础分
- **VETO规则引擎**：2条数据驱动的否决规则 + 零售狂热豁免
- **智能文本解析**：从财经新闻中自动提取IPO关键数据
- **历史回测验证**：127只新股回测，Buy信号胜率97.1%

## 安装

```bash
pip install git+https://github.com/lianyanshe-ai/hkipo.git
```

或克隆后本地安装：

```bash
git clone https://github.com/lianyanshe-ai/hkipo.git
pip install -e .
```

## 使用方法

### 1. 手动搜索模式（推荐）

先用搜索引擎收集IPO数据，然后传给CLI：

```bash
hkipo search \
  --code 1879 \
  --name "曦智科技" \
  --date 2026-04-28 \
  --price 183.2 \
  --text "基石阿里巴巴、GIC Private Limited、富达国际、贝莱德，红杉中国、云锋基金，认购约16.44亿港元，占全球发售股份约50%，孖展认购78倍，15%绿鞋，稳价人高盛，行业AI，市值845亿港元，PE=500，联席保荐高盛、中金公司"
```

### 2. 自动搜索模式

需要设置 `EXA_API_KEY` 或 `MINIMAX_API_KEY` 环境变量：

```bash
hkipo auto --code 1879 --name "曦智科技" --date 2026-04-28 --price 183.2
```

### 3. 手动输入模式

```bash
hkipo score \
  --code 1879 --name "曦智科技" --date 2026-04-28 --price 183.2 \
  --mcap 845 --sponsor "高盛、中金" --stabilizer "高盛" \
  --cs "GIC Private Limited" "贝莱德" --cs-pct 0.52 \
  --greenshoe --industry "AI" --sub 5784 --pe 500
```

### 4. 回测验证

```bash
hkipo backtest
```

## 评分体系

| 维度 | 最高分 | 说明 |
|---|---|---|
| 认购热度 | 40分 | 最强预测因子（500x+胜率100%） |
| 行业赛道 | 25分 | 硬科技>生医>成长>消费>传统 |
| 保荐人 | 15分 | 摩根大通/大摩/高盛为顶级 |
| 基石投资者 | 10分 | 白名单机构+合理占比 |
| 绿鞋机制 | 5分 | 头部稳价人加分 |
| 估值合理性 | 5分 | PE相对行业折价/溢价 |
| 市值稳定性 | 5分 | 大盘股更稳定 |
| 基础分 | 5分 | 参与即得 |

### 决策阈值

| 分数 | 建议 |
|---|---|
| >=72 | 🟢 强烈建议打 |
| >=60 | 🟡 建议打 |
| >=48 | 🟡 谨慎观望 |
| <48 | 🔴 不建议打 |
| VETO | 🔴 直接放弃 |

## 作为 Claude Code Skill 使用

将 `SKILL.md` 复制到你的 Claude Code skills 目录：

```bash
cp SKILL.md ~/.claude/skills/hk-ipo-screener.md
```

然后在 Claude Code 中即可使用港股IPO评估功能。

## 项目结构

```
hk_ipo_screener/
├── cli.py                   # CLI入口: hkipo score/search/auto/backtest
├── core/
│   ├── types.py             # 数据模型 (IPODTO, ScoreResult)
│   ├── scoring.py           # 八维评分引擎
│   ├── veto_filter.py       # VETO规则引擎
│   ├── report.py            # Markdown报告生成
│   └── scraper.py           # 搜索文本解析器
├── backtest/
│   └── replay.py            # 历史回测
└── data/
    ├── whitelist.json       # 基石白名单+保荐人分级
    ├── sector_mapping.json  # 行业分类
    └── backtest_real_2025_2026.json  # 回测数据
```

## 回测结果

基于2025年1月-2026年4月127只港股IPO真实数据：

- **Strong Buy信号**：100%准确率
- **Buy信号**：97.1%准确率
- **整体准确率**：73.1%

## License

MIT
