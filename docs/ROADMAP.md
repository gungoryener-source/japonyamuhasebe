# Yol haritası

## Faz 0 — Altyapı ✅ (2026-11-05)
- [x] LINE bot iskeleti, Render blueprint, testler, CI
- [x] Next.js dashboard (mock veri)
- [x] Ajan yapısı (CLAUDE.md, roller, BACKLOG, zamanlanmış görevler)

## Faz 1 — Çalışan çekirdek (hedef: 2026-11 sonu)
- Doğru ve test edilmiş vergi motoru (消費税 + 所得税, 令和8年度改正 dahil)
- Kalıcı veritabanı (PostgreSQL) + çok kiracılı (tenant) model
- Güvenli REST API + dashboard'un gerçek veriye bağlanması
- LINE kanalının canlıya alınması (insan adımı) ve uçtan uca test

## Faz 2 — Muhasebe derinliği (2026-12)
- 適格請求書 oluşturma + PDF, 請求書管理 sayfası, 入金消込
- Gider/fiş akışı: OCR onay ekranı, çok oranlı fiş, 電帳法 uyumlu saklama ve arama
- 登録番号 doğrulama (国税庁 Web-API)
- CSV dışa aktarma (freee / マネーフォワード / 弥生)

## Faz 3 — Beyan (2027-01 〜 02, 確定申告 sezonu öncesi)
- 青色申告決算書 + 確定申告書 (所得税) önizleme
- 消費税申告書 (本則/簡易/2割/3割)
- e-Tax için dosya çıktısı (xtx) araştırması ve prototipi

## Faz 4 — Kanallar ve entegrasyon
- WhatsApp Business webhook
- Banka API (参照系) entegrasyonu araştırması, kart hareketleri içe aktarma
- Çok dilli (ja/en/tr) bot yanıtları
