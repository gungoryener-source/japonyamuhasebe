# J-SaaS 会計 (Tegaru Kaikei) — Ajanlar için proje anayasası

Bu depo, Japonya'daki küçük işletmeler ve serbest çalışanlar için bir **bulut ön muhasebe** ürünüdür:
fiş/fatura girişi (web + LINE + WhatsApp), 適格請求書 (インボイス) uyumu, 消費税 ve 確定申告 hazırlığı.
Bu dosyayı okuyan her ajan aşağıdaki kurallara uyar. Rolüne özel talimatlar `agents/<rol>.md` içindedir.

## Ürün sahibi
- GitHub: `gungoryener-source` · İletişim dili: **Türkçe**. Uygulama arayüz dili: **Japonca** (gerekirse küçük İngilizce yardımcı etiket).
- Ürün sahibinin kararı (2026-11-05): ajanlar işlerini **testler geçerse doğrudan `main`'e birleştirir**. `main` Render'a otomatik yayınlanır.
  Bu yüzden `main`'i kırmamak her şeyden önce gelir.

## Sprint (2026-11-06 18:00 → 2026-11-08 18:00 İstanbul)
Ürün sahibi 2 günde kod tarafının bitmesini istedi. Bu sürede geliştirici **saatte bir**, inceleyici 4 saatte bir, planlayıcı günde bir çalışır.
- Öncelik: önce `review-fix`, sonra P0 (T-055 fiyatlar, T-011 R2 depolama), sonra P1, sonra P2. (T-047 dil: tamamlandı.)
- 2026-11-07: ürün sahibi QUESTIONS'taki önerilen varsayılanları onayladı (Q-01…Q-14 cevaplı). Gerçek kişisel/şirket bilgisi (Q-12) ve hesap anahtarları ürün sahibinden gelecek; uydurma.
- Görevi tek çalışmada bitirmeye çalış; bitmiyorsa çalışan bir dilimi birleştir ve kalanını alt görev (T-0xxb) olarak aç.
- Kullanıcı kararı gereken her şey (fiyat, yasal bilgiler, anahtarlar) yapılandırmaya veya yer tutucuya bağlanır, QUESTIONS'a yazılır, iş durmaz.

## Depo yapısı
| Yol | İçerik |
|---|---|
| `bot/` | FastAPI sunucusu: LINE webhook (`app.py`), mesaj çözücü (`parser.py`), rich menu, testler (`bot/tests`) |
| `dashboard-next/` | Next.js 15 + Tailwind 3 + lucide-react web paneli (`app/page.tsx`) |
| `web/` | Eski tek-dosya HTML prototipleri (`index.html` = fiş/LINE/beyan demosu, `dashboard.html`). Referans; yeni iş `dashboard-next/`'e. |
| `docs/` | `ARCHITECTURE.md`, `TAX_RULES.md` (vergi kuralları + kaynak + tarih), `ROADMAP.md` |
| `agents/` | Rol talimatları: `developer.md`, `reviewer.md`, `tax-watcher.md`, `planner.md` |
| `tasks/BACKLOG.md` | **Tek görev kuyruğu.** Ajanlar buradan iş alır ve durumunu günceller |
| `tasks/LOG.md` | Her ajan çalışmasının 3–6 satırlık özeti (en yeni üstte) |
| `tasks/QUESTIONS.md` | İnsan kararı gereken sorular. Ajan cevap uydurmaz, buraya yazar |
| `render.yaml` | Render blueprint (`rootDir: bot`). Plan/bölge/ortam değişkeni adlarını **değiştirme** |

## Çalışma döngüsü (her ajan, her çalışma)
1. `git pull --rebase origin main`
2. `CLAUDE.md`, kendi `agents/<rol>.md`, `tasks/BACKLOG.md`, `tasks/QUESTIONS.md` (cevaplanan sorular) oku.
3. **Bir** iş birimi yap (geliştirici: tek görev). Küçük, geri alınabilir adımlar.
4. Doğrulama kapısı (aşağıda) geçmeden `main`'e push yok.
5. `tasks/BACKLOG.md` ve `tasks/LOG.md` güncelle, aynı commit'e koy.
6. `git pull --rebase origin main` → kapıyı tekrar çalıştır → `git push origin HEAD:main`.
   Push reddedilirse en fazla 2 kez rebase + yeniden test + push dene; olmazsa çalışmayı LOG'a yaz ve bırak.

