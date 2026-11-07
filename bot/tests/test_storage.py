"""T-011: fiş görseli depolama — yerel sürücü, S3/R2 sürücüsü (httpx MockTransport), SigV4 imzası."""
from datetime import datetime, timezone

import httpx
import pytest

import storage

S3_ENV = {
    "STORAGE_ENDPOINT": "https://acc123.r2.cloudflarestorage.com/",
    "STORAGE_BUCKET": "tegaru-receipts",
    "STORAGE_ACCESS_KEY": "AKTEST",
    "STORAGE_SECRET_KEY": "sekret",
}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    for k in (*storage.S3_VARS, "STORAGE_BACKEND", "STORAGE_REGION"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(storage, "_transport", None)


@pytest.fixture()
def s3(monkeypatch):
    for k, v in S3_ENV.items():
        monkeypatch.setenv(k, v)
    objects: dict[str, bytes] = {}
    calls: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        if req.method == "PUT":
            objects[req.url.path] = req.content
            return httpx.Response(200)
        if req.method == "GET":
            if req.url.path in objects:
                return httpx.Response(200, content=objects[req.url.path])
            return httpx.Response(404)
        return httpx.Response(405)

    monkeypatch.setattr(storage, "_transport", httpx.MockTransport(handler))
    return {"objects": objects, "calls": calls}


# ---------------------------------------------------------------- seçim
def test_backend_selection(monkeypatch):
    assert storage.backend() == "local"
    assert "Q-14" in storage.startup_warning()
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    assert storage.backend() == "local"  # değişken eksik → güvenli taraf
    assert "STORAGE_BUCKET" in storage.startup_warning()
    for k, v in S3_ENV.items():
        monkeypatch.setenv(k, v)
    assert storage.backend() == "s3" and storage.startup_warning() is None
    monkeypatch.delenv("STORAGE_BACKEND")
    assert storage.backend() == "s3"  # hepsi doluysa otomatik
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    assert storage.backend() == "local"
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setenv("STORAGE_SECRET_KEY", "  ")
    assert storage.backend() == "local"


@pytest.mark.parametrize("bad", ["", "../etc/passwd", "/abs/x.jpg", "receipts/../x", "receipts/a b.jpg", "a//b"])
async def test_rejects_unsafe_keys(bad):
    with pytest.raises(storage.StorageError):
        await storage.put(bad, b"x")


# ---------------------------------------------------------------- local
async def test_local_roundtrip(tmp_path):
    assert await storage.put("receipts/u1_m1.jpg", b"\xff\xd8abc") == "local"
    assert (tmp_path / "receipts/u1_m1.jpg").read_bytes() == b"\xff\xd8abc"
    assert await storage.get("receipts/u1_m1.jpg") == b"\xff\xd8abc"
    assert await storage.get("receipts/none.jpg") is None


# ---------------------------------------------------------------- s3
async def test_s3_put_get_path_and_signature(s3, tmp_path):
    assert await storage.put("receipts/u1_m1.jpg", b"IMG", "image/jpeg") == "s3"
    put = s3["calls"][0]
    assert put.method == "PUT"
    assert str(put.url) == "https://acc123.r2.cloudflarestorage.com/tegaru-receipts/receipts/u1_m1.jpg"
    assert put.content == b"IMG"
    auth = put.headers["authorization"]
    assert auth.startswith("AWS4-HMAC-SHA256 Credential=AKTEST/")
    assert "/auto/s3/aws4_request" in auth  # R2 bölgesi
    assert "SignedHeaders=content-type;host;x-amz-content-sha256;x-amz-date" in auth
    import hashlib
    assert put.headers["x-amz-content-sha256"] == hashlib.sha256(b"IMG").hexdigest()
    assert put.headers["host"] == "acc123.r2.cloudflarestorage.com"
    assert not (tmp_path / "receipts").exists()  # yerel diske yazılmadı

    assert await storage.get("receipts/u1_m1.jpg") == b"IMG"
    get = s3["calls"][1]
    assert get.method == "GET" and get.url.path == "/tegaru-receipts/receipts/u1_m1.jpg"
    assert get.headers["x-amz-content-sha256"] == storage.EMPTY_SHA256
    assert await storage.get("receipts/missing.jpg") is None


async def test_s3_region_override(s3, monkeypatch):
    monkeypatch.setenv("STORAGE_REGION", "ap-northeast-1")
    await storage.put("receipts/a.jpg", b"x")
    assert "/ap-northeast-1/s3/aws4_request" in s3["calls"][0].headers["authorization"]


async def test_s3_failure_falls_back_to_local(monkeypatch, tmp_path):
    for k, v in S3_ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(storage, "_transport", httpx.MockTransport(lambda r: httpx.Response(500)))
    assert await storage.put("receipts/f.jpg", b"keep") == "local-fallback"
    assert (tmp_path / "receipts/f.jpg").read_bytes() == b"keep"
    assert await storage.get("receipts/f.jpg") == b"keep"  # S3 hata → yerel kopya

    def boom(r):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(storage, "_transport", httpx.MockTransport(boom))
    assert await storage.put("receipts/g.jpg", b"k2") == "local-fallback"
    assert await storage.get("receipts/g.jpg") == b"k2"


def test_sigv4_aws_reference_vector():
    """AWS belgelerindeki S3 GET örneği (examplebucket/test.txt, Range: bytes=0-9)."""
    h = storage.sign_v4(
        "GET", "https://examplebucket.s3.amazonaws.com/test.txt", {"Range": "bytes=0-9"}, storage.EMPTY_SHA256,
        access_key="AKIAIOSFODNN7EXAMPLE", secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        region="us-east-1", now=datetime(2013, 5, 24, tzinfo=timezone.utc))
    assert h["authorization"] == (
        "AWS4-HMAC-SHA256 Credential=AKIAIOSFODNN7EXAMPLE/20130524/us-east-1/s3/aws4_request, "
        "SignedHeaders=host;range;x-amz-content-sha256;x-amz-date, "
        "Signature=f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41")


# ---------------------------------------------------------------- process_image
async def test_process_image_uses_s3(bot, s3, monkeypatch, tmp_path):
    import store

    async def fake_ocr(img):
        return [{"date": "2026-11-01", "kind": "exp", "store": "A", "amount": 500, "rate": 10,
                 "category": "雑費", "invoice_no": ""}]

    monkeypatch.setattr(bot, "ocr_receipt", fake_ocr)
    msg, _ = await bot.process_image("U-s3-12345678", b"\xff\xd8jpg", "m/../9", "LINE")
    assert msg.startswith("登録しました")
    with store.tx() as con:
        path = con.execute("SELECT image_path FROM entries WHERE user_id=?", ("U-s3-12345678",)).fetchone()["image_path"]
    assert path.startswith("receipts/") and ".." not in path
    assert s3["objects"][f"/tegaru-receipts/{path}"] == b"\xff\xd8jpg"
    assert not (tmp_path / "receipts").exists()
    assert await storage.get(path) == b"\xff\xd8jpg"


async def test_process_image_empty_ref_still_valid_key(bot, monkeypatch, tmp_path):
    async def fake_ocr(img):
        return [{"date": "2026-11-01", "kind": "exp", "store": "A", "amount": 500, "rate": 10,
                 "category": "雑費", "invoice_no": ""}]

    monkeypatch.setattr(bot, "ocr_receipt", fake_ocr)
    msg, _ = await bot.process_image("....", b"x", "//", "LINE")
    assert msg.startswith("登録しました")
    files = list((tmp_path / "receipts").iterdir())
    assert len(files) == 1 and files[0].read_bytes() == b"x"


async def test_s3_404_falls_back_to_legacy_local_file(s3, tmp_path):
    """review: R2 移行前に yerel diske yazılmış eski fiş, S3'te yoksa yerelden okunur."""
    (tmp_path / "receipts").mkdir()
    (tmp_path / "receipts/old.jpg").write_bytes(b"legacy")
    assert await storage.get("receipts/old.jpg") == b"legacy"
    assert [c.method for c in s3["calls"]] == ["GET"]
