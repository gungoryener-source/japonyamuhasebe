# Operasyon notları

İnsan operatörün elle yaptığı işler. Ajanlar bu adımları **otomatikleştirmez** (CLAUDE.md: veri silme yok).

## Hesap silme talepleri (T-046b)

Kullanıcı (yalnızca defter sahibi / owner) panel 設定 → 「アカウントの削除」 ile talep gönderir.
API talebi `deletion_requests` tablosuna `status='pending'` olarak yazar; **hiçbir veri silinmez** ve kullanıcı
hizmeti kullanmaya devam edebilir.

1. Bekleyen talepleri listele:
   ```bash
   curl -s -H "X-Admin-Key: $ADMIN_KEY" https://tegaru-line-bot.onrender.com/api/v1/admin/deletion-requests
   ```
   Her satırda `user_id` (defter), `account_id`, `email`, `requested_at` bulunur. `account_id=0` → yalnızca LINE
   ile kullanılan defter (e-posta yok; LINE üzerinden iletişim).
2. Ücretli abonelik varsa (`subscriptions` tablosu, `status` active/trialing/past_due) önce Stripe panelinden iptal
   edildiğini doğrula; kullanıcıya iade/dönem sonu bilgisini ilet.
3. Kullanıcıya kayıtlı e-postadan onay yaz (talebin gerçekten kendisinden geldiğini doğrula) ve
   「全データをダウンロード」 ile yedek almasını hatırlat.
4. Silme işleminin kendisi (defterin `entries`, `invoices`, `bank_tx`, `profiles`, fiş görselleri, `api_tokens`,
   `ledger_members`, `account_ledgers`, `accounts` satırları) **ürün sahibinin onayıyla, elle** yapılır. Yasal saklama
   süreleri (電子帳簿保存法 vb.) netleşmeden otomatik silme betiği yazılmaz — bkz. `tasks/QUESTIONS.md` Q-15.
5. İşlem bitince talebi kapat (veri silmeyen güncelleme):
   ```sql
   UPDATE deletion_requests SET status='done' WHERE id=<id>;      -- tamamlandı
   UPDATE deletion_requests SET status='cancelled' WHERE id=<id>; -- kullanıcı vazgeçti
   ```
   `cancelled` talebi kullanıcı yeniden gönderirse tekrar `pending` olur.

## PostgreSQL yedeği (T-046c)

`scripts/backup.sh` = `pg_dump "$DATABASE_URL" | gzip` → `./backups/tegaru-YYYYMMDD-HHMMSS-JST.sql.gz`
(`BACKUP_DIR` ile değiştirilebilir). Operatörün **kendi makinesinde** çalıştırılır; Render ayarı değişmez.

- Yalnızca okur; veritabanında ve eski yedeklerde hiçbir şey silmez (eski dosyaların temizliği elle).
- `DATABASE_URL` ekrana/dosya adına/log'a yazılmaz. Not: `pg_dump --dbname=…` olarak geçtiği için çalışma
  süresince aynı makinedeki `ps` çıktısında görünebilir — paylaşımlı sunucuda çalıştırmayın.
- Yedek dosyası izni 600; içinde kişisel ve muhasebe verisi var → şifreli diskte tutun, depoya/sohbete koymayın
  (`backups/` `.gitignore`'da).
- Yarım yedek bırakmaz: `pg_dump` hata verirse, gzip bozuksa veya döküm 「PostgreSQL database dump complete」
  satırıyla bitmiyorsa dosya oluşmaz ve çıkış kodu ≠ 0 (2: URL yok, 3: pg_dump/gzip yok, 5: pg_dump hatası,
  6: gzip, 7: kesik döküm).
- `pg_dump` sürümü sunucununkiyle aynı veya daha yeni olmalı (Render jsaas-db: PostgreSQL 16 → `postgresql-client-16`).

### Yedek alma

1. Render → `jsaas-db` → **Connect** → **External Database URL**'yi kopyala (sır; dosyaya yazma).
2. Çalıştır:
   ```bash
   read -rs DATABASE_URL && export DATABASE_URL     # yapıştır + Enter (ekranda/geçmişte görünmez)
   scripts/backup.sh                               # son satır: yedek dosyasının yolu
   unset DATABASE_URL
   ```
3. Önerilen sıklık: canlı kullanıcı varken günde bir kez ve her şema değişikliği / plan geçişinden önce.

### Geri yükleme

Her zaman **boş, yeni** bir veritabanına geri yükleyin (çalışan veritabanının üzerine yazmayın — döküm
`DROP` içermez, mevcut tablolarla çakışırsa tek işlem geri alınır).

```bash
# 1) Boş hedef: Render'da yeni PostgreSQL veya yerelde: createdb tegaru_restore
read -rs TARGET_URL && export TARGET_URL
# 2) Geri yükle — hata olursa hiçbir şey yazılmaz (tek işlem)
gunzip -c backups/tegaru-20261108-030000-JST.sql.gz \
  | psql "$TARGET_URL" -q -v ON_ERROR_STOP=1 --single-transaction
# 3) Doğrula
psql "$TARGET_URL" -c "SELECT count(*) FROM entries" -c "SELECT count(*) FROM invoices"
unset TARGET_URL
```

Uygulamayı yeni veritabanına geçirmek (`tegaru-line-bot` → `DATABASE_URL`) Render ayarıdır → ürün sahibi yapar.
Fiş görselleri veritabanında değil depolamada (T-011: R2 veya yerel disk); bu betik onları **kapsamaz**.

### Render ücretsiz veritabanı sınırı (Q-07)

Render'ın ücretsiz PostgreSQL'i oluşturulduktan ~30 gün sonra sona erer ve otomatik yedek almaz. Q-07 kararı:
gerçek kullanıcı gelmeden önce **Basic** plana geçilecek. O zamana kadar sona erme tarihinden önce bu betikle
yedek alın; süre dolarsa yeni veritabanı oluşturup yukarıdaki geri yükleme adımlarını uygulayın.
