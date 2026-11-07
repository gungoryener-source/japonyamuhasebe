/**
 * Arayüz metinleri (T-047). Anahtar = Japonca kaynak metin; ja her zaman kaynaktır.
 * Çevirisi olmayan metin Japonca gösterilir (güvenli geri dönüş).
 * Kural: vergi/muhasebe terimleri tr/en'de Japonca terimle birlikte verilir — "Kesin beyan (確定申告)".
 * Saklanan veri (勘定科目) ve fatura PDF'i her zaman Japonca kalır; yalnızca görüntü çevrilir.
 * Yer tutucu: {name} → translate(lang, s, { name }).
 */
export type Lang = "ja" | "tr" | "en";

export const LANGS: { code: Lang; label: string }[] = [
  { code: "ja", label: "日本語" },
  { code: "tr", label: "Türkçe" },
  { code: "en", label: "English" },
];

type Dict = Record<string, string>;

const TR: Dict = {
  // Kart başlıkları
  "クイックアクション": "Hızlı işlemler",
  "メンバー": "Üyeler",
  "今月の利用状況": "Bu ayki kullanım",
  "会計ソフト用CSV": "Muhasebe yazılımı için CSV",
  "入出金明細": "Banka hareketleri",
  "取引一覧・検索": "İşlem listesi ve arama",
  "所得税の概算": "Gelir vergisi tahmini (所得税)",
  "手入力": "Elle giriş",
  "明細CSVを取り込む": "Hesap dökümü CSV içe aktar",
  "法令対応ステータス": "Mevzuat uyumu",
  "消費税": "Tüketim vergisi (消費税)",
  "消費税管理": "Tüketim vergisi (消費税)",
  "消込候補": "Eşleştirme önerileri",
  "現在のプラン": "Mevcut plan",
  "税務カレンダー": "Vergi takvimi",
  "青色申告決算書（損益計算書）": "Mavi beyan tablosu – gelir tablosu (青色申告決算書)",
  "領収書を読み取る": "Fiş oku",
  // Dil
  "表示言語": "Görüntüleme dili",
  "表示言語を選んでください。帳簿データ・勘定科目・請求書PDFは日本語のままです。":
    "Arayüz dilini seçin. Defter kayıtları, hesap kalemleri (勘定科目) ve fatura PDF'leri Japonca kalır.",
  // Menü
  "ホーム": "Ana sayfa",
  "請求書管理": "Faturalar (請求書)",
  "経費精算": "Giderler (経費)",
  "銀行連携": "Banka bağlantısı",
  "確定申告 / 税務": "Vergi beyanı",
  "料金プラン": "Abonelik planı",
  "設定": "Ayarlar",
  "メインメニュー": "Ana menü",
  "メニューを閉じる": "Menüyü kapat",
  "メニューを開く": "Menüyü aç",
  "適格請求書発行事業者": "Kayıtlı fatura düzenleyici (適格請求書発行事業者)",
  // Sayfa başlıkları
  "ダッシュボード": "Kontrol paneli",
  "適格請求書（インボイス）の発行・入金管理": "Uygun faturaların (インボイス) düzenlenmesi ve tahsilat takibi",
  "ネットバンキングの入出金明細（CSV）を取り込み、請求書の消込と経費登録を自動化":
    "İnternet bankacılığı hareketlerini (CSV) içe aktarın; fatura eşleştirme ve gider kaydı otomatik",
  "青色申告決算書・所得税・消費税の概算と会計ソフト連携":
    "Mavi beyan tablosu (青色申告決算書), gelir vergisi, tüketim vergisi (消費税) tahmini ve muhasebe yazılımı aktarımı",
  "領収書の読み取り・登録・検索（電子帳簿保存法の検索要件に対応）":
    "Fiş okuma, kayıt ve arama (Elektronik defter saklama kanunu 電帳法 arama şartlarına uygun)",
  "事業者情報・LINE / WhatsApp 連携・メンバー・接続": "İşletme bilgileri, LINE / WhatsApp, üyeler, bağlantı",
  "プラン・今月の利用状況・お支払い": "Plan, bu ayki kullanım, ödeme",
  // Üst çubuk
  "検索": "Ara",
  "請求書・取引先・領収書・書類を検索…": "Fatura, müşteri, fiş veya belge ara…",
  "書類・請求書・取引先を検索": "Belge, fatura, müşteri ara",
  "該当する結果がありません": "Sonuç bulunamadı",
  "銀行明細の取込": "Banka hareketlerini içe aktar",
  "今すぐ同期": "Şimdi eşitle",
  "銀行明細": "Banka hareketleri",
  "銀行API": "Banka API",
  "CSV取込": "CSV içe aktarma",
  "同期中": "Eşitleniyor",
  "接続済": "Bağlı",
  "銀行API 接続済・同期": "Banka API bağlı · eşitle",
  "銀行明細を同期しました ・ 新規 18件": "Banka hareketleri eşitlendi · 18 yeni",
  "通知": "Bildirimler",
  "お知らせ": "Bildirimler",
  "新しいお知らせはありません": "Yeni bildirim yok",
  "事業所を切り替え": "İşletme değiştir",
  "複数の帳簿を切り替えるには": "Birden fazla defter arasında geçiş için ",
  "メールアドレスでログイン": "e-posta ile giriş yapın",
  "してください。": ".",
  "読み込み中…": "Yükleniyor…",
  "読み込み中": "Yükleniyor",
  "招待コードで帳簿に参加": "Davet koduyla deftere katıl",
  "切り替えに失敗しました: {e}": "Geçiş başarısız: {e}",
  "{name} に切り替えました": "{name} seçildi",
  "経理担当 佐藤": "Muhasebe sorumlusu Sato",
  "オーナー": "Sahip",
  "編集者": "Düzenleyici",
  "閲覧者": "Görüntüleyici",
  // Mod rozeti
  "デモデータ": "Demo veri",
  "ログイン": "Giriş",
  "新規登録": "Kayıt ol",
  "LINEで接続": "LINE ile bağlan",
  "ライブ": "Canlı",
  "閲覧専用": "Salt okunur",
  "ログアウト": "Çıkış",
  "ログイン後、LINEの帳簿をアカウントに連携できます": "Giriş yaptıktan sonra LINE defterinizi hesabınıza bağlayabilirsiniz",
  "アカウント連携": "Hesaba bağla",
  "切断": "Bağlantıyı kes",
  "サーバーに接続できなかったため、デモデータを表示しています（{e}）。": "Sunucuya bağlanılamadığı için demo veri gösteriliyor ({e}).",
  // Ayarlar
  "事業者情報": "İşletme bilgileri",
  "事業者名（屋号・会社名）": "İşletme adı (ticari unvan / şirket adı)",
  "適格請求書発行事業者 登録番号": "Fatura kayıt numarası (登録番号)",
  "形式・チェックデジット OK": "Biçim ve kontrol hanesi doğru",
  "形式またはチェックデジットが正しくありません（個人事業者の番号は国税庁の公表サイトで確認してください）":
    "Biçim veya kontrol hanesi hatalı (şahıs işletmelerinin numarasını Vergi İdaresi 国税庁 sitesinden kontrol edin)",
  "事業形態": "İşletme türü",
  "個人事業主": "Şahıs işletmesi (個人事業主)",
  "法人": "Şirket (法人)",
  "3割特例（2027・2028年分）は個人事業主のみ利用できます。": "%30 özel indirimi (3割特例, 2027–2028) yalnızca şahıs işletmeleri kullanabilir.",
  "保存中…": "Kaydediliyor…",
  "保存する": "Kaydet",
  "登録番号は T + 13桁 で入力してください": "Kayıt numarası T + 13 hane olmalı",
  "保存しました（デモ）": "Kaydedildi (demo)",
  "事業者情報を保存しました": "İşletme bilgileri kaydedildi",
  "保存に失敗しました: {e}": "Kaydedilemedi: {e}",
  "コピーしました": "Kopyalandı",
  "コピー": "Kopyala",
  "連携チャネル": "Bağlı kanallar",
  "LINE 公式アカウント": "LINE resmi hesap",
  "未設定": "Ayarlanmadı",
  "レシートの写真や「タクシー 2300」を送るだけで記帳。「パネル」と送るとこの画面への接続コードが届きます。":
    "Fiş fotoğrafı ya da 「タクシー 2300」 gibi bir mesaj göndermeniz yeterli. 「パネル」 yazarsanız bu panele bağlantı kodu gelir.",
  "海外のお客様向け。LINE と同じ操作で記帳できます。": "Yurt dışındaki kullanıcılar için. LINE ile aynı şekilde kayıt yapılır.",
  "領収書の読み取り": "Fiş okuma",
  "OCR 稼働中": "OCR çalışıyor",
  "OCR 未導入": "OCR kurulu değil",
  "方式": "Yöntem",
  "OCR＋ルール（AI不使用）": "OCR + kurallar (yapay zekâ yok)",
  "・読み取れない場合のみAIで補完": " · okunamazsa yalnızca yapay zekâ ile tamamlanır",
  "・AI補完なし": " · yapay zekâ tamamlaması yok",
  "現在のプラン・今月の利用状況の確認、アップグレードや解約はこちらから。": "Mevcut plan, bu ayki kullanım, yükseltme veya iptal buradan.",
  "料金プランを見る": "Planları gör",
  "接続": "Bağlantı",
  "帳簿に接続中": "Deftere bağlı",
  "この端末の接続を解除": "Bu cihazın bağlantısını kes",
  "デモ表示中": "Demo gösteriliyor",
  "LINE で「パネル」と送ると、あなたの帳簿に接続するリンクが届きます。": "LINE'da 「パネル」 yazın; defterinize bağlanma bağlantısı gelir.",
  "接続コードを入力": "Bağlantı kodunu gir",
};

