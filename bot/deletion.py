"""Hesap silme talebi (T-046b).

Talep yalnızca kaydedilir; veri **silinmez** (CLAUDE.md: veri silme yok). Silme işlemi insan adımıdır —
bkz. docs/OPERATIONS.md. Defter (user_id) başına tek satır (`UNIQUE(user_id)`): tekrar talep idempotenttir,
eşzamanlı iki talepte de tek satır oluşur.

Durumlar: `pending` (申請済み, işlem bekliyor). İnsan operatör ileride `done` / `cancelled` yazabilir;
`cancelled` bir talep yeniden istenirse tekrar `pending` olur.
"""
from __future__ import annotations

import billing
import store
from store import tx

PENDING = "pending"


def _row(r) -> dict:
    return {"id": int(r["id"]), "status": r["status"], "requested_at": r["requested_at"]}


def get(user_id: str) -> dict | None:
    with tx() as con:
        r = con.execute("SELECT id, status, requested_at FROM deletion_requests WHERE user_id=?",
                        (user_id,)).fetchone()
    return _row(r) if r else None


def billing_active(user_id: str) -> bool:
    """Ücretli abonelik hâlâ yenilenecek mi? (解約 önerisi için; dönem sonunda iptal edilecekse False)."""
    sub = billing.get_subscription(user_id)
    return bool(sub and sub["plan"] in billing.PAID_PLANS and sub["status"] in billing.ACTIVE_STATUSES
                and not sub["cancel_at_period_end"])


def request(user_id: str, account_id: int) -> tuple[dict, bool]:
    """Talebi kaydeder → (talep, yeni_mi). Zaten `pending` ise dokunmaz (idempotent)."""
    cur = get(user_id)
    if cur and cur["status"] == PENDING:
        return cur, False
    now = store.now()
    created = False
    with tx() as con:
        if cur:  # cancelled / done → yeniden talep
            con.execute("UPDATE deletion_requests SET status=?, requested_at=?, account_id=? WHERE user_id=?",
                        (PENDING, now, account_id, user_id))
            created = True
        else:  # eşzamanlı talepte UNIQUE(user_id) tek satır bırakır
            ins = con.execute("INSERT INTO deletion_requests(user_id, account_id, requested_at, status) "
                              "VALUES(?,?,?,?) ON CONFLICT(user_id) DO NOTHING", (user_id, account_id, now, PENDING))
            created = ins.rowcount == 1
    return get(user_id), created


def list_pending() -> list[dict]:
    """Operatör için: bekleyen talepler (sahip e-postasıyla)."""
    with tx() as con:
        rows = con.execute(
            """SELECT d.id, d.user_id, d.account_id, d.requested_at, d.status, a.email
               FROM deletion_requests d LEFT JOIN accounts a ON a.id = d.account_id
               WHERE d.status=? ORDER BY d.requested_at""", (PENDING,)).fetchall()
    return [{"id": int(r["id"]), "user_id": r["user_id"], "account_id": int(r["account_id"]),
             "email": r["email"] or "", "requested_at": r["requested_at"], "status": r["status"]} for r in rows]
