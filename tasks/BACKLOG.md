# BACKLOG — tek görev kuyruğu

Kurallar ve durum sözlüğü: `CLAUDE.md`. Öncelik: P0 (önce) > P1 > P2. Her görevin kabul ölçütü vardır; tek çalışmada bitmeyecekse önce böl.

| ID | Öncelik | Durum | Görev |
|---|---|---|---|
| T-001 | P0 | done (bu commit) | Prototiplerde 令和8年度 経過措置 düzeltmesi |
| T-002 | P0 | done (bu commit) | Vergi motoru `bot/tax/` (消費税) + testler |
| T-003 | P0 | done (bu commit) | `/entries/{user_id}` uç noktasını kapat / kimlik doğrulaması ekle |
| T-004 | P1 | done (2025 tablosu) | Vergi motoru: 所得税 (所得税・復興税・青色控除・基礎控除) |
| T-004b | P1 | blocked (Q-03) | `BASIC_DEDUCTION[2026]` (令和8年分) tablosunu ekle + sınır testleri |
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
| T-015 | P2 | todo | dashboard-next: 請求書管理 sayfası (liste, filtre, 消込) |
| T-016 | P1 | done (743716d) | dashboard-next: vergi kartını `bot/tax` kurallarıyla hizala (経過措置 satırı, 2割/3割/簡易 seçimi) |
| T-012b | P2 | todo | CSV formatlarını freee / MF / 弥生'nin güncel içe aktarma şablonlarıyla doğrula (sütun adları, 税区分 metinleri) |
| T-018 | P1 | done | Sahte/zayıf token'a karşı: token iptali (`DELETE /api/v1/tokens/current`), LINE 「パネル」 en fazla 5 aktif token |
| T-019 | P2 | todo | PostgreSQL bağlantı havuzu (`psycopg_pool`) ve yavaş istek ölçümü |
| T-020 | P1 | todo | dashboard-next: 確定申告 önizleme sayfası (`/api/v1/pl`, `/api/v1/tax/income`) |
| T-022 | P1 | done | Yapay zekâsız fiş okuma: Tesseract (jpn) + kural tabanlı ayrıştırıcı, Docker imajı |
| T-023 | P1 | done | Gerçek fişlerle OCR ölçümü (67 fiş; tüm alanlar %70, toplam %85, yanlış kayıt %7 — docs/OCR.md) |
| T-025 | P1 | todo | LINE görsel işleme süresi: OCR uzun sürerse önce 「読み取り中…」 yanıtı, sonuç push mesajla (reply token süresi) |
| T-026 | P2 | todo | OCR: kırmızı damga (印) rengini ön işlemede bastır (HSV ile kırmızı → beyaz), tarih/rakam doğruluğu |
| T-024 | P2 | todo | OCR sonrası kullanıcı onayı: düşük güvenli alanlarda (tarih yok, oran kırılımı tahmini) LINE'da 「確認」 butonlu özet |
| T-017 | P2 | todo | `TAX_RULES` ❓ satırlarını doğrula: 簡易課税 みなし仕入率 (tax-watcher) ve `KANI_RATIO` testleri |
| T-021 | P2 | todo | CI: `dashboard` işini Node 22'ye al ve `npm run check:tax` adımını ekle (TS ile Python 消費税 eşleşmesi) |
| T-027 | P1 | doing (developer, 2026-11-06) | Yıllık 消費税/損益/CSV toplamları 5000 kayıtta sessizce kesiliyor |
| T-028 | P2 | review-fix | `/admin/richmenu` ADMIN_KEY'i URL sorgusunda alıyor (log sızıntısı) |
| T-029 | P2 | review-fix | Fatura kalemlerinde qty/unit_price üst sınırı yok (PostgreSQL bigint taşması → 500) |

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

## T-004b · 令和8年分 基礎控除
- Q-03 cevaplanınca (TAX_RULES ✅) `bot/tax/income.py` → `BASIC_DEDUCTION[2026]` ve her kademe sınırı için test. `test_basic_deduction_2026_not_verified` testi kaldırılıp yerine gerçek testler gelir.

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
