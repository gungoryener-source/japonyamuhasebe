"""T-012c: マネーフォワード クラウド会計 仕訳帳インポート形式（公式27列）。"""
import csv
import io

import pytest

import export


def rows(entries, **kw):
    return list(csv.reader(io.StringIO(export.to_csv(entries, "mf", **kw))))


def col(row, name):
    return row[export.MF_HEADER.index(name)]


def exp(**kw):
    base = {"d": "2026-10-15", "kind": "exp", "store": "文具店", "amount": 1100, "category": "消耗品費",
            "rate": 10, "invoice_no": "T7011001666666", "source": "LINE"}
    return {**base, **kw}


def test_header_is_official_27_columns():
    r = rows([])
    assert r == [export.MF_HEADER] and len(r[0]) == 27
    assert r[0][:9] == ["取引No", "取引日", "借方勘定科目", "借方補助科目", "借方部門", "借方取引先", "借方税区分",
                        "借方インボイス", "借方金額(円)"]
    assert r[0][-4:] == ["作成日時", "作成者", "最終更新日時", "最終更新者"]


def test_expense_row_layout():
    _, row = rows([exp()])
    assert len(row) == 27
    assert row[0] == "1" and col(row, "取引日") == "2026/10/15"
    assert col(row, "借方勘定科目") == "消耗品費" and col(row, "借方取引先") == "文具店"
    assert col(row, "借方税区分") == "課税仕入 10%" and col(row, "借方インボイス") == "適格"
    assert col(row, "借方金額(円)") == "1100" and col(row, "貸方金額(円)") == "1100"
    assert col(row, "貸方勘定科目") == "事業主借" and col(row, "貸方税区分") == "対象外"
    assert col(row, "貸方インボイス") == "" and col(row, "借方税額") == "" and col(row, "貸方税額") == ""
    assert col(row, "摘要") == "文具店" and col(row, "仕訳メモ") == "登録番号 T7011001666666"
    assert col(row, "MF仕訳タイプ") == ""  # 空欄 → MF が「インポート」を付与


def test_income_row_layout():
    _, row = rows([exp(kind="inc", store="A社", amount=5500, category="売上高", invoice_no="")])
    assert col(row, "借方勘定科目") == "普通預金" and col(row, "借方税区分") == "対象外"
    assert col(row, "貸方勘定科目") == "売上高" and col(row, "貸方取引先") == "A社"
    assert col(row, "貸方税区分") == "課税売上 10%" and col(row, "貸方インボイス") == ""
    assert col(row, "借方インボイス") == "" and col(row, "仕訳メモ") == ""


@pytest.mark.parametrize("kind,label", [("exp", "課税仕入 (軽)8%"), ("inc", "課税売上 (軽)8%")])
def test_reduced_rate_official_name(kind, label):
    _, row = rows([exp(kind=kind, rate=8, category="会議費" if kind == "exp" else "売上高")])
    assert label in row


def test_rate_zero():
    _, a, b = rows([exp(kind="inc", rate=0, category="受取利息", invoice_no=""),
                    exp(rate=0, category="租税公課", invoice_no="")])
    assert col(a, "貸方税区分") == "非課税売上"
    assert col(b, "借方税区分") == "対象外" and col(b, "借方インボイス") == ""


@pytest.mark.parametrize("d,label", [
    ("2023-09-30", ""),           # インボイス制度前 → 空欄（MF では適格扱い = 全額控除）
    ("2023-10-01", "80％控除"),
    ("2026-09-30", "80％控除"),
    ("2026-10-01", "70％控除"),
    ("2028-09-30", "70％控除"),
    ("2028-10-01", "50％控除"),
    ("2030-09-30", "50％控除"),
    ("2030-10-01", "30％控除"),
    ("2031-09-30", "30％控除"),
    ("2031-10-01", "控除なし"),
])
def test_invoice_transitional_boundaries(d, label):
    _, row = rows([exp(d=d, invoice_no="")])
    assert col(row, "借方インボイス") == label


def test_qualified_always_tekikaku_even_late():
    _, row = rows([exp(d="2032-01-01")])
    assert col(row, "借方インボイス") == "適格"


def test_bank_source_counter_account():
    _, row = rows([exp(source="BANK_CSV", invoice_no="")])
    assert col(row, "貸方勘定科目") == "普通預金"


def test_length_limits():
    _, row = rows([exp(store="店" * 300, category="科" * 40)])
    assert len(col(row, "借方取引先")) == 255 and len(col(row, "摘要")) == 200
    assert len(col(row, "借方勘定科目")) == 30


def test_sequential_transaction_numbers():
    r = rows([exp(), exp(), exp()])
    assert [x[0] for x in r[1:]] == ["1", "2", "3"]


def test_cp932_encodable():
    text = export.to_csv([exp(invoice_no="", d="2026-11-01"), exp(rate=8), exp(kind="inc", rate=0,
                          category="受取利息")], "mf")
    assert text.encode("cp932").decode("cp932") == text


def test_escape_formulas_keeps_27_columns():
    _, row = rows([exp(store="=1+1", invoice_no="@x")], escape_formulas=True)
    assert len(row) == 27 and col(row, "借方取引先") == "'=1+1" and col(row, "摘要") == "'=1+1"
    assert not col(row, "仕訳メモ").startswith(export.FORMULA_START)
