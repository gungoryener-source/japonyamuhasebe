"""Bot yanıt dili (T-047c): ja (varsayılan) / tr / en.

Sohbet çekirdeği (`app._respond_ja`) Japonca üretir; bu modül
- kullanıcının yerel dildeki komutlarını Japonca komuta çevirir (`normalize`),
- Japonca yanıtı parça parça hedef dile çevirir (`localize`).
Veri (店名, 勘定科目 adları, tarih, tutar) çevrilmez; çevirisi olmayan parça Japonca kalır.
"""
from __future__ import annotations

import re

LANGS = ("ja", "tr", "en")
LANG_NAMES = {"ja": "日本語", "tr": "Türkçe", "en": "English"}

HELP_JA = ("レシートの写真か「店名 金額」を送ってください。\n"
           "例：ローソン 540円 軽減\n例：タクシー 2300 T1234567890123\n"
           "例：入金 330000 合同会社ミナト\n\n「合計」今月の集計　「取消」直前の記録を削除\n「パネル」ウェブ管理画面の接続コード")

# Hızlı yanıt / komut adları: Japonca komut → (tr, en)
COMMANDS: dict[str, tuple[str, str]] = {
    "取消": ("Geri al", "Undo"),
    "科目変更": ("Kategori değiştir", "Change category"),
    "税率8%": ("KDV %8", "Tax 8%"),
    "税率10%": ("KDV %10", "Tax 10%"),
    "合計": ("Toplam", "Total"),
    "📷 レシート": ("📷 Fiş", "📷 Receipt"),
    "ヘルプ": ("Yardım", "Help"),
    "パネル": ("Panel", "Panel"),
    "仕切書": ("Hurda fişi", "Scrap slip"),
    "通帳": ("Banka defteri", "Passbook"),
    "会社": ("Şirket", "Company"),
    "確認": ("Onayla", "Confirm"),
    "日付:昨日": ("Tarih: dün", "Date: yesterday"),
    "日付:一昨日": ("Tarih: önceki gün", "Date: 2 days ago"),
}

