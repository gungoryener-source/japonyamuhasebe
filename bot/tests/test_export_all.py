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
    assert ents[0][:3] == ["収支区分", "管理番号", "発生日"]
    # 3 件の経費 + 入金消込で記録された売上 1 件、全年度
    assert sorted(r[2] for r in ents[1:]) == ["2024/03/01", "2025/07/15", "2026/10/05", "2026/10/20"]
    assert any(r[5] == "文具店①" for r in ents[1:])  # CP932 外の文字も欠けない
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


def test_invoices_csv_formula_injection_neutralized(client):
    """review: 取引先名が式（=,+,-,@）で始まっても invoices.csv では文字列として扱われる。"""
    a = tok(client, "UF")
    evil = '=HYPERLINK("http://example.invalid","x")'
    assert client.post("/api/v1/invoices", json={**INVOICE, "client": evil}, headers=a).status_code == 201
    assert client.post("/api/v1/invoices", json={**INVOICE, "client": "普通商事"}, headers=a).status_code == 201
    rows = csv_rows(unzip(client.get(URL, headers=a)), "invoices.csv")[1:]
    clients = sorted(r[1] for r in rows)
    assert "'" + evil in clients and "普通商事" in clients  # 通常の名前は変更されない
    assert not any(c.startswith("=") for c in clients)


@pytest.mark.parametrize("evil", ["=1+1", "+81-3", "-2+3", "@SUM(A1)", "\t=1", "\r=1",
                                  '=HYPERLINK("http://example.invalid","x")'])
def test_entries_csv_formula_injection_neutralized(client, evil):
    """T-059: ZIP entries.csv の取引先/摘要が式で始まっても ' 付きの文字列になる。金額・通常の名前は不変。"""
    a = tok(client, "UFE")
    for name in (evil, "普通商店"):
        body = {"date": "2026-10-05", "kind": "exp", "store": name, "amount": 1100, "category": "消耗品費", "rate": 10}
        assert client.post("/api/v1/entries", json=body, headers=a).status_code == 201
    rows = csv_rows(unzip(client.get(URL, headers=a)), "entries.csv")
    head, body = rows[0], rows[1:]
    stores = sorted(r[head.index("取引先")] for r in body)
    assert sorted(["'" + evil, "普通商店"]) == stores
    assert all(r[head.index("金額")] == "1100" for r in body)


@pytest.mark.parametrize("fmt", ["freee", "mf", "yayoi"])
def test_to_csv_escape_formulas(fmt):
    """T-059: escape_formulas=True で全形式の取引先/摘要・備考が無害化、金額（負数含む）は数値のまま。"""
    import export
    e = {"d": "2026-10-05", "kind": "exp", "store": "=1+1", "amount": -500, "category": "消耗品費",
         "rate": 10, "invoice_no": "@x"}
    ok = {**e, "store": "文具店", "amount": 1100, "invoice_no": "T7011001666666"}
    safe = list(csv.reader(io.StringIO(export.to_csv([e, ok], fmt, escape_formulas=True))))
    body = safe if fmt == "yayoi" else safe[1:]   # 弥生は見出し行なし（T-012b）
    cells = [c for r in body for c in r]
    assert "'=1+1" in cells and "=1+1" not in cells
    assert "-500" in cells and "1100" in cells and "文具店" in cells
    if fmt == "freee":
        assert "'@x" in cells and "T7011001666666" in cells
    # 既定（会計ソフト取込用 /export.csv）は従来どおり（Q-17）
    raw = list(csv.reader(io.StringIO(export.to_csv([e], fmt))))
    assert "=1+1" in [c for r in (raw if fmt == "yayoi" else raw[1:]) for c in r]
    assert e["store"] == "=1+1"  # 入力の dict を書き換えない


def test_csv_cell_non_string_untouched():
    import export
    assert export.csv_cell(-5) == -5 and export.csv_cell(None) is None
    assert export.csv_cell("A-1") == "A-1" and export.csv_cell("") == ""
