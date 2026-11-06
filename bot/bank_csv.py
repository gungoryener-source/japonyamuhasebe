"""Japon bankalarının CSV hareket dökümlerini (入出金明細) ortak biçime çevirir.

Bankaların sütun adları farklıdır; başlık satırındaki anahtar kelimelerle eşleştiririz:
  日付: 日付 / 取引日 / 年月日 / お取引日 / 取扱日付 / 勘定日
  摘要: 摘要 / 内容 / お取引内容 / 取引内容 / 備考 / 取引区分
  出金: 出金 / お引出し / 引出 / 支払 / 払出
  入金: 入金 / お預入れ / 預入 / 受入
  金額: 金額 / 取引金額 (işaretli tek sütun)
  残高: 残高 / 差引残高
Kodlama: UTF-8 (BOM'lu/BOM'suz) veya Shift_JIS (CP932) otomatik.
"""
from __future__ import annotations

import csv
import io
import re
from datetime import date

KEYS = {  # sıra önemli: bir hücre ilk eşleşen anahtara atanır
    "date": r"(日付|取引日|年月日|お取引日|取扱日|勘定日|Date)",
    "desc": r"(摘要|内容|取引内容|備考|取引区分|お取引内容|Description)",
    "amount": r"(^金額$|^取引金額$|入出金|Amount)",          # işaretli tek sütun (楽天銀行: 入出金(円))
    "out": r"(出金|引出|お引出|支払|払出|Withdraw)",
    "in": r"(入金|預入|お預入|預かり|預り|受入|Deposit)",
    "balance": r"(残高|Balance)",
}


def decode(raw: bytes) -> str:
    for enc in ("utf-8-sig", "cp932"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _num(s: str) -> int | None:
    s = (s or "").strip().replace(",", "").replace("¥", "").replace("円", "").replace("\\", "")
    s = s.replace("△", "-").replace("▲", "-")
    if not s or s in ("-", "--"):
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def _date(s: str) -> str | None:
    s = (s or "").strip()
    m = re.match(r"(\d{4})\D?(\d{1,2})\D?(\d{1,2})", s)
    if m:
        y, mo, d = map(int, m.groups())
    else:
        m = re.match(r"(?:R|令和)\s*(\d{1,2})\D(\d{1,2})\D(\d{1,2})", s)
        if not m:
            return None
        y, mo, d = 2018 + int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return date(y, mo, d).isoformat()
    except ValueError:
        return None


def parse(raw: bytes) -> list[dict]:
    text = decode(raw)
    rows = list(csv.reader(io.StringIO(text)))
    header_idx, cols = None, {}
    for i, row in enumerate(rows[:15]):  # başlıktan önce hesap bilgisi satırları olabilir
        found = {}
        for j, cell in enumerate(row):
            c = cell.strip()
            for key, pat in KEYS.items():
                if key not in found and re.search(pat, c):
                    found[key] = j
                    break
        if "date" in found and ("amount" in found or "in" in found or "out" in found):
            header_idx, cols = i, found
            break
    if header_idx is None:
        raise ValueError("ヘッダー行（日付・入金/出金）が見つかりません")
    out = []
    for row in rows[header_idx + 1:]:
        if not row or all(not c.strip() for c in row):
            continue
        get = lambda k: row[cols[k]] if k in cols and cols[k] < len(row) else ""  # noqa: E731
        d = _date(get("date"))
        if not d:
            continue
        if "amount" in cols:
            amt = _num(get("amount"))
        else:
            inn, outv = _num(get("in")) or 0, _num(get("out")) or 0
            amt = inn - outv
        if not amt:
            continue
        out.append({"d": d, "description": (get("desc") or "").strip() or "(摘要なし)", "amount": amt,
                    "balance": _num(get("balance"))})
    return out