# Japonca parça → (tr, en). Uzun parçalar önce uygulanır.
PHRASES: dict[str, tuple[str, str]] = {
    # T-024 低信頼の読み取り結果
    "⚠️ 日付を読み取れなかったため、今日（": ("⚠️ Tarih okunamadığı için bugünün tarihiyle (", "⚠️ The date could not be read, so it was saved with today's date ("),
    "）の日付で記録しました。日付を確認してください。": (") kaydedildi. Lütfen tarihi kontrol edin.", "). Please check the date."),
    "違う場合は「日付 11/3」のように送ってください。": ("Yanlışsa 「日付 11/3」 gibi gönderin.", "If wrong, send e.g. 「日付 11/3」."),
    "⚠️ 税率ごとの内訳を読み取れなかったため、推定で記録しました。税率を確認してください。": (
        "⚠️ KDV oranı dökümü okunamadı; tahminle kaydedildi. Lütfen KDV oranını kontrol edin.",
        "⚠️ The tax-rate breakdown could not be read, so it was estimated. Please check the tax rate."),
    "確認しました ✅ この内容で記録しています。": ("Onaylandı ✅ Kayıt bu haliyle duruyor.", "Confirmed ✅ The record is kept as is."),
    "確認する記録がありません": ("Onaylanacak kayıt yok", "No record to confirm"),
    "日付を読み取れませんでした。「日付 11/3」や「日付 2026-11-03」のように送ってください（未来の日付は不可）。": (
        "Tarih anlaşılamadı. 「日付 11/3」 veya 「日付 2026-11-03」 gibi gönderin (gelecek tarih olmaz).",
        "Could not read the date. Send e.g. 「日付 11/3」 or 「日付 2026-11-03」 (no future dates)."),
    "日付を変更しました：": ("Tarih değiştirildi: ", "Date changed: "),
    "件をまとめて変更）": (" kayıt birlikte değişti)", " records updated)"),
    # 複数の事業所
    "記録先の事業所を選んでください": ("Kayıtların gideceği şirketi seçin", "Choose the company to record to"),
    "（記録先）": (" (seçili)", " (current)"),
    "記録先を「": ("Kayıtlar artık 「", "Now recording to 「"),
    "」に切り替えました。": ("」 şirketine gidecek.", "」."),
    "その番号の事業所はありません。": ("Bu numarada şirket yok.", "No company with that number."),
    "事業所は1つです。事業所を追加するには、パネルの右上のメニューから「事業所を追加」を選んでください。": (
        "Tek şirketiniz var. Şirket eklemek için panelde sağ üstteki menüden 「Şirket ekle」yi seçin.",
        "You have one company. To add one, use 「Add company」 in the panel's top-right menu."),
    "（LINE の帳簿）": ("(LINE defteri)", "(LINE ledger)"),
    "（名称未設定）": ("(adsız)", "(unnamed)"),
    # AI 読み取りの設定
    "レシートの読み取り方法を選んでください（現在: ": ("Fiş okuma yöntemini seçin (şu an: ", "Choose how receipts are read (now: "),
    "・OCR: 無料（印字のレシート向け）": ("・OCR: ücretsiz (basılı fişler için)", "・OCR: free (for printed receipts)"),
    "・AI: 約": ("・Yapay zekâ: yaklaşık ", "・AI: about "),
    "円/枚（手書き・かすれにも強い）": (" yen/fiş (el yazısı ve silik fişlerde de iyi)", " yen/receipt (handles handwriting and faded print)"),
    "・自動: まず OCR、読めなかったときだけ AI（読めなかった分だけ約": (
        "・Otomatik: önce OCR, okuyamazsa yapay zekâ (yalnızca okunamayanlar için yaklaşık ",
        "・Auto: OCR first, AI only if unreadable (about "),
    "円）": (" yen)", " yen)"),
    "レシートの読み取り方法を「": ("Fiş okuma yöntemi 「", "Receipt reading set to 「"),
    "」にしました。": ("」 olarak ayarlandı.", "」."),
    "OCR（無料）": ("OCR (ücretsiz)", "OCR (free)"),
    "自動（OCR → 読めなければ AI）": ("Otomatik (OCR → olmazsa yapay zekâ)", "Auto (OCR → AI if needed)"),
    "AI 読み取りはまだ設定されていません（管理者に連絡してください）。": (
        "Yapay zekâ ile okuma henüz ayarlanmadı (yöneticiye haber verin).", "AI reading isn't set up yet (contact the admin)."),
    # T-062 通帳
    "通帳のページを1枚ずつ撮影して送ってください（PDF ファイルでも可）。\nこれから30分間、送られた写真は通帳として読み取ります。": (
        "Banka defterinin sayfalarını tek tek çekip gönderin (PDF de olur).\n30 dakika boyunca gönderilen fotoğraflar banka defteri olarak okunur.",
        "Photograph each passbook page and send it (PDF also works).\nFor 30 minutes, photos are read as passbook pages."),
    "通帳を読み取りました": ("Banka defteri okundu", "Passbook read"),
    "明細 ": ("Satır ", "Rows "), "件・新規 ": (" · yeni ", " · new "), "件・重複 ": (" · tekrar ", " · duplicates "),
    "⚠️ 残高が合わない行が ": ("⚠️ Bakiyesi tutmayan satır: ", "⚠️ Rows with balance mismatch: "),
    "件あります（パネルで確認）": (" (panelde kontrol edin)", " (check in the panel)"),
    "「パネル」と送ると取引先・勘定科目の確認画面が開けます": (
        "「Panel」 yazınca firma ve hesap kalemi onay ekranı açılır", "Send 「Panel」 to open the counterparty / category review"),
    "通帳の読み取りには AI の設定が必要です。管理者に連絡するか、ネットバンキングの CSV をパネルから取り込んでください。": (
        "Banka defterini okumak için yapay zekâ ayarı gerekiyor. Yöneticiye haber verin ya da internet bankacılığı CSV'sini panelden yükleyin.",
        "Reading passbooks needs the AI setting. Contact the admin or import your online-banking CSV in the panel."),
    "通帳の明細を読み取れませんでした。明るい場所で、1ページずつまっすぐ撮影してください。": (
        "Defter satırları okunamadı. Aydınlık bir yerde, her sayfayı düz çekin.",
        "Couldn't read the rows. Photograph each page straight, in good light."),
    # T-060 仕切書
    "仕切書の写真を送ってください。\nこれから30分間、送られた写真は仕切書として確認待ちに入ります。": (
        "Hurda fişinin (仕切書) fotoğrafını gönderin.\n30 dakika boyunca gönderilen fotoğraflar hurda fişi olarak onay kuyruğuna girer.",
        "Send a photo of the scrap slip (仕切書).\nFor 30 minutes, photos you send go to the review queue as slips."),
    "仕切書を受け付けました（確認待ち）": ("Hurda fişi alındı (onay bekliyor)", "Scrap slip received (awaiting review)"),
    "発行元未読取": ("firma okunamadı", "issuer not read"),
    "日付未読取": ("tarih okunamadı", "date not read"),
    "金額はパネルで入力してください": ("Tutarları panelde girin", "Enter the amounts in the panel"),
    "「パネル」と送ると確認画面のリンクが届きます。承認すると売上として記録されます": (
        "「Panel」 yazınca onay ekranının bağlantısı gelir. Onayladığınızda satış olarak kaydedilir",
        "Send 「Panel」 to get the review link. Once approved it's recorded as sales"),
    "手書きの仕切書なら「仕切書」と送ってから写真を送ってください。": (
        "El yazısı hurda fişiyse önce 「Hurda fişi」 yazıp sonra fotoğrafı gönderin.",
        "For a handwritten scrap slip, send 「Scrap slip」 first, then the photo."),
    "\n合計 ¥": ("\nToplam ¥", "\nTotal ¥"),
    HELP_JA: (
        "Fiş fotoğrafı ya da 「mağaza tutar」 gönderin.\n"
        "Örnek: ローソン 540円 軽減 (indirimli %8)\nÖrnek: Taksi 2300 T1234567890123\n"
        "Örnek: 入金 330000 合同会社ミナト (gelir)\n\n"
        "「Toplam」 bu ayın özeti　「Geri al」 son kaydı sil\n「Panel」 web paneli bağlantı kodu\n「Dil」 dil seçimi",
        "Send a receipt photo or 「store amount」.\n"
        "e.g. ローソン 540円 軽減 (reduced 8%)\ne.g. Taxi 2300 T1234567890123\n"
        "e.g. 入金 330000 合同会社ミナト (income)\n\n"
        "「Total」 this month's summary　「Undo」 delete the last record\n「Panel」 web panel code\n「Language」 change language",
    ),
    "てがる会計へようこそ！": ("Tegaru Kaikei'ye hoş geldiniz!", "Welcome to Tegaru Kaikei!"),
    "登録しました ✅": ("Kaydedildi ✅", "Saved ✅"),
    "変更しました ✅": ("Güncellendi ✅", "Updated ✅"),
    "間違っていたら「取消」を押してください": ("Yanlışsa 「Geri al」a basın", "If it's wrong, tap 「Undo」"),
    "⚠️ 登録番号なし（仕入税額控除": ("⚠️ Kayıt numarası yok (vergi indirimi ", "⚠️ No registration number (input tax credit "),
    "登録番号 ": ("Kayıt no ", "Reg. no "),
    "・税率": (" · KDV ", " · tax "),
    "取り消す記録がありません": ("Geri alınacak kayıt yok", "Nothing to undo"),
    "」を取り消しました": ("」 geri alındı", "」 was undone"),
    "変更する記録がありません": ("Değiştirilecek kayıt yok", "No record to change"),
    "」の勘定科目を選んでください": ("」 için hesap kalemini (勘定科目) seçin", "」: choose an account title (勘定科目)"),
    "変更できませんでした（経費の記録と一覧の科目のみ変更できます）": (
        "Değiştirilemedi (yalnızca gider kayıtları ve listedeki kalemler)",
        "Could not change (only expense records and listed titles)"),
    "今月の集計": ("Bu ayın özeti", "This month"),
    "\n売上 ": ("\nGelir ", "\nSales "),
    "\n経費 ": ("\nGider ", "\nExpenses "),
    "\n差引 ": ("\nFark ", "\nNet "),
    "下のボタンでレシートを撮影するか、写真を送ってください。": (
        "Aşağıdaki düğmeyle fişi çekin ya da fotoğraf gönderin.",
        "Tap the button below to take a photo, or send one."),
    "ウェブ管理画面の接続コードです（他人に見せないでください）:": (
        "Web paneli bağlantı kodunuz (kimseyle paylaşmayın):",
        "Your web panel code (do not share it):"),
    "こちらから開けます:": ("Buradan açabilirsiniz:", "Open it here:"),
    "金額が見つかりませんでした。": ("Tutar bulunamadı.", "No amount found."),
    "金額が大きすぎます。1件20億円未満で入力してください。": (
        "Tutar çok büyük. Kayıt başına 2 milyar yenin altında girin.",
        "Amount too large. Enter less than ¥2 billion per record."),
    "今回の内容は記録されていません。": ("Bu mesaj kaydedilmedi.", "This was not recorded."),
    "プランの確認・変更はこちら:": ("Planınızı buradan görüp değiştirebilirsiniz:", "Check or change your plan here:"),
    "「パネル」と送るとウェブ管理画面からプランを変更できます。": (
        "「Panel」 yazarak web panelinden planınızı değiştirebilirsiniz.",
        "Send 「Panel」 to change your plan on the web panel."),
    "レシートを読み取り中です…\n結果はこのあと届きます（少しお待ちください）。": (
        "Fiş okunuyor…\nSonuç birazdan gelecek.", "Reading the receipt…\nThe result will follow shortly."),
    "画像を読み取れませんでした。もう一度送るか「店名 金額」で入力してください。": (
        "Görsel okunamadı. Tekrar gönderin ya da 「mağaza tutar」 yazın.",
        "Could not read the image. Send it again or type 「store amount」."),
    "画像を取得できませんでした。もう一度送ってください。": (
        "Görsel alınamadı. Lütfen tekrar gönderin.", "Could not fetch the image. Please send it again."),
    "テキストかレシート画像を送ってください。": ("Metin ya da fiş görseli gönderin.", "Please send text or a receipt image."),
    "金額を読み取れませんでした（": ("Tutar okunamadı (", "Could not read the amount ("),
    "\n読み取れた項目: ": ("\nOkunanlar: ", "\nRead so far: "),
    "のように金額を送ってください。": (" şeklinde tutarı gönderin.", " — send the amount like this."),
    "「店名 1234」": ("「mağaza 1234」", "「store 1234」"),
    "（税率ごとに": (" (KDV oranına göre ", " (split by tax rate into "),
    "件に分けて記録）": (" kayda bölündü)", " records)"),
    "%対象 ": ("% matrah ", "% base "),
    "%）": ("%)", "%)"),
    "）。": (").", ")."),
    "%・": ("% · ", "% · "),
}

