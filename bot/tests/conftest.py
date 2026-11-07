import os
import sys

import pytest

BOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BOT_DIR)

os.environ.setdefault("LINE_CHANNEL_SECRET", "test-secret")
os.environ.setdefault("LINE_CHANNEL_ACCESS_TOKEN", "test-token")
os.environ.setdefault("ADMIN_KEY", "test-admin")
os.environ.setdefault("RICHMENU_AUTO", "0")  # testlerde LINE API çağrılmasın


@pytest.fixture()
def bot(tmp_path, monkeypatch):
    """Her test için boş veritabanı ve sahte LINE reply."""
    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.db"))
    if os.environ.get("DATABASE_URL"):
        # PostgreSQL ile çalışırken her testten önce tabloları sıfırla
        import store
        with store.tx() as con:
            con.execute("DROP TABLE IF EXISTS entries, api_tokens, invoices, profiles, bank_tx, accounts, account_ledgers, password_resets, subscriptions, billing_events, ledger_members, team_invites, deletion_requests, slips, counterparties, counterparty_aliases")
    import importlib
    import app as app_module
    app_module = importlib.reload(app_module)
    sent = []

    async def fake_reply(token, messages):
        sent.append(messages)

    monkeypatch.setattr(app_module, "reply", fake_reply)
    app_module.sent = sent
    return app_module


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """Hız sınırı sayaçları süreç geneli; testler birbirini etkilemesin (T-048)."""
    import ratelimit
    ratelimit.reset()
    yield
    ratelimit.reset()
