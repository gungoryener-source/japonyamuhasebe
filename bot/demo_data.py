"""'demo' defteri için gerçekçi örnek veri (panel denemesi ve geliştirme)."""
from datetime import date

import invoices as inv_mod
import store

MONTHS = [("2026-05", 3_420_000, 1_710_000), ("2026-06", 3_880_000, 1_950_000), ("2026-07", 3_560_000, 1_790_000),
          ("2026-08", 3_210_000, 1_840_000), ("2026-09", 3_795_000, 1_876_000), ("2026-10", 4_250_000, 1_820_000)]
CLIENTS = ["株式会社サクラ製作所", "株式会社アオイ商事", "合同会社ヒカリデザイン"]
EXPENSES = [("地代家賃", "東京シェアオフィス", 0.30, 10, "T9010001444444"), ("外注工賃", "株式会社クラウドワン", 0.40, 10, "T1011101555555"),
            ("旅費交通費", "JR東日本", 0.08, 10, "T7011001666666"), ("通信費", "楽天モバイル", 0.05, 10, "T9010001888888"),
            ("会議費", "ローソン", 0.02, 8, "T3011001000001"), ("接待交際費", "居酒屋たぬき", 0.07, 10, ""),
            ("消耗品費", "ヨドバシカメラ", 0.08, 10, "T1011101555556")]


def seed(uid: str) -> None:
    store.save_profile(uid, business_name="合同会社ミナト", registration_no="T3010001222222", individual=0)
    for ym, inc, exp in MONTHS:
        parts = [inc * 45 // 100, inc * 35 // 100]
        parts.append(inc - sum(parts))
        for i, (c, a) in enumerate(zip(CLIENTS, parts)):
            store.add_entry(uid, {"date": f"{ym}-{25 + i}", "kind": "inc", "store": c, "amount": a,
                                  "category": "売上高", "rate": 10, "invoice_no": ""}, source="DEMO")
        used = 0
        for j, (cat, shop, share, rate, inv) in enumerate(EXPENSES):
            a = exp - used if j == len(EXPENSES) - 1 else int(exp * share)
            used += a
            store.add_entry(uid, {"date": f"{ym}-{5 + j * 3:02d}", "kind": "exp", "store": shop, "amount": a,
                                  "category": cat, "rate": rate, "invoice_no": inv}, source="DEMO")
    for client, items, issued, due, paid in [
        (CLIENTS[0], [{"name": "業務システム保守（10月分）", "qty": 1, "unit_price": 1_200_000, "rate": 10}], "2026-10-31", "2026-11-30", False),
        (CLIENTS[1], [{"name": "Webサイト改修", "qty": 1, "unit_price": 900_000, "rate": 10}], "2026-10-31", "2026-11-30", False),
        ("有限会社カエデフーズ", [{"name": "試食会 弁当", "qty": 100, "unit_price": 4_000, "rate": 8}], "2026-09-30", "2026-10-31", False),
        (CLIENTS[2], [{"name": "デザイン監修", "qty": 1, "unit_price": 500_000, "rate": 10}], "2026-09-30", "2026-10-31", True),
    ]:
        items = inv_mod.validate_items(items)
        t = inv_mod.compute_totals(items)
        inv = store.insert_invoice(uid, {"no": store.next_invoice_no(uid, issued), "client": client, "issued": issued,
                                         "due": due, "items": items, "subtotal10": t.subtotal10, "subtotal8": t.subtotal8,
                                         "tax10": t.tax10, "tax8": t.tax8, "total": t.total})
        if paid:
            from contextlib import closing
            with closing(store.connect()) as con, con:  # 入金は既に売上に含まれるため帳簿へ二重計上しない
                con.execute("UPDATE invoices SET status='paid', paid_on=? WHERE user_id=? AND no=?",
                            (date(2026, 10, 30).isoformat(), uid, inv["no"]))
