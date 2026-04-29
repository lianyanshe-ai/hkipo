"""港股IPO智能打新评估工具 CLI v3.0"""

import argparse
import json
import os
import sys
from pathlib import Path

from hk_ipo_screener.core.scoring import ScoringEngine
from hk_ipo_screener.core.report import generate_report
from hk_ipo_screener.core.types import IPODTO
from hk_ipo_screener.core.scraper import (
    parse_cornerstone, parse_sponsor, parse_stabilizer,
    parse_greenshoe, parse_market_cap, parse_cs_pct,
    parse_industry, parse_pe, parse_subscription_ratio,
    build_ipo_from_text
)

# Resolve data paths relative to this package (works after pip install)
_DATA_DIR = Path(__file__).parent / "data"
_WHITELIST_PATH = str(_DATA_DIR / "whitelist.json")
_SECTOR_PATH = str(_DATA_DIR / "sector_mapping.json")


def _make_engine() -> ScoringEngine:
    """Create ScoringEngine with bundled data files."""
    return ScoringEngine(
        whitelist_path=_WHITELIST_PATH,
        sector_path=_SECTOR_PATH
    )


def fetch_with_exa(name: str, code: str, api_key: str) -> str:
    try:
        import urllib.request
        query = f"{name} {code} 港股 IPO 保荐人 基石 绿鞋 孖展 发行价"
        params = json.dumps({
            "query": query,
            "numResults": 5,
            "texts": {"maxCharacters": 5000, "includeAnswer": True}
        }).encode()
        req = urllib.request.Request(
            "https://api.exa.ai/search",
            data=params,
            headers={
                "Authorization": api_key,
                "Content-Type": "application/json",
                "User-Agent": "HKIPO-Screener-v3.0"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        texts = []
        if "results" in data:
            for r in data["results"]:
                if isinstance(r, dict):
                    title = r.get("title", "")
                    snippet = r.get("highlight", "") or r.get("snippet", "")
                    url = r.get("url", "")
                    texts.append(f"来源: {url}\n标题: {title}\n内容: {snippet}")
        return "\n\n".join(texts)
    except Exception as e:
        return f"[EXA搜索失败: {e}]"


def fetch_with_minimax(name: str, api_key: str) -> str:
    try:
        import urllib.request
        query = f"{name} 港股 IPO 保荐人 基石 绿鞋 孖展认购 超额认购"
        params = json.dumps({"query": query, "num_results": 8}).encode()
        req = urllib.request.Request(
            "https://api.minimax.chat/v1/search",
            data=params,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        results = data.get("results", data.get("data", {}).get("results", []))
        texts = []
        for r in results:
            if isinstance(r, dict):
                title = r.get("title", "")
                snippet = r.get("snippet", "") or r.get("content", "")
                url = r.get("url", "")
                texts.append(f"来源: {url}\n标题: {title}\n内容: {snippet}")
        return "\n\n".join(texts)
    except Exception as e:
        return f"[MiniMax搜索失败: {e}]"


def _fetch_search_results(name: str, code: str, api_key: str) -> str:
    text = fetch_with_exa(name, code, api_key)
    if not text or "[EXA搜索失败" in text:
        text = fetch_with_minimax(name, api_key)
    return text


def cmd_score(args):
    """Score a single IPO with manually specified fields."""
    ipo = IPODTO(
        code=args.code, name=args.name, listing_date=args.date,
        offer_price=args.price, market_cap=args.mcap,
        sponsor=args.sponsor, stabilizer=args.stabilizer,
        cornerstone_investors=args.cs, cornerstone_pct=args.cs_pct,
        greenshoe=args.greenshoe, industry=args.industry,
        subscription_ratio=args.sub, pe=args.pe, industry_pe_avg=args.ind_pe
    )
    engine = _make_engine()
    result = engine.score(ipo)
    print(generate_report(ipo, result))


def cmd_search(args):
    """Parse raw search text and score an IPO."""
    ipo = build_ipo_from_text(
        code=args.code,
        name=args.name,
        search_text=args.text,
        listing_date=args.date,
        offer_price=args.price
    )
    engine = _make_engine()
    result = engine.score(ipo)
    print(generate_report(ipo, result))


def cmd_auto(args):
    """Auto-search via Exa/MiniMax API and score."""
    api_key = os.environ.get("EXA_API_KEY") or os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        print("Error: Set EXA_API_KEY or MINIMAX_API_KEY environment variable")
        sys.exit(1)
    search_text = _fetch_search_results(args.name, args.code, api_key)
    if not search_text:
        print(f"Error: No search results found for {args.name}")
        sys.exit(1)
    ipo = build_ipo_from_text(
        code=args.code,
        name=args.name,
        search_text=search_text,
        listing_date=args.date,
        offer_price=args.price
    )
    engine = _make_engine()
    result = engine.score(ipo)
    print(generate_report(ipo, result))


def cmd_backtest(args):
    """Run backtest on historical IPOs."""
    from hk_ipo_screener.backtest.replay import run_backtest
    run_backtest()


def main():
    parser = argparse.ArgumentParser(
        prog="hkipo",
        description="港股IPO智能打新评估工具 v3.0 — 基于127只真实IPO数据回测校准"
    )
    sub = parser.add_subparsers(dest="cmd")

    # score command
    p = sub.add_parser("score", help="手动输入参数评分")
    p.add_argument("--code", required=True, help="股票代码")
    p.add_argument("--name", required=True, help="公司名称")
    p.add_argument("--date", required=True, help="上市日期")
    p.add_argument("--price", type=float, required=True, help="发行价(HKD)")
    p.add_argument("--mcap", type=float, required=True, help="市值(亿港元)")
    p.add_argument("--sponsor", required=True, help="保荐人")
    p.add_argument("--stabilizer", default="", help="稳价人")
    p.add_argument("--cs", nargs="*", default=[], help="基石投资者")
    p.add_argument("--cs-pct", type=float, default=0.0, help="基石占比(0-1)")
    p.add_argument("--greenshoe", action="store_true", help="是否有绿鞋")
    p.add_argument("--industry", required=True, help="行业分类")
    p.add_argument("--sub", type=float, default=0.0, help="超额认购倍数")
    p.add_argument("--pe", type=float, default=None, help="市盈率")
    p.add_argument("--ind-pe", type=float, default=None, help="行业平均PE")

    # search command
    ps = sub.add_parser("search", help="解析搜索文本并评分(推荐)")
    ps.add_argument("--code", required=True, help="股票代码")
    ps.add_argument("--name", required=True, help="公司名称")
    ps.add_argument("--date", required=True, help="上市日期")
    ps.add_argument("--price", type=float, default=0.0, help="发行价(HKD)")
    ps.add_argument("--text", required=True, help="原始搜索结果文本")

    # auto command
    pa = sub.add_parser("auto", help="自动搜索+评分(需要EXA_API_KEY)")
    pa.add_argument("--code", required=True, help="股票代码")
    pa.add_argument("--name", required=True, help="公司名称")
    pa.add_argument("--date", required=True, help="上市日期")
    pa.add_argument("--price", type=float, default=0.0, help="发行价(HKD)")

    # backtest command
    sub.add_parser("backtest", help="运行历史IPO回测")

    args = parser.parse_args()

    if args.cmd == "score":
        cmd_score(args)
    elif args.cmd == "search":
        cmd_search(args)
    elif args.cmd == "auto":
        cmd_auto(args)
    elif args.cmd == "backtest":
        cmd_backtest(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
