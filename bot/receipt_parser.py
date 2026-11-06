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

TOTAL_KEYS = r"(T\S{1,3}ng\s*thanh\s*to[aá]n|総?合\s*計|お会\s*計|^会\s*計(?!\s*機)|お?買\s*上\s*(げ|計|合計)?|領\s*収\s*金\s*額|ご?請\s*求\s*(金\s*)?額|お支払(金額|額)?|税込\s*合計|TOTAL)"
EXCLUDE_TOTAL = r"(\d\s*点|ポイント|小\s*計|商\s*品\s*合|値\s*引|税\s*合|税\s*抜|会\s*計\s*機|獲\s*得|内\s*税|消\s*費\s*税|税\s*額|対\s*象|お\s*預|預\s*り|お\s*釣|釣\s*銭|おつり|点\s*数|値引|割引|ポイント)"
# "10%対象" + OCR varyantları: "10%%対象", "10O%対象", "109%対象", "89対象", "8名対象", "8対象", "10%対旬"
RATE_LINE = re.compile(r"(?<![\d.,])(1\s*[0OoD]\s*[0O]?|8)\s*9?\s*[%％]{0,2}\s*[^\d\s()（）]{0,2}?\s*[%％]?\s*(?:対|[タﾀ]\s*[イｲ]\s*[ソシｼッｯ])")
RATE_LINE_AFTER = re.compile(r"(?:対\s*象\s*額?|課\s*税|[タﾀ]\s*[イｲ]\s*[ソシｼッｯ]\S{0,2})\s*[(（]?\s*(1\s*[0OoD]|8)\s*[%％]")
RATE_EXCLUDE = re.compile(r"(小\s*計|消\s*費\s*税|税\s*額|税\s*等|外\s*税)")
YEN_NUM = re.compile(r"[¥￥\\]?\s*(\d{1,3}(?:[,，.]\d{3})+|\d+)\s*円?")
STORE_SKIP = re.compile(r"(TEL|電話|〒|\d{2,4}-\d{2,4}-\d{3,4}|領収書|レシート|登録番号|毎度|ありがとう|いらっしゃい|営業時間|http|www|様$|No\.|レジ|担当|責)", re.I)


def normalize(text: str) -> str:
    """Tam genişlik → yarım genişlik, OCR'ın sık karıştırdığı karakterler."""
    t = unicodedata.normalize("NFKC", text)
    t = t.replace("ー", "ー")
    # tarih: "202 5年" / "9月1 7日" / "Z025年"
    t = re.sub(r"Z(?=0\d\d\s*年)", "2", t)
    t = re.sub(r"(20\d)\s(\d)\s*年", r"\1\2年", t)
    t = re.sub(r"(月\s*\d)\s(\d)\s*日", r"\1\2日", t)
    t = re.sub(r"(年\s*\d)\s(\d)\s*月", r"\1\2月", t)
    # "8. 00%" → "8%"
    t = re.sub(r"(\d+)\s*\.\s*0+\s*[%％]", r"\1%", t)
    # ¥1 → "補"/"]" gibi kayıp baş rakam: Japon fişinde virgüllü tutar ≥1,000 olmak zorunda
    t = re.sub(r"(?<=[\s¥\\])[補\]\[|!lI](?=\s*[,.]\s*\d{3}(?!\d))", "1", t)
    t = re.sub(r"(?<=\s)[WY](?=\d)", "¥", t)          # "W5" → "¥5"
    # "1, 000" / "1,.060" / "3. 410" gibi OCR boşluklarını birleştir
    t = re.sub(r"(\d)\s*[,.，]\s*[,.]?\s*(\d{3})(?!\d)", r"\1,\2", t)
    # rakam bağlamında O/o/〇 → 0, l/I → 1
    t = re.sub(r"(?<=\d)[OoU〇](?=\d)|(?<=[\d,])[OoU〇]\b", "0", t)
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


def check_digit_ok(num13: str) -> bool:
    """法人番号のチェックデジット（先頭1桁）。適格請求書の登録番号（法人）＝ T + 法人番号。"""
    if len(num13) != 13 or not num13.isdigit():
        return False
    d = [int(c) for c in num13]
    s = sum(x * (1 if i % 2 == 0 else 2) for i, x in enumerate(reversed(d[1:])))
    return d[0] == 9 - (s % 9)


