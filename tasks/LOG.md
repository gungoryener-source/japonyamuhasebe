# Ajan çalışma günlüğü (en yeni üstte)

Biçim: `## YYYY-MM-DD HH:MM JST · <rol> · <görev>` + 3–6 satır: ne yapıldı, testler, sonraki adım/engeller.

## 2026-11-07 19:46 JST · developer · T-046 tüm veri ZIP
- Yeni `bot/archive.py` + `GET /api/v1/export/all.zip` (tüm roller, viewer dahil): `entries.csv` (tüm dönem, freee sütunları), `invoices.csv` (明細 JSON sütunu, 入金済/未入金, 入金日), `invoices/<番号>.pdf`, Japonca `README.txt` (JST oluşturma zamanı, sayılar). Bellekte `zipfile`, `entries_in_range` ile satır sınırı yok.
- Yorum: ZIP içindeki CSV'ler **UTF-8 BOM** (yedek amaçlı, CP932'de olmayan karakterler kaybolmasın); muhasebe yazılımı içe aktarımı için mevcut Shift_JIS `/export.csv` duruyor (README'de not). PDF adı yol geçişine karşı temizleniyor. 電帳法 保存期間 TAX_RULES'ta ⚠️ olduğundan README'ye süre yazılmadı.
- Panel 設定: 「データのダウンロード」 kartı + 「全データをダウンロード」 (ja/tr/en). docs/API.md güncellendi.
- Kapı: pytest 456 geçti (yeni 10: 401, boş defter, tüm yıllar + fatura durumları, kiracı ayrımı, viewer, >5000 kayıt, PDF adı güvenliği); `next build` + check:tax/legal/team yeşil.
- Sonraki: T-046b (hesap silme talebi), sonra T-044 / T-044b.

## 2026-11-07 18:44 JST · developer · T-011 fiş görseli depolama (R2)
- Yeni `bot/storage.py`: `put`/`get`, sürücü local | s3 (S3 uyumlu, Cloudflare R2; yol stili, AWS SigV4 — yeni paket yok). 4 `STORAGE_*` doluysa otomatik s3; değilse yerel + başlangıç uyarısı.
- `process_image` görseli `storage.put` ile yazar; `image_path` biçimi (`receipts/<ad>.jpg`) aynı. S3 hatasında yerel yedek; anahtar doğrulaması yol geçişini reddeder.
- render.yaml'a `STORAGE_ENDPOINT/BUCKET/ACCESS_KEY/SECRET_KEY` `sync: false` (mevcut değişkenlere dokunulmadı). Q-14'e "değer girilmeli" notu.
- Kapı: pytest 446 geçti (yeni 14; SigV4 AWS referans vektörü dahil). dashboard-next değişmedi.
- Sonraki: P1 — T-056 (Resend e-posta) / T-057 (OCR varsayılanı); T-034 artık açılabilir (görsel okuma uç noktası).

## 2026-11-07 18:08 JST · reviewer (oturum) · T-058 hız sınırı XFF sahteleme
- Render istemcinin XFF'ini silmeyip `<istemci>, <Cloudflare kenarı>` ekliyor → `RATE_LIMIT_PROXY_HOPS` varsayılanı 0 → 2 (sağdan 2.); her istekte değişen sahte ilk değer artık yeni kova açmıyor.
- `/auth/login` için IP'den bağımsız e-posta kovası (20/10dk, `RATE_LIMIT_LOGIN_EMAIL`); `ratelimit.check()` yardımcı. docs/API.md güncellendi. render.yaml değişmedi.
- Testler +2 (sahte XFF ile atlatma yok; IP değiştirerek aynı e-postaya 21. deneme 429, büyük/küçük harf aynı kova). Toplam 432 yeşil.
- Ödünleşim: saldırgan bir e-postayı 10 dk kilitleyebilir; gerekirse sınır env ile gevşetilir.

## 2026-11-07 17:50 JST · developer · T-055 kesin fiyatlar
- `billing.PLANS` Free ¥0 / 個人 ¥980 / 法人 ¥2,980 (aylık, 税抜) `placeholder=False`; `/billing/plans` yanıtına `tax_excluded: true`, `interval: "month"` eklendi (alan adları korunur, geriye uyumlu).
- Panel 料金プラン: 「仮」 rozeti ve 「価格は仮のものです」 notu kaldırıldı → 「価格はすべて月額・税抜です」 (ja/tr/en). Demo planlar `placeholder: false`.
- 特商法 販売価格 satırı gerçek fiyatlarla; 税込 gösterim sorusu (Q-12) açık olduğundan 「要確認」 işareti duruyor. `check:legal`'e fiyat/「仮」 kontrolü eklendi. docs/API.md güncellendi.
- Kapı: pytest 430 geçti (rebase sonrası), `next build` + check:legal/tax/team yeşil. Tanıtım sayfası henüz yok (T-044 fiyatları `PLANS`'tan alacak).
- Sonraki: T-058 (review-fix, XFF hız sınırı), sonra T-011 (R2 depolama, P0).

## 2026-11-07 17:44 JST · reviewer · 732e831..7332dab incelemesi (T-041b, T-021, T-048, T-047/b/c, T-045, T-048b)
- Kapı başta yeşil (425, SQLite). Vergi oranı/eşik değişikliği yok; render.yaml değişmedi; SecurityHeaders en dışta, CORS PATCH/DELETE düzeltmesi doğru. T-045 PDF `current_user` arkasında, 控除 所得'i aşmıyor.
- **Hata düzeltmesi (T-047c):** `i18n.parse_lang_command` 「Dil kursu 2000」「Language school 30000」 gibi kayıtları dil komutu sanıp seçenek gösteriyor, kaydı yutuyordu. Bilinmeyen değer artık yalnızca 「:」 ile yazılırsa (「dil: klingon」) komut sayılır.
- Yeni testler (+5): dil kelimesiyle başlayan kayıt (düzeltmesiz başarısız olduğu doğrulandı), hızlı yanıt ↔ normalize gidiş-dönüş, PDF 赤字年 控除 0, 控除 = min(選択, 所得), PDF kullanıcı ayrımı. Toplam 430 yeşil.
- Açılan: **T-058 (review-fix, P1)** hız sınırı XFF ilk değeri sahtelenebilir → login sınırı atlatılabilir. T-049'a not: blue-return.pdf 2027+ için 55万 kabul ediyor, dipnot yıla göre değil.
- dashboard-next bu çalışmada değişmedi (build gerekmedi).

## 2026-11-07 16:43 JST · developer · T-048b CORS + güvenlik başlıkları
- Yeni `bot/security.py`: `CORS_ORIGINS` boş/`*` → yalnızca `PANEL_URL` origin'i + `http://localhost:3000` (render.yaml'daki `"*"` değiştirilmedi, kodda daraltıldı); açık liste verilirse aynen kullanılır.
- Tüm yanıtlara nosniff, Referrer-Policy, HSTS (1 yıl), X-Frame-Options DENY, CSP `frame-ancestors 'none'` (ASGI middleware, en dışta).
- Bulunan hata: CORS `allow_methods` yalnızca GET/POST/PUT idi → panelin PATCH/DELETE istekleri (kayıt düzenle/sil, token iptali, ekip) ön kontrolde reddediliyordu; düzeltildi.
- Kapı: pytest 425 geçti (yeni 18). dashboard-next değişmedi. Q-05'e not: `PANEL_URL` gerçek panel adresi olmalı.
- Sonraki: T-046 (tüm veri dışa aktarma).

## 2026-11-07 · developer (oturum) · T-045 青色申告決算書 PDF
- `bot/reports.py`: 損益計算書 転記用 PDF (2 sayfa: ①〜㊺ satırları + aylık satış/gider). Sabit kalemler form sırasıyla, diğer kalemler ㉕〜㉚ boş satırlara (büyükten küçüğe), taşan → 雑費. "参考資料" uyarısı basılı.
- `GET /api/v1/reports/blue-return.pdf?year=&blue=` (blue ∈ 0/10万/55万/65万). Panel 税務 sayfasında 「決算書PDF」 düğmesi.
- 5 yeni test (pypdf==5.1.0 dev bağımlılığı, yalnızca test). Toplam 407 yeşil, `next build` yeşil.

## 2026-11-07 · developer (oturum) · T-047b sayfa metinleri
- Hook gerektirmeyen `T()` (lib/i18n.ts; LangProvider dil değişince ağacı yeniden kurar). Tüm sayfalar (ホーム, 請求書, 経費, 銀行, 税務, 料金, メンバー, login/signup/reset/join/connect) `T()` ile sarıldı; ~430 metin `lib/locales/tr.json` + `en.json`.
- Veri (勘定科目, mağaza/şirket adları, API'ye giden metin) çevrilmez. Grafik ekseni tr/en'de "M" birimi.
- `next build` yeşil; 8 sayfa tr ekran görüntüsüyle kontrol edildi, konsol hatası yok.

## 2026-11-07 · developer (oturum) · T-047c bot dili
- `bot/i18n.py`: Japonca çekirdek yanıtı parça bazında tr/en'e çevirir; yerel komutlar (Toplam/Geri al/Total/Undo…) Japonca komuta normalize edilir. Veri ve 勘定科目 Japonca kalır.
- Komut: 「言語」/「dil」/「language」 → seçenekler; 「Türkçe」/「English」/「日本語」/「言語:tr」 → ayarla. Yeni tablo `user_prefs(user_id, lang)`.
- LINE kamera düğmesi ve WhatsApp filtreleri değişmedi (gönderilen metin `📷 レシート` kalır). 7 yeni test, toplam 402 yeşil.

## 2026-11-07 · developer (oturum) · T-047 dilim 1
- `app/lib/i18n.ts` (Japonca metinle anahtarlı ja/tr/en sözlük, `{x}` yer tutucu) + `components/lang.tsx` (LangProvider, useT, LangSwitcher; localStorage `jsaas.lang`, `<html lang>`).
- Üst çubukta dil seçici; 設定'de "表示言語" kartı. Kabuk (menü, üst çubuk, arama, mod rozeti, sayfa başlık/alt başlıkları) ve 設定 tamamen çevrildi; `Card` başlıkları tüm sayfalarda çevriliyor (tr/en'de Japonca başlık küçük etiket).
- Kalan: T-047b (sayfa gövdeleri), T-047c (bot). `next build` yeşil, tr ekran görüntüsüyle kontrol edildi.

## 2026-11-07 15:20 JST · developer · T-048 hız sınırı
- Yeni `bot/ratelimit.py`: (kural, IP) başına bellek içi kayan pencere; login 10/dk, signup 5/dk, password-reset/request 5/dk, `/receipts/ocr` 20/dk → 429 + `Retry-After` + 「リクエストが多すぎます…」. Reddedilen istek pencereye sayılmaz; anahtar sayısı 20.000 ile sınırlı (süresi dolanlar temizlenir).
- IP: `X-Forwarded-For` ilk değeri (görev tanımı). Not (reviewer): istemci kendi XFF'ini gönderip vekil sonuna eklerse ilk değer sahtelenebilir → `RATE_LIMIT_PROXY_HOPS=1` sağdan değeri kullanır; Render'ın XFF davranışı doğrulanınca varsayılan değiştirilebilir. Sınırlar `RATE_LIMIT_<KURAL>` ile ayarlanır (render.yaml değişmedi, kod varsayılanı).
- `/callback`, `/` ve diğer uçlar etkilenmez; `conftest` her testte sayaçları sıfırlar. docs/API.md'ye not.
- Kapı: pytest 395 geçti (yeni `tests/test_ratelimit.py` 10: N geçer/N+1 429, pencere sonrası 401'e dönüş (saat monkeypatch), IP ve kural bağımsızlığı, env override/kapatma, proxy hops, bellek sınırı). dashboard-next değişmedi.
- Sonraki: T-048b (CORS + güvenlik başlıkları).

## 2026-11-07 14:44 JST · developer · T-021 CI panel işi
- `.github/workflows/ci.yml` `dashboard` işi: Node 20 → 22 (`--experimental-strip-types` için 22.6+ gerekli), `next build` sonrası adlandırılmış 3 adım: `npm run check:tax`, `check:legal` (build çıktısı `out/legal/*` HTML'ini de denetler), `check:team`. Diğer işler değişmedi.
- Yerel kapı (Node 22.23): `npm ci && next build` geçti, 3 kontrol OK (check:tax honsoku=1419500 …). pytest 385 geçti (bot değişmedi). YAML ayrıştırıldı.
- CI #61 (ea86f92) yeşil: bot, bot-postgres, docker, dashboard; dashboard işinde check:tax / check:legal / check:team adımları görünüyor ve geçti.
- Sonraki: P1 T-048 (hız sınırı) → T-048b.

## 2026-11-07 14:16 JST · planner · haftalık planlama
- ROADMAP: Faz 1 kod tarafı, Faz 2'nin biten maddeleri, Faz 4 WhatsApp/banka CSV ve Faz 5 P0 (T-040–T-043, T-025) ✅ işaretlendi. Blocked/terk edilmiş görev yok; CI #58 yeşil.
- BACKLOG: T-044→T-044/T-044b, T-045→T-045/T-045b, T-046→T-046/b/c, T-048→T-048/T-048b bölündü; T-010/12b/19/24/26/33/34/35/47'ye kabul ölçütü eklendi; önerilen sıra tablonun üstünde. T-021 P2→P1 (panel kontrolleri CI'da yok), T-011 P2→P1.
- Yeni risk: `process_image` görselleri konteyner diskine yazıyor, Render'da disk yok → her deploy'da siliniyor. Q-14 (R2/S3 kararı) açıldı.
- Yeni cevaplanmış soru yok (Q-03 zaten T-004b'ye yansımıştı). `tasks/WEEKLY.md` oluşturuldu. Kod değişmedi.

## 2026-11-07 13:48 JST · developer · T-041b ekip paneli
- `dashboard-next`: 設定 「メンバー」 kartı (owner: 招待コード発行 → kod + `/join/#iv_…` bağlantısı yalnızca bir kez, 未使用の招待 取消, 役割変更 select, 2 adımlı 削除; accountant/viewer: rolü + açıklama). Demo modunda statik veri.
- Yeni `/join` sayfası: hash'teki kod adres çubuğundan silinir; hesapsız/LINE-only oturumda kod sekmede (sessionStorage) tutulur → giriş/kayıt sonrası otomatik dolu. Katılım/defter değişiminde eski token sunucuda iptal edilir (token sınırı dolmasın).
- Üst menü: `/team/ledgers` defter seçici + 「招待コードで帳簿に参加」; profil satırında rol etiketi. `useShell()` artık `role` + `canEdit` verir; rol `/auth/me` ile "live"dan önce çözülür (viewer'a düğme bir an bile görünmez). Viewer'da tüm yazma düğmeleri gizli + 「閲覧専用」; 料金プラン değişikliği yalnızca owner (sunucu 403 ile zaten koruyor).
- Kapı: `npm ci && next build` geçti (yeni `/join` rotası), `npm run check:team` OK, Playwright duman testi (sahte API: viewer/owner/ seçici/join) hatasız. pytest 385 geçti (bot değişmedi). `check:team` CI'a T-021 ile (Node 22).
- Sonraki: P1 T-044 (LP + kurulum sihirbazı) veya T-048 (güvenlik).

## 2026-11-07 13:43 JST · reviewer · f424677..0b4b6e9 incelemesi (T-054, T-025, T-041)
- Kapı başta yeşil (380, SQLite). T-054 `COUNT(DISTINCT image_path|id)` doğru, sınır OCR öncesi. T-041 yazma uçlarının hepsi `writer_user`/`owner_user` arkasında; vergi kuralı değişikliği yok, render.yaml değişmedi.
- **Güvenlik düzeltmesi (T-041):** `accounts.link_ledger` her token'ı 「パネル」 kodu sayıyordu → LINE-only defterin viewer'ı kendi üye token'ını `/auth/link-line`'a verip defterin **sahibi** olabiliyordu. Artık yalnızca `account_id=0` token kabul edilir (üye token'ı → 400).
- **Düzeltme (T-025):** yavaş OCR yolunda 「読み取り中」 reply ağ hatası verirse istisna yükseliyor, OCR sonucu push edilmiyordu; reply try/except'e alındı, sonuç yine push edilir.
- **Yeni testler** `tests/test_review_team.py` (5): üye token'ı bağlama kodu olamaz (eski kodda kırmızı), gerçek パネル kodu bağlar, LINE-only sahip üye yönetimi + viewer 403, yabancı deftere switch 403, reply hatasında push (eski kodda kırmızı). Kapı: 385 geçti.
- Açılan review-fix yok.

## 2026-11-07 12:45 JST · developer · T-041 ekip üyeleri (API dilimi)
- `bot/team.py`: roller owner / accountant / viewer. Sahip = `account_ledgers` hesabı veya `account_id=0` token (LINE 「パネル」, admin; eski token'lar owner kalır). Davet: tek kullanımlık `iv_…` (7 gün, hash'li saklanır, koşullu UPDATE ile yarışta tek kullanım), açık davet ≤10, üye ≤20.
- Yeni ekleyici şema: `ledger_members`, `team_invites`, `api_tokens.account_id` (yıkıcı migration yok). Rol her istekte `ledger_members`'tan çözülür → rol değişimi/çıkarma eski token'lara hemen yansır. Token sınırı (5) (defter, hesap) başına.
- `api.py`: `writer_user` tüm muhasebe yazma uçlarında (viewer 403), `owner_user` abonelik + `/auth/link-line` (üyenin sahibin defterini yeniden bağlaması engellendi) + `/team/*`. Yeni uçlar: `/team/invites|members|join|ledgers|switch`. `/auth/me` + `role` (eski testte beklenti buna göre güncellendi). Parola sıfırlama üyenin diğer defterlerdeki oturumlarını da kapatır; üyesi olan web defteri LINE'a bağlanamaz (409).
- Testler: yeni `tests/test_team.py` (21). Kapı: pytest 380 geçti (SQLite); yerel PostgreSQL 16'da 378 geçti + 2 atlandı. dashboard-next değişmedi.
- Sonraki: T-041b (panel: üye yönetimi, /join, defter seçici) veya P1 T-048 (güvenlik).

## 2026-11-07 11:44 JST · developer · T-025 LINE OCR uzun sürerse 「読み取り中…」 + push
- `app.handle_image`: görsel alma + OCR + kayıt tek görev; `LINE_REPLY_WAIT_SEC` (varsayılan 8 sn, 0–50 arası sınırlanır) içinde biterse sonuç reply ile (push kotası harcanmaz). Bitmezse önce 「レシートを読み取り中です…」 reply, görev iptal edilmeden (shield) tamamlanır, sonuç hızlı yanıt butonlarıyla `push` (`/v2/bot/message/push`) ile gider.
- Push yolunda OCR/DB hatası → 「画像を読み取れませんでした…」 push; push ağ hatası yutulur (log). Hızlı yolda beklenmedik hata → aynı metin reply. `/callback` ve metin akışı değişmedi; render.yaml değişmedi (kod varsayılanı).
- Yeni `tests/test_line_image_async.py` (14: hızlı → yalnız reply, yavaş → 読み取り中 + push + tek kayıt, yavaş hata/beklenmedik hata push, push hatası, get_image hatası, bekleme süresi sınırları, push isteği gövdesi/5 mesaj kesmesi). Kapı: pytest 359 geçti (SQLite); webhook/OCR/T-025 testleri yerel PostgreSQL 16'da 30 geçti. dashboard-next değişmedi.
- Not (Q-01'e eklendi): push mesajları LINE aylık mesaj kotasına sayılır; reply sayılmaz.
- Sonraki: P1 T-041 (ekip üyeleri) veya T-044/T-048.

## 2026-11-07 11:10 JST · developer · T-054 çok oranlı fiş kotası (review-fix)
- Yorum (ürün kararı gerekmedi): Q-11 planı 「ayda 30 fiş」 → kota fiş başına. `billing.usage` 経費 sayımı `COUNT(DISTINCT image_path | 'id:'+id)`: 税率ごとに分割された tek fiş 1 件, görselsiz (metin/web) kayıt satır başına. Şema değişmedi.
- Sonuç: 29/30 kullanımda 8%+10% fiş kabul edilir → kullanım 30 (31 satır); sonraki fiş OCR öncesi, metin girişi de reddedilir. Panel kullanım çubuğu `status()` ile aynı sayıyı gösterir.
- Yeni `tests/test_receipt_quota_split.py` (4; 3'ü eski kodda kırmızı). Kapı: pytest 345 geçti (SQLite); billing/limit testleri yerel PostgreSQL 16'da 31 geçti. dashboard-next değişmedi.
- Sonraki: P1 T-025 (LINE OCR uzun sürerse önce 「読み取り中…」 + push).

## 2026-11-07 10:05 JST · reviewer · 6012a33..8c1a4f6 incelemesi (T-042b, T-052, T-053, T-043)
- Kapı başta yeşil (297, SQLite). T-052 koşullu UPDATE + ekleyici sütun (yıkıcı migration yok), T-053 409 yalnızca e-posta gerçekten kayıtlıysa, T-042b sınır OCR öncesi — doğru. Vergi kuralı değişikliği yok; render.yaml yalnızca `sync: false` değişken ekledi.
- **Düzeltme:** T-043 プライバシーポリシー 「レシート画像…画像そのものは保存しません」 yanlıştı — `process_image` görseli `receipts/` altına yazıp kayda `image_path` bağlıyor. Metin 「…取引データと紐づけてサーバーに保存します」 olarak düzeltildi (`dashboard-next/app/lib/legal.ts`).
- **Yeni testler** `tests/test_review_limits_privacy.py` (4): PANEL_URL sonda `/` → tek eğik çizgi, geçen ayın kayıtları sınırı tetiklemez, sınır defter bazında, fiş görseli diske yazılır + `image_path` güvenli (politikadaki ifadeyi sabitler).
- **Açılan:** T-054 (P2) çok oranlı fiş 29/30 kullanımda 31 kayda çıkıyor ve tek fiş 2 kota sayılıyor.

## 2026-11-07 10:00 JST · developer · T-004b 基礎控除 令和8・9年分
- `bot/tax/income.py`: `BASIC_DEDUCTION[2026]`=`[2027]` (TAX_RULES §2 ✅, Q-03): ≤489万 104万 · ≤655万 67万 · ≤2,350万 62万 · ≤2,400万 48万 · ≤2,450万 32万 · ≤2,500万 16万 · 超 0. 2024 ve 2028+ hâlâ `NotImplementedError` (2028 ⚠️).
- `/api/v1/tax/income?year=2026|2027` artık 200; 2028 → 409. Kabul örneği: 2026年分 事業所得 3,000,000 → 基礎控除 1,040,000, 課税 1,960,000, 申告納税額 100,500 (API + panel `estimateIncomeTax` aynı).
- Panel: `app/lib/income.ts` yıl→tablo haritası (`BASIC_DEDUCTION`), `year !== 2025` koruması kalktı; hesaplanamayan yıl mesajı 「対応: 2025〜2027年分」. Yıl seçici zaten vardı.
- Testler: her kademe sınırında ±1 yen (2026 ve 2027), 2024/2028 reddi, 2026 tam örnek, API 2026/2027/2028; yeni `test_income_card_parity.py` (income.ts tablosu = Python tablosu); `check:tax`'a 所得税 örnekleri. Kapı: pytest 337 geçti; `check:tax`, `check:legal`, `next build` geçti.
- Sonraki: P1 T-025 (LINE OCR uzun sürerse önce 「読み取り中…」 + push).

## 2026-11-07 09:00 JST · developer · T-043 yasal sayfalar
- Panelde `/legal/terms/` (利用規約: 税理士法 — vergi danışmanlığı değil, OCR/hesap sonuçları referans, veri sahipliği, 民法548条の4 değişiklik), `/legal/privacy/` (APPI: 取得情報, 利用目的, 27条 第三者提供, 委託先 + 外国 (Render/Singapur, Stripe, LINEヤフー, Meta, Anthropic), 開示等 32〜35条), `/legal/tokushoho/` (zorunlu 11 madde tablosu). Her sayfada 「本ページは確認中のドラフトです」 bandı.
- İçerik `app/lib/legal.ts`'de; satıcı bilgileri derleme zamanı `NEXT_PUBLIC_LEGAL_*` (render.yaml jsaas-panel, `sync: false`), boşsa 「要確認」. Hukuki onay gereken maddeler 「要確認」 rozetli; saklama süresi TAX_RULES'ta ⚠️ olduğundan sayı yazılmadı. Q-12'ye değer listesi + avukat kontrol maddeleri eklendi.
- Bağlantılar: kayıt formuna 同意文, giriş/kayıt/sıfırlama kartları altına, kenar menü altına, 料金プラン'a (特商法・規約).
- Yeni `npm run check:legal` (şablon: 要確認 yedeği, 特商法 zorunlu maddeler, boş blok/başlık tekrarı yok; `out/legal/*` HTML'de ドラフト bandı + maddeler). Kapı: pytest 297 geçti; `next build` geçti; env ile derlemede satıcı adı HTML'e girdi; Playwright ile masaüstü + 375px (yatay taşma yok) kontrolü.
- Sonraki: P0 bitti → P1 (T-004b 基礎控除 2026/2027, sonra T-025 / T-041 …).

## 2026-11-07 07:45 JST · developer · T-053 kayıt yarışında 500 (review-fix)
- `store.is_integrity_error(exc)`: sqlite3.IntegrityError ve psycopg.IntegrityError (UniqueViolation dahil) tanır; psycopg yoksa güvenle False.
- `accounts.signup`: işlem bloğu bütünlük hatası verirse (SELECT–INSERT arası rakip kayıt) ve e-posta artık kayıtlıysa `AccountError(…, 409)` 「このメールアドレスはすでに登録されています。」; e-posta kayıtlı değilse hata gizlenmez, aynen yükselir. tx rollback → yarım hesap/defter yok.
- Yeni `tests/test_signup_race.py` (4; ön kontrolü atlayan monkeypatch ile API 409 + tek hesap/tek defter + ilk hesap giriş yapabilir, doğrudan çağrıda 409, maskelenmeyen başka bütünlük hatası, sürücü tanıma). 3'ü eski kodda kırmızı. Kapı: pytest 297 geçti (SQLite); hesap testleri yerel PostgreSQL 16'da 19 geçti. dashboard-next değişmedi.
- Not: kod commit'i (c5108d7) BACKLOG/LOG'suz gitti (güncelleme betiği hata verdi); bu kayıt ayrı commit'te.
- Sonraki: P0 T-043 (yasal sayfalar, Q-12 yer tutucu ile).

## 2026-11-07 06:44 JST · developer · T-052 Stripe webhook olay sırası (review-fix)
- `subscriptions`'a ekleyici sütun `last_event_created` (unix sn). `store.ADDED_COLUMNS` + `_add_columns`: mevcut veritabanlarına `init_db` sırasında eklenir (SQLite `PRAGMA table_info` kontrolü, PG `ADD COLUMN IF NOT EXISTS`); veri korunur, yıkıcı migration yok.
- `billing._upsert(event_created=…)`: karşılaştırma + yazma tek koşullu UPDATE (`WHERE last_event_created<=?`) → eski olay `ignored`, eşit/yeni uygulanır; eşzamanlı teslimde de eski olay kazanamaz. `checkout.session.completed` ve `customer.subscription.*` aynı kurala tabi; `cancel()` API yanıtı zamanı değiştirmez. Eksik/bozuk `created` → 0.
- Yeni `tests/test_billing_event_order.py` (14; deleted(200)→updated(100) free kalır, 199/200/201 sınırı, geç checkout, eski DB taşıma). 12'si eski kodda kırmızı. Kapı: pytest 293 geçti (SQLite) / 292+1 skip (yerel PostgreSQL 16); PG'de eski tabloya sütun ekleme elle doğrulandı. dashboard-next değişmedi.
- Sonraki: T-053 (review-fix, kayıt yarışında 500), ardından P0 T-043.

## 2026-11-07 05:50 JST · developer · T-042b abonelik paneli + kanal sınırları
- Yeni panel sayfası `/billing` (料金プラン): mevcut plan + durum/yenileme tarihi, bu ayki kullanım çubukları (経費 x/30, 請求書 x/3; %80 sarı, dolunca kırmızı), plan kartları (yer tutucu fiyat 「仮」), 「アップグレード」 → Checkout `url`, 「解約（期間末）」 onaylı; ödeme kapalıyken 「準備中」 bandı ve butonları. `?billing=success|cancel` bandı; demo modunda statik. Menüye 料金プラン, `/settings`'e bağlantı kartı.
- LINE/WhatsApp: `app.limit_notice` — sınır aşıldıysa 経費 kaydedilmez, Japonca uyarı + `{PANEL_URL}/billing/` (yoksa 「パネル」 yönlendirmesi). Fiş görselinde OCR'dan önce kontrol (görsel işlenmez/saklanmaz). 入金 ve komutlar (合計/取消) etkilenmez. Checkout `success_url`/`cancel_url` → `/billing/`.
- Yeni `tests/test_channel_limits.py` (9; 30/31 sınırı, ödeme kapalı, `BILLING_ENFORCE_LIMITS=0`, ücretli plan, görsel OCR öncesi, WhatsApp). Kapı: rebase sonrası pytest 279 geçti (SQLite + yerel PostgreSQL 16); `next build` geçti; Playwright ile demo + canlı (31/30 kullanım, success bandı) ekran kontrolü.
- Sonraki: P0 T-043 (yasal sayfalar).

## 2026-11-07 05:45 JST · reviewer · 1709d00..37ed9ee incelemesi (T-040, T-051, T-040b, T-042)
- Kapı başta yeşil (255, SQLite); T-051 eski parmak izi mantığı, T-040b `nextPath` (açık yönlendirme yok), T-042 sınır 30/31·3/4 ve imza doğrulaması doğru. Vergi kuralı değişikliği yok.
- **Düzeltmeler:** (1) `accounts.send_mail` sağlayıcı yokken sıfırlama bağlantısını INFO log'a ve tam e-postayı WARNING'e yazıyordu → gövde DEBUG, adres `t***@…` maskeli. (2) Parola sıfırlanınca hesabın diğer kullanılmamış `rs_` bağlantıları da geçersiz. (3) `link_ledger`: web defterinde abonelik varsa 409 (ücretli plan sahipsiz kalıyordu). (4) `billing.handle_event`: işleme hata verirse olay kaydı geri alınır → Stripe yeniden denemesi `duplicate` sayılmaz.
- **Yeni testler** `tests/test_review_auth_billing.py` (15): yukarıdakiler (5'i eski kodda kırmızı), abonelik durum sınırları (active/trialing/past_due ↔ unpaid/canceled/incomplete*), bilinmeyen price, e-posta büyük/küçük harf.
- **Açılan:** T-052 (P1) webhook olay sırası, T-053 (P2) kayıt yarışında 500.
- Kapı: pytest 270 geçti (SQLite + yerel PostgreSQL 16); dashboard-next değişmedi.

## 2026-11-07 04:46 JST · developer · T-042 abonelik (API dilimi)
- Yeni `bot/billing.py`: planlar (free 30 経費/3 請求書 aylık, personal/business sınırsız; fiyatlar yer tutucu Q-11), aylık kullanım (JST, `created_at`; BANK/INVOICE/DEMO kaynakları fiş sayılmaz), `check_limit` → 402 Japonca. Sınırlar yalnızca `STRIPE_SECRET_KEY` varken ve `BILLING_ENFORCE_LIMITS≠0` uygulanır (yükseltme yolu yokken kimse engellenmez).
- Stripe REST (httpx, SDK yok): Checkout oturumu (abonelik, `client_reference_id`=defter), dönem sonu iptal, webhook `Stripe-Signature` HMAC (300 sn), olay kimliğiyle idempotent; `checkout.session.completed` + `customer.subscription.*` işlenir. Anahtar yoksa ödeme uçları 503.
- Tablolar `subscriptions`, `billing_events` (ekleyici). render.yaml'a 4 `STRIPE_*` değişkeni `sync: false`; Q-10'a değer girilmesi notu, Q-11'e mevcut kullanıcılara geçiş süresi sorusu.
- Yeni `tests/test_billing.py` (18; sınır 30/31 ve 3/4, imza tolerans sınırı, httpx MockTransport ile gerçek form kodlaması — bir `data=` hatasını yakaladı). Kapı: pytest 255 geçti (SQLite + yerel PostgreSQL 16).
- Sonraki: T-042b (panel /billing + LINE/WhatsApp sınırı), ardından T-043.

## 2026-11-07 03:40 JST · developer · T-040b panel hesap sayfaları
- Yeni `/signup` (e-posta + parola×2, ≥10 文字 istemci kontrolü → `/connect/?welcome=1`), `/login` (`?next=` yalnız site içi yol), `/reset` (hash `rs_…` → yeni parola formu, token adres çubuğundan silinir; yoksa e-posta isteği, her zaman aynı mesaj). Ortak `components/auth.tsx`; hata metni API `detail`'inden, ağ hatasında 「デモデータで見る」 yönlendirmesi.
- `/connect`: hesapla oturum açıksa (`/auth/me`) kod hash'ten gelse bile onay butonuyla `POST /auth/link-line` (409 mesajı gösterilir); hesapsızsa eski davranış (kod = token, otomatik). Token saklama aynı `jsaas.token`.
- Üst satır: hesap oturumunda e-posta + ログアウト (`DELETE /tokens/current` → /login); yalnızca LINE kodu oturumunda eski 切断 (yalnız yerel) + 「アカウント連携」; demo modunda ログイン / 新規登録 / LINEで接続.
- Doğrulama: `next build` geçti; pytest 237 geçti. Yerel API (uvicorn + demo-seed) + statik `out/` ile Playwright: kayıt (kısa parola hatası) → hash kodla bağlama → ダッシュボード ライブ + e-posta → ログアウト → yanlış/doğru parola → sıfırlama isteği → `rs_` ile parola değişimi, ikinci kullanım reddi → ikinci hesapla aynı LINE defteri 409. Betik CI'a T-035 ile.
- Sonraki: P0 T-042 (abonelik, Stripe test modu), ardından T-043.

## 2026-11-07 02:44 JST · developer · T-051 banka CSV çoklu 摘要 sütunu
- `bank_csv.parse`: başlıktaki tüm 摘要 sütunları (摘要/摘要内容/備考/取引区分 …) soldan sağa boşlukla birleşir, boş hücreler atlanır (「口座振替 ﾗｸﾃﾝﾓﾊﾞｲﾙ」). Tutar/入出金 kalıbına da uyan sütunlar 摘要 sayılmaz; 200 karakter sınırı store'da korunuyor.
- Geriye uyum: birleşik metin ilk sütundan farklıysa satırda `legacy_description`; `store.insert_bank_rows` eski parmak izini (eski biçimin aynı gün sayacıyla) da arar → T-051 öncesi alınmış dosya yeniden yüklenince yinelenme 3/3 doğru, yeni kayıt yok.
- Yeni `tests/test_bank_multi_desc.py` (7; eski parmak izi testi kontrolsüz kodda kırmızı), `test_bank_csv_parse_variants` beklentisi güncellendi. Kapı: pytest 237 geçti (SQLite + yerel PostgreSQL 16).
- Sonraki: P0 T-040b (panel hesap sayfaları), ardından T-042, T-043.

## 2026-11-07 01:48 JST · developer · T-040 hesap sistemi (API dilimi)
- Yeni `bot/accounts.py`: scrypt (stdlib, 16 bayt tuz) parola, ≥10/≤128 karakter; tablolar `accounts`, `account_ledgers` (hesap ↔ tek defter), `password_resets` (yalnızca ekleyici, store.SCHEMA).
- `/api/v1/auth/signup|login|me|link-line|password-reset/request|confirm`. Kayıt boş `web:…` defteri açar, oturum = mevcut `api_tokens` → tüm uçlar aynen çalışır. LINE 「パネル」 koduyla bağlama: web defterinde veri varsa / LINE defteri başka hesaptaysa 409 (veri birleştirme yok), kod ve eski token'lar iptal. Sıfırlama 1 saat, tek kullanım, tüm oturumları kapatır; e-posta keşfi yok.
- `MAIL_PROVIDER`/`MAIL_API_KEY` render.yaml'a `sync: false` eklendi (Q-13'e not); sağlayıcı yokken e-posta log'a.
- Yeni `tests/test_accounts.py` (15). Kapı: rebase sonrası pytest 230 geçti (SQLite + yerel PostgreSQL 16).
- Sonraki: T-040b (panel /signup /login /reset /connect), ardından T-042, T-043.

## 2026-11-07 01:45 JST · reviewer · 5f49a70..58cca61 incelemesi (T-027, panel menüleri, T-028, T-029, T-029b, tax-watcher)
- Kapı başta yeşil (189, SQLite); dashboard-next `next build` geçti. T-027 sayfalama, T-028 başlık+compare_digest, T-029/T-029b int4 sınırları doğru; LINE düzenleme yolu tutar değiştirmiyor (taşma riski yok). TAX_RULES değişiklikleri kaynaklı + tarihli.
- **Düzeltme:** `store.delete_entry` banka kaynaklı 経費 silinince `bank_tx.entry_id` asılı kalıyordu → hareket bir daha kaydedilemiyordu (409). Artık bağ kaldırılıyor. `PATCH /entries/{id}` boş gövdede `null`/200 yerine 400.
- **Yeni testler** `tests/test_review_bank.py` (26): bank_csv tarih (和暦/年月日/geçersiz) ve tutar (△▲¥円) biçimleri, alt bilgi/0/boş satır atlama, başlık 15 satır sınırı, kısa satır; 消込 önerisi (fatura tarihinden önceki giriş yok, bir fatura tek öneri), tutar uyuşmazlığı 400, silme↔banka bağı, başka kullanıcının kaydı 404. Silme testi eski kodda kırmızı.
- **Açılan:** T-051 (P2 review-fix) banka CSV'de birden çok 摘要 sütunu → karşı taraf adı kayboluyor.
- Kapı: pytest 215 geçti (SQLite + yerel PostgreSQL 16).

## 2026-11-07 00:40 JST · developer · T-029b kayıt tutarı int4 taşması
- Seçenek (a): şema değişmeden `store.MAX_ENTRY_AMOUNT = 2,000,000,000` (< 2^31−1). 1e9 seçilmedi çünkü ödenen en büyük fatura 税込 ~1.1e9 → 売上 kaydı reddedilirdi.
- `store.check_amount` → `add_entry`/`update_entry` merkezi kontrol (`AmountOutOfRange`). API `EntryIn`/`EntryPatch` `lt=MAX_ENTRY_AMOUNT` (422, mevcut doğrulama kuralıyla aynı), `/bank/{id}/entry` büyük çekimde 400; LINE/WhatsApp metin ve fiş yolu 「金額が大きすぎます。1件20億円未満で入力してください。」 yanıtı, kayıt yok.
- Not: api.py'de `EntryIn.store` alanı `store` modülünü sınıf gövdesinde gölgeliyor → sabit modül düzeyinde içe aktarıldı.
- Yeni `tests/test_entry_limits.py` (7). Kapı: pytest 189 geçti (SQLite + yerel PostgreSQL 16).
- Sonraki: P0 T-040 (hesap sistemi).

## 2026-11-06 23:58 JST · tax-watcher · haftalık vergi kuralı kontrolü
- **Q-03 kapandı (✅):** 令和8・9年分 基礎控除 = ≤489万 104万 · ≤655万 67万 · ≤2,350万 62万 (2,350万超 değişmedi); 104万 tüm ≤2,350万 için değil. Kaynak: NTA 令和8年分 年末調整のしかた, 財務省 大綱, NTA No.1199. T-004b → todo. 令和10年分以後 ⚠️ (yalnızca ≤132万 99万 kesin).
- **Yeni kural:** 青色申告特別控除 令和9年分以後 75万/65万/10万 (書面55万 kalkar, 簡易簿記 前々年収入>1,000万 → 0) → T-049 (P1).
- ✅'a çekilen: 簡易課税 みなし仕入率 (No.6505; kodla aynı → T-017 yalnızca test), 3割特例 şartları, 経過措置 tablosu + 1億円/10億円 sınırı (NTA Q&A), 電帳法 電子取引 検索要件/猶予措置. Kod 1億 sınırını ve 2割/3割 uygunluk şartlarını kontrol etmiyor → T-050 (P2).
- Takvim (60 gün) yenilendi: 11/10, 11/30 予定納税 第2期, 12/1 改正施行, 12/10; yakın: 2027-01-12 年末調整分 源泉, 01-20 納期の特例. Kod değişmedi; kapı: bot pytest.

## 2026-11-06 23:20 JST · developer · T-029 fatura kalemi tutar sınırları
- `invoices.validate_items`: qty ≤ 1,000,000; unit_price, satır tutarı ve 税抜合計 < 1e9 円; en fazla 200 kalem → aşımda ValueError → API 400.
- Not: inceleyicinin önerdiği 1e11 PostgreSQL'de yetmiyor — `invoices.subtotal*/tax*/total` INTEGER (int4); 1e11-1 fatura yerel PG 16'da hâlâ 500 verdi. 1e9 ile total ≤ 1.1e9 < 2^31, şema değişikliği yok.
- Yeni `tests/test_invoice_limits.py` (13): her sınırın iki yanı, 10%/8% karışık en büyük fatura, API'de 400. Kapı: pytest 182 geçti (SQLite + yerel PostgreSQL 16).
- Aynı int4 sorunu `entries.amount`'ta da var (API 1e11 kabul ediyor, 3e9 → 500) → T-029b (review-fix) açıldı.
- Sonraki: T-029b, ardından P0 T-040.

## 2026-11-06 22:40 JST · developer · T-028 /admin/richmenu anahtarı başlığa taşındı
- `admin_richmenu` artık `X-Admin-Key` başlığını okuyor; `?key=` geriye uyum için kabul ediliyor ama log'a "deprecated" uyarısı yazıyor; başlık varsa sorgu yok sayılıyor. ADMIN_KEY boşsa her zaman 403.
- Belgeler: README, `setup_richmenu.py` docstring, QUESTIONS Q-01 komutu başlıklı curl'e güncellendi.
- Yeni `tests/test_admin_richmenu.py` (5, LINE çağrısı sahte modülle): başlıkla 200, yanlış/eksik 403, sorgu hâlâ 200, başlık önceliği, ADMIN_KEY yok → 403. Kapı: pytest 169 geçti (SQLite).
- Sonraki: T-029 (fatura kalemi üst sınırları, review-fix), ardından P0 T-040.

## 2026-11-06 21:30 JST · kurulum (Claude) · T-015, T-020, T-030–T-032 panel menüleri
- Panel artık sayfa yönlendirmeli: ortak kabuk `components/shell.tsx` (menü, arama, bağlantı/demo modu), ortak UI `components/ui.tsx`, demo veri `lib/demo.ts`.
- 請求書管理 (çok kalemli 適格請求書, 消込, PDF), 経費精算 (fiş OCR önizleme→onay, elle giriş, 電帳法 arama, satır içi düzenleme/silme), 銀行連携 (CSV içe aktarma Shift_JIS/UTF-8, tekrar korumalı, otomatik 消込 önerisi, çekimi gidere çevirme), 確定申告/税務 (損益, 所得税, 消費税 yöntemleri, freee/MF/弥生 CSV, takvim), 設定 (事業者情報 + 登録番号 kontrol hanesi, kanal durumu, bağlantı).
- API: PATCH/DELETE /entries/{id}, POST /receipts/ocr, /bank/import|transactions|match|{id}/entry, /channels. Testler: 164 (SQLite). Uçtan uca: yerel API + panel, tüm menüler canlı ve demo modda, 1366/390 px.

## 2026-11-06 15:10 JST · developer · T-027 yıllık toplamlarda 5000 satır kesmesi
- `store.entries_in_range()`: (d, id) anahtar kümesiyle sayfalı tam okuma (sayfa 2000). `/tax/consumption`, `/pl`, `/export.csv` ve `/entries/{user_id}` artık `limit=5000` yerine bunu kullanıyor; `search_entries` (電帳法 arama) değişmedi.
- Yeni `tests/test_year_totals.py` (5): 5001+1 kayıtta 損益 toplamı, 仕入税額 (¥100×5001), CSV satır sayısı, admin listesi; sayfa sınırlarında boşluk/çift kayıt yok; aralık dışı ve başka tenant hariç. Eski kodda 4'ü kırmızı.
- Kapı: pytest 157 geçti (SQLite + yerel PostgreSQL 16).
- Sonraki: T-020 (確定申告 önizleme) veya P2 review-fix'ler T-028/T-029.

## 2026-11-06 13:27 JST · reviewer · son 26 saat (c46d946..f1e4297)
- Kapı başta yeşil (143). 外税 regresyonu düzeltildi (T-023): `RATE_EXCLUDE` 「外税8%対象額」 satırlarını atıyordu → karışık oranlı 外税 fişte tüm tutar 10%'a yazılıyordu; artık yalnızca 外税額 hariç. `_rate_amount` 「税額 ¥80」 sonrasını tutar saymıyor.
- `hmac.compare_digest` str + ASCII olmayan girdi → TypeError/500 (LINE imza, WhatsApp imza/verify, ADMIN_KEY ×3); bayt karşılaştırmasına geçildi → 400/401/403.
- Yeni testler: `test_auth_hardening.py` (3), `test_receipt_parser.py` (+6: 外税 karışık, 税額 kesme, ¥…- 領収書, 小計 yedeği, 令和元年, okunamayan oran). Toplam 152. Not: 68 gerçek fiş depoda olmadığından 外税 değişikliği gerçek set üzerinde yeniden ölçülmeli.
- Açılan review-fix: T-027 (P1, yıllık toplamlar 5000 satırda kesiliyor), T-028 (richmenu anahtarı URL'de), T-029 (fatura kalemi üst sınır).
- Vergi oranları/eşikleri TAX_RULES ile tutarlı; みなし仕入率 hâlâ ❓ (T-017).

## 2026-11-06 06:30 JST · kurulum (Claude) · T-023 gerçek fişlerle OCR
- Ürün sahibinin 68 gerçek fişiyle ölçüm (görseller depoda değil). Tüm alanlar %6 → %70, toplam %19 → %85, yanlış kayıt %7 (docs/OCR.md).
- Toplam artık 10%/8%対象 satırlarından; 外税, kayıp baş rakam (内消費税 ile), 登録番号 kontrol hanesi, gün adıyla tarih onarımı, Vietnamca fişler.
- Docker imajı tessdata_best 4.1.0 indiriyor; okunamayan fişte bot okunan alanları gösterip tutarı istiyor. Testler: 143.

## 2026-11-06 05:30 JST · kurulum (Claude) · T-022 yapay zekâsız fiş okuma
- `receipt_ocr.py`: Pillow ön işleme (EXIF, ölçekleme, median, Otsu) + Tesseract jpn; İngilizce ikinci geçişle T番号 doğrulaması.
- `receipt_parser.py`: 合計/お会計, 10%/8%対象 (OCR varyantlarıyla), 和暦 tarih, T番号, mağaza adı, kalem tahmini.
- Ürün sahibinin isteğiyle varsayılan motor `tesseract`; `auto` modda AI yalnızca yedek. Render servisi Docker'a geçirildi (Q-08), CI imajı derleyip içinde OCR'ı test ediyor.
- Testler: 133 geçti (5 gerçek OCR fikstürü dahil). Sonraki: T-023 gerçek fişlerle doğruluk.

## 2026-11-06 04:55 JST · developer · T-016
- 消費税カード `bot/tax` ile hizalandı: 本則/簡易/2割/3割 seçici (kullanılamayan yöntem gerekçesiyle devre dışı; 3割 yalnızca 個人・2027/2028), 簡易 için 事業区分 seçimi (みなし仕入率 ❓ notuyla), 経過措置 (80%/70%) kayıtsız alım tablosu, eksi tutarda 還付見込額.
- `app/lib/tax.ts` = `consumption.py`'nin TS kopyası; ortak örnek `tax-example.json` iki tarafta da test ediliyor (本則 差引 ¥1,419,500 → 納付見込 ¥899,500).
- API `/tax/consumption` yanıtına ekleyici `unqualified` alanı (`transitional_breakdown`). Testler: pytest 107 geçti, `next build` ✓, `npm run check:tax` ✓, tarayıcıda konsol hatası yok.
- Not: kod commit'i (743716d) BACKLOG/LOG güncellemesinden ayrı gitti (betik hatası); bu commit onu tamamlar.
- Sonraki: T-020 (確定申告 önizleme). Yeni alt görev T-021 (CI'da check:tax).

## 2026-11-06 02:35 JST · kurulum (Claude) · T-014 + 確定申告 API
- OCR çıktısı oran bazında (total10/total8); karışık fiş iki kayda bölünüyor (`normalize_ocr`), görsel yolu temizleniyor.
- `/api/v1/pl` (損益計算書, kalem bazında) ve `/api/v1/tax/income` (2026 için Q-03 nedeniyle 409). Testler: 99 geçti.

## 2026-11-06 04:30 JST · kurulum (Claude) · T-006
- `store.py`: `DATABASE_URL` varsa PostgreSQL (psycopg 3), yoksa SQLite; ortak `tx()` katmanı, `RETURNING id`, taşınabilir LIKE kaçışı.
- render.yaml: `jsaas-db` (free, singapore) + `DATABASE_URL`; CI'a PostgreSQL 16 servisiyle `bot-postgres` işi.
- Testler: 94/94 SQLite, 94/94 PostgreSQL 16 (yerel).

## 2026-11-06 03:55 JST · kurulum (Claude) · T-009, T-013, T-018
- Sohbet çekirdeği `app.respond()` kanaldan bağımsız hale getirildi; LINE ve WhatsApp aynı mantığı kullanıyor.
- LINE/WA: 「科目変更」 (kalem seçimi), 「税率8%/10%」 ile son kaydı düzeltme.
- WhatsApp Cloud API webhook (imza doğrulama, buton/liste mesajları, görsel → OCR), defter anahtarı `wa:<tel>`.
- Token iptali `DELETE /api/v1/tokens/current`, kullanıcı başına en fazla 5 token. Testler: 94 geçti.

## 2026-11-06 03:20 JST · kurulum (Claude) · T-007
- dashboard-next API'ye bağlandı (`app/lib/api.ts`): token varsa canlı veri (summary/cashflow/tax/invoices/profile), yoksa "デモデータ" rozetiyle mock. 消込 ve 請求書作成 API'ye yazar; fatura no tıklanınca PDF.
- `/connect#tk_...` bağlantı sayfası (LINE 「パネル」 linki). Static export → Render `jsaas-panel` (render.yaml).
- Yerelde uçtan uca denendi: demo-seed → connect → canlı KPI ¥4,250,000 → 消込 API'ye gitti.

## 2026-11-06 02:50 JST · kurulum (Claude) · T-005, T-008, T-012
- `store.py` veri katmanı (entries, api_tokens, invoices, profiles); `api.py` REST v1 (summary, cashflow, entries araması, 消費税, profil, faturalar, PDF, CSV), `docs/API.md`.
- 適格請求書: oran başına tek yuvarlama, PDF'de IPAゴシック gömülü (`bot/fonts/`, IPA lisansı). 入金消込 oran başına 売上 kaydı yazar.
- LINE 「パネル」 komutu web token'ı verir; `/api/v1/admin/demo-seed` örnek defter. Testler: 85 geçti.
- Sonraki: T-007 (dashboard → API), T-009, T-018.

## 2026-11-06 02:10 JST · kurulum (Claude) · T-004
- `bot/tax/income.py`: 速算表, 1,000円/100円 切捨て, 復興特別所得税 2.1%, 青色控除 (kârla sınırlı), 基礎控除 2025.
- 2026 基礎控除 Q-03 doğrulanana kadar `NotImplementedError` → T-004b (blocked). Testler: 70 geçti.

## 2026-11-06 02:00 JST · kurulum (Claude) · T-001, T-002, T-003
- `bot/tax/consumption.py`: 税込→税額, 経過措置 (80/70/50/30/0), 本則/簡易/2割/3割 hesap; 税率ごと端数処理, 100円未満切捨て.
- Bot yanıtı kayıtsız alım oranını tarihe göre gösteriyor; `web/` prototipleri 令和8年度改正'ye göre düzeltildi.
- `/entries/{user_id}` artık `X-Admin-Key` istiyor. Testler: 46 geçti.
- Sonraki: T-004 (所得税 motoru), T-005 (REST API).

## 2026-11-05 · kurulum (Claude, ürün sahibiyle)
- Depo proje yapısına geçirildi: `bot/`, `dashboard-next/`, `web/`, `docs/`, `agents/`, `tasks/`; Render `rootDir: bot`.
- 11 bot testi + CI (pytest, next build). Next.js dashboard derlendi ve masaüstü/telefon genişliğinde denendi.
- Vergi araştırması: 令和8年度改正 ile 経過措置 2026-10〜 %70, 3割特例 (個人, 2027–2028) → TAX_RULES + T-001/T-002.
- Açık sorular: Q-01 LINE kanalı, Q-02 API anahtarı, Q-03 基礎控除 2026, Q-04 hedef müşteri.
