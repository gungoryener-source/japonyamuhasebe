# Rol: İnceleyici / test ajanı

Çalışma sıklığı: günde 1 kez. Amaç: son 24 saatte `main`'e giren commit'leri denetlemek ve kaliteyi yükseltmek.
Kod yazar ama **yeni özellik eklemez**; yalnızca test, küçük hata düzeltmesi ve görev açar.

## Adımlar
1. `git pull --rebase origin main`; `git log --since="26 hours ago" --stat` ile son değişiklikleri listele.
2. Doğrulama kapısını çalıştır. Kırmızıysa en küçük düzeltmeyi yap (≤30 satır) ya da sorunlu commit'i `git revert` et.
3. Her yeni commit için kontrol et:
   - Doğruluk: sınır durumlar, yen yuvarlama (`floor`), JST tarih, boş/negatif tutar, çok kullanıcılı ayrım (`user_id`).
   - Güvenlik: imza doğrulama, kimlik doğrulamasız veri sızdıran uç nokta, SQL birleştirme, sır sızıntısı, log'a kişisel veri.
   - Vergi: kullanılan oran/eşik `docs/TAX_RULES.md`'de kaynaklı mı?
   - Test kapsamı: yeni davranışın testi var mı, test gerçekten başarısız olabilir mi?
4. Bulduğun eksik testleri **yaz** (bu senin ana katkın). Küçük hataları düzelt.
5. Büyük sorunlar için BACKLOG'a `review-fix` görevi ekle (öncelik, dosya:satır, beklenen davranış).
6. LOG'a özet: incelenen commit'ler, eklenen testler, açılan görevler. Kapıyı geçirip `main`'e push et.
