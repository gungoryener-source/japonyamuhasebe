"""Hesap sistemi (T-040): e-posta + parola, defter (ledger) bağlama, parola sıfırlama.

- Parola: `hashlib.scrypt` (stdlib), 16 bayt tuz; saklama biçimi `scrypt$n$r$p$salt_hex$hash_hex`.
- Her hesabın tek defteri vardır (`account_ledgers`). Kayıtta boş bir web defteri (`web:<rastgele>`) açılır;
  LINE 「パネル」 koduyla LINE defteri hesaba bağlanabilir (`link_ledger`).
- Oturum token'ı mevcut `api_tokens` tablosudur (defter `user_id`'sine bağlı) → tüm `/api/v1` uçları aynen çalışır.
- E-posta gönderimi soyut: `MAIL_PROVIDER` yoksa yalnızca sunucu log'una yazılır (Q-13).
Şema yalnızca ekleyici; muhasebe verisi silinmez (token/parola sıfırlama satırları muhasebe verisi değildir).
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
import secrets
from datetime import datetime, timedelta

import store
from store import JST, tx

log = logging.getLogger("accounts")

PASSWORD_MIN = 10
PASSWORD_MAX = 128
RESET_TTL = timedelta(hours=1)
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]+$")
_N, _R, _P = 2 ** 14, 8, 1

# Tablolar (accounts, account_ledgers, password_resets) store.SCHEMA içinde; init_db oluşturur.


class AccountError(ValueError):
    """Kullanıcıya gösterilebilir hata. `code` API durum kodu için."""

    def __init__(self, message: str, code: int = 400):
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------- parola
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${h.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt, h = stored.split("$")
        if algo != "scrypt":
            return False
        got = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p),
                             dklen=len(h) // 2)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(got.hex().encode(), h.encode())


_DUMMY_HASH = hash_password("dummy-password-for-timing")


def normalize_email(email: str) -> str:
    e = (email or "").strip().lower()
    if len(e) > 254 or not EMAIL_RE.match(e):
        raise AccountError("メールアドレスの形式が正しくありません。")
    return e


def check_password_policy(password: str) -> None:
    if not isinstance(password, str) or len(password) < PASSWORD_MIN:
        raise AccountError(f"パスワードは{PASSWORD_MIN}文字以上にしてください。")
    if len(password) > PASSWORD_MAX:
        raise AccountError(f"パスワードは{PASSWORD_MAX}文字以内にしてください。")


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ---------------------------------------------------------------- hesaplar
def ledger_of(account_id: int) -> str | None:
    with tx() as con:
        row = con.execute("SELECT user_id FROM account_ledgers WHERE account_id=?", (account_id,)).fetchone()
    return row["user_id"] if row else None


def account_by_id(account_id: int) -> dict | None:
    with tx() as con:
        row = con.execute("SELECT id, email, email_verified, created_at FROM accounts WHERE id=?",
                          (account_id,)).fetchone()
    return dict(row) if row else None


def account_for_ledger(user_id: str) -> dict | None:
    with tx() as con:
        row = con.execute(
            """SELECT a.id, a.email, a.email_verified, a.created_at FROM accounts a
               JOIN account_ledgers l ON l.account_id = a.id WHERE l.user_id=?""", (user_id,)).fetchone()
    return dict(row) if row else None


def _email_exists(email: str) -> bool:
    with tx() as con:
        return con.execute("SELECT 1 FROM accounts WHERE email=?", (email,)).fetchone() is not None


def signup(email: str, password: str) -> tuple[dict, str]:
    """Yeni hesap + boş web defteri. (hesap, oturum token'ı) döner."""
    email = normalize_email(email)
    check_password_policy(password)
    pw = hash_password(password)
    ledger = "web:" + secrets.token_hex(12)
    duplicate = AccountError("このメールアドレスはすでに登録されています。", 409)
    try:
        with tx() as con:
            if con.execute("SELECT 1 FROM accounts WHERE email=?", (email,)).fetchone():
                raise duplicate
            con.execute("INSERT INTO accounts(email,password_hash,email_verified,created_at) VALUES(?,?,0,?)",
                        (email, pw, store.now()))
            acc_id = con.execute("SELECT id FROM accounts WHERE email=?", (email,)).fetchone()["id"]
            con.execute("INSERT INTO account_ledgers(account_id,user_id,linked_at) VALUES(?,?,?)",
                        (acc_id, ledger, store.now()))
    except Exception as exc:
        # T-053: SELECT ile INSERT arasında aynı e-postayla eşzamanlı kayıt → UNIQUE ihlali (işlem geri alındı).
        # Yalnızca e-posta gerçekten kayıtlıysa 409; başka bütünlük hatası olduğu gibi yükselir.
        if store.is_integrity_error(exc) and _email_exists(email):
            raise duplicate from exc
        raise
    token = store.issue_token(ledger, "web-login")
    return {"id": acc_id, "email": email, "user_id": ledger}, token


def login(email: str, password: str) -> tuple[dict, str]:
    try:
        email = normalize_email(email)
    except AccountError:
        email = ""
    with tx() as con:
        row = con.execute("SELECT id, password_hash FROM accounts WHERE email=?", (email,)).fetchone()
    # Hesap yoksa da aynı süre harca (e-posta keşfini zorlaştırır)
    ok = verify_password(password or "", row["password_hash"] if row else _DUMMY_HASH)
    if not row or not ok:
        raise AccountError("メールアドレスまたはパスワードが違います。", 401)
    ledger = ledger_of(row["id"])
    return {"id": row["id"], "email": email, "user_id": ledger}, store.issue_token(ledger, "web-login")


def _ledger_has_data(con, user_id: str) -> bool:
    # subscriptions (T-042): ücretli abonelik web defterindeyse bağlama onu sahipsiz bırakırdı
    # ledger_members (T-041): ekip üyeleri boş kalan eski defterde mahsur kalmasın
    for table in ("entries", "invoices", "bank_tx", "subscriptions", "ledger_members"):
        if con.execute(f"SELECT 1 FROM {table} WHERE user_id=? LIMIT 1", (user_id,)).fetchone():
            return True
    return False


def link_ledger(current_user_id: str, code: str) -> tuple[dict, str]:
    """Oturumdaki hesabı, LINE 「パネル」 kodunun (tk_...) gösterdiği deftere bağlar.

    Veri kaybını önlemek için: mevcut web defterinde kayıt varsa veya hedef defter başka hesaba bağlıysa 409.
    Eski defterin token'ları iptal edilir; yeni defter için oturum token'ı döner.
    """
    acc = account_for_ledger(current_user_id)
    if not acc:
        raise AccountError("アカウントでログインしてください。", 403)
    # Yalnızca sahip/LINE 「パネル」 token'ı (account_id=0) bağlama kodudur; ekip üyesi oturumu (T-041)
    # kod olarak verilirse üye defterin sahibi olurdu (reviewer 2026-11-07).
    info = store.token_info((code or "").strip())
    target = info["user_id"] if info and info["account_id"] == 0 else None
    if not target:
        raise AccountError("接続コードが無効です。LINEで「パネル」と送って新しいコードを取得してください。", 400)
    if target == current_user_id:
        return {"id": acc["id"], "email": acc["email"], "user_id": target}, store.issue_token(target, "web-login")
    with tx() as con:
        other = con.execute("SELECT account_id FROM account_ledgers WHERE user_id=?", (target,)).fetchone()
        if other and other["account_id"] != acc["id"]:
            raise AccountError("このLINEの帳簿はすでに別のアカウントに連携されています。", 409)
        if _ledger_has_data(con, current_user_id):
            raise AccountError("現在の帳簿にデータがあるため連携できません。サポートにお問い合わせください。", 409)
        con.execute("UPDATE account_ledgers SET user_id=?, linked_at=? WHERE account_id=?",
                    (target, store.now(), acc["id"]))
        con.execute("DELETE FROM api_tokens WHERE user_id=?", (current_user_id,))
    # Kod tek kullanımlık: paylaşılmış olabilecek LINE kodunu iptal et
    store.revoke_token(code.strip())
    return {"id": acc["id"], "email": acc["email"], "user_id": target}, store.issue_token(target, "web-login")


# ---------------------------------------------------------------- parola sıfırlama
def send_mail(to: str, subject: str, body: str) -> None:
    """E-posta gönderimi soyutlaması. Sağlayıcı seçilene kadar (Q-13) yalnızca log."""
    provider = os.environ.get("MAIL_PROVIDER", "")
    if not provider:
        # Gövde (sıfırlama bağlantısı = parola ele geçirme anahtarı) ve tam adres üretim log'una yazılmaz.
        log.warning("MAIL_PROVIDER not set; mail to %s not sent: %s", mask_email(to), subject)
        log.debug("mail body (dev only): %s", body)
        return
    log.warning("MAIL_PROVIDER=%s is not implemented yet (Q-13); mail to %s not sent", provider, mask_email(to))


def mask_email(email: str) -> str:
    """Log için: taro@example.jp → t***@example.jp"""
    local, _, domain = (email or "").partition("@")
    return f"{local[:1]}***@{domain}" if domain else "***"


def request_password_reset(email: str) -> str | None:
    """Sıfırlama bağlantısı üretip e-postalar. Hesap yoksa sessizce None (e-posta keşfi yok)."""
    try:
        email = normalize_email(email)
    except AccountError:
        return None
    with tx() as con:
        row = con.execute("SELECT id FROM accounts WHERE email=?", (email,)).fetchone()
        if not row:
            return None
        token = "rs_" + secrets.token_urlsafe(24)
        con.execute("INSERT INTO password_resets(token_hash,account_id,expires_at,used_at) VALUES(?,?,?,'')",
                    (_hash(token), row["id"], (datetime.now(JST) + RESET_TTL).isoformat()))
    base = os.environ.get("PANEL_URL", "")
    send_mail(email, "【手軽会計】パスワード再設定",
              f"以下のリンクから1時間以内にパスワードを再設定してください。\n{base}/reset#{token}\n"
              "お心当たりのない場合はこのメールを破棄してください。")
    return token


def confirm_password_reset(token: str, new_password: str) -> None:
    check_password_policy(new_password)
    with tx() as con:
        row = con.execute("SELECT account_id, expires_at, used_at FROM password_resets WHERE token_hash=?",
                          (_hash(token or ""),)).fetchone()
        if not row or row["used_at"] or datetime.fromisoformat(row["expires_at"]) < datetime.now(JST):
            raise AccountError("再設定リンクが無効か期限切れです。もう一度お試しください。", 400)
        con.execute("UPDATE accounts SET password_hash=? WHERE id=?", (hash_password(new_password), row["account_id"]))
        # Bu hesabın kullanılmamış tüm sıfırlama bağlantıları da geçersiz (eski e-postadaki bağlantı çalışmasın)
        con.execute("UPDATE password_resets SET used_at=? WHERE account_id=? AND used_at=''",
                    (store.now(), row["account_id"]))
        led = con.execute("SELECT user_id FROM account_ledgers WHERE account_id=?", (row["account_id"],)).fetchone()
        if led:
            # Parola değişince tüm oturumları kapat
            con.execute("DELETE FROM api_tokens WHERE user_id=?", (led["user_id"],))
        # T-041: bu hesabın başka defterlerdeki üye oturumları da kapanır
        con.execute("DELETE FROM api_tokens WHERE account_id=?", (row["account_id"],))
