# Japonya vergi kuralları (ürün içinde kullanılanlar)

Kural: koddaki her oran/eşik/tarih burada **kaynak + kontrol tarihi** ile bulunur. Güncelleyen: `agents/tax-watcher.md`.
Durum etiketleri: ✅ birincil kaynakla doğrulandı · ⚠️ ikincil kaynak / yorum gerekiyor · ❓ doğrulanmadı.

## 1. 消費税 (Tüketim vergisi)
| Kural | Değer | Durum | Kaynak · kontrol |
|---|---|---|---|
| Standart oran | 10%（国税7.8% + 地方2.2%） | ✅ | nta.go.jp 消費税 · kontrol: 2026-11-05 (令和8年度改正で変更なし) |
| İndirimli oran (飲食料品・新聞) | 8%（国税6.24% + 地方1.76%） | ✅ | nta.go.jp 軽減税率制度 · 2026-11-05 |
| KDV dahil tutardan vergi | `floor(gross × r / (100 + r))` (請求書単位, 税率ごとに1回端数処理) | ✅ | インボイス制度 Q&A · 2026-11-05 |
| 2割特例 (免税→課税 olanlar) | 納付税額 = 売上税額 × 20%. 個人: **令和8年分の確定申告まで**; 法人: 2026-09-30 を含む課税期間まで. Şart: 基準期間 課税売上高 ≤ 1,000万 **ve** 特定期間 (個人: 前年1〜6月) 課税売上高 ≤ 1,000万 — 特定期間は売上高に代えて 給与等支払額 ile de判定 (消法9の2①); ayrıca 課税期間短縮, 相続・合併・分割, 新設法人, 高額特定資産・調整対象固定資産 nedeniyle課税 olanlar hariç (登録がなければ免税だった事業者) | ✅ | [NTA 2割特例](https://www.nta.go.jp/taxes/shiraberu/zeimokubetsu/shohi/keigenzeiritsu/invoice_2tokurei.htm), [NTA お知らせ 令和8年度改正特集](https://www.nta.go.jp/taxes/shiraberu/zeimokubetsu/shohi/keigenzeiritsu/pdf/0026004-066_01.pdf) · kontrol: 2026-11-06; 特定期間: [NTA インボイスQ&A 問115](https://www.nta.go.jp/taxes/shiraberu/zeimokubetsu/shohi/keigenzeiritsu/pdf/qa/115.pdf), [NTA 2割特例 適用可否フローチャート](https://www.nta.go.jp/taxes/shiraberu/zeimokubetsu/shohi/keigenzeiritsu/pdf/0024003-131.pdf) · kontrol: 2026-11-08 (T-066) |
| 3割特例 (令和8年度改正) | 納付税額 = 売上税額 × 30% (控除 = 売上税額 × 70%). **令和9年分・令和10年分, yalnızca 個人事業者** (法人不可). Şartlar: インボイス登録; 基準期間 (前々年) 課税売上高 ≤ 1,000万; 特定期間 (前年1〜6月) 課税売上高 (veya 給与) ≤ 1,000万; 課税期間短縮・相続・高額資産取得で課税事業者になった場合 hariç. Önceden 届出 gerekmez (申告書に付記) | ✅ | [NTA 3割特例 リーフレット](https://www.nta.go.jp/taxes/shiraberu/zeimokubetsu/shohi/keigenzeiritsu/invoice-review/pdf/0026004-099-01-2.pdf), [NTA 3割特例の創設](https://www.nta.go.jp/taxes/shiraberu/zeimokubetsu/shohi/keigenzeiritsu/invoice-review/pdf/0026002-095.pdf) · kontrol: 2026-11-06 |
| 簡易課税 みなし仕入率 | 第1種 卸売 90 / 第2種 小売・飲食料品の農林漁業 80 / 第3種 製造・建設等 70 / 第4種 その他(飲食店等) 60 / 第5種 運輸通信・金融保険・サービス 50 / 第6種 不動産 40 % · 基準期間課税売上 ≤ 5,000万円 · 選択届出書は適用課税期間の初日の前日まで | ✅ | [NTA No.6505](https://www.nta.go.jp/taxes/shiraberu/taxanswer/shohi/6505.htm) (令和8年4月1日現在法令等), [No.6509 事業区分](https://www.nta.go.jp/taxes/shiraberu/taxanswer/shohi/6509.htm) · kontrol: 2026-11-06 |

### 免税事業者等からの仕入 経過措置 (令和8年度改正後) — **ÖNEMLİ DEĞİŞİKLİK**
| Alım tarihi (課税仕入れの日) | 控除割合 |
|---|---|
| 2023-10-01 〜 2026-09-30 | 80% |
| 2026-10-01 〜 2028-09-30 | **70%** (eski kural 50% idi) |
| 2028-10-01 〜 2030-09-30 | 50% |
| 2030-10-01 〜 2031-09-30 | 30% |
| 2031-10-01 〜 | 0% (控除不可) |
- Oran, **課税仕入れの日** (alım tarihi) ile belirlenir.
- Tek bir muaf satıcıdan bir yılda/事業年度で経過措置 uygulanabilecek alım üst sınırı (税込): 2024-10-01〜2026-09-30 arasında başlayan課税期間 **10億円**, 2026-10-01 以後に開始する課税期間 **1億円** (aşan kısım控除不可). Kod: `transitional_cap_warnings` satıcı (取引先) bazında uyarı verir (T-050); aşan kısım `compute` içinde düşülmez, panelde uyarı olarak gösterilir.
- Durum ✅ (birincil kaynak) · Kaynaklar: [NTA お知らせ 経過措置が変わります](https://www.nta.go.jp/taxes/shiraberu/zeimokubetsu/shohi/keigenzeiritsu/pdf/0026004-066_02.pdf), [NTA インボイスQ&A 問113-3 / 経過措置](https://www.nta.go.jp/taxes/shiraberu/zeimokubetsu/shohi/keigenzeiritsu/pdf/qa/01-15.pdf) · ikincil: [弥生](https://www.yayoi-kk.co.jp/kaiketsu/invoice/zeiseikaisei-r8/) · kontrol: 2026-11-06
- `web/` prototipleri T-001 ile düzeltildi; motor: `bot/tax/consumption.py` `TRANSITIONAL_CREDIT` (tablo ile uyumlu, kontrol: 2026-11-06).

### 消費税申告書の計算手順 (T-070, kontrol: 2026-11-08)
Beyanname (第一表/第二表/付表) satırları **国税 (7.8% / 6.24%) ile 地方消費税'i ayrı** hesaplar. `consumption.compute` toplam oranla (10/8) yaklaşık hesap yapar; beyanname motoru (T-071) bu tabloya göre çalışır. Tüm ara hesaplarda 1円未満 kesirler **her adımda** atılır.

| # | Adım | Kural | Durum | Kaynak · kontrol |
|---|---|---|---|---|
| 1 | 課税標準額 (税率ごと) | 税込課税売上合計 × 100/110 (標準) · × 100/108 (軽減) → **千円未満切捨て** (第二表①, 付表 ①A/B) | ✅ | [NTA No.6371 端数計算](https://www.nta.go.jp/taxes/shiraberu/taxanswer/shohi/6371.htm) (令和8年4月1日現在法令等), [NTA 消費税のあらまし 端数計算](https://www.nta.go.jp/publication/pamph/shohi/aramashi/pdf/012.pdf), [付表 記載要領](https://www.nta.go.jp/taxes/tetsuzuki/shinsei/shinkoku/shohi/07/06.pdf) · 2026-11-08 |
| 2 | 課税標準額に対する消費税額 — 割戻し (原則) | 課税標準額 × 7.8% (標準) / 6.24% (軽減) → 1円未満切捨て | ✅ | No.6371, [NTA No.6383](https://www.nta.go.jp/taxes/shiraberu/taxanswer/shohi/6383.htm) · 2026-11-08 |
| 3 | 同 — 積上げ (特例) | 交付した適格請求書等の**写しを保存**している場合: 記載した消費税額等の合計 × 78/100 (1円未満切捨て). 売上側では取引ごとに割戻しと併用可 | ✅ | No.6383, あらまし 012 · 2026-11-08 |
| 4 | 仕入税額 — 積上げ (原則) | 受領した適格請求書等の消費税額等合計 × 78/100. 帳簿積上げ: 仕入ごとに 10/110 · 8/108 (切捨て/四捨五入) を仮払消費税とし合計 × 78/100 | ✅ | [NTA No.6351](https://www.nta.go.jp/taxes/shiraberu/taxanswer/shohi/6351.htm) (令和8年4月1日現在法令等) · 2026-11-08 |
| 5 | 仕入税額 — 割戻し (特例) | 税込課税仕入合計 × 7.8/110 · 6.24/108 (1円未満切捨て). **Yalnızca satış tarafı da割戻し ise**; 仕入側で積上げ ile併用不可 (売上 積上げ + 仕入 割戻し yasak) | ✅ | No.6351, No.6371 · 2026-11-08 |
| 6 | 経過措置 (免税事業者等からの仕入) | Seçilen yöntemle (割戻し/積上げ) aynı şekilde hesaplanır; **控除割合 (80/70/50/30) 税率ごとに en sonda** çarpılır | ✅ | [NTA 経過措置 計算資料](https://www.nta.go.jp/taxes/shiraberu/zeimokubetsu/shohi/keigenzeiritsu/pdf/0024002-044_130.pdf) (örnekler eski 80/50 tablosuyla; güncel oranlar yukarıdaki 経過措置 tablosunda) · 2026-11-08 |
| 7 | 売上返還等・貸倒れに係る税額 | 返還等/貸倒れ税込額 × 7.8/110 · 6.24/108 → 1円未満切捨て | ✅ | No.6371 · 2026-11-08 |
| 8 | 差引税額 (国税, 第一表⑨) | ② 消費税額 + ③ 控除過大調整税額 − ⑦ 控除税額小計 → **百円未満切捨て**. Eksi ise 控除不足還付税額 (1円未満切捨て; 1円未満の還付は1円) | ✅ | No.6371, [NTA 申告書(一般用)の書き方 令和7年10月1日以後終了課税期間](https://www.nta.go.jp/publication/pamph/shohi/kaisei/yoshiki/pdf/202411_01.pdf) ■7 · 2026-11-08 |
| 9 | 地方消費税 (譲渡割額, 第一表⑬) | 地方消費税の課税標準となる消費税額 (= 差引税額) × **22/78** → **百円未満切捨て**. Test vektörü (NTA 設例 甲野商店): 231,200 × 22/78 = 65,210 → **65,200** | ✅ | [NTA 確定申告の手引き 個人事業者用 step.17](https://www.nta.go.jp/publication/pamph/shohi_kojin/r05/pdf/02-07.pdf), 書き方 ■9, [NTA 軽減税率制度 税率表](https://www.nta.go.jp/taxes/shiraberu/zeimokubetsu/shohi/keigenzeiritsu/01.htm) (地方 = 消費税額の22/78) · 2026-11-08 |
| 10 | 納付税額 | 国税 差引税額 + 譲渡割額 (中間納付税額 varsa her biri ayrı düşülür) | ✅ | 書き方 (第一表 構成) · 2026-11-08 |
| 11 | 簡易課税 | 控除対象仕入税額 = 売上げに係る消費税額 × みなし仕入率 (tek 事業区分). 2+ 事業区分: 原則法 / 簡便法 / 75%特例 — **uygulanmadı** (tek 事業区分 varsayımı; panelde uyarı). 貸倒回収・返還等 terimlerinin formüldeki yeri No.6505'te yalnızca görsel → ⚠️ | ⚠️ | No.6505 (令和8年4月1日現在法令等; formül görsel, metin olarak doğrulanamadı) · 2026-11-08 |
| 12 | 2割特例 | 特別控除税額 = (課税標準額に対する消費税額 − 売上げに係る対価の返還等の金額に係る消費税額) × **80/100**; 付表6 kullanılır; 差引税額 = 第二表⑪ − 付表6⑦ − ⑰ (百円未満切捨て); 地方 = × 22/78 (百円未満切捨て) | ✅ | [NTA 確定申告の手引き 2割特例用 〈令和8年11月版〉](https://www.nta.go.jp/publication/pamph/pdf/0023008-043.pdf) · 2026-11-08 |
| 13 | 3割特例 (令和9・10年分) | Aynı yapı, oran **70/100** (納付 = 売上税額の3割). 令和9年分 申告書/付表 ve 手引き henüz yayımlanmadı (yalnızca R9.4.1以後終了課税期間用 **ドラフト版** 様式) → satır numaraları ⚠️ | ⚠️ | 3割特例 リーフレット (yukarıda), [NTA 申告書様式 ドラフト版](https://www.nta.go.jp/taxes/shiraberu/zeimokubetsu/shohi/keigenzeiritsu/pdf/0026010-002-01.pdf) · 2026-11-08 |
| 14 | 申告・納付期限 (個人) | 翌年3月31日 (令和7年分 → 令和8年3月31日) | ✅ | [NTA 広報 令和8年3月](https://www.nta.go.jp/publication/pamph/koho/campaign/r8/Mar/01.htm) · 2026-11-08 |

### 飲食料品 税率 1% (令和9年4月1日〜令和11年3月31日) — ⚠️ **法案成立前**
- 2026-09-15 閣議決定 「飲食料品消費税率の臨時的な引下げ…に関する大綱」: 現行の軽減税率対象 飲食料品 → **1% (国税 0.78% + 地方 0.22%)**, 2027-04-01〜2029-03-31. NTA 特設サイト açıldı; NTA No.6371 / No.6505 / 軽減税率 sayfaları 「引き下げられます」 notu taşıyor. Yan özel kurallar: 簡易課税'te 飲食料品 satış için 売上税額と同額の仕入控除, 届出 özel süreleri, 総額表示 özel dönemi (2027-02-01〜05-31), bazı sözleşmelerde 8% kalır.
- Durum ⚠️: kaynaklar (TKC 2026-11) 「今後、必要な法制上の措置等が講じられる予定」 diyor → **kod değiştirilmez**; yasa çıkınca tax-watcher ✅ yapar (T-079). Etki: `RATES`, OCR/parser 税率, CSV 税区分, 申告書 (付表 yeni sütun), 簡易課税.
- Kaynak: [NTA 軽減税率制度の概要 (引下げ notu)](https://www.nta.go.jp/taxes/shiraberu/zeimokubetsu/shohi/keigenzeiritsu/01.htm), [岡山市 NTA 特設サイト案内](https://www.city.okayama.jp/kurashi/0000085867.html), [TKC 2026-11](https://www.tkc.jp/ao/topics/202611_kaisei01) · kontrol: 2026-11-08

## 2. 所得税 (Gelir vergisi, bireyler)
| Kural | Değer | Durum | Kaynak · kontrol |
|---|---|---|---|
| Oran dilimleri (課税所得) | ≤195万 5% · ≤330万 10% (−97,500) · ≤695万 20% (−427,500) · ≤900万 23% (−636,000) · ≤1,800万 33% (−1,536,000) · ≤4,000万 40% (−2,796,000) · üstü 45% (−4,796,000); 課税所得は1,000円未満切捨て | ✅ | nta.go.jp タックスアンサー No.2260 · kontrol: 2026-11-05; 2026-11-06 [令和8年度大綱 概要](https://www.mof.go.jp/tax_policy/tax_reform/outline/fy2026/08taikou_gaiyou.htm) ile genel dilimlerde değişiklik olmadığı teyit edildi (yalnızca 極めて高い所得 特例 22.5%→30%, ürün kapsamı dışı) |
| 復興特別所得税 | 基準所得税額 × 2.1% (2037年分まで) | ✅ | nta.go.jp · kontrol: 2026-11-05 |
| 青色申告特別控除 — **令和8年分まで** | 65万 (正規の簿記 + e-Tax veya 優良電子帳簿) / 55万 (正規の簿記, 書面申告) / 10万 (簡易簿記) | ✅ | [NTA No.2072](https://www.nta.go.jp/taxes/shiraberu/taxanswer/shotoku/2072.htm) · kontrol: 2026-11-06 |
| 青色申告特別控除 — **令和9年分以後** (令和8年度改正) | **75万** (65万要件 + 優良な電子帳簿 veya デジタルシームレス保存 + 届出書) / 65万 (正規の簿記 + 期限内 e-Tax) / **55万 廃止** (書面申告 → 10万) / 10万 (簡易簿記; ancak 前々年分 事業・不動産 収入金額 > 1,000万 ise **0**) / 現金主義の特例: yalnızca 10万 | ✅ | [NTA リーフレット 青色申告特別控除](https://www.nta.go.jp/taxes/shiraberu/shinkoku/kojin_jigyo/0026007-003_02.pdf) · ikincil: [山田&パートナーズ](https://www.yamada-partners.jp/reform/r8/k08-revision-of-special-deduction-for-blue-tax-returns) · kontrol: 2026-11-06 → BACKLOG T-049 |
| 基礎控除 令和7年分 (2025) | 合計所得 ≤132万: 95万 · ≤336万: 88万 · ≤489万: 68万 · ≤655万: 63万 · ≤2,350万: 58万 · ≤2,400万: 48万 · ≤2,450万: 32万 · ≤2,500万: 16万 · 超: 0 | ✅ | [NTA No.1199](https://www.nta.go.jp/taxes/shiraberu/taxanswer/shotoku/1199.htm) · kontrol: 2026-11-05 |
| 基礎控除 令和8年分・令和9年分 (2026, 2027) — 令和8年度改正 | 本則 62万 (≤2,350万; 58万→62万) + 特例 (措法41の16の2): ≤489万 +42万, 489万超〜655万 +5万. → 合計所得 **≤489万: 104万 · ≤655万: 67万 · ≤2,350万: 62万** · ≤2,400万: 48万 · ≤2,450万: 32万 · ≤2,500万: 16万 · 超: 0. 施行 2026-12-01, 令和8年分以後に適用 (年末調整で精算). 非居住者: 62万 | ✅ | [NTA 令和8年分 年末調整のしかた「昨年と比べて変わった点」](https://www.nta.go.jp/publication/pamph/gensen/nencho2026/pdf/102.pdf) (注: 「62万円にそれぞれ42万円、5万円、37万円を加算」; 489万超655万以下 67万 · 655万超2,350万以下 62万), [財務省 令和8年度税制改正の大綱](https://www.mof.go.jp/tax_policy/tax_reform/outline/fy2026/20251226taikou.pdf) (本則 +4万; 特例 42万/5万, 上限 655万), [NTA No.1199](https://www.nta.go.jp/taxes/shiraberu/taxanswer/shotoku/1199.htm) (令和8年4月1日現在法令等, 根拠 所法86・措法41の16の2) · ikincil tutarlı: [マネーフォワード](https://biz.moneyforward.com/payroll/basic/111924/) · kontrol: 2026-11-06 · **Q-03 kapandı** |
| 基礎控除 令和10年分以後 (2028〜) | ≤132万: **99万** (62万 + 37万) kesin. 132万超 kademeleri: 大綱'a göre 62万 (特例上限 132万); NTA No.1199 tablosu 489万超〜655万 için 67万 gösteriyor gibi — birleşik hücre okuması belirsiz | ⚠️ | NTA No.1199, 年末調整のしかた 102.pdf, 大綱 · kontrol: 2026-11-06 · koda ekleme (2028年分 henüz gerekli değil); bir sonraki tax-watcher çalışmasında No.1199 metniyle doğrula |
| 給与所得控除 最低保障額 (参考; ürün 給与所得 hesaplamıyor) | 65万 → 69万 (本則) + 令和8・9年分 特例 +5万 = **74万** | ✅ | [NTA 102.pdf](https://www.nta.go.jp/publication/pamph/gensen/nencho2026/pdf/102.pdf), [大綱 概要](https://www.mof.go.jp/tax_policy/tax_reform/outline/fy2026/08taikou_gaiyou.htm) · kontrol: 2026-11-06 |

### 減価償却 (個人事業者, T-073, kontrol: 2026-11-08)
Motor kapsamı (T-074): **平成19年4月1日以後に取得**, **定額法**, 月割, 備忘価額1円, 一括償却資産, 少額減価償却資産の特例. 定率法・旧定額法・除却/売却・特別償却は **uygulanmadı** (kayıt reddedilir veya uyarı). Parametreler: `bot/tax/params/depreciation.toml`.

| Kural | Değer | Durum | Kaynak · kontrol |
|---|---|---|---|
| 定額法 | 各年の償却費 = 取得価額 × 定額法の償却率 | ✅ | [NTA No.2106](https://www.nta.go.jp/taxes/shiraberu/taxanswer/shotoku/2106.htm) (令和8年4月1日現在法令等) · 2026-11-08 |
| 月割 | 取得/事業供用の年は 12 で割り、**その年に業務に使用した月数**を掛ける (月の途中は1か月として数える) | ✅ | No.2106; [NTA 確定申告の手引き 償却期間](https://www.nta.go.jp/taxes/shiraberu/shinkoku/tebiki/2021/pdf/041.pdf) · 2026-11-08 |
| 備忘価額 | 有形減価償却資産は取得価額から **1円**を控除した額まで償却 (最終年 = 期首帳簿価額 − 1円) | ✅ | No.2106 · 2026-11-08 |
| 償却率 | 別表第八 (定額法). 耐用年数2〜12 の値 0.500 / 0.334 / 0.250 / 0.200 / 0.167 / 0.143 / 0.125 / 0.112 / 0.100 / 0.091 / 0.084 は 2 つの二次資料と一致し、`ceil(1000/耐用年数)/1000` の規則と整合. 一次資料 (e-Gov 耐用年数省令 別表八) は**この環境から取得できず未照合** | ⚠️ | 二次: [創業手帳](https://sogyotecho.jp/genkashoukyaku-taiyounensu/), [luft](https://www.luft.co.jp/cgi/depreciation.php); 一次 (要照合): [e-Gov 340M50000040015 別表八](https://elaws.e-gov.go.jp/search/elawsSearch/elaws_search/lsg0500/detail?lawId=340M50000040015) · 2026-11-08 |
| 建物・建物附属設備・構築物 | 定額法のみ (建物: 平成10年4月以後取得 / 附属設備・構築物: 平成28年4月以後取得). 個人は届出がなければ定額法 (定率法は届出が必要) | ✅ | No.2105 注2・注3, No.2106 · 2026-11-08 |
| 10万円未満 | 全額を取得した年に必要経費 (固定資産台帳の対象外) | ⚠️ | 二次: [マネーフォワード](https://biz.moneyforward.com/accounting/basic/65238/) (所令138) · 2026-11-08 |
| 一括償却資産 | 取得価額 10万円以上 **20万円未満**: 3年間で 1/3 ずつ必要経費 (月割なし) | ⚠️ | 二次: [マネーフォワード](https://biz.moneyforward.com/accounting/basic/79255/) (所令139) · 2026-11-08 |
| 少額減価償却資産の特例 (措法28の2) | 青色申告者. 取得価額 **30万円未満** (令和8年3月31日以前取得) / **40万円未満** (令和8年4月1日以後取得), 年間合計 **300万円**まで. 適用期限 **令和11年3月31日**まで (令和8年度改正) | ✅ | [中小企業庁 リーフレット 令和8年5月](https://www.chusho.meti.go.jp/zaimu/zeisei/pamphlet/syougaku_shisan.pdf), [弥生 2026-04-07](https://www.yayoi-kk.co.jp/lawinfo/detail.20260407/), [dosai.jp](https://dosai.jp/news/shougaku-genka-shokyaku-40man-2026/) · 2026-11-08 |
| 事業専用割合 | 事業と家事の両方に使う資産は、償却費に事業専用割合を乗じた額が必要経費 (決算書 ㋠ 欄) | ✅ | NTA 手引き (上記 PDF) · 2026-11-08 |
| 端数 | 1円未満切捨てとして実装 (一括償却の第3年は残額) | ⚠️ | 規定の明記を未確認 (TODO(verify)) |

## 3. 源泉所得税 / takvim (3月決算法人 ve bireyler)
| Olay | Tarih | Durum |
|---|---|---|
| 源泉所得税 aylık納付 | ertesi ayın 10'u (土日祝 → 翌営業日; 納期の特例: 7/10 ve 1/20) | ✅ (kontrol: 2026-11-06) |
| 年末調整分 源泉所得税 (令和8年分) | 通常 **2027-01-12 (火)** · 納期の特例 **2027-01-20 (水)** | ✅ [NTA](https://www.nta.go.jp/users/gensen/nencho/pdf/02.pdf) · kontrol: 2026-11-06 |
| 所得税 予定納税 第2期 (令和8年分) | 2026-11-02 〜 **2026-11-30 (月)** (振替日 同日) | ✅ [NTA](https://www.nta.go.jp/publication/pamph/koho/campaign/r8/Nov/02.htm) · kontrol: 2026-11-06 |
| 個人 確定申告 | 2/16 〜 3/15 (2026年分 → 2027-02-16 〜 2027-03-15) | ✅ (kontrol: 2026-11-06) |
| 個人 消費税 申告 | 3/31 | ✅ (kontrol: 2026-11-06) |
| 法人税・消費税 確定申告 | 決算日翌日から2ヶ月 (3月決算 → 5/31) | ✅ (kontrol: 2026-11-06) |

## 4. インボイス / 電子帳簿保存法
- 登録番号 formatı: `T` + 13 hane (法人番号 veya 個人用番号). Doğrulama: 国税庁 適格請求書発行事業者公表システム Web-API (uygulama ID gerekir → `NTA_APP_ID`). ✅
- 適格請求書 zorunlu alanlar: 発行者名+登録番号, 取引年月日, 取引内容 (軽減対象の明示), 税率ごとの対価合計と適用税率, 税率ごとの消費税額, 交付先名. ✅
- 電子取引データ保存 (令和6年1月〜): 真実性 (タイムスタンプ veya 訂正削除履歴の残るシステム veya 不当な訂正削除の防止に関する事務処理規程) + 可視性 (ディスプレイ・説明書の備付け + 「取引年月日・金額・取引先」で検索). **検索要件不要**: 2課税年度前 (基準期間) の売上高 ≤ 5,000万 **veya** 出力書面を日付・取引先ごとに整理 — her iki durumda da 「ダウンロードの求め」に応じられること. **猶予措置**: 税務署長が相当の理由を認め + ダウンロード・出力書面の提示に応じられる場合, 保存のみで可 (事前申請不要). 宥恕措置 2023-12-31 終了. ✅ [NTA 令和6年1月からの電子取引データの保存方法](https://www.nta.go.jp/law/joho-zeikaishaku/sonota/jirei/tokusetsu/pdf/0023011-012.pdf) · kontrol: 2026-11-06
- 保存期間: 法人7年 (欠損金 10年), 個人 7年/5年. ⚠️ bu çalışmada birincil kaynakla yeniden doğrulanmadı
- 優良な電子帳簿: 令和9年分以後 青色 75万 şartı (yukarıda §2). Ürün 優良 şartlarını (訂正削除履歴, 相互関連性, 検索) karşılıyor mu → T-049 kapsamında değerlendirilecek.

## 5. Takvim (önümüzdeki 60 gün: 2026-11-06 → 2027-01-05) — tax-watcher günceller · kontrol: 2026-11-06
- 2026-11-10 (火) 源泉所得税 (10月分) 納付
- 2026-11-30 (月) 所得税 予定納税 第2期 納期限 ([NTA](https://www.nta.go.jp/publication/pamph/koho/campaign/r8/Nov/02.htm))
- 2026-11-30 (月) 9月決算法人 確定申告 / 3月決算法人 中間申告 (消費税 中間申告 該当法人)
- 2026-12-01 (火) 令和8年度改正 施行: 基礎控除 62万/67万/104万 + 給与所得控除 最低保障 74万 (令和8年分に適用, 12月の年末調整で精算)
- 2026-12-10 (木) 源泉所得税 (11月分) 納付
- 2026-12 年末調整 (改正後の基礎控除で年税額計算)
- 60 gün sonrası, yakın: 2027-01-12 (火) 源泉 (12月分・年末調整分) · 2027-01-20 (水) 納期の特例 (7〜12月分) · 2027-02-01 (月) 法定調書・給与支払報告書・償却資産申告 (1/31 日曜) · 2027-02-16〜03-15 確定申告 (令和8年分; 2割特例の最終年分) · 2027-03-31 個人 消費税
