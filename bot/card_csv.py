"""クレジットカード利用明細 CSV を銀行明細と同じ形 (bank_tx) に変換する (T-077)。

カード会社ごとに列名が違い、一次資料で確認できた CSV 見出しはまだない（docs/CARD_CSV.md）。
そのため会社名で分岐せず、見出し行の語句で列を割り当てる:
  利用日: 利用日 / ご利用日 / 利用年月日 / ご利用年月日 / 取引日
  利用先: 利用店名 / ご利用店名 / 利用先 / ご利用先 / 加盟店 / 利用内容 / 摘要
  利用金額: 利用金額 / ご利用金額 / 利用額 / 金額 （支払金額・支払総額・手数料は使わない）
  支払日: 支払日 / お支払日 / 引落日 （あれば摘要の末尾に「(支払日 YYYY-MM-DD)」）
  支払区分: 支払区分 / 支払方法 （1回払い以外は摘要に追記）
金額は常に出金（負）。返金・取消（マイナス表記）は入金（正）として取り込む。
日付が読めない行（合計・分割/リボの注記・空行）は取り込まない。
摘要は CSV の文字をそのまま保存する（先頭の =+-@ もそのまま。書き出し時の無害化は export 側）。
"""
from __future__ import annotations

import csv
import io
import re

from bank_csv import _date, _num, decode

KEYS = {
    "date": r"^(ご?利用(年月)?日|取引日|日付)",
    "desc": r"(ご?利用店名|ご?利用先|加盟店|ご?利用内容|摘要)",
    "amount": r"^(ご?利用金額|ご?利用額|金額)",
    "pay_date": r"(お?支払(い)?日|引落日|お?引き?落とし?日)",
    "kind": r"(支払区分|支払方法|支払回数)",
}
SKIP_ROW = r"(合計|小計|ご請求|請求額|お支払(い)?金額|リボ|分割払い手数料)"


def parse(raw: bytes) -> list[dict]:
    rows = list(csv.reader(io.StringIO(decode(raw))))
    header_idx, cols = None, {}
    for i, row in enumerate(rows[:20]):
        found: dict[str, int] = {}
        for j, cell in enumerate(row):
            c = cell.strip()
            key = next((k for k, pat in KEYS.items() if k not in found and re.search(pat, c)), None)
            if key:
                found[key] = j
        if {"date", "desc", "amount"} <= found.keys():
            header_idx, cols = i, found
            break
    if header_idx is None:
        raise ValueError("ヘッダー行（利用日・利用店名・利用金額）が見つかりません")
    out: list[dict] = []
    for row in rows[header_idx + 1:]:
        get = lambda k: row[cols[k]].strip() if k in cols and cols[k] < len(row) else ""  # noqa: E731
        d = _date(get("date"))
        if not d:
            continue                     # 合計・注記・空行
        amt = _num(get("amount"))
        if not amt:
            continue
        desc = get("desc") or "(利用先なし)"
        if re.search(SKIP_ROW, desc):
            continue                     # 手数料・合計などの注記行
        kind = get("kind")
        if kind and kind not in ("1", "1回", "1回払い", "一括", "一括払い"):
            desc += f" [{kind}]"
        pay = _date(get("pay_date"))
        if pay:
            desc += f" (支払日 {pay})"
        out.append({"d": d, "description": desc, "amount": -amt, "balance": None, "src": "card"})
    return out
