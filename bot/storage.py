"""
Fiş görseli depolama soyutlaması (T-011).

Sürücüler:
  local — çalışma dizinine yazar (`receipts/...`). Render'da disk bağlı olmadığı için her deploy'da silinir.
  s3    — S3 uyumlu nesne depolama (Cloudflare R2 önerilen, Q-14). Yol stili URL: {ENDPOINT}/{BUCKET}/{key},
          AWS Signature V4 (yeni paket yok: hashlib/hmac + httpx).

Ortam değişkenleri:
  STORAGE_BACKEND     local | s3 (boşsa: S3 değişkenlerinin hepsi doluysa s3, değilse local)
  STORAGE_ENDPOINT    ör. https://<accountid>.r2.cloudflarestorage.com
  STORAGE_BUCKET, STORAGE_ACCESS_KEY, STORAGE_SECRET_KEY
  STORAGE_REGION      varsayılan "auto" (R2). AWS S3 için ör. ap-northeast-1

Anahtar `receipts/<güvenli ad>.jpg` biçimindedir ve `entries.image_path`'e aynen yazılır (geriye uyumlu).
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
from datetime import datetime, timezone
from urllib.parse import quote, urlsplit

import httpx

S3_VARS = ("STORAGE_ENDPOINT", "STORAGE_BUCKET", "STORAGE_ACCESS_KEY", "STORAGE_SECRET_KEY")
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+(/[A-Za-z0-9_.-]+)*$")

# Testler httpx.MockTransport enjekte eder
_transport: httpx.AsyncBaseTransport | None = None


class StorageError(Exception):
    pass


def safe_key(key: str) -> str:
    """Yol geçişi (`..`, mutlak yol) olan anahtarları reddeder."""
    if not key or not _KEY_RE.match(key) or ".." in key:
        raise StorageError("invalid key")
    return key


def s3_configured() -> bool:
    return all(os.environ.get(k, "").strip() for k in S3_VARS)


def backend() -> str:
    """Etkin sürücü. `s3` istenip değişkenler eksikse güvenli tarafta kalır: local."""
    want = os.environ.get("STORAGE_BACKEND", "").strip().lower()
    if want == "local":
        return "local"
    if want in ("s3", "r2") or not want:
        return "s3" if s3_configured() else "local"
    return "local"


def startup_warning() -> str | None:
    """Başlangıçta log'a yazılacak uyarı (yoksa None)."""
    want = os.environ.get("STORAGE_BACKEND", "").strip().lower()
    if backend() == "s3":
        return None
    if want in ("s3", "r2"):
        missing = [k for k in S3_VARS if not os.environ.get(k, "").strip()]
        return f"storage: STORAGE_BACKEND={want} ama eksik değişken {missing} → yerel disk kullanılıyor"
    return "storage: yerel disk (receipts/) — kalıcı değil, deploy'da silinir. STORAGE_* değişkenlerini girin (Q-14)"


# ---------------------------------------------------------------- local
def _local_put(key: str, data: bytes) -> None:
    d = os.path.dirname(key)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(key, "wb") as f:
        f.write(data)


def _local_get(key: str) -> bytes | None:
    try:
        with open(key, "rb") as f:
            return f.read()
    except FileNotFoundError:
        return None


# ---------------------------------------------------------------- AWS SigV4
def _h(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def sign_v4(method: str, url: str, headers: dict[str, str], payload_hash: str, *,
            access_key: str, secret_key: str, region: str, now: datetime, service: str = "s3") -> dict[str, str]:
    """İmzalı başlıkları döndürür (host, x-amz-date, x-amz-content-sha256, Authorization + verilenler).

    Sorgu dizesi desteklenmez (yalnızca nesne PUT/GET). URL yolu çağıran tarafından kodlanmış olmalı.
    """
    u = urlsplit(url)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    day = amz_date[:8]
    h = {k.lower(): str(v).strip() for k, v in headers.items()}
    h["host"] = u.netloc
    h["x-amz-date"] = amz_date
    h["x-amz-content-sha256"] = payload_hash
    names = sorted(h)
    canonical_headers = "".join(f"{n}:{h[n]}\n" for n in names)
    signed = ";".join(names)
    canonical = "\n".join([method.upper(), u.path or "/", u.query, canonical_headers, signed, payload_hash])
    scope = f"{day}/{region}/{service}/aws4_request"
    to_sign = "\n".join(["AWS4-HMAC-SHA256", amz_date, scope, hashlib.sha256(canonical.encode()).hexdigest()])
    k = _h(_h(_h(_h(("AWS4" + secret_key).encode(), day), region), service), "aws4_request")
    sig = hmac.new(k, to_sign.encode(), hashlib.sha256).hexdigest()
    h["authorization"] = f"AWS4-HMAC-SHA256 Credential={access_key}/{scope}, SignedHeaders={signed}, Signature={sig}"
    return h


def _s3_url(key: str) -> str:
    ep = os.environ["STORAGE_ENDPOINT"].strip().rstrip("/")
    bucket = os.environ["STORAGE_BUCKET"].strip()
    return f"{ep}/{quote(bucket, safe='')}/{quote(key, safe='/-_.~')}"


async def _s3_request(method: str, key: str, data: bytes = b"", content_type: str = "") -> httpx.Response:
    url = _s3_url(key)
    extra = {"content-type": content_type} if content_type else {}
    headers = sign_v4(method, url, extra, hashlib.sha256(data).hexdigest(),
                      access_key=os.environ["STORAGE_ACCESS_KEY"].strip(),
                      secret_key=os.environ["STORAGE_SECRET_KEY"].strip(),
                      region=os.environ.get("STORAGE_REGION", "").strip() or "auto",
                      now=datetime.now(timezone.utc))
    headers.pop("host", None)  # httpx URL'den aynı değeri koyar
    async with httpx.AsyncClient(timeout=20, transport=_transport) as c:
        return await c.request(method, url, content=data if method == "PUT" else None, headers=headers)


# ---------------------------------------------------------------- genel API
async def put(key: str, data: bytes, content_type: str = "image/jpeg") -> str:
    """Kaydeder, kullanılan sürücü adını döndürür. S3 hatasında görsel kaybolmasın diye yerele yazar."""
    key = safe_key(key)
    if backend() == "s3":
        try:
            r = await _s3_request("PUT", key, data, content_type)
            if r.status_code < 300:
                return "s3"
            print("storage s3 put failed", r.status_code)
        except httpx.HTTPError as ex:
            print("storage s3 put error", type(ex).__name__)
        _local_put(key, data)
        return "local-fallback"
    _local_put(key, data)
    return "local"


async def get(key: str) -> bytes | None:
    """Görseli döndürür; yoksa None. S3'te bulunamazsa yerel diske (eski/yedek kayıtlar) bakar."""
    key = safe_key(key)
    if backend() == "s3":
        try:
            r = await _s3_request("GET", key)
            if r.status_code == 200:
                return r.content
            if r.status_code not in (403, 404):
                print("storage s3 get failed", r.status_code)
        except httpx.HTTPError as ex:
            print("storage s3 get error", type(ex).__name__)
    return _local_get(key)
