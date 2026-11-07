# BACKLOG — tek görev kuyruğu

Kurallar ve durum sözlüğü: `CLAUDE.md`. Öncelik: P0 (önce) > P1 > P2. Her görevin kabul ölçütü vardır; tek çalışmada bitmeyecekse önce böl.

**Önerilen sıra (planner, 2026-11-07):** P0 bitti. Sprint sonuna kadar (2026-11-09 00:00 JST): review-fix → T-021 → T-048 → T-048b → T-046 → T-046b → T-045 → T-044 → T-044b → T-011 → T-049. Sonra P2.

| ID | Öncelik | Durum | Görev |
|---|---|---|---|
| T-001 | P0 | done (bu commit) | Prototiplerde 令和8年度 経過措置 düzeltmesi |
| T-002 | P0 | done (bu commit) | Vergi motoru `bot/tax/` (消費税) + testler |
| T-003 | P0 | done (bu commit) | `/entries/{user_id}` uç noktasını kapat / kimlik doğrulaması ekle |
| T-004 | P1 | done (2025 tablosu) | Vergi motoru: 所得税 (所得税・復興税・青色控除・基礎控除) |
| T-004b | P1 | done (bu commit) | `BASIC_DEDUCTION[2026]` ve `[2027]` (令和8・9年分) tablosunu ekle + sınır testleri (Q-03 cevaplandı) |
| T-005 | P1 | done | REST API v1: tenant'a göre özet, nakit akışı, faturalar |
| T-006 | P1 | done | PostgreSQL desteği (`DATABASE_URL`), SQLite yedek |
| T-007 | P1 | done | dashboard-next'i API'ye bağla (mock → fetch, yükleniyor/hata durumları) |
| T-008 | P1 | done | 適格請求書 oluşturma API + PDF |
| T-009 | P1 | done | LINE: son kaydı düzenleme (勘定科目 / 税率 hızlı yanıtla) |
| T-010 | P2 | todo | 登録番号 doğrulama (国税庁 Web-API, mock'lu testler) |
| T-011 | P1 | todo | Fiş görselleri için depolama soyutlaması (yerel / S3 uyumlu); Render diski kalıcı değil → her deploy'da `receipts/` siliniyor (Q-14) |
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
| T-025 | P1 | done (bu commit) | LINE görsel işleme süresi: OCR uzun sürerse önce 「読み取り中…」 yanıtı, sonuç push mesajla (reply token süresi) |
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
| T-041 | P1 | done (bu commit; panel → T-041b) | Ekip üyeleri: bir işletmeye çok kullanıcı (owner / accountant / viewer), davet kodu, yetki kontrolü |
| T-041b | P1 | done (bu commit) | Panel: /settings 「メンバー」 bölümü (davet kodu üret/iptal, rol değiştir, çıkar) + /join sayfası + üst menüde defter değiştirici; viewer'da düzenleme düğmeleri gizli (T-041 API'si) |
| T-042 | P0 | done (bu commit; panel+LINE → T-042b) | Abonelik: planlar + Stripe test modu (Checkout, webhook, iptal), plan bazlı sınırlar; anahtar yoksa ödeme kapalı |
| T-042b | P0 | done (bu commit) | Abonelik: panel 料金プラン sayfası (/billing: plan kartları, Checkout yönlendirme, 解約, kullanım, 準備中 durumu) + LINE/WhatsApp kayıt yolunda sınır (Japonca uyarı) |
| T-043 | P0 | done (bu commit; içerik onayı Q-12) | Yasal sayfalar: 利用規約, プライバシーポリシー (APPI), 特定商取引法に基づく表記 — şablon + yapılandırma, 「要確認」 işaretli |
| T-044 | P1 | todo | Tanıtım sayfası `/lp` (ürün, LINE ile başla, fiyat tablosu `PLANS`'tan, SSS) |
| T-044b | P1 | todo | Kayıt sonrası 3 adımlı kurulum sihirbazı `/welcome` (事業者情報 → LINE bağlantısı → ilk fiş) |
| T-045 | P1 | todo | 青色申告決算書 (損益計算書) PDF: `GET /api/v1/reports/blue-return.pdf?year=` + panel 確定申告 sayfasında indirme |
| T-045b | P2 | todo | e-Tax xtx araştırma notu `docs/ETAX.md` (resmi şema/仕様 kaynakları, yalnızca belge) |
| T-046 | P1 | todo | Tüm veri dışa aktarma: `GET /api/v1/export/all.zip` (kayıtlar CSV + faturalar CSV/PDF) + 設定'te indirme düğmesi |
| T-046b | P1 | todo | Hesap silme talebi: `POST /api/v1/account/delete-request` → `deletion_requests` tablosu (hemen silmez) + 設定'te onaylı düğme |
| T-046c | P2 | todo | PostgreSQL yedekleme betiği `scripts/backup.sh` (pg_dump) + `docs/OPERATIONS.md` |
| T-047 | P0 | done (dilim 1: altyapı + seçici + kabuk + 設定 + tüm kart başlıkları) | **Dil seçeneği (ürün sahibi isteği 2026-11-07):** 日本語 / Türkçe / English |
| T-047b | P0 | todo | Dil dilim 2: ホーム gövdesi, 請求書, 経費, 銀行, 税務, 料金プラン, メンバー kartı, login/signup/reset/join/connect metinleri `t()` ile; sözlüğe tr+en ekle |
| T-047c | P0 | doing (developer, 2026-11-07) | Bot dili: `profiles.lang` sütunu, `言語`/`dil`/`language` komutu + hızlı yanıt, `bot/i18n.py` ja/tr/en, testler |
| T-048 | P1 | done (bu commit) | Güvenlik: bellek içi hız sınırı (login / signup / password-reset / OCR) → 429 |
| T-048b | P1 | todo | Güvenlik: CORS `*` yerine PANEL_URL (+ localhost geliştirme) ve güvenlik başlıkları (nosniff, Referrer-Policy, HSTS, frame-ancestors) |
| T-017 | P2 | todo | `KANI_RATIO` testleri — みなし仕入率 TAX_RULES'ta ✅ (tax-watcher 2026-11-06, NTA No.6505); yalnızca test eklenecek |
| T-049 | P1 | todo | 所得税: 青色申告特別控除 令和9年分以後 (75万 kademesi, 55万 kaldırılır, 簡易簿記 10万→0 şartı) — yıl parametreli |
| T-050 | P2 | todo | 消費税: 2割/3割特例 uygunluk şartları (基準期間・特定期間 ≤1,000万) uyarısı + 経過措置 tek satıcı 1億円 üst sınırı uyarısı |
| T-021 | P1 | done (bu commit) | CI: dashboard işi (Node 22, `npm ci`, `next build`, `check:tax`, `check:legal`, `check:team`) — panel kontrolleri şu an CI'da yok |
| T-027 | P1 | done (bu commit) | Yıllık 消費税/損益/CSV toplamları 5000 kayıtta sessizce kesiliyor |
| T-028 | P2 | done (bu commit) | `/admin/richmenu` ADMIN_KEY'i URL sorgusunda alıyor (log sızıntısı) |
| T-029 | P2 | done (bu commit) | Fatura kalemlerinde qty/unit_price üst sınırı yok (PostgreSQL bigint taşması → 500) |
| T-029b | P2 | done (bu commit) | `entries.amount` INTEGER (PG int4) ama API `lt=10**11` kabul ediyor → ¥2,147,483,648+ kayıt PostgreSQL'de 500 |
| T-051 | P2 | done (bu commit) | Banka CSV: birden çok 摘要 sütunu (MUFG 「摘要」+「摘要内容」) → yalnızca ilki alınıyor; karşı taraf adı kayboluyor |
| T-052 | P1 | done (bu commit) | Stripe webhook olay sırası: geç gelen eski `customer.subscription.updated`, `deleted` sonrası aboneliği yeniden ücretli yapabilir |
| T-053 | P2 | done (c5108d7) | Eşzamanlı aynı e-postayla kayıt → UNIQUE ihlali 500 (409 olmalı) |
| T-054 | P2 | done (bu commit) | Çok oranlı fiş plan sınırını aşıyor / iki kota yiyor |

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

## T-011 · Görsel saklama (P1, planner 2026-11-07 yükseltti)
- Sorun: `app.process_image` görseli konteyner diskine (`receipts/`) yazıyor; render.yaml'da disk yok ve `main` saatte bir yayınlanıyor → her deploy'da görseller kayboluyor (gizlilik politikası ve 電帳法 saklama iddiasıyla çelişir). Arama uç noktası (`/api/v1/entries`) zaten ✅.
- Yap: `bot/storage.py` (`put(key, bytes)`, `get(key)`), sürücü `STORAGE_BACKEND=local|s3`; s3 için S3 uyumlu (R2/S3) imzalı istek — yeni paket gerekiyorsa sürümü sabitle. Değişkenler render.yaml'a `sync: false` (`STORAGE_BUCKET`, `STORAGE_ENDPOINT`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`); değer Q-14. Anahtar yoksa yerel (bugünkü davranış) + başlangıçta uyarı log'u.
- Kabul: `process_image` ve `image_path` storage üzerinden; yerel sürücü testleri + s3 sürücüsü httpx MockTransport ile (imza başlığı var, PUT/GET yolu doğru); mevcut testler yeşil.

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
- ✅ 2026-11-07 developer: `BASIC_DEDUCTION[2026/2027]`, API 2026/2027 → 200 (2028 → 409), panel `BASIC_DEDUCTION` haritası, parity testi `test_income_card_parity.py` + `check:tax` 所得税 örnekleri.

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

## T-012b · CSV şablon doğrulaması (P2)
- `bot/export.py` başlıkları ve 税区分 metinleri her yazılımın resmi şablon sayfasıyla karşılaştırılsın (kaynak URL + kontrol tarihi `docs/EXPORT.md`). Fark varsa düzelt + test.
- Kabul: 3 yazılımın her biri için kaynaklı başlık listesi; örnek CSV testi başlıkları birebir karşılaştırır; doğrulanamayan alan `docs/EXPORT.md`'de ⚠️.

## T-018 · Token yönetimi
- Token iptali uç noktası; kullanıcı başına en fazla 5 token (en eskisi silinir — token tablosunda silme serbest, kişisel muhasebe verisi değil). Testler.

## T-021 · CI'da panel işi (P1)
- `.github/workflows/ci.yml`'a `dashboard` işi: `actions/setup-node` `node-version: "22"`, `working-directory: dashboard-next`, `npm ci`, `npx next build`, `npm run check:tax`, `npm run check:legal`, `npm run check:team`.
- Kabul: push sonrası Actions'ta iş yeşil ve 3 kontrol adımı görünür (GitHub MCP `actions_list` ile doğrula, LOG'a run numarası). Kırmızıysa aynı çalışmada düzelt.

