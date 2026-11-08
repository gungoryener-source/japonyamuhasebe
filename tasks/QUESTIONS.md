# İnsan kararı bekleyen sorular

Ürün sahibi cevabı `**Cevap:**` satırına yazar. Ajanlar cevaplanmış soruya göre ilgili `blocked` görevi `todo` yapar.

## Q-01 · LINE kanalı (açık)
LINE Developers'ta Messaging API kanalı açılmadı. Gerekenler: kanal açılışı, `LINE_CHANNEL_SECRET` ve `LINE_CHANNEL_ACCESS_TOKEN` değerlerinin Render → tegaru-line-bot → Environment'a girilmesi, Webhook URL `https://tegaru-line-bot.onrender.com/callback`, ardından `curl -X POST -H "X-Admin-Key: <ADMIN_KEY>" https://tegaru-line-bot.onrender.com/admin/richmenu` (eski `?key=` biçimi de geçici olarak çalışır).
(2026-11-07 developer, T-025: OCR 8 sn'den uzun sürerse sonuç **push** mesajla gönderiliyor; push mesajları LINE Official Account aylık ücretsiz mesaj kotasına sayılır (reply sayılmaz). Kota küçükse Render'da `LINE_REPLY_WAIT_SEC` (en fazla 50) artırılabilir; daha hızlı plan (Q-09) push ihtiyacını azaltır. Bilgi — işlem gerekmez.)
**Cevap:** Kanal ürün sahibiyle birlikte açılacak (insan adımı). Ajanlar beklemez; LINE kodu hazır kalır. (ürün sahibi 2026-11-07'de önerilen varsayılanları onayladı)

## Q-02 · Anthropic API anahtarı (isteğe bağlı)
Fiş okuma artık varsayılan olarak yapay zekâsız (Tesseract OCR + kurallar). `ANTHROPIC_API_KEY` girilirse `OCR_ENGINE=auto` modunda yalnızca kural tabanlı okuma başarısız olduğunda yedek olarak kullanılır. Hiç kullanılmasın istenirse Render'da `OCR_ENGINE=tesseract` yap.
**Cevap:** Fişler (レシート) yapay zekâsız kalır. **Yapay zekâ yalnızca el yazısı 仕切書 ve banka defteri (通帳) okumada** kullanılır (ürün sahibi kararı 2026-11-07). `ANTHROPIC_API_KEY` Render'a girilmeli; `OCR_ENGINE=tesseract` önerilir.

## Q-03 · 令和8年分 基礎控除 tablosu (cevaplandı — tax-watcher, 2026-11-06)
NTA No.1199 tablosundan 2026 yılı için ≤2,350万 → 104万 okunuyor ama hücre yapısı belirsiz. tax-watcher birincil kaynaktan (改正法 / NTA Q&A 令和8年5月版) doğrulayıp TAX_RULES'u ✅ yapınca T-004'ün 2026 kısmı açılır.
**Cevap:** tax-watcher 2026/2027 tablosunu doğruladı (T-004b done). Kapandı.

## Q-04 · Hedef müşteri önceliği (açık)
Önce 個人事業主 (確定申告) mi, yoksa 小規模法人 (3月決算, 法人税) mı? Şu anki varsayım: **個人事業主 + küçük 合同会社**, beyan tarafında önce 個人.
**Cevap:** Öncelik **個人事業主 (確定申告)**, ikinci olarak küçük 合同会社. Beyan tarafı önce 個人. (ürün sahibi 2026-11-07'de önerilen varsayılanları onayladı)

## Q-05 · Panel adresi (açık)
render.yaml'a `jsaas-panel` statik sitesi eklendi; Render blueprint senkronunda otomatik oluşur. Render alt alan adı farklı çıkarsa (ör. `jsaas-panel-xxxx.onrender.com`) tegaru-line-bot → Environment → `PANEL_URL` değerini düzelt. Blueprint senkronu "manual" ise Render → Blueprints → japonyamuhasebe → Sync.
(2026-11-07 developer, T-048b: API artık yalnızca `PANEL_URL` origin'inden (+ localhost:3000) gelen tarayıcı isteklerine CORS izni veriyor. `PANEL_URL` panelin gerçek adresiyle aynı değilse panel API'ye bağlanamaz (「通信エラー」) — bu durumda `PANEL_URL`'yi düzelt ya da `CORS_ORIGINS`'e panel adresini virgülle yaz.)
**Cevap:** Blueprint senkronundan sonra gerçek panel adresi `PANEL_URL`'ye yazılacak (insan adımı, Render). (ürün sahibi 2026-11-07'de önerilen varsayılanları onayladı)

## Q-06 · WhatsApp Business (açık)
Kod hazır (`bot/whatsapp.py`, webhook `https://tegaru-line-bot.onrender.com/whatsapp`). Canlıya almak için Meta for Developers'ta WhatsApp uygulaması + telefon numarası gerekir; Render'a `WHATSAPP_APP_SECRET`, `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID` girilmeli (`WHATSAPP_VERIFY_TOKEN` Render'da otomatik üretildi, Meta'daki "Verify token" alanına aynısı yazılır). Japonya'da LINE öncelikli olduğundan bu adım ertelenebilir.
**Cevap:** WhatsApp ertelendi; Japonya'da önce LINE. Kod hazır kalır, canlıya alma satış sonrası. (ürün sahibi 2026-11-07'de önerilen varsayılanları onayladı)

