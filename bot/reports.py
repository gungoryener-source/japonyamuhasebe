"""青色申告決算書（一般用）損益計算書の参考資料 PDF（T-045）。

公式様式ではなく、決算書へ転記するための集計表。科目は様式の固定科目順に並べ、
様式にない科目（会議費・新聞図書費・支払手数料・広告以外の任意科目）は空欄行（㉕〜㉚）に入れる。
金額は税込経理（帳簿の税込金額）。青色申告特別控除額は利用者が選んだ値を表示するだけで判定はしない。
"""
from __future__ import annotations

import io

from invoices import _register_font

# 損益計算書の固定科目（様式の番号順）
FIXED = [
    ("⑧", "租税公課"), ("⑨", "荷造運賃"), ("⑩", "水道光熱費"), ("⑪", "旅費交通費"), ("⑫", "通信費"),
    ("⑬", "広告宣伝費"), ("⑭", "接待交際費"), ("⑮", "損害保険料"), ("⑯", "修繕費"), ("⑰", "消耗品費"),
    ("⑱", "減価償却費"), ("⑲", "福利厚生費"), ("⑳", "給料賃金"), ("㉑", "外注工賃"), ("㉒", "利子割引料"),
    ("㉓", "地代家賃"), ("㉔", "貸倒金"),
]
FREE_SLOTS = ["㉕", "㉖", "㉗", "㉘", "㉙", "㉚"]
MISC = ("㉛", "雑費")


def layout_expenses(by_cat: dict[str, int]) -> list[tuple[str, str, int]]:
    """(番号, 科目, 金額) の行。固定科目 → 任意科目（空欄行、金額の大きい順）→ 雑費。
    空欄行が足りない場合、残りは雑費に合算する。"""
    rest = dict(by_cat)
    rows = [(no, name, rest.pop(name, 0)) for no, name in FIXED]
    misc = rest.pop(MISC[1], 0)
    extra = sorted(rest.items(), key=lambda kv: -kv[1])
    for i, slot in enumerate(FREE_SLOTS):
        if i < len(extra):
            rows.append((slot, extra[i][0], extra[i][1]))
        else:
            rows.append((slot, "", 0))
    misc += sum(v for _, v in extra[len(FREE_SLOTS):])
    rows.append((MISC[0], MISC[1], misc))
    return rows


def monthly(entries: list[dict]) -> list[tuple[int, int, int]]:
    """(月, 売上, 経費) × 12。"""
    out = {m: [0, 0] for m in range(1, 13)}
    for r in entries:
        m = int(str(r["d"] if "d" in r else r["date"])[5:7])
        out[m][0 if r["kind"] == "inc" else 1] += int(r["amount"])
    return [(m, v[0], v[1]) for m, v in out.items()]


def render_blue_return_pdf(year: int, pl: dict, entries: list[dict], profile: dict, blue: int) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfgen import canvas

    font = _register_font(pdfmetrics, UnicodeCIDFont)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"青色申告決算書（損益計算書）参考資料 {year}年分")
    W, H = A4
    L, R = 20 * mm, W - 20 * mm
    yen = lambda n: f"{n:,}"  # noqa: E731

    def text(x, y, s, size=9.5, right=False):
        c.setFont(font, size)
        (c.drawRightString if right else c.drawString)(x, y, s)

    # ---- 1 ページ目: 損益計算書
    y = H - 22 * mm
    text(L, y, f"令和{year - 2018}年分　青色申告決算書（一般用）損益計算書", 14)
    text(R, y, f"{year}年1月1日〜12月31日", 9, right=True)
    y -= 7 * mm
    text(L, y, f"事業者名　{profile.get('business_name') or '（未設定）'}", 10)
    text(R, y, f"登録番号　{profile.get('registration_no') or '—'}", 9, right=True)
    y -= 5 * mm
    c.setFillColorRGB(0.75, 0.1, 0.1)
    text(L, y, "※ 転記用の参考資料です（公式様式ではありません）。金額は税込経理による集計です。", 8.5)
    c.setFillColorRGB(0, 0, 0)
    y -= 8 * mm

    def row(no, label, amount, bold=False, shade=False):
        nonlocal y
        if shade:
            c.setFillGray(0.93)
            c.rect(L, y - 1.8 * mm, R - L, 6 * mm, stroke=0, fill=1)
            c.setFillGray(0)
        size = 10 if bold else 9.5
        text(L + 2 * mm, y, no, size)
        text(L + 12 * mm, y, label, size)
        text(R - 2 * mm, y, yen(amount) if (amount or label) else "", size, right=True)
        c.setStrokeGray(0.85)
        c.line(L, y - 2 * mm, R, y - 2 * mm)
        y -= 6.2 * mm

    revenue = int(pl["revenue"])
    row("①", "売上（収入）金額（雑収入を含む）", revenue, bold=True, shade=True)
    row("⑦", "差引金額（①−⑥）　※売上原価は計上していません", revenue)
    y -= 1.5 * mm
    text(L, y, "経費", 10)
    y -= 5.5 * mm
    by_cat = {e["category"]: int(e["amount"]) for e in pl["expenses"]}
    for no, name, amt in layout_expenses(by_cat):
        row(no, name, amt)
    total = int(pl["expenses_total"])
    row("㉜", "計", total, bold=True, shade=True)
    diff = revenue - total
    row("㉝", "差引金額（⑦−㉜）", diff, bold=True)
    row("㊸", "青色申告特別控除前の所得金額", diff, bold=True, shade=True)
    blue_used = max(0, min(blue, diff))
    row("㊹", f"青色申告特別控除額（選択: {blue:,}円）", blue_used)
    row("㊺", "所得金額（㊸−㊹）", diff - blue_used, bold=True, shade=True)
    y -= 3 * mm
    for line in (
        "・繰戻額・繰入額（貸倒引当金等）、専従者給与、売上原価（棚卸）は含みません。該当する場合は決算書で調整してください。",
        "・青色申告特別控除は、65万円は e-Tax 提出等、55万円は複式簿記等、10万円は簡易簿記の要件があります。",
        "・番号は青色申告決算書（一般用）の損益計算書の欄に対応しています。提出前に税理士等にご確認ください。",
    ):
        text(L, y, line, 7.8)
        y -= 4.3 * mm

    # ---- 2 ページ目: 月別売上・経費
    c.showPage()
    y = H - 22 * mm
    text(L, y, f"{year}年分　月別売上（収入）金額・経費", 14)
    y -= 10 * mm
    cols = (L + 2 * mm, L + 60 * mm, L + 110 * mm)
    c.setFillGray(0.93)
    c.rect(L, y - 2 * mm, R - L, 7 * mm, stroke=0, fill=1)
    c.setFillGray(0)
    text(cols[0], y, "月", 10)
    text(cols[1], y, "売上（収入）金額", 10, right=True)
    text(cols[2], y, "経費", 10, right=True)
    y -= 7 * mm
    s_tot = e_tot = 0
    for m, s, e in monthly(entries):
        text(cols[0], y, f"{m}月")
        text(cols[1], y, yen(s), right=True)
        text(cols[2], y, yen(e), right=True)
        c.setStrokeGray(0.85)
        c.line(L, y - 2 * mm, cols[2] + 5 * mm, y - 2 * mm)
        s_tot += s
        e_tot += e
        y -= 6.2 * mm
    text(cols[0], y, "計", 10)
    text(cols[1], y, yen(s_tot), 10, right=True)
    text(cols[2], y, yen(e_tot), 10, right=True)
    y -= 12 * mm
    text(L, y, "作成: てがる会計（J-SaaS 会計）", 8)
    c.save()
    return buf.getvalue()
