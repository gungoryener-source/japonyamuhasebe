"""T-053: eşzamanlı aynı e-postayla kayıt → UNIQUE ihlali 500 değil 409 olmalı."""
import sqlite3

import pytest
from fastapi.testclient import TestClient

PW = "correct-horse-1"


class _Empty:
    def fetchone(self):
        return None


def _skip_first_email_check(monkeypatch, store):
    """signup'ın ön SELECT kontrolünü bir kez boş döndür: rakip istek araya girmiş gibi."""
    real = store._Conn.execute
    state = {"skipped": False}

    def fake(self, sql, args=()):
        if not state["skipped"] and sql.startswith("SELECT 1 FROM accounts WHERE email"):
            state["skipped"] = True
            return _Empty()
        return real(self, sql, args)

    monkeypatch.setattr(store._Conn, "execute", fake)
    return state


def test_signup_race_returns_409(bot, monkeypatch):
    import store
    client = TestClient(bot.app)
    first = client.post("/api/v1/auth/signup", json={"email": "race@example.jp", "password": PW})
    assert first.status_code in (200, 201)
    state = _skip_first_email_check(monkeypatch, store)

    r = client.post("/api/v1/auth/signup", json={"email": "Race@Example.jp", "password": PW})
    assert state["skipped"]
    assert r.status_code == 409
    assert "すでに登録" in r.json()["detail"]
    # işlem geri alındı: tek hesap, tek defter bağlantısı; ilk hesap hâlâ giriş yapabiliyor
    with store.tx() as con:
        assert con.execute("SELECT COUNT(*) AS n FROM accounts").fetchone()["n"] == 1
        assert con.execute("SELECT COUNT(*) AS n FROM account_ledgers").fetchone()["n"] == 1
    login = client.post("/api/v1/auth/login", json={"email": "race@example.jp", "password": PW})
    assert login.status_code == 200


def test_signup_race_direct_raises_account_error(bot, monkeypatch):
    import accounts
    import store
    accounts.signup("dup@example.jp", PW)
    _skip_first_email_check(monkeypatch, store)
    with pytest.raises(accounts.AccountError) as ei:
        accounts.signup("dup@example.jp", PW)
    assert ei.value.code == 409


def test_other_integrity_error_is_not_masked(bot, monkeypatch):
    """E-posta kayıtlı değilse bütünlük hatası 409'a çevrilmez (gerçek hata gizlenmez)."""
    import accounts
    import store
    real = store._Conn.execute

    def fake(self, sql, args=()):
        if sql.startswith("INSERT INTO accounts"):
            raise sqlite3.IntegrityError("simulated")
        return real(self, sql, args)

    monkeypatch.setattr(store._Conn, "execute", fake)
    with pytest.raises(sqlite3.IntegrityError):
        accounts.signup("new@example.jp", PW)


def test_is_integrity_error():
    import store
    assert store.is_integrity_error(sqlite3.IntegrityError("x"))
    assert not store.is_integrity_error(ValueError("x"))
    psycopg = pytest.importorskip("psycopg")
    assert store.is_integrity_error(psycopg.errors.UniqueViolation("x"))
