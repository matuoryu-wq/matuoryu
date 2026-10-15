"""AI送信前の匿名化と、応答の復元。

方針:
- 案件の当事者(氏名・カナ・姓・名・住所・電話・メール)、事件番号、手動登録語を辞書で置換する。
- 辞書にない会社名・住所・電話番号・メール・郵便番号・口座番号は正規表現で検出して置換する。
- 異体字(髙/高 等)・カタカナ/ひらがな・空白の有無の揺れを吸収して照合する。
- 送信直前に「置換漏れ検査」を行い、1語でも残っていれば送信しない(fail closed)。
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from .conflicts import CORP_WORDS, VARIANTS, kata_to_hira, normalize_name

PLACEHOLDER_RE = re.compile(r"【[^【】]{1,20}】")

# 異体字グループ: 文字 → その文字と同一視する文字の集合
_GROUPS: dict[str, set[str]] = {}
for _a, _b in VARIANTS.items():
    g = _GROUPS.get(_a) or _GROUPS.get(_b) or set()
    g |= {_a, _b}
    for ch in g:
        _GROUPS[ch] = g

ROLE_LABEL = {"依頼者": "依頼者", "相談者": "相談者", "相手方": "相手方", "相手方代理人": "相手方代理人",
              "関係者": "関係者"}

CORP_RE_WORDS = sorted({unicodedata.normalize("NFKC", w) for w in CORP_WORDS if not w.isascii()}, key=len, reverse=True)
_CORP_ALT = "|".join(re.escape(w) for w in CORP_RE_WORDS)
_NAME_CHARS = r"[一-龥々〆ヵヶァ-ヴーA-Za-z0-9&＆・\.]"

PREFS = ("北海道|青森県|岩手県|宮城県|秋田県|山形県|福島県|茨城県|栃木県|群馬県|埼玉県|千葉県|東京都|神奈川県|"
         "新潟県|富山県|石川県|福井県|山梨県|長野県|岐阜県|静岡県|愛知県|三重県|滋賀県|京都府|大阪府|兵庫県|"
         "奈良県|和歌山県|鳥取県|島根県|岡山県|広島県|山口県|徳島県|香川県|愛媛県|高知県|福岡県|佐賀県|"
         "長崎県|熊本県|大分県|宮崎県|鹿児島県|沖縄県")

AUTO_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("メール", re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")),
    ("電話", re.compile(r"(?<![\d-])0\d{1,4}-\d{1,4}-\d{3,4}(?![\d-])|(?<!\d)0[5789]0\d{8}(?!\d)|(?<!\d)0\d{9}(?!\d)")),
    ("郵便番号", re.compile(r"〒\s*\d{3}-?\d{4}|(?<![\d-])\d{3}-\d{4}(?![\d-])")),
    ("口座番号", re.compile(r"(?:口座番号|口座|普通|当座)\s*(?:No\.?|番号)?\s*[::]?\s*\d{6,8}")),
    ("番号", re.compile(r"(?<!\d)\d{4}\s?\d{4}\s?\d{4}(?!\d)")),   # マイナンバー等12桁
    ("住所", re.compile(rf"(?:{PREFS})[一-龥ァ-ヶー0-9\-−のがヶケ]{{2,40}}")),
    ("住所", re.compile(r"[一-龥]{1,5}[市区町村郡][一-龥ァ-ヶ]{0,12}\d+(?:丁目|番地|番|-|の)[\d\-番地号の]*")),
    ("会社", re.compile(rf"(?:{_CORP_ALT})\s*{_NAME_CHARS}{{1,20}}")),
    ("会社", re.compile(rf"{_NAME_CHARS}{{1,20}}?\s*(?:{_CORP_ALT})")),
]


# 敬称・肩書の直前の語は人名として自動置換する(辞書にない第三者・言い間違いの対策)
HONORIFICS = "さん|様|さま|氏|君|くん|ちゃん|先生|弁護士|裁判官|書記官|調停委員|部長|課長|係長|社長|専務|常務|会長|店長|主任"
TITLES = ["部長", "課長", "係長", "社長", "専務", "常務", "会長", "店長", "主任", "先生", "弁護士"]
NOT_NAMES = {
    "父", "母", "兄", "姉", "弟", "妹", "祖父", "祖母", "叔父", "叔母", "伯父", "伯母", "義父", "義母", "奥", "息子",
    "娘", "夫", "妻", "嫁", "婿", "孫", "親", "父親", "母親", "主人", "旦那", "奥様", "社長", "部長", "課長", "係長",
    "店長", "会長", "専務", "常務", "主任", "担当", "担当者", "先方", "皆", "皆様", "相手", "相手方", "依頼者", "相談者",
    "本人", "客", "大家", "管理人", "先生", "弁護士", "上司", "同僚", "友人", "知人", "彼", "彼女", "職員", "社員",
    "警察", "刑事", "検事", "裁判官", "書記官", "調停委員", "医師", "看護師", "業者", "隣人", "各位", "当方", "貴社",
    "御社", "弊社", "同氏", "両氏", "被告", "原告", "被告人", "証人", "申立人", "相続人", "被相続人", "代理人", "裁判所",
    "家裁", "地裁", "高裁", "検察官", "相手方代理人", "元夫", "元妻", "前妻", "前夫", "長男", "長女", "次男", "次女",
    "三男", "三女", "先輩", "後輩", "店員", "運転手", "家主", "所長", "院長", "校長", "担任", "大将", "神", "仏",
}
NAME_BEFORE_HONORIFIC = re.compile(rf"(?<![一-龥々])(?P<name>[一-龥々]{{1,4}}|[ァ-ヴー]{{2,8}})(?=\s?(?:{HONORIFICS}))")
BRACKETED = re.compile(r"(?<=「)(?P<name>[一-龥々]{2,4})(?=」)")


def nfkc(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "")


def _char_class(ch: str) -> str:
    opts = set(_GROUPS.get(ch, {ch}))
    if "ァ" <= ch <= "ヶ":
        opts.add(chr(ord(ch) - 0x60))
    elif "ぁ" <= ch <= "ゖ":
        opts.add(chr(ord(ch) + 0x60))
    if len(opts) == 1:
        return re.escape(ch)
    return "[" + "".join(re.escape(o) for o in sorted(opts)) + "]"


def term_pattern(term: str) -> str:
    """異体字・カナ・空白の揺れを許す正規表現。"""
    t = re.sub(r"\s+", "", nfkc(term))
    return r"[\s]*".join(_char_class(c) for c in t)


@dataclass
class Entry:
    original: str     # 復元時に戻す表記
    label: str        # 置換後の表記(【依頼者1】等)
    category: str
    pattern: re.Pattern
    check_key: str    # 漏れ検査用の正規化キー(空なら検査しない)


@dataclass
class Anonymizer:
    entries: list[Entry] = field(default_factory=list)
    auto: dict[str, str] = field(default_factory=dict)   # 自動検出: 元の表記 → ラベル
    counters: dict[str, int] = field(default_factory=dict)

    # ------------------------------------------------------------ 構築

    def _next(self, prefix: str) -> str:
        self.counters[prefix] = self.counters.get(prefix, 0) + 1
        return f"【{prefix}{self.counters[prefix]}】"

    def add(self, original: str, label: str, category: str, check: bool = True) -> None:
        original = nfkc(original).strip()
        if len(re.sub(r"\s", "", original)) < 2:
            return
        if any(e.original == original for e in self.entries):
            return
        key = normalize_name(original) if check else ""
        self.entries.append(Entry(original, label, category, re.compile(term_pattern(original)),
                                  key if len(key) >= 2 else ""))

    def add_party(self, role: str, name: str, kana: str = "", address: str = "", phone: str = "",
                  email: str = "") -> str:
        prefix = ROLE_LABEL.get(role, "関係者")
        name = nfkc(name).strip()
        corp = next((w for w in CORP_RE_WORDS if w in name), None)
        if corp:
            label = self._next(prefix)[:-1] + "(法人)】"
            core = name.replace(corp, "").strip()
            self.add(name, label, "会社")
            if len(core) >= 2:
                # 「株式会社」の前後・略記(㈱)を含めて置換するため、法人格つきの形も登録
                for w in CORP_RE_WORDS:
                    self.add(f"{w}{core}", label, "会社", check=False)
                    self.add(f"{core}{w}", label, "会社", check=False)
                self.add(core, label, "会社")
        else:
            label = self._next(prefix)
            self.add(name, label, "人物")
            parts = name.split()
            if len(parts) >= 2:
                fam, given = parts[0], "".join(parts[1:])
                self.add(fam, self._surname_label(fam), "人物(姓)")
                if len(given) >= 2:
                    self.add(given, label[:-1] + "(名)】", "人物(名)")
        if kana:
            kana_n = nfkc(kana).strip()
            self.add(kana_n, label, "読み")
            kp = kana_n.split()
            if len(kp) >= 2 and len(kp[0]) >= 2 and not corp:
                fam_label = self._surname_label(name.split()[0]) if len(name.split()) >= 2 else label
                self.add(kp[0], fam_label, "読み(姓)")
        if address:
            self.add(address, self._next("住所"), "住所")
        if phone:
            self.add(phone, self._next("電話"), "電話")
        if email:
            self.add(email, self._next("メール"), "メール")
        return label

    def _surname_label(self, fam: str) -> str:
        fam = nfkc(fam)
        key = normalize_name(fam)
        for e in self.entries:
            if e.category == "人物(姓)" and normalize_name(e.original) == key:
                return e.label
        return self._next("姓")

    # ------------------------------------------------------------ 置換・復元

    def anonymize(self, text: str) -> str:
        text = nfkc(text)
        # 長い語から置換(「斎藤 正」を「斎藤」より先に)
        for e in sorted(self.entries, key=lambda e: -len(e.original)):
            text = _sub_outside_placeholders(e.pattern, e.label, text)
        for cat, pat in AUTO_PATTERNS:
            def repl(m: re.Match, cat=cat) -> str:
                s = m.group(0)
                if cat == "会社" and not _looks_like_company(s):
                    return s
                if s not in self.auto:
                    self.auto[s] = self._next(cat)
                return self.auto[s]
            text = _sub_outside_placeholders(pat, repl, text)
        text = _sub_outside_placeholders(NAME_BEFORE_HONORIFIC, self._honorific_repl, text)
        text = _sub_outside_placeholders(BRACKETED, self._misspelling_repl, text)
        return text

    def _auto_label(self, s: str, prefix: str) -> str:
        if s not in self.auto:
            self.auto[s] = self._next(prefix)
        return self.auto[s]

    def _honorific_repl(self, m: re.Match) -> str:
        s = m.group("name")
        name = s
        for t in TITLES:
            if name.endswith(t) and len(name) > len(t):
                name = name[: -len(t)]
                break
        if name in NOT_NAMES or s in NOT_NAMES or (len(name) == 1 and not ("ァ" <= name[0] <= "ヴ")):
            return s
        return self._auto_label(name, "人物") + s[len(name):]

    def _misspelling_repl(self, m: re.Match) -> str:
        """「佐藤」のように括弧書きされた語が、登録済みの氏名と1字違いなら人名として置換する。"""
        s = m.group("name")
        for e in self.entries:
            if e.category.startswith(("人物", "会社")):
                o = _fold(re.sub(r"\s", "", e.original))
                if len(o) == len(s) and sum(a != b for a, b in zip(o, _fold(s))) == 1:
                    return self._auto_label(s, "人物")
        return s

    def restore(self, text: str) -> str:
        if not text:
            return text
        mapping = self.mapping()
        return PLACEHOLDER_RE.sub(lambda m: mapping.get(m.group(0), m.group(0)), text)

    def restore_obj(self, obj):
        if isinstance(obj, str):
            return self.restore(obj)
        if isinstance(obj, list):
            return [self.restore_obj(x) for x in obj]
        if isinstance(obj, dict):
            return {k: self.restore_obj(v) for k, v in obj.items()}
        return obj

    def mapping(self) -> dict[str, str]:
        m: dict[str, str] = {}
        # 同じラベルに複数の表記がある場合は、最初に登録した(正式な)表記で復元する
        for e in self.entries:
            m.setdefault(e.label, e.original)
        for orig, label in self.auto.items():
            m.setdefault(label, orig)
        return m

    # ------------------------------------------------------------ 漏れ検査

    def find_leaks(self, text: str) -> list[str]:
        """匿名化後のテキストに、匿名化対象の語が残っていないか検査する。"""
        leaks: list[str] = []
        stripped = PLACEHOLDER_RE.sub("|", nfkc(text))
        flat = normalize_name(stripped.replace("|", "\u0000"))
        flat_hira = kata_to_hira(flat)
        for e in self.entries:
            if e.pattern.search(stripped):
                leaks.append(e.original)
            elif e.check_key and e.check_key in flat_hira:
                leaks.append(e.original)
        for orig in self.auto:
            if orig in stripped:
                leaks.append(orig)
        return sorted(set(leaks))

    def summary(self) -> list[dict]:
        """画面表示用の置換一覧(PC内のみ)。"""
        seen, out = set(), []
        for e in self.entries:
            if (e.label, e.original) in seen or (e.category == "会社" and not e.check_key):
                continue   # 法人格の付け方の揺れ(内部用の別表記)は表示しない
            seen.add((e.label, e.original))
            out.append({"label": e.label, "original": e.original, "category": e.category})
        out += [{"label": v, "original": k, "category": "自動検出"} for k, v in self.auto.items()]
        return out


def _fold(s: str) -> str:
    return "".join(VARIANTS.get(c, c) for c in s)


def _looks_like_company(s: str) -> bool:
    core = s
    for w in CORP_RE_WORDS:
        core = core.replace(w, "")
    return len(core.strip()) >= 1


def _sub_outside_placeholders(pat: re.Pattern, repl, text: str) -> str:
    """既に置換済みの【…】の内部は書き換えない。"""
    out, last = [], 0
    for m in PLACEHOLDER_RE.finditer(text):
        out.append(pat.sub(repl, text[last:m.start()]))
        out.append(m.group(0))
        last = m.end()
    out.append(pat.sub(repl, text[last:]))
    return "".join(out)


class AnonymizationLeak(Exception):
    def __init__(self, leaks: list[str]):
        super().__init__(f"匿名化の漏れを検出したため送信を中止しました({len(leaks)}語)")
        self.leaks = leaks


def build_for_case(conn, case_id: int) -> Anonymizer:
    an = Anonymizer()
    for p in conn.execute("SELECT * FROM parties WHERE case_id=? ORDER BY CASE role WHEN '依頼者' THEN 0 "
                          "WHEN '相談者' THEN 1 WHEN '相手方' THEN 2 ELSE 3 END, id", (case_id,)):
        an.add_party(p["role"], p["name"], p["kana"] or "", p["address"] or "", p["phone"] or "", p["email"] or "")
    c = conn.execute("SELECT case_number FROM cases WHERE id=?", (case_id,)).fetchone()
    if c and c["case_number"]:
        an.add(c["case_number"], "【事件番号】", "事件番号", check=False)
    for t in conn.execute("SELECT * FROM anon_terms WHERE case_id=? ORDER BY id", (case_id,)):
        an.add(t["term"], an._next(t["category"] or "固有名"), t["category"] or "固有名")
    return an
