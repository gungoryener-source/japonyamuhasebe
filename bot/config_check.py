"""T-078: canlıya alma öncesi yapılandırma kontrolü (`GET /admin/config-check`).

Her ortam değişkeni için YALNIZCA "girildi mi" (true/false) ve ilgili QUESTIONS numarası döner.
Değer, uzunluk, önek, maske — hiçbiri yanıtta yer almaz (sır sızıntısı riski sıfır olmalı).
Panel (jsaas-panel, statik site) değişkenleri bu sunucudan görünmez; onlar için docs/GO_LIVE.md.

`required`: ilk gerçek kullanıcıdan önce girilmesi gerekenler (docs/GO_LIVE.md sırası).
`recommended`: özellik açar ama yoksa sistem çalışır. `optional`: ertelenen kanal / isteğe bağlı.
"""
from __future__ import annotations

import os

# (ad, Q numarası, düzey) — düzey: required | recommended | optional
VARS: tuple[tuple[str, str | None, str], ...] = (
    ("LINE_CHANNEL_SECRET", "Q-01", "required"),
    ("LINE_CHANNEL_ACCESS_TOKEN", "Q-01", "required"),
    ("ADMIN_KEY", None, "required"),
    ("DATABASE_URL", "Q-07", "required"),
    ("PANEL_URL", "Q-05", "required"),
    ("STORAGE_ENDPOINT", "Q-14", "required"),
    ("STORAGE_BUCKET", "Q-14", "required"),
    ("STORAGE_ACCESS_KEY", "Q-14", "required"),
    ("STORAGE_SECRET_KEY", "Q-14", "required"),
    ("MAIL_PROVIDER", "Q-13", "required"),
    ("MAIL_API_KEY", "Q-13", "required"),
    ("MAIL_FROM", "Q-13", "required"),
    ("STRIPE_SECRET_KEY", "Q-10", "required"),
    ("STRIPE_WEBHOOK_SECRET", "Q-10", "required"),
    ("STRIPE_PRICE_PERSONAL", "Q-10", "required"),
    ("STRIPE_PRICE_BUSINESS", "Q-10", "required"),
    ("ANTHROPIC_API_KEY", "Q-02", "recommended"),  # 仕切書・通帳 AI 読み取り
    ("NTA_APP_ID", "Q-20", "recommended"),         # 登録番号 確認
    ("NTA_INVOICE_APP_ID", "Q-20", "optional"),    # NTA_APP_ID ile aynıysa gereksiz
    ("WHATSAPP_VERIFY_TOKEN", "Q-06", "optional"),
    ("WHATSAPP_APP_SECRET", "Q-06", "optional"),
    ("WHATSAPP_TOKEN", "Q-06", "optional"),
    ("WHATSAPP_PHONE_ID", "Q-06", "optional"),
)


def _set(name: str) -> bool:
    return bool(os.environ.get(name, "").strip())


def report() -> dict:
    """Yalnızca bool / sabit etiket döndürür; hiçbir ortam değişkeni değeri yanıta kopyalanmaz."""
    import receipt_ocr
    import storage
    import store

    env = [{"name": n, "set": _set(n), "question": q, "level": lvl} for n, q, lvl in VARS]
    missing_required = [e["name"] for e in env if e["level"] == "required" and not e["set"]]
    missing_questions = sorted({e["question"] for e in env
                                if e["level"] == "required" and not e["set"] and e["question"]})
    return {
        "ready": not missing_required,
        "missing_required": missing_required,
        "open_questions": missing_questions,
        "env": env,
        "runtime": {
            "db": "postgres" if store.is_pg() else "sqlite",
            "storage": "s3" if storage.backend() == "s3" else "local",
            "tesseract": bool(receipt_ocr.available()),
            # sabit küçük bir küme; kullanıcı değerini değil yalnızca bilinen etiketi döndür
            "mail_provider_supported": os.environ.get("MAIL_PROVIDER", "").strip().lower() == "resend",
        },
    }

