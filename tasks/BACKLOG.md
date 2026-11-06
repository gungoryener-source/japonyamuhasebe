# BACKLOG — tek görev kuyruğu

Kurallar ve durum sözlüğü: `CLAUDE.md`. Öncelik: P0 (önce) > P1 > P2. Her görevin kabul ölçütü vardır; tek çalışmada bitmeyecekse önce böl.

| ID | Öncelik | Durum | Görev |
|---|---|---|---|
| T-001 | P0 | done (bu commit) | Prototiplerde 令和8年度 経過措置 düzeltmesi |
| T-002 | P0 | done (bu commit) | Vergi motoru `bot/tax/` (消費税) + testler |
| T-003 | P0 | done (bu commit) | `/entries/{user_id}` uç noktasını kapat / kimlik doğrulaması ekle |
| T-004 | P1 | done (2025 tablosu) | Vergi motoru: 所得税 (所得税・復興税・青色控除・基礎控除) |
| T-004b | P1 | todo | `BASIC_DEDUCTION[2026]` ve `[2027]` (令和8・9年分) tablosunu ekle + sınır testleri (Q-03 cevaplandı) |
| T-005 | P1 | done | REST API v1: tenant'a göre özet, nakit akışı, faturalar |
| T-006 | P1 | done | PostgreSQL desteği (`DATABASE_URL`), SQLite yedek |
| T-007 | P1 | done | dashboard-next'i API'ye bağla (mock → fetch, yükleniyor/hata durumları) |
| T-008 | P1 | done | 適格請求書 oluşturma API + PDF |
| T-009 | P1 | done | LINE: son kaydı düzenleme (勘定科目 / 税率 hızlı yanıtla) |
| T-010 | P2 | todo | 登録番号 doğrulama (国税庁 Web-API, mock'lu testler) |
| T-011 | P2 | todo | Fiş görsellerini nesne depolamaya taşıma (arama uç noktası ✅ `/api/v1/entries`) |
| T-012 | P2 | done (T-012b doğrulama) | CSV dışa aktarma (freee / MF / 弥生 formatları) |
| T-013 | P2 | done (canlı: Q-06) | WhatsApp Business webhook kanalı (parser paylaşımlı) |
| T-014 | P2 | done | OCR: çok oranlı (8%+10%) fişleri satır bazında ayırma |
| T-015 | P1 | done | dashboard-next: 請求書管理 sayfası (liste, filtre, 消込) |
| T-016 | P1 | done (743716d) | dashboard-next: vergi kartını `bot/tax` kurallarıyla hizala (経過措置 satırı, 2割/3割/簡易 seçimi) |
| T-012b | P2 | todo | CSV formatlarını freee / MF / 弥生'nin güncel içe aktarma şablonlarıyla doğrula (sütun adları, 税区分 metinleri) |
| T-018 | P1 | done | Sahte/zayıf token'a karşı: token iptali (`DELETE /api/v1/tokens/current`), LINE 「パネル」 en fazla 5 aktif token |
| T-019 | P2 | todo | PostgreSQL bağlantı havuzu (`psycopg_pool`) ve yavaş istek ölçümü |
| T-020 | P1 | done | dashboard-next: 確定申告 önizleme sayfası (`/api/v1/pl`, `/api/v1/tax/income`) |
| T-022 | P1 | done | Yapay zekâsız fiş okuma: Tesseract (jpn) + kural tabanlı ayrıştırıcı, Docker imajı |
| T-023 | P1 | done | Gerçek fişlerle OCR ölçümü (67 fiş; tüm alanlar %70, toplam %85, yanlış kayıt %7 — docs/OCR.md) |
| T-025 | P1 | todo | LINE görsel işleme süresi: OCR uzun sürerse önce 「読み取り中…」 yanıtı, sonuç push mesajla (reply token süresi) |
| T-026 | P2 | todo | OCR: kırmızı damga (印) rengini ön işlemede bastır (HSV ile kırmızı → beyaz), tarih/rakam doğruluğu |
| T-024 | P2 | todo | OCR sonrası kullanıcı onayı: düşük güvenli alanlarda (tarih yok, oran kırılımı tahmini) LINE'da 「確認」 butonlu özet |
| T-030 | P1 | done | dashboard-next: 経費精算 sayfası (kayıt listesi/arama, fiş yükleme + OCR, ekle/düzenle/sil) |
| T-031 | P1 | done | dashboard-next: 銀行連携 sayfası (banka CSV içe aktarma, faturalarla otomatik eşleştirme) |
| T-032 | P1 | done | dashboard-next: 設定 sayfası (事業者情報, kanal bağlantıları, oturum) + sayfa yönlendirmeli menü |
| T-033 | P2 | todo | Banka CSV: gerçek banka dosyalarıyla doğrulama (MUFG, SMBC, みずほ, ゆうちょ, 楽天, PayPay, 住信SBI, GMOあおぞら örnek başlıkları + testler) |
| T-034 | P2 | todo | Panel: fiş görselini kayıtla birlikte saklama/gösterme (`/api/v1/receipts/ocr` → kaydetme seçeneği, 電帳法 görsel arşivi) |
| T-035 | P2 | todo | Panel: e2e testleri (Playwright) CI'a — tüm menüler demo + canlı mod |
| T-040 | P0 | done (bu commit; panel → T-040b) | Hesap sistemi: e-posta + şifre kayıt/giriş, oturum token'ı, LINE defterini hesaba bağlama, panelde /signup ve /login |
| T-040b | P0 | done (bu commit) | Panel: /signup, /login, /reset sayfaları + /connect'te hesaba LINE bağlama (T-040 API'si) |
| T-041 | P1 | todo | Ekip üyeleri: bir işletmeye çok kullanıcı (owner / accountant / viewer), davet kodu, yetki kontrolü |
| T-042 | P0 | doing (developer, 2026-11-07) | Abonelik: planlar + Stripe test modu (Checkout, webhook, iptal), plan bazlı sınırlar; anahtar yoksa ödeme kapalı |
| T-043 | P0 | todo | Yasal sayfalar: 利用規約, プライバシーポリシー (APPI), 特定商取引法に基づく表記 — şablon + yapılandırma, 「要確認」 işaretli |
| T-044 | P1 | todo | Tanıtım sayfası (/lp), kayıt akışı ve ilk kurulum sihirbazı (事業者情報 → LINE bağlantısı → ilk fiş) |
| T-045 | P1 | todo | 確定申告 çıktıları: 青色申告決算書 (損益計算書) PDF, 申告書 alan numaralarıyla özet; e-Tax xtx araştırma notu (docs/ETAX.md) |
| T-046 | P1 | todo | Veri dışa aktarma (tüm veri ZIP: CSV + fatura PDF), hesap silme talebi, PostgreSQL yedekleme betiği ve belge |
| T-047 | P2 | todo | Panel metinlerini `app/lib/i18n.ts`'de topla (ja varsayılan, en), anadil kontrolü için tek liste |
| T-048 | P1 | todo | Güvenlik: giriş/OCR için hız sınırı, CORS'u PANEL_URL ile kısıtla, güvenlik başlıkları, parola politikası |
| T-017 | P2 | todo | `KANI_RATIO` testleri — みなし仕入率 TAX_RULES'ta ✅ (tax-watcher 2026-11-06, NTA No.6505); yalnızca test eklenecek |
| T-049 | P1 | todo | 所得税: 青色申告特別控除 令和9年分以後 (75万 kademesi, 55万 kaldırılır, 簡易簿記 10万→0 şartı) — yıl parametreli |
| T-050 | P2 | todo | 消費税: 2割/3割特例 uygunluk şartları (基準期間・特定期間 ≤1,000万) uyarısı + 経過措置 tek satıcı 1億円 üst sınırı uyarısı |
| T-021 | P2 | todo | CI: `dashboard` işini Node 22'ye al ve `npm run check:tax` adımını ekle (TS ile Python 消費税 eşleşmesi) |
| T-027 | P1 | done (bu commit) | Yıllık 消費税/損益/CSV toplamları 5000 kayıtta sessizce kesiliyor |
| T-028 | P2 | done (bu commit) | `/admin/richmenu` ADMIN_KEY'i URL sorgusunda alıyor (log sızıntısı) |
| T-029 | P2 | done (bu commit) | Fatura kalemlerinde qty/unit_price üst sınırı yok (PostgreSQL bigint taşması → 500) |
| T-029b | P2 | done (bu commit) | `entries.amount` INTEGER (PG int4) ama API `lt=10**11` kabul ediyor → ¥2,147,483,648+ kayıt PostgreSQL'de 500 |
| T-051 | P2 | done (bu commit) | Banka CSV: birden çok 摘要 sütunu (MUFG 「摘要」+「摘要内容」) → yalnızca ilki alınıyor; karşı taraf adı kayboluyor |

