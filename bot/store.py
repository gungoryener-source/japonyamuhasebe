"""Veri katmanı (SQLite). Tüm kanallar (LINE, WhatsApp, web API) buradan okur/yazar.

Defter anahtarı `user_id`: LINE userId, `wa:<telefon>` (WhatsApp) veya web'den açılan defterler.
Şema yalnızca ekleyici (additive) değişir — CLAUDE.md "veri silme yok".
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
from contextlib import closing
from datetime import date, datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS entries(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        d TEXT NOT NULL,
        kind TEXT NOT NULL CHECK(kind IN ('inc','exp')),
        store TEXT NOT NULL,
        amount INTEGER NOT NULL,
        category TEXT NOT NULL,
        rate INTEGER NOT NULL,
        invoice_no TEXT DEFAULT '',
        source TEXT DEFAULT 'LINE',
        image_path TEXT DEFAULT '',
        created_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS ix_user_d ON entries(user_id, d)",
    """CREATE TABLE IF NOT EXISTS api_tokens(
        token_hash TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        label TEXT DEFAULT '',
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS invoices(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        no TEXT NOT NULL,
        client TEXT NOT NULL,
        issued TEXT NOT NULL,
        due TEXT NOT NULL,
        items_json TEXT NOT NULL,
        subtotal10 INTEGER NOT NULL DEFAULT 0,
        subtotal8 INTEGER NOT NULL DEFAULT 0,
        tax10 INTEGER NOT NULL DEFAULT 0,
        tax8 INTEGER NOT NULL DEFAULT 0,
        total INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'unpaid',
        paid_on TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        UNIQUE(user_id, no)
    )""",
    """CREATE TABLE IF NOT EXISTS profiles(
        user_id TEXT PRIMARY KEY,
        business_name TEXT DEFAULT '',
        registration_no TEXT DEFAULT '',
        individual INTEGER DEFAULT 1,
        updated_at TEXT NOT NULL
    )""",
]


def db_path() -> str:
    return os.environ.get("DB_PATH", "tegaru.db")


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(db_path())
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    with closing(connect()) as con, con:
        for stmt in SCHEMA:
            con.execute(stmt)


def now() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def today() -> date:
    return datetime.now(JST).date()


# ---------------------------------------------------------------- entries
def add_entry(user_id: str, e: dict, image_path: str = "", source: str = "LINE") -> int:
    with closing(connect()) as con, con:
        cur = con.execute(
            """INSERT INTO entries(user_id,d,kind,store,amount,category,rate,invoice_no,source,image_path,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id, e["date"], e["kind"], e["store"], int(e["amount"]), e["category"],
             int(e["rate"]), e.get("invoice_no", ""), source, image_path, now()),
        )
        return int(cur.lastrowid)


