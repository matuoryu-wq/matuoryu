"""法定期間の計算。

計算結果は「計算値」であり、確定は人間が行う(承認操作が必要)。
各結果に根拠条文と計算過程を付ける。
"""
from __future__ import annotations

import calendar
import datetime as dt
from dataclasses import dataclass, field

from .holidays_jp import holiday_name

D = dt.date
WEEKDAYS = "月火水木金土日"


def fmt(d: D) -> str:
    return f"{d.year}年{d.month}月{d.day}日({WEEKDAYS[d.weekday()]})"


# ---------------------------------------------------------------- 休日ルール

@dataclass(frozen=True)
class RuleSet:
    code: str
    name: str
    first_day_rule: str      # 初日不算入の根拠
    month_rule: str          # 暦による計算の根拠
    holiday_rule: str        # 末日休日の扱いの根拠
    saturday: bool           # 土曜を休日として扱うか
    year_end: bool           # 1/2,1/3,12/29〜31 を休日として扱うか
    note: str = ""


RULESETS: dict[str, RuleSet] = {
    "minso": RuleSet(
        "minso", "民事訴訟法(家事・非訟も準用)",
        "民訴法95条1項・民法140条(初日不算入)",
        "民訴法95条1項・民法143条(暦に従って計算)",
        "民訴法95条3項(末日が日曜・土曜・祝日法の休日・1月2日・3日・12月29日〜31日の場合は翌日に満了)",
        True, True,
        "家事事件手続法34条4項、非訟事件手続法32条4項で民訴法95条が準用される。",
    ),
    "keiso": RuleSet(
        "keiso", "刑事訴訟法",
        "刑訴法55条1項(初日不算入。ただし時効期間の初日は算入)",
        "刑訴法55条2項(月・年は暦に従う)",
        "刑訴法55条3項(末日が日曜・土曜・祝日法の休日・1月2日・3日・12月29日〜31日の場合は期間に算入しない。時効期間を除く)",
        True, True,
    ),
    "minpo": RuleSet(
        "minpo", "民法(実体法上の期間)",
        "民法140条(初日不算入。午前零時から始まるときは算入)",
        "民法143条(暦に従って計算。応当日の前日に満了、応当日がなければ月末)",
        "民法142条(末日が日曜・祝日法の休日その他の休日で、その日に取引をしない慣習がある場合に限り翌日に満了)",
        True, True,
        "民法142条は「取引をしない慣習」がある場合に限る。土曜・年末年始を休日扱いにするかは"
        "事案ごとに確認すること。家庭裁判所・行政庁への申述・提出は実務上翌開庁日まで扱われることが多いが、"
        "安全側(延長前の日)での対応を推奨する。",
    ),
}


def holiday_reason(day: D, rs: RuleSet, extra: dict[D, str] | None = None) -> str | None:
    if day.weekday() == 6:
        return "日曜日"
    if rs.saturday and day.weekday() == 5:
        return "土曜日"
    name = holiday_name(day)
    if name:
        return f"祝日法の休日({name})"
    if rs.year_end and ((day.month == 1 and day.day in (2, 3)) or (day.month == 12 and day.day >= 29)):
        return "年末年始(1月2日・3日・12月29日〜31日)"
    if extra and day in extra:
        return f"登録休日({extra[day]})"
    return None


# ---------------------------------------------------------------- プリセット

@dataclass(frozen=True)
class Preset:
    code: str
    name: str
    field: str            # 分野
    amount: int
    unit: str             # day / week / month / year
    ruleset: str
    basis: str            # 根拠条文
    start_event: str      # 起算点の説明
    note: str = ""


