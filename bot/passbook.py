"""通帳（紙の預金通帳）のスキャン → 入出金明細（T-062）。

- 読み取りは AI（Claude）。PDF はそのまま、写真は画像として送る（ürün sahibi kararı 2026-11-07）。
- 残高チェック: 前行の残高 − 支払 + 預り = 残高。合わない行は balance_ok=0 で確認画面に赤表示。
- 取込は既存の bank_tx（CSV 取込と同じ表）に入れ、指紋で重複を除く（同じページを2回送っても二重にならない）。
"""
from __future__ import annotations

import base64
import json
import re

import store

MODE_SECONDS = 30 * 60
_mode: dict[str, float] = {}


def start_mode(user_id: str) -> None:
    import time
    _mode[user_id] = time.time() + MODE_SECONDS


def mode_active(user_id: str) -> bool:
    import time
    return _mode.get(user_id, 0) > time.time()

AI_PROMPT = """これは日本の銀行の預金通帳（紙）のスキャンです。入出金の明細行だけを読み取り、次の JSON だけを返してください（説明文なし）:
{"bank":"銀行名と支店名（表紙にあれば）","rows":[{"date":"YYYY-MM-DD","withdrawal":お支払金額(整数円、なければ0),
"deposit":お預り金額(整数円、なければ0),"description":"摘要（印字のまま。半角カナもそのまま）","balance":差引残高(整数円)}]}
規則:
- 年月日の2桁の年は令和（例: 06-11-15 → 2024-11-15、05-08-04 → 2023-08-04）。
- 金額の「*」「\\」「,」は除く。「繰越」行は rows に含めず、その残高を最初の行の前残高として "opening_balance" に入れる。
- 表紙・注意書き・名義・口座番号などの個人情報は出力しない。空白行は出力しない。ページ順に並べる。"""


def parse_ai(text: str) -> dict:
    m = re.search(r"\{.*\}", text or "", re.S)
    try:
        data = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        data = {}
    rows = []
    for r in data.get("rows") or []:
        d = str(r.get("date") or "")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
            continue
        w, dep = _int(r.get("withdrawal")), _int(r.get("deposit"))
        desc = str(r.get("description") or "").strip()[:120]
        if not w and not dep:
            continue
        rows.append({"d": d, "description": desc or "（摘要なし）", "amount": dep - w, "balance": _int_or_none(r.get("balance"))})
    return {"bank": str(data.get("bank") or "").strip()[:50], "rows": rows,
            "opening_balance": _int_or_none(data.get("opening_balance"))}


def _int(v) -> int:
    n = _int_or_none(v)
    return n or 0


def _int_or_none(v) -> int | None:
    if v is None or v == "":
        return None
    try:
        return int(round(float(str(v).replace(",", "").replace("*", "").replace("¥", "").replace("\\", ""))))
    except ValueError:
        return None


def check_balances(rows: list[dict], opening: int | None = None) -> list[dict]:
    """各行に balance_ok（True/False/None）を付ける。前の行の残高がわからない行は None。"""
    prev = opening
    for r in rows:
        if prev is not None and r["balance"] is not None:
            r["balance_ok"] = prev + r["amount"] == r["balance"]
        else:
            r["balance_ok"] = None
        if r["balance"] is not None:
            prev = r["balance"]
    return rows


async def ai_read(data: bytes, api_key: str, model: str) -> dict:
    import httpx

    if data[:5] == b"%PDF-":
        block = {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                                 "data": base64.b64encode(data).decode()}}
    else:
        media = "image/png" if data[:8].startswith(b"\x89PNG") else "image/jpeg"
        block = {"type": "image", "source": {"type": "base64", "media_type": media, "data": base64.b64encode(data).decode()}}
    async with httpx.AsyncClient(timeout=180) as c:
        r = await c.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": model, "max_tokens": 16000,
                  "messages": [{"role": "user", "content": [block, {"type": "text", "text": AI_PROMPT}]}]},
        )
        r.raise_for_status()
        text = "".join(b.get("text", "") for b in r.json()["content"])
    return parse_ai(text)


def import_rows(user_id: str, parsed: dict, account: str = "") -> dict:
    rows = check_balances(parsed["rows"], parsed.get("opening_balance"))
    for r in rows:
        r["src"] = "passbook"
    account = (account or parsed.get("bank") or "通帳")[:50]
    added, dup = store.insert_bank_rows(user_id, rows, account)
    bad = sum(1 for r in rows if r["balance_ok"] is False)
    return {"account": account, "read": len(rows), "imported": added, "duplicates": dup, "balance_errors": bad,
            "date_from": rows[0]["d"] if rows else "", "date_to": rows[-1]["d"] if rows else ""}


def line_reply(res: dict) -> str:
    if not res["read"]:
        return "通帳の明細を読み取れませんでした。明るい場所で、1ページずつまっすぐ撮影してください。"
    msg = (f"通帳を読み取りました（{res['account']}）\n{res['date_from']}〜{res['date_to']}\n"
           f"明細 {res['read']}件・新規 {res['imported']}件・重複 {res['duplicates']}件")
    if res["balance_errors"]:
        msg += f"\n⚠️ 残高が合わない行が {res['balance_errors']}件あります（パネルで確認）"
    return msg + "\n\n「パネル」と送ると取引先・勘定科目の確認画面が開けます"
