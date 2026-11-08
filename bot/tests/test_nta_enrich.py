"""国税庁での取引先・登録番号の自動確認 (bank/review/enrich)。ネットワークは差し替え。"""
import pytest
from fastapi.testclient import TestClient

import counterparties as cpmod
import receipt_parser

BODY = "日付,摘要,出金,入金,残高\n2026-10-03,ｶ)ｻｸﾗｾｲｻｸｼﾖ,11000,,100000\n2026-10-04,ｱ)ｱｲｳｴｵ,500,,99500\n"


def good_corp():
    for n in range(10**12, 10**12 + 500):
        s = f"{n:013d}"
        if receipt_parser.check_digit_ok(s):
            return s
    raise AssertionError


@pytest.fixture()
def client(bot):
    return TestClient(bot.app)


def hdr(client, uid):
    t = client.post("/api/v1/admin/tokens", json={"user_id": uid}, headers={"X-Admin-Key": "test-admin"}).json()["token"]
    return {"Authorization": f"Bearer {t}"}


def setup(client, h, monkeypatch, found, status):
    monkeypatch.setenv("NTA_APP_ID", "x")
    client.post("/api/v1/bank/import", content=BODY.encode(), headers=h)

    async def fake_search(app_id, desc):
        return found if "ｻｸﾗ" in desc else []

    async def fake_lookup(app_id, numbers):
        return {n: {"status": status, "name": "", "registration_date": "", "end_date": ""} for n in numbers}

    monkeypatch.setattr(cpmod, "nta_search", fake_search)
    monkeypatch.setattr(cpmod, "invoice_lookup", fake_lookup)


def test_requires_app_id_and_auth(client, monkeypatch):
    monkeypatch.delenv("NTA_APP_ID", raising=False)
    h = hdr(client, "N0")
    assert client.post("/api/v1/bank/review/enrich").status_code == 401
    assert client.post("/api/v1/bank/review/enrich", headers=h).status_code == 503


def test_single_valid_match_is_saved(client, monkeypatch):
    h = hdr(client, "N1")
    n = good_corp()
    setup(client, h, monkeypatch, [{"name": "株式会社サクラ製作所", "furigana": "", "corporate_number": n, "address": ""}], "valid")
    r = client.post("/api/v1/bank/review/enrich", headers=h).json()
    assert [s["name"] for s in r["saved"]] == ["株式会社サクラ製作所"] and r["saved"][0]["registration_no"] == "T" + n
    assert r["checked"] == 2 and r["suggestions"] == []        # ｱ)ｱｲｳｴｵ は見つからず（書き込まない）
    rows = client.get("/api/v1/bank/review", headers=h).json()["rows"]
    sakura = next(x for x in rows if "ｻｸﾗ" in x["description"])
    assert sakura["counterparty"]["registration_no"] == "T" + n and sakura["counterparty"]["invoice_status"] == "valid"
    assert client.post("/api/v1/bank/review/enrich", headers=h).json()["saved"] == []     # 2回目は対象なし


@pytest.mark.parametrize("status", ["expired", "notfound"])
def test_not_valid_is_only_suggested(client, monkeypatch, status):
    h = hdr(client, "N2")
    n = good_corp()
    setup(client, h, monkeypatch, [{"name": "株式会社サクラ製作所", "furigana": "", "corporate_number": n, "address": ""}], status)
    r = client.post("/api/v1/bank/review/enrich", headers=h).json()
    assert r["saved"] == [] and r["suggestions"][0]["candidates"][0]["invoice_status"] == status
    assert client.get("/api/v1/counterparties", headers=h).json()["counterparties"] == []


def test_multiple_candidates_not_saved(client, monkeypatch):
    h = hdr(client, "N3")
    n = good_corp()
    f = [{"name": "A", "furigana": "", "corporate_number": n, "address": ""}, {"name": "B", "furigana": "", "corporate_number": n, "address": ""}]
    setup(client, h, monkeypatch, f, "valid")
    r = client.post("/api/v1/bank/review/enrich", headers=h).json()
    assert r["saved"] == [] and len(r["suggestions"][0]["candidates"]) == 2


def test_connection_error_skips(client, monkeypatch):
    h = hdr(client, "N4")
    setup(client, h, monkeypatch, [], "valid")

    async def boom(a, d):
        raise RuntimeError("down")
    monkeypatch.setattr(cpmod, "nta_search", boom)
    r = client.post("/api/v1/bank/review/enrich", headers=h).json()
    assert r["failed"] == 2 and r["saved"] == []
