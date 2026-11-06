# Ajan çalışma günlüğü (en yeni üstte)

Biçim: `## YYYY-MM-DD HH:MM JST · <rol> · <görev>` + 3–6 satır: ne yapıldı, testler, sonraki adım/engeller.

## 2026-11-07 06:44 JST · developer · T-052 Stripe webhook olay sırası (review-fix)
- `subscriptions`'a ekleyici sütun `last_event_created` (unix sn). `store.ADDED_COLUMNS` + `_add_columns`: mevcut veritabanlarına `init_db` sırasında eklenir (SQLite `PRAGMA table_info` kontrolü, PG `ADD COLUMN IF NOT EXISTS`); veri korunur, yıkıcı migration yok.
- `billing._upsert(event_created=…)`: karşılaştırma + yazma tek koşullu UPDATE (`WHERE last_event_created<=?`) → eski olay `ignored`, eşit/yeni uygulanır; eşzamanlı teslimde de eski olay kazanamaz. `checkout.session.completed` ve `customer.subscription.*` aynı kurala tabi; `cancel()` API yanıtı zamanı değiştirmez. Eksik/bozuk `created` → 0.
- Yeni `tests/test_billing_event_order.py` (14; deleted(200)→updated(100) free kalır, 199/200/201 sınırı, geç checkout, eski DB taşıma). 12'si eski kodda kırmızı. Kapı: pytest 293 geçti (SQLite) / 292+1 skip (yerel PostgreSQL 16); PG'de eski tabloya sütun ekleme elle doğrulandı. dashboard-next değişmedi.
- Sonraki: T-053 (review-fix, kayıt yarışında 500), ardından P0 T-043.

## 2026-11-07 05:50 JST · developer · T-042b abonelik paneli + kanal sınırları
- Yeni panel sayfası `/billing` (料金プラン): mevcut plan + durum/yenileme tarihi, bu ayki kullanım çubukları (経費 x/30, 請求書 x/3; %80 sarı, dolunca kırmızı), plan kartları (yer tutucu fiyat 「仮」), 「アップグレード」 → Checkout `url`, 「解約（期間末）」 onaylı; ödeme kapalıyken 「準備中」 bandı ve butonları. `?billing=success|cancel` bandı; demo modunda statik. Menüye 料金プラン, `/settings`'e bağlantı kartı.
- LINE/WhatsApp: `app.limit_notice` — sınır aşıldıysa 経費 kaydedilmez, Japonca uyarı + `{PANEL_URL}/billing/` (yoksa 「パネル」 yönlendirmesi). Fiş görselinde OCR'dan önce kontrol (görsel işlenmez/saklanmaz). 入金 ve komutlar (合計/取消) etkilenmez. Checkout `success_url`/`cancel_url` → `/billing/`.
- Yeni `tests/test_channel_limits.py` (9; 30/31 sınırı, ödeme kapalı, `BILLING_ENFORCE_LIMITS=0`, ücretli plan, görsel OCR öncesi, WhatsApp). Kapı: rebase sonrası pytest 279 geçti (SQLite + yerel PostgreSQL 16); `next build` geçti; Playwright ile demo + canlı (31/30 kullanım, success bandı) ekran kontrolü.
- Sonraki: P0 T-043 (yasal sayfalar).