## Doğrulama kapısı (zorunlu)
```bash
cd bot && pip install -q -r requirements-dev.txt && python -m pytest -q
# (CI aynı testleri PostgreSQL 16 ile de koşar; yerelde: DATABASE_URL=postgresql://... python -m pytest -q)
cd dashboard-next && npm ci && npx next build      # yalnızca dashboard-next/ değiştiyse
```
- Kırmızı test varken push etme. Testi silerek/atlayarak yeşile çevirme.
- Yeni davranış = yeni test. Vergi hesabı içeren her fonksiyon için sınır değer testleri yaz.
- GitHub Actions (`.github/workflows/ci.yml`) aynı kapıyı çalıştırır; `main` kırmızıysa bir sonraki geliştirici çalışmasının **ilk işi** onu düzeltmektir.

## Kesin kurallar
- **Sır yok:** anahtar, token, gerçek kişi verisi commit'leme. Ortam değişkenleri: `LINE_CHANNEL_SECRET`, `LINE_CHANNEL_ACCESS_TOKEN`, `ANTHROPIC_API_KEY`, `ADMIN_KEY`, (ileride) `DATABASE_URL`, `NTA_APP_ID`, `WHATSAPP_*`. Yeni değişken gerekiyorsa `render.yaml`'a `sync: false` ile ekle ve `tasks/QUESTIONS.md`'ye "değer girilmeli" diye yaz.
- **Veri silme yok:** veritabanı şemasında yıkıcı migration yazma; sütun eklemek serbest, silmek/yeniden adlandırmak QUESTIONS'a.
- **Geriye uyum:** LINE webhook `/callback` ve sağlık uç noktası `/` sözleşmesi bozulmaz.
- **Vergi kuralı uydurma:** her oran/eşik/tarih `docs/TAX_RULES.md`'de kaynak URL ve kontrol tarihiyle bulunmalı. Emin değilsen QUESTIONS'a yaz, kodu ekleme.
- **Kapsam:** çalışma başına tek görev; ilgisiz yeniden yazım yok. Büyük görevi önce BACKLOG'da alt görevlere böl.
- **Bağımlılık:** yeni paket eklemeden önce gerçekten gerekli mi düşün; sürümü tam sabitle.
- **Ödeme/üretim hesapları:** Render, LINE, GitHub ayarlarını değiştirme; sadece koda dokun.
- İnsan sorusu bekleyen görev `blocked` olur, sıradakine geç.

## Kod kuralları
- Python 3.12, FastAPI, tip ipuçları, `httpx` (async). Para birimi her zaman **tamsayı yen**; KDV dahil tutardan vergi: `floor(gross * r / (100 + r))`.
- Tarih: `Asia/Tokyo`. Mali yıl ayarı şirket bazında (bireyler takvim yılı, şirketler çoğunlukla 4月〜3月).
- Hesap kalemleri (勘定科目) Japonca adıyla saklanır. Kullanıcıya dönük metinler Japonca.
- Frontend: Tailwind sınıfları, lucide-react ikonları, renkler `navy #1E293B` / `mint #10B981`, arka plan `#F9FAFB`, yoğun bento düzeni, sayılar `tabular-nums`, `¥1,234,567` formatı.
- Commit mesajı: `T-0xx: kısa açıklama` + gövdede ne/neden. Ajan imzası: `Agent: <rol>`.

## Görev durumu sözlüğü (BACKLOG)
`todo` → `doing (<rol>, <tarih>)` → `done (<commit>)` · `blocked (Q-xx)` · `review-fix` (inceleyicinin açtığı düzeltme)
`doing` 24 saatten eskiyse terk edilmiş sayılır, başka ajan alabilir.
