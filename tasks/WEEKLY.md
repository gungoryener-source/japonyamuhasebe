# Haftalık rapor (en yeni üstte)

## 2026-11-08 · planner · hafta 2 (sprint sonu, 2026-11-07 → 11-08)
- **Bitti:** Sprint kod hedefi tamam: Faz 5'in tamamı (T-044/b /lp + /welcome, T-046/b/c ZIP·silme talebi·yedek, T-047 dil ja/tr/en, T-048/b/T-058 güvenlik, T-021+T-035 CI'da panel + e2e, T-055 kesin fiyatlar, T-056 Resend, T-011 R2); Faz 2 derinliği (T-024/T-026 OCR, T-034 fiş görseli, T-060 仕切書, T-061 取引先, T-062 通帳 AI, T-063 登録番号, T-064 çok şirket, T-065/b 訂正履歴); vergi T-049/T-050/T-066/T-017; CSV T-012b/c, banka T-033, e-Tax araştırması T-045b. pytest 777 yeşil.
- **Takılan:** Kodda terk edilmiş görev yok. Blocked: T-033b (banka CSV örneği, Q-22), T-064b (Q-16), T-065c (Q-18), T-067→069 e-Tax (Q-19). Canlıya alma tamamen insan adımlarında (Render planı/Docker, LINE, anahtarlar).
- **Cevap bekleyen:** Q-19 e-Tax 仕様書 kabulü · Q-15 silme süresi/saklama · Q-17 CSV formül nötrleme · Q-18 slips geçmişi izni · Q-16 çok şirket fiyatı · Q-21 LINE 友だち追加 URL + `/lp` kök sayfa mı · Q-20 NTA_APP_ID · Q-22 banka CSV örnekleri. Değer girilmesi bekleyenler: Q-01, Q-10, Q-12, Q-13, Q-14.
- **Düzeltme:** QUESTIONS'ta çift numaralar giderildi (eski 2. Q-15 → Q-20, LINE URL Q-16 → Q-21).
- **BACKLOG:** 9 yeni todo (kabul ölçütlü): T-078 canlıya alma kontrolü, T-070→072 消費税申告書, T-073→075 減価償却/固定資産, T-076 家事按分, T-077 kart CSV.
- **Gelecek hafta hedefi:** T-078 ile canlıya alma listesi + senin LINE/Render adımlarınla ilk uçtan uca test; Faz 3: 消費税申告書 hesap (T-070/071) ve 個人 için 家事按分 + 減価償却 (T-076, T-073/074).

## 2026-11-07 · planner · hafta 1 (2026-11-05 → 11-07)
- **Bitti:** Faz 0–1 kod tarafı (消費税/所得税 motoru, 基礎控除 2025–27, PostgreSQL, REST API, panel); Faz 2'de 適格請求書+PDF, 請求書/経費/銀行 sayfaları, çok oranlı OCR, CSV; Faz 5 P0'ın tamamı: hesap+giriş (T-040/b), ekip rolleri (T-041/b), Stripe abonelik (T-042/b), yasal sayfalar ドラフト (T-043), LINE OCR push (T-025). 3 inceleme, 5 review-fix kapandı; CI yeşil (pytest 385).
- **Takılan:** Kodda blocked/terk edilmiş görev yok. Canlıya alma tamamen senin adımlarına bağlı: LINE kanalı (Q-01), Render Docker geçişi (Q-08). Yeni risk: fiş görselleri her deploy'da siliniyor (Render'da disk yok) → T-011 P1'e alındı, depolama kararı Q-14.
- **Cevap bekleyen (öncelik sırasıyla):** Q-01 LINE anahtarları · Q-14 görsel depolama (R2/S3) · Q-10 Stripe anahtarları · Q-11 gerçek fiyatlar + mevcut kullanıcı geçişi · Q-12 特商法 satıcı bilgileri + hukuk kontrolü · Q-13 e-posta servisi · Q-07/Q-09 ücretli DB/plan · Q-04, Q-05, Q-06, Q-08, Q-02.
- **BACKLOG:** büyük görevler bölündü (T-044b, T-045b, T-046b/c, T-048b), tüm todo'lara kabul ölçütü eklendi; 23 todo. CI'da panel kontrolleri olmadığı için T-021 P1'e çıktı.
- **Gelecek hafta hedefi:** Sprint sonuna kadar Faz 5 kalanları (T-021, T-048/b, T-046/b, T-045, T-044/b, T-011); sonra Faz 2 kalanları (T-010, T-024, T-034) ve T-049 (青色控除 令和9年分). Senden en kritik adım: Q-01 + Q-14 ile ilk canlı uçtan uca test.