## 2026-11-07 05:45 JST · reviewer · 1709d00..37ed9ee incelemesi (T-040, T-051, T-040b, T-042)
- Kapı başta yeşil (255, SQLite); T-051 eski parmak izi mantığı, T-040b `nextPath` (açık yönlendirme yok), T-042 sınır 30/31·3/4 ve imza doğrulaması doğru. Vergi kuralı değişikliği yok.
- **Düzeltmeler:** (1) `accounts.send_mail` sağlayıcı yokken sıfırlama bağlantısını INFO log'a ve tam e-postayı WARNING'e yazıyordu → gövde DEBUG, adres `t***@…` maskeli. (2) Parola sıfırlanınca hesabın diğer kullanılmamış `rs_` bağlantıları da geçersiz. (3) `link_ledger`: web defterinde abonelik varsa 409 (ücretli plan sahipsiz kalıyordu). (4) `billing.handle_event`: işleme hata verirse olay kaydı geri alınır → Stripe yeniden denemesi `duplicate` sayılmaz.
- **Yeni testler** `tests/test_review_auth_billing.py` (15): yukarıdakiler (5'i eski kodda kırmızı), abonelik durum sınırları (active/trialing/past_due ↔ unpaid/canceled/incomplete*), bilinmeyen price, e-posta büyük/küçük harf.
- **Açılan:** T-052 (P1) webhook olay sırası, T-053 (P2) kayıt yarışında 500.
- Kapı: pytest 270 geçti (SQLite + yerel PostgreSQL 16); dashboard-next değişmedi.

## 2026-11-07 04:46 JST · developer · T-042 abonelik (API dilimi)
- Yeni `bot/billing.py`: planlar (free 30 経費/3 請求書 aylık, personal/business sınırsız; fiyatlar yer tutucu Q-11), aylık kullanım (JST, `created_at`; BANK/INVOICE/DEMO kaynakları fiş sayılmaz), `check_limit` → 402 Japonca. Sınırlar yalnızca `STRIPE_SECRET_KEY` varken ve `BILLING_ENFORCE_LIMITS≠0` uygulanır (yükseltme yolu yokken kimse engellenmez).
- Stripe REST (httpx, SDK yok): Checkout oturumu (abonelik, `client_reference_id`=defter), dönem sonu iptal, webhook `Stripe-Signature` HMAC (300 sn), olay kimliğiyle idempotent; `checkout.session.completed` + `customer.subscription.*` işlenir. Anahtar yoksa ödeme uçları 503.
- Tablolar `subscriptions`, `billing_events` (ekleyici). render.yaml'a 4 `STRIPE_*` değişkeni `sync: false`; Q-10'a değer girilmesi notu, Q-11'e mevcut kullanıcılara geçiş süresi sorusu.
- Yeni `tests/test_billing.py` (18; sınır 30/31 ve 3/4, imza tolerans sınırı, httpx MockTransport ile gerçek form kodlaması — bir `data=` hatasını yakaladı). Kapı: pytest 255 geçti (SQLite + yerel PostgreSQL 16).
- Sonraki: T-042b (panel /billing + LINE/WhatsApp sınırı), ardından T-043.

## 2026-11-07 03:40 JST · developer · T-040b panel hesap sayfaları
- Yeni `/signup` (e-posta + parola×2, ≥10 文字 istemci kontrolü → `/connect/?welcome=1`), `/login` (`?next=` yalnız site içi yol), `/reset` (hash `rs_…` → yeni parola formu, token adres çubuğundan silinir; yoksa e-posta isteği, her zaman aynı mesaj). Ortak `components/auth.tsx`; hata metni API `detail`'inden, ağ hatasında 「デモデータで見る」 yönlendirmesi.
- `/connect`: hesapla oturum açıksa (`/auth/me`) kod hash'ten gelse bile onay butonuyla `POST /auth/link-line` (409 mesajı gösterilir); hesapsızsa eski davranış (kod = token, otomatik). Token saklama aynı `jsaas.token`.
- Üst satır: hesap oturumunda e-posta + ログアウト (`DELETE /tokens/current` → /login); yalnızca LINE kodu oturumunda eski 切断 (yalnız yerel) + 「アカウント連携」; demo modunda ログイン / 新規登録 / LINEで接続.
- Doğrulama: `next build` geçti; pytest 237 geçti. Yerel API (uvicorn + demo-seed) + statik `out/` ile Playwright: kayıt (kısa parola hatası) → hash kodla bağlama → ダッシュボード ライブ + e-posta → ログアウト → yanlış/doğru parola → sıfırlama isteği → `rs_` ile parola değişimi, ikinci kullanım reddi → ikinci hesapla aynı LINE defteri 409. Betik CI'a T-035 ile.
- Sonraki: P0 T-042 (abonelik, Stripe test modu), ardından T-043.

## 2026-11-07 02:44 JST · developer · T-051 banka CSV çoklu 摘要 sütunu
- `bank_csv.parse`: başlıktaki tüm 摘要 sütunları (摘要/摘要内容/備考/取引区分 …) soldan sağa boşlukla birleşir, boş hücreler atlanır (「口座振替 ﾗｸﾃﾝﾓﾊﾞｲﾙ」). Tutar/入出金 kalıbına da uyan sütunlar 摘要 sayılmaz; 200 karakter sınırı store'da korunuyor.
- Geriye uyum: birleşik metin ilk sütundan farklıysa satırda `legacy_description`; `store.insert_bank_rows` eski parmak izini (eski biçimin aynı gün sayacıyla) da arar → T-051 öncesi alınmış dosya yeniden yüklenince yinelenme 3/3 doğru, yeni kayıt yok.
- Yeni `tests/test_bank_multi_desc.py` (7; eski parmak izi testi kontrolsüz kodda kırmızı), `test_bank_csv_parse_variants` beklentisi güncellendi. Kapı: pytest 237 geçti (SQLite + yerel PostgreSQL 16).
- Sonraki: P0 T-040b (panel hesap sayfaları), ardından T-042, T-043.

## 2026-11-07 01:48 JST · developer · T-040 hesap sistemi (API dilimi)
- Yeni `bot/accounts.py`: scrypt (stdlib, 16 bayt tuz) parola, ≥10/≤128 karakter; tablolar `accounts`, `account_ledgers` (hesap ↔ tek defter), `password_resets` (yalnızca ekleyici, store.SCHEMA).
- `/api/v1/auth/signup|login|me|link-line|password-reset/request|confirm`. Kayıt boş `web:…` defteri açar, oturum = mevcut `api_tokens` → tüm uçlar aynen çalışır. LINE 「パネル」 koduyla bağlama: web defterinde veri varsa / LINE defteri başka hesaptaysa 409 (veri birleştirme yok), kod ve eski token'lar iptal. Sıfırlama 1 saat, tek kullanım, tüm oturumları kapatır; e-posta keşfi yok.
- `MAIL_PROVIDER`/`MAIL_API_KEY` render.yaml'a `sync: false` eklendi (Q-13'e not); sağlayıcı yokken e-posta log'a.
- Yeni `tests/test_accounts.py` (15). Kapı: rebase sonrası pytest 230 geçti (SQLite + yerel PostgreSQL 16).
- Sonraki: T-040b (panel /signup /login /reset /connect), ardından T-042, T-043.

