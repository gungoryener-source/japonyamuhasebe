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
- [x] Gider/fiş akışı: çok oranlı fiş (T-014), yapay zekâsız OCR (T-022/T-023/T-026), arama, OCR onay (T-024), R2 görsel saklama (T-011; değerler Q-14), panelde görsel (T-034)
- [x] 登録番号 doğrulama — インボイス公表サイト Web-API (T-063; T-010 obsolete)
- [x] 仕切書 akışı (T-060), 取引先マスタ (T-061), 通帳取込 AI (T-062), çok şirket (T-064; fiyat Q-16), 訂正削除履歴 (T-065/b; slips T-065c Q-18)
- [ ] 家事按分 (T-076), 固定資産台帳 + 減価償却 (T-073 → T-074 → T-075), kart ekstresi CSV (T-077)
- [x] CSV dışa aktarma (freee / マネーフォワード / 弥生) (T-012, T-012b, T-012c; formül nötrleme kararı Q-17)

## Faz 3 — Beyan (2027-01 〜 02, 確定申告 sezonu öncesi)
- [x] 青色申告決算書 PDF (T-045) + 確定申告 önizleme (T-020); 青色控除 令和9年分 (T-049)
- [ ] 消費税申告書 (本則/簡易/2割/3割): kurallar T-070 → hesap T-071 → PDF T-072 (2割/3割 uygunluk T-050/T-066 ✅)
- [ ] e-Tax xtx: araştırma ✅ (T-045b, docs/ETAX.md); uygulama T-067/068/069 (Q-19)

## Faz 4 — Kanallar ve entegrasyon
- [x] WhatsApp Business webhook (T-013; canlı Q-06)
- [x] Banka CSV içe aktarma + 消込 (T-031, T-051); gerçek banka başlıkları T-033 ✅ (kalan bankalar T-033b, Q-22)
- Banka API (参照系) entegrasyonu araştırması; [ ] kart hareketleri içe aktarma (T-077)
- [x] Çok dilli (ja/en/tr) bot yanıtları + panel (T-047/b/c)

## Faz 5 — Satışa hazırlık (sprint: 2026-11-06 18:00 → 2026-11-08 18:00 İstanbul) — kod tarafı ✅ (2026-11-08)
- [x] E-posta ile hesap, giriş, şifre sıfırlama; LINE defterini hesaba bağlama (T-040, T-040b; e-posta gönderimi Q-13)
- [x] İşletmeye birden fazla kullanıcı: sahip / 税理士 / görüntüleyici (T-041, T-041b)
- [x] Abonelik ve ödeme (Stripe test modu, plan bazlı özellikler) (T-042, T-042b, T-052, T-054; anahtar/fiyat Q-10, Q-11)
- [x] 利用規約 / プライバシーポリシー / 特定商取引法に基づく表記 — ドラフト (T-043; satıcı bilgisi + hukuk kontrolü Q-12)
- [x] LINE OCR uzun sürerse 「読み取り中…」 + push (T-025)
- [x] Tanıtım sayfası (T-044; LINE URL Q-21), ilk kurulum sihirbazı (T-044b)
- [x] 確定申告 çıktıları: 青色申告決算書 PDF (T-045) + e-Tax araştırması (T-045b → docs/ETAX.md; xtx: T-067…069)
- [x] Veri dışa aktarma (T-046) / hesap silme talebi (T-046b; süre kararı Q-15) / yedekleme (T-046c)
- [x] Güvenlik: hız sınırı (T-048, T-058), CORS + başlıklar (T-048b); CI'da panel kontrolleri (T-021) + e2e (T-035)
- [x] Metinlerin tek dosyada toplanması + dil seçeneği (T-047)
- [ ] Canlıya alma kontrolü `/admin/config-check` + `docs/GO_LIVE.md` (T-078); ardından insan adımları
