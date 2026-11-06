/**
 * 法務ページ（/legal/terms, /legal/privacy, /legal/tokushoho）の本文テンプレート（T-043）。
 *
 * - 販売業者情報は環境変数（ビルド時, NEXT_PUBLIC_LEGAL_*）から。未設定の項目は「要確認」と表示する（Q-12）。
 * - 各ページの冒頭に DRAFT_NOTICE を表示する。Q-12 が回答され、専門家の確認が済むまで外さない。
 * - `todo: true` の段落は内容が未確定（専門家確認待ち）で、画面上で「要確認」バッジが付く。
 * - JSX を含まない純粋な TS（scripts/check-legal.mjs から読み込んで検査する）。
 */

export const DRAFT_NOTICE = "本ページは確認中のドラフトです";
export const PENDING = "要確認";
/** 最終更新日（文面を変えたら更新する） */
export const LEGAL_UPDATED = "2026年11月7日";
export const SERVICE_NAME = "J-SaaS 会計";

export type Seller = {
  name: string;      // 販売業者
  manager: string;   // 運営統括責任者
  address: string;   // 所在地
  phone: string;     // 電話番号
  email: string;     // メールアドレス
};

type Env = Record<string, string | undefined>;

/** 環境変数から販売業者情報を読む。空・未設定は PENDING。 */
export function sellerFrom(env: Env): Seller {
  const v = (k: string) => (env[k] ?? "").trim() || PENDING;
  return {
    name: v("NEXT_PUBLIC_LEGAL_SELLER"),
    manager: v("NEXT_PUBLIC_LEGAL_MANAGER"),
    address: v("NEXT_PUBLIC_LEGAL_ADDRESS"),
    phone: v("NEXT_PUBLIC_LEGAL_PHONE"),
    email: v("NEXT_PUBLIC_LEGAL_EMAIL"),
  };
}

// Next.js は NEXT_PUBLIC_* を「process.env.NAME」の字句でのみビルド時に埋め込むため、個別に参照する。
export const SELLER: Seller = sellerFrom({
  NEXT_PUBLIC_LEGAL_SELLER: process.env.NEXT_PUBLIC_LEGAL_SELLER,
  NEXT_PUBLIC_LEGAL_MANAGER: process.env.NEXT_PUBLIC_LEGAL_MANAGER,
  NEXT_PUBLIC_LEGAL_ADDRESS: process.env.NEXT_PUBLIC_LEGAL_ADDRESS,
  NEXT_PUBLIC_LEGAL_PHONE: process.env.NEXT_PUBLIC_LEGAL_PHONE,
  NEXT_PUBLIC_LEGAL_EMAIL: process.env.NEXT_PUBLIC_LEGAL_EMAIL,
});

export type Block = { text?: string; items?: string[]; todo?: boolean };
export type Section = { heading: string; blocks: Block[] };
export type Row = { label: string; value: string; todo?: boolean };
export type LegalDoc = { slug: "terms" | "privacy" | "tokushoho"; title: string; en: string; intro: string; sections: Section[]; rows?: Row[] };

const contact = (s: Seller) => `お問い合わせ窓口：${s.name}（メール：${s.email}）`;

