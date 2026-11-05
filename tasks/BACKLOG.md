# BACKLOG — tek görev kuyruğu

Kurallar ve durum sözlüğü: `CLAUDE.md`. Öncelik: P0 (önce) > P1 > P2. Her görevin kabul ölçütü vardır; tek çalışmada bitmeyecekse önce böl.

| ID | Öncelik | Durum | Görev |
|---|---|---|---|
| T-001 | P0 | done (bu commit) | Prototiplerde 令和8年度 経過措置 düzeltmesi |
| T-002 | P0 | done (bu commit) | Vergi motoru `bot/tax/` (消費税) + testler |
| T-003 | P0 | done (bu commit) | `/entries/{user_id}` uç noktasını kapat / kimlik doğrulaması ekle |
| T-004 | P1 | todo | Vergi motoru: 所得税 (所得税・復興税・青色控除・基礎控除) |
| T-005 | P1 | todo | REST API v1: tenant'a göre özet, nakit akışı, faturalar |
| T-006 | P1 | todo | PostgreSQL desteği (`DATABASE_URL`), SQLite yedek |
| T-007 | P1 | todo | dashboard-next'i API'ye bağla (mock → fetch, yükleniyor/hata durumları) |
| T-008 | P1 | todo | 適格請求書 oluşturma API + PDF |
| T-009 | P1 | todo | LINE: son kaydı düzenleme (勘定科目 / 税率 hızlı yanıtla) |
| T-010 | P2 | todo | 登録番号 doğrulama (国税庁 Web-API, mock'lu testler) |
| T-011 | P2 | todo | Fiş görsellerini nesne depolamaya taşıma + 電帳法 arama alanları |
| T-012 | P2 | todo | CSV dışa aktarma (freee / MF / 弥生 formatları) |
| T-013 | P2 | todo | WhatsApp Business webhook kanalı (parser paylaşımlı) |
| T-014 | P2 | todo | OCR: çok oranlı (8%+10%) fişleri satır bazında ayırma |
| T-015 | P2 | todo | dashboard-next: 請求書管理 sayfası (liste, filtre, 消込) |
| T-016 | P1 | todo | dashboard-next: vergi kartını `bot/tax` kurallarıyla hizala (経過措置 satırı, 2割/3割/簡易 seçimi) |
| T-017 | P2 | todo | `TAX_RULES` ❓ satırlarını doğrula: 簡易課税 みなし仕入率 (tax-watcher) ve `KANI_RATIO` testleri |

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

## T-017 · 簡易課税 みなし仕入率 doğrulaması
- tax-watcher birincil kaynakla oranları ✅ yapınca `KANI_RATIO` için her tür adına test ekle.
