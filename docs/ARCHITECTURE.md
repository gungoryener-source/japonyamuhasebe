# Mimari

```
 LINE / WhatsApp ──webhook──▶ bot/ (FastAPI, Render)
                                 │  parser.py   : "店名 金額" → kayıt
                                 │  OCR         : Claude Vision → JSON
                                 │  tax/ (plan) : 消費税・所得税 hesap motoru
                                 ▼
                           DB (bugün SQLite → hedef PostgreSQL)
                                 ▲
 Tarayıcı ──▶ dashboard-next/ (Next.js) ──REST /api/*──┘   (plan: T-004)
```

## Bugünkü durum (2026-11-05)
- `bot/app.py`: `/callback` (LINE), `/whatsapp` (WhatsApp Cloud API), `/api/v1/*` (`bot/api.py`, Bearer token), `/entries/{user_id}` (admin), `/admin/richmenu`, `/`.
- Sohbet çekirdeği `app.respond()` kanaldan bağımsız; vergi motoru `bot/tax/`; fatura `bot/invoices.py`; CSV `bot/export.py`.
- Veritabanı: Render PostgreSQL `jsaas-db` (`DATABASE_URL`); yerelde/testte SQLite. Katman: `bot/store.py`.
- `dashboard-next/`: API'ye bağlı panel (token yoksa demo veri), Render statik site `jsaas-panel`.
- Render: `tegaru-line-bot` web servisi, bölge singapore, free plan, `main` push'unda otomatik deploy.
- LINE kanalı: **henüz açılmadı** (insan işi, Q-01).

## Hedef veri modeli (özet)
- `tenants` (事業所: ad, 登録番号, mali yıl başlangıcı, 課税方式: 本則/簡易/2割/3割, 個人|法人)
- `users` (LINE userId / WhatsApp numarası / web hesabı → tenant)
- `entries` (tarih, tür, karşı taraf, tutar_brüt, oran 10/8/0, 登録番号, 勘定科目, kaynak, görsel_yolu, durum)
- `invoices` (発行: no, alıcı, kalemler, oran bazında toplam ve vergi, vade, durum 未入金/支払済/期日超過)
- `bank_tx` (banka hareketleri, eşleştirme)

## Tasarım ilkeleri
- Para = tamsayı yen. Vergi hesabı tek bir saf Python modülünde (`bot/tax/`), hem bot hem API hem testler oradan kullanır.
- Her kanal (LINE, WhatsApp, web) aynı servis katmanını çağırır; kanal kodu ince kalır.