---

## T-001 · Prototiplerde 令和8年度 経過措置 düzeltmesi
`docs/TAX_RULES.md` §1: 2026-10-01 〜 2028-09-30 arası kayıtsız alımlarda indirim **70%** (eskiden 50% sanılıyordu).
- `bot/app.py` (`saved_text`: "仕入税額控除50%" → tarihe göre oran), `web/index.html` (`creditRate`, açıklama metinleri) ve `web/dashboard.html` (vergi kartı notu, "経過措置50%" satırı) güncellensin.
- 2割特例 açıklamasına "個人は令和9・10年分 3割特例" notu eklensin.
- Kabul: iki dosyada "50%" geçen vergi metinleri doğru tarihlere göre 80/70/50/30 tablosunu yansıtır; tarayıcıda hata yok.

## T-002 · Vergi motoru `bot/tax/` (消費税)
- `bot/tax/consumption.py`: `tax_included(gross, rate)`, `input_credit_ratio(purchase_date)` (TAX_RULES tablosu), `compute(sales, purchases, method)` → `{output_tax, input_tax, payable}`; method ∈ `honsoku | kani(業種) | niwari | sanwari`. 100円未満切捨て.
- `sanwari` yalnızca 個人 ve 2027/2028 vergi yılları için izinli, aksi `ValueError`.
- Kabul: ≥15 test (sınır tarihleri 2026-09-30/10-01, 2028-09-30/10-01, 2030-10-01, 2031-10-01; yuvarlama; karışık oran). Saf fonksiyon, I/O yok.

