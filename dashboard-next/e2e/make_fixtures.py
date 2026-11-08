"""T-035: panel e2e canlı mod için sahte API yanıtlarını gerçek bot'tan üretir.

Kullanım (depo kökünden):  python dashboard-next/e2e/make_fixtures.py
Geçici SQLite'a `demo_data.seed` ile örnek defter kurar, aşağıdaki GET uçlarını
TestClient ile çağırır ve `e2e/fixtures/api.json` dosyasına yazar. Sır/gerçek veri yok.
`bot/tests/test_e2e_fixtures.py` dosyanın güncel olduğunu (yolların hâlâ 200 döndüğünü
ve üst düzey anahtarların değişmediğini) denetler.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOT = HERE.parent.parent / "bot"
OUT = HERE / "fixtures" / "api.json"

# Panelin canlı modda okuduğu GET uçları (sorgu dizesi olmadan anahtarlanır).
PATHS = [
    "/auth/me", "/profile", "/summary", "/cashflow?months=6", "/entries", "/invoices",
    "/tax/consumption?year=2026", "/tax/consumption/return?year=2026", "/pl?year=2026", "/tax/income?year=2026",
    "/assets", "/assets/schedule?year=2026", "/bank/transactions", "/bank/review", "/counterparties", "/slips",
    "/settings/ai", "/channels", "/account/delete-request",
    "/team/members", "/team/ledgers", "/billing/plans", "/billing/status",
]
USER = "E2E"


def collect(client, admin_key: str) -> dict[str, object]:
    """`demo_data.seed` ile defter kurar, PATHS'i çağırır. `client`: bot uygulamasına TestClient."""
    import demo_data

    demo_data.seed(USER)
    r = client.post("/api/v1/admin/tokens", json={"user_id": USER}, headers={"X-Admin-Key": admin_key})
    r.raise_for_status()
    auth = {"Authorization": f"Bearer {r.json()['token']}"}
    out: dict[str, object] = {}
    for p in PATHS:
        res = client.get(f"/api/v1{p}", headers=auth)
        if res.status_code != 200:
            raise SystemExit(f"{p}: HTTP {res.status_code} {res.text[:200]}")
        out[p.split("?")[0]] = res.json()
    return out


def main() -> None:
    with tempfile.TemporaryDirectory() as d:
        os.environ["DB_PATH"] = str(Path(d) / "e2e.db")
        os.environ.pop("DATABASE_URL", None)
        os.environ.setdefault("LINE_CHANNEL_SECRET", "e2e-secret")
        os.environ.setdefault("LINE_CHANNEL_ACCESS_TOKEN", "e2e-token")
        os.environ["ADMIN_KEY"] = "e2e-admin"
        os.environ["RICHMENU_AUTO"] = "0"
        sys.path.insert(0, str(BOT))
        from fastapi.testclient import TestClient

        import app as app_module

        data = collect(TestClient(app_module.app), "e2e-admin")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{OUT}: {len(data)} uç")


if __name__ == "__main__":
    main()
