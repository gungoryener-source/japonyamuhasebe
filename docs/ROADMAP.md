# Yol haritası

## Faz 0 — Altyapı ✅ (2026-11-05)
- [x] LINE bot iskeleti, Render blueprint, testler, CI
- [x] Next.js dashboard (mock veri)
- [x] Ajan yapısı (CLAUDE.md, roller, BACKLOG, zamanlanmış görevler)

## Faz 1 — Çalışan çekirdek (hedef: 2026-11 sonu) — kod tarafı ✅, canlıya alma insan adımında
- [x] Doğru ve test edilmiş vergi motoru (消費税 + 所得税, 令和8年度改正 dahil; 基礎控除 2025–2027) (T-002, T-004, T-004b) — 青色控除 令和9年分 → T-049
- [x] Kalıcı veritabanı (PostgreSQL) + çok kiracılı (tenant) model (T-006)
- [x] Güvenli REST API + dashboard'un gerçek veriye bağlanması (T-005, T-007, T-018)
- [ ] LINE kanalının canlıya alınması (insan adımı, Q-01) ve uçtan uca test

## Faz 2 — Muhasebe derinliği (2026-12)
- [x] 適格請求書 oluşturma + PDF, 請求書管理 sayfası, 入金消込 (T-008, T-015, T-031)
- [ ] Gider/fiş akışı: [x] çok oranlı fiş (T-014), [x] yapay zekâsız OCR (T-022/T-023), [x] arama, [ ] OCR onay (T-024), [ ] kalıcı görsel saklama (T-011, Q-14), [ ] panelde görsel (T-034)
- [ ] 登録番号 doğrulama (国税庁 Web-API) (T-010)
- [x] CSV dışa aktarma (freee / マネーフォワード / 弥生) (T-012) — şablon doğrulaması T-012b

## Faz 3 — Beyan (2027-01 〜 02, 確定申告 sezonu öncesi)
- 青色申告決算書 + 確定申告書 (所得税) önizleme
- 消費税申告書 (本則/簡易/2割/3割)
- e-Tax için dosya çıktısı (xtx) araştırması ve prototipi

## Faz 4 — Kanallar ve entegrasyon
- [x] WhatsApp Business webhook (T-013; canlı Q-06)
- [x] Banka CSV içe aktarma + 消込 (T-031, T-051); gerçek banka başlıkları T-033
- Banka API (参照系) entegrasyonu araştırması, kart hareketleri içe aktarma
- Çok dilli (ja/en/tr) bot yanıtları

## Faz 5 — Satışa hazırlık (sprint: 2026-11-06 18:00 → 2026-11-08 18:00 İstanbul)
- [x] E-posta ile hesap, giriş, şifre sıfırlama; LINE defterini hesaba bağlama (T-040, T-040b; e-posta gönderimi Q-13)
- [x] İşletmeye birden fazla kullanıcı: sahip / 税理士 / görüntüleyici (T-041, T-041b)
- [x] Abonelik ve ödeme (Stripe test modu, plan bazlı özellikler) (T-042, T-042b, T-052, T-054; anahtar/fiyat Q-10, Q-11)
- [x] 利用規約 / プライバシーポリシー / 特定商取引法に基づく表記 — ドラフト (T-043; satıcı bilgisi + hukuk kontrolü Q-12)
- [x] LINE OCR uzun sürerse 「読み取り中…」 + push (T-025)
- [ ] Tanıtım sayfası (T-044), ilk kurulum sihirbazı (T-044b)
- [ ] 確定申告 çıktıları: 青色申告決算書 PDF (T-045) + e-Tax araştırması (T-045b)
- [ ] Veri dışa aktarma (T-046) / hesap silme talebi (T-046b) / yedekleme (T-046c)
- [ ] Güvenlik: hız sınırı (T-048), CORS + başlıklar (T-048b); CI'da panel kontrolleri (T-021)
- [ ] Metinlerin tek dosyada toplanması (T-047)
