"""会計ソフト向け CSV 出力（freee / マネーフォワード / 弥生）。

各社の取込フォーマットは版により列が増減するため、ここでは各社が案内する
「仕訳（取引）インポート」の基本列に合わせた簡易版を出力する。
本番前に各ソフトの最新テンプレートで取込検証すること（BACKLOG T-012b）。
"""
from __future__ import annotations

import csv
import io

FORMATS = ("freee", "mf", "yayoi")
FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def csv_cell(v):
    """CSV 数式インジェクション対策: 表計算ソフトで式と解釈される先頭文字の文字列に ' を付ける。

    文字列以外（金額などの int）はそのまま返す。
    """
    return "'" + v if isinstance(v, str) and v.startswith(FORMULA_START) else v


def _tax_label(e: dict, fmt: str) -> str:
    r = e["rate"]
    if r == 0:
        return "対象外"
    if e["kind"] == "inc":
        return {"freee": f"課税売上{r}%", "mf": f"課税売上 {r}%", "yayoi": f"課税売上込{r}%"}[fmt] + ("（軽）" if r == 8 and fmt != "freee" else "")
    qualified = bool(e.get("invoice_no"))
    if fmt == "freee":
        return f"課対仕入{r}%" + ("" if qualified else "（控80）" if e["d"] < "2026-10-01" else "（控70）")
    if fmt == "mf":
        return f"課税仕入 {r}%" + ("" if qualified else " 経過措置")
    return f"課対仕入込{r}%" + ("" if qualified else "適格外")


def to_csv(entries: list[dict], fmt: str, *, escape_formulas: bool = False) -> str:
    """仕訳を CSV にする。

    escape_formulas=True: 取引先/摘要・勘定科目・備考（登録番号）の先頭が `=+-@`/TAB/CR なら ' を付ける
    （Excel で直接開く全データ ZIP 用。T-059）。会計ソフト取込用 `/export.csv` は、取込時に ' が
    取引先名の一部として取り込まれるかが未検証のため既定 False（QUESTIONS Q-17）。
    """
    if fmt not in FORMATS:
        raise ValueError(f"format must be one of {FORMATS}")
    if escape_formulas:
        entries = [{**e, "store": csv_cell(e["store"]), "category": csv_cell(e["category"]),
                    "invoice_no": csv_cell(e.get("invoice_no") or "")} for e in entries]
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    if fmt == "freee":
        w.writerow(["収支区分", "発生日", "取引先", "勘定科目", "税区分", "金額", "備考"])
        for e in entries:
            w.writerow(["収入" if e["kind"] == "inc" else "支出", e["d"], e["store"],
                        e["category"], _tax_label(e, fmt), e["amount"], e.get("invoice_no", "")])
    elif fmt == "mf":
        w.writerow(["取引No", "取引日", "借方勘定科目", "借方税区分", "借方金額(円)", "貸方勘定科目", "貸方税区分", "貸方金額(円)", "摘要"])
        for i, e in enumerate(entries, 1):
            if e["kind"] == "inc":
                w.writerow([i, e["d"].replace("-", "/"), "普通預金", "対象外", e["amount"], e["category"], _tax_label(e, fmt), e["amount"], e["store"]])
            else:
                w.writerow([i, e["d"].replace("-", "/"), e["category"], _tax_label(e, fmt), e["amount"], "事業主借", "対象外", e["amount"], e["store"]])
    else:  # yayoi
        w.writerow(["識別フラグ", "取引日付", "借方勘定科目", "借方税区分", "借方金額", "貸方勘定科目", "貸方税区分", "貸方金額", "摘要"])
        for e in entries:
            d = e["d"].replace("-", "/")
            if e["kind"] == "inc":
                w.writerow([2000, d, "普通預金", "対象外", e["amount"], e["category"], _tax_label(e, fmt), e["amount"], e["store"]])
            else:
                w.writerow([2000, d, e["category"], _tax_label(e, fmt), e["amount"], "事業主借", "対象外", e["amount"], e["store"]])
    return buf.getvalue()