def last_entry(user_id: str) -> dict | None:
    with closing(connect()) as con:
        row = con.execute("SELECT * FROM entries WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
    return dict(row) if row else None


def update_entry(user_id: str, entry_id: int, **fields) -> dict | None:
    allowed = {"category", "rate", "store", "amount", "d", "invoice_no", "kind"}
    sets = {k: v for k, v in fields.items() if k in allowed}
    if not sets:
        return None
    cols = ", ".join(f"{k}=?" for k in sets)
    with closing(connect()) as con, con:
        con.execute(f"UPDATE entries SET {cols} WHERE id=? AND user_id=?", (*sets.values(), entry_id, user_id))
        row = con.execute("SELECT * FROM entries WHERE id=? AND user_id=?", (entry_id, user_id)).fetchone()
    return dict(row) if row else None


def undo_last(user_id: str) -> dict | None:
    with closing(connect()) as con, con:
        row = con.execute("SELECT * FROM entries WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
        if row:
            con.execute("DELETE FROM entries WHERE id=?", (row["id"],))
    return dict(row) if row else None


def month_summary(user_id: str, ym: str | None = None) -> tuple[int, int]:
    ym = ym or datetime.now(JST).strftime("%Y-%m")
    with closing(connect()) as con:
        r = con.execute(
            """SELECT COALESCE(SUM(CASE WHEN kind='inc' THEN amount END),0) inc,
                      COALESCE(SUM(CASE WHEN kind='exp' THEN amount END),0) exp
               FROM entries WHERE user_id=? AND substr(d,1,7)=?""",
            (user_id, ym),
        ).fetchone()
    return int(r["inc"]), int(r["exp"])


def search_entries(user_id: str, *, date_from: str | None = None, date_to: str | None = None,
                   q: str | None = None, amount_min: int | None = None, amount_max: int | None = None,
                   kind: str | None = None, limit: int = 500) -> list[dict]:
    """電子帳簿保存法の検索要件（取引年月日・金額・取引先）を満たす検索。"""
    sql = "SELECT * FROM entries WHERE user_id=?"
    args: list = [user_id]
    if date_from:
        sql += " AND d>=?"; args.append(date_from)
    if date_to:
        sql += " AND d<=?"; args.append(date_to)
    if q:
        sql += " AND store LIKE ? ESCAPE '\\'"
        args.append("%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%")
    if amount_min is not None:
        sql += " AND amount>=?"; args.append(amount_min)
    if amount_max is not None:
        sql += " AND amount<=?"; args.append(amount_max)
    if kind in ("inc", "exp"):
        sql += " AND kind=?"; args.append(kind)
    sql += " ORDER BY d, id LIMIT ?"
    args.append(max(1, min(limit, 5000)))
    with closing(connect()) as con:
        return [dict(r) for r in con.execute(sql, args).fetchall()]


# ---------------------------------------------------------------- tokens
def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


MAX_TOKENS_PER_USER = 5


def issue_token(user_id: str, label: str = "") -> str:
    """Yeni token üretir; kullanıcı başına en fazla MAX_TOKENS_PER_USER (en eskiler iptal edilir)."""
    token = "tk_" + secrets.token_urlsafe(24)
    with closing(connect()) as con, con:
        con.execute("INSERT INTO api_tokens(token_hash,user_id,label,created_at) VALUES(?,?,?,?)",
                    (_hash(token), user_id, label, now()))
        con.execute(
            """DELETE FROM api_tokens WHERE user_id=? AND token_hash NOT IN (
                   SELECT token_hash FROM api_tokens WHERE user_id=? ORDER BY created_at DESC, rowid DESC LIMIT ?)""",
            (user_id, user_id, MAX_TOKENS_PER_USER),
        )
    return token


def revoke_token(token: str) -> bool:
    with closing(connect()) as con, con:
        cur = con.execute("DELETE FROM api_tokens WHERE token_hash=?", (_hash(token),))
    return cur.rowcount > 0


def user_for_token(token: str) -> str | None:
    if not token:
        return None
    with closing(connect()) as con:
        row = con.execute("SELECT user_id FROM api_tokens WHERE token_hash=?", (_hash(token),)).fetchone()
    return row["user_id"] if row else None


# ---------------------------------------------------------------- profiles
def get_profile(user_id: str) -> dict:
    with closing(connect()) as con:
        row = con.execute("SELECT * FROM profiles WHERE user_id=?", (user_id,)).fetchone()
    return dict(row) if row else {"user_id": user_id, "business_name": "", "registration_no": "", "individual": 1}


def save_profile(user_id: str, **fields) -> dict:
    p = get_profile(user_id)
    p.update({k: v for k, v in fields.items() if k in ("business_name", "registration_no", "individual")})
    with closing(connect()) as con, con:
        con.execute(
            """INSERT INTO profiles(user_id,business_name,registration_no,individual,updated_at) VALUES(?,?,?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET business_name=excluded.business_name,
               registration_no=excluded.registration_no, individual=excluded.individual, updated_at=excluded.updated_at""",
            (user_id, p["business_name"], p["registration_no"], int(p["individual"]), now()),
        )
    return get_profile(user_id)


# ---------------------------------------------------------------- invoices
def next_invoice_no(user_id: str, issued: str) -> str:
    prefix = f"INV-{issued[:4]}-"
    with closing(connect()) as con:
        row = con.execute("SELECT no FROM invoices WHERE user_id=? AND no LIKE ? ORDER BY no DESC LIMIT 1",
                          (user_id, prefix + "%")).fetchone()
    n = int(row["no"].rsplit("-", 1)[1]) + 1 if row else 1
    return f"{prefix}{n:04d}"


def insert_invoice(user_id: str, inv: dict) -> dict:
    with closing(connect()) as con, con:
        con.execute(
            """INSERT INTO invoices(user_id,no,client,issued,due,items_json,subtotal10,subtotal8,tax10,tax8,total,status,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id, inv["no"], inv["client"], inv["issued"], inv["due"], json.dumps(inv["items"], ensure_ascii=False),
             inv["subtotal10"], inv["subtotal8"], inv["tax10"], inv["tax8"], inv["total"], "unpaid", now()),
        )
    return get_invoice(user_id, inv["no"])  # type: ignore[return-value]


def _inv_row(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["items"] = json.loads(d.pop("items_json"))
    return d


def get_invoice(user_id: str, no: str) -> dict | None:
    with closing(connect()) as con:
        row = con.execute("SELECT * FROM invoices WHERE user_id=? AND no=?", (user_id, no)).fetchone()
    return _inv_row(row) if row else None


def list_invoices(user_id: str, status: str | None = None) -> list[dict]:
    sql, args = "SELECT * FROM invoices WHERE user_id=?", [user_id]
    if status in ("paid", "unpaid"):
        sql += " AND status=?"; args.append(status)
    sql += " ORDER BY issued DESC, no DESC"
    with closing(connect()) as con:
        return [_inv_row(r) for r in con.execute(sql, args).fetchall()]


def mark_invoice_paid(user_id: str, no: str, paid_on: str) -> dict | None:
    """入金消込: 請求書を支払済にし、売上入金として帳簿にも記録する。"""
    inv = get_invoice(user_id, no)
    if not inv or inv["status"] == "paid":
        return inv
    with closing(connect()) as con, con:
        con.execute("UPDATE invoices SET status='paid', paid_on=? WHERE user_id=? AND no=?", (paid_on, user_id, no))
    # 税率ごとに1件ずつ記録（混在請求書でも消費税計算が正しくなるように）
    for rate, gross in ((10, inv["subtotal10"] + inv["tax10"]), (8, inv["subtotal8"] + inv["tax8"])):
        if gross > 0:
            add_entry(user_id, {"date": paid_on, "kind": "inc", "store": f"{inv['client']}（{no}）", "amount": gross,
                                "category": "売上高", "rate": rate, "invoice_no": ""}, source="INVOICE")
    return get_invoice(user_id, no)
