# REST API v1

Taban: `https://tegaru-line-bot.onrender.com/api/v1` · Kimlik: `Authorization: Bearer tk_...`
Token alma: LINE'da 「パネル」 yaz **veya** admin: `POST /api/v1/admin/tokens {"user_id": "..."}` (`X-Admin-Key`).
Hesap (T-040): `POST /auth/signup` / `POST /auth/login` `{email, password}` → `{account:{id,email}, user_id, token}` (token yukarıdaki Bearer ile aynı).
Deneme verisi: `POST /api/v1/admin/demo-seed` (`X-Admin-Key`) → `demo` defteri + token.

| Yöntem | Yol | Açıklama |
|---|---|---|
| GET | `/summary?month=YYYY-MM` | 売上・経費・利益, önceki aya göre % değişim, 登録番号なし gider sayısı, 売掛金 |
| GET | `/cashflow?months=6&end=YYYY-MM` | Aylık gelen/giden/net |
| GET | `/entries?date_from&date_to&q&amount_min&amount_max&kind` | 電子帳簿保存法 arama (tarih/tutar/karşı taraf) |
| POST | `/entries` | Web'den kayıt `{date, kind, store, amount, category, rate, invoice_no}` |
| GET | `/tax/consumption?year=2026&method=honsoku|kani|niwari|sanwari&kani_type=` | 消費税 hesabı (`bot/tax/consumption.py`). Yanıtta `unqualified`: 登録番号なし仕入の控除割合別内訳 `[{ratio, gross, tax, credited}]` |
| GET/PUT | `/profile` | 事業者名, 登録番号, 個人/法人 |
| GET | `/invoices?status=paid|unpaid` | Faturalar (+ `overdue` bayrağı) |
| POST | `/invoices` | 適格請求書 oluştur `{client, issued?, due, items:[{name, qty, unit_price(税抜), rate}]}` |
| POST | `/invoices/{no}/paid?paid_on=` | 入金消込 (oran başına 売上 kaydı da oluşturur) |
| GET | `/invoices/{no}/pdf` | PDF (IPAゴシック gömülü) |
| GET | `/export.csv?format=freee|mf|yayoi&year=` | Muhasebe yazılımı CSV (Shift_JIS) |

