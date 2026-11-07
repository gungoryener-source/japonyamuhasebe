"""Ekip üyeleri (T-041): bir deftere (işletme) birden çok kullanıcı.

Roller:
- `owner`      — defterin sahibi: `account_ledgers` ile bağlı hesap veya `account_id=0` token (LINE 「パネル」, admin).
                 Her şeyi yapar; davet/rol/üye yönetimi, abonelik ve LINE bağlama yalnızca sahibe açıktır.
- `accountant` — muhasebe verisini okur ve düzenler (kayıt, fiş, banka, fatura, 事業者情報).
- `viewer`     — yalnızca okur (özet, liste, CSV/PDF indirme).

Akış: sahip `create_invite(role)` → tek kullanımlık `iv_…` kodu (7 gün) → davetli kendi hesabıyla giriş yapıp
`join(code)` → üyelik + o defter için üye oturum token'ı (`api_tokens.account_id = üye hesabı`).
Rol her istekte `ledger_members`'tan okunur: üye çıkarılınca/rol değişince eski token'lar hemen etkilenir.
Şema yalnızca ekleyici; muhasebe verisine dokunulmaz.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta

import store
from store import JST, tx

ROLES = ("owner", "accountant", "viewer")
MEMBER_ROLES = ("accountant", "viewer")
WRITE_ROLES = ("owner", "accountant")
INVITE_TTL = timedelta(days=7)
MAX_MEMBERS = 20          # defter başına üye üst sınırı (kötüye kullanım koruması; plan bazlı sınır yok)
MAX_OPEN_INVITES = 10     # defter başına kullanılmamış, süresi dolmamış davet


class TeamError(ValueError):
    def __init__(self, message: str, code: int = 400):
        super().__init__(message)
        self.code = code


def _hash(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


# ---------------------------------------------------------------- kimlik çözümü
def resolve(token: str) -> dict | None:
    """Token → {user_id, role, account_id} veya None (geçersiz / üyelik kaldırılmış).

    `account_id` isteği yapan hesabın kimliği: sahip token'ında defterin bağlı hesabı (yoksa 0, ör. yalnızca LINE).
    """
    info = store.token_info(token)
    if not info:
        return None
    uid, acc = info["user_id"], info["account_id"]
    with tx() as con:
        if acc == 0:
            row = con.execute("SELECT account_id FROM account_ledgers WHERE user_id=?", (uid,)).fetchone()
            return {"user_id": uid, "role": "owner", "account_id": int(row["account_id"]) if row else 0}
        row = con.execute("SELECT role FROM ledger_members WHERE user_id=? AND account_id=?", (uid, acc)).fetchone()
    if not row:
        return None
    return {"user_id": uid, "role": row["role"], "account_id": acc}


def _own_ledger(con, account_id: int) -> str | None:
    row = con.execute("SELECT user_id FROM account_ledgers WHERE account_id=?", (account_id,)).fetchone()
    return row["user_id"] if row else None


# ---------------------------------------------------------------- davet
def create_invite(user_id: str, role: str) -> dict:
    if role not in MEMBER_ROLES:
        raise TeamError("役割は accountant または viewer を指定してください。")
    code = "iv_" + secrets.token_urlsafe(18)
    now = datetime.now(JST)
    expires = (now + INVITE_TTL).isoformat()
    with tx() as con:
        open_n = con.execute("SELECT COUNT(*) AS n FROM team_invites WHERE user_id=? AND used_at='' AND expires_at>?",
                             (user_id, now.isoformat())).fetchone()["n"]
        if open_n >= MAX_OPEN_INVITES:
            raise TeamError("未使用の招待コードが多すぎます。不要な招待を取り消してください。", 409)
        con.execute("INSERT INTO team_invites(code_hash,user_id,role,created_at,expires_at) VALUES(?,?,?,?,?)",
                    (_hash(code), user_id, role, now.isoformat(), expires))
    return {"code": code, "role": role, "expires_at": expires}


def list_invites(user_id: str) -> list[dict]:
    """Kullanılmamış ve süresi dolmamış davetler (kod gösterilmez; yalnızca kimlik = hash'in ilk 12 hanesi)."""
    with tx() as con:
        rows = con.execute(
            """SELECT code_hash, role, created_at, expires_at FROM team_invites
               WHERE user_id=? AND used_at='' AND expires_at>? ORDER BY created_at""",
            (user_id, datetime.now(JST).isoformat())).fetchall()
    return [{"id": r["code_hash"][:12], "role": r["role"], "created_at": r["created_at"],
             "expires_at": r["expires_at"]} for r in rows]


def revoke_invite(user_id: str, invite_id: str) -> bool:
    if not invite_id or len(invite_id) != 12 or not all(c in "0123456789abcdef" for c in invite_id):
        return False
    with tx() as con:
        cur = con.execute("UPDATE team_invites SET used_at=? WHERE user_id=? AND used_at='' AND code_hash LIKE ?",
                          ("revoked:" + store.now(), user_id, invite_id + "%"))
    return cur.rowcount > 0


def join(account_id: int, code: str) -> tuple[dict, str]:
    """Davet kodunu kullanır → (üyelik, üye oturum token'ı)."""
    if not account_id:
        raise TeamError("招待を受けるにはメールアドレスでログインしてください。", 403)
    code = (code or "").strip()
    now = datetime.now(JST).isoformat()
    with tx() as con:
        inv = con.execute("SELECT code_hash, user_id, role, expires_at, used_at FROM team_invites WHERE code_hash=?",
                          (_hash(code),)).fetchone()
        if not inv or inv["used_at"] or inv["expires_at"] <= now:
            raise TeamError("招待コードが無効か期限切れです。オーナーに新しいコードを依頼してください。", 400)
        uid = inv["user_id"]
        if _own_ledger(con, account_id) == uid:
            raise TeamError("ご自身の帳簿には参加できません。", 409)
        if con.execute("SELECT 1 FROM ledger_members WHERE user_id=? AND account_id=?", (uid, account_id)).fetchone():
            raise TeamError("すでにこの帳簿のメンバーです。", 409)
        n = con.execute("SELECT COUNT(*) AS n FROM ledger_members WHERE user_id=?", (uid,)).fetchone()["n"]
        if n >= MAX_MEMBERS:
            raise TeamError("この帳簿のメンバー数が上限に達しています。", 409)
        # Tek kullanımlık: koşullu UPDATE — eşzamanlı iki kullanımda yalnızca biri geçer
        cur = con.execute("UPDATE team_invites SET used_at=?, used_by=? WHERE code_hash=? AND used_at=''",
                          (now, account_id, inv["code_hash"]))
        if cur.rowcount != 1:
            raise TeamError("招待コードが無効か期限切れです。オーナーに新しいコードを依頼してください。", 400)
        con.execute("INSERT INTO ledger_members(user_id,account_id,role,created_at) VALUES(?,?,?,?)",
                    (uid, account_id, inv["role"], now))
    token = store.issue_token(uid, "team-member", account_id)
    return {"user_id": uid, "role": inv["role"]}, token


# ---------------------------------------------------------------- üyeler
def list_members(user_id: str) -> list[dict]:
    with tx() as con:
        rows = con.execute(
            """SELECT m.account_id, m.role, m.created_at, a.email FROM ledger_members m
               JOIN accounts a ON a.id = m.account_id WHERE m.user_id=? ORDER BY m.created_at""",
            (user_id,)).fetchall()
        owner = con.execute(
            """SELECT a.id, a.email FROM accounts a JOIN account_ledgers l ON l.account_id=a.id
               WHERE l.user_id=?""", (user_id,)).fetchone()
    out = [{"account_id": int(owner["id"]), "email": owner["email"], "role": "owner"}] if owner else []
    out += [{"account_id": int(r["account_id"]), "email": r["email"], "role": r["role"],
             "joined_at": r["created_at"]} for r in rows]
    return out


def set_role(user_id: str, account_id: int, role: str) -> dict:
    if role not in MEMBER_ROLES:
        raise TeamError("役割は accountant または viewer を指定してください。")
    with tx() as con:
        cur = con.execute("UPDATE ledger_members SET role=? WHERE user_id=? AND account_id=?",
                          (role, user_id, account_id))
    if cur.rowcount == 0:
        raise TeamError("メンバーが見つかりません。", 404)
    return {"account_id": account_id, "role": role}


def remove_member(user_id: str, account_id: int) -> None:
    """Üyeliği kaldırır ve o üyenin bu defterdeki oturumlarını kapatır."""
    with tx() as con:
        cur = con.execute("DELETE FROM ledger_members WHERE user_id=? AND account_id=?", (user_id, account_id))
        con.execute("DELETE FROM api_tokens WHERE user_id=? AND account_id=?", (user_id, account_id))
    if cur.rowcount == 0:
        raise TeamError("メンバーが見つかりません。", 404)


# ---------------------------------------------------------------- defterler arası geçiş
def ledgers_for(account_id: int) -> list[dict]:
    """Hesabın erişebildiği defterler: kendi defteri (owner) + üye olduğu defterler."""
    if not account_id:
        return []
    with tx() as con:
        own = _own_ledger(con, account_id)
        rows = con.execute(
            """SELECT m.user_id, m.role, p.business_name FROM ledger_members m
               LEFT JOIN profiles p ON p.user_id = m.user_id WHERE m.account_id=? ORDER BY m.created_at""",
            (account_id,)).fetchall()
        own_name = con.execute("SELECT business_name FROM profiles WHERE user_id=?", (own,)).fetchone() if own else None
    out = [{"user_id": own, "role": "owner", "business_name": (own_name["business_name"] if own_name else "")}] \
        if own else []
    out += [{"user_id": r["user_id"], "role": r["role"], "business_name": r["business_name"] or ""} for r in rows]
    return out


def switch(account_id: int, user_id: str) -> tuple[dict, str]:
    """Hesabı başka bir deftere geçirir → (defter + rol, yeni token). Erişim yoksa 403."""
    if not account_id:
        raise TeamError("メールアドレスでログインしてください。", 403)
    with tx() as con:
        if _own_ledger(con, account_id) == user_id:
            role, tok_acc = "owner", 0
        else:
            row = con.execute("SELECT role FROM ledger_members WHERE user_id=? AND account_id=?",
                              (user_id, account_id)).fetchone()
            if not row:
                raise TeamError("この帳簿へのアクセス権がありません。", 403)
            role, tok_acc = row["role"], account_id
    return {"user_id": user_id, "role": role}, store.issue_token(user_id, "web-login" if role == "owner"
                                                                  else "team-member", tok_acc)