PRESETS: list[Preset] = [
    Preset("civil_appeal", "控訴期間(民事)", "民事", 2, "week", "minso",
           "民訴法285条", "判決書又は調書判決の送達を受けた日",
           "判決言渡し前に提起した控訴も有効(285条ただし書)。"),
    Preset("civil_jokoku", "上告期間・上告受理申立期間(民事)", "民事", 2, "week", "minso",
           "民訴法313条・285条、318条5項", "判決書の送達を受けた日"),
    Preset("civil_appeal_brief", "控訴理由書提出期間(民事)", "民事", 50, "day", "minso",
           "民訴規則182条", "控訴の提起の日",
           "裁判所から別途期間の指定がある場合はそれに従う。"),
    Preset("civil_jokoku_brief", "上告理由書提出期間(民事)", "民事", 50, "day", "minso",
           "民訴規則194条", "上告提起通知書の送達を受けた日"),
    Preset("civil_immediate", "即時抗告期間(民事)", "民事", 1, "week", "minso",
           "民訴法332条", "裁判の告知を受けた日"),
    Preset("shiharai_tokusoku", "仮執行宣言付支払督促に対する督促異議", "民事", 2, "week", "minso",
           "民訴法393条", "仮執行宣言付支払督促の送達を受けた日",
           "期間経過後は仮執行宣言付支払督促が確定判決と同一の効力を有する(396条)。"),
    Preset("rodo_shinpan", "労働審判に対する異議申立て", "労働", 2, "week", "minso",
           "労働審判法21条1項", "審判書の送達又は審判の告知を受けた日"),
    Preset("kaji_immediate", "家事審判に対する即時抗告", "家事", 2, "week", "minso",
           "家事事件手続法86条1項・2項、34条4項", "審判の告知を受けた日(申立人以外は即時抗告権者が告知を受けた日)",
           "申立人による却下審判への即時抗告など起算点の例外(86条2項)に注意。"),
    Preset("kaji_hoshi_appeal", "家事調停に代わる審判への異議", "家事", 2, "week", "minso",
           "家事事件手続法286条2項・3項", "審判の告知を受けた日"),
    Preset("souzoku_houki", "相続放棄・限定承認の熟慮期間", "相続", 3, "month", "minpo",
           "民法915条1項", "自己のために相続の開始があったことを知った時",
           "家庭裁判所に期間伸長の申立てが可能(915条1項ただし書)。起算点(知った時)の認定は事実関係による。"),
    Preset("iryubun", "遺留分侵害額請求権の消滅時効", "相続", 1, "year", "minpo",
           "民法1048条前段", "相続の開始及び遺留分を侵害する贈与又は遺贈があったことを知った時",
           "相続開始から10年の除斥期間(1048条後段)にも注意。時効の完成猶予・更新事由を別途確認。"),
    Preset("gyosei_torikeshi", "取消訴訟の出訴期間", "行政", 6, "month", "minso",
           "行政事件訴訟法14条1項", "処分又は裁決があったことを知った日",
           "処分の日から1年(14条2項)の制限、正当な理由による例外にも注意。初日不算入は最判昭和52年2月17日。末日の休日の扱いは行訴法7条により民訴法95条によるとして計算。"),
    Preset("gyosei_shinsa", "審査請求期間(行政不服審査法)", "行政", 3, "month", "minpo",
           "行政不服審査法18条1項", "処分があったことを知った日の翌日から起算",
           "処分の日の翌日から1年(18条2項)の制限にも注意。"),
    Preset("criminal_appeal", "控訴提起期間(刑事)", "刑事", 14, "day", "keiso",
           "刑訴法373条", "判決宣告の日",
           "判決宣告日が起算日の前日(初日不算入)。"),
    Preset("criminal_jokoku", "上告提起期間(刑事)", "刑事", 14, "day", "keiso",
           "刑訴法414条・373条", "判決宣告の日"),
    Preset("criminal_kokoku", "即時抗告(刑事)", "刑事", 3, "day", "keiso",
           "刑訴法422条", "裁判の告知を受けた日"),
    Preset("criminal_junkokoku", "準抗告(過料・費用賠償の裁判)", "刑事", 3, "day", "keiso",
           "刑訴法429条1項4号・5号、4項", "裁判のあった日",
           "勾留・保釈・押収等に関する裁判(429条1項2号)への準抗告には期間の定めがない。"),
]
PRESETS_BY_CODE = {p.code: p for p in PRESETS}

UNIT_LABEL = {"day": "日", "week": "週間", "month": "箇月", "year": "年"}


# ---------------------------------------------------------------- 計算

@dataclass
class DeadlineResult:
    start_event_date: D
    first_day: D
    raw_end: D
    due: D
    steps: list[str] = field(default_factory=list)
    basis: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "start_event_date": self.start_event_date.isoformat(),
            "first_day": self.first_day.isoformat(),
            "raw_end": self.raw_end.isoformat(),
            "due": self.due.isoformat(),
            "due_label": fmt(self.due),
            "steps": self.steps,
            "basis": self.basis,
            "warnings": self.warnings,
        }


