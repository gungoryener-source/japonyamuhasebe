"""Kural tabanlı Japon fişi (レシート / 領収書) ayrıştırıcı — yapay zekâ kullanmaz.

Girdi: OCR'dan gelen düz metin. Çıktı: `app.normalize_ocr` ile aynı biçimde dict
  {"date", "store", "total", "total10", "total8", "invoice_no", "category"} veya {"error": ...}

Kurallar (Japonya'da yaygın fiş düzenleri):
- 合計 / お買上計 / 領収金額 / ご請求額 satırındaki en büyük tutar = toplam
- 「10%対象 ¥1,100」「(8%対象 ¥540)」「※は軽減税率対象」 → oran başına toplam
- 登録番号: T + 13 hane (OCR'ın araya koyduğu boşluk/tire ve O→0 karışıklığı düzeltilir)
- Tarih: 2026年11月5日 · 2026/11/05 · 2026-11-05 · 26/11/05 · 令和8年11月5日 · R8.11.5
- Mağaza adı: üst satırlardan tarih/telefon/adres/sayı olmayan ilk anlamlı satır
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date

from parser import guess_category

REIWA_START = 2018  # 令和1年 = 2019

TOTAL_KEYS = r"(総?合\s*計|お?会\s*計|お?買\s*上\s*(げ|計|合計)?|領\s*収\s*金\s*額|ご?請\s*求\s*(金\s*)?額|お支払(金額|額)?|税込\s*合計|TOTAL)"
EXCLUDE_TOTAL = r"(小\s*計|内\s*税|消\s*費\s*税|税\s*額|対\s*象|お\s*預|預\s*り|お\s*釣|釣\s*銭|おつり|点\s*数|値引|割引|ポイント)"
# "10%対象" + OCR varyantları: "109%対象" (% → 9%), "89対象", "8対象" (% kayıp)
RATE_LINE = re.compile(r"(?<!\d)(10|8)\s*(?:9?\s*[%％]|9(?=\s*対)|(?=\s*対))\s*(対\s*象|対象計|課税|標準|軽減)")
YEN_NUM = re.compile(r"[¥￥\\]?\s*(\d{1,3}(?:[,，.]\d{3})+|\d+)\s*円?")
STORE_SKIP = re.compile(r"(TEL|電話|〒|\d{2,4}-\d{2,4}-\d{3,4}|領収書|レシート|登録番号|毎度|ありがとう|いらっしゃい|営業時間|http|www|様$|No\.|レジ|担当|責)", re.I)


def normalize(text: str) -> str:
    """Tam genişlik → yarım genişlik, OCR'ın sık karıştırdığı karakterler."""
    t = unicodedata.normalize("NFKC", text)
    t = t.replace("ー", "ー")
    # "1, 000" / "1,.060" / "3. 410" gibi OCR boşluklarını birleştir
    t = re.sub(r"(\d)\s*[,.，]\s*[,.]?\s*(\d{3})(?!\d)", r"\1,\2", t)
    # rakam bağlamında O/o/〇 → 0, l/I → 1
    t = re.sub(r"(?<=\d)[Oo〇](?=\d)|(?<=[\d,])[Oo〇]\b", "0", t)
    t = re.sub(r"(?<=\d)[lI|](?=\d)", "1", t)
    return t


def _amounts(line: str) -> list[int]:
    out = []
    for m in YEN_NUM.finditer(line):
        raw = m.group(1).replace(",", "").replace("，", "").replace(".", "")
        if raw.isdigit():
            n = int(raw)
            if 0 < n < 100_000_000:
                out.append(n)
    return out


def find_invoice_no(t: str) -> str:
    # T の後に 13 桁（間に空白・ハイフン・O が混ざることがある）
    for m in re.finditer(r"T[\s:：-]*((?:[\dOo][\s-]?){13})", t):
        digits = re.sub(r"[\s-]", "", m.group(1)).replace("O", "0").replace("o", "0")
        if len(digits) == 13 and digits.isdigit():
            return "T" + digits
    return ""