## T-023 · Gerçek fişlerle OCR doğruluğu
- Ürün sahibinden veya kamuya açık olmayan örnekler gerekiyorsa QUESTIONS'a yaz; kişisel bilgi içeren fişleri depoya koyma (maskele).
- `receipt_parser.py` kurallarını gerçek hatalara göre geliştir; her düzeltme için metin tabanlı test ekle.

## T-024 · Düşük güvenli OCR sonucu onayı (P2)
- Kabul: tarih bulunamayan sahte OCR → yanıtta 「日付を確認してください」 + hızlı yanıt; oran kırılımı tahmini → uyarı; güvenli sonuçta mevcut yanıt değişmez (webhook testleri).
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
- ✅ API dilimi yapıldı: `bot/team.py`, tablolar `ledger_members`, `team_invites`, `api_tokens.account_id` (ekleyici). `api.py` `current_principal` / `writer_user` / `owner_user`; `/api/v1/team/*` (docs/API.md). Testler `tests/test_team.py`. LINE/WhatsApp kanalları değişmedi (yalnızca sahibin kanalı). Plan bazlı üye sınırı yok (sabit 20) — fiyatlandırma kararıyla (Q-11) gerekirse eklenir.

## T-041b · Ekip paneli (P1)
- `dashboard-next/app/settings`: 「メンバー」 kartı — `GET /team/members`, 「招待コードを発行」 (役割: 編集者=accountant / 閲覧者=viewer) → kodu bir kez göster + kopyala, 招待取消, 役割変更, 削除 (onaylı). Yalnızca `auth/me.role === "owner"` görür.
- `/join` sayfası: kod gir → `POST /team/join` → token'ı kaydet, panele yönlendir. Üst menü: `GET /team/ledgers` ile defter seçici → `POST /team/switch`.
- Viewer: kayıt ekle/düzenle/sil, fatura oluştur, banka içe aktar düğmeleri gizli/pasif + 「閲覧専用」 rozeti. Demo modunda statik. `next build` geçer.
- ✅ Yapıldı: `app/lib/team.ts` (saf: rol etiketleri, `parseRole`/`canWrite`/`isOwner`, davet kodu çıkarma, `/join/#iv_…` bağlantısı, JST tarih, defter listesi) + `npm run check:team`. `settings/members.tsx` (owner: davet üret → kod+bağlantı bir kez, 取消, 役割変更, 2 adımlı 削除; diğer roller: rol açıklaması; demo statik). `/join` (hash'ten kod, giriş yoksa sessionStorage'da tutup /login veya /signup → geri dön). Üst menü: `/team/ledgers` defter seçici → `/team/switch` (eski token iptal edilir). `useShell()` → `role`, `canEdit`; rol "live"dan önce çözülür. Viewer: ホーム クイックアクション/消込, 経費 formları/satır içi düzenleme/silme, 請求書作成/入金消込, 銀行 取込/消込/経費登録, 事業者情報 kaydı gizli + 「閲覧専用」 rozeti; 料金プラン düğmeleri yalnızca owner.

