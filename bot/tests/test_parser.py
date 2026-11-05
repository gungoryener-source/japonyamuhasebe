from datetime import date

import pytest

from parser import parse_text

D = date(2026, 11, 2)


@pytest.mark.parametrize("text,store,amount,cat,rate,kind,inv", [
    ("ローソン 540円 軽減", "ローソン", 540, "消耗品費", 8, "exp", ""),
    ("タクシー 2,300 T1234567890123", "タクシー", 2300, "旅費交通費", 10, "exp", "T1234567890123"),
    ("入金 330000 合同会社ミナト", "合同会社ミナト", 330000, "売上高", 10, "inc", ""),
    ("スタバ １，４８０円", "スタバ", 1480, "会議費", 10, "exp", ""),
    ("セブン 10% 1200", "セブン", 1200, "消耗品費", 8, "exp", ""),
])
def test_parse(text, store, amount, cat, rate, kind, inv):
    e = parse_text(text, D)
    assert e["store"] == store
    assert e["amount"] == amount
    assert e["category"] == cat
    assert e["rate"] == rate
    assert e["kind"] == kind
    assert e["invoice_no"] == inv
    assert e["date"] == "2026-11-02"


def test_no_amount():
    assert parse_text("ありがとう", D) is None
