import pytest

from app.conflicts import THRESHOLD, match_score, normalize_name


@pytest.mark.parametrize("a,b", [
    ("髙橋 一郎", "高橋一郎"),
    ("齋藤 誠", "斉藤誠"),
    ("斎藤 誠", "齊藤　誠"),
    ("渡邊健太", "渡辺 健太"),
    ("山﨑太郎", "山崎 太郎"),
    ("ヤマダ タロウ", "やまだたろう"),
    ("ｻﾝﾌﾟﾙ", "サンプル"),
    ("株式会社サンプル商事", "サンプル商事株式会社"),
    ("(株)サンプル商事", "㈱サンプル商事"),
    ("ＡＢＣ㈱", "ABC株式会社"),
    ("一般社団法人 テスト協会", "テスト協会"),
    ("山田太郎 様", "山田太郎"),
    ("霞ヶ関商事", "霞ケ関商事"),
])
def test_normalize_equal(a, b):
    assert normalize_name(a) == normalize_name(b)


def test_kana_match():
    score, why = match_score("佐藤 健", "サトウケン", "佐東 健", "さとう けん")
    assert score >= THRESHOLD and "読み" in why


def test_maiden_name_in_parentheses():
    score, _ = match_score("山田花子(旧姓佐藤花子)", "", "佐藤 花子", "")
    assert score == 1.0


def test_trade_name_alias():
    score, _ = match_score("鈴木一郎こと鈴木商店", "", "鈴木商店", "")
    assert score == 1.0


@pytest.mark.parametrize("a,b", [
    ("田中一郎", "高橋一郎"),
    ("山田太郎", "鈴木花子"),
    ("株式会社まるで無関係", "株式会社サンプル商事"),
])
def test_different_names_not_matched(a, b):
    score, _ = match_score(a, "", b, "")
    assert score < THRESHOLD


def test_same_given_name_different_family_by_kana_not_matched():
    score, _ = match_score("田中一郎", "タナカイチロウ", "高橋一郎", "タカハシイチロウ")
    assert score < THRESHOLD
