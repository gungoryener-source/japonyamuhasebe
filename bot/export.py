"""会計ソフト向け CSV 出力（freee / マネーフォワード / 弥生）。

T-012b（2026-11-07 確認）:
- 弥生: 公式「仕訳データの項目と記述形式」25項目（識別フラグ〜調整）に準拠。税区分は公式の記述
  （課税売上込10% / 課税売上込軽減8% / 課対仕入込10% / 課対仕入込軽減8% / 非課売上 / 対象外）、
  インボイスは末尾に「適格」または「区分80%」等（経過措置の控除割合）を付ける。
  https://support.yayoi-kk.co.jp/subcontents.html?page_id=18545 , page_id=18111
  ※ 見出し行の要否は公式に記載なし → 弥生のテンプレート慣行に合わせ見出し行なし。
- freee: 公式「取引インポート」21列（収支区分〜決済金額）に準拠、日付 YYYY/MM/DD、見出し行あり。
  決済（決済日・決済口座）は freee 側の口座名と一致が必要なため空欄（未決済として取込）。
  https://support.freee.co.jp/hc/ja/articles/202847320
  ※ freee の税区分ラベル（課対仕入10%（控80）等）は公式一覧で未確認。
- マネーフォワード（T-012c, 2026-11-08 確認）: 公式「仕訳帳インポート（マネーフォワード クラウド会計形式）」
  27列（取引No〜最終更新者、更新日 2026-07-09）に準拠、取引日 yyyy/MM/dd、1行目は見出し。
  税区分は公式「税区分一覧」の正式名称（課税売上 10% / 課税売上 (軽)8% / 課税仕入 10% / 課税仕入 (軽)8% /
  非課税売上 / 対象外）。インボイス列は 適格 / 80％控除 / 70％控除 / 50％控除 / 30％控除 / 控除なし
  （取引日で決まり、`tax.consumption.input_credit_ratio` と同じ境界日）。空欄は「適格」扱いのため、
  仕入以外とインボイス制度前の仕入は空欄。税額列は公式指示どおり空欄。登録番号は仕訳メモへ。
  文字数上限: 勘定科目30・取引先255・摘要/仕訳メモ200。
  https://biz.moneyforward.com/support/account/guide/import-books/ib01.html
  https://biz.moneyforward.com/support/account/faq/service/s15.html (税区分一覧)
  https://biz.moneyforward.com/support/account/faq/service/tax-class02.html (対象外)
- 相手科目: 銀行明細から記帳したもの（source=BANK）は「普通預金」、それ以外の経費は「事業主借」、売上は「普通預金」。
- 受取利息（税率0）は「非課売上」、その他の税率0は「対象外」。
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
        return {"freee": f"課税売上{r}%", "yayoi": f"課税売上込{r}%"}[fmt] + ("（軽）" if r == 8 and fmt != "freee" else "")
    qualified = bool(e.get("invoice_no"))
    if fmt == "freee":
        return f"課対仕入{r}%" + ("" if qualified else "（控80）" if e["d"] < "2026-10-01" else "（控70）")
    return f"課対仕入込{r}%" + ("" if qualified else "適格外")


def _counter(e: dict) -> str:
    if (e.get("source") or "").startswith("BANK") or e["kind"] == "inc":
        return "普通預金"
    return "事業主借"


def _yayoi_tax(e: dict) -> str:
    r = e["rate"]
    if r == 0:
        return "非課売上" if e["category"] == "受取利息" else "対象外"
    rate = "軽減8%" if r == 8 else f"{r}%"
    if e["kind"] == "inc":
        return f"課税売上込{rate}"
    from datetime import date as _date

    from tax.consumption import input_credit_ratio
    if e.get("invoice_no"):
        return f"課対仕入込{rate}適格"
    pct = input_credit_ratio(_date.fromisoformat(e["d"]), False)
    return f"課対仕入込{rate}区分{pct}%" if pct else f"課対仕入込{rate}区分控不"


MF_HEADER = ["取引No", "取引日", "借方勘定科目", "借方補助科目", "借方部門", "借方取引先", "借方税区分", "借方インボイス",
             "借方金額(円)", "借方税額", "貸方勘定科目", "貸方補助科目", "貸方部門", "貸方取引先", "貸方税区分",
             "貸方インボイス", "貸方金額(円)", "貸方税額", "摘要", "仕訳メモ", "タグ", "MF仕訳タイプ", "決算整理仕訳",
             "作成日時", "作成者", "最終更新日時", "最終更新者"]
MF_INVOICE = {80: "80％控除", 70: "70％控除", 50: "50％控除", 30: "30％控除", 0: "控除なし"}


def _mf_tax(e: dict) -> str:
    r = e["rate"]
    if r == 0:
        return "非課税売上" if e["category"] == "受取利息" else "対象外"
    side = "売上" if e["kind"] == "inc" else "仕入"
    return f"課税{side} (軽)8%" if r == 8 else f"課税{side} {r}%"


def _mf_invoice(e: dict) -> str:
    """仕入側のインボイス区分。空欄は MF で「適格」扱い。"""
    if e["kind"] == "inc" or e["rate"] == 0:
        return ""
    if e.get("invoice_no"):
        return "適格"
    from datetime import date as _date

    from tax.consumption import input_credit_ratio
    pct = input_credit_ratio(_date.fromisoformat(e["d"]), False)
    return MF_INVOICE.get(pct, "")  # 100 = インボイス制度前 → 空欄


def _mf_row(no: int, e: dict) -> list:
    d, amt = e["d"].replace("-", "/"), e["amount"]
    partner = str(e["store"])[:255]
    cat, other = str(e["category"])[:30], _counter(e)
    memo = f"登録番号 {e['invoice_no']}"[:200] if e.get("invoice_no") else ""
    if e["kind"] == "inc":
        debit = [other, "", "", "", "対象外", "", amt, ""]
        credit = [cat, "", "", partner, _mf_tax(e), "", amt, ""]
    else:
        debit = [cat, "", "", partner, _mf_tax(e), _mf_invoice(e), amt, ""]
        credit = [other, "", "", "", "対象外", "", amt, ""]
    return [no, d, *debit, *credit, partner[:200], memo, "", "", "", "", "", "", ""]


def _freee_tax(e: dict) -> str:
    if e["rate"] == 0:
        return "非課売上" if e["category"] == "受取利息" else "対象外"
    return _tax_label(e, "freee")


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
        w.writerow(["収支区分", "管理番号", "発生日", "決済期日", "取引先コード", "取引先", "勘定科目", "税区分", "金額",
                    "税計算区分", "税額", "備考", "品目", "部門", "メモタグ",
                    "決済日", "決済口座", "決済金額"])
        for e in entries:
            w.writerow(["収入" if e["kind"] == "inc" else "支出", "", e["d"].replace("-", "/"), "", "", e["store"],
                        e["category"], _freee_tax(e), e["amount"], "", "", e.get("invoice_no", ""), "", "", "",
                        "", "", ""])
    elif fmt == "mf":  # T-012c: 公式27列
        w.writerow(MF_HEADER)
        for i, e in enumerate(entries, 1):
            w.writerow(_mf_row(i, e))
    else:  # yayoi: 25項目・見出しなし・タイプ0（仕訳）・調整 no
        for e in entries:
            d = e["d"].replace("-", "/")
            memo = (e.get("invoice_no") or "")[:180]
            tax, other, amt = _yayoi_tax(e), _counter(e), e["amount"]
            if e["kind"] == "inc":
                debit, dtax, credit, ctax = other, "対象外", e["category"], tax
            else:
                debit, dtax, credit, ctax = e["category"], tax, other, "対象外"
            w.writerow([2000, "", "", d, debit, "", "", dtax, amt, "", credit, "", "", ctax, amt, "",
                        str(e["store"])[:64], "", "", 0, "", memo, "", "", "no"])
    return buf.getvalue()
