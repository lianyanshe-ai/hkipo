import json
from hk_ipo_screener.core.types import IPODTO, ScoreResult
from hk_ipo_screener.core.veto_filter import VetoFilter


class ScoringEngine:
    """HK IPO Scoring Engine v3.0 — data-driven weights from 127 real IPOs (2025-2026).

    Scoring breakdown (max 100):
        subscription : 40 pts  — strongest predictor (17% win @ <5x → 100% @ 500x+)
        sector       : 25 pts  — hot sectors 83% win vs cold 63%
        sponsor      : 15 pts  — moderate signal, tiered
        greenshoe    :  5 pts  — rare but strong when present
        pe_valuation :  5 pts  — discount/premium adjustment
        market_cap   :  5 pts  — large-cap stability bonus
        base         :  5 pts  — participation score
    """

    def __init__(self, whitelist_path: str, sector_path: str):
        with open(whitelist_path) as f:
            self.whitelist = json.load(f)
        with open(sector_path) as f:
            self.sector_map = json.load(f)
        self.veto_filter = VetoFilter(whitelist_path, sector_path)

    def score(self, ipo: IPODTO) -> ScoreResult:
        veto_result = self.veto_filter.check(ipo)

        if veto_result.triggered and not veto_result.exempt:
            return ScoreResult(
                total=0,
                decision="🔴 VETO",
                breakdown={},
                veto_triggered=True,
                veto_reasons=veto_result.reasons
            )

        scores = {}

        # --- Sponsor (15 pts) ---
        sponsor = ipo.sponsor
        tiers = self.whitelist["sponsor_tiers"]
        bottom = self.whitelist.get("bottom_sponsors", [])
        if any(s in sponsor for s in tiers["tier0"]):
            scores["sponsor"] = 15
        elif any(s in sponsor for s in tiers["tier1"]):
            scores["sponsor"] = 13
        elif any(s in sponsor for s in tiers["tier2"]):
            scores["sponsor"] = 10
        elif any(s in sponsor for s in tiers["tier3"]):
            scores["sponsor"] = 6
        elif any(s in sponsor for s in bottom):
            scores["sponsor"] = 3
        else:
            scores["sponsor"] = 5

        # --- Cornerstone bonus (separate from main score, adds up to 10) ---
        cs_list = ipo.cornerstone_investors
        pct = ipo.cornerstone_pct
        whitelist = self.whitelist["cornerstone_whitelist"]
        cs_whitelist_count = sum(1 for c in cs_list if any(w in c for w in whitelist))

        cs_bonus = 0
        if veto_result.exempt:
            cs_bonus = 3
        elif cs_whitelist_count >= 2 and 0.30 <= pct <= 0.70:
            cs_bonus = 10
        elif cs_whitelist_count >= 1 and 0.25 <= pct <= 0.75:
            cs_bonus = 7
        elif cs_whitelist_count >= 1:
            cs_bonus = 4
        elif pct > 0:
            cs_bonus = 2
        scores["cornerstone"] = cs_bonus

        # --- Greenshoe (5 pts) ---
        if ipo.greenshoe:
            stabilizers = self.whitelist["stabilizer_top"]
            stabilizer = str(ipo.stabilizer)
            scores["greenshoe"] = 5 if any(s in stabilizer for s in stabilizers) else 3
        else:
            scores["greenshoe"] = 0

        # --- Sector/Industry (25 pts) ---
        industry = ipo.industry
        tier1 = self.sector_map["tier1_hard_tech"]
        tier2 = self.sector_map["tier2_biomed"]
        tier3 = self.sector_map["tier3_growth"]
        tier4 = self.sector_map["tier4_consumer"]

        if any(t in industry for t in tier1):
            sector_score = 25
        elif any(t in industry for t in tier2):
            sector_score = 20
        elif any(t in industry for t in tier3):
            sector_score = 15
        elif any(t in industry for t in tier4):
            sector_score = 10
        else:
            sector_score = 5

        # Hot sector bonus (from data: hot sectors have 83% win rate)
        if ipo.sector_hot:
            sector_score = min(sector_score + 5, 25)

        scores["sector"] = sector_score

        # --- Subscription ratio (40 pts) — strongest predictor ---
        sub = ipo.subscription_ratio
        if sub >= 500:
            scores["subscription"] = 40  # 100% win rate, avg +164%
        elif sub >= 200:
            scores["subscription"] = 36  # 97% win rate, avg +98%
        elif sub >= 100:
            scores["subscription"] = 32
        elif sub >= 50:
            scores["subscription"] = 28  # 97% win rate
        elif sub >= 20:
            scores["subscription"] = 22
        elif sub >= 10:
            scores["subscription"] = 16  # 75% win rate
        elif sub >= 5:
            scores["subscription"] = 10
        elif sub >= 2:
            scores["subscription"] = 5   # 17% win rate below 5x
        else:
            scores["subscription"] = 0   # Very low demand = danger

        # --- PE Valuation (5 pts) ---
        pe_bonus = 0
        if ipo.pe is not None and ipo.industry_pe_avg is not None:
            if ipo.pe < ipo.industry_pe_avg * 0.7:
                pe_bonus = 5   # Significant discount
            elif ipo.pe < ipo.industry_pe_avg * 0.9:
                pe_bonus = 3   # Moderate discount
            elif ipo.pe > ipo.industry_pe_avg * 2.0:
                pe_bonus = -3  # Extreme premium
            elif ipo.pe > ipo.industry_pe_avg * 1.5:
                pe_bonus = -1  # High premium
        scores["pe_valuation"] = max(pe_bonus, 0)

        # --- Market cap stability (5 pts) ---
        mcap = ipo.market_cap
        if mcap >= 500:
            scores["market_cap"] = 5   # Large cap, more stable
        elif mcap >= 100:
            scores["market_cap"] = 3
        elif mcap >= 30:
            scores["market_cap"] = 1
        else:
            scores["market_cap"] = 0   # Micro cap, higher risk

        # --- Base participation (5 pts) ---
        scores["base"] = 5

        total = sum(scores.values())

        # Decision thresholds (calibrated to 2025-2026 data)
        if total >= 72:
            decision = "🟢 强烈建议打"
        elif total >= 60:
            decision = "🟡 建议打"
        elif total >= 48:
            decision = "🟡 谨慎观望"
        else:
            decision = "🔴 不建议打"

        return ScoreResult(
            total=total,
            decision=decision,
            breakdown=scores,
            veto_triggered=False,
            veto_reasons=[],
            exempt_note=veto_result.exempt_note if veto_result.exempt else ""
        )
