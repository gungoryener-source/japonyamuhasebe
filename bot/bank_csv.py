"""Japon bankalarının CSV hareket dökümlerini (入出金明細) ortak biçime çevirir.

Bankaların sütun adları farklıdır; başlık satırındaki anahtar kelimelerle eşleştiririz:
  日付: 日付 / 取引日 / 年月日 / お取引日 / 取扱日付 / 勘定日
  摘要: 摘要 / 内容 / お取引内容 / 取引内容 / 備考 / 取引区分
        (birden çok 摘要 sütunu varsa — MUFG 「摘要」+「摘要内容」 — soldan sağa boşlukla birleştirilir)
  出金: 出金 / お引出し / 引出 / 支払 / 払出
  入金: 入金 / お預入れ / 預入 / 受入
  金額: 金額 / 取引金額 (işaretli tek sütun)
  区分: 入出金区分 / 入払区分 — 金額 işaretsizse yön sütunu (受入・入金・1 → +, 払出・出金・2 → −;
        tanınmayan değer → satır atlanır, yanlış işaretle kayıt yazmaktansa)
  残高: 残高 / 差引残高 / 現在（貸付）高
Tarih üç sütuna bölünmüşse (「操作日(年)」「操作日(月)」「操作日(日)」) birleştirilir.
「番号」「口数」 içeren sütunlar (受入明細番号, 取引順番号 …) hiçbir anahtara atanmaz.
Banka bazında kaynaklar ve doğrulama durumu: docs/BANK_CSV.md (T-033).
Kodlama: UTF-8 (BOM'lu/BOM'suz) veya Shift_JIS (CP932) otomatik.
"""
from __future__ import annotations

import csv
import io
import re
from datetime import date

KEYS = {  # sıra önemli: bir hücre ilk eşleşen anahtara atanır
    "date": r"(日付|取引日|取り引き日|年月日|お取引日|取扱日|勘定日|Date)",
    "dir": r"(入出金区分|入払区分)",                          # ゆうちょBizダイレクト: 受入/払出
    "desc": r"(摘要|内容|取引内容|備考|取引区分|お取引内容|送金人名|依頼人名|Description)",
    "amount": r"(^金額$|^取引金額$|入出金|Amount)",          # işaretli tek sütun (楽天銀行: 入出金(円))
    "out": r"(出金|引出|引き出し|お引出|支払|払出|Withdraw)",
    "in": r"(入金|預入|預け入れ|お預入|預かり|預り|受入|Deposit)",
    "balance": r"(残高|現在.{0,6}高|Balance)",
}
SKIP_COL = r"(番号|口数)"
SPLIT_DATE = {"y": r"[(（]年[)）]", "m": r"[(（]月[)）]", "d": r"[(（]日[)）]"}  # ジャパンネット銀行 (現 PayPay銀行)
DIR_IN = {"受入", "入金", "預入", "1"}
DIR_OUT = {"払出", "出金", "支払", "引出", "2"}


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
    header_idx, cols, desc_cols = None, {}, []
    for i, row in enumerate(rows[:15]):  # başlıktan önce hesap bilgisi satırları olabilir
        found, descs, ymd = {}, [], {}
        for j, cell in enumerate(row):
            c = cell.strip()
            part = next((k for k, pat in SPLIT_DATE.items() if re.search(pat, c)), None)
            if part and "date" not in found:
                ymd.setdefault(part, j)
                continue
            if re.search(SKIP_COL, c):
                continue
            key = next((k for k, pat in KEYS.items() if k not in found and re.search(pat, c)), None)
            if key:
                found[key] = j
                if key == "desc":
                    descs.append(j)
            elif re.search(KEYS["desc"], c) and not any(
                    re.search(KEYS[k], c) for k in KEYS if k not in ("date", "desc")):
                descs.append(j)  # ek 摘要 sütunu (ör. 摘要内容)
        if "date" not in found and len(ymd) == 3:
            found["ymd"] = ymd  # type: ignore[assignment]
        if ("date" in found or "ymd" in found) and ("amount" in found or "in" in found or "out" in found):
            header_idx, cols, desc_cols = i, found, descs
            break
    if header_idx is None:
        raise ValueError("ヘッダー行（日付・入金/出金）が見つかりません")
    out = []
    for row in rows[header_idx + 1:]:
        if not row or all(not c.strip() for c in row):
            continue
        get = lambda k: row[cols[k]] if k in cols and cols[k] < len(row) else ""  # noqa: E731
        if "ymd" in cols:
            yi, mi, di = (cols["ymd"][k] for k in ("y", "m", "d"))  # type: ignore[index]
            if max(yi, mi, di) >= len(row):
                continue
            d = _date(f"{row[yi].strip()}-{row[mi].strip()}-{row[di].strip()}")
        else:
            d = _date(get("date"))
        if not d:
            continue
        if "amount" in cols:
            amt = _num(get("amount"))
            if amt and "dir" in cols:
                kind = get("dir").strip()
                if kind in DIR_OUT:
                    amt = -abs(amt)
                elif kind in DIR_IN:
                    amt = abs(amt)
                else:
                    continue  # yönü bilinmeyen satır: işaret tahmin edilmez
        else:
            inn, outv = _num(get("in")) or 0, _num(get("out")) or 0
            amt = inn - outv
        if not amt:
            continue
        parts = [row[j].strip() for j in desc_cols if j < len(row) and row[j].strip()]
        first = (get("desc") or "").strip() or "(摘要なし)"
        rec = {"d": d, "description": " ".join(parts) or "(摘要なし)", "amount": amt,
               "balance": _num(get("balance"))}
        if rec["description"] != first:
            # T-051 öncesi yalnızca ilk 摘要 sütunu alınıyordu; eski içe aktarmaların
            # parmak izini tanımak için store.insert_bank_rows bunu da kontrol eder.
            rec["legacy_description"] = first
        out.append(rec)
    return out
