# Haftalık rapor (en yeni üstte)

## 2026-11-07 · planner · hafta 1 (2026-11-05 → 11-07)
- **Bitti:** Faz 0–1 kod tarafı (消費税/所得税 motoru, 基礎控除 2025–27, PostgreSQL, REST API, panel); Faz 2'de 適格請求書+PDF, 請求書/経費/銀行 sayfaları, çok oranlı OCR, CSV; Faz 5 P0'ın tamamı: hesap+giriş (T-040/b), ekip rolleri (T-041/b), Stripe abonelik (T-042/b), yasal sayfalar ドラフト (T-043), LINE OCR push (T-025). 3 inceleme, 5 review-fix kapandı; CI yeşil (pytest 385).
- **Takılan:** Kodda blocked/terk edilmiş görev yok. Canlıya alma tamamen senin adımlarına bağlı: LINE kanalı (Q-01), Render Docker geçişi (Q-08). Yeni risk: fiş görselleri her deploy'da siliniyor (Render'da disk yok) → T-011 P1'e alındı, depolama kararı Q-14.
- **Cevap bekleyen (öncelik sırasıyla):** Q-01 LINE anahtarları · Q-14 görsel depolama (R2/S3) · Q-10 Stripe anahtarları · Q-11 gerçek fiyatlar + mevcut kullanıcı geçişi · Q-12 特商法 satıcı bilgileri + hukuk kontrolü · Q-13 e-posta servisi · Q-07/Q-09 ücretli DB/plan · Q-04, Q-05, Q-06, Q-08, Q-02.
- **BACKLOG:** büyük görevler bölündü (T-044b, T-045b, T-046b/c, T-048b), tüm todo'lara kabul ölçütü eklendi; 23 todo. CI'da panel kontrolleri olmadığı için T-021 P1'e çıktı.
- **Gelecek hafta hedefi:** Sprint sonuna kadar Faz 5 kalanları (T-021, T-048/b, T-046/b, T-045, T-044/b, T-011); sonra Faz 2 kalanları (T-010, T-024, T-034) ve T-049 (青色控除 令和9年分). Senden en kritik adım: Q-01 + Q-14 ile ilk canlı uçtan uca test.