def invoice_candidates(t: str) -> list[str]:
    out = []
    # T の後に 13 桁（間に空白・ハイフン・O が混ざることがある）
    for m in re.finditer(r"T[\s:：-]*((?:[\dOo][\s-]?){13})(?!\d)", t):
        digits = re.sub(r"[\s-]", "", m.group(1)).replace("O", "0").replace("o", "0")
        if len(digits) == 13 and digits.isdigit():
            out.append("T" + digits)
    # 「登録番号 : 「8220002014654」: T が 「 などに化けた / 欠落した
    for m in re.finditer(r"登\s*録\s*番\s*号\s*[:：]?\s*[T「「ＴI1l|]?\s*((?:\d[\s-]?){13})(?!\d)", t):
        digits = re.sub(r"[\s-]", "", m.group(1))
        if len(digits) == 13:
            out.append("T" + digits)
    return list(dict.fromkeys(out))


def find_invoice_no(t: str) -> str:
    cands = invoice_candidates(t)
    valid = [c for c in cands if check_digit_ok(c[1:])]
    return (valid or cands or [""])[0]


WEEKDAYS = "月火水木金土日"


def _weekday_after(t: str, end: int) -> int | None:
    m = re.match(r"\s*[(（]\s*([月火水木金土日])\s*[)）]", t[end:end + 6])
    return WEEKDAYS.index(m.group(1)) if m else None


