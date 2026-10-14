"""利益相反チェック用の氏名・名称の正規化と照合。

見落としより過剰検出を優先する(最終判断は弁護士が行う)。
"""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

# 異体字・旧字 → 代表字(過剰検出側に寄せる)
VARIANTS = {
    "髙": "高", "﨑": "崎", "嵜": "崎", "碕": "崎", "邊": "辺", "邉": "辺", "齋": "斉", "齊": "斉", "斎": "斉",
    "澤": "沢", "濱": "浜", "濵": "浜", "廣": "広", "櫻": "桜", "冨": "富", "國": "国", "眞": "真",
    "惠": "恵", "德": "徳", "藪": "薮", "龍": "竜", "萬": "万", "學": "学", "實": "実", "壽": "寿",
    "與": "与", "榮": "栄", "舘": "館", "嶋": "島", "嶌": "島", "峯": "峰", "栁": "柳", "曾": "曽",
    "淵": "渕", "條": "条", "莊": "荘", "藏": "蔵", "圓": "円", "槗": "橋", "桒": "桑", "瀨": "瀬",
    "鷗": "鴎", "槇": "槙", "增": "増", "黑": "黒", "險": "険", "邨": "村", "埜": "野",
    "冲": "沖", "髮": "髪", "瀧": "滝", "傳": "伝", "徠": "来", "禮": "礼",
    "籐": "藤", "鐵": "鉄", "驒": "騨", "靜": "静", "淸": "清", "晉": "晋", "亞": "亜",
    "惡": "悪", "營": "営", "驛": "駅", "戶": "戸", "佛": "仏", "絲": "糸", "雙": "双",
    "ヶ": "ケ", "ヵ": "カ", "ゑ": "え", "ゐ": "い", "ヱ": "エ", "ヰ": "イ",
}

CORP_WORDS = [
    "株式会社", "有限会社", "合同会社", "合資会社", "合名会社", "一般社団法人", "一般財団法人",
    "公益社団法人", "公益財団法人", "社会福祉法人", "医療法人社団", "医療法人財団", "医療法人",
    "学校法人", "宗教法人", "特定非営利活動法人", "npo法人", "弁護士法人", "税理士法人", "司法書士法人",
    "(株)", "(有)", "(合)", "(同)", "(一社)", "(一財)", "(医)", "(社)", "(財)", "(学)",
    "co.,ltd.", "co.ltd.", "co.,ltd", "inc.", "inc", "ltd.", "ltd", "llc", "corp.", "corporation", "k.k.",
]

HONORIFICS = ["様", "殿", "さん", "氏", "先生"]

_SPACE_RE = re.compile(r"[\s・･.,、。,\-‐―ー−_/]")


def kata_to_hira(s: str) -> str:
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def normalize_name(name: str) -> str:
    """表記ゆれを吸収した照合キー。"""
    s = unicodedata.normalize("NFKC", name or "").lower()
    s = "".join(VARIANTS.get(c, c) for c in s)
    for w in CORP_WORDS:
        s = s.replace(unicodedata.normalize("NFKC", w), "")
    for h in HONORIFICS:
        if s.endswith(h) and len(s) > len(h) + 1:
            s = s[: -len(h)]
    s = kata_to_hira(s)
    s = _SPACE_RE.sub("", s)
    return s


def similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def split_variants(name: str) -> list[str]:
    """「山田花子(旧姓佐藤)」「A社こと山田」等から照合候補を作る。"""
    s = unicodedata.normalize("NFKC", name or "")
    parts = re.split(r"[()()\[\]「」『』//]|こと|旧姓|旧商号|又は|または|ほか", s)
    out = [s] + [p for p in parts if p.strip()]
    seen, res = set(), []
    for p in out:
        k = normalize_name(p)
        if len(k) >= 2 and k not in seen:
            seen.add(k)
            res.append(k)
    return res


def match_score(query: str, query_kana: str, cand_name: str, cand_kana: str) -> tuple[float, str]:
    """(スコア, 判定理由)。スコア1.0=正規化後一致。"""
    best, reason = 0.0, ""
    for qk in split_variants(query):
        for ck in split_variants(cand_name):
            if qk == ck:
                return 1.0, "氏名が一致(表記ゆれ吸収後)"
            sc = similarity(qk, ck)
            if (len(qk) >= 3 and qk in ck) or (len(ck) >= 3 and ck in qk):
                sc = max(sc, 0.85)
                why = "氏名の一部が一致"
            else:
                why = "氏名が類似"
            if sc > best:
                best, reason = sc, why
    qn, cn = normalize_name(query_kana), normalize_name(cand_kana)
    if qn and cn:
        if qn == cn:
            return max(best, 0.95), "読み(カナ)が一致"
        # 読みの部分一致は「名が同じで姓が違う」別人を拾いやすいため、高い類似度のみ採る
        ks = similarity(qn, cn)
        if ks >= KANA_THRESHOLD and ks > best:
            best, reason = ks, "読み(カナ)が類似"
    return best, reason


THRESHOLD = 0.75
KANA_THRESHOLD = 0.9
