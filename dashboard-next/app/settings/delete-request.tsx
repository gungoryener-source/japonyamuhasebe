"use client";

/**
 * 設定 → 「アカウントの削除」カード（T-046b）。API: GET|POST /account/delete-request（owner のみ）。
 * 申請しても即時削除はされません（運営が確認のうえ対応・docs/OPERATIONS.md）。
 * 2段階確認：①「削除を申請する」→ ② 確認文を入力して「申請を確定」。有料プランが更新予定なら先に解約を案内。
 */
import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, UserX } from "lucide-react";
import { api, type ApiDeleteRequest } from "../lib/api";
import { useShell } from "../components/shell";
import { Badge, Btn, Card, inputCls } from "../components/ui";
import { useT } from "../components/lang";
import { shortJST } from "../lib/team";

const CONFIRM_WORD = "削除";

export function DeleteRequestCard() {
  const { live, mode, role, toast } = useShell();
  const t = useT();
  const [state, setState] = useState<ApiDeleteRequest | null>(null);
  const [step, setStep] = useState<0 | 1>(0);
  const [word, setWord] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!live || role !== "owner") return;
    api.deleteRequest().then(setState).catch(() => {});
  }, [live, role]);

  if (mode === "loading" || (live && role !== "owner")) return null;

  const submit = async () => {
    if (word.trim() !== CONFIRM_WORD) return;
    if (!live) { toast(t("削除の申請はデモでは送信されません")); setStep(0); setWord(""); return; }
    setBusy(true);
    try {
      setState(await api.requestDelete());
      toast(t("アカウント削除を申請しました"));
      setStep(0);
      setWord("");
    } catch (err) {
      toast(t("申請に失敗しました: {e}", { e: err instanceof Error ? err.message : String(err) }));
    } finally {
      setBusy(false);
    }
  };

  const req = state?.request;
  const pending = req?.status === "pending";

  return (
    <Card title="アカウントの削除" en="Delete account" right={<UserX size={16} className="text-slate-400" />} className="lg:col-span-2">
      <div className="space-y-2 text-xs">
        {pending ? (
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="info" icon={false}><CheckCircle2 size={11} />{t("申請済み")}</Badge>
            <span className="text-slate-500">{t("申請日時")}: <span className="tabular-nums">{shortJST(req!.requested_at)}</span></span>
            <span className="min-w-0 flex-1 text-slate-500">{t("運営が内容を確認のうえ、登録メールアドレスにご連絡します。それまでは通常どおりご利用いただけます。")}</span>
          </div>
        ) : (
          <>
            <p className="text-slate-500">{t("帳簿データ（仕訳・請求書・領収書画像）とアカウントの削除を申請します。申請後すぐには削除されず、運営が確認してから対応します。削除後は復元できません。先に「全データをダウンロード」で保存しておくことをおすすめします。")}</p>
            {state?.billing_active && (
              <div className="flex flex-wrap items-center gap-2 rounded-lg bg-amber-50 px-3 py-2 text-amber-700">
                <AlertTriangle size={14} />
                <span className="min-w-0 flex-1">{t("有料プランが継続中です。削除を申請する前に、料金プランから解約してください。")}</span>
                <a href="/billing/"><Btn kind="ghost">{t("料金プランを見る")}</Btn></a>
              </div>
            )}
            {step === 0 ? (
              <div className="flex justify-end">
                <Btn kind="danger" onClick={() => setStep(1)}><UserX size={13} />{t("削除を申請する")}</Btn>
              </div>
            ) : (
              <div className="space-y-2 rounded-lg border border-rose-200 bg-rose-50/50 p-3">
                <label htmlFor="del-confirm" className="block font-bold text-rose-700">
                  {t("確認のため「{w}」と入力してください", { w: CONFIRM_WORD })}
                </label>
                <div className="flex flex-wrap items-center gap-2">
                  <input id="del-confirm" value={word} onChange={(e) => setWord(e.target.value)} className={inputCls + " max-w-[10rem]"} autoComplete="off" />
                  <Btn kind="danger" onClick={submit} disabled={busy || word.trim() !== CONFIRM_WORD} className="ml-auto">{t(busy ? "送信中…" : "申請を確定")}</Btn>
                  <Btn kind="ghost" onClick={() => { setStep(0); setWord(""); }}>{t("キャンセル")}</Btn>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </Card>
  );
}
