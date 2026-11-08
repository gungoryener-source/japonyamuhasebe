"""T-071b: 消費税申告書 カードのデモ表示用データを、実際の計算エンジン（bot/tax/consumption_return.py）から生成する。

使い方（depo kökünden）:  python dashboard-next/scripts/make_consumption_example.py
手書きの数値は使わない。入力は app/lib/tax-example.json（消費税カードの共通例）。
bot/tests/test_consumption_return.py が出力ファイルの最新性を検証する。
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "bot"))

from tax.consumption import Purchase, Sale  # noqa: E402
from tax.consumption_return import compute_return  # noqa: E402

SRC = ROOT / "dashboard-next" / "app" / "lib" / "tax-example.json"
OUT = ROOT / "dashboard-next" / "app" / "lib" / "consumption-return-example.json"


def build() -> dict:
    ex = json.loads(SRC.read_text(encoding="utf-8"))
    year = ex["taxYear"]
    sales = [Sale(s["gross"], s["rate"]) for s in ex["sales"]]
    purchases = [Purchase(p["gross"], p["rate"], date.fromisoformat(p["day"]), p["qualified"], p.get("seller"))
                 for p in ex["purchases"]]
    return {
        "_note": "生成物。python dashboard-next/scripts/make_consumption_example.py で更新（手編集しない）。",
        "year": year,
        "results": {
            "honsoku": compute_return(year, sales, purchases, "honsoku").to_dict(),
            "kani": compute_return(year, sales, purchases, "kani", kani_type=5).to_dict(),
            "niwari": compute_return(year, sales, purchases, "niwari").to_dict(),
        },
    }


if __name__ == "__main__":
    OUT.write_text(json.dumps(build(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("wrote", OUT)
