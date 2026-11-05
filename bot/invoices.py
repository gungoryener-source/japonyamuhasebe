"""適格請求書（インボイス）の計算と PDF 出力。docs/TAX_RULES.md §4

記載事項: 発行者名・登録番号 / 取引年月日 / 取引内容（軽減税率対象の明示）/
税率ごとの対価の合計と適用税率 / 税率ごとの消費税額 / 交付先名。
端数処理は「税率ごとに1回」（税抜合計 × 税率、切捨て）。
"""
from __future__ import annotations

import io
import os
from dataclasses import dataclass

RATES = (10, 8)


@dataclass(frozen=True)
class Totals:
    subtotal10: int
    subtotal8: int
    tax10: int
    tax8: int

    @property
    def total(self) -> int:
        return self.subtotal10 + self.subtotal8 + self.tax10 + self.tax8


def validate_items(items: list[dict]) -> list[dict]:
    """items: [{"name": str, "qty": int, "unit_price": int (税抜), "rate": 10|8}]"""
    if not items:
        raise ValueError("at least one item is required")
    out = []
    for it in items:
        name = str(it.get("name", "")).strip()
        qty = int(it.get("qty", 1))
        price = int(it.get("unit_price", 0))
        rate = int(it.get("rate", 10))
        if not name:
            raise ValueError("item name is required")
        if qty <= 0 or price < 0:
            raise ValueError("qty must be > 0 and unit_price >= 0")
        if rate not in RATES:
            raise ValueError("rate must be 10 or 8")
        out.append({"name": name, "qty": qty, "unit_price": price, "rate": rate, "amount": qty * price})
    return out


def compute_totals(items: list[dict]) -> Totals:
    sub = {r: sum(i["amount"] for i in items if i["rate"] == r) for r in RATES}
    return Totals(sub[10], sub[8], sub[10] * 10 // 100, sub[8] * 8 // 100)


FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "ipag.ttf")  # IPAゴシック（IPAフォントライセンス）


def _register_font(pdfmetrics, UnicodeCIDFont) -> str:
    """IPAゴシックをサブセット埋め込み（どのビューアでも表示可能）。無ければ CID フォントにフォールバック。"""
    if os.path.exists(FONT_PATH):
        from reportlab.pdfbase.ttfonts import TTFont
        try:
            pdfmetrics.getFont("IPAGothic")
        except KeyError:
            pdfmetrics.registerFont(TTFont("IPAGothic", FONT_PATH))
        return "IPAGothic"
    try:
        pdfmetrics.getFont("HeiseiKakuGo-W5")
    except KeyError:
        pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
    return "HeiseiKakuGo-W5"


def render_pdf(inv: dict, issuer: dict) -> bytes:
    """請求書 PDF（A4）。"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfgen import canvas

    font = _register_font(pdfmetrics, UnicodeCIDFont)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"請求書 {inv['no']}")
    W, H = A4
    y = H - 25 * mm

    def text(x, yy, s, size=10, right=False):
        c.setFont(font, size)
        (c.drawRightString if right else c.drawString)(x, yy, s)

    yen = lambda n: f"¥{n:,}"  # noqa: E731
    text(20 * mm, y, "請求書", 22)
    text(W - 20 * mm, y, f"請求書番号 {inv['no']}", 9, right=True)
    text(W - 20 * mm, y - 5 * mm, f"発行日 {inv['issued']}", 9, right=True)
    y -= 18 * mm
    text(20 * mm, y, f"{inv['client']} 御中", 13)
    c.line(20 * mm, y - 2 * mm, 105 * mm, y - 2 * mm)
    # 発行者
    ix = W - 20 * mm
    text(ix, y, issuer.get("business_name") or "（事業者名未設定）", 11, right=True)
    text(ix, y - 5 * mm, f"登録番号 {issuer.get('registration_no') or '（未登録）'}", 9, right=True)
    y -= 16 * mm
    text(20 * mm, y, "ご請求金額（税込）", 10)
    text(75 * mm, y, yen(inv["total"]), 16)
    text(W - 20 * mm, y, f"お支払期限 {inv['due']}", 10, right=True)
    y -= 12 * mm

    # 明細
    cols = (20 * mm, 118 * mm, 145 * mm, 160 * mm, W - 20 * mm)
    c.setFillGray(0.93)
    c.rect(20 * mm, y - 2 * mm, W - 40 * mm, 7 * mm, stroke=0, fill=1)
    c.setFillGray(0)
    for x, h, r in zip(cols, ("品目", "数量", "単価", "税率", "金額（税抜）"), (0, 1, 1, 1, 1)):
        text(x if not r else x, y, h, 9, right=bool(r))
    y -= 8 * mm
    for it in inv["items"]:
        name = it["name"] + (" ※" if it["rate"] == 8 else "")
        text(cols[0], y, name[:40], 9)
        text(cols[1], y, f"{it['qty']:,}", 9, right=True)
        text(cols[2], y, yen(it["unit_price"]), 9, right=True)
        text(cols[3], y, f"{it['rate']}%", 9, right=True)
        text(cols[4], y, yen(it["amount"]), 9, right=True)
        c.setStrokeGray(0.85)
        c.line(20 * mm, y - 2 * mm, W - 20 * mm, y - 2 * mm)
        y -= 7 * mm
        if y < 60 * mm:
            c.showPage()
            y = H - 25 * mm
    c.setStrokeGray(0)
    y -= 4 * mm
    # 税率ごとの集計（適格請求書の必須記載）
    rows = []
    if inv["subtotal10"]:
        rows.append(("10%対象", inv["subtotal10"], "消費税（10%）", inv["tax10"]))
    if inv["subtotal8"]:
        rows.append(("8%対象（軽減税率）", inv["subtotal8"], "消費税（8%）", inv["tax8"]))
    for label, sub, tl, tax in rows:
        text(98 * mm, y, label, 9)
        text(142 * mm, y, yen(sub), 9, right=True)
        text(148 * mm, y, tl, 9)
        text(W - 20 * mm, y, yen(tax), 9, right=True)
        y -= 6 * mm
    c.line(98 * mm, y + 2 * mm, W - 20 * mm, y + 2 * mm)
    text(98 * mm, y - 2 * mm, "合計（税込）", 11)
    text(W - 20 * mm, y - 2 * mm, yen(inv["total"]), 11, right=True)
    if inv["subtotal8"]:
        text(20 * mm, 30 * mm, "※ は軽減税率（8%）対象品目です。", 8)
    c.showPage()
    c.save()
    return buf.getvalue()
