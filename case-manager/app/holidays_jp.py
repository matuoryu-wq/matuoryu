"""国民の祝日に関する法律に基づく休日の算出(2000〜2099年)。

外部データに依存せず計算する。春分・秋分の日は天文計算の近似式
(1980〜2099年で有効)による。官報公示(前年2月)と食い違う場合は、
アプリの「休日追加」で補正すること。
"""
from __future__ import annotations

import datetime as dt
from functools import lru_cache

D = dt.date


def _nth_monday(year: int, month: int, n: int) -> D:
    first = D(year, month, 1)
    offset = (7 - first.weekday()) % 7  # weekday(): 月=0
    return first + dt.timedelta(days=offset + 7 * (n - 1))


def _vernal_equinox(year: int) -> int:
    return int(20.8431 + 0.242194 * (year - 1980) - int((year - 1980) / 4))


def _autumnal_equinox(year: int) -> int:
    return int(23.2488 + 0.242194 * (year - 1980) - int((year - 1980) / 4))


def _base_holidays(year: int) -> dict[D, str]:
    h: dict[D, str] = {}

    def add(month: int, day: int, name: str) -> None:
        h[D(year, month, day)] = name

    add(1, 1, "元日")
    h[_nth_monday(year, 1, 2)] = "成人の日"
    add(2, 11, "建国記念の日")
    if year >= 2020:
        add(2, 23, "天皇誕生日")
    elif year <= 2018:
        add(12, 23, "天皇誕生日")
    add(3, _vernal_equinox(year), "春分の日")
    if year >= 2007:
        add(4, 29, "昭和の日")
        add(5, 4, "みどりの日")
    else:
        add(4, 29, "みどりの日")
    add(5, 3, "憲法記念日")
    add(5, 5, "こどもの日")

    # 海の日・山の日・スポーツの日(東京五輪特措法による2020・2021年の移動を含む)
    if year == 2020:
        add(7, 23, "海の日")
        add(7, 24, "スポーツの日")
        add(8, 10, "山の日")
    elif year == 2021:
        add(7, 22, "海の日")
        add(7, 23, "スポーツの日")
        add(8, 8, "山の日")
    else:
        if year >= 2003:
            h[_nth_monday(year, 7, 3)] = "海の日"
        else:
            add(7, 20, "海の日")
        if year >= 2016:
            add(8, 11, "山の日")
        h[_nth_monday(year, 10, 2)] = "スポーツの日" if year >= 2020 else "体育の日"

    if year >= 2003:
        h[_nth_monday(year, 9, 3)] = "敬老の日"
    else:
        add(9, 15, "敬老の日")
    add(9, _autumnal_equinox(year), "秋分の日")
    add(11, 3, "文化の日")
    add(11, 23, "勤労感謝の日")

    if year == 2019:  # 天皇の即位の日及び即位礼正殿の儀の行われる日を休日とする法律
        add(5, 1, "天皇の即位の日")
        add(10, 22, "即位礼正殿の儀の行われる日")
    return h


@lru_cache(maxsize=256)
def holidays_of_year(year: int) -> dict[D, str]:
    h = _base_holidays(year)
    # 振替休日(祝日法3条2項): 祝日が日曜 → その後の最も近い「祝日でない日」
    for day in sorted(h):
        if day.weekday() == 6:
            sub = day + dt.timedelta(days=1)
            while sub in h:
                sub += dt.timedelta(days=1)
            if sub.year == year:
                h[sub] = "振替休日"
    # 国民の休日(祝日法3条3項): 前日と翌日が祝日である日(日曜・祝日を除く)
    for day in sorted(h):
        mid = day + dt.timedelta(days=1)
        nxt = day + dt.timedelta(days=2)
        if nxt in h and mid not in h and mid.weekday() != 6:
            h[mid] = "国民の休日"
    return dict(sorted(h.items()))


def holiday_name(day: D) -> str | None:
    return holidays_of_year(day.year).get(day)
