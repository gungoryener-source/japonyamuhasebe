"use client";

/** T-065b/T-065c: 訂正・削除の履歴ドロワー（電子帳簿保存法）。誰が・いつ・何を変えたか。取引・仕切書で共用。 */
import { useEffect, useState, type ReactNode } from "react";
import type { ApiAuditRow } from "../lib/api";
import { T } from "../lib/i18n";
import { ROLE_LABEL, type Role } from "../lib/team";
import { Badge, Empty } from "./ui";
import { useShell } from "./shell";

const ACTION_LABEL: Record<ApiAuditRow["action"], string> = { create: "登録", update: "訂正", delete: "削除" };
const KIND_LABEL: Record<string, string> = { line: "LINE", whatsapp: "WhatsApp", bank: "銀行明細", web: "Web" };

function actorText(r: ApiAuditRow): string {
  if (r.actor_kind !== "web") return KIND_LABEL[r.actor_kind] ?? r.actor ?? "—";
  const role = r.actor_role in ROLE_LABEL ? T(ROLE_LABEL[r.actor_role as Role]) : r.actor_role;
  if (r.actor_former) return T("{a}（退出したメンバー）", { a: role });
  const who = r.actor_is_me ? T("あなた") : r.actor_email;
  return who ? `${who}（${role}）` : role;
}

export default function HistoryDrawer({ subtitle, load, demo, fieldLabels, fmt, emptyText, onClose }: {
  subtitle: ReactNode; load: () => Promise<ApiAuditRow[]>; demo: ApiAuditRow[];
  fieldLabels: Record<string, string>; fmt: (k: string, v: unknown) => string; emptyText: string; onClose: () => void;
}) {
  const { live } = useShell();
  const [rows, setRows] = useState<ApiAuditRow[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    if (!live) { setRows(demo); return; }
    load().then(setRows).catch((e) => setErr(e instanceof Error ? e.message : String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [live]);

  return (
    <div className="fixed inset-0 z-[65] flex justify-end bg-slate-900/40" onMouseDown={onClose}>
      <div onMouseDown={(e) => e.stopPropagation()} className="flex h-full w-full max-w-lg flex-col bg-white shadow-2xl" role="dialog" aria-label={T("訂正・削除の履歴")}>
        <div className="flex h-14 items-center border-b border-slate-200 px-5">
          <h3 className="text-sm font-bold text-navy">{T("訂正・削除の履歴")} <span className="text-[10px] font-normal text-slate-400">History</span></h3>
          <button type="button" onClick={onClose} className="ml-auto text-xs text-slate-400 hover:text-navy">{T("閉じる")}</button>
        </div>
        <div className="flex-1 space-y-3 overflow-y-auto p-5 text-xs">
          <p className="text-slate-500">{subtitle}</p>
          {!live && <p className="text-[11px] text-slate-400">{T("デモでは登録の記録のみ表示されます。")}</p>}
          {err && <p className="rounded-lg bg-rose-50 px-3 py-2 text-rose-700">{T("履歴を読み込めませんでした: {a}", { a: err })}</p>}
          {!rows && !err && <p className="text-slate-400">{T("読み込み中…")}</p>}
          {rows && rows.length === 0 && <Empty>{emptyText}</Empty>}
          <ol className="space-y-2">
            {rows?.map((h) => (
              <li key={h.id} className="rounded-lg border border-slate-100 p-3">
                <div className="flex items-center gap-2">
                  <Badge tone={h.action === "delete" ? "bad" : h.action === "update" ? "warn" : "ok"} icon={false}>{T(ACTION_LABEL[h.action])}</Badge>
                  <span className="font-mono text-[11px] text-slate-500 tabular">{h.created_at.slice(0, 16).replace("T", " ")}</span>
                  <span className="ml-auto truncate text-[11px] text-slate-500">{actorText(h)}</span>
                </div>
                {h.action === "update" && h.changed.filter((k) => fieldLabels[k]).length > 0 && (
                  <table className="mt-2 w-full text-[11px]">
                    <tbody>
                      {h.changed.filter((k) => fieldLabels[k]).map((k) => (
                        <tr key={k}>
                          <td className="w-24 py-0.5 text-slate-400">{T(fieldLabels[k])}</td>
                          <td className="py-0.5 text-slate-500 line-through">{fmt(k, h.before?.[k])}</td>
                          <td className="px-1 text-slate-300">→</td>
                          <td className="py-0.5 font-semibold text-navy">{fmt(k, h.after?.[k])}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </li>
            ))}
          </ol>
          <p className="text-[10px] text-slate-400">{T("訂正・削除の記録は消去できません（電子帳簿保存法）。")}</p>
        </div>
      </div>
    </div>
  );
}
