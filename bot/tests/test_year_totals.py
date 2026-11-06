"""T-027: 年次集計（消費税・損益・CSV）が 5000 件を超えても欠けないこと。"""
import csv
import io

import pytest
from fastapi.testclient import TestClient

ADMIN = {"X-Admin-Key": "test-admin"}
N = 5001


def bulk_insert(user_id: str, rows: list[tuple]) -> None:
    import store
    with store.tx() as con:
        for d, kind, amount, category, rate in rows:
            con.execute(
                """INSERT INTO entries(user_id,d,kind,store,amount,category,rate,invoice_no,source,image_path,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (user_id, d, kind, "テスト商店", amount, category, rate, "T7011001666666", "WEB", "",
                 "2026-01-01T00:00:00+09:00"),
            )


@pytest.fixture()
def big(bot):
    client = TestClient(bot.app)
    r = client.post("/api/v1/admin/tokens", json={"user_id": "UBIG"}, headers=ADMIN)
    auth = {"Authorization": f"Bearer {r.json()['token']}"}
    # 2025-01-01 から 1 日 ~14 件、全件 1,100 円の経費（10%）＋ 売上 1 件
    rows = [(f"2025-{1 + i // 420:02d}-{1 + (i % 420) // 15:02d}", "exp", 1100, "消耗品費", 10) for i in range(N)]
    rows.append(("2025-12-31", "inc", 11_000_000, "売上高", 10))
    rows.append(("2024-12-31", "exp", 999_999, "消耗品費", 10))  # 範囲外
    rows.append(("2026-01-01", "exp", 999_999, "消耗品費", 10))  # 範囲外
    bulk_insert("UBIG", rows)
    bulk_insert("OTHER", [("2025-06-01", "exp", 5_000, "消耗品費", 10)])  # 他テナント
    return client, auth


def test_entries_in_range_pages_without_gaps(bot):
    import store
    rows = [("2025-03-01", "exp", i + 1, "消耗品費", 10) for i in range(7)]  # 同日複数で id 順
    rows += [("2025-03-02", "exp", 100 + i, "消耗品費", 8) for i in range(5)]
    bulk_insert("UP", rows)
    for size in (1, 2, 3, 5, 12, 13, 2000):
        got = store.entries_in_range("UP", "2025-01-01", "2025-12-31", page_size=size)
        assert [r["amount"] for r in got] == [r[2] for r in rows], size
    assert store.entries_in_range("UP", "2026-01-01", "2026-12-31") == []


def test_pl_counts_all_rows(big):
    client, auth = big
    r = client.get("/api/v1/pl?year=2025", headers=auth)
    assert r.status_code == 200
    j = r.json()
    assert j["revenue"] == 11_000_000
    assert j["expenses_total"] == N * 1100


def test_consumption_tax_counts_all_rows(big):
    client, auth = big
    r = client.get("/api/v1/tax/consumption?year=2025", headers=auth)
    assert r.status_code == 200
    j = r.json()
    # 1,100 円（10% 税込）× 5001 件 → 仕入税額 100 円 × 5001。5000 件で切れると 100 円少ない
    assert j["input_tax"] == N * 100
    assert j["output_tax"] == 1_000_000


def test_export_csv_has_all_rows(big):
    client, auth = big
    r = client.get("/api/v1/export.csv?format=freee&year=2025", headers=auth)
    assert r.status_code == 200
    lines = list(csv.reader(io.StringIO(r.content.decode("cp932"))))
    assert len(lines) - 1 == N + 1  # ヘッダー + 経費 5001 + 売上 1


def test_admin_entries_returns_all_rows(big, bot):
    client, _ = big
    r = client.get("/entries/UBIG?year=2025", headers=ADMIN)
    assert r.status_code == 200
    assert len(r.json()) == N + 1
