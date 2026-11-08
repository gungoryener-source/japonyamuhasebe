# Ajan çalışma günlüğü (en yeni üstte)

Biçim: `## YYYY-MM-DD HH:MM JST · <rol> · <görev>` + 3–6 satır: ne yapıldı, testler, sonraki adım/engeller.

## 2026-11-08 23:20 JST · developer · T-072 消費税申告書 PDF
- `reports.render_consumption_return_pdf` + `GET /reports/consumption-return.pdf` (hesap = `/tax/consumption/return`; satır başına formül/kural, 未検証 işareti, uyarılar, 税理士・税務署 notu, çok sayfa taşması). /tax kartında 「申告書PDF」 düğmesi (canlı mod).
- Testler: içerik (toplamlar API ile aynı), 401, geçersiz method 400, yıl 422, kullanıcı izolasyonu.
- Kapı: pytest, next build, check:*, Playwright 31/31.
- Sonraki: T-082b, T-065c/T-067 (izin/onay gerekir).

## 2026-11-08 22:50 JST · developer · T-080 eski sabitleri params dosyalarına taşıma
- `tax/params/consumption_static.toml` (RATES, TRANSITIONAL_CREDIT, KANI_RATIO, SMALL_BUSINESS_LIMIT, TRANSITIONAL_CAP) ve `income_static.toml` (速算表, 復興特別所得税 21/1000, 基礎控除 2025–2027, 青色控除 tabloları): her değerde source/rule/checked. `consumption.py` ve `income.py` aynı isimlerle bunları yükler; imza/çıktı aynı (mevcut testler + TS parite testleri kanıt).
- `tests/test_static_params.py`: şema (source+rule+checked), değerlerin birebir aynılığı, tablo sıralaması.
- Kalan küçük sabitler: yuvarlama birimleri (1,000/100 yen) ve 2割/3割 oranları `consumption_return` yıl dosyasında; `income.py` yuvarlamaları kodda (oran değil, kural).
- Kapı: pytest 902 geçti (dashboard değişmedi).

## 2026-11-08 22:10 JST · developer · 国税庁 otomatik firma/登録番号 kontrolü (T-082)
- `POST /bank/review/enrich`: eşleşmemiş harcama satırları için 法人番号 Web-API + インボイス公表サイト; tek aday ve valid ise `source=nta` ile 取引先 kaydı, aksi halde yalnızca öneri. `NTA_APP_ID` yoksa 503. 通帳 sayfasında 「国税庁で一括確認」 düğmesi; 通帳 yüklemesinden sonra otomatik.
- Sunucu tarafı çağrı: geliştirme oturumunun tarayıcı/ağ erişimine bağlı değil. Canlıda Q-20 (NTA_APP_ID) girilmeden çalışmaz.
- Kapı: pytest, next build, check:*, Playwright.