## T-003 · `/entries/{user_id}` güvenliği
Şu an herkes herhangi bir kullanıcının kayıtlarını okuyabiliyor.
- Geçici: uç noktayı `ADMIN_KEY` gerektirecek şekilde kilitle (header `X-Admin-Key`). 
- Kabul: anahtarsız 401/403 testi; doğru anahtarla 200 testi.

## T-004 · Vergi motoru: 所得税
- `bot/tax/income.py`: dilim tablosu, 1,000円未満切捨て, 復興特別所得税 2.1%, 青色申告特別控除 (65/55/10万, kârdan büyük olamaz), 基礎控除 yıl parametreli (2025 tablosu ✅; 2026 tablosu Q-03 cevaplanana kadar `NotImplementedError` veya ⚠️ bayraklı).
- Kabul: dilim sınırlarında testler (1,950,000 / 3,300,000 / 6,950,000 ...), toplam vergi 100円未満切捨て.

## T-005 · REST API v1
- `GET /api/v1/summary?month=YYYY-MM`, `GET /api/v1/cashflow?months=6`, `GET /api/v1/invoices`.
- Kimlik: geçici olarak tenant başına API token (`Authorization: Bearer`), tablo `api_tokens`.
- Kabul: şema dokümante (`docs/API.md`), her uç nokta için yetkisiz/yetkili test.

