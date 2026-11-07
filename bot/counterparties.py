"""取引先マスタ: 通帳の摘要（半角カナの略称）→ 正式名称・法人番号・登録番号・勘定科目（T-061）。

- 通帳の摘要「ｶ)ｴﾑｱｰﾙｴﾌ」→ 照合キー「エムアールエフ」（法人格の略号・空白・小書き文字を除去）
- 正式名称「株式会社ＭＲＦ」→ 照合キー「エムアールエフ」（英字を読みに変換）。漢字の名称は
  フリガナがないとキーを作れないため、国税庁 法人番号 Web-API（NTA_APP_ID）か利用者の確認で覚える。
- 一度確認した対応は利用者ごとに保存され、次回から自動で当たる。
"""
from __future__ import annotations

import io
import re
import unicodedata
from datetime import date, datetime

import store

LEGAL_WORDS = ("株式会社", "有限会社", "合同会社", "合資会社", "合名会社", "一般社団法人", "一般財団法人",
               "医療法人", "社会福祉法人", "(株)", "（株）", "㈱", "(有)", "（有）", "㈲", "(同)")
# 通帳・振込で使われる法人格の略号（全角化後）
ABBR = r"(カ|ユ|ド|ゴ|メ|シ|ザイ|シヤ|イ|フク|ガク|トク|シユウ|ギヨ|ノウ|セイ)"
SMALL = str.maketrans("ァィゥェォッャュョヮヵヶ", "アイウエオツヤユヨワカケ")
LETTERS = {"A": "エー", "B": "ビー", "C": "シー", "D": "デイー", "E": "イー", "F": "エフ", "G": "ジー", "H": "エイチ",
           "I": "アイ", "J": "ジエー", "K": "ケー", "L": "エル", "M": "エム", "N": "エヌ", "O": "オー", "P": "ピー",
           "Q": "キユー", "R": "アール", "S": "エス", "T": "テイー", "U": "ユー", "V": "ブイ", "W": "ダブリユー",
           "X": "エツクス", "Y": "ワイ", "Z": "ゼツト"}
KATA = re.compile(r"^[ァ-ヶー]+$")

# 摘要の定型（取引先ではないもの）。(パターン, 勘定科目, 記帳するか)
SYSTEM_RULES: list[tuple[str, str, bool]] = [
    (r"利息", "受取利息", True),
    (r"振込手数|振込手数料|EB基本手数料|基本手数料|手数料", "支払手数料", True),
    (r"繰越", "繰越", False),
    (r"ATM|ゆうちよ|ゆうちょ|セブン銀行|ローソン銀行|イーネツト|イーネット|現金|カード", "現金", False),
]
TRANSFER_CATEGORIES = ("現金", "現金引出", "現金預入", "事業主貸", "事業主借", "繰越")
CATEGORY_ALIASES = {"売上": "売上高", "手数料": "支払手数料", "振込手数料": "支払手数料", "利息": "受取利息"}