def add_months_end(first_day: D, months: int) -> tuple[D, str]:
    """民法143条2項: 起算日に応当する日の前日に満了。応当日がなければその月の末日。"""
    total = first_day.month - 1 + months
    y, m = first_day.year + total // 12, total % 12 + 1
    last = calendar.monthrange(y, m)[1]
    if first_day.day > last:
        end = D(y, m, last)
        return end, f"{y}年{m}月に起算日({first_day.day}日)の応当日がないため、その月の末日 {fmt(end)} に満了(民法143条2項ただし書)"
    corr = D(y, m, first_day.day)
    end = corr - dt.timedelta(days=1)
    return end, f"起算日の応当日 {fmt(corr)} の前日 {fmt(end)} に満了(民法143条2項本文)"


def compute_deadline(
    event_date: D,
    amount: int,
    unit: str,
    ruleset: str = "minso",
    include_first_day: bool = False,
    extend_on_holiday: bool = True,
    extra_holidays: dict[D, str] | None = None,
    basis: str | None = None,
) -> DeadlineResult:
    if amount <= 0:
        raise ValueError("期間は1以上で指定してください")
    if unit not in UNIT_LABEL:
        raise ValueError(f"不明な単位: {unit}")
    rs = RULESETS[ruleset]
    steps: list[str] = []
    basis_list = [basis] if basis else []
    basis_list += [rs.first_day_rule]
    warnings: list[str] = []

    steps.append(f"起算点となる事実の日: {fmt(event_date)}")
    if include_first_day:
        first = event_date
        steps.append(f"初日を算入する(午前零時から開始する場合等)。起算日 = {fmt(first)}")
        warnings.append("初日算入としています。初日不算入の原則(民法140条等)の例外に当たるか確認してください。")
    else:
        first = event_date + dt.timedelta(days=1)
        steps.append(f"初日不算入のため、翌日 {fmt(first)} を起算日とする")

    label = f"{amount}{UNIT_LABEL[unit]}"
    if unit in ("day", "week"):
        days = amount * (7 if unit == "week" else 1)
        raw_end = first + dt.timedelta(days=days - 1)
        if unit == "week":
            steps.append(f"{label} = {days}日")
        steps.append(f"起算日から{days}日目 = {fmt(raw_end)}(期間の末日)")
    else:
        months = amount * (12 if unit == "year" else 1)
        basis_list.append(rs.month_rule)
        raw_end, msg = add_months_end(first, months)
        steps.append(f"{label}を暦に従って計算: {msg}")

    due = raw_end
    if extend_on_holiday:
        basis_list.append(rs.holiday_rule)
        while (reason := holiday_reason(due, rs, extra_holidays)):
            nxt = due + dt.timedelta(days=1)
            steps.append(f"{fmt(due)} は{reason}のため、翌日 {fmt(nxt)} に延長")
            due = nxt
        if due == raw_end:
            steps.append(f"末日 {fmt(due)} は休日に当たらない")
    else:
        steps.append("末日が休日でも延長しない設定(時効期間等)")
        if holiday_reason(due, rs, extra_holidays):
            warnings.append(f"末日 {fmt(due)} は休日ですが延長していません。")

    steps.append(f"期限: {fmt(due)} の終了(午後12時)まで")
    if rs.note:
        warnings.append(rs.note)
    return DeadlineResult(event_date, first, raw_end, due, steps, basis_list, warnings)


def compute_preset(code: str, event_date: D, extra_holidays: dict[D, str] | None = None) -> tuple[Preset, DeadlineResult]:
    p = PRESETS_BY_CODE[code]
    res = compute_deadline(event_date, p.amount, p.unit, p.ruleset,
                           extra_holidays=extra_holidays, basis=f"{p.basis}({p.amount}{UNIT_LABEL[p.unit]})")
    res.steps.insert(0, f"起算点: {p.start_event}")
    if p.code == "gyosei_shinsa":
        res.steps.insert(1, "行審法18条1項は「知った日の翌日から起算」と規定(初日不算入と同じ結論)")
    if p.note:
        res.warnings.insert(0, p.note)
    return p, res
