"use client";

/**
 * /connect#tk_xxx — LINE「パネル」komutunun verdiği bağlantı.
 * - Hesapla oturum açıksa (GET /auth/me → account): kod, onaydan sonra POST /auth/link-line ile hesaba bağlanır (T-040b).
 * - Değilse eski davranış: kod token olarak tarayıcıya kaydedilir ve panele dönülür.
 */
import { useEffect, useState } from "react";
import { KeyRound, LoaderCircle } from "lucide-react";
import { api, setToken, getToken } from "../lib/api";
import { AuthCard, AuthInput, errorText, Notice, SubmitBtn } from "../components/auth";
import { T } from "../lib/i18n";

type Session = { state: "loading" } | { state: "none" } | { state: "account"; email: string };

export default function ConnectPage() {
  const [value, setValue] = useState("");
  const [session, setSession] = useState<Session>({ state: "loading" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [welcome, setWelcome] = useState(false);

  /** Hesapsız: kodu oturum token'ı olarak kullan (T-040 öncesi davranış). */
  const openWithCode = async (t: string) => {
    setBusy(true);
    setError(null);
    setToken(t);
    try {
      await api.profile();
      location.href = "/";
    } catch {
      setToken(null);
      setError(T("接続コードが正しくないか、サーバーに接続できません。"));
      setBusy(false);
    }
  };

  /** Hesap açık: LINE帳簿をアカウントに連携. Başarıda yeni token gelir, eskileri sunucuda iptal edilir. */
  const link = async (t: string) => {
    setBusy(true);
    setError(null);
    try {
      const r = await api.linkLine(t);
      setToken(r.token);
      location.href = "/";
    } catch (e) {
      setError(errorText(e));
      setBusy(false);
    }
  };

  const submit = () => {
    const t = value.trim();
    if (!t.startsWith("tk_")) { setError(T("接続コードは「tk_」で始まります。LINE で「パネル」と送って取得してください。")); return; }
    if (session.state === "account") link(t);
    else openWithCode(t);
  };

  useEffect(() => {
    const h = location.hash.slice(1);
    if (h) history.replaceState(null, "", "/connect/"); // kod adres çubuğunda kalmasın
    setWelcome(new URLSearchParams(location.search).has("welcome"));
    const code = h.startsWith("tk_") ? h : "";
    if (code) setValue(code);
    const resolve = async (): Promise<Session> => {
      if (!getToken()) return { state: "none" };
      try {
        const me = await api.me();
        return me.account ? { state: "account", email: me.account.email } : { state: "none" };
      } catch {
        return { state: "none" }; // eski sunucu / geçersiz token: hesapsız akış
      }
    };
    resolve().then((s) => {
      setSession(s);
      // Hesapsız oturumda LINE bağlantısı eskisi gibi doğrudan açılır; hesapta onay beklenir.
      if (code && s.state === "none") openWithCode(code);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (session.state === "loading")
    return (
      <main className="grid min-h-screen place-items-center bg-[#F9FAFB]">
        <LoaderCircle size={20} className="animate-spin text-slate-400" />
      </main>
    );

  const account = session.state === "account";
  return (
    <AuthCard
      icon={<KeyRound size={18} />}
      title={account ? T("LINEの帳簿をアカウントに連携") : T("帳簿に接続")}
      sub={T("LINE で「パネル」と送ると接続コードが届きます")}
      onSubmit={submit}
      footer={account
        ? <a href="/" className="font-bold text-navy hover:underline">{T("あとで連携する")}</a>
        : <><a href="/login/?next=/connect/" className="font-bold text-navy hover:underline">{T("ログイン")}</a><a href="/signup/" className="hover:text-navy">{T("新規登録")}</a></>}
    >
      {welcome && account && <Notice tone="ok">{T("アカウントを登録しました。LINE で記録している場合は、接続コードで帳簿を連携できます。")}</Notice>}
      {account && (
        <p className="rounded-lg bg-slate-50 px-3 py-2 text-[11px] text-slate-500">
          {T("ログイン中：")}<span className="font-bold text-navy">{session.email}</span><br />
          {T("連携すると、LINE で記録した帳簿がこのアカウントの帳簿になります。現在の帳簿にデータがある場合は連携できません。")}
        </p>
      )}
      <AuthInput label={T("接続コード")} value={value} onChange={(e) => setValue(e.target.value)} placeholder="tk_..." autoComplete="off" spellCheck={false}
        className="font-mono" />
      {error && <Notice tone="error">{error}</Notice>}
      <SubmitBtn busy={busy}>{account ? T("連携する") : T("接続する")}</SubmitBtn>
      {!account && (
        <p className="text-[10px] leading-relaxed text-slate-400">
          {T("アカウントをお持ちの方は、ログインしてからコードを入力すると LINE の帳簿をアカウントに連携できます。")}
        </p>
      )}
    </AuthCard>
  );
}
