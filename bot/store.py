"""Veri katmanı (SQLite veya PostgreSQL). Tüm kanallar (LINE, WhatsApp, web API) buradan okur/yazar.

`DATABASE_URL` (postgres://...) tanımlıysa PostgreSQL, değilse `DB_PATH` SQLite dosyası kullanılır.
SQL'ler `?` yer tutucusuyla yazılır; PostgreSQL için `%s`'ye çevrilir. Literal `%` kullanma.

Defter anahtarı `user_id`: LINE userId, `wa:<telefon>` (WhatsApp) veya web'den açılan defterler.
Şema yalnızca ekleyici (additive) değişir — CLAUDE.md "veri silme yok".
"""
from __future__ import annotations

import atexit
import hashlib
import json
import os
import secrets
import sqlite3
import threading
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))

SCHEMA = [
    # T-065: 訂正・削除の履歴 (電帳法). Satırlar yalnızca eklenir; güncellenmez/silinmez.
    """CREATE TABLE IF NOT EXISTS audit_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        entity TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        action TEXT NOT NULL,
        before_json TEXT NOT NULL DEFAULT '',
        after_json TEXT NOT NULL DEFAULT '',
        actor TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS ix_audit_entity ON audit_log(user_id, entity, entity_id)",
    # Bir hesapta birden çok şirket (companies.py): ana defter account_ledgers'ta, ekler burada
    """CREATE TABLE IF NOT EXISTS account_companies(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id BIGINT NOT NULL,
        user_id TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS line_targets(
        line_user_id TEXT PRIMARY KEY,
        ledger_user_id TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""",
    # AI 読み取りの利用量（概算料金の表示用）
    """CREATE TABLE IF NOT EXISTS ai_usage(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        kind TEXT NOT NULL,
        units INTEGER NOT NULL DEFAULT 1,
        input_tokens INTEGER NOT NULL DEFAULT 0,
        output_tokens INTEGER NOT NULL DEFAULT 0,
        cost_jpy REAL NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    )""",
    # T-061: 取引先マスタ（通帳の摘要 → 正式名称・登録番号・科目）
    """CREATE TABLE IF NOT EXISTS counterparties(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        name TEXT NOT NULL,
        match_key TEXT NOT NULL DEFAULT '',
        furigana TEXT NOT NULL DEFAULT '',
        corporate_number TEXT NOT NULL DEFAULT '',
        registration_no TEXT NOT NULL DEFAULT '',
        category TEXT NOT NULL DEFAULT '',
        source TEXT NOT NULL DEFAULT 'user',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(user_id, name)
    )""",
    """CREATE TABLE IF NOT EXISTS counterparty_aliases(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        alias TEXT NOT NULL,
        counterparty_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(user_id, alias)
    )""",
    # T-060: 仕切書（買取伝票）の確認キュー
    """CREATE TABLE IF NOT EXISTS slips(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    kind TEXT NOT NULL DEFAULT 'inc',
    d TEXT NOT NULL DEFAULT '',
    issuer TEXT NOT NULL DEFAULT '',
    registration_no TEXT NOT NULL DEFAULT '',
    total BIGINT NOT NULL DEFAULT 0,
    lines TEXT NOT NULL DEFAULT '[]',
    image_path TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'LINE',
    reader TEXT NOT NULL DEFAULT 'manual',
    entry_id INTEGER,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)""",
    "CREATE INDEX IF NOT EXISTS slips_user_status ON slips(user_id, status, d)",
    # T-047c: kullanıcı tercihleri (bot yanıt dili)
    """CREATE TABLE IF NOT EXISTS user_prefs(
        user_id TEXT PRIMARY KEY,
        lang TEXT NOT NULL DEFAULT 'ja',
        updated_at TEXT NOT NULL
    )""",
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
    # T-042 abonelik (billing.py) — defter (user_id) başına bir satır
    """CREATE TABLE IF NOT EXISTS subscriptions(
        user_id TEXT PRIMARY KEY,
        plan TEXT NOT NULL DEFAULT 'free',
        status TEXT NOT NULL DEFAULT 'incomplete',
        stripe_customer TEXT DEFAULT '',
        stripe_subscription TEXT DEFAULT '',
        current_period_end TEXT DEFAULT '',
        cancel_at_period_end INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS ix_sub_stripe ON subscriptions(stripe_subscription)",
    """CREATE TABLE IF NOT EXISTS billing_events(
        event_id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        received_at TEXT NOT NULL
    )""",
    # T-041 ekip üyeleri (team.py) — sahip (owner) account_ledgers / LINE token'ıdır; burada yalnızca davetliler
    """CREATE TABLE IF NOT EXISTS ledger_members(
        user_id TEXT NOT NULL,
        account_id BIGINT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('accountant','viewer')),
        created_at TEXT NOT NULL,
        PRIMARY KEY(user_id, account_id)
    )""",
    "CREATE INDEX IF NOT EXISTS ix_members_account ON ledger_members(account_id)",
    """CREATE TABLE IF NOT EXISTS team_invites(
        code_hash TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('accountant','viewer')),
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        used_at TEXT DEFAULT '',
        used_by BIGINT NOT NULL DEFAULT 0
    )""",
    # T-046b hesap silme talebi (deletion.py) — yalnızca kayıt; veri silinmez (işlem insan adımı)
    """CREATE TABLE IF NOT EXISTS deletion_requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL UNIQUE,
        account_id BIGINT NOT NULL DEFAULT 0,
        requested_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending'
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


def is_integrity_error(exc: BaseException) -> bool:
    """UNIQUE/FK ihlali mi? sqlite3.IntegrityError veya psycopg.IntegrityError (UniqueViolation dahil)."""
    if isinstance(exc, sqlite3.IntegrityError):
        return True
    try:
        import psycopg
    except ImportError:  # pragma: no cover - psycopg yalnızca PG kurulumunda
        return False
    return isinstance(exc, psycopg.IntegrityError)


# T-019: PostgreSQL bağlantı havuzu (yalnızca DATABASE_URL varken). Her istekte yeni TCP+TLS bağlantısı
# açmak yerine `psycopg_pool.ConnectionPool` yeniden kullanılır. URL değişirse (testler) eski havuz kapanır.
POOL_MIN_SIZE = 1
POOL_MAX_SIZE = 10  # iç içe tx() derinliği + eşzamanlı istekler için yeterli; Render free PG ~97 bağlantı
POOL_TIMEOUT = 30.0  # sn: havuz doluysa bekleme üst sınırı (sonra PoolTimeout)
_pool = None
_pool_url = ""
_pool_lock = threading.Lock()
_atexit_registered = False


def _get_pool():
    """Süreç başına tek havuz; ilk kullanımda açılır (uvicorn worker fork'undan sonra)."""
    global _pool, _pool_url, _atexit_registered
    url = database_url()
    with _pool_lock:
        if _pool is not None and _pool_url == url and not _pool.closed:
            return _pool
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool

        old = _pool
        _pool = ConnectionPool(
            url,
            min_size=POOL_MIN_SIZE,
            max_size=POOL_MAX_SIZE,
            timeout=POOL_TIMEOUT,
            # prepare_threshold=None: sunucu tarafı hazır ifade yok → init_db sütun eklese de
            # havuzdaki eski bağlantılarda "cached plan must not change result type" olmaz.
            kwargs={"row_factory": dict_row, "prepare_threshold": None},
            # Render'ın kapattığı boş bağlantılar verilmeden önce yoklanır
            check=ConnectionPool.check_connection,
            name="tegaru",
            open=True,
        )
        _pool_url = url
        if not _atexit_registered:  # betikler/testler: süreç biterken arka plan iş parçacıkları düzgün dursun
            atexit.register(close_pool)
            _atexit_registered = True
    if old is not None:
        old.close()
    return _pool


def close_pool() -> None:
    """Uygulama kapanışında havuzu kapat (app.py shutdown). Havuz yoksa bir şey yapmaz."""
    global _pool, _pool_url
    with _pool_lock:
        pool, _pool, _pool_url = _pool, None, ""
    if pool is not None:
        pool.close()


@contextmanager
def tx():
    """Tek işlem (transaction): blok hatasız biterse commit, hata olursa rollback."""
    if is_pg():
        # pool.connection(): blok sonunda commit (hata → rollback) ve bağlantıyı havuza iade
        with _get_pool().connection() as con:
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


# Sonradan eklenen sütunlar (yalnızca ekleyici; mevcut veritabanlarında init_db sırasında eklenir).
# (tablo, sütun, SQLite tanımı, PostgreSQL tanımı)
ADDED_COLUMNS: list[tuple[str, str, str, str]] = [
    # レシートの読み取り方法（'' = サーバー既定 / ocr / ai / auto）
    ("user_prefs", "receipt_reader", "TEXT NOT NULL DEFAULT ''", "TEXT NOT NULL DEFAULT ''"),
    # T-063: 登録番号の確認結果（形式 / 国税庁 インボイス公表サイト）
    ("counterparties", "invoice_status", "TEXT NOT NULL DEFAULT ''", "TEXT NOT NULL DEFAULT ''"),
    ("counterparties", "invoice_name", "TEXT NOT NULL DEFAULT ''", "TEXT NOT NULL DEFAULT ''"),
    ("counterparties", "invoice_checked_at", "TEXT NOT NULL DEFAULT ''", "TEXT NOT NULL DEFAULT ''"),
    # T-062: 通帳取込（取込元・残高チェック）と確認状態
    ("bank_tx", "src", "TEXT NOT NULL DEFAULT 'csv'", "TEXT NOT NULL DEFAULT 'csv'"),
    ("bank_tx", "balance_ok", "INTEGER", "INTEGER"),
    ("bank_tx", "status", "TEXT NOT NULL DEFAULT ''", "TEXT NOT NULL DEFAULT ''"),
    ("bank_tx", "category", "TEXT NOT NULL DEFAULT ''", "TEXT NOT NULL DEFAULT ''"),
    ("bank_tx", "counterparty_id", "INTEGER", "BIGINT"),
    # T-052: işlenen son Stripe olayının `created` zamanı (unix sn) — eski olaylar durumu ezmesin
    ("subscriptions", "last_event_created", "INTEGER NOT NULL DEFAULT 0", "BIGINT NOT NULL DEFAULT 0"),
    # T-041: 0 = defter sahibi / eski token; >0 = o hesabın ekip üyesi oturumu (rol ledger_members'tan)
    ("api_tokens", "account_id", "INTEGER NOT NULL DEFAULT 0", "BIGINT NOT NULL DEFAULT 0"),
]


def _add_columns(con: "_Conn") -> None:
    for table, col, lite, pg in ADDED_COLUMNS:
        if con.pg:
            con.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {pg}")
        else:
            have = {r["name"] for r in con.execute(f"PRAGMA table_info({table})").fetchall()}
            if col not in have:
                con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {lite}")


def init_db() -> None:
    with tx() as con:
        for stmt in _schema():
            con.execute(stmt)
        _add_columns(con)


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


# ---------------------------------------------------------------- audit (T-065)
AUDIT_ENTITIES = ("entry", "invoice", "bank_tx")


def _audit(con: "_Conn", user_id: str, entity: str, entity_id, action: str,
           before: dict | None, after: dict | None, actor: str = "") -> None:
    """訂正・削除の履歴: aynı işlemde (transaction) önce/sonra görüntüsünü ekler. Değişiklik yoksa yazmaz."""
    if action == "update" and before == after:
        return
    dump = (lambda r: json.dumps(r, ensure_ascii=False, sort_keys=True, default=str) if r is not None else "")
    con.execute(
        """INSERT INTO audit_log(user_id,entity,entity_id,action,before_json,after_json,actor,created_at)
           VALUES(?,?,?,?,?,?,?,?)""",
        (user_id, entity, str(entity_id), action, dump(before), dump(after), actor or "", now()),
    )


def _audit_row(r) -> dict:
    d = dict(r)
    d["before"] = json.loads(d.pop("before_json")) if d.get("before_json") else None
    d["after"] = json.loads(d.pop("after_json")) if d.get("after_json") else None
    if d["before"] and d["after"]:
        d["changed"] = sorted(k for k in set(d["before"]) | set(d["after"]) if d["before"].get(k) != d["after"].get(k))
    else:
        d["changed"] = []
    return d


def audit_history(user_id: str, entity: str, entity_id) -> list[dict]:
    """Bir kaydın tüm geçmişi (eskiden yeniye). Silinmiş kayıtlar için de döner."""
    with tx() as con:
        rows = con.execute("SELECT * FROM audit_log WHERE user_id=? AND entity=? AND entity_id=? ORDER BY id",
                           (user_id, entity, str(entity_id))).fetchall()
    return [_audit_row(r) for r in rows]


def audit_recent(user_id: str, entity: str | None = None, action: str | None = None, limit: int = 100) -> list[dict]:
    """Defterin son değişiklikleri (yeniden eskiye)."""
    sql, args = "SELECT * FROM audit_log WHERE user_id=?", [user_id]
    if entity:
        sql += " AND entity=?"; args.append(entity)
    if action:
        sql += " AND action=?"; args.append(action)
    sql += " ORDER BY id DESC LIMIT ?"; args.append(int(limit))
    with tx() as con:
        return [_audit_row(r) for r in con.execute(sql, args).fetchall()]


def _entry_snapshot(con: "_Conn", user_id: str, entry_id: int) -> dict | None:
    row = con.execute("SELECT * FROM entries WHERE id=? AND user_id=?", (entry_id, user_id)).fetchone()
    return dict(row) if row else None


def add_entry(user_id: str, e: dict, image_path: str = "", source: str = "LINE", actor: str = "") -> int:
    check_amount(e["amount"])
    with tx() as con:
        cur = con.execute(
            """INSERT INTO entries(user_id,d,kind,store,amount,category,rate,invoice_no,source,image_path,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?) RETURNING id""",
            (user_id, e["date"], e["kind"], e["store"], int(e["amount"]), e["category"],
             int(e["rate"]), e.get("invoice_no", ""), source, image_path, now()),
        )
        eid = int(cur.fetchone()["id"])
        _audit(con, user_id, "entry", eid, "create", None, _entry_snapshot(con, user_id, eid), actor or source)
        return eid


def last_entry(user_id: str) -> dict | None:
    with tx() as con:
        row = con.execute("SELECT * FROM entries WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
    return dict(row) if row else None


def update_entry(user_id: str, entry_id: int, actor: str = "", **fields) -> dict | None:
    allowed = {"category", "rate", "store", "amount", "d", "invoice_no", "kind"}
    sets = {k: v for k, v in fields.items() if k in allowed}
    if not sets:
        return None
    if "amount" in sets:
        sets["amount"] = check_amount(sets["amount"])
    cols = ", ".join(f"{k}=?" for k in sets)
    with tx() as con:
        before = _entry_snapshot(con, user_id, entry_id)
        con.execute(f"UPDATE entries SET {cols} WHERE id=? AND user_id=?", (*sets.values(), entry_id, user_id))
        after = _entry_snapshot(con, user_id, entry_id)
        if before is not None:
            _audit(con, user_id, "entry", entry_id, "update", before, after, actor)
    return after


def undo_last(user_id: str, actor: str = "LINE") -> dict | None:
    with tx() as con:
        row = con.execute("SELECT * FROM entries WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
        if row:
            con.execute("DELETE FROM entries WHERE id=?", (row["id"],))
            _audit(con, user_id, "entry", row["id"], "delete", dict(row), None, actor)
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


def issue_token(user_id: str, label: str = "", account_id: int = 0) -> str:
    """Yeni token üretir; (defter, hesap) başına en fazla MAX_TOKENS_PER_USER (en eskiler iptal edilir).

    `account_id=0` sahip/eski token'dır. Ekip üyesi oturumları (T-041) kendi hesap kimliğiyle ayrı sayılır,
    böylece üyeler birbirinin (veya sahibin) oturumunu düşürmez.
    """
    token = "tk_" + secrets.token_urlsafe(24)
    with tx() as con:
        con.execute("INSERT INTO api_tokens(token_hash,user_id,label,created_at,account_id) VALUES(?,?,?,?,?)",
                    (_hash(token), user_id, label, datetime.now(JST).isoformat(), int(account_id)))
        con.execute(
            """DELETE FROM api_tokens WHERE user_id=? AND account_id=? AND token_hash NOT IN (
                   SELECT token_hash FROM (SELECT token_hash FROM api_tokens WHERE user_id=? AND account_id=?
                                           ORDER BY created_at DESC LIMIT ?) AS keep)""",
            (user_id, int(account_id), user_id, int(account_id), MAX_TOKENS_PER_USER),
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


def token_info(token: str) -> dict | None:
    """{user_id, account_id} — account_id 0 ise sahip/eski token (T-041)."""
    if not token:
        return None
    with tx() as con:
        row = con.execute("SELECT user_id, account_id FROM api_tokens WHERE token_hash=?",
                          (_hash(token),)).fetchone()
    return {"user_id": row["user_id"], "account_id": int(row["account_id"] or 0)} if row else None


# ---------------------------------------------------------------- profiles
def get_lang(user_id: str) -> str:
    """Bot yanıt dili (T-047c). Kayıt yoksa / hata olursa 'ja'."""
    try:
        with tx() as con:
            row = con.execute("SELECT lang FROM user_prefs WHERE user_id=?", (user_id,)).fetchone()
    except Exception:
        return "ja"
    return row["lang"] if row and row["lang"] in ("ja", "tr", "en") else "ja"


def set_lang(user_id: str, lang: str) -> str:
    if lang not in ("ja", "tr", "en"):
        raise ValueError("lang")
    with tx() as con:
        con.execute(
            """INSERT INTO user_prefs(user_id,lang,updated_at) VALUES(?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET lang=excluded.lang, updated_at=excluded.updated_at""",
            (user_id, lang, datetime.now(JST).isoformat(timespec="seconds")),
        )
    return lang


READERS = ("", "ocr", "ai", "auto")


def get_receipt_reader(user_id: str) -> str:
    try:
        with tx() as con:
            row = con.execute("SELECT receipt_reader FROM user_prefs WHERE user_id=?", (user_id,)).fetchone()
    except Exception:
        return ""
    return row["receipt_reader"] if row and row["receipt_reader"] in READERS else ""


def set_receipt_reader(user_id: str, reader: str) -> str:
    if reader not in READERS:
        raise ValueError("reader")
    with tx() as con:
        con.execute(
            """INSERT INTO user_prefs(user_id,lang,updated_at,receipt_reader) VALUES(?,?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET receipt_reader=excluded.receipt_reader, updated_at=excluded.updated_at""",
            (user_id, "ja", now(), reader))
    return reader


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


def _invoice_snapshot(con: "_Conn", user_id: str, no: str) -> dict | None:
    row = con.execute("SELECT * FROM invoices WHERE user_id=? AND no=?", (user_id, no)).fetchone()
    return _inv_row(row) if row else None


def insert_invoice(user_id: str, inv: dict, actor: str = "") -> dict:
    with tx() as con:
        con.execute(
            """INSERT INTO invoices(user_id,no,client,issued,due,items_json,subtotal10,subtotal8,tax10,tax8,total,status,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id, inv["no"], inv["client"], inv["issued"], inv["due"], json.dumps(inv["items"], ensure_ascii=False),
             inv["subtotal10"], inv["subtotal8"], inv["tax10"], inv["tax8"], inv["total"], "unpaid", now()),
        )
        _audit(con, user_id, "invoice", inv["no"], "create", None, _invoice_snapshot(con, user_id, inv["no"]), actor)
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


def mark_invoice_paid(user_id: str, no: str, paid_on: str, actor: str = "") -> dict | None:
    """入金消込: 請求書を支払済にし、売上入金として帳簿にも記録する。"""
    inv = get_invoice(user_id, no)
    if not inv or inv["status"] == "paid":
        return inv
    with tx() as con:
        con.execute("UPDATE invoices SET status='paid', paid_on=? WHERE user_id=? AND no=?", (paid_on, user_id, no))
        _audit(con, user_id, "invoice", no, "update", inv, _invoice_snapshot(con, user_id, no), actor)
    # 税率ごとに1件ずつ記録（混在請求書でも消費税計算が正しくなるように）
    for rate, gross in ((10, inv["subtotal10"] + inv["tax10"]), (8, inv["subtotal8"] + inv["tax8"])):
        if gross > 0:
            add_entry(user_id, {"date": paid_on, "kind": "inc", "store": f"{inv['client']}（{no}）", "amount": gross,
                                "category": "売上高", "rate": rate, "invoice_no": ""}, source="INVOICE", actor=actor)
    return get_invoice(user_id, no)


# ---------------------------------------------------------------- entries (web)
def get_entry(user_id: str, entry_id: int) -> dict | None:
    with tx() as con:
        row = con.execute("SELECT * FROM entries WHERE id=? AND user_id=?", (entry_id, user_id)).fetchone()
    return dict(row) if row else None


def delete_entry(user_id: str, entry_id: int, actor: str = "") -> bool:
    """Kullanıcının kendi kaydını silmesi (LINE 「取消」 ile aynı yetki). Silinen kayıt audit_log'da kalır (T-065)."""
    with tx() as con:
        before = _entry_snapshot(con, user_id, entry_id)
        cur = con.execute("DELETE FROM entries WHERE id=? AND user_id=?", (entry_id, user_id))
        if cur.rowcount > 0:
            _audit(con, user_id, "entry", entry_id, "delete", before, None, actor)
            # 銀行明細からの経費なら紐付けを外し、再登録できるようにする (T-065b: bank_tx 側にも履歴)
            linked = con.execute("SELECT id FROM bank_tx WHERE entry_id=? AND user_id=?", (entry_id, user_id)).fetchall()
            for r in linked:
                b = _bank_snapshot(con, user_id, r["id"])
                con.execute("UPDATE bank_tx SET entry_id=NULL WHERE id=? AND user_id=?", (r["id"], user_id))
                _audit(con, user_id, "bank_tx", r["id"], "update", b, _bank_snapshot(con, user_id, r["id"]), actor)
            return True
    return False


# ---------------------------------------------------------------- bank
def insert_bank_rows(user_id: str, rows: list[dict], account: str = "") -> tuple[int, int]:
    """(eklenen, yinelenen). Parmak izi: tarih + açıklama + tutar + bakiye + aynı gün sıra no.

    `legacy_description` (bank_csv, T-051) varsa eski biçimdeki parmak izi de kontrol edilir."""
    import hashlib as _h
    added = dup = 0
    seen: dict[str, int] = {}
    seen_legacy: dict[str, int] = {}

    def _fp(base: str, counter: dict[str, int]) -> str:
        counter[base] = counter.get(base, 0) + 1
        return _h.sha256(f"{account}|{base}|{counter[base]}".encode()).hexdigest()[:32]

    with tx() as con:
        for r in rows:
            fps = [_fp(f"{r['d']}|{r['description']}|{r['amount']}|{r.get('balance')}", seen)]
            # T-051: eski biçim (yalnızca ilk 摘要 sütunu) ile alınmış satırlar da yineleme sayılır.
            # Sayaç eski biçimin anahtarına göre tutulur → eski içe aktarmadaki sıra numarasıyla aynı.
            legacy = r.get("legacy_description") or r["description"]
            fps.append(_fp(f"{r['d']}|{legacy}|{r['amount']}|{r.get('balance')}", seen_legacy))
            fp = fps[0]
            exists = con.execute(
                "SELECT 1 FROM bank_tx WHERE user_id=? AND fingerprint IN (?, ?)", (user_id, fps[0], fps[1])
            ).fetchone()
            if exists:
                dup += 1
                continue
            con.execute(
                """INSERT INTO bank_tx(user_id,d,description,amount,balance,account,fingerprint,created_at,src,balance_ok)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (user_id, r["d"], r["description"][:200], int(r["amount"]), r.get("balance"), account[:50], fp, now(),
                 r.get("src", "csv"), None if r.get("balance_ok") is None else int(r["balance_ok"])),
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


def link_bank_tx(user_id: str, tx_id: int, *, invoice_no: str | None = None, entry_id: int | None = None,
                 actor: str = "") -> None:
    fields = {k: v for k, v in (("invoice_no", invoice_no), ("entry_id", entry_id)) if v is not None}
    if fields:
        update_bank_tx(user_id, tx_id, actor=actor, **fields)


def _bank_snapshot(con: "_Conn", user_id: str, tx_id: int) -> dict | None:
    row = con.execute("SELECT * FROM bank_tx WHERE id=? AND user_id=?", (tx_id, user_id)).fetchone()
    return dict(row) if row else None


BANK_TX_EDITABLE = ("amount", "balance", "status", "category", "counterparty_id", "entry_id", "invoice_no")


def update_bank_tx(user_id: str, tx_id: int, actor: str = "", **fields) -> dict | None:
    """bank_tx düzeltmesi/durum değişikliği (T-065b): aynı transaction'da önce/sonra audit_log'a yazılır.

    `balance_ok` türetilmiş bir alandır (残高チェック) ve burada değiştirilmez/kaydedilmez."""
    sets = {k: v for k, v in fields.items() if k in BANK_TX_EDITABLE}
    with tx() as con:
        before = _bank_snapshot(con, user_id, tx_id)
        if before is None or not sets:
            return before
        cols = ", ".join(f"{k}=?" for k in sets)
        con.execute(f"UPDATE bank_tx SET {cols} WHERE id=? AND user_id=?", (*sets.values(), tx_id, user_id))
        after = _bank_snapshot(con, user_id, tx_id)
        _audit(con, user_id, "bank_tx", tx_id, "update", before, after, actor)
    return after
