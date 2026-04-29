import json
from pathlib import Path
from hk_ipo_screener.core.scoring import ScoringEngine
from hk_ipo_screener.core.types import IPODTO

_DATA_DIR = Path(__file__).parent.parent / "data"

def load_engine():
    return ScoringEngine(
        whitelist_path=str(_DATA_DIR / "whitelist.json"),
        sector_path=str(_DATA_DIR / "sector_mapping.json")
    )

def load_real_data():
    """Load real 2025-2026 IPO data from JSON file."""
    with open(_DATA_DIR / "backtest_real_2025_2026.json") as f:
        return json.load(f)

def get_ipo_data():
    """Legacy data for backward compatibility."""
    return load_real_data()

def classify_decision(result):
    """Classify scoring result into buy/skip/hold."""
    if result.veto_triggered:
        return "skip"
    if result.total >= 72:
        return "buy"
    if result.total >= 60:
        return "hold"
    return "skip"

def run_backtest():
    engine = load_engine()
    data = load_real_data()

    total = len(data)
    results = []

    # Stats
    tp = fp = tn = fn = 0  # true/false positive/negative
    hold_correct = hold_total = 0
    veto_correct = veto_total = 0
    exempt_count = 0

    for item in data:
        ipo = IPODTO(
            code=item["code"], name=item["name"], listing_date=item["listing_date"],
            offer_price=item["offer_price"], market_cap=item["market_cap"],
            sponsor=item["sponsor"], stabilizer=item.get("stabilizer",""),
            cornerstone_investors=item.get("cornerstone_investors",[]),
            cornerstone_pct=item.get("cornerstone_pct", 0.0),
            greenshoe=item.get("greenshoe", False),
            greenshoe_pct=item.get("greenshoe_pct", 0.0),
            industry=item.get("industry",""), sector_hot=item.get("sector_hot", False),
            pe=item.get("pe"), industry_pe_avg=item.get("industry_pe_avg"),
            subscription_ratio=item.get("subscription_ratio", 0.0)
        )
        result = engine.score(ipo)

        actual_pct = float(item["actual"].replace("%","").replace("+",""))
        actual_buy = actual_pct > 0
        actual_profit = actual_pct > 5   # meaningful profit
        actual_loss = actual_pct < -5    # meaningful loss

        decision = classify_decision(result)

        # Evaluate correctness
        if decision == "buy":
            if actual_buy:
                tp += 1
                hit = True
            else:
                fp += 1
                hit = False
        elif decision == "skip":
            if result.veto_triggered:
                veto_total += 1
                if not actual_buy or actual_loss:
                    veto_correct += 1
            if not actual_buy:
                tn += 1
                hit = True
            else:
                fn += 1
                hit = False
        else:  # hold
            hold_total += 1
            hit = True  # hold is always "correct" (no action)
            if actual_buy:
                hold_correct += 1

        if result.exempt_note:
            exempt_count += 1

        results.append({
            "code": item["code"],
            "name": item["name"],
            "actual": item["actual"],
            "actual_pct": actual_pct,
            "actual_buy": actual_buy,
            "decision": decision,
            "v2_decision": result.decision,
            "v2_total": result.total,
            "hit": hit,
            "veto": result.veto_triggered,
            "reasons": result.veto_reasons if result.veto_triggered else [],
            "exempt": result.exempt_note if result.exempt_note else None,
            "breakdown": result.breakdown
        })

    # Calculate metrics
    actionable = tp + fp + tn + fn
    correct = tp + tn
    accuracy = correct / actionable if actionable > 0 else 0

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    # Profit analysis for "buy" recommendations
    buy_results = [r for r in results if r["decision"] == "buy"]
    buy_returns = [r["actual_pct"] for r in buy_results]
    avg_buy_return = sum(buy_returns) / len(buy_returns) if buy_returns else 0
    win_rate = sum(1 for r in buy_returns if r > 0) / len(buy_returns) if buy_returns else 0

    # Skip analysis
    skip_results = [r for r in results if r["decision"] == "skip"]
    skip_returns = [r["actual_pct"] for r in skip_results]
    avg_skip_return = sum(skip_returns) / len(skip_returns) if skip_returns else 0

    # Print report
    print(f"\n{'='*70}")
    print(f"  HK IPO Screener v2.0 Backtest Report (Real Data 2025-2026)")
    print(f"{'='*70}")
    print(f"")
    print(f"  Dataset: {total} IPOs | {len([r for r in results if '2025' in r['code'][:4] or True])} scored")
    print(f"  Period:  2025-01 to 2026-04")
    print(f"")
    print(f"  --- Classification Metrics ---")
    print(f"  Actionable:  {actionable} (buy + skip decisions)")
    print(f"  Correct:     {correct} ({accuracy:.1%})")
    print(f"  TP (buy→up):   {tp} | FP (buy→down): {fp}")
    print(f"  TN (skip→down):{tn} | FN (skip→up):  {fn}")
    print(f"  Precision:   {precision:.1%} | Recall: {recall:.1%} | F1: {f1:.1%}")
    print(f"")
    print(f"  --- Profit Analysis ---")
    print(f"  Buy signals:     {len(buy_results)} | Avg return: {avg_buy_return:+.1f}% | Win rate: {win_rate:.1%}")
    print(f"  Skip signals:    {len(skip_results)} | Avg return: {avg_skip_return:+.1f}%")
    print(f"  VETO triggered:  {veto_total} | VETO correct: {veto_correct}")
    print(f"  Exempt applied:  {exempt_count}")
    print(f"")
    print(f"  --- Value of Model ---")
    print(f"  If $10k per buy signal: ${10000 * (1 + avg_buy_return/100):,.0f} avg return")
    print(f"  Avoided avg loss by skipping: {avg_skip_return:+.1f}%")
    print(f"{'='*70}")
    print(f"")

    # Detail table
    print(f"| # | Code | Name | Actual | Decision | Score | Hit | Breakdown |")
    print(f"|---|------|------|--------|----------|-------|-----|-----------|")
    for i, r in enumerate(results, 1):
        flag = "✅" if r["hit"] else "❌"
        bd = r["breakdown"]
        bd_str = f"S{bd.get('sponsor',0)} C{bd.get('cornerstone',0)} G{bd.get('greenshoe',0)} F{bd.get('fundamentals',0)} M{bd.get('sentiment',0)}"
        print(f"| {i} | {r['code']} | {r['name'][:8]} | {r['actual']:>8} | {r['v2_decision'][:8]} | {r['v2_total']:>3} | {flag} | {bd_str} |")

    print(f"\n--- Error Analysis ---")
    for r in results:
        if not r["hit"]:
            print(f"  ❌ {r['name']} ({r['code']}): actual={r['actual']}, decision={r['v2_decision']}, score={r['v2_total']}, reasons={r['reasons']}, exempt={r['exempt']}")

    # Score distribution analysis
    print(f"\n--- Score Distribution ---")
    brackets = [(80, 100, "Strong Buy"), (70, 80, "Buy"), (58, 70, "Hold"), (0, 58, "Skip")]
    for lo, hi, label in brackets:
        bracket_results = [r for r in results if lo <= r["v2_total"] < hi and not r["veto"]]
        if bracket_results:
            ups = sum(1 for r in bracket_results if r["actual_pct"] > 0)
            avg_ret = sum(r["actual_pct"] for r in bracket_results) / len(bracket_results)
            print(f"  {label} ({lo}-{hi}): {len(bracket_results)} IPOs | {ups}/{len(bracket_results)} up | avg {avg_ret:+.1f}%")

    veto_results = [r for r in results if r["veto"]]
    if veto_results:
        veto_ups = sum(1 for r in veto_results if r["actual_pct"] > 0)
        veto_avg = sum(r["actual_pct"] for r in veto_results) / len(veto_results)
        print(f"  VETO: {len(veto_results)} IPOs | {veto_ups}/{len(veto_results)} up | avg {veto_avg:+.1f}%")

    return accuracy, results

if __name__ == "__main__":
    run_backtest()
