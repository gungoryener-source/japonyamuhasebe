"""「店名 金額」形式の短いメッセージを帳簿レコードに変換する。LINE / WhatsApp 共通。"""
import re
from datetime import date

KEYWORDS = [
    (r"タクシー|電車|JR|Suica|PASMO|新幹線|バス|ENEOS|ガソリン|駐車|タイムズ|乗車|交通株式会社", "旅費交通費"),
    (r"スタバ|スターバックス|カフェ|ドトール|喫茶|コメダ", "会議費"),
    (r"居酒屋|レストラン|寿司|焼肉|接待", "接待交際費"),
    (r"docomo|ドコモ|au|ソフトバンク|楽天モバイル|AWS|サーバ|ネット|Wi-?Fi", "通信費"),
    (r"家賃|オフィス|コワーキング", "地代家賃"),
    (r"電気|ガス代|水道", "水道光熱費"),
    (r"書店|紀伊國屋|本代|書籍", "新聞図書費"),
    (r"外注|業務委託", "外注工賃"),
    (r"売上|入金|請求", "売上高"),
]
FOOD = r"ローソン|セブン|ファミマ|ファミリーマート|スーパー|弁当|軽減|食品|8%|8％"
INVOICE = re.compile(r"T\d{13}")


def guess_category(text: str) -> str:
    for pat, cat in KEYWORDS:
        if re.search(pat, text, re.I):
            return cat
    return "消耗品費"


def parse_text(text: str, today: date) -> dict | None:
    # 全角数字 → 半角
    t = text.translate(str.maketrans("０１２３４５６７８９，", "0123456789,"))
    inv_m = INVOICE.search(t)
    inv = inv_m.group(0) if inv_m else ""
    rest = t.replace(inv, " ") if inv else t
    rest_wo_rate = re.sub(r"(8|10)\s*[%％]", " ", rest)
    nums = [int(n.replace(",", "")) for n in re.findall(r"\d[\d,]*", rest_wo_rate)]
    nums = [n for n in nums if n > 0]
    if not nums:
        return None
    amount = max(nums)
    cat = guess_category(t)
    kind = "inc" if cat == "売上高" else "exp"
    store = re.sub(r"\d[\d,]*\s*(円|yen|¥)?|[¥￥]", " ", rest_wo_rate, flags=re.I)
    store = re.sub(r"軽減|売上|入金", " ", store)
    store = re.sub(r"\s+", " ", store).strip() or "(取引先未入力)"
    return {
        "date": today.isoformat(),
        "kind": kind,
        "store": store,
        "amount": amount,
        "category": cat,
        "rate": 8 if re.search(FOOD, t) and kind == "exp" else 10,
        "invoice_no": inv,
    }