def _repair_by_weekday(dt: date, wd: int, today: date) -> date | None:
    """OCR'ın düşürdüğü/bozduğu ay veya gün rakamını gün adıyla onar.
    Örn. 2026年1月05日(木) → 11月05日; 9月18日(火) → 9月16日. Tek alan değişikliği, en yakın tarih tercih edilir."""
    months = {dt.month} | ({10 + dt.month} if dt.month <= 2 else set()) | ({dt.month % 10} if dt.month >= 10 else set())
    days = {dt.day, dt.day % 10} | {k * 10 + dt.day % 10 for k in range(4)} | {(dt.day // 10) * 10 + j for j in range(10)}
    best = None
    for mo in months:
        for d in days:
            if (mo != dt.month) and (d != dt.day):
                continue  # yalnızca tek alan onarılır
            try:
                c = date(dt.year, mo, d)
            except ValueError:
                continue
            age = (today - c).days
            if c.weekday() == wd and 0 <= age < 500 and (best is None or age < (today - best).days):
                best = c
    return best


def find_date(t: str, today: date | None = None) -> str | None:
    today = today or date.today()
    pats = [
        (r"(20\d{2})\s*[年/.\-]\s*(\d{1,2})\s*[月/.\-]\s*(\d{1,2})\s*日?", lambda y, m, d: (int(y), int(m), int(d))),
        (r"(?:令和|R)\s*(\d{1,2}|元)\s*[年.\-/]\s*(\d{1,2})\s*[月.\-/]\s*(\d{1,2})\s*日?",
         lambda y, m, d: (REIWA_START + (1 if y == "元" else int(y)), int(m), int(d))),
        # Vietnamca: "Ngày 05 tháng 09 năm 2025", "Ngày 22/09/2025" (OCR: "/" → "7")
        (r"Ng\S{0,2}\s*a?\s*y\s*(\d{1,2})\s*th\S{0,3}ng\s*(\d{1,2})\s*n\S{0,3}m\s*(20\d{2})",
         lambda d, m, y: (int(y), int(m), int(d))),
        (r"Ng\S{0,2}\s*a?\s*y\s*(\d{2})\s*[/7]\s*(\d{2})\s*[/7]\s*(20\d{2})", lambda d, m, y: (int(y), int(m), int(d))),
        (r"(?<!\d)(\d{2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{1,2})(?!\d)", lambda y, m, d: (2000 + int(y), int(m), int(d))),
    ]
    for pat, conv in pats:
        for m in re.finditer(pat, t):
            try:
                y, mo, d = conv(*m.groups())
                dt = date(y, mo, d)
            except ValueError:
                continue
            if not (date(2019, 1, 1) <= dt <= date(today.year + 1, 12, 31)):
                continue
            wd = _weekday_after(t, m.end())
            if wd is not None and dt.weekday() != wd:
                fixed = _repair_by_weekday(dt, wd, today)
                if fixed:
                    return fixed.isoformat()
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


def _rate_amount(rest: str) -> int | None:
    rest = re.split(r"(内\s*消\s*費|消\s*費\s*税)", rest)[0]   # "(10%対象 ¥3,410 内消費税 ¥310)"
    rest = re.sub(r"\(\s*\d+\s*点\s*\)|\d+\s*点", " ", rest)     # "( 8点)" adet bilgisi
    nums = _amounts(rest)
    return nums[-1] if nums else None


def _check_with_tax(amt: int, rate: int, next_line: str) -> int:
    """「(8%対象 ¥311)(内消費税等 ¥97)」: 税額と合わない場合、OCR'ın düşürdüğü binler basamağını onar (311 → 1,311)."""
    if not re.search(r"(内\s*)?消\s*費\s*税|税\s*額", next_line):
        return amt
    other = re.findall(r"(\d+)\s*[%％]", next_line)
    if other and str(rate) not in other:          # başka oranın vergi satırı
        return amt
    taxes = _amounts(re.sub(r"\d+\s*[%％]", " ", next_line))
    if not taxes:
        return amt
    tax = taxes[-1]
    fits = lambda x: abs(x * rate // (100 + rate) - tax) <= 1  # noqa: E731
    if fits(amt) or amt < 100:
        return amt
    for k in range(1, 10):
        cand = amt + k * 1000
        if fits(cand):
            return cand
    return amt


def find_rate_totals(lines: list[str]) -> tuple[int | None, int | None, set[str]]:
    """Oran başına 税込 tutar. Bulunamayan oran None. Üçüncü değer: satırı görülen ama tutarı okunamayan oranlar."""
    found: dict[str, int] = {}
    unreadable: set[str] = set()
    for i, line in enumerate(lines):
        m = RATE_LINE.search(line) or RATE_LINE_AFTER.search(line)
        if not m:
            continue
        head = line[: m.start()]
        if RATE_EXCLUDE.search(head + line[m.start(): m.end() + 2]) or re.search(r"内\s*消\s*費|消\s*費\s*税\s*等", head):
            continue
        rate = 8 if m.group(1).strip() == "8" else 10
        key = str(rate)
        amt = _rate_amount(line[m.end():])
        if amt is None and i + 1 < len(lines) and not (RATE_LINE.search(lines[i + 1]) or RATE_LINE_AFTER.search(lines[i + 1])):
            amt = _rate_amount(lines[i + 1])
        if amt is None:
            unreadable.add(key)
            continue
        if re.search(r"外", head) and not re.search(r"外\s*税\s*額", head):   # 外税: tutar vergi hariç
            amt = amt + amt * rate // 100
        else:
            amt = _check_with_tax(amt, rate, lines[i + 1] if i + 1 < len(lines) else "")
        found[key] = max(found.get(key, 0), amt)
    return found.get("10"), found.get("8"), unreadable - set(found)


def find_dash_total(lines: list[str]) -> int:
    """領収証 tipi: 「¥1,688-」 (sonda tire) satırı."""
    best = 0
    for line in lines:
        for m in re.finditer(r"[¥￥\\]\s*(\d{1,3}(?:,\d{3})+|\d+)\s*[-ー一―]", line):
            n = int(m.group(1).replace(",", ""))
            best = max(best, n)
    return best


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
    store = find_store(lines)
    base = {"date": find_date(t, today), "store": store, "invoice_no": find_invoice_no(t),
            "category": guess_category(store + " " + " ".join(lines[:5]))}

    stated = find_total(lines) or find_dash_total(lines)   # fişte yazan toplam (iri yazı → sık bozulur)
    r10, r8, unreadable = find_rate_totals(lines)           # oran satırları (küçük yazı → daha güvenilir)
    reduced_marked = bool(re.search(r"(※|★|\*|軽)\s*(印|は|マーク)?.{0,6}軽[減滅]", t)) or "軽減税率" in t

    if r10 is not None and r8 is not None:
        t10, t8 = r10, r8
        total = t10 + t8
        if total == 0 and stated:
            total, t10, t8 = stated, (0 if reduced_marked else stated), (stated if reduced_marked else 0)
    elif r10 is not None or r8 is not None:
        known = r10 if r10 is not None else r8
        if unreadable and not (stated and stated > known):
            # diğer oranın satırı var ama okunamadı ve güvenilir toplam yok → yanlış tutar kaydetme
            return {"error": "金額の一部を読み取れませんでした", **base}
        if stated and stated >= known:
            other = stated - known
            total = stated
        else:
            other, total = 0, known
        t10, t8 = (known, other) if r10 is not None else (other, known)
    elif stated:
        total = stated
        only8 = reduced_marked and not re.search(r"(?<!\d)10\s*[%％]", t)
        t10, t8 = (0, total) if only8 else (total, 0)
    else:
        sub = max((max(_amounts(l)) for l in lines if re.search(r"小\s*計", l) and _amounts(l)), default=0)
        if not sub:
            return {"error": "合計金額が見つかりませんでした", **base}
        total = sub
        t10, t8 = (0, total) if reduced_marked else (total, 0)
    if total < 50:
        # ¥50 altı fiş çok nadir; genelde poşet ücreti (¥3–7) veya OCR hatası → kaydetmek yerine sor
        return {"error": "合計金額を確認できませんでした", **base}
    return {**base, "total": total, "total10": t10, "total8": t8}