## 2026-11-07 01:45 JST · reviewer · 5f49a70..58cca61 incelemesi (T-027, panel menüleri, T-028, T-029, T-029b, tax-watcher)
- Kapı başta yeşil (189, SQLite); dashboard-next `next build` geçti. T-027 sayfalama, T-028 başlık+compare_digest, T-029/T-029b int4 sınırları doğru; LINE düzenleme yolu tutar değiştirmiyor (taşma riski yok). TAX_RULES değişiklikleri kaynaklı + tarihli.
- **Düzeltme:** `store.delete_entry` banka kaynaklı 経費 silinince `bank_tx.entry_id` asılı kalıyordu → hareket bir daha kaydedilemiyordu (409). Artık bağ kaldırılıyor. `PATCH /entries/{id}` boş gövdede `null`/200 yerine 400.
- **Yeni testler** `tests/test_review_bank.py` (26): bank_csv tarih (和暦/年月日/geçersiz) ve tutar (△▲¥円) biçimleri, alt bilgi/0/boş satır atlama, başlık 15 satır sınırı, kısa satır; 消込 önerisi (fatura tarihinden önceki giriş yok, bir fatura tek öneri), tutar uyuşmazlığı 400, silme↔banka bağı, başka kullanıcının kaydı 404. Silme testi eski kodda kırmızı.
- **Açılan:** T-051 (P2 review-fix) banka CSV'de birden çok 摘要 sütunu → karşı taraf adı kayboluyor.
- Kapı: pytest 215 geçti (SQLite + yerel PostgreSQL 16).

