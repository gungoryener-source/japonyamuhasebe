# İnsan kararı bekleyen sorular

Ürün sahibi cevabı `**Cevap:**` satırına yazar. Ajanlar cevaplanmış soruya göre ilgili `blocked` görevi `todo` yapar.

## Q-01 · LINE kanalı (açık)
LINE Developers'ta Messaging API kanalı açılmadı. Gerekenler: kanal açılışı, `LINE_CHANNEL_SECRET` ve `LINE_CHANNEL_ACCESS_TOKEN` değerlerinin Render → tegaru-line-bot → Environment'a girilmesi, Webhook URL `https://tegaru-line-bot.onrender.com/callback`, ardından `curl -X POST -H "X-Admin-Key: <ADMIN_KEY>" https://tegaru-line-bot.onrender.com/admin/richmenu` (eski `?key=` biçimi de geçici olarak çalışır).
**Cevap:**

## Q-02 · Anthropic API anahtarı (isteğe bağlı)
Fiş okuma artık varsayılan olarak yapay zekâsız (Tesseract OCR + kurallar). `ANTHROPIC_API_KEY` girilirse `OCR_ENGINE=auto` modunda yalnızca kural tabanlı okuma başarısız olduğunda yedek olarak kullanılır. Hiç kullanılmasın istenirse Render'da `OCR_ENGINE=tesseract` yap.
**Cevap:**

## Q-03 · 令和8年分 基礎控除 tablosu (cevaplandı — tax-watcher, 2026-11-06)
NTA No.1199 tablosundan 2026 yılı için ≤2,350万 → 104万 okunuyor ama hücre yapısı belirsiz. tax-watcher birincil kaynaktan (改正法 / NTA Q&A 令和8年5月版) doğrulayıp TAX_RULES'u ✅ yapınca T-004'ün 2026 kısmı açılır.
**Cevap:** (tax-watcher, birincil kaynak) 104万 yalnızca **合計所得 ≤489万** için; tablo 令和8年分・令和9年分 aynı: ≤489万 104万 · ≤655万 67万 · ≤2,350万 62万 · ≤2,400万 48万 · ≤2,450万 32万 · ≤2,500万 16万 · 超 0 (本則62万 + 措法41の16の2 特例 42万/5万). 施行 2026-12-01, 令和8年分から適用. Kaynak: [NTA 令和8年分 年末調整のしかた 102.pdf](https://www.nta.go.jp/publication/pamph/gensen/nencho2026/pdf/102.pdf), [財務省 大綱](https://www.mof.go.jp/tax_policy/tax_reform/outline/fy2026/20251226taikou.pdf), [NTA No.1199](https://www.nta.go.jp/taxes/shiraberu/taxanswer/shotoku/1199.htm). TAX_RULES §2 ✅; T-004b → todo. 令和10年分以後 (≤132万 99万 kesin, diğer kademeler ⚠️) ayrıca izleniyor; ürün sahibinin işlem yapması gerekmez.

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

## Q-10 · Ödeme sağlayıcısı (açık)
Varsayılan: **Stripe** (JPY, Japonya kartları, konbini ödemesi). Alternatif: PAY.JP (Japon şirketi). Ajanlar Stripe test moduyla geliştiriyor; canlı anahtar senin Stripe hesabından gelmeli.
(2026-11-07 developer, T-042: Render'a `sync: false` ile eklendi — **değer girilmeli**: `STRIPE_SECRET_KEY` (önce `sk_test_…`), `STRIPE_WEBHOOK_SECRET` (Stripe → Developers → Webhooks → uç nokta `https://tegaru-line-bot.onrender.com/api/v1/billing/webhook`, olaylar: `checkout.session.completed`, `customer.subscription.created/updated/deleted`), `STRIPE_PRICE_PERSONAL`, `STRIPE_PRICE_BUSINESS` (Stripe'ta aylık JPY "Price" kimlikleri `price_…`). Anahtar girilene kadar ödeme kapalı ve ücretsiz plan sınırları **uygulanmıyor**.)
**Cevap:**

## Q-11 · Fiyatlandırma (açık)
Yer tutucu: Free (ayda 30 fiş, 3 fatura) / 個人 ¥980 / 法人 ¥2,980 (vergi hariç, aylık). Gerçek fiyatları yaz.
(2026-11-07 developer, T-042: yer tutucular `bot/billing.py` `PLANS` içinde. Ek karar: `STRIPE_SECRET_KEY` girildiği anda mevcut LINE kullanıcılarına da ücretsiz plan sınırı uygulanır — mevcut kullanıcılara geçiş süresi / ücretsiz dönem istiyor musun? İstemezsen `BILLING_ENFORCE_LIMITS=0` ile sınırlar kapalı tutulabilir.)
(2026-11-07 developer, T-054: 税率ごとに分割 edilen tek fiş kotada 1 件 sayılıyor (aynı görsel = 1). Satır başına sayılmasını istersen belirt.)
**Cevap:**

## Q-12 · Satıcı bilgileri — 特定商取引法に基づく表記 (açık)
Zorunlu: 販売業者名, 運営責任者, 所在地, 電話番号, メールアドレス, 販売価格, 支払方法・時期, 解約・返金. Japonya'da şirket/adres yoksa nasıl gösterileceğini müşavirle netleştir. Yasal metinler bu cevaplanana kadar "ドラフト" olarak yayında.
(2026-11-07 developer, T-043: sayfalar yayında — `/legal/terms/`, `/legal/privacy/`, `/legal/tokushoho/`, metin `dashboard-next/app/lib/legal.ts`. Satıcı bilgileri Render → jsaas-panel → Environment'a **değer girilmeli**: `NEXT_PUBLIC_LEGAL_SELLER`, `_MANAGER`, `_ADDRESS`, `_PHONE`, `_EMAIL` (girildikten sonra Manual Deploy ile yeniden derle). Boş alanlar 「要確認」 görünür. Avukat/müşavir kontrolü gereken ve 「要確認」 işaretli maddeler: 返金なし・期間末解約, 損害賠償上限 (月額料金), 合意管轄, 外国にある第三者 bilgi sunumu (APPI 28条: ülke + o ülkenin sistemi), 帳簿 saklama süresi ve hesap silindikten sonra veri silme süresi, fiyat gösterimi (税込 gösterim zorunlu mu). Ayrıca karar: 規約 üzerindeki sorumluluğu "当社" mı (şirket kurulana kadar bireysel ad mı) yazılacak?)
**Cevap:**

## Q-13 · E-posta gönderim servisi (açık)
Şifre sıfırlama ve bildirimler için: Resend / SendGrid / Amazon SES. Seçilen servisin anahtarı Render'a `MAIL_PROVIDER` + `MAIL_API_KEY` olarak girilmeli; o zamana kadar e-postalar yalnızca sunucu log'una yazılır. (2026-11-07 developer: iki değişken `render.yaml`'a `sync: false` ile eklendi — **değer girilmeli**; T-040 parola sıfırlama e-postası şu an yalnızca log'a düşüyor.)
**Cevap:**
