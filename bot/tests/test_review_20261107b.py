"""reviewer 2026-11-07 (akşam): T-049 / T-064 / T-060 / AI okuma ayarı için eksik sınır testleri."""
import pytest
from fastapi.testclient import TestClient

import companies
import slips
import store

ADMIN = {"X-Admin-Key": "test-admin"}


@pytest.fixture()
def client(bot):
    return TestClient(bot.app)


@pytest.fixture()
def auth(client):
    r = client.post("/api/v1/admin/tokens", json={"user_id": "Urev"}, headers=ADMIN)
    return {"Authorization": f"Bearer {r.json()['token']}"}


# ---------------------------------------------------------------- T-049: /tax/income 青色控除 yıl sınırı (API)
def test_income_api_blue_options_by_year(client, auth):
    ok27 = client.get("/api/v1/tax/income?year=2027&blue=750000", headers=auth)
    assert ok27.status_code == 200 and ok27.json()["blue_deduction"] == 0   # 所得 0 → 控除も 0
    assert client.get("/api/v1/tax/income?year=2027&blue=550000", headers=auth).status_code == 400   # 55万 廃止
    assert client.get("/api/v1/tax/income?year=2026&blue=550000", headers=auth).status_code == 200
    assert client.get("/api/v1/tax/income?year=2026&blue=750000", headers=auth).status_code == 400   # 75万 は 令和9年分から


# ---------------------------------------------------------------- T-064: LINE 記録先は所有中の帳簿だけ
def test_line_target_ignores_foreign_or_stale_selection(bot):
    # line_targets に他人の帳簿が入っていても（改ざん・所有解除後）LINE 自身の帳簿に戻る
    with store.tx() as con:
        con.execute("INSERT INTO line_targets(line_user_id,ledger_user_id,updated_at) VALUES(?,?,?)",
                    ("Ufree", "web:someone-else", store.now()))
    assert companies.line_target("Ufree") == "Ufree"
    with pytest.raises(companies.CompanyError):
        companies.set_line_target("Ufree", "web:someone-else")


def test_company_name_length_limit(bot):
    with pytest.raises(companies.CompanyError):
        companies.create(1, "あ" * 101)
    with pytest.raises(companies.CompanyError) as ex:
        companies.create(0, "名前")
    assert ex.value.code == 403


# ---------------------------------------------------------------- T-060: 処理済みの仕切書は変更不可
def test_slip_update_and_reject_only_when_pending(bot):
    s = slips.create("U1", {})
    slips.reject("U1", s["id"])
    with pytest.raises(ValueError):
        slips.update("U1", s["id"], {"issuer": "改ざん"})
    with pytest.raises(ValueError):
        slips.reject("U1", s["id"])
    with pytest.raises(ValueError):
        slips.approve("U1", s["id"])
    with pytest.raises(KeyError):
        slips.update("U2", s["id"], {"issuer": "他人"})          # 他の帳簿からは見えない
    assert slips.get("U1", s["id"])["issuer"] == ""


def test_slip_update_rejects_bad_kind(bot):
    s = slips.create("U1", {})
    with pytest.raises(ValueError):
        slips.update("U1", s["id"], {"kind": "xxx"})


# ---------------------------------------------------------------- AI 読み取り設定: 言語設定を壊さない
def test_receipt_reader_keeps_language(bot):
    store.set_lang("Ulang", "tr")
    assert store.set_receipt_reader("Ulang", "ai") == "ai"
    assert store.get_lang("Ulang") == "tr"
    assert store.get_receipt_reader("Ulang") == "ai"
    with pytest.raises(ValueError):
        store.set_receipt_reader("Ulang", "gpt")
    assert store.get_receipt_reader("Unobody") == ""
