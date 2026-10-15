import re

import pytest

from app.anonymize import Anonymizer


@pytest.fixture
def an():
    a = Anonymizer()
    a.add_party("依頼者", "髙橋 一郎", "タカハシ イチロウ", "東京都新宿区西新宿1-2-3", "090-0000-0001", "ichiro@example.com")
    a.add_party("相手方", "株式会社サンプル商事", "サンプルショウジ")
    a.add_party("関係者", "佐東 健", "サトウ ケン")
    a.add_party("相手方", "齋藤 誠", "さいとう まこと")
    a.add_party("依頼者", "斎藤 美咲", "サイトウ ミサキ")
    a.add("令和8年(ワ)第1234号", "【事件番号】", "事件番号", check=False)
    return a


SENSITIVE = ["髙橋", "高橋", "一郎", "タカハシ", "たかはし", "イチロウ", "サンプル商事", "サンプルショウジ", "佐東",
             "サトウ", "齋藤", "斎藤", "斉藤", "さいとう", "サイトウ", "まこと", "美咲", "ミサキ", "西新宿",
             "090-0000-0001", "ichiro@example.com", "1234号"]


@pytest.mark.parametrize("text", [
    "髙橋一郎さんが来所",
    "高橋 一郎氏",
    "高橋さんいわく",
    "たかはし いちろう",
    "タカハシイチロウ",
    "ｻﾝﾌﾟﾙ商事㈱",
    "(株)サンプル商事",
    "サンプル商事株式会社の佐東さん",
    "サトウさん",
    "斉藤誠は弟",
    "齊藤 誠",
    "美咲さん",
    "住所は東京都新宿区西新宿1-2-3",
    "電話 090-0000-0001 メール ichiro@example.com",
    "令和8年(ワ)第1234号",
])
def test_no_sensitive_terms_remain(an, text):
    out = an.anonymize(text)
    for w in SENSITIVE:
        assert w not in out, (text, out, w)
    assert an.find_leaks(out) == []


def test_restore_round_trip(an):
    text = "髙橋一郎は株式会社サンプル商事の佐東 健と取引した。"
    out = an.anonymize(text)
    assert "【依頼者1】" in out and "【相手方1(法人)】" in out
    assert an.restore(out) == "髙橋 一郎は株式会社サンプル商事の佐東 健と取引した。"


def test_surname_shared_by_family(an):
    labels = re.findall(r"【姓\d+】", an.anonymize("斎藤さんと齋藤さん"))
    assert len(labels) == 2 and labels[0] == labels[1]  # 同じ姓(異体字)は同じ記号


def test_auto_detection(an):
    text = ("担当は株式会社ミライとXYZ合同会社。住所は横浜市中区山下町1-2、〒231-0023、電話045-123-4567、"
            "口座番号 1234567。")
    out = an.anonymize(text)
    for w in ["ミライ", "XYZ", "山下町", "231-0023", "045-123-4567", "1234567"]:
        assert w not in out
    assert an.restore(out) == text


def test_dates_and_amounts_kept(an):
    text = "2026-05-10に面談。令和8年3月15日納品。金320万円(3,200,000円)。"
    assert an.anonymize(text) == text


def test_placeholders_not_rewritten():
    a = Anonymizer()
    a.add_party("依頼者", "依頼 太郎")   # ラベル【依頼者1】と同じ文字を含む氏名
    out = a.anonymize("依頼太郎と依頼者")
    assert out.startswith("【依頼者1】")
    assert a.restore(out).startswith("依頼 太郎")


def test_leak_detected_for_unusual_separator(an):
    # 中黒で区切られた氏名は置換されないが、漏れ検査が検出する
    out = an.anonymize("髙・橋さんの件")
    assert an.find_leaks(out)


def test_custom_term(an):
    an.add("グリーンヒルズ", "【固有名1】", "固有名")
    out = an.anonymize("マンション名はグリーンヒルズ")
    assert "グリーンヒルズ" not in out and an.find_leaks(out) == []


@pytest.mark.parametrize("text,name", [
    ("証人の田中さんによれば", "田中"),
    ("鈴木様からの電話", "鈴木"),
    ("担当の佐藤部長が対応", "佐藤"),
    ("ヤマモトさんが来た", "ヤマモト"),
    ("相手の佐藤さん、佐東さんだったかな", "佐藤"),
])
def test_unregistered_name_with_honorific(an, text, name):
    out = an.anonymize(text)
    assert name not in out and "【人物" in out
    assert an.restore(out) == text


@pytest.mark.parametrize("text", ["お父さんが言うには", "相手方さんに", "担当者様へ", "弁護士先生", "皆さん", "長男さん"])
def test_common_words_with_honorific_kept(an, text):
    assert an.anonymize(text) == text


def test_misspelled_registered_name_in_brackets(an):
    out = an.anonymize("相手方担当者は佐東氏(依頼者は「佐藤」と記憶)。「契約」の話も。")
    assert "佐藤" not in out and "佐東" not in out
    assert "「契約」" in out   # 登録名と無関係な語は置換しない
