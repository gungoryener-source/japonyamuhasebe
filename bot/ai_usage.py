"""AI 読み取りの利用量と概算料金（ürün sahibi isteği 2026-11-07: AI seçeneği + tahmini ücret).

- 価格は環境変数で変更できる（Anthropic の価格改定・為替に合わせる）。既定値:
  Claude Sonnet 5.5 = 入力 $2 / 出力 $10（100万トークンあたり。apidog.com/blog/claude-sonnet-5-5-pricing, 2026-11-07 確認。
  公式価格ページ https://claude.com/pricing で要確認）、1ドル = 155円。
- 画像のトークン = ⌈幅/28⌉ × ⌈高さ/28⌉（公式 Vision ドキュメント）。送信前に長辺を縮小してコストを抑える。
- 実際の利用量（API 応答の usage）を記録し、平均が取れたら概算に使う。
"""
from __future__ import annotations

import contextvars
import io
import math
import os
from datetime import datetime

import store

current_user: contextvars.ContextVar[str] = contextvars.ContextVar("ai_user", default="")

KINDS = ("receipt", "slip", "passbook")
# 送信前の長辺（px）。レシートは印字、仕切書は手書きのため少し大きめ。
MAX_EDGE = {"receipt": 1600, "slip": 2000}
# 概算用の想定（記録がないとき）: プロンプト文字・出力トークン・1枚の画像サイズ（縮小後）
ASSUME = {
    "receipt": {"prompt": 500, "output": 250, "image": (1200, 1600)},
    "slip": {"prompt": 650, "output": 600, "image": (1500, 2000)},
    "passbook": {"prompt": 650, "output": 1100, "image": (1600, 1150)},   # 1ページ（見開き片面）
}


def price_in() -> float:
    return float(os.environ.get("AI_PRICE_INPUT_USD_PER_MTOK", "2"))


def price_out() -> float:
    return float(os.environ.get("AI_PRICE_OUTPUT_USD_PER_MTOK", "10"))


def usd_jpy() -> float:
    return float(os.environ.get("USD_JPY", "155"))


def image_tokens(w: int, h: int) -> int:
    return math.ceil(w / 28) * math.ceil(h / 28)


def cost_jpy(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens * price_in() + output_tokens * price_out()) / 1_000_000 * usd_jpy()


def assumed_jpy(kind: str) -> float:
    a = ASSUME[kind]
    return cost_jpy(a["prompt"] + image_tokens(*a["image"]), a["output"])


def shrink(img: bytes, kind: str) -> bytes:
    """長辺を MAX_EDGE に縮小した JPEG（コスト削減）。読めない画像はそのまま返す。"""
    edge = MAX_EDGE.get(kind)
    if not edge or img[:5] == b"%PDF-":
        return img
    try:
        from PIL import Image, ImageOps

        im = ImageOps.exif_transpose(Image.open(io.BytesIO(img)))
        if max(im.size) <= edge:
            return img
        im.thumbnail((edge, edge))
        buf = io.BytesIO()
        im.convert("RGB").save(buf, "JPEG", quality=85)
        return buf.getvalue()
    except Exception:  # noqa: BLE001
        return img


def record(kind: str, usage: dict | None, units: int = 1, user_id: str = "") -> None:
    """API 応答の usage（input_tokens / output_tokens）を記録。units = 枚数（通帳はページ数）。"""
    uid = user_id or current_user.get()
    if not uid or not usage:
        return
    it, ot = int(usage.get("input_tokens") or 0), int(usage.get("output_tokens") or 0)
    try:
        with store.tx() as con:
            con.execute("""INSERT INTO ai_usage(user_id,kind,units,input_tokens,output_tokens,cost_jpy,created_at)
                           VALUES(?,?,?,?,?,?,?)""",
                        (uid, kind, max(1, units), it, ot, round(cost_jpy(it, ot), 2), store.now()))
    except Exception as ex:  # noqa: BLE001  記録失敗で読み取りを止めない
        print("ai_usage record error", type(ex).__name__)


def per_unit_jpy(user_id: str = "") -> dict[str, dict]:
    """1枚（1ページ）あたりの概算。全利用者の直近の実績が5件以上あれば実績平均、なければ想定値。"""
    out = {}
    with store.tx() as con:
        for k in KINDS:
            r = con.execute("""SELECT COUNT(*) AS n, SUM(input_tokens) AS it, SUM(output_tokens) AS ot, SUM(units) AS u
                               FROM (SELECT * FROM ai_usage WHERE kind=? ORDER BY id DESC LIMIT 200) t""", (k,)).fetchone()
            n = int(r["n"] or 0)
            if n >= 5 and r["u"]:
                out[k] = {"jpy": round(cost_jpy(int(r["it"]), int(r["ot"])) / int(r["u"]), 1), "basis": "measured", "samples": n}
            else:
                out[k] = {"jpy": round(assumed_jpy(k), 1), "basis": "estimate", "samples": n}
    return out


def month_summary(user_id: str) -> dict:
    start = datetime.now(store.JST).strftime("%Y-%m-01")
    with store.tx() as con:
        rows = con.execute("""SELECT kind, COUNT(*) AS n, SUM(units) AS u, SUM(cost_jpy) AS c FROM ai_usage
                              WHERE user_id=? AND created_at>=? GROUP BY kind""", (user_id, start)).fetchall()
    by = {r["kind"]: {"count": int(r["u"] or 0), "jpy": round(float(r["c"] or 0), 1)} for r in rows}
    return {"by_kind": by, "total_jpy": round(sum(v["jpy"] for v in by.values()), 1)}


def prices() -> dict:
    return {"input_usd_per_mtok": price_in(), "output_usd_per_mtok": price_out(), "usd_jpy": usd_jpy(),
            "model": os.environ.get("OCR_MODEL", "claude-sonnet-5-5")}
