import json
import os
import re
from typing import Optional
from hk_ipo_screener.core.types import IPODTO

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

def _load_whitelist() -> list[str]:
    """从 whitelist.json 加载基石白名单（单一数据源）"""
    path = os.path.join(_DATA_DIR, "whitelist.json")
    try:
        with open(path) as f:
            data = json.load(f)
        return data.get("cornerstone_whitelist", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def parse_subscription_ratio(text: str) -> float:
    match = re.search(r'(\d+(?:\.\d+)?)\s*[xX倍]', text)
    if match:
        return float(match.group(1))
    match = re.search(r'超额认购.*?(\d+(?:\.\d+)?)\s*倍', text)
    if match:
        return float(match.group(1))
    match = re.search(r'认购.*?(\d+(?:\.\d+)?)\s*[xX]', text)
    if match:
        return float(match.group(1))
    return 0.0

def parse_offer_price(text: str) -> Optional[float]:
    m = re.search(r'(?:发行价|发售价|招股价)[^\d]*?HK?\$?\s*([\d.]+)', text)
    if m:
        return float(m.group(1))
    m = re.search(r'HK?\$\s*([\d.]+)\s*元', text)
    if m:
        return float(m.group(1))
    return None

def parse_cornerstone(text: str) -> list[str]:
    cs = []
    for pat in [
        r'基石投资者[：:]\s*([^\n]+)',
        r'基石[：:]\s*([^\n]+)',
        r'Cornerstone[^\n]*?[：:]\s*([^\n]+)',
        r'基石认购[^\n]*?[：:]\s*([^\n]+)',
    ]:
        m = re.search(pat, text)
        if m:
            raw = m.group(1)
            names = re.split(r'[，、,\n]+', raw)
            cs = [n.strip() for n in names if n.strip() and len(n.strip()) > 2]
            if cs:
                break
    if not cs or len(cs) < 2:
        m = re.search(r'基石(.*?)(?:。|$)', text)
        if m:
            raw = m.group(1)
            names = re.split(r'[，、,\n]+', raw)
            cs = [n.strip() for n in names if n.strip() and len(n.strip()) > 2]
        if len(cs) < 2:
            m = re.search(r'基石(.*)$', text)
            if m:
                raw = m.group(1)
                names = re.split(r'[，、,\n]+', raw)
                cs = [n.strip() for n in names if n.strip() and len(n.strip()) > 2]

    junk_prefixes = ['投资者包括', '包括', '合计', '认购', '参与', '基石']
    clean_cs = []
    for c in cs:
        c = c.strip()
        for jp in junk_prefixes:
            if c.startswith(jp):
                c = c[len(jp):]
        c = re.sub(r'\d+家$', '', c)
        c = re.sub(r'等\d+家$', '', c)
        c = re.sub(r'等$', '', c)
        if c and len(c) > 2:
            clean_cs.append(c)
    cs = clean_cs if clean_cs else cs
    whitelist = _load_whitelist()
    filtered = [c for c in cs if any(w in c for w in whitelist)]
    return filtered if filtered else cs[:5]

def parse_sponsor(text: str) -> str:
    for pat in [
        r'保荐人[：:]\s*([^\n，。]+)',
        r'联席保荐[^\n]*?(?:[：:]\s*)?([^\n，。]+)',
        r'主承销商[：:]\s*([^\n，。]+)',
        r'Sponsor[^\n]*?[：:]\s*([^\n，。]+)',
    ]:
        m = re.search(pat, text)
        if m:
            result = m.group(1).strip()
            result = re.sub(r'，行业.+$', '', result)
            result = re.sub(r'，市值.+$', '', result)
            result = re.sub(r'，PE[^\n]+$', '', result)
            if result:
                return result
    return ""

def parse_stabilizer(text: str) -> str:
    for pat in [
        r'稳价人[：:]\s*([^\n，。、]+)',
        r'稳定价格操作人[：:]\s*([^\n，。、]+)',
        r'Stabilizing[^\n]*?[：:]\s*([^\n，。、]+)',
        r'稳价承办[^\n]*?[：:]\s*([^\n，。、]+)',
        r'稳价人\s*([^\n，。、]+)',
        r'stabilizer\s*([^\n，。、]+)',
    ]:
        m = re.search(pat, text)
        if m:
            return m.group(1).strip()
    return ""

def parse_greenshoe(text: str) -> tuple[bool, float]:
    if re.search(r'绿鞋|超额配股|greenshoe', text, re.I):
        m = re.search(r'(\d+(?:\.\d+)?)\s*%', text)
        pct = float(m.group(1)) if m else 15.0
        return True, pct
    return False, 0.0

def parse_market_cap(text: str) -> Optional[float]:
    m = re.search(r'(?:市值|发行后总市值)[^\d]*?(\d+(?:\.\d+)?)\s*亿', text)
    if m:
        return float(m.group(1))
    m = re.search(r'market cap.*?(\d+(?:\.\d+)?)\s*b', text, re.I)
    if m:
        return float(m.group(1)) * 100
    return None

def parse_cs_pct(text: str) -> float:
    m = re.search(r'(?:占(?:全球)?发售[^0-9]*?)(\d+(?:\.\d+)?)\s*%', text)
    if m:
        pct = float(m.group(1))
        if 1 <= pct <= 100:
            return pct / 100
    m = re.search(r'基石[^\d]*?(\d+(?:\.\d+)?)\s*%', text)
    if m:
        pct = float(m.group(1))
        if 1 <= pct <= 100:
            return pct / 100
    m = re.search(r'占比[^\d]*?(\d+(?:\.\d+)?)\s*%', text)
    if m:
        pct = float(m.group(1))
        if 1 <= pct <= 100:
            return pct / 100
    return 0.0

def parse_industry(text: str) -> str:
    industries = [
        "AI", "人工智能", "机器人", "半导体", "芯片", "集成电路", "光芯片",
        "创新药", "医疗器械", "生物医药", "生物科技", "新能源", "电动车",
        "汽车智能化", "云计算", "SaaS", "软件", "消费电子", "食品",
        "饮料", "户外", "环保", "物流", "保险", "融资租赁", "人力资源",
        "游戏", "文娱", "房地产", "建筑", "铜工艺", "金属加工", "AI医疗",
        "人力资源", "消费", "文娱", "计算机", "通信", "医药"
    ]
    for ind in industries:
        m = re.search(rf'行业\s*([^\s，。、]+)', text)
        if m:
            return m.group(1).strip()
    for ind in industries:
        if ind in text:
            return ind
    return ""

def parse_pe(text: str) -> Optional[float]:
    m = re.search(r'PE[^\d]*?(\d+(?:\.\d+)?)', text)
    if m:
        return float(m.group(1))
    m = re.search(r'市盈率[^\d]*?(\d+(?:\.\d+)?)', text)
    if m:
        return float(m.group(1))
    return None

def build_ipo_from_text(code: str, name: str, search_text: str, listing_date: str = "", offer_price: float = 0.0) -> IPODTO:
    sponsor = parse_sponsor(search_text)
    stabilizer = parse_stabilizer(search_text)
    cornerstone = parse_cornerstone(search_text)
    cs_pct = parse_cs_pct(search_text)
    greenshoe, gs_pct = parse_greenshoe(search_text)
    industry = parse_industry(search_text)
    pe = parse_pe(search_text)
    mcap = parse_market_cap(search_text)
    price = parse_offer_price(search_text) or offer_price
    sub = parse_subscription_ratio(search_text)

    return IPODTO(
        code=code,
        name=name,
        listing_date=listing_date,
        offer_price=price,
        market_cap=mcap or 0.0,
        sponsor=sponsor,
        stabilizer=stabilizer,
        cornerstone_investors=cornerstone,
        cornerstone_pct=cs_pct,
        greenshoe=greenshoe,
        greenshoe_pct=gs_pct,
        industry=industry,
        subscription_ratio=sub,
        pe=pe
    )

def fetch_ipo_from_hkex(code: str) -> Optional[IPODTO]:
    raise NotImplementedError("Use search + build_ipo_from_text workflow")

def fetch_ipo_from_media(name: str) -> Optional[dict]:
    raise NotImplementedError("Use search + build_ipo_from_text workflow")

def enrich_ipo(ipo: IPODTO) -> IPODTO:
    return ipo