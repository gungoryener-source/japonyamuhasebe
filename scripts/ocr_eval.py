#!/usr/bin/env python3
"""OCR doğruluk ölçümü — kırmızı damga bastırma açık/kapalı karşılaştırması (T-026, docs/OCR.md).

Gerçek fişler (kişisel veri; depoya konmaz):
    python scripts/ocr_eval.py --images ~/fisler --truth ~/fisler/truth.csv
    truth.csv sütunları: file,date,store,total,total10,total8,invoice_no  (boş = kontrol edilmez)

Sentetik (depodaki fikstürler + üretilmiş 朱色 damgalar):
    python scripts/ocr_eval.py --synthetic

Çıktı: alan bazında doğruluk (%), "tüm alanlar" ve "yanlış kayıt" (toplam okunmuş ama yanlış) — iki ayar için.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "bot"), os.path.join(ROOT, "bot", "tests")]

import receipt_ocr  # noqa: E402

FIELDS = ["date", "store", "total", "total10", "total8", "invoice_no"]


def _cases_synthetic():
    from stamp_fixture import stamped_fixture
    from test_ocr_red_stamp import EXPECTED

    for name, exp in sorted(EXPECTED.items()):
        yield f"{name}+damga", stamped_fixture(name), exp
        with open(os.path.join(ROOT, "bot", "tests", "fixtures", f"{name}.jpg"), "rb") as f:
            yield f"{name} (temiz)", f.read(), exp


def _cases_real(images: str, truth: str):
    with open(truth, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            with open(os.path.join(images, row["file"]), "rb") as g:
                exp = {k: (int(row[k]) if k.startswith("total") and row.get(k) else row.get(k) or None)
                       for k in FIELDS}
                yield row["file"], g.read(), exp


def evaluate(cases, today: date) -> dict:
    stats = {flag: {"n": 0, "all": 0, "wrong": 0, **{k: 0 for k in FIELDS}} for flag in (False, True)}
    for name, img, exp in cases:
        line = [name]
        for flag in (False, True):
            receipt_ocr.RED_SUPPRESS = flag
            r = receipt_ocr.read_receipt(img, today)
            st = stats[flag]
            st["n"] += 1
            ok_all = True
            for k in FIELDS:
                if exp.get(k) is None:
                    continue
                ok = r.get(k) == exp[k] or (k == "invoice_no" and not exp[k] and not r.get(k))
                st[k] += ok
                ok_all &= ok
            st["all"] += ok_all
            st["wrong"] += bool(r.get("total")) and r.get("total") != exp.get("total")
            line.append(("ON " if flag else "OFF") + (" ✓" if ok_all else " ✗"))
        print("  ".join(line))
    receipt_ocr.RED_SUPPRESS = True
    return stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images")
    ap.add_argument("--truth")
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--today", default="2026-11-05")
    a = ap.parse_args()
    if not receipt_ocr.available():
        sys.exit("tesseract + jpn kurulu değil")
    cases = _cases_synthetic() if a.synthetic else _cases_real(a.images, a.truth)
    stats = evaluate(cases, date.fromisoformat(a.today))
    print("\n| Ayar | " + " | ".join(FIELDS) + " | Tüm alanlar | Yanlış kayıt |")
    print("|---" * (len(FIELDS) + 3) + "|")
    for flag in (False, True):
        st = stats[flag]
        pct = lambda v: f"%{round(100 * v / max(st['n'], 1))}"  # noqa: E731
        print(f"| OCR_RED_SUPPRESS={int(flag)} | " + " | ".join(pct(st[k]) for k in FIELDS)
              + f" | {pct(st['all'])} | {pct(st['wrong'])} |")


if __name__ == "__main__":
    main()
