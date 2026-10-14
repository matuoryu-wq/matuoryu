import datetime as dt

import pytest

from app.deadlines import PRESETS, compute_deadline, compute_preset

D = dt.date


def test_civil_appeal_plain():
    # 2026/10/1(木)送達 → 起算日 10/2 → 14日目 10/15(木)
    _, r = compute_preset("civil_appeal", D(2026, 10, 1))
    assert r.first_day == D(2026, 10, 2)
    assert r.due == D(2026, 10, 15)
    assert any("民訴法285条" in b for b in r.basis)
    assert any("初日不算入" in s for s in r.steps)


def test_civil_appeal_ends_on_saturday():
    # 10/3(土)送達 → 末日 10/17(土) → 10/18(日) → 10/19(月)
    _, r = compute_preset("civil_appeal", D(2026, 10, 3))
    assert r.raw_end == D(2026, 10, 17)
    assert r.due == D(2026, 10, 19)
    assert any("土曜日" in s for s in r.steps) and any("日曜日" in s for s in r.steps)
    assert any("95条3項" in b for b in r.basis)


def test_civil_appeal_year_end():
    # 12/17(木)送達 → 末日 12/31 → 1/1 元日 → 1/2・1/3 → 2027/1/4(月)
    _, r = compute_preset("civil_appeal", D(2026, 12, 17))
    assert r.raw_end == D(2026, 12, 31)
    assert r.due == D(2027, 1, 4)


def test_golden_week():
    # 4/21送達 → 末日 5/5(祝) → 5/6(振替休日) → 5/7(木)
    _, r = compute_preset("civil_appeal", D(2026, 4, 21))
    assert r.raw_end == D(2026, 5, 5)
    assert r.due == D(2026, 5, 7)


def test_souzoku_houki_months():
    # 1/31に知った → 起算日 2/1 → 応当日 5/1 の前日 4/30(木)
    _, r = compute_preset("souzoku_houki", D(2026, 1, 31))
    assert r.due == D(2026, 4, 30)
    assert any("民法915条1項" in b for b in r.basis)
    assert any("143条" in b for b in r.basis)


def test_month_without_corresponding_day():
    # 11/29に知った → 起算日 11/30 → 3か月後の応当日(2/30)なし → 2/28(日) → 3/1(月)
    _, r = compute_preset("souzoku_houki", D(2026, 11, 29))
    assert r.raw_end == D(2027, 2, 28)
    assert r.due == D(2027, 3, 1)
    assert any("末日" in s and "143条2項ただし書" in s for s in r.steps)


def test_month_feb_end_saturday():
    # 2025/11/30 → 起算日 12/1 → 応当日 3/1 の前日 2/28(土) → 3/2(月)
    r = compute_deadline(D(2025, 11, 30), 3, "month", "minpo")
    assert r.raw_end == D(2026, 2, 28)
    assert r.due == D(2026, 3, 2)


def test_criminal_appeal():
    # 刑訴: 10/14(水)宣告 → 10/28(水)
    _, r = compute_preset("criminal_appeal", D(2026, 10, 14))
    assert r.due == D(2026, 10, 28)
    assert any("刑訴法55条" in b for b in r.basis)


def test_criminal_kokoku_weekend():
    # 即時抗告3日: 10/15(木)告知 → 末日 10/18(日) → 10/19(月)
    _, r = compute_preset("criminal_kokoku", D(2026, 10, 15))
    assert r.due == D(2026, 10, 19)


def test_include_first_day():
    r = compute_deadline(D(2026, 10, 14), 3, "day", "minpo", include_first_day=True)
    assert r.due == D(2026, 10, 16)
    assert r.warnings


def test_no_extension():
    r = compute_deadline(D(2026, 10, 3), 2, "week", "minso", extend_on_holiday=False)
    assert r.due == D(2026, 10, 17)
    assert any("延長していません" in w for w in r.warnings)


def test_custom_holiday_extends():
    extra = {D(2026, 10, 15): "庁舎閉庁"}
    r = compute_deadline(D(2026, 10, 1), 2, "week", "minso", extra_holidays=extra)
    assert r.due == D(2026, 10, 16)
    assert any("登録休日" in s for s in r.steps)


def test_year_unit():
    r = compute_deadline(D(2026, 2, 28), 1, "year", "minpo")
    # 起算日 3/1 → 応当日 2027/3/1 の前日 2/28(日) → 3/1(月)
    assert r.raw_end == D(2027, 2, 28)
    assert r.due == D(2027, 3, 1)


def test_all_presets_compute():
    for p in PRESETS:
        _, r = compute_preset(p.code, D(2026, 10, 14))
        assert r.due >= D(2026, 10, 14)
        assert r.steps and r.basis


@pytest.mark.parametrize("bad", [0, -1])
def test_invalid_amount(bad):
    with pytest.raises(ValueError):
        compute_deadline(D(2026, 1, 1), bad, "day")