## T-006 · PostgreSQL
- `DATABASE_URL` varsa Postgres (`psycopg` veya `asyncpg`), yoksa SQLite. Basit migration betiği (`bot/migrations/*.sql`, yalnızca ekleyici).
- `render.yaml`'a `DATABASE_URL` (`sync: false`) ekle; QUESTIONS'a "Render Postgres oluşturulmalı" yaz.
- Kabul: testler SQLite ile geçer; Postgres yolu en az bir CI job'unda (service container) test edilir.

## T-007 · dashboard-next → API
- `NEXT_PUBLIC_API_BASE` ile T-005 uç noktalarından veri çek; `MOCK` yalnızca API yoksa (demo modu, ekranda "デモデータ" rozeti).
- Kabul: `next build` geçer; API kapalıyken demo modu çalışır.

## T-008 · 適格請求書 API + PDF
- `POST /api/v1/invoices` (kalemler, oranlar), oran bazında toplam ve vergi (T-002 motoru), numara üretimi, PDF (zorunlu alanlar TAX_RULES §4).
- Kabul: zorunlu alan testi, yuvarlama testi, PDF üretimi testi (içerik metni kontrolü).

## T-009 · LINE: son kaydı düzenleme
- Kayıttan sonra hızlı yanıt: 「科目変更」「税率8%↔10%」; seçimle güncelleme.
- Kabul: webhook testleriyle düzenleme akışı.

## T-010 · 登録番号 doğrulama
- `bot/nta.py`: 国税庁 Web-API istemcisi, `NTA_APP_ID` yoksa yalnızca format kontrolü. Sonuç önbelleği.
- Kabul: httpx mock ile testler.

## T-011 · Görsel saklama + 電帳法 arama
- Depolama soyutlaması (yerel / S3 uyumlu), `entries` için tarih-tutar-karşı taraf arama uç noktası.

## T-012 · CSV dışa aktarma
- freee, マネーフォワード, 弥生 içe aktarma formatları; her biri için örnek dosya testi.

## T-013 · WhatsApp
- Meta Cloud API webhook doğrulama (`hub.verify_token`), mesaj → aynı servis katmanı.

## T-014 · Çok oranlı fiş OCR
- OCR çıktısı `lines: [{amount, rate}]`; kayıt oran başına bölünür.

## T-015 · 請求書管理 sayfası
- `dashboard-next/app/invoices/page.tsx`; dashboard'daki tablo bileşenini paylaş.

