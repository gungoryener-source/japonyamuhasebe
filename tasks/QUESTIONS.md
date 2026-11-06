# İnsan kararı bekleyen sorular

Ürün sahibi cevabı `**Cevap:**` satırına yazar. Ajanlar cevaplanmış soruya göre ilgili `blocked` görevi `todo` yapar.

## Q-01 · LINE kanalı (açık)
LINE Developers'ta Messaging API kanalı açılmadı. Gerekenler: kanal açılışı, `LINE_CHANNEL_SECRET` ve `LINE_CHANNEL_ACCESS_TOKEN` değerlerinin Render → tegaru-line-bot → Environment'a girilmesi, Webhook URL `https://tegaru-line-bot.onrender.com/callback`, ardından `POST /admin/richmenu?key=<ADMIN_KEY>`.
**Cevap:**

## Q-02 · Anthropic API anahtarı (isteğe bağlı)
Fiş okuma artık varsayılan olarak yapay zekâsız (Tesseract OCR + kurallar). `ANTHROPIC_API_KEY` girilirse `OCR_ENGINE=auto` modunda yalnızca kural tabanlı okuma başarısız olduğunda yedek olarak kullanılır. Hiç kullanılmasın istenirse Render'da `OCR_ENGINE=tesseract` yap.
**Cevap:**

## Q-03 · 令和8年分 基礎控除 tablosu (açık — tax-watcher doğrulasın)
NTA No.1199 tablosundan 2026 yılı için ≤2,350万 → 104万 okunuyor ama hücre yapısı belirsiz. tax-watcher birincil kaynaktan (改正法 / NTA Q&A 令和8年5月版) doğrulayıp TAX_RULES'u ✅ yapınca T-004'ün 2026 kısmı açılır.
**Cevap:**

## Q-04 · Hedef müşteri önceliği (açık)
Önce 個人事業主 (確定申告) mi, yoksa 小規模法人 (3月決算, 法人税) mı? Şu anki varsayım: **個人事業主 + küçük 合同会社**, beyan tarafında önce 個人.
**Cevap:**

## Q-05 · Panel adresi (açık)
render.yaml'a `jsaas-panel` statik sitesi eklendi; Render blueprint senkronunda otomatik oluşur. Render alt alan adı farklı çıkarsa (ör. `jsaas-panel-xxxx.onrender.com`) tegaru-line-bot → Environment → `PANEL_URL` değerini düzelt. Blueprint senkronu "manual" ise Render → Blueprints → japonyamuhasebe → Sync.
**Cevap:**

## Q-06 · WhatsApp Business (açık)
Kod hazır (`bot/whatsapp.py`, webhook `https://tegaru-line-bot.onrender.com/whatsapp`). Canlıya almak için Meta for Developers'ta WhatsApp uygulaması + telefon numarası gerekir; Render'a `WHATSAPP_APP_SECRET`, `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID` girilmeli (`WHATSAPP_VERIFY_TOKEN` Render'da otomatik üretildi, Meta'daki "Verify token" alanına aynısı yazılır). Japonya'da LINE öncelikli olduğundan bu adım ertelenebilir.
**Cevap:**

## Q-07 · Render ücretsiz PostgreSQL süresi (bilgi)
render.yaml'a `jsaas-db` (free) eklendi; artık kayıtlar yeniden başlatmada silinmez. Render'ın ücretsiz veritabanları oluşturulduktan ~30 gün sonra süresi dolar (yükseltme veya yeniden oluşturma gerekir). Canlı kullanıcı gelmeden önce ücretli plana (Basic) geçilmeli veya başka bir sağlayıcı seçilmeli. Ayrıca Render hesabında yalnızca bir ücretsiz veritabanı olabilir.
**Cevap:**

## Q-08 · Render servisinin Docker'a geçişi (kontrol gerekli)
Sunucuda Tesseract olması için `tegaru-line-bot` servisi render.yaml'da `runtime: docker` yapıldı (`bot/Dockerfile`). Render mevcut bir servisin çalışma ortamını blueprint ile değiştirmeyi reddederse: Render → tegaru-line-bot → Settings → Delete Service, ardından Blueprints → japonyamuhasebe → Sync (servis Docker olarak yeniden oluşur; ortam değişkenleri yeniden girilmeli). Kontrol: `https://tegaru-line-bot.onrender.com/` yanıtında `"tesseract": true`.
**Cevap:**

## Q-09 · OCR hızı ve Render planı (bilgi)
tessdata_best modeliyle fiş başına ~2–5 sn (tam çekirdek). Render free planı 0.1 CPU olduğundan 20–50 sn sürebilir; LINE'da yanıt gecikir (T-025 ile çözülecek). Canlı kullanıcıdan önce tegaru-line-bot için Starter (0.5 CPU) plana geçilmesi önerilir.
**Cevap:**