## 2026-11-07 00:40 JST · developer · T-029b kayıt tutarı int4 taşması
- Seçenek (a): şema değişmeden `store.MAX_ENTRY_AMOUNT = 2,000,000,000` (< 2^31−1). 1e9 seçilmedi çünkü ödenen en büyük fatura 税込 ~1.1e9 → 売上 kaydı reddedilirdi.
- `store.check_amount` → `add_entry`/`update_entry` merkezi kontrol (`AmountOutOfRange`). API `EntryIn`/`EntryPatch` `lt=MAX_ENTRY_AMOUNT` (422, mevcut doğrulama kuralıyla aynı), `/bank/{id}/entry` büyük çekimde 400; LINE/WhatsApp metin ve fiş yolu 「金額が大きすぎます。1件20億円未満で入力してください。」 yanıtı, kayıt yok.
- Not: api.py'de `EntryIn.store` alanı `store` modülünü sınıf gövdesinde gölgeliyor → sabit modül düzeyinde içe aktarıldı.
- Yeni `tests/test_entry_limits.py` (7). Kapı: pytest 189 geçti (SQLite + yerel PostgreSQL 16).
- Sonraki: P0 T-040 (hesap sistemi).

## 2026-11-06 23:58 JST · tax-watcher · haftalık vergi kuralı kontrolü
- **Q-03 kapandı (✅):** 令和8・9年分 基礎控除 = ≤489万 104万 · ≤655万 67万 · ≤2,350万 62万 (2,350万超 değişmedi); 104万 tüm ≤2,350万 için değil. Kaynak: NTA 令和8年分 年末調整のしかた, 財務省 大綱, NTA No.1199. T-004b → todo. 令和10年分以後 ⚠️ (yalnızca ≤132万 99万 kesin).
- **Yeni kural:** 青色申告特別控除 令和9年分以後 75万/65万/10万 (書面55万 kalkar, 簡易簿記 前々年収入>1,000万 → 0) → T-049 (P1).
- ✅'a çekilen: 簡易課税 みなし仕入率 (No.6505; kodla aynı → T-017 yalnızca test), 3割特例 şartları, 経過措置 tablosu + 1億円/10億円 sınırı (NTA Q&A), 電帳法 電子取引 検索要件/猶予措置. Kod 1億 sınırını ve 2割/3割 uygunluk şartlarını kontrol etmiyor → T-050 (P2).
- Takvim (60 gün) yenilendi: 11/10, 11/30 予定納税 第2期, 12/1 改正施行, 12/10; yakın: 2027-01-12 年末調整分 源泉, 01-20 納期の特例. Kod değişmedi; kapı: bot pytest.

## 2026-11-06 23:20 JST · developer · T-029 fatura kalemi tutar sınırları
- `invoices.validate_items`: qty ≤ 1,000,000; unit_price, satır tutarı ve 税抜合計 < 1e9 円; en fazla 200 kalem → aşımda ValueError → API 400.
- Not: inceleyicinin önerdiği 1e11 PostgreSQL'de yetmiyor — `invoices.subtotal*/tax*/total` INTEGER (int4); 1e11-1 fatura yerel PG 16'da hâlâ 500 verdi. 1e9 ile total ≤ 1.1e9 < 2^31, şema değişikliği yok.
- Yeni `tests/test_invoice_limits.py` (13): her sınırın iki yanı, 10%/8% karışık en büyük fatura, API'de 400. Kapı: pytest 182 geçti (SQLite + yerel PostgreSQL 16).
- Aynı int4 sorunu `entries.amount`'ta da var (API 1e11 kabul ediyor, 3e9 → 500) → T-029b (review-fix) açıldı.
- Sonraki: T-029b, ardından P0 T-040.