const EN: Dict = {
  "クイックアクション": "Quick actions",
  "メンバー": "Team",
  "今月の利用状況": "Usage this month",
  "会計ソフト用CSV": "CSV for accounting software",
  "入出金明細": "Transactions",
  "取引一覧・検索": "Transactions & search",
  "所得税の概算": "Income tax estimate (所得税)",
  "手入力": "Manual entry",
  "明細CSVを取り込む": "Import statement CSV",
  "法令対応ステータス": "Compliance status",
  "消費税": "Consumption tax (消費税)",
  "消費税管理": "Consumption tax (消費税)",
  "消込候補": "Matching suggestions",
  "現在のプラン": "Current plan",
  "税務カレンダー": "Tax calendar",
  "青色申告決算書（損益計算書）": "Blue return – P/L (青色申告決算書)",
  "領収書を読み取る": "Read a receipt",
  "表示言語": "Display language",
  "表示言語を選んでください。帳簿データ・勘定科目・請求書PDFは日本語のままです。":
    "Choose the interface language. Ledger data, account titles (勘定科目) and invoice PDFs stay in Japanese.",
  "ホーム": "Home",
  "請求書管理": "Invoices",
  "経費精算": "Expenses",
  "銀行連携": "Bank Sync",
  "確定申告 / 税務": "Tax Return (確定申告)",
  "料金プラン": "Billing",
  "設定": "Settings",
  "メインメニュー": "Main menu",
  "メニューを閉じる": "Close menu",
  "メニューを開く": "Open menu",
  "適格請求書発行事業者": "Qualified invoice issuer (適格請求書発行事業者)",
  "ダッシュボード": "Dashboard",
  "適格請求書（インボイス）の発行・入金管理": "Issue qualified invoices (インボイス) and track payments",
  "ネットバンキングの入出金明細（CSV）を取り込み、請求書の消込と経費登録を自動化":
    "Import online-banking statements (CSV) to auto-match invoices and record expenses",
  "青色申告決算書・所得税・消費税の概算と会計ソフト連携":
    "Blue return statement (青色申告決算書), income tax, consumption tax (消費税) estimates and accounting-software export",
  "領収書の読み取り・登録・検索（電子帳簿保存法の検索要件に対応）":
    "Read, record and search receipts (meets 電帳法 search requirements)",
  "事業者情報・LINE / WhatsApp 連携・メンバー・接続": "Business profile, LINE / WhatsApp, members, connection",
  "プラン・今月の利用状況・お支払い": "Plan, this month's usage, payment",
  "検索": "Search",
  "請求書・取引先・領収書・書類を検索…": "Search invoices, clients, receipts, documents…",
  "書類・請求書・取引先を検索": "Search documents, invoices, clients",
  "該当する結果がありません": "No results",
  "銀行明細の取込": "Import bank statement",
  "今すぐ同期": "Sync now",
  "銀行明細": "Bank statement",
  "銀行API": "Bank API",
  "CSV取込": "CSV import",
  "同期中": "Syncing",
  "接続済": "Connected",
  "銀行API 接続済・同期": "Bank API connected · sync",
  "銀行明細を同期しました ・ 新規 18件": "Bank statement synced · 18 new",
  "通知": "Notifications",
  "お知らせ": "Notifications",
  "新しいお知らせはありません": "No new notifications",
  "事業所を切り替え": "Switch business",
  "複数の帳簿を切り替えるには": "To switch between ledgers, ",
  "メールアドレスでログイン": "sign in with email",
  "してください。": ".",
  "読み込み中…": "Loading…",
  "読み込み中": "Loading",
  "招待コードで帳簿に参加": "Join a ledger with an invite code",
  "切り替えに失敗しました: {e}": "Switch failed: {e}",
  "{name} に切り替えました": "Switched to {name}",
  "経理担当 佐藤": "Accounting · Sato",
  "オーナー": "Owner",
  "編集者": "Editor",
  "閲覧者": "Viewer",
  "デモデータ": "Demo data",
  "ログイン": "Sign in",
  "新規登録": "Sign up",
  "LINEで接続": "Connect via LINE",
  "ライブ": "Live",
  "閲覧専用": "Read-only",
  "ログアウト": "Sign out",
  "ログイン後、LINEの帳簿をアカウントに連携できます": "After signing in you can link your LINE ledger to your account",
  "アカウント連携": "Link account",
  "切断": "Disconnect",
  "サーバーに接続できなかったため、デモデータを表示しています（{e}）。": "Could not reach the server, showing demo data ({e}).",
  "事業者情報": "Business profile",
  "事業者名（屋号・会社名）": "Business name (trade or company name)",
  "適格請求書発行事業者 登録番号": "Invoice registration number (登録番号)",
  "形式・チェックデジット OK": "Format and check digit OK",
  "形式またはチェックデジットが正しくありません（個人事業者の番号は国税庁の公表サイトで確認してください）":
    "Invalid format or check digit (verify sole-proprietor numbers on the 国税庁 public site)",
  "事業形態": "Business type",
  "個人事業主": "Sole proprietor (個人事業主)",
  "法人": "Corporation (法人)",
  "3割特例（2027・2028年分）は個人事業主のみ利用できます。": "The 30% special rule (3割特例, 2027–2028) is for sole proprietors only.",
  "保存中…": "Saving…",
  "保存する": "Save",
  "登録番号は T + 13桁 で入力してください": "Registration number must be T + 13 digits",
  "保存しました（デモ）": "Saved (demo)",
  "事業者情報を保存しました": "Business profile saved",
  "保存に失敗しました: {e}": "Save failed: {e}",
  "コピーしました": "Copied",
  "コピー": "Copy",
  "連携チャネル": "Channels",
  "LINE 公式アカウント": "LINE Official Account",
  "未設定": "Not set up",
  "レシートの写真や「タクシー 2300」を送るだけで記帳。「パネル」と送るとこの画面への接続コードが届きます。":
    "Just send a receipt photo or a message like 「タクシー 2300」. Send 「パネル」 to get a link to this panel.",
  "海外のお客様向け。LINE と同じ操作で記帳できます。": "For users abroad. Works the same way as LINE.",
  "領収書の読み取り": "Receipt reading",
  "OCR 稼働中": "OCR running",
  "OCR 未導入": "OCR not installed",
  "方式": "Method",
  "OCR＋ルール（AI不使用）": "OCR + rules (no AI)",
  "・読み取れない場合のみAIで補完": " · AI fallback only when unreadable",
  "・AI補完なし": " · no AI fallback",
  "現在のプラン・今月の利用状況の確認、アップグレードや解約はこちらから。": "See your plan and usage, upgrade or cancel here.",
  "料金プランを見る": "View plans",
  "接続": "Connection",
  "帳簿に接続中": "Connected to ledger",
  "この端末の接続を解除": "Disconnect this device",
  "デモ表示中": "Showing demo",
  "LINE で「パネル」と送ると、あなたの帳簿に接続するリンクが届きます。": "Send 「パネル」 on LINE to receive a link to your ledger.",
  "接続コードを入力": "Enter connection code",
};

// Sayfa metinleri (T-047b): app/lib/locales/*.json — anahtar yine Japonca kaynak metin.
import TR_PAGES from "./locales/tr.json";
import EN_PAGES from "./locales/en.json";

export const DICTS: Record<Exclude<Lang, "ja">, Dict> = {
  tr: { ...(TR_PAGES as Dict), ...TR },
  en: { ...(EN_PAGES as Dict), ...EN },
};

export function translate(lang: Lang, ja: string, vars?: Record<string, unknown>): string {
  let s = lang === "ja" ? ja : (DICTS[lang][ja] || ja);
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(String(v));
  return s;
}

/**
 * Hook gerektirmeyen çeviri: geçerli dil modül düzeyinde tutulur (LangProvider ayarlar).
 * Dil değişince LangProvider ağacı yeniden kurar (key), böylece T() çağrıları yeni dille çalışır.
 */
let current: Lang = "ja";
export function setCurrentLang(l: Lang) { current = l; }
export function currentLang(): Lang { return current; }
export function T(ja: string, vars?: Record<string, unknown>): string {
  return translate(current, ja, vars);
}