_PHRASE_ORDER = sorted(PHRASES, key=len, reverse=True)

# Yerel komut / takma ad → Japonca komut (küçük harfe çevrilmiş anahtarlar)
_ALIASES: dict[str, str] = {}
for _ja, (_tr, _en) in COMMANDS.items():
    _ALIASES[_tr.lower()] = _ja
    _ALIASES[_en.lower()] = _ja
_ALIASES.update({"cancel": "取消", "toplam": "合計", "özet": "合計", "summary": "合計", "yardim": "ヘルプ",
                 "kdv 8": "税率8%", "kdv 10": "税率10%", "kdv %8": "税率8%", "kdv %10": "税率10%"})

_LANG_WORDS = {
    "ja": "ja", "日本語": "ja", "japonca": "ja", "japanese": "ja",
    "tr": "tr", "türkçe": "tr", "turkce": "tr", "turkish": "tr", "トルコ語": "tr",
    "en": "en", "english": "en", "ingilizce": "en", "i̇ngilizce": "en", "英語": "en",
}
_LANG_CMD = re.compile(r"^(言語|dil|language|lang)(?:\s*[:：\s]\s*(.+))?$", re.I)


def norm_lang(value: str | None) -> str:
    return value if value in LANGS else "ja"


def normalize(text: str) -> str:
    """Yerel dildeki komutu Japonca komuta çevir; komut değilse metni olduğu gibi döndür."""
    return _ALIASES.get(text.strip().lower(), text)


