# e-Tax 青色申告決算書（一般用）— 様式ID・バージョン・項目対応表 (T-067)

Kontrol tarihi: **2026-11-09**. Kod yok; bu belge T-068 (.xtx üretimi) için girdidir.
Kaynak: 国税庁 e-Tax仕様書 (https://www.e-tax.nta.go.jp/shiyo/ksk2/ksk2_shiyo3.htm), ürün sahibi onayı Q-19 (2026-11-08) ile indirilen üç arşiv:
項番7 手続一覧・手続内帳票対応表・対象帳票一覧 (令和8年8月28日) · 項番9 XML構造設計書及び帳票フィールド仕様書【所得税関係】 (令和8年1月30日) · 項番19 XMLスキーマ (令和8年8月28日).
Dosyalar depoya **konmadı** (yeniden dağıtım yok); tablo bu dosyalardan elle/script ile çıkarıldı. Seviye: ✅ 仕様書'den doğrudan · ⚠️ çıkarım / doğrulanmadı.

## 1. Kimlik ✅
| Öğe | Değer | Kaynak dosya |
|---|---|---|
| 帳票 | 年分青色申告決算書（一般用） | `帳票フィールド仕様書(所得-申告)Ver11x.xlsx` シート `KOA210` |
| 様式ID | **KOA210** | 同上、手続内帳票対応表(申告) Ver250x |
| 帳票バージョン | **11.0** (XSD `KOA210-011.xsd`, 2023-09-27; 仕様書 Ver11x'ten beri değişmedi, 対応表 Ver230x〜Ver250x hepsinde 11.0) | `KOA210-011.xsd` içindeki `version：11.0` |
| 手続 | **RKO0010** 所得税及び復興特別所得税申告 (XSD `RKO0010-250.xsd`, 手続一覧 Ver250x/260x; 令和7年度) | 手続一覧（申告）Ver260x |
| 帳票セット内の位置 | 任意帳票（△）、複数帳票（2）— 申告書B(第一表・第二表, **KOA020 v23.0**) ile birlikte gönderilir | 手続内帳票対応表(申告）Ver250x |
| 名前空間 / 要素 | `http://xml.e-tax.nta.go.jp/XSD/shotoku`, kök grup `KOA210-11-0group`, öğe `<KOA210>`, alanlar `<AMFxxxxx>` (tutar türü `gen:kingaku`) | `KOA210-011.xsd` |
| 面 | 4面: 損益計算書 / 月別・仕入 / 減価償却・内訳 / 貸借対照表 (+ 製造原価 AMH) | 対象帳票一覧（申告）Ver11x |

⚠️ **Taslak (ドラフト版)**: 令和9年1月4日受付開始予定の güncelleme taslağı (令和8年10月30日) **indirilmedi**. 申告書 yılı 2026 için kesin sürüm yukarıdaki; 2027 yılı için (75万 青色控除 vb.) taslağa bakılmalı → T-068 öncesi tekrar kontrol.
⚠️ Sonraki 申告 yılında 様式 versiyonu artabilir; XSD `version` ve 対応表 her yıl yeniden okunmalı.

## 2. /api/v1/pl ↔ KOA210 alan eşlemesi (損益計算書, 面1) ✅
Form 項番 (reports.py FIXED/FREE_SLOTS ile aynı numaralar) → XML etiketi. Tutarlar **税込経理** (mevcut davranış), 整数円, `0≦x`.

| Bizde (`pl`) | 決算書 項番 | XML | Not |
|---|---|---|---|
| 売上高 (inc) | ① 売上（収入）金額 | `AMF00100` | ayrıca aylık toplamlar `AMF00600…AMF00930`'un toplamı + 家事消費 `AMF00950` + 雑収入 `AMF00960` = `AMF00980` (hesaplı) |
| 仕入高 | ③ 仕入金額 | `AMF00130` | ② 期首 `AMF00120`, ⑤ 期末棚卸 `AMF00150` bizde yok → 0/boş (⚠️ stok yönetimi yok; kullanıcı girişi gerekir) |
| 租税公課 | ⑧ | `AMF00190` | |
| 荷造運賃 | ⑨ | `AMF00200` | |
| 水道光熱費 | ⑩ | `AMF00210` | |
| 旅費交通費 | ⑪ | `AMF00220` | |
| 通信費 | ⑫ | `AMF00230` | |
| 広告宣伝費 | ⑬ | `AMF00240` | |
| 接待交際費 | ⑭ | `AMF00250` | |
| 損害保険料 | ⑮ | `AMF00260` | |
| 修繕費 | ⑯ | `AMF00270` | |
| 消耗品費 | ⑰ | `AMF00280` | |
| 減価償却費 | ⑱ | `AMF00290` | = 減価償却費の計算 [リ] `AMF01840` (T-073, **別表 ile aynı olmalı**) |
| 福利厚生費 | ⑲ | `AMF00300` | |
| 給料賃金 | ⑳ | `AMF00310` | |
| 外注工賃 | ㉑ | `AMF00320` | |
| 利子割引料 | ㉒ | `AMF00330` | |
| 地代家賃 | ㉓ | `AMF00340` | |
| 貸倒金 | ㉔ | `AMF00350` | |
| 任意科目（会議費・新聞図書費・支払手数料 …）| ㉕〜㉚ (6 slot) | tutar `AMF00360` (繰返し 6), ad `AMF00060` (繰返し 6) | reports.py FREE_SLOTS ile aynı; 6'dan fazlası 雑費'ye |
| 雑費 | ㉛ | `AMF00370` | |
| 経費計 | ㉜ | `AMF00380` | **hesaplı** (AMF00190…AMF00370 toplamı) — XML'e yazılırsa kontrol: toplam eşit olmalı |
| 青色申告特別控除前の所得金額 | ㊸ | `AMF00500` | hesap: `AMF00390 + AMF00440 − AMF00490` |
| 青色申告特別控除額 | ㊹ | `AMF00510` | **kullanıcı seçimi** (650,000 / 550,000 / 100,000 / 0; 2027 yılı sonrası için taslağa bak ⚠️) |
| 所得金額 | ㊺ | `AMF00530` | hesap: `AMF00500 − AMF00510` |

Bizde olmayan → boş bırakılır (zorunlu değil, `minOccurs="0"`): ㉞〜㊶ 引当金・準備金 (`AMF00420…AMF00490`: 専従者給与 `AMF00460`, 貸倒引当金 `AMF00470`), 家事消費等, 軽減税率対象 `AMF00995`, 製造原価 (AMH, 製造業のみ).

## 3. 面2: 月別売上・仕入 ✅
| Bizde | XML |
|---|---|
| `reports.monthly()` — ay m için売上 | `AMF00600, 00630, 00660, 00690, 00720, 00750, 00780, 00810, 00840, 00870, 00900, 00930` (1〜12月, 3'er adım) |
| ay m için 仕入 | `AMF00610, 00640, …, 00940` (売上'nın +10'u; 例 1月 `AMF00610`, 4月 `AMF00700`, 12月 `AMF00940`) ⚠️ ara tag numaraları 仕様書 satırlarından örüntü olarak çıkarıldı; T-068'de XSD ile birebir doğrulanacak |
| 雑収入 / 家事消費等 | `AMF00960` / `AMF00950` (bizde yok) |

## 4. 面3: 減価償却費の計算 (T-073 `/assets/schedule`) ✅
繰返し **7** satır; 次葉 toplamı (`AMF0179x`) 7'den fazla varlık için.
| `AssetRow` (bizde) | 決算書 列 | XML |
|---|---|---|
| name | 減価償却資産の名称等 | `AMF01610` |
| 取得年月 (acquired) | 取得年月 (元号 3:昭和/4:平成/5:令和 + 年 + 月) | `AMF01630` |
| cost | イ 取得価額 | `AMF01640` |
| 償却の基礎になる金額 | ロ | `AMF01650` — 定額法: = 取得価額 (bizde ayrı alan yok) |
| method | 償却方法 | `AMF01660` (metin; 「定額法」「一括償却」「少額特例」ya da boş) |
| life | 耐用年数 (`2≦x≦100` ✅ params ile aynı) | `AMF01670` |
| rate_permille / 1000 | ハ 償却率 (`Z.ZZZ`, **3 ondalık** → bizim ceil_3dp kuralının biçimiyle uyumlu; kural hâlâ ⚠️) | `AMF01690` |
| months | ニ 本年中の償却期間 (1〜12) | `AMF01720` |
| ordinary | ホ 本年分の普通償却費 | `AMF01730` |
| business_pct | チ 事業専用割合 (`ZZZ.ZZ`) | `AMF01760` |
| expense | リ 本年分の必要経費算入額 | `AMF01770` |
| book_end | ヌ 未償却残高 | `AMF01780` |
| — | ヘ 割増(特別)償却費 / ト 償却費合計 | `AMF01740` / `AMF01750` (bizde 割増なし → 0; ト = ホ + ヘ) |
Toplamlar (hesaplı, `AMF01810…AMF01850`): `AMF01730`'ların toplamı + `AMF01793`. **`AMF01840` (必要経費算入額 計) = 面1 `AMF00290` olmalı.** 少額特例/一括償却 varlıkları için 償却率/期間 alanlarının nasıl doldurulacağı 仕様書 Ver11x'te "入力補足" yok → ⚠️ T-068'de 仕様書 備考 + 手引き kontrolü.

## 5. Desteklenmeyen / sonraki iş
- 面4 貸借対照表 (`AMG…`): 65万控除 için zorunlu; bizde defter yok → T-068'de yalnızca 55万/10万 (B/S gerektirmeyen: **10万**) hesaplanabilir; 55万・65万 için B/S verisi yok ⚠️ (kullanıcıya uyarı).
- 売上先/仕入先 明細 (`AMF02240…`), 地代家賃の内訳 (`AMF02140…`), 給料賃金/専従者給与 内訳, 製造原価 (AMH) — v1'de boş.
- Kimlik alanları (氏名・住所・屋号 `AMB…`, 年分 `AMA00000`) `profile`'dan.
- 申告書B (KOA020 v23.0) ile bağlantı: `AMF00530` → 申告書B 事業所得 (`ABB…` alanları) 帳票間連動 (項番8 仕様書 — **indirilmedi** ⚠️).

## 6. T-068 için girdi listesi
1. Bu tablo; 2. `KOA210-011.xsd` / `RKO0010-250.xsd` + `General.xsd` ile şema doğrulaması (xmllint, repoya şema koymadan); 3. 項番8 帳票間連動仕様書 ve ドラフト版 (2027 yılı) indirilmeli; 4. imza ve gönderim kullanıcıda (docs/ETAX.md).