## T-016 · dashboard-next vergi kartı
- `ConsumptionTax` bileşeni: kayıtsız alımlar satırı (2026-10〜 70%), yöntem seçici (本則/簡易/2割/3割) — hesap mantığı `bot/tax/consumption.py` ile birebir (ileride API'den gelecek, T-005).
- Kabul: `next build` geçer; aynı örnek veriyle Python motoru ve UI aynı 納付見込額'yı verir (değer README/test notunda).
- ✅ Yapıldı: `dashboard-next/app/lib/tax.ts` (motorun TS kopyası), ortak örnek `app/lib/tax-example.json`
  (2026年分: 本則 差引 ¥1,419,500 / 簡易第5種 ¥1,168,000 / 2割 ¥467,200 / 3割 kullanılamaz; 中間納付 ¥520,000 sonrası 本則 納付見込 ¥899,500).
  Python: `bot/tests/test_tax_card_parity.py`; TS: `npm run check:tax` (Node 22+, CI'a ekleme → T-021).

## T-017 · 簡易課税 みなし仕入率 doğrulaması
- tax-watcher birincil kaynakla oranları ✅ yapınca `KANI_RATIO` için her tür adına test ekle.
- ✅ 2026-11-06 tax-watcher: oranlar NTA No.6505 (令和8年4月1日現在法令等) ile doğrulandı, kodla aynı (90/80/70/60/50/40). `bot/tax/consumption.py` yorumundaki 「❓ のため要確認」 notu da kaldırılmalı.

## T-004b · 令和8年分 基礎控除
- Q-03 cevaplanınca (TAX_RULES ✅) `bot/tax/income.py` → `BASIC_DEDUCTION[2026]` ve her kademe sınırı için test. `test_basic_deduction_2026_not_verified` testi kaldırılıp yerine gerçek testler gelir.
- ✅ Q-03 cevaplandı (tax-watcher 2026-11-06). Kural (令和8年分・令和9年分 aynı): 合計所得 ≤4,890,000 → 1,040,000 · ≤6,550,000 → 670,000 · ≤23,500,000 → 620,000 · ≤24,000,000 → 480,000 · ≤24,500,000 → 320,000 · ≤25,000,000 → 160,000 ·超 → 0. 2028+ ⚠️ → `NotImplementedError` kalsın.
- Dosyalar: `bot/tax/income.py` (`BASIC_DEDUCTION` 2026/2027), `bot/tests/` (her sınırda ±1 yen testi: 4,890,000/4,890,001, 6,550,000/6,550,001, 23,500,000/23,500,001 …), `bot/api.py` `/tax/income` (2026 artık 200), `dashboard-next/app/lib/income.ts` (`BASIC_2026`, `year !== 2025` korumasını 2025–2027'ye genişlet), `dashboard-next/app/tax/page.tsx` (yıl seçici). `web/index.html` `basicDed` prototip — dokunma (referans).
- Kabul: pytest yeşil; 2026年分 örnek (事業所得 3,000,000 → 基礎控除 1,040,000) API ve panelde aynı; `next build` geçer.
- Kaynak: TAX_RULES §2 (NTA 令和8年分 年末調整のしかた 102.pdf, 財務省 大綱, NTA No.1199).

## T-049 · 青色申告特別控除 令和9年分以後 (P1)
- Kural (令和8年度改正, 令和9年分以後): 75万 (正規の簿記 + 期限内 e-Tax + 優良な電子帳簿 veya デジタルシームレス保存 + 届出書) / 65万 (正規の簿記 + 期限内 e-Tax) / 書面申告 → 10万 (55万 kalkar) / 簡易簿記 10万, ancak 前々年分 事業・不動産 収入金額 > 1,000万 ise 0 / 現金主義の特例 → yalnızca 10万. 令和8年分 (2026) için mevcut 65/55/10 aynen kalır.
- Dosyalar: `bot/tax/income.py` (`BLUE_RETURN` → yıla göre izinli değerler, 2027+ için 750,000 ekle / 550,000 reddet), `bot/api.py` `/tax/income` (`blue` doğrulaması), `dashboard-next/app/tax/page.tsx` (seçenekler yıla göre: 2027+ 「75万円（優良電子帳簿＋e-Tax）」, 55万 gizli), `dashboard-next/app/lib/income.ts`.
- Kabul: 2026 → 550,000 kabul, 750,000 ValueError; 2027 → 750,000 kabul, 550,000 ValueError; 控除は所得を超えない testi; `next build` geçer. Ürünün 優良な電子帳簿 şartlarını karşılayıp karşılamadığına dair not `docs/` altına (iddia etme; QUESTIONS'a gerekirse).
- Kaynak: [NTA リーフレット](https://www.nta.go.jp/taxes/shiraberu/shinkoku/kojin_jigyo/0026007-003_02.pdf), TAX_RULES §2.

## T-050 · 2割/3割特例 uygunluk + 経過措置 1億円 sınırı (P2)
- Kural: 2割/3割特例 yalnızca 基準期間 課税売上高 ≤1,000万 (3割: ayrıca 特定期間 ≤1,000万, 個人のみ, 令和9・10年分). 経過措置: 2026-10-01 以後開始課税期間, 一の免税事業者等からの経過措置対象仕入 年 1億円 (税込) aşan kısım控除不可. Şu an `bot/tax/consumption.py` ve `dashboard-next/app/lib/tax.ts` bunları kontrol etmiyor (küçük müşteride nadir → P2).
- Dosyalar: `bot/tax/consumption.py` (`compute` için isteğe bağlı `base_period_sales` / `specific_period_sales` parametreleri → uygun değilse ValueError; `transitional_breakdown`'a satıcı bazında 1億 uyarı bayrağı), `dashboard-next/app/lib/tax.ts` (`methodUnavailable` mesajı), parity testi `bot/tests/test_tax_card_parity.py`.
- Kabul: 基準期間 10,000,000 → 2割 OK, 10,000,001 → reddedilir; tek satıcı 100,000,000 / 100,000,001 sınır testi; parametre verilmezse mevcut davranış değişmez.
- Kaynak: [NTA 3割特例](https://www.nta.go.jp/taxes/shiraberu/zeimokubetsu/shohi/keigenzeiritsu/invoice-review/pdf/0026004-099-01-2.pdf), [NTA インボイスQ&A 経過措置](https://www.nta.go.jp/taxes/shiraberu/zeimokubetsu/shohi/keigenzeiritsu/pdf/qa/01-15.pdf), TAX_RULES §1.

## T-012b · CSV şablon doğrulaması
- `bot/export.py` başlıkları ve 税区分 metinleri her yazılımın resmi şablon sayfasıyla karşılaştırılsın (kaynak URL'leri `docs/` altına). Fark varsa düzelt + test.

## T-018 · Token yönetimi
- Token iptali uç noktası; kullanıcı başına en fazla 5 token (en eskisi silinir — token tablosunda silme serbest, kişisel muhasebe verisi değil). Testler.

## T-021 · CI'da TS vergi eşleşme kontrolü
- `.github/workflows/ci.yml` dashboard işi: `node-version: "22"` + `npm run check:tax`. Kabul: CI yeşil, kontrol adımı görünür.

## T-023 · Gerçek fişlerle OCR doğruluğu
- Ürün sahibinden veya kamuya açık olmayan örnekler gerekiyorsa QUESTIONS'a yaz; kişisel bilgi içeren fişleri depoya koyma (maskele).
- `receipt_parser.py` kurallarını gerçek hatalara göre geliştir; her düzeltme için metin tabanlı test ekle.

## T-024 · Düşük güvenli OCR sonucu onayı
- `parse_receipt` güven bayrakları döndürsün (date_found, rate_breakdown_found); eksikse LINE yanıtında "日付を確認してください" vb. ve hızlı düzeltme butonları.

## T-027 · Yıllık toplamlarda 5000 satır kesmesi (review-fix, P1)
- `bot/api.py:136` (`/tax/consumption`), `:156` (`/pl` → `/tax/income`), `:270` (`/export.csv`) ve `bot/app.py` `/entries/{user_id}` `store.search_entries(..., limit=5000)` kullanıyor; `store.py:212` limiti 5000'e kırpıyor. Yılda >5000 kaydı olan kullanıcıda vergi/損益 **sessizce eksik** hesaplanır.
- Beklenen: toplamlar SQL `SUM ... GROUP BY kind, rate, ...` ile ya da sayfalı tam okuma ile; CSV tüm satırları içermeli. Kabul: 5001 kayıtlı testte toplam ve CSV satır sayısı doğru.

## T-028 · `/admin/richmenu` anahtarı sorgu dizesinde (review-fix, P2)
- `bot/app.py` `admin_richmenu(key: str = "")` → anahtar erişim log'larına düşer. Beklenen: `X-Admin-Key` başlığı (geriye uyum için sorgu bir süre kabul edilebilir, docs güncellenir). Test: başlıkla 200/403.

## T-029 · Fatura kalemi tutar sınırları (review-fix, P2)
- `bot/api.py` `ItemIn` / `bot/invoices.py:validate_items`: `qty`, `unit_price` için üst sınır yok; çok büyük değer PostgreSQL BIGINT'te 500 verir. Beklenen: ör. `qty ≤ 1e6`, `unit_price < 1e11`, satır tutarı < 1e11 → 400. Sınır testleri.

## T-029b · Kayıt tutarı int4 taşması (review-fix, P2)
- `store.py` `entries.amount INTEGER` → PostgreSQL'de int4 (≤ 2,147,483,647). `api.py` `EntryIn.amount` / `EntryPatch.amount` `lt=10**11` → 3e9 yen kayıt `NumericValueOutOfRange` → 500 (T-029 sırasında yerel PG 16'da doğrulandı).
- Seçenekler: (a) API sınırını `lt=2**31` / ör. `< 1e9` yap (şema değişmez), (b) `ALTER TABLE entries ALTER COLUMN amount TYPE BIGINT` (veri kaybı yok, genişletme; `init_db`'de idempotent). LINE/WhatsApp/OCR yolu da aynı sınırı kullanmalı. Test: sınırda 201, üstünde 400 (SQLite + PG).
- **Çözüm (a):** `store.MAX_ENTRY_AMOUNT = 20億` (int4 altında, en büyük fatura 税込 ≤ 1.1e9 sığar); `add_entry`/`update_entry` merkezi kontrol, API 422, banka→経費 400, LINE/WhatsApp metin+fiş Japonca uyarı. Şema değişmedi.

## T-040 · Hesap sistemi (P0)
- Tablolar: `accounts(id, email UNIQUE, password_hash, created_at, email_verified)`; `account_ledgers(account_id, user_id)` (bir hesap ↔ defter `user_id`). Parola: `hashlib.scrypt` (stdlib, tuzlu), en az 10 karakter.
- API: `POST /api/v1/auth/signup`, `/auth/login` (→ mevcut `api_tokens` token'ı), `/auth/link-line` (LINE 「パネル」 kodu ile LINE defterini hesaba bağla), `/auth/password-reset/request|confirm` (e-posta gönderimi soyut: `MAIL_PROVIDER` yoksa log'a yaz; Q-13).
- Panel: `/signup`, `/login`, `/connect` korunur. Testler: kayıt, yanlış parola, aynı e-posta, token ile erişim, kullanıcı ayrımı.
- ✅ API dilimi yapıldı: `bot/accounts.py`, `/api/v1/auth/{signup,login,me,link-line,password-reset/request,password-reset/confirm}` (docs/API.md). Bağlama, web defterinde veri varsa 409 verir (veri birleştirme yok). Panel sayfaları → T-040b. E-posta doğrulama (`email_verified`) şimdilik yalnızca sütun; gönderim Q-13'e bağlı.

## T-040b · Panel hesap sayfaları (P0)
- `dashboard-next/app/signup`, `/login`, `/reset` (hash'teki `rs_…` token), `/connect`: oturum açıksa LINE kodunu `POST /auth/link-line` ile bağla, değilse mevcut davranış (kodu token olarak kaydet). Token saklama mevcut `connect` ile aynı yerde; menüde oturum e-postası + çıkış (`DELETE /tokens/current`).
- Metinler Japonca; hata mesajları API'nin `detail` alanından. Demo modunda sayfalar "デモ" uyarısıyla çalışır.
- Kabul: `next build` geçer; yerel API ile kayıt → giriş → LINE kodu bağlama → özet görünür (elle/Playwright notu LOG'a).
- ✅ Yapıldı: `app/login`, `app/signup`, `app/reset`, `app/connect` (hesap varsa onaylı `link-line`), ortak `components/auth.tsx`; üst çubukta e-posta + ログアウト. Playwright e2e betiği CI'a T-035 ile girecek.

## T-041 · Ekip üyeleri (P1)
- `members(user_id(defter), account_id, role)`; owner davet kodu üretir; accountant: okuma + düzenleme, viewer: yalnız okuma. Tüm yazma uçlarında rol kontrolü + testler.

## T-042 · Abonelik (P0)
- `plans` sabitleri `bot/billing.py`: free (aylık 30 fiş, 3 fatura), personal, business — fiyatlar Q-11 cevaplanana kadar yer tutucu ve yapılandırmadan.
- Stripe Checkout + webhook (`/billing/webhook`, imza doğrulama), `subscriptions` tablosu. `STRIPE_SECRET_KEY` yoksa ödeme uçları 503 ve panelde "準備中". httpx ile Stripe REST (SDK şart değil), testlerde mock.

## T-043 · Yasal sayfalar (P0)
- Panel: `/legal/terms`, `/legal/privacy`, `/legal/tokushoho`. İçerik `app/lib/legal.ts` şablonu; satıcı bilgileri yapılandırmadan (Q-12). Her sayfanın başında "本ページは確認中のドラフトです" uyarısı (Q-12 cevaplanana kadar).
- Privacy: 利用目的, 第三者提供, 外国にある第三者への提供 (Render/Google Cloud bölgesi), 保存期間 (電帳法 7年), 開示請求 窓口.

## T-044 · Tanıtım + kayıt + sihirbaz (P1)
- `/lp` (ürün, LINE ile kayıt, fiyat tablosu Q-11'den, SSS), `/signup` sonrası 3 adımlı sihirbaz. Mobil uyumlu.

## T-045 · 確定申告 çıktıları (P1)
- `GET /api/v1/reports/blue-return.pdf?year=` (損益計算書 alan numaralarıyla), panelde indirme. e-Tax xtx için resmi şema araştırması `docs/ETAX.md` (kaynaklı); uygulama ayrı görev.

## T-046 · Veri dışa aktarma / silme / yedek (P1)
- `GET /api/v1/export/all.zip`; `POST /api/v1/account/delete-request` (hemen silmez, QUESTIONS'a değil `deletion_requests` tablosuna yazar); `scripts/backup.sh` (pg_dump) + `docs/OPERATIONS.md`.

## T-047 · Metinler (P2) — `app/lib/i18n.ts`, sayfalar buradan okur; `docs/JA_REVIEW.md` anadil kontrol listesi.

## T-048 · Güvenlik (P1)
- Basit bellek içi hız sınırı (IP + uç nokta), CORS `PANEL_URL`, `X-Content-Type-Options`, `Referrer-Policy`, `Strict-Transport-Security`; testler.

## T-051 · Banka CSV çoklu 摘要 sütunu (review-fix, P2)
- `bot/bank_csv.py` `parse()` (~satır 360–367): `desc` anahtarı ilk eşleşen sütuna atanıyor. MUFG/ゆうちょ biçiminde 「摘要」=振込/口座振替, karşı taraf 「摘要内容」'nde → `description` = 「口座振替」; `/bank/{id}/entry` ile oluşan 経費'in `store` alanı anlamsız, 消込 önerisinde müşteri ayırt edilemiyor.
- Beklenen: tüm `desc` eşleşen sütunları sırayla boşlukla birleştir (「口座振替 ﾗｸﾃﾝﾓﾊﾞｲﾙ」), boşları atla, 200 karakter sınırı korunur. Parmak izi değişeceği için mevcut içe aktarmaların yeniden alınmasında yinelenme tespiti bozulmamalı (ör. eski parmak izi biçimini de kontrol et) → test.
- Test: `tests/test_bank_and_entries.py::test_bank_csv_parse_variants` beklentisi güncellenir + yeniden içe aktarmada `duplicates` sayısı.
- ✅ Yapıldı: `bank_csv.parse` tüm 摘要 sütunlarını (boşları atlayarak) birleştirir; farklıysa `legacy_description` (yalnızca ilk sütun) döner. `store.insert_bank_rows` eski biçimin parmak izini de (eski sıra sayacıyla) kontrol eder → eski içe aktarmalar çoğalmaz. Testler `tests/test_bank_multi_desc.py`.
