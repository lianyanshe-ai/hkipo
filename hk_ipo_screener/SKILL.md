---
name: hk-ipo-screener
version: 3.0.0
description: |
  港股IPO智能打新评估工具。告诉股票名称或代码，自动搜索招股数据并生成评分报告。
  工作流程: 搜索 → 解析(hkipo search) → 评分 → Markdown报告。
  VETO规则引擎过滤问题股，八维评分体系给出数据驱动的投资建议。
  回测准确率: 73.1% (19/26, 2026年1-4月)。
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - WebFetch
  - WebSearch
  - mcp__MiniMax__web_search
  - mcp__MiniMax__understand_image
---

# 港股IPO打新评估工具 v3.0

基于127只2025-2026年真实港股IPO数据回测校准的智能评分引擎。

## 安装

```bash
pip install git+https://github.com/lianyanshe/HKIPO.git
```

或克隆后本地安装：

```bash
git clone https://github.com/lianyanshe/HKIPO.git
cd HKIPO
pip install -e .
```

## 工作流程（必须按顺序执行）

```
Step 1: 搜索 IPO 数据
  使用 WebSearch 搜索: "{公司名} {代码} 港股 IPO 保荐人 基石 绿鞋 超额认购"
  收集所有包含以下字段的搜索结果:
  - 保荐人（联席保荐/主承销商）
  - 基石投资者名单 + 占比
  - 孖展认购倍数
  - 绿鞋（超额配股）
  - 稳价人
  - 发行价/招股价
  - 市值
  - 行业分类

Step 2: 解析 + 评分
  将原始搜索文本传给 hkipo search 命令:
  hkipo search \
    --code {代码} \
    --name "{公司名}" \
    --date {上市日期} \
    --price {发行价} \
    --text "{完整搜索结果文本}"

Step 3: 输出报告
  CLI 自动解析所有字段，生成八维评分报告
```

## 快速使用

### 手动搜索模式（推荐，不需要 API key）
```bash
# Step 1: 用 WebSearch 搜索收集数据
# Step 2: 将文本传给 search 命令
hkipo search \
  --code 1879 \
  --name "曦智科技" \
  --date 2026-04-28 \
  --price 183.2 \
  --text "基石阿里巴巴、GIC Private Limited、富达国际、贝莱德，红杉中国、云锋基金，认购约16.44亿港元，占全球发售股份约50%，孖展认购78倍，15%绿鞋，稳价人高盛，行业AI，市值845亿港元，PE=500，联席保荐高盛、中金公司"
```

### 自动搜索模式（需要 EXA_API_KEY 或 MINIMAX_API_KEY）
```bash
EXA_API_KEY=$EXA_API_KEY \
  hkipo auto \
  --code 1879 \
  --name "曦智科技" \
  --date 2026-04-28 \
  --price 183.2
```

### 回测验证
```bash
hkipo backtest
```

## VETO 规则（命中即放弃）

v3.0 精简为2条数据驱动的VETO规则（旧版4条规则过于激进，误杀了13只盈利股）：

| 规则 | 触发条件 | 含义 |
|---|---|---|
| V1 | 认购<2x + 冷门行业 + 无顶级保荐人 | 极低需求+无机构背书 |
| V2 | PE>200x + 冷门行业 + 无基石 | 极端估值+无机构锁仓 |

### 零售狂热豁免
- 条件：认购≥500x **且** 热门赛道
- 效果：豁免所有VETO（数据：500x+认购的IPO胜率100%）

## 八维评分（满分100分）

基于127只真实IPO数据回测校准的权重分配：

| 维度 | 最高分 | 评分逻辑 |
|---|---|---|
| ① 认购热度 | 40分 | 500x+=40, 200x=36, 100x=32, 50x=28, 20x=22, 10x=16, 5x=10, 2x=5, <2=0 |
| ② 行业赛道 | 25分 | T1硬科技25→T2生医20→T3成长15→T4消费10→T5传统5; 热门赛道+5 |
| ③ 保荐人 | 15分 | T0(摩根大通/大摩/高盛)15→T1(中金/中信/瑞银)13→T2(华泰/招银)10→T3(华兴等)6→底部3 |
| ④ 基石投资者 | 10分 | ≥2家白名单+占比30-70%→10; ≥1家+占比合理→7; ≥1家→4; 有基石→2 |
| ⑤ 绿鞋机制 | 5分 | 头部稳价人=5; 其他稳价人=3; 无绿鞋=0 |
| ⑥ 估值合理性 | 5分 | PE<0.7x行业均值→5; <0.9x→3; >2x→-3; >1.5x→-1 |
| ⑦ 市值稳定性 | 5分 | ≥500亿=5; ≥100亿=3; ≥30亿=1; <30亿=0 |
| ⑧ 基础分 | 5分 | 参与即得5分 |

### 决策阈值
- **≥72分**: 🟢 强烈建议打
- **≥60分**: 🟡 建议打
- **≥48分**: 🟡 谨慎观望
- **<48分**: 🔴 不建议打
- **VETO触发**: 🔴 直接放弃

## 解析字段（scraper.py）

从搜索文本中自动提取：
- `保荐人` / `联席保荐` → sponsor
- `稳价人` → stabilizer
- `基石投资者` / `基石` → cornerstone_investors（白名单过滤）
- `占全球发售股份XX%` → cornerstone_pct
- `绿鞋` / `超额配股` → greenshoe（自动检测15%）
- `市值XX亿` → market_cap
- `行业` → industry（AI/半导体/创新药等）
- `PE` → pe / industry_pe_avg
- `超额认购XX倍` / `孖展XX倍` → subscription_ratio

## 已知局限

1. 冷门大盘股（顺丰/金山云）：强基石仍破发，模型无法预测市场情绪
2. 暗盘数据缺失：暗盘表现是更重要的参考
3. PE数据缺失时无低估/高估加成
4. 数据来源依赖财经媒体搜索，准确性由搜索质量决定

## 文件结构

```
hk_ipo_screener/
├── __init__.py              # 包入口 + 公共API导出
├── cli.py                   # CLI: hkipo score/search/auto/backtest
├── core/
│   ├── types.py             # IPODTO, ScoreResult, Decision 数据模型
│   ├── scoring.py           # 八维评分引擎 v3.0
│   ├── veto_filter.py       # VETO规则引擎 (2条规则+豁免)
│   ├── report.py            # Markdown报告生成器
│   └── scraper.py           # 搜索文本正则解析器 (11个parse函数)
├── backtest/
│   └── replay.py            # 127只新股回测运行器
└── data/
    ├── whitelist.json       # 26家基石白名单 + 保荐人分级 + 稳价人
    ├── sector_mapping.json  # 五级行业分类 (~120个关键词)
    └── backtest_real_2025_2026.json  # 127只真实IPO回测数据
```
