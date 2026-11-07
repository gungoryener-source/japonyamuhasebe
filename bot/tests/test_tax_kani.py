"""T-017: 簡易課税 みなし仕入率（docs/TAX_RULES.md §1 ✅, 国税庁 No.6505 / No.6509, 確認 2026-11-06）。

第1種 卸売 90 / 第2種 小売 80 / 第3種 製造・建設 70 / 第4種 その他 60 /
第5種 サービス等 50 / 第6種 不動産 40 (%)。
"""
import re
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tax.consumption import KANI_RATIO, Purchase, Sale, compute

TAX_TS = Path(__file__).resolve().parents[2] / "dashboard-next" / "app" / "lib" / "tax.ts"

EXPECTED = {1: 90, 2: 80, 3: 70, 4: 60, 5: 50, 6: 40}


def test_ratio_table_matches_tax_rules():
    assert KANI_RATIO == EXPECTED


def test_ratio_table_matches_dashboard():
    """パネルの消費税カード（tax.ts）も同じ率を使う。"""
    src = TAX_TS.read_text(encoding="utf-8")
    m = re.search(r"KANI_RATIO[^=]*=\s*\{([^}]*)\}", src)
    assert m, "KANI_RATIO not found in tax.ts"
    ts = {int(k): int(v) for k, v in re.findall(r"(\d+)\s*:\s*(\d+)", m.group(1))}
    assert ts == EXPECTED


@pytest.mark.parametrize("kani_type,ratio", sorted(EXPECTED.items()))
def test_each_type_deemed_input(kani_type, ratio):
    # 税込 11,000,000（10%）→ 売上税額 1,000,000
    r = compute([Sale(11_000_000, 10)], method="kani", kani_type=kani_type)
    assert r.output_tax == 1_000_000
    assert r.input_tax == 1_000_000 * ratio // 100
    assert r.payable == 1_000_000 * (100 - ratio) // 100
    assert r.method == "kani"


@pytest.mark.parametrize("kani_type,payable", [(1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0)])
def test_small_output_floors_to_zero(kani_type, payable):
    # 税込 1,100 → 売上税額 100; 差引は 100円未満切捨て
    r = compute([Sale(1_100, 10)], method="kani", kani_type=kani_type)
    assert r.output_tax == 100
    assert r.payable == payable


@pytest.mark.parametrize("kani_type", list(EXPECTED))
def test_deemed_input_is_floored(kani_type):
    # 売上税額 999 → みなし仕入税額は円未満切捨て
    r = compute([Sale(10_989, 10)], method="kani", kani_type=kani_type)
    assert r.output_tax == 999
    assert r.input_tax == 999 * EXPECTED[kani_type] // 100
    assert r.payable == ((999 - r.input_tax) // 100) * 100


def test_mixed_rates_use_total_output():
    # 10%: 税込 1,100,000 → 100,000 / 8%: 税込 1,080,000 → 80,000 → 合計 180,000
    r = compute([Sale(1_100_000, 10), Sale(1_080_000, 8)], method="kani", kani_type=2)
    assert r.output_tax == 180_000
    assert r.input_tax == 144_000
    assert r.payable == 36_000


def test_purchases_are_ignored():
    sales = [Sale(11_000_000, 10)]
    big = [Purchase(5_500_000, 10, date(2026, 6, 1), True)]
    assert compute(sales, big, "kani", kani_type=3) == compute(sales, (), "kani", kani_type=3)


def test_zero_sales():
    r = compute([], method="kani", kani_type=1)
    assert (r.output_tax, r.input_tax, r.payable) == (0, 0, 0)


@pytest.mark.parametrize("bad", [0, 7, -1, None, "5", 5.5])
def test_invalid_type_rejected(bad):
    with pytest.raises(ValueError):
        compute([Sale(1_100, 10)], method="kani", kani_type=bad)  # type: ignore[arg-type]


# ---------------------------------------------------------------- API
ADMIN = {"X-Admin-Key": "test-admin"}


@pytest.fixture()
def client(bot):
    return TestClient(bot.app)


@pytest.fixture()
def auth(client):
    r = client.post("/api/v1/admin/tokens", json={"user_id": "UKANI"}, headers=ADMIN)
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_api_kani(client, auth):
    body = {"date": "2026-05-10", "kind": "inc", "store": "A社", "amount": 2_200_000,
            "category": "売上高", "rate": 10, "invoice_no": ""}
    assert client.post("/api/v1/entries", json=body, headers=auth).status_code == 201
    exp = {"date": "2026-05-12", "kind": "exp", "store": "B商店", "amount": 1_100_000,
           "category": "消耗品費", "rate": 10, "invoice_no": "T7011001666666"}
    assert client.post("/api/v1/entries", json=exp, headers=auth).status_code == 201
    q = lambda p: client.get("/api/v1/tax/consumption?year=2026&method=kani" + p, headers=auth)  # noqa: E731
    r = q("&kani_type=5").json()
    assert r["output_tax"] == 200_000 and r["input_tax"] == 100_000 and r["payable"] == 100_000
    r = q("&kani_type=6").json()
    assert r["input_tax"] == 80_000 and r["payable"] == 120_000
    assert q("&kani_type=7").status_code == 400
    assert q("").status_code == 400