## Q-07 · Render ücretsiz PostgreSQL süresi (bilgi)
render.yaml'a `jsaas-db` (free) eklendi; artık kayıtlar yeniden başlatmada silinmez. Render'ın ücretsiz veritabanları oluşturulduktan ~30 gün sonra süresi dolar (yükseltme veya yeniden oluşturma gerekir). Canlı kullanıcı gelmeden önce ücretli plana (Basic) geçilmeli veya başka bir sağlayıcı seçilmeli. Ayrıca Render hesabında yalnızca bir ücretsiz veritabanı olabilir.
**Cevap:** Gerçek kullanıcı gelmeden önce Render PostgreSQL **Basic** plana geçilecek. Ücretsiz DB yalnızca test için. (ürün sahibi 2026-11-07'de önerilen varsayılanları onayladı)

## Q-08 · Render servisinin Docker'a geçişi (kontrol gerekli)
Sunucuda Tesseract olması için `tegaru-line-bot` servisi render.yaml'da `runtime: docker` yapıldı (`bot/Dockerfile`). Render mevcut bir servisin çalışma ortamını blueprint ile değiştirmeyi reddederse: Render → tegaru-line-bot → Settings → Delete Service, ardından Blueprints → japonyamuhasebe → Sync (servis Docker olarak yeniden oluşur; ortam değişkenleri yeniden girilmeli). Kontrol: `https://tegaru-line-bot.onrender.com/` yanıtında `"tesseract": true`.
**Cevap:** Docker'a geçiş kabul. Render reddederse servis silinip blueprint'ten yeniden oluşturulacak (insan adımı). (ürün sahibi 2026-11-07'de önerilen varsayılanları onayladı)

## Q-09 · OCR hızı ve Render planı (bilgi)
tessdata_best modeliyle fiş başına ~2–5 sn (tam çekirdek). Render free planı 0.1 CPU olduğundan 20–50 sn sürebilir; LINE'da yanıt gecikir (T-025 ile çözülecek). Canlı kullanıcıdan önce tegaru-line-bot için Starter (0.5 CPU) plana geçilmesi önerilir.
**Cevap:** Canlı kullanıcıdan önce `tegaru-line-bot` **Starter** plana geçilecek. (ürün sahibi 2026-11-07'de önerilen varsayılanları onayladı)

## Q-10 · Ödeme sağlayıcısı (açık)
Varsayılan: **Stripe** (JPY, Japonya kartları, konbini ödemesi). Alternatif: PAY.JP (Japon şirketi). Ajanlar Stripe test moduyla geliştiriyor; canlı anahtar senin Stripe hesabından gelmeli.
(2026-11-07 developer, T-042: Render'a `sync: false` ile eklendi — **değer girilmeli**: `STRIPE_SECRET_KEY` (önce `sk_test_…`), `STRIPE_WEBHOOK_SECRET` (Stripe → Developers → Webhooks → uç nokta `https://tegaru-line-bot.onrender.com/api/v1/billing/webhook`, olaylar: `checkout.session.completed`, `customer.subscription.created/updated/deleted`), `STRIPE_PRICE_PERSONAL`, `STRIPE_PRICE_BUSINESS` (Stripe'ta aylık JPY "Price" kimlikleri `price_…`). Anahtar girilene kadar ödeme kapalı ve ücretsiz plan sınırları **uygulanmıyor**.)
**Cevap:** **Stripe** (JPY, kart + konbini). Test moduyla devam; canlı anahtar ürün sahibinin Stripe hesabından girilecek. (ürün sahibi 2026-11-07'de önerilen varsayılanları onayladı)

## Q-11 · Fiyatlandırma (açık)
Yer tutucu: Free (ayda 30 fiş, 3 fatura) / 個人 ¥980 / 法人 ¥2,980 (vergi hariç, aylık). Gerçek fiyatları yaz.
(2026-11-07 developer, T-042: yer tutucular `bot/billing.py` `PLANS` içinde. Ek karar: `STRIPE_SECRET_KEY` girildiği anda mevcut LINE kullanıcılarına da ücretsiz plan sınırı uygulanır — mevcut kullanıcılara geçiş süresi / ücretsiz dönem istiyor musun? İstemezsen `BILLING_ENFORCE_LIMITS=0` ile sınırlar kapalı tutulabilir.)
(2026-11-07 developer, T-054: 税率ごとに分割 edilen tek fiş kotada 1 件 sayılıyor (aynı görsel = 1). Satır başına sayılmasını istersen belirt.)
**Cevap:** Fiyatlar onaylandı: **Free** (ayda 30 fiş, 3 fatura) / **個人 ¥980** / **法人 ¥2,980** (aylık, vergi hariç). `placeholder` işaretini kaldır, yıllık plan yok. (ürün sahibi 2026-11-07'de önerilen varsayılanları onayladı)

## Q-12 · Satıcı bilgileri — 特定商取引法に基づく表記 (açık)
Zorunlu: 販売業者名, 運営責任者, 所在地, 電話番号, メールアドレス, 販売価格, 支払方法・時期, 解約・返金. Japonya'da şirket/adres yoksa nasıl gösterileceğini müşavirle netleştir. Yasal metinler bu cevaplanana kadar "ドラフト" olarak yayında.
(2026-11-07 developer, T-043: sayfalar yayında — `/legal/terms/`, `/legal/privacy/`, `/legal/tokushoho/`, metin `dashboard-next/app/lib/legal.ts`. Satıcı bilgileri Render → jsaas-panel → Environment'a **değer girilmeli**: `NEXT_PUBLIC_LEGAL_SELLER`, `_MANAGER`, `_ADDRESS`, `_PHONE`, `_EMAIL` (girildikten sonra Manual Deploy ile yeniden derle). Boş alanlar 「要確認」 görünür. Avukat/müşavir kontrolü gereken ve 「要確認」 işaretli maddeler: 返金なし・期間末解約, 損害賠償上限 (月額料金), 合意管轄, 外国にある第三者 bilgi sunumu (APPI 28条: ülke + o ülkenin sistemi), 帳簿 saklama süresi ve hesap silindikten sonra veri silme süresi, fiyat gösterimi (税込 gösterim zorunlu mu). Ayrıca karar: 規約 üzerindeki sorumluluğu "当社" mı (şirket kurulana kadar bireysel ad mı) yazılacak?)
**Cevap:** Yapı onaylandı, metinler 'ドラフト' kalır. **Gerçek bilgiler (販売業者名, 運営責任者, 所在地, 電話, e-posta) ürün sahibinden gelecek** — ajanlar uydurmaz. Japonya'da adres yoksa '請求があった場合は遅滞なく開示します' yöntemi müşavirle netleştirilecek. (ürün sahibi 2026-11-07'de önerilen varsayılanları onayladı)

## Q-13 · E-posta gönderim servisi (açık)
Şifre sıfırlama ve bildirimler için: Resend / SendGrid / Amazon SES. Seçilen servisin anahtarı Render'a `MAIL_PROVIDER` + `MAIL_API_KEY` olarak girilmeli; o zamana kadar e-postalar yalnızca sunucu log'una yazılır. (2026-11-07 developer: iki değişken `render.yaml`'a `sync: false` ile eklendi — **değer girilmeli**; T-040 parola sıfırlama e-postası şu an yalnızca log'a düşüyor.)
**Cevap:** **Resend** (`MAIL_PROVIDER=resend`). Anahtar ürün sahibi hesabı açınca Render'a girilecek; o zamana kadar log. Gönderen alan adı doğrulaması gerekecek. (ürün sahibi 2026-11-07'de önerilen varsayılanları onayladı)

## Q-14 · Fiş görselleri için kalıcı depolama (açık — planner, 2026-11-07)
Fiş görselleri şu an sunucu konteynerinin diskine (`receipts/`) yazılıyor. Render'da bu servise disk bağlı değil ve `main` her birleştirmede yeniden yayınlandığı için **görseller her deploy'da siliniyor** (gizlilik politikası ve 電帳法 saklama beklentisiyle çelişir). T-011 depolama soyutlamasını yazacak. Karar: (a) S3 uyumlu nesne depolama — Cloudflare R2 (çıkış ücreti yok, önerilen) / AWS S3 Tokyo / başka; hesap açılıp `STORAGE_BUCKET`, `STORAGE_ENDPOINT`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY` Render'a **değer girilmeli** (T-011 sonrası), veya (b) Render Persistent Disk (ücretli plan gerektirir). Cevap gelene kadar davranış değişmez (yerel disk).
**Cevap:** **(a) Cloudflare R2** (S3 uyumlu, çıkış ücreti yok). T-011 S3 uyumlu soyutlamayı yazsın; değişkenler `sync: false` ile render.yaml'a, değerler hesap açılınca girilecek. (ürün sahibi 2026-11-07'de önerilen varsayılanları onayladı)
**Değer girilmeli (developer, 2026-11-07, T-011 tamam):** Render `tegaru-line-bot` → Environment: `STORAGE_ENDPOINT` (`https://<accountid>.r2.cloudflarestorage.com`), `STORAGE_BUCKET`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY` (R2 → Manage API tokens → Object Read & Write, yalnızca bu bucket). Dördü girilene kadar görseller yerel diskte (deploy'da silinir).

## Q-15 · Hesap silme talebinin işlenmesi (açık — developer, 2026-11-07, T-046b)
Panelden gelen silme talepleri artık `deletion_requests` tablosuna kaydediliyor (veri silinmiyor; operatör listesi `GET /api/v1/admin/deletion-requests`, adımlar `docs/OPERATIONS.md`). Karar gerekiyor: (1) talep sonrası kaç gün içinde silinsin (öneri: 30 gün), (2) 電子帳簿保存法 / 法人税法 saklama yükümlülüğü kullanıcıda olduğundan silmeden önce ZIP yedeği yeterli mi, yoksa belirli süre (ör. 7 yıl) bizde de tutulacak mı (gizlilik politikası Q-12 ile uyumlu olmalı), (3) talebi kullanıcı panelden geri alabilsin mi. Cevap gelene kadar silme tamamen elle ve ürün sahibi onayıyla; otomatik silme betiği yazılmaz.

## Q-16 · Resmî LINE hesabı "友だち追加" bağlantısı (açık — developer, 2026-11-07, T-044)
Tanıtım sayfası `/lp/` 「LINEで友だち追加」 düğmesini yalnızca bağlantı tanımlıysa gösterir. Render → jsaas-panel → Environment'a **değer girilmeli**: `NEXT_PUBLIC_LINE_ADD_URL` (LINE Official Account Manager → 友だち追加ガイド → URL, ör. `https://lin.ee/xxxx`; yalnızca `https://lin.ee/` veya `https://line.me/` kabul edilir), sonra Manual Deploy. Boşken sayfa yalnızca 「無料で始める」 (/signup/) gösterir. Ayrıca: kök `/` yerine `/lp/` ziyaretçilerin açılış sayfası olsun mu (şu an `/` = panel)?

## Q-17 · Muhasebe yazılımı CSV'sinde formül nötrleme (açık — developer, 2026-11-07, T-059)
Tüm veri ZIP'indeki `entries.csv` artık `=`/`+`/`-`/`@`/TAB/CR ile başlayan 取引先/摘要 hücrelerine `'` ekliyor (Excel'de formül çalışmaz). Ancak freee / マネーフォワード / 弥生 içe aktarımının bu `'`'yu silip silmediği resmi belgelerden doğrulanamadı; silmezse 取引先 adı `'=…` olarak içe aktarılır. Bu yüzden içe aktarma amaçlı `/api/v1/export.csv` **değişmedi** (Shift_JIS, Japonca Excel'de doğrudan açılabildiği için risk sürüyor). Karar: (a) `/export.csv`'de de nötrle (öneri: güvenlik öncelikli; böyle adlar nadir), (b) olduğu gibi bırak, (c) T-012b'de gerçek içe aktarma denemesinden sonra karar ver. Kod hazır: `api.py` içinde `export.to_csv(rows, format, escape_formulas=True)`.


## Q-15 · 国税庁 法人番号 Web-API アプリケーションID (açık — ürün sahibi)
Banka defterindeki firma adlarını resmi kayıttan bulmak için. Başvuru ücretsiz: https://www.houjin-bangou.nta.go.jp/webapi/ → 「アプリケーションIDの発行届出」. Gelen kimlik Render'a `NTA_APP_ID` olarak girilir. O zamana kadar firma rehberi (Excel + onaylar) ile çalışır.
**Cevap:**

## Q-16 · Birden çok şirket — fiyatlandırma (açık — ürün sahibi, sonraya bırakıldı 2026-11-07)
Bir hesaba sınırsız şirket (事業所) eklenebiliyor; her şirket ayrı defter ve şimdilik kendi planı (Free). Seçenekler: (a) her şirket ayrı abonelik, (b) 法人 planında N şirkete kadar dahil + ek şirket başına ücret, (c) şirket sayısına göre kademeli plan. Koruma sınırı: `MAX_COMPANIES_PER_ACCOUNT` (varsayılan 100).
**Cevap:**

## Q-18 · 仕切書 (slips) değişiklik geçmişi — T-060 dosyalarına dokunma izni (açık — developer, 2026-11-08, T-065b)
entries / invoices / bank_tx değişiklikleri artık `audit_log`'a yazılıyor ve panel 経費精算'te 「履歴」 ile görünüyor. 仕切書'nin onay/red/düzeltmeleri `bot/slips*.py` içinde; bu dosyalara ajanların dokunmaması istendiği için eklenmedi (onaylanan 仕切書'nin oluşturduğu 売上 kaydı zaten entries geçmişinde var). Karar: (a) ajan `slips.py`'de update/approve/reject çağrılarına `store._audit(..., "slip", ...)` eklesin (öneri; küçük, davranış değişmez), (b) ürün sahibi kendisi ekler, (c) gerek yok. Görev: T-065c (blocked).
**Cevap:**

## Q-19 · e-Tax 仕様書 indirme — 利用上の注意 kabulü (açık — developer, 2026-11-08, T-045b/T-067)
e-Tax .xtx üretimi (T-067/T-068) için 国税庁'nin 仕様書'si (項番7 手続一覧, 9 所得税, 19 XMLスキーマ; CAB arşivi) gerekiyor. Sayfa: indirme, 「利用上の注意」'yi kabul etmek sayılır — ajan bunu ürün sahibi adına kabul etmemeli. Seçenekler: (a) ürün sahibi https://www.e-tax.nta.go.jp/shiyo/ksk2/ksk2_shiyo3.htm 'deki 利用上の注意'yi okuyup ajanın indirmesine izin verir (öneri), (b) ürün sahibi dosyaları kendisi indirip depoya değil özel bir yere koyar, (c) e-Tax çıktısı şimdilik yapılmaz (PDF + elle giriş yeter). Ayrıntı: `docs/ETAX.md`.
**Cevap:**