def parse_lang_command(text: str) -> tuple[bool, str | None]:
    """(dil komutu mu, seçilen dil). 「言語」/「dil」 tek başına → (True, None) = seçenekleri göster.
    「Türkçe」, 「English」, 「日本語」 ya da 「言語:tr」 → (True, 'tr')."""
    t = text.strip()
    if t.lower() in _LANG_WORDS and not t.lower() in ("ja", "tr", "en"):
        return True, _LANG_WORDS[t.lower()]
    m = _LANG_CMD.match(t)
    if not m:
        return False, None
    if not m.group(2):
        return True, None
    chosen = _LANG_WORDS.get(m.group(2).strip().lower())
    # 「Dil kursu 2000」「Language school 30000」 gibi kayıtlar komut sayılmaz:
    # bilinmeyen değer yalnızca 「:」 ile yazıldıysa (「dil: klingon」) seçenekleri gösterir.
    if chosen is None and not re.match(r"^\S+\s*[:：]", t):
        return False, None
    return True, chosen


def lang_prompt(lang: str) -> str:
    return {"ja": "表示言語を選んでください。", "tr": "Dil seçin.", "en": "Choose a language."}[norm_lang(lang)]


def lang_options() -> list[tuple[str, str]]:
    return [(LANG_NAMES[c], f"言語:{c}") for c in LANGS]