def find_date(t: str, today: date | None = None) -> str | None:
    today = today or date.today()
    pats = [
        (r"(20\d{2})\s*[年/.\-]\s*(\d{1,2})\s*[月/.\-]\s*(\d{1,2})", lambda y, m, d: (int(y), int(m), int(d))),
        (r"(?:令和|R)\s*(\d{1,2}|元)\s*[年.\-/]\s*(\d{1,2})\s*[月.\-/]\s*(\d{1,2})",
         lambda y, m, d: (REIWA_START + (1 if y == "元" else int(y)), int(m), int(d))),
        (r"(?<!\d)(\d{2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{1,2})(?!\d)", lambda y, m, d: (2000 + int(y), int(m), int(d))),
    ]
    for pat, conv in pats:
        for m in re.finditer(pat, t):
            try:
                y, mo, d = conv(*m.groups())
                dt = date(y, mo, d)
            except ValueError:
                continue
            if date(2019, 1, 1) <= dt <= date(today.year + 1, 12, 31):
                return dt.isoformat()
    return None


def find_total(lines: list[str]) -> int:
    best = 0
    for i, line in enumerate(lines):
        if re.search(TOTAL_KEYS, line, re.I) and not re.search(EXCLUDE_TOTAL, line):
            nums = _amounts(line)
            if not nums and i + 1 < len(lines):  # tutar bir alt satıra kaymış olabilir
                nums = _amounts(lines[i + 1])
            if nums:
                best = max(best, max(nums))
    return best


def find_rate_totals(lines: list[str]) -> tuple[int, int]:
    t10 = t8 = 0
    for i, line in enumerate(lines):
        m = RATE_LINE.search(line)
        if not m:
            continue
        rest = line[m.end():]
        nums = _amounts(rest) or (_amounts(lines[i + 1]) if i + 1 < len(lines) else [])
        if not nums:
            continue
        amt = nums[0]
        # 「(内消費税 ¥100)」 gibi küçük sayıları değil, satırdaki ilk (ana) tutarı al
        if m.group(1) == "10":
            t10 = max(t10, amt)
        else:
            t8 = max(t8, amt)
    return t10, t8


STORE_HINT = re.compile(r"(株式会社|有限会社|合同会社|\(株\)|㈱|店|本店|支店|堂|屋|商店|ストア|マート|薬局|ホテル|交通|タクシー|鉄道|書店)")
TITLE_LIKE = re.compile(r"^.{0,1}(収|収書|領収|領.書|.収書|レシート|御請求書)$")


def find_store(lines: list[str]) -> str:
    cands = []
    for i, line in enumerate(lines[:8]):
        s = re.split(r"\s{2,}", line.strip())[0].strip(" 　*-=_|・“”\"'")
        if len(s) < 2 or STORE_SKIP.search(s) or TITLE_LIKE.match(s) or find_date(s) or re.fullmatch(r"[\d\s¥,.:/()-]+", s):
            continue
        if len(re.findall(r"[ぁ-んァ-ヶ一-龠]", s)) < 2:  # en az 2 Japonca karakter
            continue
        if re.search(r"(都|道|府|県).{1,6}(市|区|町|村)", s):  # adres satırı
            continue
        cands.append((0 if STORE_HINT.search(s) else 1, i, s[:40]))
    return min(cands)[2] if cands else ""


def parse_receipt(text: str, today: date | None = None) -> dict:
    t = normalize(text)
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    if not lines:
        return {"error": "文字を読み取れませんでした"}
    total = find_total(lines)
    t10, t8 = find_rate_totals(lines)
    reduced_marked = bool(re.search(r"(※|★|\*)\s*(印|は|マーク)?.{0,6}軽減", t)) or "軽減税率" in t
    if not total and (t10 or t8):
        total = t10 + t8
    if not total:
        return {"error": "合計金額が見つかりませんでした"}
    if t10 + t8 != total:
        # oran kırılımı toplamla tutmuyorsa: tek oran varsay
        if t8 and not t10 and t8 < total:
            t10 = total - t8
        elif t10 and not t8 and t10 < total:
            t8 = total - t10
        elif t10 + t8 != total:
            t10, t8 = (0, total) if reduced_marked and "10%" not in t else (total, 0)
    store = find_store(lines)
    return {
        "date": find_date(t, today),
        "store": store,
        "total": total,
        "total10": t10,
        "total8": t8,
        "invoice_no": find_invoice_no(t),
        "category": guess_category(store + " " + " ".join(lines[:5])),
    }
