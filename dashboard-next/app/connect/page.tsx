"use client";

/** /connect#tk_xxx — LINE「パネル」komutunun verdiği bağlantı. Token tarayıcıya kaydedilir ve panele dönülür. */
import { useEffect, useState } from "react";
import { KeyRound, LoaderCircle } from "lucide-react";
import { api, setToken } from "../lib/api";

export default function ConnectPage() {
  const [value, setValue] = useState("");
  const [state, setState] = useState<"idle" | "checking" | "error">("idle");

  const connect = async (token: string) => {
    const t = token.trim();
    if (!t.startsWith("tk_")) { setState("error"); return; }
    setState("checking");
    setToken(t);
    try {
      await api.profile();
      history.replaceState(null, "", "/connect");
      location.href = "/";
    } catch {
      setToken(null);
      setState("error");
    }
  };

  useEffect(() => {
    const h = location.hash.slice(1);
    if (h) connect(h);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main className="grid min-h-screen place-items-center p-4">
      <form
        onSubmit={(e) => { e.preventDefault(); connect(value); }}
        className="w-full max-w-sm space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <div className="flex items-center gap-2.5">
          <div className="grid h-9 w-9 place-items-center rounded-lg bg-navy text-mint"><KeyRound size={18} /></div>
          <div>
            <h1 className="text-sm font-bold text-navy">帳簿に接続</h1>
            <p className="text-[11px] text-slate-400">LINE で「パネル」と送ると接続コードが届きます</p>
          </div>
        </div>
        <label className="block space-y-1 text-xs">
          <span className="font-bold text-slate-600">接続コード</span>
          <input
            id="token"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="tk_..."
            autoComplete="off"
            className="h-10 w-full rounded-lg border border-slate-200 px-3 font-mono text-sm outline-none focus:border-navy"
          />
        </label>
        {state === "error" && <p className="rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-700">接続コードが正しくないか、サーバーに接続できません。</p>}
        <button disabled={state === "checking"} className="flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-navy text-sm font-bold text-white hover:bg-navy-700 disabled:opacity-60">
          {state === "checking" && <LoaderCircle size={15} className="animate-spin" />}接続する
        </button>
        <a href="/" className="block text-center text-[11px] text-slate-400 hover:text-navy">デモデータで見る</a>
      </form>
    </main>
  );
}
