"""T-034: パネルで読み取った領収書画像を記録と紐付けて保存・表示（電帳法）。"""
import pytest
from fastapi.testclient import TestClient

ADMIN = {"X-Admin-Key": "test-admin"}
JPEG = b"\xff\xd8\xff\xe0fake-receipt"


@pytest.fixture()
def client(bot, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    async def fake_ocr(img, reader=""):
        return bot.normalize_ocr({"date": "2026-11-01", "store": "文具店", "total10": 1100})

    monkeypatch.setattr(bot, "ocr_receipt", fake_ocr)
    return TestClient(bot.app)


def tok(client, uid):
    t = client.post("/api/v1/admin/tokens", json={"user_id": uid}, headers=ADMIN).json()["token"]
    return {"Authorization": f"Bearer {t}"}


def test_ocr_saves_image_and_entry_links_it(client):
    h = tok(client, "UIMG")
    r = client.post("/api/v1/receipts/ocr", content=JPEG, headers={**h, "Content-Type": "image/jpeg"}).json()
    assert r["ok"] and r["image_path"].startswith("receipts/w")
    e = {**r["entries"][0], "image_path": r["image_path"]}
    eid = client.post("/api/v1/entries", json=e, headers=h).json()["id"]
    img = client.get(f"/api/v1/entries/{eid}/image", headers=h)
    assert img.status_code == 200 and img.content == JPEG and img.headers["content-type"] == "image/jpeg"


def test_cannot_attach_or_read_other_ledgers_image(client):
    ha, hb = tok(client, "UA1"), tok(client, "UB1")
    path = client.post("/api/v1/receipts/ocr", content=JPEG, headers={**ha, "Content-Type": "image/jpeg"}).json()["image_path"]
    body = {"date": "2026-11-01", "kind": "exp", "store": "X", "amount": 100, "category": "雑費", "rate": 10,
            "invoice_no": "", "image_path": path}
    assert client.post("/api/v1/entries", json=body, headers=hb).status_code == 400       # 他の帳簿の画像
    assert client.post("/api/v1/entries", json={**body, "image_path": "receipts/../../etc/passwd"}, headers=ha).status_code == 400
    eid = client.post("/api/v1/entries", json=body, headers=ha).json()["id"]
    assert client.get(f"/api/v1/entries/{eid}/image", headers=hb).status_code == 404
    noimg = client.post("/api/v1/entries", json={**body, "image_path": ""}, headers=ha).json()["id"]
    assert client.get(f"/api/v1/entries/{noimg}/image", headers=ha).status_code == 404