## T-042 · Abonelik (P0)
- `plans` sabitleri `bot/billing.py`: free (aylık 30 fiş, 3 fatura), personal, business — fiyatlar Q-11 cevaplanana kadar yer tutucu ve yapılandırmadan.
- Stripe Checkout + webhook (`/billing/webhook`, imza doğrulama), `subscriptions` tablosu. `STRIPE_SECRET_KEY` yoksa ödeme uçları 503 ve panelde "準備中". httpx ile Stripe REST (SDK şart değil), testlerde mock.

- ✅ API dilimi yapıldı: `bot/billing.py` (PLANS yer tutucu, `usage`/`check_limit`, Stripe REST httpx + form kodlama, imza doğrulama, olay idempotensi), tablolar `subscriptions`, `billing_events`; `/api/v1/billing/{plans,status,checkout,cancel,webhook}` (docs/API.md). Sınırlar web `POST /entries` (exp) ve `POST /invoices`'ta; yalnızca ödeme açıkken. Panel ve LINE/WhatsApp → T-042b.

## T-042b · Abonelik paneli + kanal sınırları (P0)
- `dashboard-next/app/billing`: `/billing/plans` + `/billing/status` → plan kartları (yer tutucu fiyat 「仮」 etiketi), bu ayki kullanım (経費 x/30, 請求書 x/3), 「アップグレード」 → `POST /billing/checkout` → `url`'e git, 「解約（期間末）」; `payments_enabled=false` ise 「準備中」. `?billing=success|cancel` sonuç bandı; `/settings`'e bağlantı. Demo modunda statik.
- `bot/app.py` + `whatsapp.py`: metin/fiş kaydından önce `billing.check_limit(user_id, "receipts")`; aşılırsa kaydetmeden Japonca uyarı + panel bağlantısı. Testler (LINE + WhatsApp).
- ✅ Yapıldı: `/billing` sayfası (plan kartları 「仮」, kullanım çubukları, Checkout, 期間末解約, 準備中 bandı, `?billing=` sonucu, demo statik), menü + `/settings` bağlantısı; Checkout dönüşü artık `/billing/`. LINE/WhatsApp: `app.limit_notice` metin kaydı ve fiş görselinde (OCR'dan önce) — `tests/test_channel_limits.py`.

## T-043 · Yasal sayfalar (P0)
- Panel: `/legal/terms`, `/legal/privacy`, `/legal/tokushoho`. İçerik `app/lib/legal.ts` şablonu; satıcı bilgileri yapılandırmadan (Q-12). Her sayfanın başında "本ページは確認中のドラフトです" uyarısı (Q-12 cevaplanana kadar).
- Privacy: 利用目的, 第三者提供, 外国にある第三者への提供 (Render/Google Cloud bölgesi), 保存期間 (電帳法 7年), 開示請求 窓口.
- ✅ Yapıldı: `app/lib/legal.ts` (saf TS şablon; satıcı bilgisi `NEXT_PUBLIC_LEGAL_*` → yoksa 「要確認」), `components/legal.tsx` (sunucu bileşeni, JS'siz okunur; ドラフト bandı, 「要確認」 rozetleri), üç sayfa; bağlantılar: kayıt formu (同意文), giriş kartları altı, kenar menü altı, 料金プラン. 保存期間 TAX_RULES'ta ⚠️ olduğu için sayı yazılmadı (要確認). Kontrol: `npm run check:legal` (şablon + `out/legal` HTML). CI'a ekleme T-021 ile.

## T-044 · Tanıtım sayfası (P1)
- `dashboard-next/app/lp/page.tsx` (sunucu bileşeni, JS'siz okunur): kahraman bölümü (LINE'a fiş at → 帳簿・インボイス・確定申告), 3 özellik kartı, fiyat tablosu (`/billing/plans` yer tutucu fiyatlar 「仮」; API yoksa statik yedek), SSS (≥5 soru, vergi danışmanlığı değildir notu), 「無料で始める」 → `/signup/`, alt bilgide yasal sayfa bağlantıları.
- Kabul: `next build` geçer; 375px'te yatay taşma yok (Playwright notu LOG'a); metinler Japonca, uydurma rakam/iddia yok (ör. "電帳法対応" yalnızca T-011/T-034 bitince).

## T-044b · Kurulum sihirbazı (P1)
- `/welcome`: kayıt sonrası yönlendirme; adım 1 事業者情報 (mevcut settings API), adım 2 LINE bağlantısı (`/connect` akışı veya 「あとで」), adım 3 ilk fiş (経費 sayfasına yükleme veya LINE). İlerleme adım göstergesi; atlanabilir; tamamlanınca ホーム.
- Kabul: `next build` geçer; signup → /welcome yönlendirmesi; demo modunda statik; viewer/üye katılımında sihirbaz gösterilmez.

## T-045 · 青色申告決算書 PDF (P1)
- `GET /api/v1/reports/blue-return.pdf?year=` — mevcut `/api/v1/pl` verisinden 損益計算書 (売上 ①, 売上原価, 経費 科目別, 差引金額, 青色申告特別控除前の所得). Alan numaraları yalnızca NTA 様式 kaynağıyla (`docs/TAX_RULES.md`'ye URL + tarih); emin olunmayan numara yazılmaz, ad ile gösterilir. 「参考資料（提出用ではありません）」 notu. PDF üretimi mevcut fatura PDF altyapısı + `bot/fonts`.
- Panel `/tax`: 「決算書PDF」 indirme düğmesi (viewer da indirebilir).
- Kabul: yetkisiz 401, başka defter erişilemez, PDF metninde toplamlar `/pl` ile aynı (test), kayıt yokken boş tablo; `next build` geçer.

## T-045b · e-Tax araştırması (P2)
- `docs/ETAX.md`: e-Tax 仕様書 (XML/xtx, 帳票 ID'leri, 青色申告決算書・確定申告書B/第一表), 個人向け 外部ソフト連携 seçenekleri, kaynak URL + kontrol tarihi. Kod yok. Kabul: her iddia kaynaklı; uygulama için 2–3 alt görev önerisi BACKLOG'a.

## T-046 · Tüm veri ZIP (P1)
- `GET /api/v1/export/all.zip`: `entries.csv` (mevcut export biçimi, tüm yıllar), `invoices.csv`, `invoices/<番号>.pdf`, `README.txt` (Japonca, oluşturma zamanı JST). Bellekte (`zipfile`), sınırsız satır (T-027 dersi). Viewer dahil okuma yetkisi olan herkes.
- Panel 設定: 「全データをダウンロード」.
- Kabul: 401/başka defter testleri, ZIP içindeki dosya listesi ve satır sayısı testi (>5000 kayıt dahil), `next build` geçer.

## T-046b · Hesap silme talebi (P1)
- `deletion_requests(id, user_id, account_id, requested_at, status)` (ekleyici). `POST /api/v1/account/delete-request` yalnızca owner; tekrar talep idempotent; `GET` durum. Veri silinmez (CLAUDE.md: veri silme yok) — işlem insan adımı, `docs/OPERATIONS.md`'ye not. Panel 設定: 2 adımlı onay + 「申請済み」 durumu; ödeme aktifse önce 解約 uyarısı.
- Kabul: owner 202, accountant/viewer 403, idempotent test; `next build` geçer.

## T-046c · Yedekleme (P2)
- `scripts/backup.sh` (`pg_dump "$DATABASE_URL" | gzip`, tarih adlı dosya, sır yazmaz) + `docs/OPERATIONS.md` (geri yükleme adımları, Render free DB 30 gün sınırı — Q-07). Kabul: `bash -n` + shellcheck temiz (varsa); belge geri yükleme komutunu içerir.

## T-047 · Dil seçeneği ja / tr / en (P0 — review-fix'lerden hemen sonra, T-040'tan önce)
Ürün sahibi 2026-11-07'de istedi: programda dil seçeneği olsun, **Türkçe de olsun**.
- `dashboard-next/app/lib/i18n.ts`: `ja` (varsayılan), `tr`, `en` sözlükleri + `useT()` hook; seçim localStorage `jsaas.lang` (try/catch), `<html lang>` güncellenir.
- Üst çubuğa (Topbar) ve 設定 sayfasına dil seçici (日本語 / Türkçe / English).
- Dilim 1 (bu çalışma): shell (menü, üst çubuk, komut paleti), ホーム, 設定. Dilim 2 (T-047b): 請求書, 経費, 銀行, 税務, connect.
- Vergi/muhasebe terimleri (確定申告, 消費税, 適格請求書, 勘定科目 adları) tr/en'de Japonca terim parantez içinde kalır: "Kesin beyan (確定申告)". Saklanan veri (勘定科目) her zaman Japonca; yalnızca görüntü çevrilir. Fatura PDF'i Japonca kalır (yasal belge).
- Bot (T-047c): `profiles.lang` sütunu ekle (sütun ekleme serbest), `言語` / `dil` / `language` komutu + hızlı yanıt; bot metinleri `bot/i18n.py`'de ja/tr/en. Testler: her dilde temel akış.
- `docs/JA_REVIEW.md`: anadil kontrol listesi.
- Kabul: `next build` geçer; taşınan sayfalarda sabit Japonca dize kalmaz (grep notu LOG'a); görünüm değişmez.

## T-019 · PostgreSQL bağlantı havuzu (P2)
- `psycopg_pool` (sürüm sabit) yalnızca `DATABASE_URL` varken; istek süresi > 1 sn ise WARNING log (yol + süre, kişisel veri yok).
- Kabul: SQLite testleri değişmeden yeşil; CI bot-postgres işi yeşil; havuz kapanışı uygulama kapanışında.

## T-026 · OCR kırmızı damga bastırma (P2)
- `receipt_ocr` ön işleme: HSV kırmızı aralığı → beyaz (Pillow ile; yeni paket yok). Kabul: `docs/OCR.md` ölçüm betiğiyle önce/sonra doğruluk (toplam alanı düşmemeli), damgalı sentetik görsel testi.

## T-033 · Banka CSV gerçek başlıkları (P2)
- Her banka için kamuya açık örnek/yardım sayfasındaki başlık satırı (kaynak URL `docs/BANK_CSV.md`), kişisel veri içermeyen sentetik fixture + `bank_csv.parse` testi. Doğrulanamayan banka ⚠️ ile listelenir.
- Kabul: ≥5 banka testli; mevcut testler yeşil.

## T-034 · Panelde fiş görseli (P2, T-011'den sonra)
- `GET /api/v1/entries/{id}/image` (yetki kontrollü, storage üzerinden) + 経費 listesinde küçük önizleme / büyütme. `/receipts/ocr` → 「画像も保存」 seçeneği.
- Kabul: başka defterin görseli 404; görselsiz kayıt 404; `next build` geçer.

## T-035 · Panel e2e (P2, T-021'den sonra)
- Playwright betiği (`dashboard-next/e2e/`) demo modunda tüm menüler açılır, konsol hatası yok; CI dashboard işine adım. Canlı mod sahte API ile (route mock).
- Kabul: CI'da e2e adımı yeşil; süre < 3 dk.

## T-048 · Hız sınırı (P1)
- `bot/ratelimit.py`: bellek içi kayan pencere (IP + uç nokta; `X-Forwarded-For` ilk değeri Render arkasında). Sınırlar (yapılandırılabilir): login 10/dk, signup 5/dk, password-reset/request 5/dk, `/receipts/ocr` 20/dk → 429 + `Retry-After`, Japonca `detail`. LINE `/callback` ve `/` etkilenmez.
- Kabul: sınırda N geçer, N+1 → 429; pencere sonrası tekrar 200 (saat monkeypatch); farklı IP bağımsız. Parola politikası zaten var (`accounts.PASSWORD_MIN`) — değiştirme.
- ✅ Yapıldı: `bot/ratelimit.py` (kayan pencere, kilitli, ≤20.000 anahtar), `api.py` 4 uçta `dependencies=[Depends(ratelimit.limiter(...))]`. Reddedilen istek sayılmaz. Ortam: `RATE_LIMIT_<KURAL>="adet/sn"` / `0`, `RATE_LIMIT_PROXY_HOPS` (varsayılan 0 = XFF ilk değer; istemci XFF sahteleyebiliyorsa 1 yap). Testler `tests/test_ratelimit.py`.

## T-048b · CORS + güvenlik başlıkları (P1)
- `app.py` CORS: `CORS_ORIGINS` boş veya `*` ise `PANEL_URL` (+ `http://localhost:3000`) kullan; render.yaml'daki `CORS_ORIGINS: "*"` değerini değiştirmeden kodda ele al (değişken adı aynı kalır). Middleware: `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Strict-Transport-Security: max-age=31536000`, `X-Frame-Options: DENY`.
- Kabul: izinli origin → `Access-Control-Allow-Origin` döner, yabancı origin dönmez; başlıklar `/` ve `/api/v1/*` yanıtlarında; `/callback` LINE imza testleri yeşil.

## T-051 · Banka CSV çoklu 摘要 sütunu (review-fix, P2)
- `bot/bank_csv.py` `parse()` (~satır 360–367): `desc` anahtarı ilk eşleşen sütuna atanıyor. MUFG/ゆうちょ biçiminde 「摘要」=振込/口座振替, karşı taraf 「摘要内容」'nde → `description` = 「口座振替」; `/bank/{id}/entry` ile oluşan 経費'in `store` alanı anlamsız, 消込 önerisinde müşteri ayırt edilemiyor.
- Beklenen: tüm `desc` eşleşen sütunları sırayla boşlukla birleştir (「口座振替 ﾗｸﾃﾝﾓﾊﾞｲﾙ」), boşları atla, 200 karakter sınırı korunur. Parmak izi değişeceği için mevcut içe aktarmaların yeniden alınmasında yinelenme tespiti bozulmamalı (ör. eski parmak izi biçimini de kontrol et) → test.
- Test: `tests/test_bank_and_entries.py::test_bank_csv_parse_variants` beklentisi güncellenir + yeniden içe aktarmada `duplicates` sayısı.
- ✅ Yapıldı: `bank_csv.parse` tüm 摘要 sütunlarını (boşları atlayarak) birleştirir; farklıysa `legacy_description` (yalnızca ilk sütun) döner. `store.insert_bank_rows` eski biçimin parmak izini de (eski sıra sayacıyla) kontrol eder → eski içe aktarmalar çoğalmaz. Testler `tests/test_bank_multi_desc.py`.

## T-052 · Stripe webhook olay sırası (review-fix, P1)
- `bot/billing.py` `_apply_subscription_object` (~satır 250) her olayda durumu koşulsuz yazar. Stripe olay sırasını garanti etmez: `customer.subscription.deleted` (status=canceled) sonrası yeniden denenen eski bir `updated` (status=active) gelirse defter tekrar ücretli olur.
- Beklenen: `subscriptions`'a ekleyici sütun (ör. `last_event_created INTEGER DEFAULT 0`); olayın `created` zamanı kayıttakinden eskiyse durum yazılmaz (`ignored`). `checkout.session.completed` için de aynı.
- Test: deleted(created=200) → updated(created=100, active) → plan `free` kalır; eşit/yeni zamanlı olay uygulanır.
- ✅ Yapıldı: `subscriptions.last_event_created` (ekleyici; `store.ADDED_COLUMNS` + `init_db` mevcut DB'lere ekler). Webhook yazımı koşullu UPDATE (`last_event_created<=created`) → eski olay `ignored`; checkout.session.completed dahil. API yanıtı yazımları (cancel) zamanı değiştirmez. Testler `tests/test_billing_event_order.py`.

## T-053 · Kayıt yarışında 500 (review-fix, P2)
- `bot/accounts.py` `signup()` (~satır 95): SELECT ile INSERT arasında aynı e-postayla ikinci istek gelirse `accounts.email UNIQUE` ihlali yakalanmıyor → 500. Beklenen: IntegrityError (sqlite3 + psycopg) → `AccountError(..., 409)`. Test: INSERT'i önceden yapıp kontrolü atlayan monkeypatch ile 409.
- ✅ Yapıldı: `store.is_integrity_error` (sqlite3 + psycopg); `signup` bütünlük hatasında e-posta gerçekten kayıtlıysa 409, değilse hatayı olduğu gibi yükseltir (gizlemez). İşlem geri alınır, yarım hesap/defter kalmaz. Testler `tests/test_signup_race.py`.

## T-054 · Çok oranlı fiş plan sınırını aşıyor / iki kota yiyor (review-fix, P2)
- `bot/app.py` `process_image` (~satır 324): `limit_notice` OCR'dan önce bir kez kontrol eder; OCR 8%/10% karışık fişi N kayda böler (`for e in result: add_entry`). Ücretsiz planda 29/30 kullanımda iki oranlı fiş → 31 kayıt; ayrıca `billing.usage` (`entries` satırı sayar) tek fişi 2 sayar, oysa plan metni 「経費 30件」.
- Beklenen (ürün sahibi kararı gerekebilir → gerekirse QUESTIONS): ya kota "fiş" başına sayılır (aynı `image_path` = 1) ya da kalan kota < N ise kayıt yapılmaz/uyarı verilir. Panel kullanım çubuğu ile aynı tanımı kullanmalı.
- Test: 29 kullanımda 2 oranlı sahte OCR → beklenen sayım; `usage()` sonucu.
- ✅ Yapıldı: kota "fiş" başına (Q-11 「ayda 30 fiş」): `billing.usage` aynı `image_path`'li satırları 1 sayar, görselsiz kayıtlar satır başına. 29 kullanımda 2 oranlı fiş → 30 (31 satır), sonraki fiş/metin reddedilir. Panel kullanım çubuğu `status()` üzerinden aynı tanımı kullanır. Testler `tests/test_receipt_quota_split.py`.