## 2026-11-06 22:40 JST · developer · T-028 /admin/richmenu anahtarı başlığa taşındı
- `admin_richmenu` artık `X-Admin-Key` başlığını okuyor; `?key=` geriye uyum için kabul ediliyor ama log'a "deprecated" uyarısı yazıyor; başlık varsa sorgu yok sayılıyor. ADMIN_KEY boşsa her zaman 403.
- Belgeler: README, `setup_richmenu.py` docstring, QUESTIONS Q-01 komutu başlıklı curl'e güncellendi.
- Yeni `tests/test_admin_richmenu.py` (5, LINE çağrısı sahte modülle): başlıkla 200, yanlış/eksik 403, sorgu hâlâ 200, başlık önceliği, ADMIN_KEY yok → 403. Kapı: pytest 169 geçti (SQLite).
- Sonraki: T-029 (fatura kalemi üst sınırları, review-fix), ardından P0 T-040.

## 2026-11-06 21:30 JST · kurulum (Claude) · T-015, T-020, T-030–T-032 panel menüleri
- Panel artık sayfa yönlendirmeli: ortak kabuk `components/shell.tsx` (menü, arama, bağlantı/demo modu), ortak UI `components/ui.tsx`, demo veri `lib/demo.ts`.
- 請求書管理 (çok kalemli 適格請求書, 消込, PDF), 経費精算 (fiş OCR önizleme→onay, elle giriş, 電帳法 arama, satır içi düzenleme/silme), 銀行連携 (CSV içe aktarma Shift_JIS/UTF-8, tekrar korumalı, otomatik 消込 önerisi, çekimi gidere çevirme), 確定申告/税務 (損益, 所得税, 消費税 yöntemleri, freee/MF/弥生 CSV, takvim), 設定 (事業者情報 + 登録番号 kontrol hanesi, kanal durumu, bağlantı).
- API: PATCH/DELETE /entries/{id}, POST /receipts/ocr, /bank/import|transactions|match|{id}/entry, /channels. Testler: 164 (SQLite). Uçtan uca: yerel API + panel, tüm menüler canlı ve demo modda, 1366/390 px.

## 2026-11-06 15:10 JST · developer · T-027 yıllık toplamlarda 5000 satır kesmesi
- `store.entries_in_range()`: (d, id) anahtar kümesiyle sayfalı tam okuma (sayfa 2000). `/tax/consumption`, `/pl`, `/export.csv` ve `/entries/{user_id}` artık `limit=5000` yerine bunu kullanıyor; `search_entries` (電帳法 arama) değişmedi.
- Yeni `tests/test_year_totals.py` (5): 5001+1 kayıtta 損益 toplamı, 仕入税額 (¥100×5001), CSV satır sayısı, admin listesi; sayfa sınırlarında boşluk/çift kayıt yok; aralık dışı ve başka tenant hariç. Eski kodda 4'ü kırmızı.
- Kapı: pytest 157 geçti (SQLite + yerel PostgreSQL 16).
- Sonraki: T-020 (確定申告 önizleme) veya P2 review-fix'ler T-028/T-029.

