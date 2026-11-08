# Banka CSV (入出金明細) biçimleri — T-033

Ayrıştırıcı: `bot/bank_csv.py` (başlık satırındaki anahtar kelimelerle eşleştirir; banka adına göre dal yok).
Testler: `bot/tests/test_bank_csv_formats.py` (sentetik satırlar; başlıklar aşağıdaki kaynaklardan birebir).
Kontrol tarihi: **2026-11-08**. Kaynak seviyesi: ✅ banka/resmî belge · 🟡 üçüncü taraf (eski olabilir) · ⚠️ doğrulanamadı.

| Banka | Başlık satırı (kaynaktaki sırayla) | Seviye | Kaynak | Test |
|---|---|---|---|---|
| ゆうちょ銀行 (ゆうちょBizダイレクト, 法人) | `取引日,入出金区分,取引内容,送金人名等,受入明細番号,取扱口数,取引金額,現在（貸付）高,EDI 情報等` — 入出金区分 = 「受入」/「払出」, 取引金額 işaretsiz, CSV 取引日 azalan sırada | ✅ | [操作説明書 18.4 (2023-05)](https://www.jp-bank.japanpost.jp/hojin/smart/bizdirect/pdf/bizdirect_18.pdf) | ✅ |
| 京都銀行 (Web-EB ANSER) | `照会口座,番号,勘定日,（起算日）,出金金額（円）,入金金額（円）,小切手区分,残高（円）,取引区分,明細区分,金融機関名,支店名,摘要` | ✅ | [入出金明細照会結果ファイル（ＣＳＶ形式）](https://www.kyotobank.co.jp/houjin/webeb/manual/pdf/sougou_file.pdf) | ✅ |
| 楽天銀行 (旧イーバンク) | `取引日,入出金(円),残高(円),入出金先内容` (işaretli tek tutar) | 🟡 | [felica2money wiki](https://github.com/tmurakam/felica2money/wiki/Csv%E5%8F%96%E3%82%8A%E8%BE%BC%E3%81%BF) | ✅ |
| PayPay銀行 (旧ジャパンネット銀行) | `"操作日(年)","操作日(月)","操作日(日)","取引順番号","摘要","お支払金額","お預り金額","残高"` (tarih 3 sütun) | 🟡 | felica2money wiki (aynı) | ✅ |
| ソニー銀行 (円普通) | `"お取り引き日","摘要","お預け入れ額","お引き出し額","差し引き残高"` | 🟡 | felica2money wiki (aynı) | ✅ |
| 三菱UFJ銀行 | Mevcut fixture `日付,摘要,摘要内容,支払い金額,預かり金額,差引残高` (T-051) kaynaksız. Resmî belge yalnızca sabit uzunluklu 全銀 biçimi ([15-02.pdf](https://www.bk.mufg.jp/houjin/ebp/info/pdf/15-02.pdf): 入払区分 1=入金 / 2=出金) — CSV değil | ⚠️ | — | (T-051) |
| 三井住友銀行 | Yardım sayfası yalnızca ekrandaki 「お取り扱い内容」 sütununu anlatıyor ([help_kouza/9](https://www.smbc.co.jp/direct/sousa/help_kouza/9.html)) | ⚠️ | — | — |
| みずほ銀行 | Kamuya açık başlık bulunamadı | ⚠️ | — | — |
| 住信SBIネット銀行 | Kamuya açık başlık bulunamadı (MF FAQ yalnızca hesap türleri) | ⚠️ | — | — |
| GMOあおぞらネット銀行 | Yalnızca API (JSON: transactionDate, amount, remarks, balance …) belgelendi ([api-spec](https://gmo-aozora.com/business/service/pdf/api-spec-indivisual.pdf)) | ⚠️ | — | — |

Notlar
- 楽天銀行 法人 SSS'si CSV özelliklerini listeliyor ([help.rakuten-bank.net/faq/show/6420](https://help.rakuten-bank.net/faq/show/6420?category_id=198&site_domain=business)) ama sayfa robots ile kapalı; okunamadı. Güncel başlığın 「取引後残高(円)」「入出金内容」 olması muhtemel — ayrıştırıcı ikisini de kabul eder (残高 / 内容 anahtarları).
- ソニー銀行 外貨 CSV ([fc/39](https://sonybank.jp/products/fc/39.html)) yabancı para cinsinden; yen defterine alınmaz (kapsam dışı).
- ゆうちょ: tarih biçimi belgede yok. Ayrıştırıcı `YYYY/MM/DD`, `YYYYMMDD`, `YYYY年MM月DD日`, 令和 (`R8.11.1`) kabul eder.
- Yön sütunundaki tanınmayan değer (ör. 訂正) → satır atlanır; yanlış işaretle kayıt yazılmaz.
- ⚠️ bankalar: ürün sahibi gerçek (kişisel verisi silinmiş) bir başlık satırı paylaşırsa fixture + test eklenir.
