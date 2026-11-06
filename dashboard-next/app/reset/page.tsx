"use client";

/**
 * /reset — parola sıfırlama.
 * Hash'te `rs_…` token varsa yeni parola formu (POST /auth/password-reset/confirm), yoksa e-posta ile istek formu.
 */
import { useEffect, useState } from "react";
import { KeyRound } from "lucide-react";
import { auth, PASSWORD_MAX, PASSWORD_MIN, setToken } from "../lib/api";
import { AuthCard, AuthInput, EMAIL_RE, errorText, Notice, SubmitBtn } from "../components/auth";

export default function ResetPage() {
  const [resetToken, setResetToken] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    const h = location.hash.slice(1);
    if (h.startsWith("rs_")) {
      setResetToken(h);
      history.replaceState(null, "", "/reset/"); // token adres çubuğunda/geçmişte kalmasın
    }
  }, []);

  const request = async () => {
    if (!EMAIL_RE.test(email.trim())) { setError("メールアドレスを正しく入力してください。"); return; }
    setBusy(true);
    setError(null);
    try {
      await auth.resetRequest(email.trim());
      setDone(true);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  };

  const confirmReset = async () => {
    if (password.length < PASSWORD_MIN) { setError(`パスワードは${PASSWORD_MIN}文字以上にしてください。`); return; }
    if (password.length > PASSWORD_MAX) { setError(`パスワードは${PASSWORD_MAX}文字以内にしてください。`); return; }
    if (password !== confirm) { setError("確認用パスワードが一致しません。"); return; }
    setBusy(true);
    setError(null);
    try {
      await auth.resetConfirm(resetToken!, password);
      setToken(null); // sunucu tüm oturumları kapattı
      setDone(true);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  };

  const footer = <a href="/login/" className="font-bold text-navy hover:underline">ログインへ戻る</a>;

  if (resetToken)
    return (
      <AuthCard icon={<KeyRound size={18} />} title="新しいパスワードの設定" sub="Reset password" onSubmit={done ? undefined : confirmReset} footer={footer}>
        {done ? (
          <>
            <Notice tone="ok">パスワードを変更しました。すべての端末からログアウトしています。新しいパスワードでログインしてください。</Notice>
            <a href="/login/" className="flex h-10 w-full items-center justify-center rounded-lg bg-navy text-sm font-bold text-white hover:bg-navy-700">ログイン</a>
          </>
        ) : (
          <>
            <AuthInput label="新しいパスワード" type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)}
              hint={`${PASSWORD_MIN}文字以上`} />
            <AuthInput label="新しいパスワード（確認）" type="password" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
            {error && <Notice tone="error">{error}</Notice>}
            <SubmitBtn busy={busy}>変更する</SubmitBtn>
          </>
        )}
      </AuthCard>
    );

  return (
    <AuthCard icon={<KeyRound size={18} />} title="パスワードの再設定" sub="再設定用のリンクをメールでお送りします" onSubmit={done ? undefined : request} footer={footer}>
      {done ? (
        <Notice tone="ok">
          入力されたメールアドレスが登録されている場合、再設定用のリンクを送信しました。リンクの有効期限は1時間です。
        </Notice>
      ) : (
        <>
          <AuthInput label="メールアドレス" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.jp" />
          {error && <Notice tone="error">{error}</Notice>}
          <SubmitBtn busy={busy}>リンクを送信</SubmitBtn>
        </>
      )}
    </AuthCard>
  );
}
