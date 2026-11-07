"""パネルの所得税概算（dashboard-next/app/lib/income.ts）の基礎控除表が bot/tax/income.py と一致するか。"""
import re
from pathlib import Path

import pytest

from tax.income import BASIC_DEDUCTION

TS = Path(__file__).resolve().parents[2] / "dashboard-next" / "app" / "lib" / "income.ts"


def _ts_tables() -> dict[int, tuple]:
    src = TS.read_text(encoding="utf-8")
    consts = {}
    for name, body in re.findall(r"const (BASIC_\d{4}): \[number, number\]\[\] = \[(.*?)\];", src, re.S):
        rows = re.findall(r"\[(Infinity|[\d_]+), ([\d_]+)\]", body)
        consts[name] = tuple((None if lim == "Infinity" else int(lim.replace("_", "")), int(amt.replace("_", "")))
                             for lim, amt in rows)
    m = re.search(r"BASIC_DEDUCTION: Record<number, \[number, number\]\[\]> = \{(.*?)\};", src, re.S)
    assert m, "BASIC_DEDUCTION map not found in income.ts"
    return {int(y): consts[c] for y, c in re.findall(r"(\d{4}): (BASIC_\d{4})", m.group(1))}


def test_same_years():
    assert sorted(_ts_tables()) == sorted(BASIC_DEDUCTION)


@pytest.mark.parametrize("year", sorted(BASIC_DEDUCTION))
def test_same_table(year):
    assert _ts_tables()[year] == BASIC_DEDUCTION[year]
