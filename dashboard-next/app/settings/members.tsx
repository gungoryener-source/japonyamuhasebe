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
          <span className="text-slate-500">この帳簿には</span>
          <Badge tone="info" icon={false}>{ROLE_LABEL[role]}</Badge>
          <span className="text-slate-500">として参加しています（{ROLE_HINT[role]}）。メンバーの管理はオーナーのみ行えます。</span>
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
    try { await fn(); } catch (e) { toast(`失敗しました: ${e instanceof Error ? e.message : e}`); } finally { setBusy(null); }
  };

  const issue = () => run("issue", async () => {
    if (!live) {
      setIssued({ code: "iv_DEMOxxxxxxxxxxxxxxxxxxxx", role: newRole, expires_at: new Date(Date.now() + 7 * 864e5).toISOString() });
      return toast("招待コードを発行しました（デモ）");
    }
    const r = await api.teamInvite(newRole);
    setIssued(r);
    await load();
    toast("招待コードを発行しました");
  });

  const revokeInvite = (id: string) => run(`inv:${id}`, async () => {
    if (live) await api.teamRevokeInvite(id);
    setInvites((p) => p.filter((i) => i.id !== id));
    toast(live ? "招待を取り消しました" : "招待を取り消しました（デモ）");
  });

  const setRole = (m: ApiMember, role: MemberRole) => run(`role:${m.account_id}`, async () => {
    if (live) await api.teamSetRole(m.account_id, role);
    setMembers((p) => p.map((x) => (x.account_id === m.account_id ? { ...x, role } : x)));
    toast(`${m.email} を${ROLE_LABEL[role]}に変更しました${live ? "" : "（デモ）"}`);
  });

  const remove = (m: ApiMember) => run(`rm:${m.account_id}`, async () => {
    if (live) await api.teamRemove(m.account_id);
    setMembers((p) => p.filter((x) => x.account_id !== m.account_id));
    setConfirmId(null);
    toast(`${m.email} を帳簿から外しました${live ? "" : "（デモ）"}`);
  });

  const copy = async (text: string, label: string) => {
    try { await navigator.clipboard.writeText(text); toast(`${label}をコピーしました`); } catch { toast(text); }
  };
  const link = issued ? joinLink(typeof location === "undefined" ? "" : location.origin, issued.code) : "";

  return (
    <Card title="メンバー" en="Team" right={<Users size={16} className="text-mint" />} className="lg:col-span-2">
      <div className="grid gap-4 lg:grid-cols-5">
        {/* 招待 */}
        <div className="space-y-2 text-xs lg:col-span-2">
          <p className="font-bold text-slate-600">メンバーを招待</p>
          <div className="space-y-1.5">
            {MEMBER_ROLES.map((r) => (
              <label key={r} className={cx("flex cursor-pointer gap-2 rounded-lg border px-3 py-2", newRole === r ? "border-navy bg-slate-50" : "border-slate-200")}>
                <input type="radio" name="invite-role" checked={newRole === r} onChange={() => setNewRole(r)} className="mt-0.5 accent-[#1E293B]" />
                <span>
                  <span className="block font-bold text-navy">{ROLE_LABEL[r]}</span>
                  <span className="block text-[10px] text-slate-400">{ROLE_HINT[r]}</span>
                </span>
              </label>
            ))}
          </div>
          <Btn kind="primary" onClick={issue} disabled={busy !== null}>
            {busy === "issue" ? <LoaderCircle size={13} className="animate-spin" /> : <UserPlus size={13} />}招待コードを発行
          </Btn>
          {issued && (
            <div className="space-y-1.5 rounded-lg border border-mint-100 bg-mint-50/60 p-3" role="status">
              <p className="font-bold text-mint-700">{ROLE_LABEL[issued.role]}の招待コード（{shortJST(issued.expires_at)} まで・1回限り）</p>
              <CopyRow value={issued.code} onCopy={() => copy(issued.code, "招待コード")} />
              <CopyRow value={link} onCopy={() => copy(link, "招待リンク")} />
              <p className="text-[10px] text-amber-700">このコードは今だけ表示されます。メールやチャットで相手に送ってください。相手はメールアドレスでログインして参加します。</p>
            </div>
          )}
        </div>

        {/* メンバー一覧・未使用の招待 */}
        <div className="space-y-3 text-xs lg:col-span-3">
          {error && <p className="rounded-lg bg-amber-50 px-3 py-2 text-amber-800">メンバーを読み込めませんでした（{error}）。</p>}
          {loading ? (
            <p className="flex items-center gap-2 text-slate-400"><LoaderCircle size={13} className="animate-spin" />読み込み中…</p>
          ) : members.length === 0 ? (
            <Empty>メンバーはまだいません。メールアドレスでログインすると、オーナーとして表示されます。</Empty>
          ) : (
            <ul className="divide-y divide-slate-100 rounded-lg border border-slate-100">
              {members.map((m) => (
                <li key={m.account_id} className="flex items-center gap-2 px-3 py-2">
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-bold text-navy" title={m.email}>{m.email}</span>
                    {m.joined_at && <span className="block text-[10px] text-slate-400">参加 {shortJST(m.joined_at)}</span>}
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
                        aria-label={`${m.email} の役割`}
                        className={selectCls + " !h-8"}
                      >
                        {MEMBER_ROLES.map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
                      </select>
                      </span>
                      {confirmId === m.account_id ? (
                        <span className="flex items-center gap-1">
                          <Btn kind="danger" onClick={() => remove(m)} disabled={busy !== null} className="h-8">
                            {busy === `rm:${m.account_id}` && <LoaderCircle size={13} className="animate-spin" />}外す
                          </Btn>
                          <Btn onClick={() => setConfirmId(null)} className="h-8">やめる</Btn>
                        </span>
                      ) : (
                        <button onClick={() => setConfirmId(m.account_id)} className="rounded p-1.5 text-slate-300 hover:text-rose-500" aria-label={`${m.email} を削除`} title="帳簿から外す">
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
              <p className="font-bold text-slate-600">未使用の招待</p>
              <ul className="divide-y divide-slate-100 rounded-lg border border-slate-100">
                {invites.map((i) => (
                  <li key={i.id} className="flex items-center gap-2 px-3 py-1.5">
                    <Badge tone="muted" icon={false}>{ROLE_LABEL[i.role]}</Badge>
                    <span className="flex-1 font-mono text-[11px] text-slate-500 tabular">{shortJST(i.expires_at)} まで有効</span>
                    <Btn onClick={() => revokeInvite(i.id)} disabled={busy !== null} className="h-7">
                      {busy === `inv:${i.id}` && <LoaderCircle size={12} className="animate-spin" />}取消
                    </Btn>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <p className="text-[10px] text-slate-400">役割の変更・削除はすぐに反映され、外したメンバーはこの帳簿にアクセスできなくなります。</p>
        </div>
      </div>
    </Card>
  );
}

function CopyRow({ value, onCopy }: { value: string; onCopy: () => void }) {
  return (
    <div className="flex items-center gap-2 rounded-md bg-white px-2 py-1 ring-1 ring-mint-100">
      <code className="min-w-0 flex-1 truncate font-mono text-[11px] text-slate-700">{value}</code>
      <button type="button" onClick={onCopy} className="text-slate-400 hover:text-navy" aria-label="コピー"><Copy size={13} /></button>
    </div>
  );
}
