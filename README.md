# J-SaaS 会計 (Tegaru Kaikei)

Japonya'daki küçük işletmeler ve serbest çalışanlar için bulut ön muhasebe: LINE/WhatsApp ile fiş gönderme, 適格請求書, 消費税 ve 確定申告 hazırlığı.

| Bölüm | Yol | Çalıştırma |
|---|---|---|
| LINE bot + API (FastAPI) | `bot/` | `cd bot && pip install -r requirements-dev.txt && uvicorn app:app --reload` · test: `python -m pytest -q` |
| Web paneli (Next.js + Tailwind + lucide) | `dashboard-next/` | `cd dashboard-next && npm ci && npm run dev` |
| HTML prototipleri | `web/` | tarayıcıda aç |

- Canlı test sunucusu: https://tegaru-line-bot.onrender.com (Render, `main`'e her push'ta otomatik yayın)
- Mimari: `docs/ARCHITECTURE.md` · Vergi kuralları (kaynaklı): `docs/TAX_RULES.md` · Yol haritası: `docs/ROADMAP.md`

## Otonom ajanlar
Bu depo zamanlanmış Claude ajanlarıyla sürekli geliştirilir. Kurallar `CLAUDE.md`, roller `agents/`.

| Ajan | Sıklık (İstanbul saati) | Ne yapar |
|---|---|---|
| Geliştirici | her gün 10:37 ve 22:37 | `tasks/BACKLOG.md`'den bir görevi kodlar, test eder, testler geçerse `main`'e birleştirir |
| İnceleyici | her gün 07:23 | son 24 saatin commit'lerini inceler, eksik test yazar, düzeltme görevi açar |
| Vergi takipçisi | pazartesi 09:11 | Japonya vergi değişikliklerini tarar, `docs/TAX_RULES.md`'yi günceller |
| Planlayıcı | pazar 21:07 | yol haritası ve görev listesini düzenler, `tasks/WEEKLY.md` raporu yazar |

**Senin işin:** `tasks/QUESTIONS.md`'deki soruları cevaplamak ve `tasks/WEEKLY.md` raporunu okumak.

## LINE bot kurulumu (tek seferlik, insan adımı)
1. LINE Developers → Provider → Messaging API kanalı. Auto-reply ve Greeting kapalı.
2. Render → `tegaru-line-bot` → Environment: `LINE_CHANNEL_SECRET`, `LINE_CHANNEL_ACCESS_TOKEN`, `ANTHROPIC_API_KEY`.
3. Webhook URL: `https://tegaru-line-bot.onrender.com/callback` → Verify → Use webhook.
4. Menü: `curl -X POST "https://tegaru-line-bot.onrender.com/admin/richmenu?key=<ADMIN_KEY>"` (ADMIN_KEY Render'da otomatik üretildi).

Bot komutları (LINE ve WhatsApp): `タクシー 2300 T1234567890123` · `ローソン 540円 軽減` · `入金 330000 合同会社ミナト` · fotoğraf · `合計` · `取消` · `科目変更` · `税率8%` · `パネル` (web paneli bağlantısı) · `ヘルプ`

Web paneli: https://jsaas-panel.onrender.com (LINE'da 「パネル」 yazınca gelen link ile bağlanır; bağlantı yoksa demo veri gösterir). API: `docs/API.md`.

> Render free planında SQLite kalıcı değildir; kalıcı veritabanı görevi T-006.