## 2026-11-06 13:27 JST · reviewer · son 26 saat (c46d946..f1e4297)
- Kapı başta yeşil (143). 外税 regresyonu düzeltildi (T-023): `RATE_EXCLUDE` 「外税8%対象額」 satırlarını atıyordu → karışık oranlı 外税 fişte tüm tutar 10%'a yazılıyordu; artık yalnızca 外税額 hariç. `_rate_amount` 「税額 ¥80」 sonrasını tutar saymıyor.
- `hmac.compare_digest` str + ASCII olmayan girdi → TypeError/500 (LINE imza, WhatsApp imza/verify, ADMIN_KEY ×3); bayt karşılaştırmasına geçildi → 400/401/403.
- Yeni testler: `test_auth_hardening.py` (3), `test_receipt_parser.py` (+6: 外税 karışık, 税額 kesme, ¥…- 領収書, 小計 yedeği, 令和元年, okunamayan oran). Toplam 152. Not: 68 gerçek fiş depoda olmadığından 外税 değişikliği gerçek set üzerinde yeniden ölçülmeli.
- Açılan review-fix: T-027 (P1, yıllık toplamlar 5000 satırda kesiliyor), T-028 (richmenu anahtarı URL'de), T-029 (fatura kalemi üst sınır).
- Vergi oranları/eşikleri TAX_RULES ile tutarlı; みなし仕入率 hâlâ ❓ (T-017).

## 2026-11-06 06:30 JST · kurulum (Claude) · T-023 gerçek fişlerle OCR
- Ürün sahibinin 68 gerçek fişiyle ölçüm (görseller depoda değil). Tüm alanlar %6 → %70, toplam %19 → %85, yanlış kayıt %7 (docs/OCR.md).
- Toplam artık 10%/8%対象 satırlarından; 外税, kayıp baş rakam (内消費税 ile), 登録番号 kontrol hanesi, gün adıyla tarih onarımı, Vietnamca fişler.
- Docker imajı tessdata_best 4.1.0 indiriyor; okunamayan fişte bot okunan alanları gösterip tutarı istiyor. Testler: 143.

## 2026-11-06 05:30 JST · kurulum (Claude) · T-022 yapay zekâsız fiş okuma
- `receipt_ocr.py`: Pillow ön işleme (EXIF, ölçekleme, median, Otsu) + Tesseract jpn; İngilizce ikinci geçişle T番号 doğrulaması.
- `receipt_parser.py`: 合計/お会計, 10%/8%対象 (OCR varyantlarıyla), 和暦 tarih, T番号, mağaza adı, kalem tahmini.
- Ürün sahibinin isteğiyle varsayılan motor `tesseract`; `auto` modda AI yalnızca yedek. Render servisi Docker'a geçirildi (Q-08), CI imajı derleyip içinde OCR'ı test ediyor.
- Testler: 133 geçti (5 gerçek OCR fikstürü dahil). Sonraki: T-023 gerçek fişlerle doğruluk.

## 2026-11-06 04:55 JST · developer · T-016
- 消費税カード `bot/tax` ile hizalandı: 本則/簡易/2割/3割 seçici (kullanılamayan yöntem gerekçesiyle devre dışı; 3割 yalnızca 個人・2027/2028), 簡易 için 事業区分 seçimi (みなし仕入率 ❓ notuyla), 経過措置 (80%/70%) kayıtsız alım tablosu, eksi tutarda 還付見込額.
- `app/lib/tax.ts` = `consumption.py`'nin TS kopyası; ortak örnek `tax-example.json` iki tarafta da test ediliyor (本則 差引 ¥1,419,500 → 納付見込 ¥899,500).
- API `/tax/consumption` yanıtına ekleyici `unqualified` alanı (`transitional_breakdown`). Testler: pytest 107 geçti, `next build` ✓, `npm run check:tax` ✓, tarayıcıda konsol hatası yok.
- Not: kod commit'i (743716d) BACKLOG/LOG güncellemesinden ayrı gitti (betik hatası); bu commit onu tamamlar.
- Sonraki: T-020 (確定申告 önizleme). Yeni alt görev T-021 (CI'da check:tax).

## 2026-11-06 02:35 JST · kurulum (Claude) · T-014 + 確定申告 API
- OCR çıktısı oran bazında (total10/total8); karışık fiş iki kayda bölünüyor (`normalize_ocr`), görsel yolu temizleniyor.
- `/api/v1/pl` (損益計算書, kalem bazında) ve `/api/v1/tax/income` (2026 için Q-03 nedeniyle 409). Testler: 99 geçti.

## 2026-11-06 04:30 JST · kurulum (Claude) · T-006
- `store.py`: `DATABASE_URL` varsa PostgreSQL (psycopg 3), yoksa SQLite; ortak `tx()` katmanı, `RETURNING id`, taşınabilir LIKE kaçışı.
- render.yaml: `jsaas-db` (free, singapore) + `DATABASE_URL`; CI'a PostgreSQL 16 servisiyle `bot-postgres` işi.
- Testler: 94/94 SQLite, 94/94 PostgreSQL 16 (yerel).

## 2026-11-06 03:55 JST · kurulum (Claude) · T-009, T-013, T-018
- Sohbet çekirdeği `app.respond()` kanaldan bağımsız hale getirildi; LINE ve WhatsApp aynı mantığı kullanıyor.
- LINE/WA: 「科目変更」 (kalem seçimi), 「税率8%/10%」 ile son kaydı düzeltme.
- WhatsApp Cloud API webhook (imza doğrulama, buton/liste mesajları, görsel → OCR), defter anahtarı `wa:<tel>`.
- Token iptali `DELETE /api/v1/tokens/current`, kullanıcı başına en fazla 5 token. Testler: 94 geçti.

## 2026-11-06 03:20 JST · kurulum (Claude) · T-007
- dashboard-next API'ye bağlandı (`app/lib/api.ts`): token varsa canlı veri (summary/cashflow/tax/invoices/profile), yoksa "デモデータ" rozetiyle mock. 消込 ve 請求書作成 API'ye yazar; fatura no tıklanınca PDF.
- `/connect#tk_...` bağlantı sayfası (LINE 「パネル」 linki). Static export → Render `jsaas-panel` (render.yaml).
- Yerelde uçtan uca denendi: demo-seed → connect → canlı KPI ¥4,250,000 → 消込 API'ye gitti.

## 2026-11-06 02:50 JST · kurulum (Claude) · T-005, T-008, T-012
- `store.py` veri katmanı (entries, api_tokens, invoices, profiles); `api.py` REST v1 (summary, cashflow, entries araması, 消費税, profil, faturalar, PDF, CSV), `docs/API.md`.
- 適格請求書: oran başına tek yuvarlama, PDF'de IPAゴシック gömülü (`bot/fonts/`, IPA lisansı). 入金消込 oran başına 売上 kaydı yazar.
- LINE 「パネル」 komutu web token'ı verir; `/api/v1/admin/demo-seed` örnek defter. Testler: 85 geçti.
- Sonraki: T-007 (dashboard → API), T-009, T-018.

## 2026-11-06 02:10 JST · kurulum (Claude) · T-004
- `bot/tax/income.py`: 速算表, 1,000円/100円 切捨て, 復興特別所得税 2.1%, 青色控除 (kârla sınırlı), 基礎控除 2025.
- 2026 基礎控除 Q-03 doğrulanana kadar `NotImplementedError` → T-004b (blocked). Testler: 70 geçti.

## 2026-11-06 02:00 JST · kurulum (Claude) · T-001, T-002, T-003
- `bot/tax/consumption.py`: 税込→税額, 経過措置 (80/70/50/30/0), 本則/簡易/2割/3割 hesap; 税率ごと端数処理, 100円未満切捨て.
- Bot yanıtı kayıtsız alım oranını tarihe göre gösteriyor; `web/` prototipleri 令和8年度改正'ye göre düzeltildi.
- `/entries/{user_id}` artık `X-Admin-Key` istiyor. Testler: 46 geçti.
- Sonraki: T-004 (所得税 motoru), T-005 (REST API).

## 2026-11-05 · kurulum (Claude, ürün sahibiyle)
- Depo proje yapısına geçirildi: `bot/`, `dashboard-next/`, `web/`, `docs/`, `agents/`, `tasks/`; Render `rootDir: bot`.
- 11 bot testi + CI (pytest, next build). Next.js dashboard derlendi ve masaüstü/telefon genişliğinde denendi.
- Vergi araştırması: 令和8年度改正 ile 経過措置 2026-10〜 %70, 3割特例 (個人, 2027–2028) → TAX_RULES + T-001/T-002.
- Açık sorular: Q-01 LINE kanalı, Q-02 API anahtarı, Q-03 基礎控除 2026, Q-04 hedef müşteri.
