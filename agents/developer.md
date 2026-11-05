# Rol: Geliştirici ajan

Çalışma sıklığı: günde 2 kez. Amaç: `tasks/BACKLOG.md`'den **bir** görevi uçtan uca bitirip `main`'e güvenle birleştirmek.

## Adımlar
1. `git pull --rebase origin main`. CI veya yerel testler kırmızıysa **önce onu düzelt** (bu çalışmanın görevi budur).
2. BACKLOG'da öncelik sırasına göre (`P0` > `P1` > `P2`) ilk `todo` veya `review-fix` görevini seç.
   `blocked` olanları ve 24 saatten yeni `doing` olanları atla.
3. Görevi `doing (developer, YYYY-MM-DD)` yap — bu satırı commit'leyip push ederek görevi "kilitle" (diğer çalışmalarla çakışmayı önler).
4. Görevin "Kabul ölçütleri"ni oku. Belirsizse en makul yorumu seç ve LOG'a yaz; ürün kararı gerekiyorsa `tasks/QUESTIONS.md`'ye soru ekle, görevi `blocked (Q-xx)` yap, sıradakine geç.
5. Kodla + test yaz. Görev çok büyükse bu çalışmada bitebilecek ilk dilimi yap, kalanını BACKLOG'a yeni alt görev olarak ekle.
6. Doğrulama kapısını çalıştır (CLAUDE.md). Geçmezse düzelt; 3 denemede geçmezse değişiklikleri `main`'e koyma, `agent/T-0xx` dalına push et, görevi `todo` bırak ve LOG'a nedenini yaz.
7. BACKLOG'da görevi `done (<kısa commit>)` yap, LOG'a özet ekle, `main`'e push et.
8. Push sonrası Render otomatik yayınlar. Sağlık kontrolü (`https://tegaru-line-bot.onrender.com/`) erişilebilirse bak; `ok:false` veya 5xx ise commit'i `git revert` ile geri al ve LOG'a yaz.

## İyi bir çalışmanın ölçüsü
- Tek konu, okunur diff, yeni testler, BACKLOG/LOG güncel.
- Kullanıcıya dönük her yeni metin Japonca ve doğal.
