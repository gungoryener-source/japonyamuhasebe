# 電子帳簿保存法 ve 「優良な電子帳簿」 — ürün durumu (T-049 notu, 2026-11-07)

令和9年分以後の青色申告特別控除 **75万円** は、65万円の要件（正規の簿記・期限内 e-Tax）に加えて
「優良な電子帳簿」（またはデジタルシームレス保存）と事前の届出を求める（TAX_RULES §2, NTA リーフレット 0026007-003_02）。

**Bu ürün şu an 「優良な電子帳簿」 şartlarını karşıladığını İDDİA ETMEZ.** Panel yalnızca 75万 seçeneğini
hesaplamada sunar; şartların karşılanıp karşılanmadığı kullanıcının / 税理士'nin kararıdır.

Bilinen durum (doğrulanmadı, uzman kontrolü gerekir):
- 訂正・削除の履歴: T-065 ile entries ve invoices için `audit_log` (önce/sonra, kim, ne zaman; silinen kayıt korunur) + `GET /api/v1/entries/{id}/history`. T-065b: bank_tx düzeltme/onay/bağlama değişiklikleri de yazılır (`GET /api/v1/bank/{id}/history`); panel 経費精算 → 「履歴」 düğmesi (kim: sahip tüm e-postaları, üyeler yalnızca kendini görür; ayrılan üye 「退出したメンバー」). 仕切書 → T-065c (Q-18, eksik). Banka içe aktarma satırları (ham veri) ve türetilmiş 残高チェック (`balance_ok`) geçmişe yazılmaz.
- 相互関連性 (帳簿間の関連): fiş görseli ↔ kayıt bağlantısı var (image_path), banka satırı ↔ kayıt (entry_id) var.
- 検索機能 (日付・金額・取引先): /api/v1/entries arama var.
- 電子取引データ保存: fiş görselleri kalıcı depolama (R2, Q-14) kurulana kadar deploy'da silinir → eksik.

Açık iş: düzenleme geçmişi (audit log) + kalıcı görsel depolama tamamlanınca bir 税理士 ile 優良 şartları gözden geçirilmeli.
