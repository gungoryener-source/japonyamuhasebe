"use client";

/**
 * 設定 → 「メンバー」カード（T-041b）。API: GET /team/members, POST /team/invites, DELETE /team/invites/{id},
 * PATCH|DELETE /team/members/{account_id}（すべて owner のみ）。デモモードでは静的データ。
 */
import { useEffect, useState } from "react";
import { Copy, LoaderCircle, Trash2, UserPlus, Users } from "lucide-react";
import { api, type ApiInvite, type ApiMember, type ApiNewInvite } from "../lib/api";
import { joinLink, MEMBER_ROLES, ROLE_HINT, ROLE_LABEL, shortJST, type MemberRole } from "../lib/team";
import { useShell } from "../components/shell";
import { Badge, Btn, Card, cx, Empty, selectCls } from "../components/ui";
import { T } from "../lib/i18n";

const DEMO_MEMBERS: ApiMember[] = [
  { account_id: 1, email: "owner@example.jp", role: "owner" },
  { account_id: 2, email: "zeirishi@example.jp", role: "accountant", joined_at: "2026-10-01T10:00:00+09:00" },
  { account_id: 3, email: "partner@example.jp", role: "viewer", joined_at: "2026-10-15T09:30:00+09:00" },
];
const DEMO_INVITES: ApiInvite[] = [
  { id: "0123456789ab", role: "viewer", created_at: "2026-11-01T09:00:00+09:00", expires_at: "2026-11-08T09:00:00+09:00" },
];

export function MembersCard() {
  const { live, mode, role, toast } = useShell();
  if (mode === "loading") return null;
  if (live && role !== "owner") {
    return (
      <Card title="メンバー" en="Team" right={<Users size={16} className="text-slate-400" />} className="lg:col-span-2">
        <div className="flex flex-wrap items-center gap-3 text-xs">
          <span className="text-slate-500">{T("この帳簿には")}</span>
          <Badge tone="info" icon={false}>{T(ROLE_LABEL[role])}</Badge>
          <span className="text-slate-500">{T("として参加しています（")}{ROLE_HINT[role]}{T("）。メンバーの管理はオーナーのみ行えます。")}</span>
        </div>
      </Card>
    );
  }
  return <OwnerMembers live={live} toast={toast} />;
}

