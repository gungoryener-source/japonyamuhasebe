"""T-078: GET /admin/config-check — yalnızca var/yok, değer asla sızmaz."""
from fastapi.testclient import TestClient

import config_check

H = {"X-Admin-Key": "test-admin"}

# Ayırt edilebilir sahte değerler: yanıt gövdesinde hiçbiri (ya da parçası) geçmemeli
FAKE = {
    "LINE_CHANNEL_SECRET": "fakeSECRETline0123456789abcdefXY",
    "LINE_CHANNEL_ACCESS_TOKEN": "fakeTOKENlineQWERTYzxcv",
    # yalnızca is_pg() etiketine bakılır; bağlantı kurulmaz
    "DATABASE_URL": "postgres://fakeuser:fakePGpass99@fake-db-host.example.test/tegaru",
    "PANEL_URL": "https://fake-panel-zz9.example.test",
    "STORAGE_ENDPOINT": "https://fakeacct77.r2.example.test",
    "STORAGE_BUCKET": "fakebucket-qq1",
    "STORAGE_ACCESS_KEY": "fakeACCESSkeyR2abc",
    "STORAGE_SECRET_KEY": "fakeSECRETkeyR2xyz",
    "MAIL_PROVIDER": "resend",
    "MAIL_API_KEY": "re_fakeMAILkey556",
    "MAIL_FROM": "Fake <no-reply@fake-mail-qq.example.test>",
    "STRIPE_SECRET_KEY": "sk_test_fakeSTRIPEkey889",
    "STRIPE_WEBHOOK_SECRET": "whsec_fakeHOOK123",
    "STRIPE_PRICE_PERSONAL": "price_fakePERSONAL",
    "STRIPE_PRICE_BUSINESS": "price_fakeBUSINESS",
    "ANTHROPIC_API_KEY": "sk-ant-fakeANTHROPIC000",
    "NTA_APP_ID": "fakeNTAappid42",
    "NTA_INVOICE_APP_ID": "",
    "WHATSAPP_VERIFY_TOKEN": "fakeWAverify",
    "WHATSAPP_APP_SECRET": "",
    "WHATSAPP_TOKEN": "",
    "WHATSAPP_PHONE_ID": "",
}


def _setenv(monkeypatch, values):
    for k, v in values.items():
        if v:
            monkeypatch.setenv(k, v)
        else:
            monkeypatch.delenv(k, raising=False)


def test_requires_admin_key(bot):
    c = TestClient(bot.app)
    assert c.get("/admin/config-check").status_code == 401
    assert c.get("/admin/config-check", headers={"X-Admin-Key": ""}).status_code == 401
    assert c.get("/admin/config-check", headers={"X-Admin-Key": "wrong"}).status_code == 401


def test_query_key_not_accepted(bot):
    r = TestClient(bot.app).get("/admin/config-check", params={"key": "test-admin"})
    assert r.status_code == 401


def test_no_admin_key_configured(bot, monkeypatch):
    monkeypatch.setattr(bot, "ADMIN_KEY", "")
    r = TestClient(bot.app).get("/admin/config-check", headers={"X-Admin-Key": ""})
    assert r.status_code == 401


def test_all_required_set_no_values_leak(bot, monkeypatch):
    _setenv(monkeypatch, FAKE)
    r = TestClient(bot.app).get("/admin/config-check", headers=H)
    assert r.status_code == 200
    assert r.headers["cache-control"] == "no-store"
    body = r.text
    for name, value in FAKE.items():
        if not value or name == "MAIL_PROVIDER":
            continue
        assert value not in body, name
        # önek/parça da sızmamalı (ilk 8 karakter; DATABASE_URL'nin şeması "postgres" etiketiyle aynı)
        if name != "DATABASE_URL":
            assert value[:8] not in body, name
    for part in ("fakeuser", "fakePGpass99", "fake-db-host"):
        assert part not in body
    assert "test-admin" not in body  # ADMIN_KEY değeri
    j = r.json()
    assert j["ready"] is True and j["missing_required"] == [] and j["open_questions"] == []
    by = {e["name"]: e for e in j["env"]}
    assert by["LINE_CHANNEL_SECRET"] == {"name": "LINE_CHANNEL_SECRET", "set": True, "question": "Q-01",
                                         "level": "required"}
    assert by["NTA_INVOICE_APP_ID"]["set"] is False and by["WHATSAPP_TOKEN"]["set"] is False
    assert j["runtime"]["db"] == "postgres"
    assert j["runtime"]["storage"] == "s3"
    assert j["runtime"]["mail_provider_supported"] is True
    assert isinstance(j["runtime"]["tesseract"], bool)