export function termsDoc(s: Seller): LegalDoc {
  return {
    slug: "terms",
    title: "利用規約",
    en: "Terms of Service",
    intro: `この利用規約（以下「本規約」）は、${s.name}（以下「当社」）が提供するクラウド会計サービス「${SERVICE_NAME}」（LINE・WhatsApp 連携およびウェブ管理画面を含み、以下「本サービス」）の利用条件を定めるものです。利用者は本規約に同意のうえ本サービスを利用するものとします。`,
    sections: [
      { heading: "第1条（適用）", blocks: [{ text: "本規約は、利用者と当社との間の本サービスの利用に関わる一切の関係に適用されます。当社が本サービス上で掲載する個別のルールは本規約の一部を構成します。" }] },
      { heading: "第2条（アカウント）", blocks: [
        { text: "利用者は、正確な情報を登録し、メールアドレスおよびパスワード、LINE で発行される接続コード等の認証情報を自己の責任で管理するものとします。" },
        { text: "認証情報の第三者による使用により生じた損害について、当社に故意または重大な過失がある場合を除き、当社は責任を負いません。" },
      ] },
      { heading: "第3条（料金および支払方法）", blocks: [
        { text: "有料プランの料金、支払方法および支払時期は、料金プランページおよび「特定商取引法に基づく表記」に定めるとおりとします。" },
        { text: "有料プランは月単位の自動更新とし、利用者が解約手続を行った場合、当該請求期間の末日をもって終了します。日割りでの返金は行いません。", todo: true },
      ] },
      { heading: "第4条（本サービスの性質）", blocks: [
        { text: "本サービスは、帳簿付け、適格請求書の作成、消費税および所得税の概算、確定申告の準備を補助するものであり、税務代理、税務書類の作成または税務相談（税理士法第2条）を行うものではありません。" },
        { text: "レシートの自動読み取り（OCR）、勘定科目の推定および税額の計算結果は参考値です。申告・納税の前に、利用者自身または税理士が内容を確認してください。" },
      ] },
      { heading: "第5条（利用者データ）", blocks: [
        { text: "利用者が登録した取引、請求書、レシート画像その他のデータ（以下「利用者データ」）の権利は利用者に帰属します。当社は、本サービスの提供・改善およびプライバシーポリシーに定める目的の範囲でのみ利用者データを取り扱います。" },
        { text: "帳簿書類の保存義務は利用者にあります。利用者は、必要に応じて CSV 等の形式で利用者データを出力し保管してください。" },
      ] },
      { heading: "第6条（禁止事項）", blocks: [{ items: [
        "法令または公序良俗に違反する行為",
        "虚偽の取引記録や請求書の作成など、不正な目的での利用",
        "他人の認証情報の使用、または不正アクセスを試みる行為",
        "本サービスのサーバーやネットワークに過度な負荷をかける行為",
        "本サービスの運営を妨害する行為、その他当社が不適切と判断する行為",
      ] }] },
      { heading: "第7条（提供の停止・変更）", blocks: [{ text: "当社は、保守点検、障害、天災その他やむを得ない事由がある場合、事前の通知なく本サービスの全部または一部の提供を停止または変更できるものとします。" }] },
      { heading: "第8条（退会）", blocks: [{ text: "利用者は、当社所定の方法により退会できます。退会後の利用者データの取扱いはプライバシーポリシーに定めるとおりとします。" }] },
      { heading: "第9条（免責）", blocks: [
        { text: "当社は、本サービスに起因して利用者に生じた損害について、当社の故意または重大な過失による場合を除き、損害の発生した月に利用者が当社に支払った利用料金の額を上限として賠償責任を負います。", todo: true },
        { text: "消費者契約法その他の法令により前項が適用されない場合は、当該法令の定めに従います。" },
      ] },
      { heading: "第10条（規約の変更）", blocks: [{ text: "当社は、民法第548条の4の規定に基づき本規約を変更できるものとします。変更する場合は、効力発生日および変更内容を本サービス上で事前に周知します。" }] },
      { heading: "第11条（準拠法・管轄）", blocks: [{ text: "本規約は日本法に準拠します。本サービスに関して紛争が生じた場合、当社の所在地を管轄する地方裁判所を第一審の専属的合意管轄裁判所とします。", todo: true }] },
      { heading: "お問い合わせ", blocks: [{ text: contact(s) }] },
    ],
  };
}

