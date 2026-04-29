import json
from dataclasses import dataclass
from typing import Optional
from hk_ipo_screener.core.types import IPODTO


@dataclass
class VetoResult:
    triggered: bool
    reasons: list[str]
    exempt: bool
    exempt_note: str


class VetoFilter:
    """VETO filter v3.0 — calibrated against 127 real IPOs (2025-2026).

    Key insight: subscription ratio is the strongest danger signal.
    IPOs with <2x subscription have only 17% win rate (avg -17.6%).
    The old "小投行+无基石" rule was too aggressive (vetoed 13 winners).

    VETO rules:
        V1: Subscription <2x AND cold sector AND no top sponsor
            → Very low demand in unfavorable sector = high risk
        V2: PE >200x AND cold sector AND no cornerstone
            → Extreme valuation with no institutional backing

    Exemption:
        Retail frenzy: subscription >500x + hot sector → bypass V1
    """

    def __init__(self, whitelist_path: str, sector_path: str):
        with open(whitelist_path) as f:
            self.whitelist = json.load(f)
        with open(sector_path) as f:
            self.sector_map = json.load(f)

    def _is_hot_sector(self, industry: str) -> bool:
        hot = self.whitelist.get("hot_sectors", [])
        return any(h in industry for h in hot)

    def _is_cold_sector(self, industry: str) -> bool:
        cold = self.sector_map.get("tier5_traditional", [])
        return any(c in industry for c in cold)

    def _has_top_sponsor(self, sponsor: str) -> bool:
        tiers = self.whitelist["sponsor_tiers"]
        # tier0 and tier1 are "top"
        top = tiers.get("tier0", []) + tiers.get("tier1", [])
        return any(s in sponsor for s in top)

    def check(self, ipo: IPODTO) -> VetoResult:
        reasons = []
        sub = ipo.subscription_ratio
        industry = ipo.industry

        # V1: Very low demand + cold sector + no top sponsor
        # Data: <2x subscription has 17% win rate, avg -17.6%
        if sub < 2.0:
            is_cold = self._is_cold_sector(industry)
            has_top = self._has_top_sponsor(ipo.sponsor)
            if is_cold and not has_top:
                reasons.append(f"极低认购({sub}x)+冷门行业+无顶级保荐人")

        # V2: Extreme PE + cold sector + no cornerstone
        cs_list = ipo.cornerstone_investors
        has_any_cs = len(cs_list) > 0
        if (ipo.pe is not None
            and ipo.pe > 200
            and self._is_cold_sector(industry)
            and not has_any_cs):
            reasons.append(f"极高估值(PE {ipo.pe:.0f}x)+冷门行业+无基石")

        # Retail frenzy exemption check
        # Data: 500x+ subscription has 100% win rate
        exempt = False
        exempt_note = ""
        if sub >= 500 and self._is_hot_sector(industry) and len(reasons) > 0:
            reasons = []
            exempt = True
            exempt_note = f"【零售狂热豁免】认购{sub}x+热门赛道({industry})，市场极度追捧"

        return VetoResult(
            triggered=len(reasons) > 0,
            reasons=reasons,
            exempt=exempt,
            exempt_note=exempt_note
        )