Para birimi tamsayı yen. Hatalar: 400 (doğrulama), 401 (token), 404, 422 (şema).
| GET | `/pl?year=` | 青色申告決算書 (損益計算書) özeti: 売上, kalem bazında 経費, 所得 |
| GET | `/tax/income?year=&blue=650000&social_insurance=&other_deductions=` | 所得税 tahmini. 基礎控除 2025–2027年分 (TAX_RULES §2 ✅); diğer yıllar 409 |
| PATCH / DELETE | `/entries/{id}` | Kaydı düzelt (tarih, karşı taraf, tutar, kalem, oran, 登録番号) / sil |
| POST | `/receipts/ocr` | Ham görsel gövdesi (image/*, ≤10MB) → okunan kayıt önerileri (kaydetmez) |
| POST | `/bank/import?account=` | Banka CSV (Shift_JIS/UTF-8) içe aktar; tekrar eden satırlar atlanır |
| GET | `/bank/transactions` | Hareketler + 消込 önerileri (入金 = 未入金請求書合計) |
| POST | `/bank/match` | `{tx_id, invoice_no}` → fatura 支払済 (ödeme tarihi = hareket tarihi) |
| POST | `/bank/{id}/entry` | Çekimi 経費 olarak kaydet `{category, rate}` |
| GET | `/channels` | LINE / WhatsApp / OCR durumu (sırsız) |
| POST | `/auth/signup` | Hesap aç `{email, password(≥10)}` → 201 + boş web defteri (`web:…`) ve token. Aynı e-posta 409 |
| POST | `/auth/login` | `{email, password}` → token (hatalı 401, e-posta varlığı sızdırılmaz) |
| GET | `/auth/me` | Oturumdaki defter + hesap (`account: null` = yalnızca LINE kodu ile bağlı) |
| POST | `/auth/link-line` | `{code}` (LINE 「パネル」 kodu) → hesabın defteri LINE defteri olur, yeni token. Web defterinde veri varsa veya LINE defteri başka hesaba bağlıysa 409; eski token'lar ve kod iptal |
| POST | `/auth/password-reset/request` | `{email}` → her zaman 202; bağlantı e-postayla (`MAIL_PROVIDER` yoksa yalnızca log, Q-13), 1 saat geçerli |
| POST | `/auth/password-reset/confirm` | `{token, password}` → parola değişir, tüm oturumlar kapanır; geçersiz/süresi dolmuş 400 |
| GET | `/billing/plans` | Planlar (kimliksiz): `free` (aylık 30 経費, 3 請求書) / `personal` / `business`; fiyatlar yer tutucu (`placeholder: true`, Q-11), `available` = Stripe fiyatı tanımlı |
| GET | `/billing/status` | Defterin planı, sınırları, bu ayki kullanım (`usage.receipts` = BANK/INVOICE/DEMO dışı 経費, `usage.invoices`), `payments_enabled`, `limits_enforced`, abonelik |
| POST | `/billing/checkout` | `{plan: personal|business}` → `{url}` Stripe Checkout (abonelik). `STRIPE_SECRET_KEY` veya plan fiyatı yoksa 503; aynı plan 409; Stripe hatası 502 |
| POST | `/billing/cancel` | Dönem sonunda iptal (`cancel_at_period_end`); veri silinmez. Ücretli plan yoksa 404 |
| POST | `/billing/webhook` | Stripe webhook (`Stripe-Signature`, 300 sn tolerans). `checkout.session.completed`, `customer.subscription.created|updated|deleted` işlenir; olay kimliğiyle idempotent. Sır yoksa 503, imza hatalı 400 |

**Hız sınırı (T-048):** IP başına (`X-Forwarded-For` ilk değeri; `RATE_LIMIT_PROXY_HOPS=N` → sağdan N'inci) kayan pencere: `/auth/login` 10/dk, `/auth/signup` 5/dk, `/auth/password-reset/request` 5/dk, `/receipts/ocr` 20/dk. Aşılırsa **429** + `Retry-After` (sn) + Japonca `detail`. `RATE_LIMIT_LOGIN|SIGNUP|PASSWORD_RESET|OCR="adet/saniye"` ile değişir, `0` kapatır. Bellek içi (tek örnek); yeniden başlatmada sıfırlanır. `/callback` ve `/` etkilenmez.

**CORS ve güvenlik başlıkları (T-048b):** `CORS_ORIGINS` boş veya `*` ise izin verilen origin'ler yalnızca `PANEL_URL` (origin kısmı) + `http://localhost:3000`; açık bir liste verilirse aynen kullanılır. Yöntemler GET/POST/PUT/PATCH/DELETE, başlıklar `Authorization`, `Content-Type`; `Content-Disposition` ve `Retry-After` okunabilir. Tüm yanıtlarda: `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Strict-Transport-Security: max-age=31536000`, `X-Frame-Options: DENY`, `Content-Security-Policy: frame-ancestors 'none'` (`bot/security.py`).

Plan sınırları yalnızca ödeme açıkken (`STRIPE_SECRET_KEY` var ve `BILLING_ENFORCE_LIMITS≠0`) uygulanır: ücretsiz planda ay içinde 31. 経費 (`POST /entries`, kind=exp) veya 4. fatura → **402** (Japonca `detail`). LINE/WhatsApp: 31. 経費 kaydı (metin veya fiş görseli; görselde OCR'dan önce) kaydedilmez, Japonca uyarı + `{PANEL_URL}/billing/` bağlantısı döner (T-042b). Checkout dönüşü `/billing/?billing=success|cancel`.

## Ekip üyeleri (T-041)
Roller: **owner** (defter sahibi: hesabın kendi defteri veya LINE/admin token'ı — her şey), **accountant** (muhasebe verisini okur + yazar: kayıt, fiş OCR, banka, fatura, `/profile`), **viewer** (yalnızca GET: özet, liste, CSV/PDF). Viewer'ın yazma isteği → **403**. Abonelik (`/billing/checkout|cancel`), `/auth/link-line` ve `/team/*` yönetimi yalnızca owner (diğerleri 403). Rol her istekte okunur: rol değişikliği/çıkarma eski token'lara hemen yansır (çıkarılan üye 401).

| Yöntem | Yol | Açıklama |
|---|---|---|
| POST | `/team/invites` | (owner) `{role: accountant|viewer}` → 201 `{code: "iv_…", role, expires_at}`; tek kullanımlık, 7 gün. Açık davet en fazla 10 (409) |
| GET | `/team/members` | (owner) `{members: [{account_id, email, role, joined_at?}], invites: [{id, role, created_at, expires_at}]}` (kod tekrar gösterilmez) |
| DELETE | `/team/invites/{id}` | (owner) daveti iptal; yoksa 404 |
| PATCH | `/team/members/{account_id}` | (owner) `{role}` → rol değişir; üye yoksa 404 |
| DELETE | `/team/members/{account_id}` | (owner) üyelik + o üyenin bu defterdeki oturumları silinir |
| POST | `/team/join` | (hesapla giriş yapmış herkes) `{code}` → 201 `{user_id, role, token}` (token = davet eden defter için üye oturumu). Geçersiz/süresi dolmuş/kullanılmış 400, kendi defteri veya zaten üye 409, hesapsız (yalnızca LINE) token 403. Defter başına en fazla 20 üye |
| GET | `/team/ledgers` | `{current, ledgers: [{user_id, role, business_name}]}` — kendi defteri (owner) + üye olunan defterler |
| POST | `/team/switch` | `{user_id}` → `{user_id, role, token}`; erişim yoksa 403 |

`GET /auth/me` yanıtına `role` eklendi; üye oturumunda `account` üyenin kendi hesabıdır. Token sınırı (5) artık (defter, hesap) başınadır: üye oturumları sahibin token'larını düşürmez.
