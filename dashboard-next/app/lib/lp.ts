/**
 * Tanıtım sayfası /lp içeriği (T-044). Saf TS veri — `scripts/check-lp.mjs` ve
 * `bot/tests/test_lp_plan_parity.py` bu dosyayı denetler.
 * Kural: yalnızca bugün çalışan özellikler; uydurma rakam/iddia yok (ör. 電帳法対応 → T-034 bitmeden yazılmaz).
 */

/** bot/billing.py PLANS の写し（静的ページのため API は呼ばない）。価格は確定（Q-11 / T-055、月額・税抜）。 */
export const LP_PLANS = [
  { id: "free", name: "フリー", price_jpy: 0, receipts_per_month: 30, invoices_per_month: 3,
    notes: ["LINEで記帳", "インボイス対応の請求書", "消費税・確定申告のプレビュー"] },
  { id: "personal", name: "個人", price_jpy: 980, receipts_per_month: null, invoices_per_month: null,
    notes: ["個人事業主向け", "確定申告の準備に"] },
  { id: "business", name: "法人", price_jpy: 2980, receipts_per_month: null, invoices_per_month: null,
    notes: ["小規模法人向け", "法人の決算準備に"] },
] as const;

export type LpPlan = (typeof LP_PLANS)[number];

export const yenLabel = (n: number) => (n === 0 ? "¥0" : `¥${n.toLocaleString("en-US")}`);

export const limitLabel = (n: number | null) => (n == null ? "無制限" : `月${n}件まで`);

export const HERO = {
  title: "レシートは、LINEに送るだけ。",
  lead: "写真やひとことを送ると、帳簿に自動で記録。インボイス対応の請求書づくりから、消費税・確定申告の準備までをひとつにまとめた、個人事業主と小さな会社のためのクラウド会計です。",
  flow: ["LINEでレシートを送る", "帳簿に自動で記録", "インボイス・確定申告の準備"],
};

/** 3 ana özellik kartı. ikon adı page.tsx'te lucide bileşenine eşlenir. */
export const FEATURES = [
  {
    icon: "message",
    title: "LINEでかんたん記帳",
    body: "レシートの写真を送ると文字を読み取り、日付・金額・税率を記録します。「ローソン 540円 軽減」のような短い文でも登録でき、8%と10%が混在するレシートは税率ごとに分けて記録します。",
  },
  {
    icon: "invoice",
    title: "インボイス対応の請求書",
    body: "登録番号・税率ごとの対価と消費税額を記載した適格請求書をPDFで作成。入金の記録や、銀行明細CSVとの消込もウェブ管理画面で行えます。",
  },
  {
    icon: "tax",
    title: "消費税・確定申告の準備",
    body: "消費税の概算（一般課税・簡易課税・2割特例）と所得税の概算をいつでも確認。青色申告決算書（損益計算書）のPDFや、freee・マネーフォワード・弥生向けのCSVも出力できます。",
  },
] as const;

/** Kullanım adımları (LINE ile başla). */
export const STEPS = [
  { title: "無料で登録", body: "メールアドレスとパスワードでアカウントを作成します。" },
  { title: "LINEとつなぐ", body: "公式LINEアカウントを友だち追加し、「パネル」と送って届く接続コードで帳簿をつなぎます。" },
  { title: "レシートを送る", body: "あとは写真を送るだけ。集計・請求書・申告の準備はウェブ管理画面で確認できます。" },
] as const;

export const FAQ = [
  {
    q: "無料で使えますか？",
    a: "フリープランは月30件までの経費（レシート）と月3件までの請求書を無料でご利用いただけます。有料プランへの変更・解約は料金プランのページからいつでも行えます。",
  },
  {
    q: "LINEだけで使えますか？",
    a: "記帳はLINEだけで完結します。レシートの写真か「店名 金額」を送ってください。「合計」で今月の集計、「取消」で直前の記録の削除ができます。請求書の作成や申告の準備はウェブ管理画面で行います。",
  },
  {
    q: "インボイス制度に対応していますか？",
    a: "適格請求書の記載事項（登録番号、税率ごとに区分した対価の額と消費税額など）を備えた請求書PDFを作成できます。登録番号は設定画面の事業者情報に入力してください。",
  },
  {
    q: "確定申告の書類を作れますか？",
    a: "記帳データから青色申告決算書（損益計算書）のPDFと所得税・消費税の概算を作成できます。e-Taxへの直接送信には現在対応していません。",
  },
  {
    q: "今使っている会計ソフトにデータを移せますか？",
    a: "freee・マネーフォワード・弥生の取込形式でCSVを出力できます。帳簿と請求書をまとめた全データのZIPダウンロードにも対応しています。",
  },
  {
    q: "税理士に見てもらうことはできますか？",
    a: "メンバー招待機能（招待コード）で、税理士や経理担当の方を「編集者」または「閲覧者」の権限で帳簿に招待できます。",
  },
  {
    q: "税金の相談はできますか？",
    a: "本サービスは記帳と税額計算を補助するツールであり、税務相談・税務代理（税理士法に定める業務）は行いません。表示される税額は概算です。個別の判断は税理士または税務署にご相談ください。",
  },
] as const;

export const PRICE_NOTE = "価格はすべて月額・税抜です。お支払いは Stripe（クレジットカード）で処理されます。";

export const SIGNUP_HREF = "/signup/";
export const LOGIN_HREF = "/login/";

/** 公式LINE 友だち追加 URL（ビルド時に埋め込み）。未設定ならボタンは出さず登録への導線のみ。 */
export function lineAddUrl(raw: string | undefined): string | null {
  const v = (raw ?? "").trim();
  return /^https:\/\/(lin\.ee|line\.me)\//.test(v) ? v : null;
}

export const LINE_ADD_URL = lineAddUrl(process.env.NEXT_PUBLIC_LINE_ADD_URL);
