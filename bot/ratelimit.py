"""Bellek içi kayan pencere hız sınırı (T-048).

Anahtar: (kural adı, istemci IP). Tek süreç / tek örnek içindir (Render tek konteyner);
yeniden başlatmada sayaçlar sıfırlanır. Sınır aşılırsa 429 + `Retry-After` (saniye).

Yapılandırma (ortam değişkeni, isteğe bağlı): `RATE_LIMIT_<KURAL>` = "adet/saniye" (ör. "10/60"),
"0" kuralı kapatır. `RATE_LIMIT_PROXY_HOPS`: 0 (varsayılan) → `X-Forwarded-For` ilk değeri;
N>0 → sağdan N'inci değer (istemcinin başlığı sahteleyebildiği ortamlarda güvenilir vekil sayısı).
"""
from __future__ import annotations

import math
import os
import threading
import time
from collections import deque

from fastapi import HTTPException, Request

# kural → (izin verilen istek sayısı, pencere saniyesi)
DEFAULTS: dict[str, tuple[int, int]] = {
    "login": (10, 60),
    "signup": (5, 60),
    "password_reset": (5, 60),
    "ocr": (20, 60),
}
MAX_KEYS = 20_000  # bellek koruması: aşılırsa süresi dolmuş anahtarlar temizlenir, yine aşılırsa en eskisi atılır
DETAIL = "リクエストが多すぎます。しばらく時間をおいてから再度お試しください。"

_now = time.monotonic  # testlerde monkeypatch edilir
_lock = threading.Lock()
_hits: dict[tuple[str, str], deque[float]] = {}


def reset() -> None:
    with _lock:
        _hits.clear()


def limit_for(rule: str) -> tuple[int, int] | None:
    """Kuralın (adet, pencere) değeri; kapalıysa None."""
    raw = os.environ.get(f"RATE_LIMIT_{rule.upper()}", "").strip()
    if raw:
        if raw == "0":
            return None
        try:
            n, _, w = raw.partition("/")
            count, window = int(n), int(w or 60)
            if count > 0 and window > 0:
                return count, window
        except ValueError:
            pass  # bozuk değer → varsayılan
    return DEFAULTS[rule]


def client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    parts = [p.strip() for p in xff.split(",") if p.strip()]
    if parts:
        try:
            hops = max(0, int(os.environ.get("RATE_LIMIT_PROXY_HOPS", "0")))
        except ValueError:
            hops = 0
        if hops == 0:
            return parts[0]
        return parts[-hops] if hops <= len(parts) else parts[0]
    return request.client.host if request.client else "unknown"


def _prune(now: float) -> None:
    for key in [k for k, q in _hits.items() if not q or now - q[-1] >= _window_of(k[0])]:
        del _hits[key]
    while len(_hits) >= MAX_KEYS:
        del _hits[next(iter(_hits))]


def _window_of(rule: str) -> int:
    lim = limit_for(rule)
    return lim[1] if lim else 0  # kapalı kural → hemen temizlenir


def hit(rule: str, key: str) -> float | None:
    """İsteği say. İzinliyse None, aşıldıysa `Retry-After` saniyesi."""
    lim = limit_for(rule)
    if lim is None:
        return None
    count, window = lim
    now = _now()
    with _lock:
        q = _hits.get((rule, key))
        if q is None:
            if len(_hits) >= MAX_KEYS:
                _prune(now)
            q = _hits[(rule, key)] = deque()
        while q and now - q[0] >= window:
            q.popleft()
        if len(q) >= count:
            return max(1.0, q[0] + window - now)
        q.append(now)
        return None


def limiter(rule: str):
    """FastAPI bağımlılığı: `dependencies=[Depends(limiter("login"))]`."""
    if rule not in DEFAULTS:
        raise ValueError(rule)

    def dep(request: Request) -> None:
        retry = hit(rule, client_ip(request))
        if retry is not None:
            raise HTTPException(429, DETAIL, headers={"Retry-After": str(math.ceil(retry))})

    return dep
