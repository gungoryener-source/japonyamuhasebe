# Canlıya alma kılavuzu (T-078)

Kod tarafı hazır; canlıya alma yalnızca **insan adımlarına** (hesap açma, Render ortam değişkenleri) bağlı.
Ajanlar Render/LINE/Stripe ayarlarına dokunmaz. Bu sayfa adımların sırası ve sonunda yapılacak uçtan uca duman testidir.
Her adımın ayrıntısı `tasks/QUESTIONS.md`'deki ilgili soruda.

## 0. Durumu görmek: `/admin/config-check`

```bash
read -rs ADMIN_KEY   # Render → tegaru-line-bot → Environment → ADMIN_KEY (yapıştır, ekranda görünmez)
curl -s -H "X-Admin-Key: $ADMIN_KEY" https://tegaru-line-bot.onrender.com/admin/config-check | python3 -m json.tool
```

- Yanıt her değişken için yalnızca `set: true/false`, ilgili soru (`question`) ve düzey (`required` / `recommended` / `optional`) içerir. **Değer, uzunluk veya önek asla dönmez.**
- `ready: true` → zorunlu değişkenlerin hepsi girilmiş. `missing_required` eksik adları, `open_questions` ilgili Q numaralarını listeler.
- `runtime`: `db` (`postgres` olmalı), `storage` (`s3` olmalı; `local` = görseller deploy'da silinir), `tesseract` (`true` olmalı; `false` → Docker'a geçiş yapılmamış, Q-08), `mail_provider_supported` (`MAIL_PROVIDER=resend` ise `true`).
- Anahtar yoksa / yanlışsa 401. Sorgu dizesi (`?key=`) kabul edilmez (anahtar log'a düşmesin).
- Panel (jsaas-panel, statik site) değişkenleri bu uç noktadan görünmez → adım 8'de elle kontrol.

## Adım sırası

| # | Adım | Soru | Nerede | Kontrol |
|---|---|---|---|---|
| 1 | Render plan yükseltmeleri: `jsaas-db` → **Basic**, `tegaru-line-bot` → **Starter** | Q-07, Q-09 | Render → ilgili servis → Settings → Plan | `runtime.db == "postgres"`; ücretsiz DB ~30 günde silinir |
| 2 | Docker'a geçiş (Tesseract için). Blueprint reddederse servis silinip blueprint'ten yeniden oluşturulur | Q-08 | Render → Blueprints → japonyamuhasebe → Sync | `runtime.tesseract == true`, `GET /` → `"tesseract": true` |
| 3 | LINE Messaging API kanalı: `LINE_CHANNEL_SECRET`, `LINE_CHANNEL_ACCESS_TOKEN`; Webhook URL `https://tegaru-line-bot.onrender.com/callback` (Use webhook: ON); ardından alt menü | Q-01 | LINE Developers + Render Environment | `GET /` → `line_configured: true`, `line_secret_format_ok: true`; `curl -X POST -H "X-Admin-Key: $ADMIN_KEY" …/admin/richmenu` |
| 4 | `PANEL_URL` = panelin gerçek adresi (CORS buna göre; yanlışsa panelde 「通信エラー」) | Q-05 | Render → tegaru-line-bot → Environment | Panel açılıp giriş yapılabiliyor |
| 5 | Cloudflare R2: `STORAGE_ENDPOINT`, `STORAGE_BUCKET`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY` (token: yalnızca bu bucket, Object Read & Write) | Q-14 | Cloudflare + Render Environment | `runtime.storage == "s3"` |
| 6 | Resend: `MAIL_PROVIDER=resend`, `MAIL_API_KEY`, `MAIL_FROM` (Resend'de doğrulanmış alan adı) | Q-13 | Resend + Render Environment | `mail_provider_supported: true`; panelden şifre sıfırlama e-postası gelir |
| 7 | Stripe **test** modu: `STRIPE_SECRET_KEY` (`sk_test_…`), `STRIPE_WEBHOOK_SECRET` (uç nokta `…/api/v1/billing/webhook`, olaylar `checkout.session.completed`, `customer.subscription.created/updated/deleted`), `STRIPE_PRICE_PERSONAL`, `STRIPE_PRICE_BUSINESS` | Q-10, Q-11 | Stripe Dashboard + Render Environment | Test kartıyla abonelik → panelde plan değişir. **Not:** anahtar girildiği anda ücretsiz plan sınırları uygulanmaya başlar |
| 8 | Panel değişkenleri (jsaas-panel): `NEXT_PUBLIC_LEGAL_SELLER/_MANAGER/_ADDRESS/_PHONE/_EMAIL`, `NEXT_PUBLIC_LINE_ADD_URL` → sonra **Manual Deploy** (derleme anında okunur) | Q-12, Q-21 | Render → jsaas-panel → Environment | `/legal/tokushoho/` 「要確認」 göstermez; `/lp/` 友だち追加 düğmesi görünür |
| 9 | (Önerilen) `ANTHROPIC_API_KEY` (仕切書・通帳 AI okuma), `NTA_APP_ID` (登録番号/法人番号) | Q-02, Q-20 | Render Environment | config-check `recommended` satırları `true` |
| — | (Ertelendi) WhatsApp: `WHATSAPP_APP_SECRET`, `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID` | Q-06 | — | `optional` |

Her Environment değişikliğinden sonra Render servisi yeniden başlatır; birkaç dakika sonra config-check'i tekrar çalıştırın.
Adım 1–7 bittiğinde config-check `ready: true` olmalı.

## Uçtan uca duman testi

Önce `ready: true` ve `GET https://tegaru-line-bot.onrender.com/` → `"ok": true` olduğundan emin olun.

1. **Kayıt:** panelde `/signup/` ile test hesabı aç (gerçek kişi verisi kullanmayın). Şifre sıfırlama e-postası gelir mi bakın (adım 6).
2. **LINE bağlama:** resmî LINE hesabını telefondan arkadaş ekle; panelin gösterdiği bağlama adımını izle.
3. **Fiş:** LINE'a bir fiş fotoğrafı gönder → bot 勘定科目 / 税率 / tutar ile yanıt verir (OCR uzun sürerse sonuç push mesajla gelir, T-025).
   Metinle de dene: `コンビニ 540` gibi bir mesaj.
4. **Panelde görünür:** panel ana sayfa (`/`) ve `/expenses/`'te kayıt aynı tutarla görünür; fiş görseli açılır (R2'den, adım 5).
5. **Deploy sonrası kalıcılık:** Render'da Manual Deploy → aynı kaydın görseli hâlâ açılıyor mu (yerel diskte olsaydı silinirdi).
6. **CSV:** `/tax/`'tan freee / マネーフォワード / 弥生 CSV indir (`GET /api/v1/export.csv?format=`); Excel/muhasebe yazılımında Shift_JIS olarak açılır, satır görünür.
7. **PDF:** `/invoices/`'ta bir 適格請求書 oluştur → PDF indir (Japonca yazı tipi gömülü); `/tax/`'tan 青色申告決算書 参考 PDF indir.
8. **Ödeme (test):** `/billing/` → 個人 → Stripe test kartı `4242 4242 4242 4242` → panelde plan 「個人」 olur; Stripe Dashboard → Webhooks'ta olaylar 200.
9. **Yedek:** `docs/OPERATIONS.md` → PostgreSQL yedeği bir kez alınıp dosyanın oluştuğu doğrulanır.

Herhangi bir adım başarısızsa: Render → tegaru-line-bot → Logs; ilgili Q numarasını `tasks/QUESTIONS.md`'de not olarak ekleyin.
Test hesabını sonra `/settings/`'teki silme talebi ile silme talebine çevirin (işleme: `docs/OPERATIONS.md`).
