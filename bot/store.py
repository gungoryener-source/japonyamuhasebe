"""Veri katmanı (SQLite veya PostgreSQL). Tüm kanallar (LINE, WhatsApp, web API) buradan okur/yazar.

`DATABASE_URL` (postgres://...) tanımlıysa PostgreSQL, değilse `DB_PATH` SQLite dosyası kullanılır.
SQL'ler `?` yer tutucusuyla yazılır; PostgreSQL için `%s`'ye çevrilir. Literal `%` kullanma.

Defter anahtarı `user_id`: LINE userId, `wa:<telefon>` (WhatsApp) veya web'den açılan defterler.
Şema yalnızca ekleyici (additive) değişir — CLAUDE.md "veri silme yok".
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
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
    """CREATE TABLE IF NOT EXISTS bank_tx(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        d TEXT NOT NULL,
        description TEXT NOT NULL,
        amount BIGINT NOT NULL,           -- + 入金 / − 出金
        balance BIGINT,
        account TEXT DEFAULT '',
        fingerprint TEXT NOT NULL,        -- aynı satırın iki kez alınmasını önler
        invoice_no TEXT DEFAULT '',       -- 消込 yapılan fatura
        entry_id INTEGER,                 -- 経費 olarak kaydedildiyse
        created_at TEXT NOT NULL,
        UNIQUE(user_id, fingerprint)
    )""",
    "CREATE INDEX IF NOT EXISTS ix_bank_user_d ON bank_tx(user_id, d)",
    """CREATE TABLE IF NOT EXISTS profiles(
        user_id TEXT PRIMARY KEY,
        business_name TEXT DEFAULT '',
        registration_no TEXT DEFAULT '',
        individual INTEGER DEFAULT 1,
        updated_at TEXT NOT NULL
    )""",
    # T-040 hesap sistemi (accounts.py)
    """CREATE TABLE IF NOT EXISTS accounts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        email_verified INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS account_ledgers(
        account_id BIGINT PRIMARY KEY,
        user_id TEXT NOT NULL UNIQUE,
        linked_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS password_resets(
        token_hash TEXT PRIMARY KEY,
        account_id BIGINT NOT NULL,
        expires_at TEXT NOT NULL,
        used_at TEXT DEFAULT ''
    )""",
]


def db_path() -> str:
    return os.environ.get("DB_PATH", "tegaru.db")


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    return "postgresql://" + url[len("postgres://"):] if url.startswith("postgres://") else url


def is_pg() -> bool:
    return database_url().startswith("postgresql://")


class _Conn:
    """sqlite3 / psycopg bağlantıları için ortak arayüz (execute → cursor; satırlar dict)."""

    def __init__(self, raw, pg: bool):
        self.raw, self.pg = raw, pg

    def execute(self, sql: str, args=()):
        if self.pg:
            sql = sql.replace("?", "%s")
        return self.raw.execute(sql, tuple(args))


@contextmanager
def tx():
    """Tek işlem (transaction): blok hatasız biterse commit, hata olursa rollback."""
    if is_pg():
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(database_url(), row_factory=dict_row) as con:
            yield _Conn(con, True)
    else:
        con = sqlite3.connect(db_path())
        con.row_factory = sqlite3.Row
        try:
            with con:
                yield _Conn(con, False)
        finally:
            con.close()


def connect() -> sqlite3.Connection:
    """Geriye uyumluluk (yalnızca SQLite). Yeni kodda `tx()` kullan."""
    con = sqlite3.connect(db_path())
    con.row_factory = sqlite3.Row
    return con


def _schema() -> list[str]:
    if not is_pg():
        return SCHEMA
    return [stmt.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "BIGSERIAL PRIMARY KEY") for stmt in SCHEMA]


def init_db() -> None:
    with tx() as con:
        for stmt in _schema():
            con.execute(stmt)


def now() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def today() -> date:
    return datetime.now(JST).date()


# ---------------------------------------------------------------- entries
# entries.amount PostgreSQL'de INTEGER (int4, ≤ 2,147,483,647). Şemayı değiştirmeden taşmayı önlemek için
# tek kayıt tutarı < 20億円. Fatura toplamı (< 1e9 税抜 → 税込 ≤ 1.1e9) bu sınırın altında kalır.
MAX_ENTRY_AMOUNT = 2_000_000_000


class AmountOutOfRange(ValueError):
    """Kayıt tutarı 0 < amount < MAX_ENTRY_AMOUNT dışında."""


def check_amount(amount) -> int:
    a = int(amount)
    if not 0 < a < MAX_ENTRY_AMOUNT:
        raise AmountOutOfRange(f"amount must be > 0 and < {MAX_ENTRY_AMOUNT}")
    return a


def add_entry(user_id: str, e: dict, image_path: str = "", source: str = "LINE") -> int:
    check_amount(e["amount"])
    with tx() as con:
        cur = con.execute(
            """INSERT INTO entries(user_id,d,kind,store,amount,category,rate,invoice_no,source,image_path,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?) RETURNING id""",
            (user_id, e["date"], e["kind"], e["store"], int(e["amount"]), e["category"],
             int(e["rate"]), e.get("invoice_no", ""), source, image_path, now()),
        )
        return int(cur.fetchone()["id"])


def last_entry(user_id: str) -> dict | None:
    with tx() as con:
        row = con.execute("SELECT * FROM entries WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
    return dict(row) if row else None


def update_entry(user_id: str, entry_id: int, **fields) -> dict | None:
    allowed = {"category", "rate", "store", "amount", "d", "invoice_no", "kind"}
    sets = {k: v for k, v in fields.items() if k in allowed}
    if not sets:
        return None
    if "amount" in sets:
        sets["amount"] = check_amount(sets["amount"])
    cols = ", ".join(f"{k}=?" for k in sets)
    with tx() as con:
        con.execute(f"UPDATE entries SET {cols} WHERE id=? AND user_id=?", (*sets.values(), entry_id, user_id))
        row = con.execute("SELECT * FROM entries WHERE id=? AND user_id=?", (entry_id, user_id)).fetchone()
    return dict(row) if row else None


def undo_last(user_id: str) -> dict | None:
    with tx() as con:
        row = con.execute("SELECT * FROM entries WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
        if row:
            con.execute("DELETE FROM entries WHERE id=?", (row["id"],))
    return dict(row) if row else None


def month_summary(user_id: str, ym: str | None = None) -> tuple[int, int]:
    ym = ym or datetime.now(JST).strftime("%Y-%m")
    with tx() as con:
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
        sql += " AND store LIKE ? ESCAPE '!'"
        args.append("%" + q.replace("!", "!!").replace("%", "!%").replace("_", "!_") + "%")
    if amount_min is not None:
        sql += " AND amount>=?"; args.append(amount_min)
    if amount_max is not None:
        sql += " AND amount<=?"; args.append(amount_max)
    if kind in ("inc", "exp"):
        sql += " AND kind=?"; args.append(kind)
    sql += " ORDER BY d, id LIMIT ?"
    args.append(max(1, min(limit, 5000)))
    with tx() as con:
        return [dict(r) for r in con.execute(sql, args).fetchall()]


def entries_in_range(user_id: str, date_from: str, date_to: str, page_size: int = 2000) -> list[dict]:
    """期間内の全仕訳を (d, id) 順に返す（年次集計・CSV 用）。

    `search_entries` の上限（5000 件）で年次の消費税・損益・CSV が黙って欠けないよう、
    キーセット方式で全件を読む。
    """
    out: list[dict] = []
    last_d, last_id = "", 0
    with tx() as con:
        while True:
            rows = con.execute(
                """SELECT * FROM entries WHERE user_id=? AND d>=? AND d<=?
                   AND (d>? OR (d=? AND id>?)) ORDER BY d, id LIMIT ?""",
                (user_id, date_from, date_to, last_d, last_d, last_id, page_size),
            ).fetchall()
            out.extend(dict(r) for r in rows)
            if len(rows) < page_size:
                return out
            last_d, last_id = rows[-1]["d"], rows[-1]["id"]


# ---------------------------------------------------------------- tokens
def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


MAX_TOKENS_PER_USER = 5


def issue_token(user_id: str, label: str = "") -> str:
    """Yeni token üretir; kullanıcı başına en fazla MAX_TOKENS_PER_USER (en eskiler iptal edilir)."""
    token = "tk_" + secrets.token_urlsafe(24)
    with tx() as con:
        con.execute("INSERT INTO api_tokens(token_hash,user_id,label,created_at) VALUES(?,?,?,?)",
                    (_hash(token), user_id, label, datetime.now(JST).isoformat()))
        con.execute(
            """DELETE FROM api_tokens WHERE user_id=? AND token_hash NOT IN (
                   SELECT token_hash FROM (SELECT token_hash FROM api_tokens WHERE user_id=?
                                           ORDER BY created_at DESC LIMIT ?) AS keep)""",
            (user_id, user_id, MAX_TOKENS_PER_USER),
        )
    return token


def revoke_token(token: str) -> bool:
    with tx() as con:
        cur = con.execute("DELETE FROM api_tokens WHERE token_hash=?", (_hash(token),))
    return cur.rowcount > 0


def user_for_token(token: str) -> str | None:
    if not token:
        return None
    with tx() as con:
        row = con.execute("SELECT user_id FROM api_tokens WHERE token_hash=?", (_hash(token),)).fetchone()
    return row["user_id"] if row else None


# ---------------------------------------------------------------- profiles
def get_profile(user_id: str) -> dict:
    with tx() as con:
        row = con.execute("SELECT * FROM profiles WHERE user_id=?", (user_id,)).fetchone()
    return dict(row) if row else {"user_id": user_id, "business_name": "", "registration_no": "", "individual": 1}


def save_profile(user_id: str, **fields) -> dict:
    p = get_profile(user_id)
    p.update({k: v for k, v in fields.items() if k in ("business_name", "registration_no", "individual")})
    with tx() as con:
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
    with tx() as con:
        row = con.execute("SELECT no FROM invoices WHERE user_id=? AND no LIKE ? ORDER BY no DESC LIMIT 1",
                          (user_id, prefix + "%")).fetchone()
    n = int(row["no"].rsplit("-", 1)[1]) + 1 if row else 1
    return f"{prefix}{n:04d}"


def insert_invoice(user_id: str, inv: dict) -> dict:
    with tx() as con:
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
    with tx() as con:
        row = con.execute("SELECT * FROM invoices WHERE user_id=? AND no=?", (user_id, no)).fetchone()
    return _inv_row(row) if row else None


def list_invoices(user_id: str, status: str | None = None) -> list[dict]:
    sql, args = "SELECT * FROM invoices WHERE user_id=?", [user_id]
    if status in ("paid", "unpaid"):
        sql += " AND status=?"; args.append(status)
    sql += " ORDER BY issued DESC, no DESC"
    with tx() as con:
        return [_inv_row(r) for r in con.execute(sql, args).fetchall()]


def mark_invoice_paid(user_id: str, no: str, paid_on: str) -> dict | None:
    """入金消込: 請求書を支払済にし、売上入金として帳簿にも記録する。"""
    inv = get_invoice(user_id, no)
    if not inv or inv["status"] == "paid":
        return inv
    with tx() as con:
        con.execute("UPDATE invoices SET status='paid', paid_on=? WHERE user_id=? AND no=?", (paid_on, user_id, no))
    # 税率ごとに1件ずつ記録（混在請求書でも消費税計算が正しくなるように）
    for rate, gross in ((10, inv["subtotal10"] + inv["tax10"]), (8, inv["subtotal8"] + inv["tax8"])):
        if gross > 0:
            add_entry(user_id, {"date": paid_on, "kind": "inc", "store": f"{inv['client']}（{no}）", "amount": gross,
                                "category": "売上高", "rate": rate, "invoice_no": ""}, source="INVOICE")
    return get_invoice(user_id, no)


# ---------------------------------------------------------------- entries (web)
def get_entry(user_id: str, entry_id: int) -> dict | None:
    with tx() as con:
        row = con.execute("SELECT * FROM entries WHERE id=? AND user_id=?", (entry_id, user_id)).fetchone()
    return dict(row) if row else None


def delete_entry(user_id: str, entry_id: int) -> bool:
    """Kullanıcının kendi kaydını silmesi (LINE 「取消」 ile aynı yetki)."""
    with tx() as con:
        cur = con.execute("DELETE FROM entries WHERE id=? AND user_id=?", (entry_id, user_id))
        if cur.rowcount > 0:  # 銀行明細からの経費なら紐付けを外し、再登録できるようにする
            con.execute("UPDATE bank_tx SET entry_id=NULL WHERE entry_id=? AND user_id=?", (entry_id, user_id))
            return True
    return False


# ---------------------------------------------------------------- bank
def insert_bank_rows(user_id: str, rows: list[dict], account: str = "") -> tuple[int, int]:
    """(eklenen, yinelenen). Parmak izi: tarih + açıklama + tutar + bakiye + aynı gün sıra no."""
    import hashlib as _h
    added = dup = 0
    seen: dict[str, int] = {}
    with tx() as con:
        for r in rows:
            base = f"{r['d']}|{r['description']}|{r['amount']}|{r.get('balance')}"
            seen[base] = seen.get(base, 0) + 1
            fp = _h.sha256(f"{account}|{base}|{seen[base]}".encode()).hexdigest()[:32]
            exists = con.execute("SELECT 1 FROM bank_tx WHERE user_id=? AND fingerprint=?", (user_id, fp)).fetchone()
            if exists:
                dup += 1
                continue
            con.execute(
                """INSERT INTO bank_tx(user_id,d,description,amount,balance,account,fingerprint,created_at)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (user_id, r["d"], r["description"][:200], int(r["amount"]), r.get("balance"), account[:50], fp, now()),
            )
            added += 1
    return added, dup


def list_bank_tx(user_id: str, limit: int = 500) -> list[dict]:
    with tx() as con:
        rows = con.execute("SELECT * FROM bank_tx WHERE user_id=? ORDER BY d DESC, id DESC LIMIT ?",
                           (user_id, max(1, min(limit, 5000)))).fetchall()
    return [dict(r) for r in rows]


def get_bank_tx(user_id: str, tx_id: int) -> dict | None:
    with tx() as con:
        row = con.execute("SELECT * FROM bank_tx WHERE id=? AND user_id=?", (tx_id, user_id)).fetchone()
    return dict(row) if row else None


def link_bank_tx(user_id: str, tx_id: int, *, invoice_no: str | None = None, entry_id: int | None = None) -> None:
    with tx() as con:
        if invoice_no is not None:
            con.execute("UPDATE bank_tx SET invoice_no=? WHERE id=? AND user_id=?", (invoice_no, tx_id, user_id))
        if entry_id is not None:
            con.execute("UPDATE bank_tx SET entry_id=? WHERE id=? AND user_id=?", (entry_id, tx_id, user_id))
