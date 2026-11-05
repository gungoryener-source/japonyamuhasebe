# Ajan çalışma günlüğü (en yeni üstte)

Biçim: `## YYYY-MM-DD HH:MM JST · <rol> · <görev>` + 3–6 satır: ne yapıldı, testler, sonraki adım/engeller.

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
