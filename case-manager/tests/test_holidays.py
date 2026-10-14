import datetime as dt

import pytest

from app.holidays_jp import holiday_name, holidays_of_year

D = dt.date


@pytest.mark.parametrize("day,name", [
    (D(2026, 1, 1), "元日"),
    (D(2026, 1, 12), "成人の日"),
    (D(2026, 2, 23), "天皇誕生日"),
    (D(2026, 3, 20), "春分の日"),
    (D(2026, 5, 6), "振替休日"),        # 5/3(日)の振替。5/4・5/5 が祝日のため 5/6
    (D(2026, 9, 21), "敬老の日"),
    (D(2026, 9, 22), "国民の休日"),      # 敬老の日と秋分の日に挟まれた日
    (D(2026, 9, 23), "秋分の日"),
    (D(2026, 10, 12), "スポーツの日"),
    (D(2025, 2, 24), "振替休日"),
    (D(2024, 5, 6), "振替休日"),
    (D(2019, 4, 30), "国民の休日"),
    (D(2019, 5, 1), "天皇の即位の日"),
    (D(2019, 5, 2), "国民の休日"),
    (D(2019, 10, 22), "即位礼正殿の儀の行われる日"),
    (D(2020, 7, 24), "スポーツの日"),
    (D(2021, 8, 9), "振替休日"),
    (D(2027, 3, 22), "振替休日"),        # 春分の日 3/21(日)
    (D(2018, 12, 24), "振替休日"),       # 天皇誕生日 12/23(日)
])
def test_known_holidays(day, name):
    assert holiday_name(day) == name


@pytest.mark.parametrize("day", [D(2019, 12, 23), D(2026, 12, 23), D(2026, 7, 21), D(2026, 5, 7)])
def test_not_holidays(day):
    assert holiday_name(day) is None


def test_count_per_year():
    # 2026年の祝日・休日は 18 日(国民の休日 9/22 を含む)
    assert len(holidays_of_year(2026)) == 18
