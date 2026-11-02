# てがる会計 LINE Bot

Kullanıcı LINE'dan fiş fotoğrafı ya da "ローソン 540円 軽減" gibi kısa bir mesaj gönderir; bot kaydı deftere işler ve hızlı yanıt butonlarıyla cevap verir.

## Dosyalar
| Dosya | Görev |
|---|---|
| `app.py` | FastAPI webhook sunucusu: imza doğrulama, metin/fotoğraf işleme, Claude ile fiş okuma, SQLite |
| `parser.py` | "店名 金額" mesaj çözücü (LINE ve WhatsApp ortak kullanır) |
| `setup_richmenu.py` | Alttaki 3 butonlu menüyü (レシート / 今月の集計 / 取り消し) oluşturur, bir kez çalıştırılır |

## Kurulum
1. **LINE Developers** → Provider oluştur → *Messaging API* kanalı aç.
   - `Channel secret` ve `Channel access token (long-lived)` değerlerini al.
   - LINE Official Account Manager'da *Auto-reply* ve *Greeting message* kapat (bot cevaplayacak).
2. Ortam değişkenleri: `.env.example` dosyasını `.env` olarak kopyalayıp doldur.
3. Çalıştır:
   ```bash
   pip install -r requirements.txt
   set -a; source .env; set +a
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```
4. Sunucuyu HTTPS ile dışarı aç (test için `ngrok http 8000`, canlıda Render / Fly.io / Cloud Run).
5. LINE Developers → Messaging API → **Webhook URL**: `https://<alan-adın>/callback` → *Verify* → *Use webhook* aç.
6. Menüyü kur: `python setup_richmenu.py`
7. QR koduyla botu arkadaş ekle, "ヘルプ" yaz.

## Komutlar
- `タクシー 2300 T1234567890123` → gider kaydı (kayıt numarasıyla)
- `ローソン 540円 軽減` → %8 indirimli oranla gider
- `入金 330000 合同会社ミナト` → gelir kaydı
- Fotoğraf → Claude fişi okur (tarih, mağaza, tutar, oran, T numarası, hesap kalemi)
- `合計` aylık özet · `取消` son kaydı sil · `ヘルプ` kullanım

## Canlıya geçmeden önce
- `/entries/{user_id}` uç noktasına kimlik doğrulama ekle (şu an açık).
- SQLite yerine PostgreSQL; fiş görsellerini S3/GCS'de sakla (電子帳簿保存法 için 7 yıl, arama yapılabilir şekilde).
- T numaralarını 国税庁 適格請求書発行事業者公表システム Web-API ile doğrula.
- Web panelindeki (demo) 確定申告 ekranı bu veritabanından beslenecek.
