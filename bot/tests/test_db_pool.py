"""T-019: PostgreSQL bağlantı havuzu + yavaş istek ölçümü."""
import logging
import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import store
import timing

PG = bool(os.environ.get("DATABASE_URL"))
pg_only = pytest.mark.skipif(not PG, reason="DATABASE_URL yok (PostgreSQL testi)")


# ---------------------------------------------------------------- havuz: SQLite yolu
def test_sqlite_path_creates_no_pool(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_PATH", str(tmp_path / "p.db"))
    store.close_pool()
    with store.tx() as con:
        con.execute("CREATE TABLE t (x INTEGER)")
        con.execute("INSERT INTO t VALUES (?)", (1,))
    with store.tx() as con:
        assert con.execute("SELECT x FROM t").fetchone()[0] == 1
    assert store._pool is None
    store.close_pool()  # havuz yokken güvenli


def test_shutdown_closes_pool(bot, monkeypatch):
    calls = []
    monkeypatch.setattr(store, "close_pool", lambda: calls.append(1))
    with TestClient(bot.app) as c:
        assert c.get("/").status_code == 200
        assert calls == []
    assert calls == [1]


def test_pool_package_pinned():
    req = open(os.path.join(os.path.dirname(store.__file__), "requirements.txt"), encoding="utf-8").read()
    assert "psycopg_pool==3.2.4" in req


# ---------------------------------------------------------------- havuz: PostgreSQL yolu
@pg_only
def test_pg_pool_reused_across_transactions(bot):
    store.close_pool()
    pids = []
    for _ in range(20):
        with store.tx() as con:
            pids.append(con.execute("SELECT pg_backend_pid() AS p").fetchone()["p"])
    pool = store._pool
    assert pool is not None and not pool.closed
    with store.tx() as con:
        con.execute("SELECT 1")
    assert store._pool is pool
    # 20 sıralı işlem → her biri yeni bağlantı değil; havuzdaki birkaç bağlantı yeniden kullanılır
    assert len(set(pids)) <= 2 < len(pids)
    assert pool.get_stats()["pool_max"] == store.POOL_MAX_SIZE


@pg_only
def test_pg_pool_commit_and_rollback(bot):
    with store.tx() as con:
        con.execute("DROP TABLE IF EXISTS pool_t")
        con.execute("CREATE TABLE pool_t (x INTEGER)")
    with pytest.raises(RuntimeError):
        with store.tx() as con:
            con.execute("INSERT INTO pool_t VALUES (?)", (1,))
            raise RuntimeError("boom")
    with store.tx() as con:
        con.execute("INSERT INTO pool_t VALUES (?)", (2,))
    with store.tx() as con:
        rows = [r["x"] for r in con.execute("SELECT x FROM pool_t ORDER BY x").fetchall()]
        con.execute("DROP TABLE pool_t")
    assert rows == [2]  # hata → rollback, bağlantı havuza temiz döner


@pg_only
def test_pg_nested_tx_does_not_deadlock(bot):
    with store.tx() as a, store.tx() as b:
        assert a.execute("SELECT 1 AS v").fetchone()["v"] == 1
        assert b.execute("SELECT 2 AS v").fetchone()["v"] == 2


@pg_only
def test_pg_close_pool_then_reopen(bot):
    with store.tx() as con:
        con.execute("SELECT 1")
    old = store._pool
    store.close_pool()
    assert old.closed and store._pool is None
    with store.tx() as con:
        assert con.execute("SELECT 1 AS v").fetchone()["v"] == 1
    assert store._pool is not None and store._pool is not old


@pg_only
def test_pg_url_change_replaces_pool(bot, monkeypatch):
    with store.tx() as con:
        con.execute("SELECT 1")
    old = store._pool
    url = os.environ["DATABASE_URL"]
    sep = "&" if "?" in url else "?"
    monkeypatch.setenv("DATABASE_URL", url + sep + "application_name=tegaru_t019")
    with store.tx() as con:
        name = con.execute("SELECT current_setting('application_name') AS n").fetchone()["n"]
    assert name == "tegaru_t019"
    assert old.closed and store._pool is not old
    store.close_pool()  # sonraki testler asıl URL ile yeni havuz açsın


@pg_only
def test_pg_schema_change_with_pooled_connection(bot):
    """Hazır ifade (prepared statement) kapalı: sütun eklense de havuzdaki bağlantı SELECT * yapabilir."""
    with store.tx() as con:
        con.execute("DROP TABLE IF EXISTS pool_s")
        con.execute("CREATE TABLE pool_s (a INTEGER)")
        con.execute("INSERT INTO pool_s VALUES (?)", (1,))
    for _ in range(8):  # psycopg varsayılan prepare_threshold=5'i aş
        with store.tx() as con:
            con.execute("SELECT * FROM pool_s").fetchall()
    with store.tx() as con:
        con.execute("ALTER TABLE pool_s ADD COLUMN b INTEGER")
    with store.tx() as con:
        row = con.execute("SELECT * FROM pool_s").fetchone()
        con.execute("DROP TABLE pool_s")
    assert row == {"a": 1, "b": None}


# ---------------------------------------------------------------- yavaş istek ölçümü
def _mini_app(threshold: float) -> FastAPI:
    app = FastAPI()
    app.add_middleware(timing.SlowRequestMiddleware, threshold=threshold)

    @app.get("/items/{item_id}")
    def item(item_id: str):
        return {"ok": True}

    return app


def test_slow_request_logs_route_template_without_personal_data(caplog):
    caplog.set_level(logging.WARNING, logger="tegaru.slow")
    c = TestClient(_mini_app(threshold=-1))  # her istek "yavaş"
    assert c.get("/items/U4af4980629secret?token=abc123&email=a@example.com").status_code == 200
    msgs = [r.getMessage() for r in caplog.records if r.name == "tegaru.slow"]
    assert len(msgs) == 1
    assert "GET /items/{item_id}" in msgs[0] and "status=200" in msgs[0]
    for secret in ("U4af4980629secret", "abc123", "a@example.com", "token"):
        assert secret not in msgs[0]
    assert caplog.records[-1].levelno == logging.WARNING


def test_fast_request_not_logged(caplog):
    caplog.set_level(logging.DEBUG, logger="tegaru.slow")
    c = TestClient(_mini_app(threshold=60))
    assert c.get("/items/x").status_code == 200
    assert [r for r in caplog.records if r.name == "tegaru.slow"] == []


def test_unmatched_path_not_logged_verbatim(caplog):
    caplog.set_level(logging.WARNING, logger="tegaru.slow")
    c = TestClient(_mini_app(threshold=-1))
    assert c.get("/U4af4980629secret/x").status_code == 404
    msg = [r.getMessage() for r in caplog.records if r.name == "tegaru.slow"][0]
    assert "(unmatched)" in msg and "status=404" in msg and "U4af" not in msg


def test_default_threshold_is_one_second():
    assert timing.SLOW_REQUEST_SECONDS == 1.0
    assert timing.SlowRequestMiddleware(lambda *a: None).threshold == 1.0


def test_main_app_has_slow_request_middleware(bot):
    assert timing.SlowRequestMiddleware in [m.cls for m in bot.app.user_middleware]


def test_main_app_logs_real_route_template(bot, caplog, monkeypatch):
    caplog.set_level(logging.WARNING, logger="tegaru.slow")
    monkeypatch.setattr(timing, "SLOW_REQUEST_SECONDS", -1)
    import importlib
    app_module = importlib.reload(bot)  # eşik middleware oluşturulurken okunur
    r = TestClient(app_module.app).get("/api/v1/entries/123/history")
    assert r.status_code in (401, 403)
    msg = [r.getMessage() for r in caplog.records if r.name == "tegaru.slow"][-1]
    assert "/api/v1/entries/{" in msg and "123" not in msg.split("status=")[0]
