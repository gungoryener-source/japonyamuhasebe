# e-Tax (国税電子申告・納税システム) araştırma notu — T-045b

Amaç: 個人事業主 kullanıcılarımızın 青色申告決算書 / 確定申告書 / 消費税申告書 verisini e-Tax'a nasıl ulaştırabileceğimizi
belgelemek. **Bu belge kod içermez**; uygulama alt görevleri en altta (T-067…T-069).
Kontrol tarihi: **2026-11-08**. Seviye: ✅ 国税庁 / e-Tax resmî sayfası · ⚠️ doğrulanmadı (uygulamadan önce kontrol).
Not: Takvim — 令和8年 = 2026.

## 1. Teknik spesifikasyon (仕様書) — ✅

Kaynak: [e-Tax仕様書一覧](https://www.e-tax.nta.go.jp/shiyo/ksk2/ksk2_shiyo3.htm) (giriş: [ソフトウェア開発業者の方へ](https://www.e-tax.nta.go.jp/shiyo/index.html)).
Dosyalar **CAB** arşivi olarak indirilir (açıldıktan sonra Word/Excel). Sayfa: indirme, sayfadaki 利用上の注意'yi kabul etmek sayılır → Q-19.

| 項番 | 仕様書名 (sayfadaki adıyla) | Bizim için | 更新日 (確定版) |
|---|---|---|---|
| 1 | データ形式等に関する仕様書 | XML/xtx genel kuralları, karakter kümesi | 令和8年1月30日 |
| 2 | 受付システムインターフェイスに関する仕様書 | 申告データの zarf yapısı | 令和8年8月28日 |
| 3 | 電子署名に関する仕様書 | imza (biz imzalamayacağız, §3) | 令和8年6月15日 |
| 7 | 手続一覧・手続内帳票対応表・対象帳票一覧 | 手続ID ↔ 帳票 (様式ID) eşlemesi, **güncel ID'ler buradan** | 令和8年8月28日 |
| 8 | 帳票間連動仕様書 | 決算書 → 申告書 alan aktarımları | 令和8年8月12日 |
| 9 | XML構造設計書及び帳票フィールド仕様書【所得税関係】 | 青色申告決算書 / 申告書 alanları | 令和8年1月30日 |
| 11 | XML構造設計書及び帳票フィールド仕様書【消費税関係】 | 消費税申告書 (一般 / 簡易 / 2割) | 令和8年8月12日 |
| 19 | XMLスキーマ | XSD doğrulama (testlerde kullanılacak) | 令和8年8月28日 |

- Bir de **ドラフト版** var (令和8年10月30日; 項番9 所得税 dahil, XMLスキーマ hariç) — 令和9年1月4日 受付開始 ile geçerli olacak değişiklikler. Sayfa: 「確定までに変更となる可能性があります」. 令和8年分 申告 için ilk uygulamada **ドラフト版 → 確定版** farkı izlenmeli.
- 様式ID örnekleri ⚠️ eski: [番号制度の導入に伴う改修帳票一覧 (平成28/29年)](https://www.e-tax.nta.go.jp/shiyo/bangou_ichiran.pdf) — `KOA010` 確定申告書A, `KOA020` 申告書B / 分離課税用(第三表). Bu liste 青色申告決算書 ID'sini içermiyor ve eski; **güncel ID'ler yalnızca 項番7'den** alınacak, koda sabit yazılmayacak (yapılandırma tablosu + kaynak sürüm).

## 2. 個人 所得税確定申告 帳票 seti — ✅

Kaynak: [所得税確定申告等（令和7年分）帳票一覧 PDF](https://www.e-tax.nta.go.jp/tetsuzuki/shinkoku/shotoku_p07.pdf) (giriş: [申告手続(所得税確定申告等)](https://www.e-tax.nta.go.jp/tetsuzuki/shinkoku/shinkoku01.htm)). PDF'te 帳票ID yok, yalnızca adlar.

Kullanıcı kitlemiz için ilgili olanlar:
- 所得税及び復興特別所得税の申告書 (第一表・第二表) — (分離課税用 第三表 kapsam dışı)
- **青色申告決算書 (一般用)** ← `GET /api/v1/reports/blue-return.pdf` (T-045) ile aynı veri; ilk hedef
- 青色申告決算書 (現金主義用 / 不動産所得用 / 農業所得用) — kapsam dışı (şimdilik)
- 収支内訳書 (一般用) — 白色申告 kullanıcıları için ikinci hedef

## 3. Gönderim yolları ve ürüne etkisi — ✅

| Yol | Ne kabul eder | Kaynak |
|---|---|---|
| **e-Taxソフト(WEB版)** | 民間会計ソフトで作成した **.xtx** dosyasını okuyup gönderebilir (マイナンバーカード: IC okuyucu veya uyumlu akıllı telefon) | [Q&A 49 (令和8年10月22日)](https://www.e-tax.nta.go.jp/toiawase/qa/e-taxweb/49.htm) |
| **e-Taxソフト (ダウンロード版)** | 「拡張子がxtxのファイルを事前に用意する必要があります」; xtx'in nasıl üretileceği → yazılım üreticisinin işi | [民間会計ソフトで作成した申告書データを送信したい (令和7年10月31日)](https://www.e-tax.nta.go.jp/toiawase/faq/sousin/03.htm) |
| **確定申告書等作成コーナー** | 決算書'ı yalnız gönderemez, 確定申告書 ile birlikte gönderilir; ve **yalnızca 決算書・収支内訳書作成コーナーで作成した** veri eklenebilir → bizim xtx'imiz buraya **eklenemez** | [作成コーナー Q&A cid1128](https://www.keisan.nta.go.jp/r6yokuaru/cat1/cat16/cat163/cid1128.html) |
| **国税電子申告・納税システムAPI** | Çoğunlukla salt okuma (基本情報, メッセージ, 受信データ xtx indirme). 「申告等データ送信など…対応していません」 → doğrudan gönderim **yok**. API anahtarı: 別紙1 ile e-tax-api@nta.go.jp başvurusu + 利用規約 | [e-Tax API](https://www.e-tax.nta.go.jp/shiyo/api.htm), [利用規約 PDF](https://www.e-tax.nta.go.jp/shiyo/api/api_kiyaku.pdf) |

Karşılaştırma (piyasa uygulaması, ✅ üretici belgesi): 弥生会計 「e-Taxデータの書き出し（e-Taxソフト取り込み用）」 ile **.xtx** üretir; 消費税 ve 所得税 ayrı dosya; 作成コーナー ve e-Taxソフト(WEB版)'e aktarım desteklemediğini yazar
([弥生 サポート page_id=18154](https://support.yayoi-kk.co.jp/subcontents.html?page_id=18154)). Not: bu, Q&A 49'daki (WEB版 .xtx okur) güncel resmî ifadeyle çelişiyor — WEB版 desteği uygulama sırasında gerçek dosyayla denenmeli.

**Sonuç (öneri):** Ürünümüz **imzalamaz ve göndermez**; yalnızca XSD'ye uygun **.xtx** üretir, kullanıcı e-Taxソフト (WEB版/ダウンロード版) ile okuyup マイナンバーカード ile imzalayıp gönderir.
Bu yol: sır/sertifika saklamayı gerektirmez, e-Tax API başvurusu gerektirmez, sorumluluk sınırı açık kalır.
作成コーナー kullanan kullanıcılara: 「決算書PDFの数字を作成コーナーに手入力」 kılavuzu (T-045 PDF'i zaten bunun için).

## 4. Riskler / açık noktalar
- ⚠️ 青色申告決算書 (一般用) 様式ID ve sürümü doğrulanmadı → T-067'de 項番7/9'dan.
- ⚠️ 決算書 alan numaraları ↔ bizim 勘定科目 eşlemesi (T-045'te alan numarası yazılmadı) → T-067.
- Yıllık sürüm: her 年分 için 帳票 sürümü değişir; xtx üretici yıl parametreli olmalı, bilinmeyen yıl → üretme (hata), uydurma yok.
- 仕様書 indirme = 利用上の注意 kabulü → Q-19 (ajan kabul edemez, ürün sahibi onayı).

## 5. Önerilen alt görevler (BACKLOG'a eklendi)
- **T-067** (P2, blocked Q-19): 仕様書 項番7・9・19'u indir, 青色申告決算書(一般用) 様式ID/sürüm + XML alanları ↔ `/api/v1/pl` 科目 eşleme tablosu `docs/ETAX_MAPPING.md` (kaynak sürüm + tarih). Kod yok.
- **T-068** (P2, T-067'den sonra): `bot/etax.py` — 青色申告決算書(一般用) .xtx üretimi (yıl parametreli, bilinmeyen yıl → 422), XSD ile doğrulayan testler; `GET /api/v1/reports/blue-return.xtx?year=` (yetki T-045 ile aynı).
- **T-069** (P2, T-068'den sonra): Panel 確定申告: 「e-Tax用データ(.xtx)」 indirme + Japonca adım kılavuzu (e-Taxソフト(WEB版)で読み込み → 署名 → 送信; 作成コーナー kullanıcısına PDF'ten elle giriş notu).
