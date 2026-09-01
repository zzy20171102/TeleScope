"""Normalization: URL canonicalization, language detection, tokenization, entities."""
from __future__ import annotations

import hashlib
import re
import urllib.parse

TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term",
                   "utm_content", "fbclid", "gclid", "mc_cid", "mc_eid", "ref"}

STOPWORDS = {"the", "a", "an", "of", "in", "on", "for", "to", "and", "or",
             "as", "at", "by", "with", "from", "is", "are", "was", "were",
             "be", "been", "its", "his", "her", "their", "this", "that",
             "after", "over", "into", "amid", "says", "said", "new"}

# canonical -> aliases (en/zh); substring match for CJK, word-boundary regex for ascii
ENTITY_DICT: list[tuple[str, list[str]]] = [
    ("美国", ["United States", "U.S.", "USA", "America", "Washington", "White House", "Pentagon", "美国", "华盛顿", "白宫", "五角大楼"]),
    ("中国", ["China", "Chinese", "Beijing", "中国", "北京"]),
    ("俄罗斯", ["Russia", "Russian", "Moscow", "Kremlin", "俄罗斯", "莫斯科", "克里姆林宫"]),
    ("日本", ["Japan", "Japanese", "Tokyo", "日本", "东京"]),
    ("韩国", ["South Korea", "Seoul", "韩国", "首尔"]),
    ("朝鲜", ["North Korea", "Pyongyang", "朝鲜", "平壤"]),
    ("印度", ["India", "Indian", "New Delhi", "印度", "新德里"]),
    ("巴基斯坦", ["Pakistan", "巴基斯坦"]),
    ("伊朗", ["Iran", "Iranian", "Tehran", "伊朗", "德黑兰"]),
    ("以色列", ["Israel", "Israeli", "Jerusalem", "以色列", "耶路撒冷"]),
    ("巴勒斯坦", ["Palestine", "Palestinian", "Gaza", "West Bank", "巴勒斯坦", "加沙", "约旦河西岸"]),
    ("沙特阿拉伯", ["Saudi Arabia", "Riyadh", "沙特", "利雅得"]),
    ("土耳其", ["Turkey", "Turkiye", "Ankara", "Istanbul", "土耳其", "安卡拉", "伊斯坦布尔"]),
    ("乌克兰", ["Ukraine", "Ukrainian", "Kyiv", "乌克兰", "基辅"]),
    ("德国", ["Germany", "German", "Berlin", "德国", "柏林"]),
    ("法国", ["France", "French", "Paris", "法国", "巴黎"]),
    ("英国", ["United Kingdom", "UK", "Britain", "London", "英国", "伦敦"]),
    ("欧盟", ["European Union", "EU", "Brussels", "欧盟", "布鲁塞尔"]),
    ("北约", ["NATO", "北约"]),
    ("联合国", ["United Nations", "U.N.", "UN", "联合国"]),
    ("台湾地区", ["Taiwan", "台湾"]),
    ("香港", ["Hong Kong", "香港"]),
    ("东盟", ["ASEAN", "东盟", "东南亚国家联盟"]),
    ("澳大利亚", ["Australia", "Canberra", "澳大利亚", "堪培拉"]),
    ("加拿大", ["Canada", "Ottawa", "加拿大", "渥太华"]),
    ("巴西", ["Brazil", "Brasilia", "巴西", "巴西利亚"]),
    ("墨西哥", ["Mexico", "墨西哥"]),
    ("阿根廷", ["Argentina", "Buenos Aires", "阿根廷", "布宜诺斯艾利斯"]),
    ("南非", ["South Africa", "Pretoria", "南非"]),
    ("埃及", ["Egypt", "Cairo", "埃及", "开罗"]),
    ("尼日利亚", ["Nigeria", "Abuja", "尼日利亚"]),
    ("埃塞俄比亚", ["Ethiopia", "Addis Ababa", "埃塞俄比亚"]),
    ("印尼", ["Indonesia", "Jakarta", "印度尼西亚", "雅加达"]),
    ("越南", ["Vietnam", "Hanoi", "越南", "河内"]),
    ("泰国", ["Thailand", "Bangkok", "泰国", "曼谷"]),
    ("缅甸", ["Myanmar", "Burma", "Naypyidaw", "缅甸"]),
    ("菲律宾", ["Philippines", "Manila", "菲律宾", "马尼拉"]),
    ("马来西亚", ["Malaysia", "Kuala Lumpur", "马来西亚", "吉隆坡"]),
    ("新加坡", ["Singapore", "新加坡"]),
]


def url_normalize(url: str) -> str:
    p = urllib.parse.urlsplit(url.strip())
    scheme = "https"
    host = (p.hostname or "").lower()
    path = p.path or "/"
    if len(path) > 1:
        path = path.rstrip("/")
    q = [(k, v) for k, v in urllib.parse.parse_qsl(p.query, keep_blank_values=False)
         if k not in TRACKING_PARAMS]
    q.sort()
    query = urllib.parse.urlencode(q)
    return urllib.parse.urlunsplit((scheme, host, path, query, ""))


def url_hash(url: str) -> str:
    return hashlib.sha256(url_normalize(url).encode("utf-8")).hexdigest()


def detect_lang(text: str) -> str:
    text = text or ""
    n = max(len(text), 1)
    counts = {"ja_kana": 0, "cjk": 0, "hangul": 0, "cyrillic": 0, "arabic": 0}
    for ch in text:
        o = ord(ch)
        if 0x3040 <= o <= 0x30FF:
            counts["ja_kana"] += 1
        elif 0x4E00 <= o <= 0x9FFF:
            counts["cjk"] += 1
        elif 0xAC00 <= o <= 0xD7AF:
            counts["hangul"] += 1
        elif 0x0400 <= o <= 0x04FF:
            counts["cyrillic"] += 1
        elif 0x0600 <= o <= 0x06FF:
            counts["arabic"] += 1
    if counts["ja_kana"] / n > 0.05:
        return "ja"
    if counts["cjk"] / n > 0.15:
        return "zh"
    if counts["hangul"] / n > 0.15:
        return "ko"
    if counts["cyrillic"] / n > 0.15:
        return "ru"
    if counts["arabic"] / n > 0.15:
        return "ar"
    return "en"


_WORD_RE = re.compile(r"[a-zA-Z]{2,}|[\u4e00-\u9fff]|[0-9]+")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _WORD_RE.findall(text or "") if t.lower() not in STOPWORDS]


def token_set(text: str) -> set[str]:
    toks = tokenize(text)
    out = set(toks)
    cjk = [t for t in toks if len(t) == 1 and "\u4e00" <= t <= "\u9fff"]
    for a, b in zip(cjk, cjk[1:]):
        out.add(a + b)
    return out


def extract_entities(text: str, limit: int = 20) -> list[str]:
    found: list[str] = []
    low = (text or "").lower()
    for canonical, aliases in ENTITY_DICT:
        hit = False
        for al in aliases:
            if al.isascii():
                if re.search(r"(?<![a-z0-9])" + re.escape(al.lower()) + r"(?![a-z0-9])", low):
                    hit = True
                    break
            elif al in (text or ""):
                hit = True
                break
        if hit:
            found.append(canonical)
            if len(found) >= limit:
                break
    return found
