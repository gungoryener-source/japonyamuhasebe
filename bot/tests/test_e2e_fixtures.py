"""T-035: panel e2e fixture'ı (dashboard-next/e2e/fixtures/api.json) API ile uyumlu mu?

Fixture bot'tan üretilir (`python dashboard-next/e2e/make_fixtures.py`). API yanıt biçimi değişip
fixture eskirse panel e2e testleri gerçekte olmayan veriyle geçer; bu test bunu yakalar.
"""
import importlib.util
import json
from pathlib import Path

from fastapi.testclient import TestClient

E2E = Path(__file__).resolve().parents[2] / "dashboard-next" / "e2e"


def _make_fixtures():
    spec = importlib.util.spec_from_file_location("make_fixtures", E2E / "make_fixtures.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _shape(v):
    """Üst düzey biçim: sözlükte anahtar kümesi, listede ilk öğenin anahtarları."""
    if isinstance(v, dict):
        return ("dict", sorted(v))
    if isinstance(v, list):
        return ("list", sorted(v[0]) if v and isinstance(v[0], dict) else None)
    return (type(v).__name__, None)


def test_fixture_matches_api(bot):
    mf = _make_fixtures()
    fresh = mf.collect(TestClient(bot.app), "test-admin")
    saved = json.loads((E2E / "fixtures" / "api.json").read_text(encoding="utf-8"))
    assert sorted(saved) == sorted(fresh), "PATHS değişti → make_fixtures.py'yi çalıştırın"
    for path, body in fresh.items():
        assert _shape(saved[path]) == _shape(body), f"{path} yanıt biçimi değişti → make_fixtures.py'yi çalıştırın"


def test_fixture_has_no_secrets():
    text = (E2E / "fixtures" / "api.json").read_text(encoding="utf-8")
    assert "tk_" not in text and "e2e-admin" not in text
    data = json.loads(text)
    assert data["/profile"]["business_name"] == "合同会社ミナト"   # demo_data örnek defteri
