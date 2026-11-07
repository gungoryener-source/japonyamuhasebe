"""T-045: 青色申告決算書（損益計算書）参考 PDF."""
import io

import pytest
from fastapi.testclient import TestClient

import reports

ADMIN = {"X-Admin-Key": "test-admin"}


@pytest.fixture()
def client(bot):
    return TestClient(bot.app)


@pytest.fixture()
def auth(client):
    r = client.post("/api/v1/admin/tokens", json={"user_id": "UR"}, headers=ADMIN)
    return {"Authorization": f"Bearer {r.json()['token']}"}


def add(client, auth, **kw):
    body = {"date": "2026-03-05", "kind": "exp", "store": "X", "amount": 1000, "category": "通信費", "rate": 10, "invoice_no": ""}
    body.update(kw)
    assert client.post("/api/v1/entries", json=body, headers=auth).status_code == 201


def test_layout_fixed_order_and_free_slots():
    rows = reports.layout_expenses({"通信費": 100, "会議費": 50, "支払手数料": 70, "雑費": 5})
    names = [n for _, n, _ in rows]
    assert names[:5] == ["租税公課", "荷造運賃", "水道光熱費", "旅費交通費", "通信費"]
    assert rows[4] == ("⑫", "通信費", 100)
    assert rows[17] == ("㉕", "支払手数料", 70)    # 任意科目は金額の大きい順
    assert rows[18] == ("㉖", "会議費", 50)
    assert rows[-1] == ("㉛", "雑費", 5)
    assert sum(a for _, _, a in rows) == 225


def test_layout_overflow_goes_to_misc():
    cats = {f"科目{i}": 10 for i in range(8)}
    rows = reports.layout_expenses(cats)
    assert sum(1 for no, n, _ in rows if no in reports.FREE_SLOTS and n) == 6
    assert rows[-1] == ("㉛", "雑費", 20)
    assert sum(a for _, _, a in rows) == 80


def test_monthly_totals():
    m = reports.monthly([{"d": "2026-01-10", "kind": "inc", "amount": 500},
                         {"d": "2026-01-11", "kind": "exp", "amount": 200},
                         {"d": "2026-12-31", "kind": "exp", "amount": 7}])
    assert m[0] == (1, 500, 200) and m[11] == (12, 0, 7) and len(m) == 12


def test_pdf_endpoint(client, auth):
    add(client, auth, kind="inc", category="売上高", amount=330000, store="合同会社ミナト")
    add(client, auth, amount=11000)
    r = client.get("/api/v1/reports/blue-return.pdf?year=2026", headers=auth)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:5] == b"%PDF-"
    from pypdf import PdfReader
    text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages)
    assert "損益計算書" in text and "330,000" in text and "319,000" in text


def test_pdf_requires_auth_and_valid_blue(client, auth):
    assert client.get("/api/v1/reports/blue-return.pdf?year=2026").status_code == 401
    assert client.get("/api/v1/reports/blue-return.pdf?year=2026&blue=123", headers=auth).status_code == 400


def test_pdf_loss_year_blue_deduction_not_negative(client, auth):
    """review: 赤字年は青色申告特別控除 0、所得金額は差引金額のまま（控除で損失を増やさない）。"""
    add(client, auth, kind="inc", category="売上高", amount=100000, store="A")
    add(client, auth, amount=250000)
    r = client.get("/api/v1/reports/blue-return.pdf?year=2026&blue=650000", headers=auth)
    assert r.status_code == 200
    from pypdf import PdfReader
    text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages)
    assert "-150,000" in text and "650,000" in text   # 選択値は表示、控除額は 0


def test_pdf_blue_clamped_to_income(client, auth):
    add(client, auth, kind="inc", category="売上高", amount=400000, store="A")
    r = client.get("/api/v1/reports/blue-return.pdf?year=2026&blue=650000", headers=auth)
    from pypdf import PdfReader
    text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages)
    assert "400,000" in text   # 控除額 = min(65万, 40万)


def test_pdf_user_isolation(client, auth):
    add(client, auth, kind="inc", category="売上高", amount=777777, store="A")
    other = client.post("/api/v1/admin/tokens", json={"user_id": "UOTHER"}, headers=ADMIN).json()["token"]
    r = client.get("/api/v1/reports/blue-return.pdf?year=2026", headers={"Authorization": f"Bearer {other}"})
    from pypdf import PdfReader
    text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages)
    assert "777,777" not in text
