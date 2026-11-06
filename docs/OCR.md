# Fiş okuma (OCR) — yapay zekâsız

Akış: görsel → `receipt_ocr.preprocess` (EXIF, 1200px genişlik, median filtre, kontrast) → Tesseract `jpn` (tessdata_best)
→ `receipt_parser.parse_receipt` (kurallar) → gerekirse Tesseract `eng` ikinci geçiş (yalnızca T番号 doğrulanamazsa).

## Ölçüm (2026-11-06, 67 gerçek fiş: FamilyMart, 7-Eleven, Lawson, Daily, クスリのアオキ, タチヤ, ハイウェイショップ, Vietnam marketleri)
Görseller ve doğru değer listesi kişisel alışveriş verisi olduğu için depoda **yok**; yalnızca sonuçlar:

| Ayar | Tarih | Toplam | %8/%10 kırılımı | T番号 | Tüm alanlar | Yanlış kayıt | Okunamadı (kullanıcıya sorulur) |
|---|---|---|---|---|---|---|---|
| İlk sürüm (fast, 1600px, ikili) | %48 | %19 | %15 | %48 | %6 | — | %37 |
| Kurallar iyileştirilmiş, fast model | %79 | %72 | %68 | %80 | %45 | %9 | %19 |
| **Varsayılan: tessdata_best, 1200px, ikili kapalı** | **%91** | **%85** | **%81** | **%93** | **%70** | **%7** | **%7** |

## Kurallar (gerçek hatalardan çıkarıldı)
- **Toplam, oran satırlarından:** 合計 satırı iri/kalın basılır ve en çok bozulan satırdır. 「10%対象」「8%対象」 satırları küçük yazılır ve daha güvenilirdir → toplam = 10% + 8%. 合計 yalnızca doğrulama/yedek.
- **OCR varyantları:** `1 0 %対象`, `10O%`, `109%`, `89対象`, `8多%対象`, `10和対象`, `対旬/対餅/対衣`, `タイソョウ` (Daily), `内税対象額 8. 00%`.
- **外税 satırları** (`外8% ﾀｲｼｮｳ ¥2,060`): tutar vergi hariç → `+ floor(tutar × oran)`.
- **Kayıp baş rakam onarımı:** `(8%対象 ¥311)` + `(内消費税等 ¥97)` → vergiyle tutmuyor → ¥1,311. `補,530` / `\],125` → `1,...`.
- **登録番号 kontrol hanesi:** 法人番号'nun ilk hanesi kontrol hanesidir; geçerli aday seçilir. `T` → `「` okunması tolere edilir.
- **Gün adıyla tarih onarımı:** `2026年1月05日(木)` → 1月5日 pazartesi → `11月05日`.
- **Güvenlik:** ¥50 altı veya bir oran satırı okunamamış ve güvenilir toplam yoksa kaydetmez; okunan alanlarla birlikte kullanıcıdan tutarı ister.

## Bilinen sınırlar
- Kırmızı damga (印) üstüne denk gelen tarih/rakamlar, buruşuk termal kâğıt, Vietnamca ürün adları.
- Ücretsiz Render (0.1 CPU) üzerinde fiş başına ~20–50 sn sürebilir; canlıda en az Starter plan önerilir (Q-09).
