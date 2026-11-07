# Fiş okuma (OCR) — yapay zekâsız

Akış: görsel → `receipt_ocr.preprocess` (EXIF, kırmızı damga bastırma, 1200px genişlik, median filtre, kontrast) → Tesseract `jpn` (tessdata_best)
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

## Kırmızı damga bastırma (T-026, 2026-11-08)
- Gri tona geçmeden önce HSV (Pillow, yeni paket yok): ton H ≤ 14 veya ≥ 232 (0–255 ölçeği; 朱色・kırmızı・koyu pembe), doygunluk ≥ 70, parlaklık ≥ 90 → beyaz. Maskenin 1 px komşuluğundaki açık renkli (gri ≥ 150) JPEG halesi de silinir.
- Damga üstüne basılmış siyah yazı (koyu, V < 90) korunur; mavi/yeşil kalem ve gri korunur.
- **Görselde kırmızı piksel yoksa çıktı birebir aynıdır** → yukarıdaki 67 fişlik ölçüm geçerliliğini korur (testle sabitlendi: `test_no_red_pixels_output_identical`).
- Kapatma: `OCR_RED_SUPPRESS=0`. Bilinen risk: kırmızı **basılmış** metin (iki renkli termal yazıcıda kırmızı 合計 vb.) de silinir; bu durumda toplam 10%/8% 対象 satırlarından okunur (yukarıdaki kural).
- Ölçüm betiği: `python scripts/ocr_eval.py --images <klasör> --truth truth.csv` (gerçek fişler, açık/kapalı karşılaştırma) veya `--synthetic`.

| Sentetik ölçüm (3 fikstür × damgalı/temiz = 6 görsel, tesseract 5.3.4 jpn) | Tarih | Mağaza | Toplam | %8/%10 | T番号 | Tüm alanlar | Yanlış kayıt |
|---|---|---|---|---|---|---|---|
| Bastırma kapalı | %83 | %67 | %100 | %100 | %83 | %67 | %0 |
| **Bastırma açık (varsayılan)** | **%100** | **%100** | **%100** | **%100** | **%100** | **%100** | %0 |

Gerçek damgalı fişlerle ölçüm henüz yapılmadı (görseller depoda yok) — ürün sahibi kendi fişleriyle betiği çalıştırabilir.

## Düşük güvenli sonuç onayı (T-024, 2026-11-08)
- `parse_receipt` güven bayrakları yalnızca False iken ekler: `date_found` (tarih okunamadı) ve `rate_breakdown_found` (税率 内訳 tahmini: oran satırı yok ya da diğer oran = 合計 − bilinen). Tek oranlı fişte 「(内消費税 ¥500)」 satırı `floor(合計×r/(100+r))` ile tutuyorsa tahmin sayılmaz.
- `app.normalize_ocr` → kayıtlarda `needs_check: ["date", "rate"]` (AI yolunda total10/total8 yoksa "rate"). Kayıt yine yapılır (tarih yoksa bugün).
- LINE/WhatsApp yanıtı: ⚠️ uyarı + 「確認」, 「日付:昨日」「日付:一昨日」, (tek kayıtta) 「税率8%/10%」. Yeni komut 「日付 11/3」 / 「日付 2026-11-03」: son fişin tüm 税率別 kayıtlarını değiştirir (audit_log'a yazılır); gelecek tarih reddedilir, yılsız tarih gelecekteyse geçen yıl sayılır.
- Güvenli sonuçta yanıt ve hızlı yanıtlar değişmedi (testli).

## Bilinen sınırlar
- Kırmızı basılmış metin (damga bastırma bunu da siler; `OCR_RED_SUPPRESS=0`), buruşuk termal kâğıt, Vietnamca ürün adları.
- Ücretsiz Render (0.1 CPU) üzerinde fiş başına ~20–50 sn sürebilir; canlıda en az Starter plan önerilir (Q-09).
