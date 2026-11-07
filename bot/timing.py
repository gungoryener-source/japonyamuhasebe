"""T-019: yavaş istek ölçümü.

İstek süresi `SLOW_REQUEST_SECONDS`'ı aşarsa WARNING log: yöntem, **rota şablonu** (ör. `/api/v1/entries/{entry_id}`),
durum kodu ve süre. Gerçek yol/sorgu dizesi yazılmaz — LINE user_id, token, e-posta gibi kişisel veriler
yol parametrelerinde veya sorguda olabilir.
"""
from __future__ import annotations

import logging
import time

from starlette.routing import Match
from starlette.types import ASGIApp, Message, Receive, Scope, Send

SLOW_REQUEST_SECONDS = 1.0
log = logging.getLogger("tegaru.slow")


def route_template(scope: Scope) -> str:
    """İsteğin eşleştiği rotanın şablon yolu; eşleşme yoksa "(unmatched)" (gerçek yol asla dönmez)."""
    app = scope.get("app")
    for route in getattr(getattr(app, "router", None), "routes", None) or getattr(app, "routes", None) or []:
        try:
            match, _ = route.matches(scope)
        except Exception:  # noqa: BLE001 - ölçüm isteği asla bozmamalı
            continue
        if match == Match.FULL:
            return getattr(route, "path", "(unknown)")
    return "(unmatched)"


class SlowRequestMiddleware:
    """Saf ASGI middleware: yanıt bitene kadar geçen süreyi ölçer (akış yanıtları dahil)."""

    def __init__(self, app: ASGIApp, threshold: float | None = None) -> None:
        self.app = app
        self.threshold = SLOW_REQUEST_SECONDS if threshold is None else threshold

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        start = time.perf_counter()
        status = 0

        async def send_wrapper(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = int(message.get("status", 0))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed = time.perf_counter() - start
            if elapsed > self.threshold:
                log.warning("slow request: %s %s status=%s %.2fs",
                            scope.get("method", ""), route_template(scope), status or "-", elapsed)