def test_only_bool_and_labels_in_env_entries(bot, monkeypatch):
    _setenv(monkeypatch, FAKE)
    j = TestClient(bot.app).get("/admin/config-check", headers=H).json()
    for e in j["env"]:
        assert set(e) == {"name", "set", "question", "level"}
        assert isinstance(e["set"], bool)
        assert e["level"] in ("required", "recommended", "optional")
    assert set(j["runtime"]) == {"db", "storage", "tesseract", "mail_provider_supported"}


def test_missing_required_reported_with_questions(bot, monkeypatch):
    vals = dict(FAKE)
    for k in ("STORAGE_SECRET_KEY", "MAIL_API_KEY", "STRIPE_WEBHOOK_SECRET"):
        vals[k] = ""
    vals["ANTHROPIC_API_KEY"] = ""  # recommended → ready'yi etkilemez
    _setenv(monkeypatch, vals)
    j = TestClient(bot.app).get("/admin/config-check", headers=H).json()
    assert j["ready"] is False
    assert j["missing_required"] == ["STORAGE_SECRET_KEY", "MAIL_API_KEY", "STRIPE_WEBHOOK_SECRET"]
    assert j["open_questions"] == ["Q-10", "Q-13", "Q-14"]
    assert j["runtime"]["storage"] == "local"  # S3 değişkeni eksik → yerel disk


def test_sqlite_label_without_database_url(bot, monkeypatch):
    _setenv(monkeypatch, {**FAKE, "DATABASE_URL": ""})
    j = TestClient(bot.app).get("/admin/config-check", headers=H).json()
    assert j["runtime"]["db"] == "sqlite"
    assert j["missing_required"] == ["DATABASE_URL"] and j["open_questions"] == ["Q-07"]


def test_whitespace_counts_as_unset(bot, monkeypatch):
    _setenv(monkeypatch, FAKE)
    monkeypatch.setenv("LINE_CHANNEL_SECRET", "   ")
    j = TestClient(bot.app).get("/admin/config-check", headers=H).json()
    assert "LINE_CHANNEL_SECRET" in j["missing_required"] and "Q-01" in j["open_questions"]


def test_unsupported_mail_provider_flag_has_no_value(bot, monkeypatch):
    _setenv(monkeypatch, FAKE)
    monkeypatch.setenv("MAIL_PROVIDER", "fakeprovZZ")
    r = TestClient(bot.app).get("/admin/config-check", headers=H)
    assert "fakeprovZZ" not in r.text
    assert r.json()["runtime"]["mail_provider_supported"] is False


def test_vars_cover_render_yaml_bot_secrets():
    """render.yaml'daki tegaru-line-bot `sync: false` / generateValue değişkenleri listede olmalı."""
    import os
    import re
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    text = open(os.path.join(root, "render.yaml"), encoding="utf-8").read()
    bot_part = text.split("name: jsaas-panel")[0]
    keys = re.findall(r"- key: ([A-Z_0-9]+)\s*(?:#.*)?\n\s+(?:sync: false|generateValue: true)", bot_part)
    names = {n for n, _, _ in config_check.VARS}
    assert keys and set(keys) <= names, set(keys) - names


def test_health_and_callback_contract_unchanged(bot):
    c = TestClient(bot.app)
    h = c.get("/")
    assert h.status_code == 200 and h.json()["ok"] is True
    assert c.post("/callback", content=b"{}", headers={"X-Line-Signature": "bad"}).status_code == 400
