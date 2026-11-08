# クレジットカード利用明細 CSV — T-077

Ayrıştırıcı: `bot/card_csv.py` (şirket adına göre dal yok; başlık satırındaki sözcüklerle sütun atar). Testler: `bot/tests/test_card_csv.py` (sentetik satırlar).
Kontrol tarihi: **2026-11-08**. Kaynak seviyesi: ✅ şirket/resmî belge · 🟡 üçüncü taraf · ⚠️ doğrulanamadı.

## Durum
Kart şirketlerinin **CSV başlık satırı** için birincil kaynak bulunamadı; bu yüzden hiçbir şirket için başlık "doğrulandı" diye yazılmadı.

| Kart şirketi | CSV başlığı | Seviye | Not |
|---|---|---|---|
| 三井住友カード | — | ⚠️ | Yalnızca ortak alan anlamları belgeli: ご利用日, 支払区分 (1=1回払い, 2=2回払い, 3〜=分割, リ=リボ, ボ=ボーナス一括), 支払回数, 備考 ([ご利用明細のご説明](https://www.smbc-card.com/mem/oshiharai/pop/wm_setsumei.jsp)) — CSV değil |
| 楽天カード / JCB / 他 | — | ⚠️ | Genel sütun eşlemesi ile denenir; gerçek (kişisel verisi silinmiş) başlık satırı gelirse fixture + test eklenir |

Bilinen genel bilgi: kart CSV biçimi şirkete göre değişir; iade/取消 satırları eksi tutarla gelir (弥生・freee yardım sayfaları: iade ayrı sütun/eksi tutar) 🟡.

## Eşleme kuralları
| Alan | Kabul edilen başlık (regex) |
|---|---|
| 利用日 | `利用日 / ご利用日 / 利用年月日 / 取引日 / 日付` |
| 利用先 | `利用店名 / ご利用店名 / 利用先 / 加盟店 / 利用内容 / 摘要` |
| 利用金額 | `利用金額 / ご利用金額 / 利用額 / 金額` (**支払金額・支払総額・手数料 kullanılmaz**) |
| 支払日 | `支払日 / お支払日 / 引落日` → 摘要 sonuna `(支払日 YYYY-MM-DD)` |
| 支払区分 | `支払区分 / 支払方法 / 支払回数` → 1回払い dışı ise 摘要'ye `[3]` gibi eklenir |

## Davranış
- Tutar daima **çıkış (−)**; iade/取消 (eksi) **giriş (+)** olarak alınır. Yönü bilinmeyen satır uydurulmaz: tutarı okunamayan/0 satır atlanır.
- Tarihi okunamayan satırlar (合計, 分割・リボ notları, boş) atlanır; 手数料/合計 gibi 摘要'ler atlanır.
- 摘要 CSV'deki gibi saklanır (`=` ile başlayan metin dahil); dışa aktarımda formül kaçışı `export.py` tarafında.
- UTF-8 (BOM'lu/BOM'suz) ve Shift_JIS otomatik.

## Akış ve sınırlar
- `POST /api/v1/card/import?account=` → mevcut `bank_tx` hattına (`src=card`, hesap adı varsayılan 「クレジットカード」) **未確認** olarak girer; aynı CSV'yi tekrar yüklemek mükerrer yaratmaz (aynı gün aynı tutar iki ayrı harekettir).
- Gider kaydı mevcut 「経費に登録」 akışıyla yapılır. **Karşı hesap 未払金 henüz yok**: `entries` tablosunda karşı hesap sütunu bulunmadığı için ayrı yazılmaz (şema değişikliği gerektirir — sormadan eklenmedi).
- Fiş kotasına (Q-11) girmez.
- Panel: yalnızca API (BACKLOG kararı); 銀行連携 sayfasında ayrı sekme yok.