def lang_set_text(lang: str) -> str:
    return {"ja": "言語を日本語に設定しました。", "tr": "Dil Türkçe olarak ayarlandı.",
            "en": "Language set to English."}[norm_lang(lang)]


def text(lang: str, msg: str) -> str:
    """Japonca yanıt metnini hedef dile çevir (parça bazında)."""
    lang = norm_lang(lang)
    if lang == "ja":
        return msg
    idx = LANGS.index(lang) - 1
    for ja in _PHRASE_ORDER:
        if ja in msg:
            msg = msg.replace(ja, PHRASES[ja][idx])
    for ja, names in COMMANDS.items():   # metindeki 「合計」 gibi komut adları
        msg = msg.replace(f"「{ja}」", f"「{names[idx]}」")
    return msg


def options(lang: str, opts: list[tuple[str, str]], camera: str) -> list[tuple[str, str]]:
    """Hızlı yanıt etiketlerini çevir. Gönderilen metin = çevrilmiş etiket (normalize geri çevirir);
    kamera düğmesi ve özel komutlar (科目:X, 言語:xx) olduğu gibi gönderilir."""
    lang = norm_lang(lang)
    if lang == "ja":
        return opts
    idx = LANGS.index(lang) - 1
    out = []
    for label, send in opts:
        name = COMMANDS[label][idx] if label in COMMANDS else label
        out.append((name, camera if send == camera else (name if send == label and label in COMMANDS else send)))
    return out
