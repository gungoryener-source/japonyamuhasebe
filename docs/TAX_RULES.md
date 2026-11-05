# Japonya vergi kuralları (ürün içinde kullanılanlar)

Kural: koddaki her oran/eşik/tarih burada **kaynak + kontrol tarihi** ile bulunur. Güncelleyen: `agents/tax-watcher.md`.
Durum etiketleri: ✅ birincil kaynakla doğrulandı · ⚠️ ikincil kaynak / yorum gerekiyor · ❓ doğrulanmadı.

## 1. 消費税 (Tüketim vergisi)
| Kural | Değer | Durum | Kaynak · kontrol |
|---|---|---|---|
| Standart oran | 10%（国税7.8% + 地方2.2%） | ✅ | nta.go.jp 消費税 · 2026-11-05 |
| İndirimli oran (飲食料品・新聞) | 8%（国税6.24% + 地方1.76%） | ✅ | nta.go.jp 軽減税率制度 · 2026-11-05 |
| KDV dahil tutardan vergi | `floor(gross × r / (100 + r))` (請求書単位, 税率ごとに1回端数処理) | ✅ | インボイス制度 Q&A · 2026-11-05 |
| 2割特例 (免税→課税 olanlar) | 納付税額 = 売上税額 × 20%. **令和5年〜令和8年** (2023-10-01〜2026年分/期) | ✅ | [NTA 2割特例](https://www.nta.go.jp/taxes/shiraberu/zeimokubetsu/shohi/keigenzeiritsu/invoice_2tokurei.htm) · 2026-11-05 |
| 3割特例 (令和8年度改正) | 納付税額 = 売上税額 × 30%. **令和9年・令和10年分, yalnızca 個人事業者** (法人 hariç) | ✅ | 同上 · [弥生 解説](https://www.yayoi-kk.co.jp/kaiketsu/invoice/zeiseikaisei-r8/) · 2026-11-05 |
| 簡易課税 みなし仕入率 | 第1種90 / 第2種80 / 第3種70 / 第4種60 / 第5種50 / 第6種40 % · 基準期間課税売上 ≤ 5,000万円 | ❓ | tax-watcher doğrulamalı |

### 免税事業者等からの仕入 経過措置 (令和8年度改正後) — **ÖNEMLİ DEĞİŞİKLİK**
| Alım tarihi (課税仕入れの日) | 控除割合 |
|---|---|
| 2023-10-01 〜 2026-09-30 | 80% |
| 2026-10-01 〜 2028-09-30 | **70%** (eski kural 50% idi) |
| 2028-10-01 〜 2030-09-30 | 50% |
| 2030-10-01 〜 2031-09-30 | 30% |
| 2031-10-01 〜 | 0% (控除不可) |
- Tek bir muaf satıcıdan alım üst sınırı (税込): 2026-10-01 öncesi başlayan dönemler 10億円, sonrası **1億円**.
- Durum ✅ (ikincil kaynaklar tutarlı; birincil metin: 令和8年度改正法) · Kaynaklar: [弥生](https://www.yayoi-kk.co.jp/kaiketsu/invoice/zeiseikaisei-r8/), [山田&パートナーズ](https://www.yamada-partners.jp/reform/r8/c01-2-revision-of-transitional-tax-credit-measures-for-taxable-purchases-from-tax-exempt-businesses?hsLang=ja-jp), [税務研究会](https://www.zeiken.co.jp/zeikenpress/column/0014zp20260301/) · kontrol 2026-11-05
- ⚠️ `web/index.html` ve `web/dashboard.html` prototipleri hâlâ eski 50% kuralını gösteriyor → BACKLOG T-001.

## 2. 所得税 (Gelir vergisi, bireyler)
| Kural | Değer | Durum | Kaynak · kontrol |
|---|---|---|---|
| Oran dilimleri (課税所得) | ≤195万 5% · ≤330万 10% (−97,500) · ≤695万 20% (−427,500) · ≤900万 23% (−636,000) · ≤1,800万 33% (−1,536,000) · ≤4,000万 40% (−2,796,000) · üstü 45% (−4,796,000); 課税所得は1,000円未満切捨て | ✅ | nta.go.jp タックスアンサー No.2260 · 2026-11-05 |
| 復興特別所得税 | 基準所得税額 × 2.1% (2037年分まで) | ✅ | nta.go.jp · 2026-11-05 |
| 青色申告特別控除 | 65万 (複式簿記 + e-Tax veya 優良電子帳簿) / 55万 / 10万 | ✅ | nta.go.jp No.2072 · 2026-11-05 |
| 基礎控除 令和7年分 (2025) | 合計所得 ≤132万: 95万 · ≤336万: 88万 · ≤489万: 68万 · ≤655万: 63万 · ≤2,350万: 58万 · ≤2,400万: 48万 · ≤2,450万: 32万 · ≤2,500万: 16万 · 超: 0 | ✅ | [NTA No.1199](https://www.nta.go.jp/taxes/shiraberu/taxanswer/shotoku/1199.htm) · 2026-11-05 |
| 基礎控除 令和8年分 (2026) — 令和8年度改正 | ≤2,350万 için **104万** görünüyor (2,350万超 kademeleri aynı); 令和10年分以後 farklı tablo. Yürürlük 2026-12-01 (2026年分に適用) | ⚠️ | NTA No.1199 tablosu birleşik hücreli; **Q-03** ile doğrulanacak |

## 3. 源泉所得税 / takvim (3月決算法人 ve bireyler)
| Olay | Tarih | Durum |
|---|---|---|
| 源泉所得税 aylık納付 | ertesi ayın 10'u (納期の特例: 7/10 ve 1/20) | ✅ |
| 個人 確定申告 | 2/16 〜 3/15 (2026年分 → 2027-02-16 〜 2027-03-15) | ✅ |
| 個人 消費税 申告 | 3/31 | ✅ |
| 法人税・消費税 確定申告 | 決算日翌日から2ヶ月 (3月決算 → 5/31) | ✅ |

## 4. インボイス / 電子帳簿保存法
- 登録番号 formatı: `T` + 13 hane (法人番号 veya 個人用番号). Doğrulama: 国税庁 適格請求書発行事業者公表システム Web-API (uygulama ID gerekir → `NTA_APP_ID`). ✅
- 適格請求書 zorunlu alanlar: 発行者名+登録番号, 取引年月日, 取引内容 (軽減対象の明示), 税率ごとの対価合計と適用税率, 税率ごとの消費税額, 交付先名. ✅
- 電子取引データ保存: 真実性 (タイムスタンプ veya 訂正削除履歴 veya 事務処理規程) + 可視性 (取引年月日・金額・取引先で検索). 保存期間: 法人7年 (欠損金 10年), 個人 7年/5年. ⚠️ ayrıntı tax-watcher

## 5. Takvim (önümüzdeki 60 gün) — tax-watcher günceller
- 2026-11-10 源泉所得税 (10月分)
- 2026-11-30 消費税 中間申告 (該当法人)
- 2026-12-01 令和8年度改正 基礎控除 yürürlük (2026年分)
- 2026-12-10 源泉所得税 (11月分)
- 2027-01-20 源泉所得税 納期の特例 (下期)
