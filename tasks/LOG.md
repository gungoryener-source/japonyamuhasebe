# Ajan çalışma günlüğü (en yeni üstte)

Biçim: `## YYYY-MM-DD HH:MM JST · <rol> · <görev>` + 3–6 satır: ne yapıldı, testler, sonraki adım/engeller.

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
