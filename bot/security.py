"""T-048b: CORS izin listesi ve güvenlik başlıkları.

CORS:
  - `CORS_ORIGINS` virgülle ayrılmış origin listesi ise aynen kullanılır.
  - Boş veya `*` içeriyorsa (render.yaml varsayılanı "*"), herkese açmak yerine
    `PANEL_URL`'nin origin'i + yerel geliştirme (`http://localhost:3000`) kullanılır.
    Değişken adları değişmedi; yalnızca "*" anlamı daraltıldı.
Güvenlik başlıkları: tüm yanıtlara (/, /callback, /api/v1/*) eklenir; uygulama
zaten bir başlık koyduysa üzerine yazılmaz.
"""
import os
from urllib.parse import urlsplit

from starlette.types import ASGIApp, Message, Receive, Scope, Send

DEV_ORIGINS = ("http://localhost:3000",)

SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Strict-Transport-Security": "max-age=31536000",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": "frame-ancestors 'none'",
}


def _origin(url: str) -> str | None:
    """'https://a.example.com/path/' → 'https://a.example.com' (geçersizse None)."""
    parts = urlsplit(url.strip())
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return None
    return f"{parts.scheme}://{parts.netloc}".lower()


def cors_origins(env: dict[str, str] | None = None) -> list[str]:
    env = os.environ if env is None else env
    raw = [o.strip() for o in env.get("CORS_ORIGINS", "").split(",") if o.strip()]
    if raw and "*" not in raw:
        out = [_origin(o) for o in raw]
    else:
        out = [_origin(env.get("PANEL_URL", "")), *DEV_ORIGINS]
    # sırayı koru, yinelenen/geçersizleri at
    return list(dict.fromkeys(o for o in out if o))


class SecurityHeadersMiddleware:
    """Saf ASGI middleware (akış yanıtlarını da bozmaz)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._headers = [(k.lower().encode(), v.encode()) for k, v in SECURITY_HEADERS.items()]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                present = {k.lower() for k, _ in headers}
                headers += [(k, v) for k, v in self._headers if k not in present]
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)