## 2026-11-08 21:20 JST · developer · T-077 クレジットカード明細 CSV
- `bot/card_csv.py` (sütun eşlemesi sözcüklerle; 返金 → giriş, 合計/分割・リボ notları atlanır, 支払区分/支払日 摘要'ye), `POST /card/import` → mevcut bank_tx hattı (`src=card`, 未確認). `docs/CARD_CSV.md`: şirket CSV başlıkları için birincil kaynak bulunamadı → ⚠️, başlık uydurulmadı.
- 未払金 karşı hesabı `entries` şemasında olmadığı için yapılmadı (T-077b). Panel sekmesi eklenmedi (BACKLOG: isteğe bağlı).
- Kapı: pytest tam yeşil.

## 2026-11-08 20:45 JST · developer · T-075b 決算書 PDF 減価償却費の計算
- `render_blue_return_pdf(..., depreciation=)`:固定資産 varsa 3. sayfa (資産名・償却方法・取得価額・月数・普通償却費・事業割合・必要経費算入額・未償却残高 + toplam); yoksa 2 sayfa (geri uyum). `test_pdf_depreciation_page`.
- Kapı: pytest tam; dashboard-next değişmedi.
- Sonraki: T-080, T-072, T-077.

## 2026-11-08 20:10 JST · developer · 申告前チェックリスト (T-081)
- `bot/tax/precheck.py` (saf fonksiyon) + `GET /tax/precheck`: eksik profil, 登録番号なし 課税仕入, 経過措置 üst sınır, fatura numarası boşlukları, eşleşmemiş banka kayıtları, 家事按分 ayarsız, varlık uyarıları, doğrulanmamış parametreler. Vergi hükmü vermez; sonda 税理士 uyarısı.
- /tax sayfasına `Precheck.tsx` kartı, tr/en, e2e fixture.
- Kapı: pytest, next build, check:*, Playwright 31/31.
- OCR onay maddesi eklenmedi (entries'te onay bayrağı yok). Sonraki: T-075b, T-080.

## 2026-11-08 19:30 JST · developer · T-076 家事按分
- `apportionments` tablosu (科目ごと 0–100, 100 = yok), `GET/PUT /settings/apportionment`; /pl (科目合計に bir kez floor), 決算書 PDF (pl üzerinden) ve 消費税 本則 仕入税額 (仕訳ごと floor) uygular; ham kayıt/CSV değişmez. Oran kullanıcı girdisi, varsayılan yok. Hukuki dayanak ⚠️ (TAX_RULES, birincil kaynak doğrulanmadı).
- 設定'e 「家事按分」 kartı (ja/tr/en), e2e fixture.
- Kapı: pytest, next build, check:*, Playwright 31/31.
- Sonraki: 申告前チェックリスト, T-075b, T-080.

## 2026-11-08 18:50 JST · developer · T-075 /assets 固定資産 sayfası
- `app/assets/page.tsx` (台帳 + 減価償却費の計算 tablosu, ekle/sil, demo + canlı), menü girişi, `api.ts` tipleri, ja/tr/en çeviri; e2e fixture'a `/assets` ve `/assets/schedule?year=2026`.
- Kapı: pytest yeşil, next build, check:* ve Playwright 31/31.
- PDF'teki 減価償却費の計算 tablosu T-075b'ye ayrıldı. Sonraki: T-076 (家事按分), 申告前チェックリスト.

## 2026-11-08 18:10 JST · developer · T-073/T-074 減価償却 + 固定資産台帳
- TAX_RULES'a 減価償却 bölümü; `tax/params/depreciation.toml` (+`load_static`); `tax/depreciation.py` (定額法 月割, 備忘価額1円, 一括償却, 少額特例 30万→40万 sınırı 2026-04-01, 300万 üst sınır uyarısı). 償却率 kuralı ve 10万/20万 eşikleri `verified=false` (別表第八 birincil kaynak doğrulanamadı).
- `fixed_assets` tablosu (yalnızca ekleme, audit `asset`), `/assets` CRUD + `/assets/schedule`, `/pl` 減価償却費 otomatik (varlık yoksa /pl değişmez).
- Kapı: pytest 865 geçti. docs/API.md güncellendi.
- Sonraki: T-075 (panel /assets), T-076 (家事按分), 申告前チェックリスト.

## 2026-11-08 17:05 JST · developer · T-071b 消費税申告書 detay ekranı
- `/tax` sayfasına `ConsumptionReturn.tsx` kartı: T-071 API'sinin satırları (国税/地方 ayrı), formül + kural no + 未検証 rozeti, Japonca uyarılar, 仕入 割戻し/帳簿積上げ seçimi (canlı mod), iade durumu. Demo modu `consumption-return-example.json` (motordan üretilir, elle yazılmadı; `test_demo_example_is_fresh` güncelliği denetler).
- Eski 消費税 kartı değişmedi (国税+地方 toplam tahmini); yeni kart beyanname biçimi. Aynı örnekte toplamlar uyumlu: yeni 1,419,400 vs eski 1,419,500 (satır bazlı yuvarlama farkı).
- tr/en çevirileri (`locales/*.json`), e2e fixture'a `/tax/consumption/return`.
- Kapı: pytest 819 geçti, next build + check:* yeşil, Playwright e2e 29/29.
- Sonraki: T-080, T-072 (PDF), T-076 (家事按分), T-073–075 (減価償却).

## 2026-11-08 16:20 JST · developer · T-071 消費税申告書 hesap motoru
- `bot/tax/params/` (yeni, paket yok: stdlib `tomllib`): yıl dosyaları 2024–2028.toml, her değer `{value, verified, source, rule, checked}`, kesirler `[pay, payda]` tamsayı. `params.unverified(yıl)` = TODO(verify) raporu (2027/2028: 3割 様式 ドラフト, 飲食料品 1% beklemede).
- `bot/tax/consumption_return.py` `compute_return`: TAX_RULES §1 申告書#1–13 — 課税標準額 千円未満切捨て, 7.8/6.24%, 仕入 割戻し / 帳簿積上げ, 経過措置 oranı税率ごと sonda, 差引 百円未満, 地方 22/78, 還付, 簡易 (tek 区分)/2割/3割. Her satırda formül + girdi + kural + verified; Japonca uyarılar (未反映項目, 税理士 確認). Saf fonksiyon.
- `GET /api/v1/tax/consumption/return` (yıl parametresi yok → 409). `docs/API.md` satırı. Eski `/tax/consumption` değişmedi.
- 25 yeni test (`tests/test_consumption_return.py`): NTA 設例 231,200 → 65,200, 千円/百円 sınırları, 割戻し vs 帳簿積上げ farkı, 70/80% sınır günleri, 還付, 2割/3割 yıl/法人/1,000万 sınırları, şema, saflık, API.
- Kapı: aşağıda. Sonraki: T-080 (eski sabitleri params'a taşıma), T-072 (PDF).

## 2026-11-08 15:40 JST · developer · T-070 消費税申告書 hesap adımları (belge)
- `docs/TAX_RULES.md` §1'e 「消費税申告書の計算手順」 tablosu (14 adım): 課税標準額 千円未満切捨て, 7.8/6.24%, 積上げ 78/100, 仕入 割戻し 7.8/110·6.24/108 (yalnızca satış da 割戻し iken), 経過措置 oranı税率ごと en sonda, 差引税額 百円未満切捨て, 地方 22/78 百円未満切捨て (NTA 設例 test vektörü 231,200 → 65,200), 2割 80/100 (手引き 〈令和8年11月版〉), 3割 70/100 ⚠️ (様式 ドラフト), 簡易 tek 事業区分 ⚠️, 期限. Kaynaklar NTA No.6371/6383/6351/6505 + 手引き/書き方, kontrol 2026-11-08.
- Yeni bulgu: 飲食料品 1% (2027-04-01〜2029-03-31, 2026-09-15 閣議決定 大綱) ⚠️ 法案成立前 → kod değişmedi, T-079 (tax-watcher) açıldı.
- LOG başlığındaki bozuk biçim satırı düzeltildi (önceki oturum notu biçim satırının içine yazılmıştı; içerik aşağıda korundu).
- Kapı: pytest SQLite 793 geçti/8 atlandı (kod değişmedi). Sonraki: T-071.

## 2026-11-08 15:15 JST · oturum (ürün sahibiyle) · T-064b
- T-064b: Q-16 şirket fiyat ayarı ekranı (`/admin/pricing`, ADMIN_KEY ile). Varsayılan kapalı = ücretsiz/sınırsız. `bot/pricing.py`, `/api/v1/admin/pricing`, `/companies/pricing`, şirket ekleme 402 kontrolü.
- CORS'a `X-Admin-Key` eklendi (tarayıcıdan yönetici ekranı çalışsın); testler eklendi.
- Q-18/Q-19 onaylandı (T-065c, T-067 açık). Q-21 cevabı yazıldı.

## 2026-11-08 14:55 JST · developer · T-078 canlıya alma kontrolü
- `GET /admin/config-check` (`bot/config_check.py` + `app.py`): yalnızca `X-Admin-Key` başlığı (sorgu dizesi yok, yoksa/yanlışsa 401, `Cache-Control: no-store`). Yanıt: 23 değişken için `set` (bool, boşluk = yok) + Q numarası + düzey (required/recommended/optional), `ready`, `missing_required`, `open_questions`; `runtime`: db (sqlite/postgres), storage (local/s3), tesseract, `mail_provider_supported`. Değer/uzunluk/önek dönmez (Stripe test/live türü de önekten türediği için bilinçli olarak eklenmedi).
- `docs/GO_LIVE.md`: insan adımları sırası (Q-07/Q-09 plan → Q-08 Docker → Q-01 LINE → Q-05 PANEL_URL → Q-14 R2 → Q-13 Resend → Q-10 Stripe test → Q-12/Q-21 panel değişkenleri, her adımda kontrol) + 9 adımlı uçtan uca duman testi. `docs/API.md`'ye uç nokta satırı.
- 12 yeni test (`tests/test_config_check.py`): 401 (anahtarsız/boş/yanlış/`?key=`/ADMIN_KEY yok), sahte değerlerin ve ilk 8 karakterinin yanıtta geçmediği, eksik zorunlu → Q listesi, boşluk = yok, desteklenmeyen MAIL_PROVIDER değeri sızmaz, render.yaml bot sırlarının listede olduğu, `/` ve `/callback` sözleşmesi.
- Kapı: pytest SQLite 788 geçti/8 atlandı, PostgreSQL 16 793 geçti/3 atlandı. dashboard-next değişmedi.
- Sonraki: T-070 (消費税申告書 hesap adımları, yalnızca belge). Yeni soru yok.

## 2026-11-08 14:25 JST · planner · haftalık planlama
- ROADMAP: Faz 2 gider akışı/登録番号 (T-063), Faz 5 kalanları (T-044/b, T-046/b/c, T-047, T-048/b, T-021/T-035), Faz 3 青色決算書 + e-Tax araştırması, Faz 4 çok dilli bot ✅ işaretlendi; Faz 5 kod tarafı tamam.
- Teşhis: todo kuyruğu boşalmıştı (yalnızca T-033b + Q-19'a bağlı T-068/069). T-033b → blocked (Q-22 yeni: banka CSV örnekleri), T-068/069 → blocked (Q-19). 24 saati aşan `doing` yok.
- Yeni görevler (kabul ölçütlü, tek çalışmalık): T-070/071/072 消費税申告書 (belge → hesap → PDF), T-073/074/075 減価償却 (belge → 台帳+hesap → panel), T-076 家事按分, T-077 kart CSV, T-078 config-check + GO_LIVE. Önerilen sıra BACKLOG başında.
- QUESTIONS: çift numaralar düzeltildi (NTA_APP_ID → Q-20, LINE 友だち追加 → Q-21; BACKLOG T-044 referansı güncellendi; kod yorumlarındaki Q-16 = çok şirket fiyatı, değişmedi). WEEKLY hafta 2 raporu yazıldı.
- Kapı: pytest SQLite 777 geçti/8 atlandı. Kod değişmedi.

## 2026-11-08 13:55 JST · developer · T-012c マネーフォワード 仕訳帳インポート CSV
- Kaynak: MF 公式「仕訳帳インポート（マネーフォワード クラウド会計形式）」 (更新日 2026-07-09) 27 sütun 取引No〜最終更新者; 税区分一覧 FAQ s15 (正式名称) ve 対象外 FAQ tax-class02 (2026-07-29). URL'ler `export.py` docstring'inde, kontrol 2026-11-08.
- `export.py` mf: eski 9 sütunlu tahmini biçim → resmî 27 sütun (`MF_HEADER`). 税区分: 課税仕入 10% / 課税仕入 (軽)8% / 課税売上 10% / 課税売上 (軽)8% / 非課税売上 (受取利息) / 対象外. 借方/貸方取引先 = 取引先, 摘要 = 取引先, 登録番号 → 仕訳メモ. インボイス: 適格 / 80％・70％・50％・30％控除 / 控除なし (`input_credit_ratio` ile aynı sınırlar = TAX_RULES §1), 売上・税率0・制度前仕入 boş (MF'de boş = 適格). 税額 boş (resmî talimat). Karşı hesap freee/弥生 ile aynı `_counter` (BANK → 普通預金; önceden MF'de hep 事業主借). Uzunluk sınırları 30/255/200.
- Yeni test 22 (`tests/test_export_mf.py`: başlık, gider/gelir satırı, 軽減 adları, 税率0, 経過措置 10 sınır tarihi, 適格, banka kaynağı, uzunluk, cp932, formül kaçışı) + `test_api` mf kontrolleri.
- Kapı (reviewer rebase sonrası): pytest SQLite 777 geçti/8 atlandı; rebase öncesi PostgreSQL 16 777 geçti/3 atlandı. dashboard-next değişmedi.
- Not: MF'ye gerçek içe aktarma denemesi yapılmadı (hesap yok); 税区分 adları kullanıcının MF 税区分 ayarlarında kapalıysa eşleştirme ekranı çıkar. Sonraki: kalan todo yalnızca T-033b (örnek CSV bekliyor); T-067〜069 Q-19'a bağlı. Yeni soru yok.
## 2026-11-08 13:50 JST · reviewer · son 26 saat incelemesi
- İncelenen (son review'dan sonra): T-033 (bank_csv yön sütunu/bölünmüş tarih), T-035 (Playwright e2e + fixture testi), T-045b (docs/ETAX.md, kod yok), T-046c (scripts/backup.sh). Doğruluk/güvenlik sorunu bulunmadı: yönü bilinmeyen satır atlanıyor, backup.sh `pipefail` + `.partial` + 600 izin + URL sızmıyor.
- 5 yeni test (`tests/test_bank_csv_formats.py`): boş 入出金区分 → atlanır, 0/boş tutar → atlanır, 全角 括弧 bölünmüş tarih + geçersiz gün (2/30) atlanır, yalnızca 年/月 sütunu → başlık yok hatası, 現在高 bakiye sütunu.
- Vergi kuralı değişikliği yok (TAX_RULES kontrolü gerekmedi). Yeni review-fix görevi yok.
- Kapı: pytest SQLite 755 geçti/8 atlandı. dashboard-next değişmedi.

## 2026-11-08 12:50 JST · developer · T-046c PostgreSQL yedekleme
- `scripts/backup.sh`: `pg_dump --dbname="$DATABASE_URL" --no-owner --no-privileges | gzip -9` → `backups/tegaru-YYYYMMDD-HHMMSS-JST.sql.gz` (`BACKUP_DIR`), izin 600, önce `.partial` → gzip testi + 「dump complete」 satırı doğrulanınca yeniden adlandırma; hata/kesik dökümde dosya kalmaz (çıkış kodları 2/3/5/6/7). URL hiçbir çıktıya yazılmaz; DB'de ve eski yedeklerde silme yok.
- `docs/OPERATIONS.md`: yedek alma (`read -rs` ile URL), boş yeni DB'ye geri yükleme (`gunzip -c … | psql -v ON_ERROR_STOP=1 --single-transaction`) + doğrulama, fiş görselleri kapsam dışı, Render free DB ~30 gün (Q-07 → Basic). `.gitignore`: `backups/`, `*.sql.gz`.
- Yerel PG 16 ile gerçek yedek → boş DB'ye geri yükleme denendi (Japonca metin dahil birebir). `bash -n` + shellcheck 0.10 temiz.
- Kapı: pytest SQLite 750 geçti/8 atlandı, PostgreSQL 16 755 geçti/3 atlandı; 11 yeni test (`tests/test_backup_script.py`: sahte pg_dump ile başarı/600/dosya adı, sır sızmaz, URL yok/boş, pg_dump hatası, kesik döküm, pg_dump yok, eski yedek korunur; PG varsa gerçek döküm). dashboard-next değişmedi.
- Sonraki: P2 — T-012c (MF CSV), T-033b (örnek CSV bekliyor). Yeni soru yok.

## 2026-11-08 11:55 JST · developer · T-045b e-Tax araştırması
- `docs/ETAX.md` (yalnızca belge, kod yok): e-Tax 仕様書 listesi (項番1/2/3/7/8/9/11/19, 令和8年 güncelleme tarihleri, ドラフト版 令和9年1月4日), 個人 所得税 帳票 seti (令和7年分), gönderim yolları — her iddia 国税庁/e-Tax sayfası + kontrol tarihi 2026-11-08.
- Bulgular: e-Taxソフト(WEB版 / ダウンロード版) 民間ソフトの .xtx'ini okuyup gönderebilir; 作成コーナー yalnızca kendi 決算書'ını ekler; e-Tax API 申告データ gönderimi desteklemez. Öneri: ürün yalnızca .xtx üretir, imza/gönderim kullanıcıda (sertifika/sır saklama yok).
- 様式ID'ler (KOA010/KOA020) yalnızca eski bir listeden ⚠️; güncel ID koda sabit yazılmayacak, 項番7'den alınacak.
- Yeni alt görevler: T-067 (blocked Q-19), T-068, T-069. Yeni soru Q-19 (仕様書 indirme = 利用上の注意 kabulü).
- Kapı: pytest SQLite 741 geçti/6 atlandı (kod değişmedi). dashboard-next değişmedi.

## 2026-11-08 11:10 JST · developer · T-035 panel e2e (Playwright)
- `dashboard-next/e2e/panel.spec.ts` (29 test): demo modunda 9 menü + kenar çubuğundan sırayla gezinti + login/signup/reset/join/connect/welcome/lp/legal×3; canlı modda 9 menü (localStorage token + `**/api/v1/**` sahte yanıt, Bearer başlığı denetlenir). Konsol hatası, yakalanmamış istisna, demoda API çağrısı, canlıda fixture'da olmayan çağrı → kırmızı.
- Sahte API verisi elle yazılmadı: `e2e/make_fixtures.py` gerçek bot'tan (geçici SQLite + `demo_data.seed`) 20 GET ucunu kaydeder; `bot/tests/test_e2e_fixtures.py` yol/biçim kaymasını ve sır olmadığını denetler. Statik sunucu `e2e/serve.mjs` (yeni paket yok); tek yeni dev paket `@playwright/test` 1.63.0 (tam sabit).
- Testin gerçekten yakaladığı doğrulandı: /summary silinip /invoices bozulunca canlı ホーム ve 請求書 testleri kırmızı.
- CI: dashboard işine `playwright install --with-deps chromium` + `npm run e2e`, başarısızlıkta trace artifact. Kapı: pytest SQLite 741 geçti/6 atlandı, PostgreSQL 16 745/2; next build + check:* yeşil; e2e 29/29 (~18 sn).
- Sonraki: P2 — T-045b, T-046c, T-012c (T-033b örnek CSV bekliyor). Yeni soru yok.

## 2026-11-08 10:20 JST · developer · T-033 banka CSV başlıkları
- `docs/BANK_CSV.md`: banka başına başlık satırı + kaynak + seviye (✅ ゆうちょBizダイレクト 操作説明書 18.4, 京都銀行 ANSER CSV; 🟡 felica2money wiki: 楽天(旧イーバンク), PayPay(旧JNB), ソニー円; ⚠️ MUFG, SMBC, みずほ, 住信SBI, GMO — kamuya açık CSV başlığı bulunamadı → T-033b).
- Bulunan hata: ゆうちょBiz CSV'de 「入出金区分」 tutar sütunu sanılıyordu → hiçbir satır alınmıyordu. `bank_csv`: yön sütunu (受入/入金/1 → +, 払出/出金/2 → −, tanınmayan → satır atlanır), 「操作日(年/月/日)」 bölünmüş tarih, 「番号」「口数」 sütunları atlanır (受入明細番号 ≠ 入金), 送金人名/依頼人名 摘要'ye eklenir, 「お取り引き日」「お預け入れ額」「お引き出し額」「現在（貸付）高」. Daha önce çalışan biçimlerin çıktısı değişmedi.
- Kapı (rebase sonrası): pytest SQLite 739 geçti/6 atlandı, PostgreSQL 16 743 geçti/2 atlandı. 17 yeni test (`tests/test_bank_csv_formats.py`). dashboard-next değişmedi.
- Sonraki: P2 — T-035, T-045b, T-046c, T-012c. Yeni soru yok (⚠️ bankalar için anonim örnek CSV T-033b'de istendi).

## 2026-11-08 09:50 JST · reviewer · son 26 saat incelemesi (T-019, T-066, T-026, T-024)
- İncelendi: e2aa9bc (T-019 havuz + yavaş istek), 7d15652 (T-066 2割 特定期間 — TAX_RULES §1 NTA Q&A 問115 kaynaklı ✅), 4edff0c (T-026 kırmızı damga), 08c7a53 (T-024 OCR onayı). Kapı başta yeşildi (711/6).
- Doğruluk/güvenlik: 日付 komutu `user_id` ile filtreli; yavaş istek log'u rota şablonu (kişisel veri yok); üretim kodunda iç içe `tx()` bulunmadı (havuz max 10 tükenme riski yok). Hata bulunmadı.
- 11 yeni test (`tests/test_review_20261108b.py`): aynı ref'li fişte kullanıcı ayrımı, fişten sonra elle kayıtta 日付 yalnızca son kaydı değiştirir (tam genişlik ：), `needs_check` DB'ye yazılmaz, güvenli çok oranlı fişte uyarı yok, handler hata verse de yavaş log (yol sızmadan), lifespan geçişi, 2割 特定期間 sınırları (10,000,000 / 10,000,001, 給与 ile kurtarma, bilinmeyen).
- Kapı: pytest SQLite 722 geçti/6 atlandı. dashboard-next değişmedi. Yeni review-fix/soru yok.

## 2026-11-08 09:20 JST · developer · T-024 düşük güvenli OCR sonucu onayı
- `receipt_parser.parse_receipt`: `date_found` / `rate_breakdown_found` bayrakları yalnızca False iken (güvenli fişte çıktı birebir aynı). Tek oranlı fişte 「内消費税」 tutarı `floor(合計×r/(100+r))` ile tutarsa tahmin sayılmaz (restoran fikstürü uyarısız kalır).
- `app.normalize_ocr` → `needs_check` (date/rate; AI yolunda 内訳 yoksa rate). LINE/WhatsApp yanıtında ⚠️ 「日付を確認してください」 / 「税率を確認してください」 + 「確認」「日付:昨日」「日付:一昨日」 (+ tek kayıtta 税率8%/10%) hızlı yanıtları; tr/en çeviriler.
- Yeni komutlar: 「確認」, 「日付 11/3」 (son fişin tüm 税率別 kayıtları, `store.last_receipt_entries`; audit_log'a yazılır; gelecek tarih red, yılsız gelecek → geçen yıl). Şema değişmedi.
- Kapı: pytest SQLite 711 geçti/6 atlandı, PostgreSQL 16 715 geçti/2 atlandı. 42 yeni test (`tests/test_ocr_confirm.py`). dashboard-next değişmedi (panel API `entries[].needs_check` görebilir → ileride vurgulama).
- Sonraki: P2 — T-033, T-035, T-045b, T-046c, T-012c. Yeni soru yok.

## 2026-11-08 07:55 JST · developer · T-026 OCR kırmızı damga bastırma
- `receipt_ocr.preprocess`: gri tondan önce `suppress_red` — Pillow HSV maskesi (H ≤14 / ≥232, S ≥70, V ≥90) + 1 px açık renkli JPEG halesi → beyaz. Damga üstündeki siyah yazı, mavi/yeşil kalem, gri korunur. Yeni paket yok. `OCR_RED_SUPPRESS=0` ile kapanır (varsayılan açık).
- Kırmızı piksel yoksa çıktı birebir aynı (5 fikstürde testli) → docs/OCR.md 67 fişlik ölçüm geçerli kalır.
- Ölçüm: `scripts/ocr_eval.py` (gerçek fiş klasörü + truth.csv, açık/kapalı karşılaştırma; `--synthetic`). Sentetik 角印/丸印 (`tests/stamp_fixture.py`, depoya ikili dosya yok): tüm alanlar %67 → %100, toplam %100 → %100 (düşmedi), yanlış kayıt %0. Gerçek damgalı fişlerle ölçüm ürün sahibinde (görseller depoda yok).
- Kapı: pytest SQLite 669 geçti/6 atlandı, PostgreSQL 16 673 geçti/2 atlandı. 19 yeni test (`tests/test_ocr_red_stamp.py`). dashboard-next değişmedi. Bilinen risk: kırmızı basılmış metin de silinir (OCR.md'de).
- Sonraki: P2 — T-024 (düşük güvenli OCR onayı), T-033, T-035, T-045b, T-046c, T-012c. Yeni soru yok.

## 2026-11-08 06:45 JST · developer · T-066 2割特例 特定期間 şartı (review-fix)
- Birincil kaynak doğrulandı: NTA インボイスQ&A 問115 (消法9の2① 特定期間 → 2割特例 不可) + NTA 適用可否フローチャート (特定期間は売上高に代えて給与等で判定可). TAX_RULES §1 2割 satırı kaynak + 2026-11-08 kontrol tarihiyle güncellendi.
- `consumption.compute` niwari: `_check_small_business("2割特例", base, specific, salaries)` (3割 ile aynı kural). Panel `tax.ts methodUnavailable` niwari'de 特定期間 mesajı (parite), `check-tax.mjs` sınır testleri.
- `test_niwari_ignores_specific_period` tersine çevrildi → 13 yeni/değişen test (10,000,000 / 10,000,001, 給与 ile kurtarma, 基準期間 önce, API 400/422).
- Kapı: pytest SQLite 650 geçti/6 atlandı, PostgreSQL 16 654 geçti/2 atlandı; `next build` + check:tax yeşil.
- Sonraki: P2 — T-026 (kırmızı damga), T-046c (yedekleme), T-024, T-033 … Yeni soru yok.

## 2026-11-08 05:55 JST · developer · T-019 PostgreSQL bağlantı havuzu + yavaş istek ölçümü
- `store.tx()` PG yolunda artık `psycopg_pool.ConnectionPool` (yeni bağımlılık `psycopg_pool==3.2.4`, saf Python): süreç başına tembel açılış, min 1 / max 10, timeout 30 sn, `check_connection` (Render'ın kapattığı boş bağlantılar), `prepare_threshold=None` (init_db sütun eklese de havuzdaki bağlantıda plan hatası yok). URL değişirse eski havuz kapanır. `close_pool()` → app `shutdown` olayı + atexit. SQLite yolu değişmedi.
- `bot/timing.py` `SlowRequestMiddleware` (en dışta): > 1 sn istekte WARNING `tegaru.slow` — yöntem + **rota şablonu** + durum + süre; gerçek yol/sorgu (LINE user_id, token) yazılmaz, eşleşmeyen yol "(unmatched)".
- Kapı: pytest SQLite 634 geçti/6 atlandı, PostgreSQL 16 638 geçti/2 atlandı (rebase sonrası). 15 yeni test (`tests/test_db_pool.py`: havuz yeniden kullanımı, commit/rollback, iç içe tx, kapat/yeniden aç, URL değişimi, şema değişikliği sonrası SELECT *, log'da kişisel veri yok). dashboard-next değişmedi.
- Sonraki: önce reviewer'ın açtığı T-066 (review-fix), sonra P2 — T-026 (kırmızı damga), T-046c (yedekleme), T-024, T-033 … Yeni soru yok.

## 2026-11-08 05:46 JST · reviewer · son 26 saat incelemesi (0c07a31..fd1410d)
- İncelenen: T-065/T-065b audit_log (entries/invoices/bank_tx; tüm sorgular user_id ile sınırlı, e-posta yalnızca owner/kendisi ✅), T-017 みなし仕入率 (TAX_RULES §1 ✅), T-050 2割/3割 1,000万 + 経過措置 1億/10億 üst sınırı (TAX_RULES §1 ✅). Kapı yeşildi (612). Hata bulunmadı.
- Eklenen testler (`tests/test_review_20261108.py`, 13): değişmeyen PATCH audit yazmaz + `changed` yalnızca fark, `/audit` limit 0/1001 → 422 ve sıralama, fatura iki kez 消込 → tek audit/tek 売上, `/bank/match` invoice+bank_tx+entry audit (actor owner) ve 409'da yeni satır yok, başka kullanıcının kaydı store'da güncellenmez/silinmez/audit yazılmaz, 経過措置 üst sınırı 2023-10-01 öncesi alımları saymaz, `/tax/consumption?method=sanwari` 特定期間 sınırları (7 durum). Toplam 625.
- Açılan: T-066 (review-fix, P2) — 2割特例 yalnızca 基準期間'e bakıyor; 特定期間 şartı birincil kaynakla doğrulanmalı (bu çalışmada NTA sayfası açılamadı, kod değiştirilmedi).

## 2026-11-08 04:49 JST · developer · T-050 2割/3割特例 uygunluk + 経過措置 1億 üst sınırı
- `consumption.compute`: isteğe bağlı `base_period_sales` / `specific_period_sales` / `specific_period_salaries`. 2割: 基準期間 >1,000万 → ValueError; 3割: 基準期間 veya 特定期間 >1,000万 → ValueError (特定期間 給与等 ≤1,000万 ise uygun — TAX_RULES §1). Parametre yoksa davranış aynı. `method_ineligible` yardımcı.
- 経過措置 üst sınırı: `transitional_cap(period_start)` (2024-10-01〜 10億, 2026-10-01〜 1億) + `transitional_cap_warnings` (取引先 bazında, kırpılmış ad,適格/非課税/isimsiz/0% hariç). Yorum: aşan kısım `compute`'ta düşülmez, yalnızca uyarı (backlog kabulüne göre). `Purchase.seller` isteğe bağlı alan.
- API `/tax/consumption`: yeni sorgu parametreleri (ge=0) + `transitional_cap`, `transitional_over_cap` (dönem = takvim yılı). Panel: `tax.ts methodUnavailable` aynı şartlar (check:tax'a sınır testleri), ホーム 消費税 kartında üst sınır aşım uyarısı (ja/tr/en).
- Kapı: pytest SQLite 612 geçti, PostgreSQL 16 610 geçti/2 atlandı; `next build` + check:* yeşil. 28 yeni test (`tests/test_tax_eligibility.py`).
- Seçim notu: P2 todo'lar arasında T-050 seçildi (önceki LOG önerisi; kaynakları TAX_RULES'ta ✅). Sonraki: T-019, T-026, T-046c … Panelde 基準期間 girişi yok (ileride 設定'e eklenebilir).

## 2026-11-08 03:50 JST · developer · T-017 簡易課税 みなし仕入率 testleri
- `bot/tests/test_tax_kani.py` (30 test): tablo = TAX_RULES §1 (NTA No.6505, 90/80/70/60/50/40), her tür için みなし仕入税額/納付, 円未満・100円未満 切捨て sınırları, 8%+10% karışık satış, alışların yok sayılması, geçersiz tür (0/7/-1/None/"5"/5.5) → ValueError, `/tax/consumption?method=kani` (5/6/7/eksik), panel `tax.ts` KANI_RATIO paritesi.
- `consumption.py` yorumu 「❓ 要確認」 → kaynak + kontrol tarihi. Panel vergi kartı notu 「みなし仕入率は確認中」 → 「第1種90%〜第6種40%」 (ja/tr/en).
- Kapı: pytest SQLite 584 geçti, PostgreSQL 16 582 geçti/2 atlandı; `next build` + check:* yeşil.
- Sonraki: P2 sırası — T-050 (2割/3割 uygunluk uyarısı), T-019, T-026 …

## 2026-11-08 02:52 JST · developer · T-065b 訂正・削除の履歴 (dilim 2)
- Panel 経費精算: her satırda 「履歴」 (History simgesi) → yan panel: 登録/訂正/削除, zaman, kim, alan bazında önce → sonra. ja/tr/en sözlük eklendi (rol etiketleri dahil).
- API: `with_actors` → actor_kind/role/email/is_me/former. E-posta yalnızca owner'a (üye listesi zaten owner'a özel) ve kişinin kendisine; çıkarılan üye 「退出したメンバー」. `/entries/{id}/history`, `/audit` ve yeni `GET /bank/{id}/history`.
- bank_tx: `store.update_bank_tx` (önce/sonra audit) — PATCH /bank/{id} tutar/bakiye, confirm/excluded, 消込 ve 経費化 bağlantıları, kayıt silinince bağ çözülmesi. Banka kaynaklı kayıtların actor'ı artık onaylayan kişi (`WEB:<rol>:<hesap>`). `balance_ok` türetilmiş → yazılmaz.
- Kapı: pytest SQLite 554 geçti, PostgreSQL 16 552 geçti/2 atlandı; `next build` + check:* yeşil; demo modunda panel ekran görüntüsüyle kontrol edildi. 6 yeni test (`tests/test_audit_bank_actor.py`).
- Yeni soru Q-18 (仕切書 geçmişi için T-060 dosyalarına izin) → T-065c blocked. Sonraki: P2 (T-017, T-050, T-019 …).

## 2026-11-08 01:44 JST · reviewer · son 26 saat incelemesi (91e4fa2..9fa1789)
- İncelenen: T-034 fiş görseli, T-049 青色 75万 (TAX_RULES §2 kaynaklı ✅), T-056 Resend (log maskeli ✅), T-060/T-061/T-062 仕切書・通帳・取引先, T-063 登録番号, T-064 çok şirket, AI okuma ayarı. Kapı yeşildi (536).
- Güvenlik: slips/counterparties/bank sorguları user_id ile sınırlı; çok şirkette sahiplik kontrolleri (switch/join/link-line/line_target) doğru. Büyük sorun yok, review-fix açılmadı.
- Eklenen testler (`tests/test_review_20261107b.py`, 6): /tax/income 2026↔2027 青色 seçenekleri (API), LINE line_target yabancı/eski seçimde kendi defterine döner, şirket adı 100 karakter + hesapsız 403, işlenmiş 仕切書 update/reject/approve engeli + başka defterden görünmez, kind doğrulaması, receipt_reader dil ayarını korur. Toplam 542.
- Not: send_mail DEBUG seviyesinde gövdeyi (sıfırlama bağlantısı) loglar; üretimde DEBUG kapalı olmalı.

## 2026-11-08 01:52 JST · developer · T-065 訂正・削除の履歴 (dilim 1)
- `audit_log` tablosu (yalnızca ekleme; additive şema): entries create/update/delete (LINE 取消・科目/税率 düzeltme dahil) ve invoices create/消込, aynı transaction'da önce/sonra JSON + actor (`WEB:<rol>:<hesap>` / `LINE` / kaynak). Değişmeyen düzeltme yazılmaz.
- API: `GET /api/v1/entries/{id}/history` (silinmiş kayıt dahil, tüm roller okur), `GET /api/v1/audit?entity=&action=&limit=`.
- CI `bot-postgres` kırmızıydı (main'de 2 test_companies hatası): conftest PG sıfırlaması account_companies/line_targets/user_prefs'i düşürmüyordu → eklendi.
- Kapı: pytest SQLite 548 geçti, PostgreSQL 16 ile 546 geçti/2 atlandı. 6 yeni test. T-064b → blocked (Q-16 fiyat; not: QUESTIONS'ta iki ayrı Q-16 var).
- Sonraki: T-065b (panel 履歴 + bank_tx), sonra P2 (T-017, T-050…).

## 2026-11-07 · developer (oturum) · T-056 + T-049 + T-034
- T-056: Resend (MAIL_PROVIDER=resend, MAIL_API_KEY, MAIL_FROM); hata sessiz, log maskeli. 3 test.
- T-049: 青色 控除 yıl bazlı (2027+: 75万 eklendi, 55万 kaldırıldı) — income.compute, /tax/income, /reports/blue-return.pdf, PDF dipnotu, panel seçenekleri. docs/DENCHOHO.md (優良 iddia edilmez), T-065 audit log açıldı.
- T-034: panel OCR görseli kaydediliyor (帳簿ごとの印 + doğrulama), kayda bağlanıyor; GET /entries/{id}/image; giderler listesinde görsel simgesi. 2 test. Toplam 536.
- Not: geliştirici zamanlanmış görevi 18:41'de ACCESS_DENIED ile başarısız (ürün sahibine bildirildi).

## 2026-11-07 · developer (oturum) · T-064 birden çok şirket
- Ürün sahibi isteği: hesap başına sınırsız şirket (fiyat kuralı Q-16'ya bırakıldı). `account_companies` + `line_targets`; companies.py sahiplik yardımcıları; team.resolve/switch/join/list_members, şifre sıfırlama (tüm şirket oturumları), link-line koruması.
- POST /companies; panel üst menüde 「事業所を追加」 → yeni şirket + /welcome. LINE 「会社」/「şirket」: kayıt yeri seçimi (yalnızca sahip olunan şirketler), cevapta ［şirket adı］.
- 6 test + yerel canlı uçtan uca (kayıt → şirket ekle → geçiş) ekran görüntüsüyle kontrol. Toplam 528.

## 2026-11-07 · developer (oturum) · AI okuma seçeneği + tahmini ücret
- Ürün sahibi isteği: market fişlerinde yapay zekâ seçeneği ve tahmini ücret. Kullanıcı başına `user_prefs.receipt_reader` ('' / ocr / ai / auto).
- `bot/ai_usage.py`: görsel token = ⌈w/28⌉×⌈h/28⌉ (resmi Vision dokümanı), fiyat env (AI_PRICE_INPUT/OUTPUT_USD_PER_MTOK, USD_JPY; varsayılan Sonnet 5.5 $2/$10, ¥155), gönderim öncesi küçültme (fiş 1600px, 仕切書 2000px), gerçek usage kaydı (`ai_usage` tablosu), 5 kayıttan sonra gerçek ortalama.
- API GET/PUT /settings/ai; LINE 「読取設定」/「okuma ayarı」; panel 設定'de kart. 6 test.

## 2026-11-07 · developer (oturum) · T-063 登録番号の確認
- Resmi şartname (k-web-api-kinou.pdf): GET web-api.invoice-kohyo.nta.go.jp/1/num?id&number(≤10, virgüllü)&type=21&history=0.
- Kimlik yokken biçim + kontrol hanesi; NTA_INVOICE_APP_ID (yoksa NTA_APP_ID) ile valid/expired/notfound. counterparties'e 3 sütun.
- POST /counterparties/verify; panel /passbook'ta rozet + 「登録番号を確認」. 1 test (mock).

## 2026-11-07 · developer (oturum) · T-057 + T-012b
- render.yaml `OCR_ENGINE=tesseract` (レシート AI なし). AI yalnızca 仕切書/通帳.
- 弥生 CSV: resmi 25 項目 (識別フラグ…調整), başlıksız, 税区分 resmi yazım (課税売上込10% / 課対仕入込軽減8% / 非課売上), インボイス 「適格」/「区分70%」 (経過措置 oranı tarihten).
- freee: resmi 取引インポート sütunları, tarih YYYY/MM/DD, 決済 boş. Banka kaynaklı kayıtlar karşı hesap 普通預金, 受取利息 → 非課売上.
- MF doğrulanamadı → T-012c. 515 test.
## 2026-11-07 23:46 JST · developer · T-044b /welcome kurulum sihirbazı
- Yeni `/welcome/` (3 adım, adım göstergesi, `?step=` ile yenilemede korunur, her adım 「あとで」 ile atlanır, sonunda ホーム): 1 事業者情報 (PUT /profile, 登録番号 チェックデジット), 2 LINE 連携 (tk_ kodu → POST /auth/link-line; `NEXT_PUBLIC_LINE_ADD_URL` varsa 友だち追加 bağlantısı), 3 最初の領収書 (経費精算'e bağlantı / LINE ile gönderme).
- `/signup` artık `/connect/?welcome=1` yerine `/welcome/`'a yönlendiriyor; davet kodu bekleyen kayıt eskisi gibi `/join/` (sihirbaz yok). Canlı oturumda accountant/viewer gelirse ホーム'a yönlendirilir; demo (token yok) statik, API çağrısı yok.
- Yorum: LINE bağlanınca oturum LINE defterine geçtiği için adım 1 bilgisi kaybolurdu → LINE defterinde 事業者名 boşsa taslak oraya yazılıyor, doluysa LINE'daki korunuyor (`lib/welcome.ts` `profileAfterLink`).
- Kapı: pytest 514 geçti; `next build` + check:tax/legal/team/lp + yeni `check:welcome` (CI'a eklendi) yeşil. Playwright demo akışı 375/1280px: taşma yok, konsol hatası yok. ja/tr/en metinler eklendi.
- Sonraki: T-049 (青色申告特別控除 令和9年分以後), sonra T-056 / T-057 / T-063.

## 2026-11-07 · developer (oturum) · T-061/T-062 通帳取込・取引先照合
- Ürün sahibi isteği: banka defteri (通帳) LINE'dan/panelden → firma resmi adı + 登録番号 + 勘定科目 → kontrol → resmi muhasebe. Karar: AI ile okuma + banka CSV.
- `bot/passbook.py` (PDF/foto → AI → bakiye kontrolü → bank_tx, görsel saklanmaz), `bot/counterparties.py` (kana anahtar, Excel'den rehber, öğrenme, 国税庁 API NTA_APP_ID ile).
- API: /bank/passbook, /bank/review, PATCH /bank/{id}, /bank/{id}/confirm, /bank/confirm-matched, /counterparties(+import, lookup), /reports/bank.xlsx. Panel /passbook. 15 test (kurgusal veri).
- Açık: NTA_APP_ID başvurusu (ürün sahibi), ANTHROPIC_API_KEY girilmesi.

## 2026-11-07 · developer (oturum) · T-060 仕切書
- Ürün sahibi isteği: el yazısı hurda satış fişleri (仕切書) LINE'dan → onay kuyruğu → 売上. AI yalnızca bu fişlerde (anahtar yoksa elle giriş).
- `bot/slips.py` + `slips` tablosu; API /slips (liste, PATCH, approve, reject, image, upload) + /reports/slips.pdf (ürün sahibinin örneğiyle aynı düzen).
- LINE: 「仕切書」/「Hurda fişi」 komutu 30 dk mod; OCR başarısız + basılı anahtar kelime (様, 盗難品, 仕切…) → otomatik kuyruk.
- Panel `/slips`: görsel + düzenlenebilir tablo, kg×fiyat ve toplam kontrolü, mükerrer uyarısı, onay/ret, PDF. 14 test.

## 2026-11-07 22:43 JST · developer · T-059 CSV formül enjeksiyonu (review-fix)
- Ortak yardımcı `export.csv_cell` (baştaki `=+-@`/TAB/CR → `'`; int/None dokunulmaz); `archive._cell` buna bağlandı.
- `export.to_csv(..., escape_formulas=True)`: 取引先/摘要, 勘定科目, 備考 nötrlenir, giriş dict'i değişmez, 金額 (negatif dahil) sayı kalır. ZIP `entries.csv` bunu kullanıyor.
- Yorum: freee/MF/弥生 içe aktarımının `'`'yu kabul ettiği doğrulanamadı → kabul ölçütü gereği `/export.csv` değişmedi; karar Q-17 (yeni).
- Kapı: pytest 485 geçti (yeni 11). dashboard-next değişmedi.
- Sonraki: T-044b (/welcome sihirbazı), sonra T-049.

## 2026-11-07 21:46 JST · developer · T-044 tanıtım sayfası /lp
- Yeni `/lp/` (sunucu bileşeni, JS'siz okunur): kahraman (LINEに送るだけ → 帳簿・インボイス・確定申告), 3 özellik, 「LINEで始める3ステップ」, fiyat tablosu (Free/個人¥980/法人¥2,980 税抜), 7 soruluk SSS (`<details>`, 税理士法 notu), alt bilgide yasal bağlantılar; CTA 「無料で始める」 → /signup/.
- Yorum: statik export → fiyatlar API'den değil `app/lib/lp.ts` `LP_PLANS`'tan; `bot/billing.py` ile eşitlik iki yerde denetleniyor (`npm run check:lp`, `tests/test_lp_plan_parity.py`). Yalnızca çalışan özellikler yazıldı (WhatsApp canlı değil, 電帳法 T-034'e kadar yok, e-Tax gönderimi yok denildi).
- 「LINEで友だち追加」 düğmesi `NEXT_PUBLIC_LINE_ADD_URL` (render.yaml'a `sync: false`, yalnızca https lin.ee/line.me) → Q-16 değer girilmeli.
- Kapı: pytest 474 geçti (yeni 2, rebase sonrası); `next build` + check:tax/legal/team/lp yeşil. Playwright: 375px (JS kapalı) ve 1280px'te yatay taşma yok, konsol hatası yok.
- Sonraki: T-044b (/welcome sihirbazı), sonra T-049.

## 2026-11-07 21:45 JST · reviewer · son 13 saat (T-055, T-058, T-011, T-046, T-046b, LINE secret/teşhis/rich menu)
- İncelenen: c4ce6cc..558f349 (8 kod commit'i). Kapı başta yeşil (468). Vergi oranı/eşiği ekleyen commit yok; T-055 fiyatları Q-11 cevabıyla uyumlu (税抜).
- Düzeltme: ZIP `invoices.csv` 取引先 alanında CSV formül enjeksiyonu (`=HYPERLINK…`) → `archive._cell` baştaki `=+-@` için `'` ekler. Aynı sorun `/export.csv` ve ZIP `entries.csv`'de → **T-059 review-fix (P2)** açıldı (içe aktarma uyumu doğrulanmalı).
- Yeni testler (+4): invoices.csv formül nötrleme; `ensure_default` 401'de menü oluşturmaz; açılış kancası `RICHMENU_AUTO=0`/token yokken LINE API çağırmaz; S3 404'te eski yerel fiş okunur.
- Not (düşük): `/` sağlık ucu `line_secret_len`/`line_token_len`/`version` herkese açık — değer sızmıyor, teşhis bittiğinde kaldırılabilir. `storage.get` henüz hiçbir uçta kullanılmıyor (T-034 bekliyor).
- Kapı: pytest 472 geçti. dashboard-next değişmedi.

## 2026-11-07 20:47 JST · developer · T-046b hesap silme talebi
- Yeni `deletion_requests` tablosu (ekleyici, `UNIQUE(user_id)`) + `bot/deletion.py`. `GET/POST /api/v1/account/delete-request` yalnızca owner (accountant/viewer 403); POST 202, tekrar POST idempotent (`created:false`, eşzamanlıda `ON CONFLICT DO NOTHING`). **Veri silinmez**; `cancelled` talep yeniden `pending` olabilir.
- `billing_active` bayrağı (ücretli plan yenilenecekse true). Yorum: talebi engellemiyor, panel önce 解約 uyarısı + 料金プラン bağlantısı gösteriyor. Operatör için `GET /admin/deletion-requests` (X-Admin-Key).
- Panel 設定: 「アカウントの削除」 kartı — 2 adımlı onay (「削除」 yazınca etkin), 「申請済み」 + tarih, ja/tr/en; owner dışı rollerde gizli. docs/OPERATIONS.md (yeni, elle işlem adımları) + docs/API.md.
- Kapı: pytest 466 geçti (yeni 8); `next build` + check:tax/legal/team yeşil; demo modda kart Playwright ile denendi.
- Yeni soru Q-15 (silme süresi / saklama yükümlülüğü / geri alma). Sonraki: T-044 (/lp), T-044b (/welcome).

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