function OwnerMembers({ live, toast }: { live: boolean; toast: (m: string) => void }) {
  const [members, setMembers] = useState<ApiMember[]>(live ? [] : DEMO_MEMBERS);
  const [invites, setInvites] = useState<ApiInvite[]>(live ? [] : DEMO_INVITES);
  const [loading, setLoading] = useState(live);
  const [error, setError] = useState<string | null>(null);
  const [newRole, setNewRole] = useState<MemberRole>("accountant");
  const [issued, setIssued] = useState<ApiNewInvite | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [confirmId, setConfirmId] = useState<number | null>(null);

  const load = async () => {
    if (!live) return;
    try {
      const r = await api.teamMembers();
      setMembers(r.members);
      setInvites(r.invites);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, [live]); // eslint-disable-line react-hooks/exhaustive-deps

  const run = async (key: string, fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(key);
    try { await fn(); } catch (e) { toast(T("失敗しました: {a}", { a: e instanceof Error ? e.message : e })); } finally { setBusy(null); }
  };

  const issue = () => run("issue", async () => {
    if (!live) {
      setIssued({ code: "iv_DEMOxxxxxxxxxxxxxxxxxxxx", role: newRole, expires_at: new Date(Date.now() + 7 * 864e5).toISOString() });
      return toast(T("招待コードを発行しました（デモ）"));
    }
    const r = await api.teamInvite(newRole);
    setIssued(r);
    await load();
    toast(T("招待コードを発行しました"));
  });

  const revokeInvite = (id: string) => run(`inv:${id}`, async () => {
    if (live) await api.teamRevokeInvite(id);
    setInvites((p) => p.filter((i) => i.id !== id));
    toast(live ? T("招待を取り消しました") : T("招待を取り消しました（デモ）"));
  });

  const setRole = (m: ApiMember, role: MemberRole) => run(`role:${m.account_id}`, async () => {
    if (live) await api.teamSetRole(m.account_id, role);
    setMembers((p) => p.map((x) => (x.account_id === m.account_id ? { ...x, role } : x)));
    toast(T("{a} を{b}に変更しました{c}", { a: m.email, b: T(ROLE_LABEL[role]), c: live ? "" : T("（デモ）") }));
  });

  const remove = (m: ApiMember) => run(`rm:${m.account_id}`, async () => {
    if (live) await api.teamRemove(m.account_id);
    setMembers((p) => p.filter((x) => x.account_id !== m.account_id));
    setConfirmId(null);
    toast(T("{a} を帳簿から外しました{b}", { a: m.email, b: live ? "" : T("（デモ）") }));
  });

  const copy = async (text: string, label: string) => {
    try { await navigator.clipboard.writeText(text); toast(T("{a}をコピーしました", { a: label })); } catch { toast(text); }
  };
  const link = issued ? joinLink(typeof location === "undefined" ? "" : location.origin, issued.code) : "";

  return (
    <Card title="メンバー" en="Team" right={<Users size={16} className="text-mint" />} className="lg:col-span-2">
      <div className="grid gap-4 lg:grid-cols-5">
        {/* 招待 */}
        <div className="space-y-2 text-xs lg:col-span-2">
          <p className="font-bold text-slate-600">{T("メンバーを招待")}</p>
          <div className="space-y-1.5">
            {MEMBER_ROLES.map((r) => (
              <label key={r} className={cx("flex cursor-pointer gap-2 rounded-lg border px-3 py-2", newRole === r ? "border-navy bg-slate-50" : "border-slate-200")}>
                <input type="radio" name="invite-role" checked={newRole === r} onChange={() => setNewRole(r)} className="mt-0.5 accent-[#1E293B]" />
                <span>
                  <span className="block font-bold text-navy">{T(ROLE_LABEL[r])}</span>
                  <span className="block text-[10px] text-slate-400">{T(ROLE_HINT[r])}</span>
                </span>
              </label>
            ))}
          </div>
          <Btn kind="primary" onClick={issue} disabled={busy !== null}>
            {busy === "issue" ? <LoaderCircle size={13} className="animate-spin" /> : <UserPlus size={13} />}{T("招待コードを発行")}
          </Btn>
          {issued && (
            <div className="space-y-1.5 rounded-lg border border-mint-100 bg-mint-50/60 p-3" role="status">
              <p className="font-bold text-mint-700">{ROLE_LABEL[issued.role]}{T("の招待コード（")}{shortJST(issued.expires_at)} {T("まで・1回限り）")}</p>
              <CopyRow value={issued.code} onCopy={() => copy(issued.code, T("招待コード"))} />
              <CopyRow value={link} onCopy={() => copy(link, T("招待リンク"))} />
              <p className="text-[10px] text-amber-700">{T("このコードは今だけ表示されます。メールやチャットで相手に送ってください。相手はメールアドレスでログインして参加します。")}</p>
            </div>
          )}
        </div>

        {/* メンバー一覧・未使用の招待 */}
        <div className="space-y-3 text-xs lg:col-span-3">
          {error && <p className="rounded-lg bg-amber-50 px-3 py-2 text-amber-800">{T("メンバーを読み込めませんでした（")}{error}）。</p>}
          {loading ? (
            <p className="flex items-center gap-2 text-slate-400"><LoaderCircle size={13} className="animate-spin" />{T("読み込み中…")}</p>
          ) : members.length === 0 ? (
            <Empty>{T("メンバーはまだいません。メールアドレスでログインすると、オーナーとして表示されます。")}</Empty>
          ) : (
            <ul className="divide-y divide-slate-100 rounded-lg border border-slate-100">
              {members.map((m) => (
                <li key={m.account_id} className="flex items-center gap-2 px-3 py-2">
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-bold text-navy" title={m.email}>{m.email}</span>
                    {m.joined_at && <span className="block text-[10px] text-slate-400">{T("参加")} {shortJST(m.joined_at)}</span>}
                  </span>
                  {m.role === "owner" ? (
                    <Badge tone="ok" icon={false}>{ROLE_LABEL.owner}</Badge>
                  ) : (
                    <>
                      <span className="w-28 shrink-0">
                      <select
                        value={m.role}
                        onChange={(e) => setRole(m, e.target.value as MemberRole)}
                        disabled={busy !== null}
                        aria-label={T("{a} の役割", { a: m.email })}
                        className={selectCls + " !h-8"}
                      >
                        {MEMBER_ROLES.map((r) => <option key={r} value={r}>{T(ROLE_LABEL[r])}</option>)}
                      </select>
                      </span>
                      {confirmId === m.account_id ? (
                        <span className="flex items-center gap-1">
                          <Btn kind="danger" onClick={() => remove(m)} disabled={busy !== null} className="h-8">
                            {busy === `rm:${m.account_id}` && <LoaderCircle size={13} className="animate-spin" />}{T("外す")}
                          </Btn>
                          <Btn onClick={() => setConfirmId(null)} className="h-8">{T("やめる")}</Btn>
                        </span>
                      ) : (
                        <button onClick={() => setConfirmId(m.account_id)} className="rounded p-1.5 text-slate-300 hover:text-rose-500" aria-label={T("{a} を削除", { a: m.email })} title={T("帳簿から外す")}>
                          <Trash2 size={14} />
                        </button>
                      )}
                    </>
                  )}
                </li>
              ))}
            </ul>
          )}

          {invites.length > 0 && (
            <div className="space-y-1">
              <p className="font-bold text-slate-600">{T("未使用の招待")}</p>
              <ul className="divide-y divide-slate-100 rounded-lg border border-slate-100">
                {invites.map((i) => (
                  <li key={i.id} className="flex items-center gap-2 px-3 py-1.5">
                    <Badge tone="muted" icon={false}>{T(ROLE_LABEL[i.role])}</Badge>
                    <span className="flex-1 font-mono text-[11px] text-slate-500 tabular">{shortJST(i.expires_at)} {T("まで有効")}</span>
                    <Btn onClick={() => revokeInvite(i.id)} disabled={busy !== null} className="h-7">
                      {busy === `inv:${i.id}` && <LoaderCircle size={12} className="animate-spin" />}{T("取消")}
                    </Btn>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <p className="text-[10px] text-slate-400">{T("役割の変更・削除はすぐに反映され、外したメンバーはこの帳簿にアクセスできなくなります。")}</p>
        </div>
      </div>
    </Card>
  );
}

function CopyRow({ value, onCopy }: { value: string; onCopy: () => void }) {
  return (
    <div className="flex items-center gap-2 rounded-md bg-white px-2 py-1 ring-1 ring-mint-100">
      <code className="min-w-0 flex-1 truncate font-mono text-[11px] text-slate-700">{value}</code>
      <button type="button" onClick={onCopy} className="text-slate-400 hover:text-navy" aria-label={T("コピー")}><Copy size={13} /></button>
    </div>
  );
}
