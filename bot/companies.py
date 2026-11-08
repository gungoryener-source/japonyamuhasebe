"""Bir hesapta birden çok şirket (事業所) — ürün sahibi isteği 2026-11-07.

- Hesabın ilk defteri `account_ledgers`'ta kalır (değişmez). Ek şirketler `account_companies` tablosunda:
  her biri ayrı bir defter (`web:<rastgele>`), tüm muhasebe verisi o defter kimliğiyle ayrılır.
- Sahiplik kontrolleri (team.resolve / switch / join, accounts.account_for_ledger) bu modülü kullanır.
- LINE: aynı LINE hesabından kayıtların hangi şirkete gideceği `line_targets` ile seçilir. Güvenlik için yalnızca
  hesabın SAHİBİ olduğu şirketler seçilebilir (üye olunan defterler hayır: 「パネル」 sahip token'ı verir).
- Fiyatlandırma kararı sonraya bırakıldı (QUESTIONS Q-16): şimdilik her yeni şirket ayrı defter, kendi planı (Free).
  Kötüye kullanım koruması: hesap başına en fazla MAX_COMPANIES_PER_ACCOUNT (varsayılan 100).
"""
from __future__ import annotations

import os
import secrets

import store
from store import tx


class CompanyError(ValueError):
    def __init__(self, message: str, code: int = 400):
        super().__init__(message)
        self.code = code


def max_companies() -> int:
    return int(os.environ.get("MAX_COMPANIES_PER_ACCOUNT", "100"))


# ---------------------------------------------------------------- sahiplik
def owned_ledgers(con, account_id: int) -> list[str]:
    """Hesabın sahibi olduğu defterler: önce ana defter, sonra eklenen şirketler (eklenme sırası)."""
    if not account_id:
        return []
    out = []
    row = con.execute("SELECT user_id FROM account_ledgers WHERE account_id=?", (account_id,)).fetchone()
    if row:
        out.append(row["user_id"])
    out += [r["user_id"] for r in con.execute(
        "SELECT user_id FROM account_companies WHERE account_id=? ORDER BY id", (account_id,)).fetchall()]
    return out


def owns(con, account_id: int, user_id: str) -> bool:
    return bool(account_id) and user_id in owned_ledgers(con, account_id)


def owner_account(con, user_id: str) -> int:
    """Defterin sahibi hesap (yoksa 0, ör. yalnızca LINE ile kullanılan defter)."""
    row = con.execute("SELECT account_id FROM account_ledgers WHERE user_id=?", (user_id,)).fetchone() or \
        con.execute("SELECT account_id FROM account_companies WHERE user_id=?", (user_id,)).fetchone()
    return int(row["account_id"]) if row else 0


# ---------------------------------------------------------------- oluşturma
def create(account_id: int, business_name: str) -> dict:
    if not account_id:
        raise CompanyError("事業所を追加するにはメールアドレスでログインしてください。", 403)
    name = (business_name or "").strip()
    if not name:
        raise CompanyError("事業者名を入力してください。")
    if len(name) > 100:
        raise CompanyError("事業者名は100文字以内にしてください。")
    ledger = "web:" + secrets.token_hex(12)
    with tx() as con:
        n = con.execute("SELECT COUNT(*) AS n FROM account_companies WHERE account_id=?", (account_id,)).fetchone()["n"]
        if n + 1 >= max_companies():
            raise CompanyError("追加できる事業所の上限に達しました。", 409)
        primary = con.execute("SELECT user_id FROM account_ledgers WHERE account_id=?", (account_id,)).fetchone()
    # Q-16: fiyat ayarı açıksa plana dahil sayıyı aşan şirket (ek ücret 0 iken) eklenemez
    import billing
    import pricing
    st = pricing.company_status(billing.current_plan(primary["user_id"]) if primary else "free", n + 1)
    if not st["can_add"]:
        raise CompanyError(f"現在のプランで追加できる事業所は {st['included']} 社までです。プランを変更してください。", 402)
    with tx() as con:
        con.execute("INSERT INTO account_companies(account_id,user_id,created_at) VALUES(?,?,?)",
                    (account_id, ledger, store.now()))
    store.save_profile(ledger, business_name=name)
    return {"user_id": ledger, "business_name": name, "role": "owner"}


# ---------------------------------------------------------------- LINE yönlendirme
def line_companies(line_user_id: str) -> list[dict]:
    """LINE hesabının bağlı olduğu hesabın SAHİP olduğu şirketler (ana defter = LINE defteri dahil)."""
    with tx() as con:
        acc = owner_account(con, line_user_id)
        ids = owned_ledgers(con, acc) if acc else [line_user_id]
        names = {r["user_id"]: r["business_name"] for r in con.execute(
            f"SELECT user_id, business_name FROM profiles WHERE user_id IN ({','.join('?' * len(ids))})", tuple(ids)).fetchall()}
    return [{"user_id": u, "business_name": names.get(u) or ("（LINE の帳簿）" if u == line_user_id else "（名称未設定）")}
            for u in ids]


def line_target(line_user_id: str) -> str:
    """LINE からの記録を入れる帳簿。選択がない / 権限がなくなった場合は LINE 自身の帳簿。"""
    try:
        with tx() as con:
            row = con.execute("SELECT ledger_user_id FROM line_targets WHERE line_user_id=?", (line_user_id,)).fetchone()
            if not row or row["ledger_user_id"] == line_user_id:
                return line_user_id
            acc = owner_account(con, line_user_id)
            return row["ledger_user_id"] if acc and owns(con, acc, row["ledger_user_id"]) else line_user_id
    except Exception:  # noqa: BLE001  tablo yoksa / DB hatası: varsayılan defter
        return line_user_id


def set_line_target(line_user_id: str, ledger_user_id: str) -> dict:
    allowed = {c["user_id"]: c for c in line_companies(line_user_id)}
    if ledger_user_id not in allowed:
        raise CompanyError("この事業所は選べません。", 403)
    with tx() as con:
        con.execute("DELETE FROM line_targets WHERE line_user_id=?", (line_user_id,))
        con.execute("INSERT INTO line_targets(line_user_id,ledger_user_id,updated_at) VALUES(?,?,?)",
                    (line_user_id, ledger_user_id, store.now()))
    return allowed[ledger_user_id]
