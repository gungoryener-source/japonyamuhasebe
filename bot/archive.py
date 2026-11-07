"""全データ ZIP（T-046）— 帳簿の全期間の仕訳・請求書を 1 ファイルにまとめる。

内容:
- entries.csv   全期間の仕訳（freee 取込形式と同じ列。UTF-8 BOM 付き＝文字化け・欠落なし）
- invoices.csv  請求書の一覧（明細は JSON 列）
- invoices/<番号>.pdf  各請求書の PDF
- README.txt    内容説明と作成日時（JST）

件数の上限なし（T-027: `entries_in_range` のキーセット読み込み）。ZIP はメモリ上で作る。
"""
from __future__ import annotations

import csv
import io
import json
import re
import zipfile

import export
import invoices as inv_mod
import store

ALL_FROM, ALL_TO = "0000-01-01", "9999-12-31"
INVOICE_COLUMNS = ["請求書番号", "取引先", "発行日", "支払期限", "10%対象（税抜）", "消費税10%",
                   "8%対象（税抜）", "消費税8%", "合計（税込）", "状態", "入金日", "明細(JSON)"]
_SAFE = re.compile(r"[^0-9A-Za-z._-]")
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def _cell(v: str) -> str:
    """CSV 数式インジェクション対策: 表計算ソフトで式と解釈される先頭文字に ' を付ける（review）。"""
    return "'" + v if isinstance(v, str) and v.startswith(_FORMULA_START) else v


def _bom(text: str) -> bytes:
    return ("﻿" + text).encode("utf-8")


def invoices_csv(invs: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(INVOICE_COLUMNS)
    for i in invs:
        w.writerow([i["no"], _cell(i["client"]), i["issued"], i["due"], i["subtotal10"], i["tax10"],
                    i["subtotal8"], i["tax8"], i["total"], "入金済" if i["status"] == "paid" else "未入金",
                    i.get("paid_on") or "", json.dumps(i["items"], ensure_ascii=False)])
    return buf.getvalue()


def pdf_name(no: str) -> str:
    """ZIP 内パス用に番号を無害化（パス区切り・`..` を通さない）。"""
    safe = _SAFE.sub("_", no).lstrip(".") or "invoice"
    return f"invoices/{safe}.pdf"


def readme(created: str, n_entries: int, n_invoices: int) -> str:
    return "\r\n".join([
        "てがる会計 — 全データのエクスポート",
        f"作成日時: {created}（日本時間）",
        "",
        f"entries.csv   仕訳 {n_entries} 件（全期間・freee 取込形式の列、UTF-8）",
        f"invoices.csv  請求書 {n_invoices} 件（明細は JSON 列）",
        "invoices/     各請求書の PDF",
        "",
        "会計ソフトへ取り込む場合は、パネルの「確定申告 / 税務」ページの CSV 出力（Shift_JIS）もご利用ください。",
        "帳簿・請求書は法定の保存期間にわたり保存が必要です。このファイルは安全な場所に保管してください。",
        "",
    ])


def build_zip(user_id: str) -> bytes:
    rows = store.entries_in_range(user_id, ALL_FROM, ALL_TO)
    invs = sorted(store.list_invoices(user_id), key=lambda i: (i["issued"], i["no"]))
    profile = store.get_profile(user_id)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("README.txt", _bom(readme(store.now(), len(rows), len(invs))))
        z.writestr("entries.csv", _bom(export.to_csv(rows, "freee")))
        z.writestr("invoices.csv", _bom(invoices_csv(invs)))
        used: set[str] = set()
        for inv in invs:
            name, n = pdf_name(inv["no"]), 2
            while name in used:  # 無害化で衝突した場合
                name = pdf_name(f"{inv['no']}-{n}"); n += 1
            used.add(name)
            z.writestr(name, inv_mod.render_pdf(inv, profile))
    return buf.getvalue()