# ---------------------------------------------------------------- normalize
def _base(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").replace(" ", "").replace("　", "")


def key_from_description(desc: str) -> str:
    """通帳の摘要 → 照合キー。例: 「振込ｶ)ｴﾑｱｰﾙｴﾌ」→「エムアールエフ」"""
    s = _base(desc).upper()
    s = re.sub(r"^(振込|振替|フリコミ|フリカエ|入金|出金|送金)", "", s)
    s = re.sub(rf"^{ABBR}\)", "", s)
    s = re.sub(rf"\({ABBR}\)?$", "", s)
    s = re.sub(rf"\({ABBR}\)", "", s)
    s = s.translate(SMALL)
    s = "".join(LETTERS.get(ch, ch) for ch in s)
    return re.sub(r"[・\.\-,()（）]", "", s)


def key_from_name(name: str, furigana: str = "") -> str:
    """正式名称（またはフリガナ）→ 照合キー。作れない（漢字が残る）場合は空文字。"""
    if furigana:
        f = _base(furigana)
        f = unicodedata.normalize("NFKC", "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in f))
        for w in ("カブシキガイシヤ", "カブシキカイシヤ", "ユウゲンガイシヤ", "ゴウドウガイシヤ"):
            f = f.translate(SMALL).replace(w, "")
        return re.sub(r"[^ァ-ヶー]", "", f.translate(SMALL))
    s = _base(name)
    for w in LEGAL_WORDS:
        s = s.replace(unicodedata.normalize("NFKC", w), "")
    s = s.upper().translate(SMALL)
    s = "".join(LETTERS.get(ch, ch) for ch in s)
    s = re.sub(r"[・\.\-,]", "", s)
    return s if KATA.match(s) else ""


def keys_match(a: str, b: str) -> bool:
    """通帳は名称が途中で切れることがあるため、4文字以上の前方一致も同一とみなす。"""
    if not a or not b:
        return False
    if a == b:
        return True
    short, long_ = sorted((a, b), key=len)
    return len(short) >= 4 and long_.startswith(short)


def normalize_category(c: str) -> str:
    c = (c or "").strip()
    return CATEGORY_ALIASES.get(c, c)


def system_rule(desc: str) -> tuple[str, bool] | None:
    s = _base(desc).upper()
    for pat, cat, book in SYSTEM_RULES:
        if re.search(pat, s):
            return cat, book
    return None


# ---------------------------------------------------------------- storage
def _now() -> str:
    return store.now()


def all_(user_id: str) -> list[dict]:
    with store.tx() as con:
        rows = con.execute("SELECT * FROM counterparties WHERE user_id=? ORDER BY name", (user_id,)).fetchall()
    return [dict(r) for r in rows]


def upsert(user_id: str, *, name: str, key: str = "", furigana: str = "", corporate_number: str = "",
           registration_no: str = "", category: str = "", source: str = "user") -> dict:
    name = name.strip()[:80]
    key = key or key_from_name(name, furigana)
    reg = registration_no.strip().upper()
    if reg and not re.fullmatch(r"T\d{13}", reg):
        raise ValueError("登録番号は T + 13桁 です")
    if not corporate_number and reg:
        corporate_number = reg[1:]
    with store.tx() as con:
        row = con.execute("SELECT id FROM counterparties WHERE user_id=? AND name=?", (user_id, name)).fetchone()
        vals = (key, furigana[:120], corporate_number[:13], reg, normalize_category(category)[:20], source, _now())
        if row:
            con.execute("""UPDATE counterparties SET match_key=CASE WHEN ?<>'' THEN ? ELSE match_key END,
                           furigana=CASE WHEN ?<>'' THEN ? ELSE furigana END,
                           corporate_number=CASE WHEN ?<>'' THEN ? ELSE corporate_number END,
                           registration_no=CASE WHEN ?<>'' THEN ? ELSE registration_no END,
                           category=CASE WHEN ?<>'' THEN ? ELSE category END, source=?, updated_at=?
                           WHERE id=?""",
                        (vals[0], vals[0], vals[1], vals[1], vals[2], vals[2], vals[3], vals[3], vals[4], vals[4],
                         source, vals[6], row["id"]))
            cid = row["id"]
        else:
            cid = con.execute("""INSERT INTO counterparties(user_id,name,match_key,furigana,corporate_number,registration_no,
                                 category,source,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?) RETURNING id""",
                              (user_id, name, *vals[:5], source, vals[6], vals[6])).fetchone()["id"]
        cur = con.execute("SELECT * FROM counterparties WHERE id=?", (cid,)).fetchone()
    return dict(cur)


def learn_alias(user_id: str, cp_id: int, desc_key: str) -> None:
    """利用者が確認した「摘要キー → 取引先」を覚える（別名テーブル）。"""
    if not desc_key:
        return
    with store.tx() as con:
        con.execute("DELETE FROM counterparty_aliases WHERE user_id=? AND alias=?", (user_id, desc_key))
        con.execute("INSERT INTO counterparty_aliases(user_id,alias,counterparty_id,created_at) VALUES(?,?,?,?)",
                    (user_id, desc_key, cp_id, _now()))


def match(user_id: str, desc: str, cps: list[dict] | None = None, aliases: dict[str, int] | None = None) -> dict:
    """摘要 → {kind: 'counterparty'|'system'|'unknown', counterparty?, category, book}"""
    rule = system_rule(desc)
    key = key_from_description(desc)
    if cps is None:
        cps = all_(user_id)
    if aliases is None:
        aliases = alias_map(user_id)
    by_id = {c["id"]: c for c in cps}
    if key in aliases and aliases[key] in by_id:
        c = by_id[aliases[key]]
        return {"kind": "counterparty", "counterparty": c, "category": c["category"], "book": True, "key": key, "how": "learned"}
    hits = [c for c in cps if keys_match(key, c["match_key"])]
    if len(hits) == 1:
        c = hits[0]
        return {"kind": "counterparty", "counterparty": c, "category": c["category"], "book": True, "key": key, "how": "name"}
    if rule:
        return {"kind": "system", "counterparty": None, "category": rule[0], "book": rule[1], "key": key, "how": "rule"}
    return {"kind": "unknown", "counterparty": None, "category": "", "book": True, "key": key, "how": "",
            "candidates": hits[:5]}


def alias_map(user_id: str) -> dict[str, int]:
    with store.tx() as con:
        rows = con.execute("SELECT alias, counterparty_id FROM counterparty_aliases WHERE user_id=?", (user_id,)).fetchall()
    return {r["alias"]: r["counterparty_id"] for r in rows}


# ---------------------------------------------------------------- Excel 取込（利用者の既存の通帳整理表）
def import_excel(user_id: str, data: bytes) -> dict:
    """既存の通帳整理表（列: 日付・支出・入金・…・勘定科目・取引先・…・インボイス登録番号）から取引先を取り込む。
    見出し行で列を探すので、列の位置が多少違っても読める。"""
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    added, seen = 0, set()
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        cat_col = name_col = reg_col = None
        for r in rows[:6]:
            for i, v in enumerate(r):
                v = str(v or "")
                if "インボイス" in v or "登録番号" in v:
                    reg_col = i
                if v in ("勘定科目", "科目", "詳細"):
                    cat_col = i
                if v in ("取引先", "相手先", "摘要"):
                    name_col = i
        if reg_col is None:
            continue
        # 既定（通帳整理表の配置）: 詳細の下が 勘定科目、その右が 取引先
        if cat_col is None:
            cat_col = 5
        if name_col is None:
            name_col = cat_col + 1
        for r in rows:
            if len(r) <= max(reg_col, name_col):
                continue
            name = str(r[name_col] or "").strip()
            reg = re.sub(r"\s", "", str(r[reg_col] or "")).upper()
            if not name or name in seen or not re.fullmatch(r"T\d{13}", reg):
                continue
            seen.add(name)
            upsert(user_id, name=name, registration_no=reg, category=str(r[cat_col] or ""), source="excel")
            added += 1
    return {"imported": added}


# ---------------------------------------------------------------- 国税庁 Web-API（NTA_APP_ID があるとき）
def parse_houjin_xml(xml: str) -> list[dict]:
    import xml.etree.ElementTree as ET

    out = []
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return out
    for c in root.iter("corporation"):
        g = lambda t: (c.findtext(t) or "").strip()  # noqa: E731
        if g("process") == "99" or g("closeDate"):
            continue
        out.append({"corporate_number": g("corporateNumber"), "name": g("name"), "furigana": g("furigana"),
                    "address": g("prefectureName") + g("cityName") + g("streetNumber")})
    return out


async def nta_search(app_id: str, desc: str) -> list[dict]:
    """摘要のカナで法人番号 Web-API を名称検索し、フリガナが摘要と一致する法人を返す（最大5件）。"""
    import httpx

    key = key_from_description(desc)
    if len(key) < 2:
        return []
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get("https://api.houjin-bangou.nta.go.jp/4/name",
                        params={"id": app_id, "name": key, "type": "12", "mode": "2", "target": "1"})
        r.raise_for_status()
    found = parse_houjin_xml(r.text)
    return [f for f in found if keys_match(key, key_from_name(f["name"], f["furigana"]))][:5]


def corporate_check_digit_ok(num: str) -> bool:
    """法人番号（13桁）のチェックデジット（receipt_parser と同じ計算）。"""
    from receipt_parser import check_digit_ok
    return bool(re.fullmatch(r"\d{13}", num)) and check_digit_ok(num)


# ---------------------------------------------------------------- 登録番号の確認（T-063）
# status: valid（登録中）/ expired（失効・取消）/ notfound（公表サイトにない）/ format_ng（形式・チェックデジット誤り）
INVOICE_API = "https://web-api.invoice-kohyo.nta.go.jp/1/num"


def format_status(reg: str) -> str:
    if not reg:
        return ""
    return "" if re.fullmatch(r"T\d{13}", reg) and corporate_check_digit_ok(reg[1:]) else "format_ng"


def parse_invoice_json(data: dict, asked: list[str]) -> dict[str, dict]:
    """公表サイト Web-API（type=21）の応答 → {登録番号: {status, name, registration_date, end_date}}"""
    out = {n: {"status": "notfound", "name": "", "registration_date": "", "end_date": ""} for n in asked}
    for a in data.get("announcement") or []:
        n = a.get("registratedNumber") or ""
        if n not in out or str(a.get("latest", "1")) != "1":
            continue
        end = a.get("disposalDate") or a.get("expireDate") or ""
        out[n] = {"status": "expired" if end else "valid", "name": a.get("name") or a.get("tradeName") or "",
                  "registration_date": a.get("registrationDate") or "", "end_date": end}
    return out


async def invoice_lookup(app_id: str, numbers: list[str]) -> dict[str, dict]:
    import httpx

    result: dict[str, dict] = {}
    async with httpx.AsyncClient(timeout=20) as c:
        for i in range(0, len(numbers), 10):   # 1回10件まで（公式仕様）
            chunk = numbers[i:i + 10]
            r = await c.get(INVOICE_API, params={"id": app_id, "number": ",".join(chunk), "type": "21", "history": "0"})
            r.raise_for_status()
            result.update(parse_invoice_json(r.json(), chunk))
    return result


def save_invoice_status(user_id: str, cp_id: int, status: str, name: str = "") -> None:
    with store.tx() as con:
        con.execute("UPDATE counterparties SET invoice_status=?, invoice_name=?, invoice_checked_at=? WHERE id=? AND user_id=?",
                    (status, name[:120], _now(), cp_id, user_id))


def today_iso() -> str:
    return date.today().isoformat()


_ = datetime  # 予約（将来の検証日時）
