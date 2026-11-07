"""T-046: 全データ ZIP — 認証、テナント分離、閲覧メンバー、ファイル一覧と件数（>5000 件）。"""
import csv
import io
import zipfile

import pytest
from fastapi.testclient import TestClient

ADMIN = {"X-Admin-Key": "test-admin"}
URL = "/api/v1/export/all.zip"
INVOICE = {"client": "株式会社テスト", "issued": "2026-10-01", "due": "2026-10-31",
           "items": [{"name": "制作費", "qty": 1, "unit_price": 10000, "rate": 10}]}


@pytest.fixture()
def client(bot):
    return TestClient(bot.app)


def tok(client, uid):
    r = client.post("/api/v1/admin/tokens", json={"user_id": uid}, headers=ADMIN)
    return {"Authorization": f"Bearer {r.json()['token']}"}


def unzip(resp) -> zipfile.ZipFile:
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/zip"
    assert "attachment" in resp.headers["content-disposition"]
    return zipfile.ZipFile(io.BytesIO(resp.content))


def csv_rows(z, name):
    raw = z.read(name)
    assert raw.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM
    return list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))


def test_requires_token(client):
    assert client.get(URL).status_code == 401
    assert client.get(URL, headers={"Authorization": "Bearer nope"}).status_code == 401


def test_empty_ledger(client):
    z = unzip(client.get(URL, headers=tok(client, "UE")))
    assert sorted(z.namelist()) == ["README.txt", "entries.csv", "invoices.csv"]
    assert len(csv_rows(z, "entries.csv")) == 1 and len(csv_rows(z, "invoices.csv")) == 1
    assert "仕訳 0 件" in z.read("README.txt").decode("utf-8-sig")


def test_contents_all_years_and_invoices(client):
    a = tok(client, "U1")
    for d in ("2024-03-01", "2025-07-15", "2026-10-05"):
        body = {"date": d, "kind": "exp", "store": "文具店①", "amount": 1100, "category": "消耗品費", "rate": 10}
        assert client.post("/api/v1/entries", json=body, headers=a).status_code == 201
    no1 = client.post("/api/v1/invoices", json=INVOICE, headers=a).json()["no"]
    no2 = client.post("/api/v1/invoices", json={**INVOICE, "client": "B社"}, headers=a).json()["no"]
    assert client.post(f"/api/v1/invoices/{no1}/paid?paid_on=2026-10-20", headers=a).status_code == 200

    z = unzip(client.get(URL, headers=a))
    assert sorted(z.namelist()) == sorted(["README.txt", "entries.csv", "invoices.csv",
                                           f"invoices/{no1}.pdf", f"invoices/{no2}.pdf"])
    ents = csv_rows(z, "entries.csv")
    assert ents[0][:2] == ["収支区分", "発生日"]
    # 3 件の経費 + 入金消込で記録された売上 1 件、全年度
    assert sorted(r[1] for r in ents[1:]) == ["2024-03-01", "2025-07-15", "2026-10-05", "2026-10-20"]
    assert any(r[2] == "文具店①" for r in ents[1:])  # CP932 外の文字も欠けない
    invs = csv_rows(z, "invoices.csv")
    assert len(invs) == 3
    by_no = {r[0]: r for r in invs[1:]}
    assert by_no[no1][9] == "入金済" and by_no[no1][10] == "2026-10-20"
    assert by_no[no2][9] == "未入金" and by_no[no2][8] == "11000"
    assert z.read(f"invoices/{no1}.pdf").startswith(b"%PDF")


def test_other_tenant_isolated(client):
    a, b = tok(client, "UA"), tok(client, "UB")
    client.post("/api/v1/entries", json={"date": "2026-10-05", "kind": "exp", "store": "A専用", "amount": 500,
                                        "category": "雑費", "rate": 10}, headers=a)
    client.post("/api/v1/invoices", json=INVOICE, headers=a)
    z = unzip(client.get(URL, headers=b))
    assert len(csv_rows(z, "entries.csv")) == 1 and len(csv_rows(z, "invoices.csv")) == 1
    assert not [n for n in z.namelist() if n.startswith("invoices/")]


def test_viewer_can_download(client):
    pw = "correct-horse-1"
    owner = client.post("/api/v1/auth/signup", json={"email": "o@example.jp", "password": pw}).json()
    view = client.post("/api/v1/auth/signup", json={"email": "v@example.jp", "password": pw}).json()
    H = lambda t: {"Authorization": f"Bearer {t}"}  # noqa: E731
    code = client.post("/api/v1/team/invites", headers=H(owner["token"]), json={"role": "viewer"}).json()["code"]
    vt = client.post("/api/v1/team/join", headers=H(view["token"]), json={"code": code}).json()["token"]
    client.post("/api/v1/entries", headers=H(owner["token"]),
                json={"date": "2026-10-05", "kind": "exp", "store": "コンビニ", "amount": 1100, "category": "消耗品費", "rate": 10})
    z = unzip(client.get(URL, headers=H(vt)))
    assert len(csv_rows(z, "entries.csv")) == 2


def test_more_than_5000_entries(client):
    from test_year_totals import bulk_insert
    rows = [(f"{2024 + i % 3}-{1 + i % 12:02d}-{1 + i % 28:02d}", "exp", 1100, "消耗品費", 10) for i in range(5003)]
    bulk_insert("UBIG", rows)
    bulk_insert("OTHER", [("2025-06-01", "exp", 5_000, "消耗品費", 10)])
    z = unzip(client.get(URL, headers=tok(client, "UBIG")))
    assert len(csv_rows(z, "entries.csv")) == 5003 + 1
    assert "仕訳 5003 件" in z.read("README.txt").decode("utf-8-sig")


@pytest.mark.parametrize("no,expected", [
    ("INV-2026-0001", "invoices/INV-2026-0001.pdf"),
    ("../../etc/passwd", "invoices/_.._etc_passwd.pdf"),
    ("..", "invoices/invoice.pdf"),
    ("請求/1", "invoices/___1.pdf"),
])
def test_pdf_name_is_safe(no, expected):
    import archive
    name = archive.pdf_name(no)
    assert name == expected
    assert "/" not in name.removeprefix("invoices/") and not name.removeprefix("invoices/").startswith(".")
