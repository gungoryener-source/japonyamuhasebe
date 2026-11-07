"""T-056: Resend ile e-posta gönderimi (ağ yok: httpx.post taklit edilir)."""
import httpx

import accounts


def test_no_provider_only_logs(monkeypatch):
    monkeypatch.delenv("MAIL_PROVIDER", raising=False)
    called = []
    monkeypatch.setattr(httpx, "post", lambda *a, **k: called.append(1))
    assert accounts.send_mail("taro@example.jp", "件名", "本文") is False and not called


def test_resend_payload(monkeypatch):
    monkeypatch.setenv("MAIL_PROVIDER", "Resend")
    monkeypatch.setenv("MAIL_API_KEY", "re_test")
    monkeypatch.setenv("MAIL_FROM", "てがる会計 <no-reply@tegaru.jp>")
    seen = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        seen.update(url=url, headers=headers, json=json)
        return httpx.Response(200, json={"id": "x"})

    monkeypatch.setattr(httpx, "post", fake_post)
    assert accounts.send_mail("taro@example.jp", "【手軽会計】パスワード再設定", "リンク") is True
    assert seen["url"] == "https://api.resend.com/emails"
    assert seen["headers"]["Authorization"] == "Bearer re_test"
    assert seen["json"] == {"from": "てがる会計 <no-reply@tegaru.jp>", "to": ["taro@example.jp"],
                            "subject": "【手軽会計】パスワード再設定", "text": "リンク"}


def test_failures_do_not_raise(monkeypatch, caplog):
    monkeypatch.setenv("MAIL_PROVIDER", "resend")
    monkeypatch.setenv("MAIL_API_KEY", "re_test")
    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(422, json={"message": "bad from"}))
    assert accounts.send_mail("taro@example.jp", "s", "secret-link") is False
    def boom(*a, **k):
        raise httpx.ConnectError("down")
    monkeypatch.setattr(httpx, "post", boom)
    assert accounts.send_mail("taro@example.jp", "s", "secret-link") is False
    assert "secret-link" not in caplog.text and "taro@example.jp" not in caplog.text
    monkeypatch.setenv("MAIL_API_KEY", "")
    assert accounts.send_mail("taro@example.jp", "s", "b") is False
    monkeypatch.setenv("MAIL_PROVIDER", "sendgrid")
    assert accounts.send_mail("taro@example.jp", "s", "b") is False
