from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Decision(str, Enum):
    """投资决策枚举"""
    STRONG_BUY = "🟢 强烈建议打"
    BUY = "🟡 建议打"
    HOLD = "🟡 谨慎观望"
    SELL = "🔴 不建议打"
    VETO = "🔴 一票否决"


@dataclass
class IPODTO:
    # 基本信息
    code: str
    name: str
    listing_date: str
    offer_price: float
    market_cap: float  # 亿港元

    # ① 保荐人 + 稳价人
    sponsor: str  # 保荐人名称（含联席）
    stabilizer: str = ""  # 稳价人

    # ② 基石
    cornerstone_investors: list[str] = field(default_factory=list)
    cornerstone_pct: float = 0.0  # 0~1

    # ③ 绿鞋
    greenshoe: bool = False
    greenshoe_pct: float = 0.0  # 通常 15%

    # ④ 行业 + 基本面
    industry: str = ""
    sector_hot: bool = False
    pe: Optional[float] = None
    industry_pe_avg: Optional[float] = None

    # ⑤ 市场热度
    subscription_ratio: float = 0.0  # 超额认购倍数

    # === v3.0 新增字段 (全部 Optional，向后兼容) ===

    # 股份结构 (V5/VETO规则需要)
    old_shares_transfer_pct: Optional[float] = None  # 老股转让比例
    public_shares_pct: Optional[float] = None  # 公开发售占比

    # 财务指标 (基本面分析)
    revenue: Optional[float] = None  # 营收(亿)
    net_income: Optional[float] = None  # 净利润(亿)
    ps: Optional[float] = None  # 市销率
    pb: Optional[float] = None  # 市净率
    roe: Optional[float] = None  # 净资产收益率
    debt_to_equity: Optional[float] = None  # 资产负债率

    # 风险事项 (V7/VETO规则需要)
    material_litigation: bool = False  # 重大诉讼
    regulatory_actions: bool = False  # 监管处罚
    related_party_transactions_pct: Optional[float] = None  # 关联交易占比

    # 回测用
    actual_return: Optional[float] = None  # 实际首日涨幅 (0.1 = +10%)

    # 数据来源
    source_url: Optional[str] = None
    scraped_at: Optional[str] = None


@dataclass
class ScoreResult:
    total: int
    decision: str
    breakdown: dict[str, int]
    veto_triggered: bool
    veto_reasons: list[str]
    exempt_note: str = ""


@dataclass
class AnalysisResult:
    """完整分析结果 — v3.0 新增，封装评分+置信度+风险/机会+建议"""
    ipo: IPODTO
    score_result: ScoreResult
    decision: Decision
    confidence: float  # 0~0.99
    risk_factors: list[str]
    opportunity_factors: list[str]
    recommendation: str  # Markdown 格式的完整建议