export function privacyDoc(s: Seller): LegalDoc {
  return {
    slug: "privacy",
    title: "プライバシーポリシー",
    en: "Privacy Policy",
    intro: `${s.name}（以下「当社」）は、「${SERVICE_NAME}」（以下「本サービス」）における個人情報を、個人情報の保護に関する法律（以下「個人情報保護法」）その他の法令に従い、以下のとおり取り扱います。`,
    sections: [
      { heading: "1. 取得する情報", blocks: [{ items: [
        "アカウント情報：メールアドレス、パスワード（ハッシュ化して保存し、当社は平文を保持しません）",
        "連携情報：LINE のユーザー識別子、WhatsApp の電話番号",
        "会計データ：取引（日付・金額・取引先・勘定科目・税率）、請求書（宛先・明細・登録番号）、取り込んだ銀行明細、事業者情報",
        "レシート画像：読み取りのために送信された画像（読み取り処理に使用し、現時点では画像そのものは保存しません）",
        "決済情報：プラン、契約状態、決済サービス上の顧客 ID（カード番号は当社では保持せず、決済代行会社が管理します）",
        "利用ログ：アクセス日時、IP アドレス、エラー情報",
      ] }] },
      { heading: "2. 利用目的", blocks: [{ items: [
        "本サービスの提供（記帳、請求書作成、税額計算、データ出力）",
        "本人確認、ログイン、パスワード再設定などのアカウント管理",
        "料金の請求および有料プランの管理",
        "お問い合わせへの対応、重要なお知らせの送付",
        "不正利用の防止、障害対応およびセキュリティの確保",
        "個人を特定できない統計情報としての本サービスの改善",
      ] }] },
      { heading: "3. 第三者提供", blocks: [{ text: "当社は、法令に基づく場合など個人情報保護法第27条第1項各号に該当する場合を除き、あらかじめ本人の同意を得ることなく個人データを第三者に提供しません。なお、次項の業務委託先への提供は第三者提供に該当しません（同条第5項第1号）。" }] },
      { heading: "4. 業務委託および外国にある第三者への提供", blocks: [
        { text: "当社は、本サービスの運営に必要な範囲で、以下の事業者に個人データの取扱いを委託しています。" },
        { items: [
          "Render Services, Inc.（米国）— サーバーおよびデータベースの運用。データはシンガポールのデータセンターに保存されます。",
          "Stripe, Inc.（米国）およびそのグループ会社 — 有料プランの決済処理",
          "LINE ヤフー株式会社（日本）— LINE でのメッセージ送受信",
          "Meta Platforms, Inc.（米国）— WhatsApp でのメッセージ送受信（WhatsApp 連携を利用する場合のみ）",
          "Anthropic, PBC（米国）— 自動読み取りが失敗したレシート画像の補助的な読み取り（当該機能を有効にしている場合のみ）",
          "メール配信事業者 — パスワード再設定等のメール送信（事業者は選定中）",
        ] },
        { text: "外国にある第三者への提供にあたっては、個人情報保護法第28条および施行規則に基づき、提供先の国名、当該国の個人情報保護制度、提供先が講じる措置に関する情報を本人に提供します。各国の制度については個人情報保護委員会が公表する情報をご参照ください。", todo: true },
      ] },
      { heading: "5. 保存期間", blocks: [
        { text: "会計データは、利用者が帳簿書類の保存義務（法人税法・所得税法・電子帳簿保存法等）を果たせるよう、法令で定められた保存期間を考慮して保存します。具体的な期間は確認中です。", todo: true },
        { text: "退会後の会計データは、データ出力の猶予期間の経過後に削除します。法令上保存が必要な情報はこの限りではありません。", todo: true },
      ] },
      { heading: "6. 安全管理措置", blocks: [{ items: [
        "通信の暗号化（HTTPS）、パスワードのハッシュ化",
        "アクセストークンによる利用者ごとのデータ分離と、有効なトークン数の上限設定",
        "管理用機能へのアクセス制限、決済通知の署名検証",
        "委託先の選定と監督",
      ] }] },
      { heading: "7. 開示等の請求", blocks: [{ text: `本人は、当社が保有する保有個人データについて、利用目的の通知、開示、訂正・追加・削除、利用停止・消去、第三者提供の停止、第三者提供記録の開示を請求できます（個人情報保護法第32条〜第35条）。請求は下記の窓口までご連絡ください。本人確認のうえ、法令に従い遅滞なく対応します。` }] },
      { heading: "8. Cookie 等", blocks: [{ text: "ウェブ管理画面では、ログイン状態を保持するためにブラウザのローカルストレージにアクセストークンを保存します。広告目的のトラッキングは行いません。" }] },
      { heading: "9. 改定", blocks: [{ text: "本ポリシーを改定する場合は、本サービス上で周知します。" }] },
      { heading: "10. お問い合わせ窓口", blocks: [{ text: `${contact(s)}／所在地：${s.address}` }] },
    ],
  };
}

export function tokushohoDoc(s: Seller): LegalDoc {
  const p = (v: string) => v === PENDING;
  return {
    slug: "tokushoho",
    title: "特定商取引法に基づく表記",
    en: "Legal Notice (Specified Commercial Transactions Act)",
    intro: `「${SERVICE_NAME}」の有料プランに関する表示です。`,
    rows: [
      { label: "販売業者", value: s.name, todo: p(s.name) },
      { label: "運営統括責任者", value: s.manager, todo: p(s.manager) },
      { label: "所在地", value: s.address, todo: p(s.address) },
      { label: "電話番号", value: s.phone, todo: p(s.phone) },
      { label: "メールアドレス", value: s.email, todo: p(s.email) },
      { label: "販売価格", value: "各プランの価格は料金プランページに表示します（現在の価格は仮のもので、正式な価格は確定後に表示します）。", todo: true },
      { label: "商品代金以外の必要料金", value: "本サービスの利用に必要なインターネット接続料金・通信料金は利用者の負担となります。" },
      { label: "支払方法", value: "クレジットカード（決済代行：Stripe）" },
      { label: "支払時期", value: "お申し込み時に初回分を決済し、以後は毎月の契約更新日に自動で決済されます。" },
      { label: "提供時期", value: "決済完了後、直ちにご利用いただけます。" },
      { label: "解約・返品", value: "料金プランページからいつでも解約できます。解約は当該請求期間の末日に効力を生じ、それまでは有料プランをご利用いただけます。サービスの性質上、提供開始後の返金には応じません。", todo: true },
      { label: "動作環境", value: "最新版の主要ブラウザ（Chrome, Safari, Edge, Firefox）および LINE アプリ" },
    ],
    sections: [],
  };
}

export const LEGAL_PAGES = [
  { slug: "terms", title: "利用規約", href: "/legal/terms/" },
  { slug: "privacy", title: "プライバシーポリシー", href: "/legal/privacy/" },
  { slug: "tokushoho", title: "特定商取引法に基づく表記", href: "/legal/tokushoho/" },
] as const;

/** 特定商取引法第11条・施行規則で表示が求められる項目（表の行ラベル）。check-legal で検査する。 */
export const TOKUSHOHO_REQUIRED = [
  "販売業者", "運営統括責任者", "所在地", "電話番号", "メールアドレス", "販売価格",
  "商品代金以外の必要料金", "支払方法", "支払時期", "提供時期", "解約・返品",
] as const;
