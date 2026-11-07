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
