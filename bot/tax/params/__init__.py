"""年分ごとの税制パラメータ（bot/tax/params/<年>.toml）。

各値は {value, verified, source, rule, checked[, note]} を持つ。出典 URL は docs/TAX_RULES.md。
コードに税率・限度額を直書きしない（T-071 以降の申告書計算はここから読む）。
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

_DIR = Path(__file__).parent


@dataclass(frozen=True)
class Param:
    key: str
    value: Any
    verified: bool
    source: str
    rule: str
    checked: str
    note: str = ""

    @property
    def frac(self) -> tuple[int, int]:
        """[分子, 分母] の整数ペア。"""
        num, den = self.value
        return int(num), int(den)


class ParamsNotAvailable(LookupError):
    pass


def years() -> list[int]:
    return sorted(int(p.stem) for p in _DIR.glob("*.toml") if p.stem.isdigit())


def _flatten(prefix: str, node: dict, out: dict[str, Param]) -> None:
    if "value" in node and "verified" in node:
        out[prefix] = Param(prefix, node["value"], bool(node["verified"]), node.get("source", ""),
                            node.get("rule", ""), node.get("checked", ""), node.get("note", ""))
        return
    for k, v in node.items():
        if isinstance(v, dict):
            _flatten(f"{prefix}.{k}" if prefix else k, v, out)


@lru_cache(maxsize=None)
def load(year: int) -> dict[str, Param]:
    path = _DIR / f"{year}.toml"
    if not path.exists():
        raise ParamsNotAvailable(f"{year}年分の税制パラメータがありません（対応: {years()}）")
    with path.open("rb") as f:
        data = tomllib.load(f)
    if data.get("tax_year") != year:
        raise ValueError(f"{path.name}: tax_year mismatch")
    out: dict[str, Param] = {}
    _flatten("", data, out)
    return out


@lru_cache(maxsize=None)
def load_static(name: str) -> dict[str, Param]:
    """年分に依存しないパラメータファイル（例: depreciation.toml）。"""
    path = _DIR / f"{name}.toml"
    if not path.exists():
        raise ParamsNotAvailable(f"{name}.toml がありません")
    with path.open("rb") as f:
        data = tomllib.load(f)
    out: dict[str, Param] = {}
    _flatten("", data, out)
    return out


def get(year: int, key: str) -> Param:
    try:
        return load(year)[key]
    except KeyError:
        raise ParamsNotAvailable(f"{year}年分: {key} がありません") from None


def has(year: int, key: str) -> bool:
    return key in load(year)


def unverified(year: int) -> list[Param]:
    """verified = false のパラメータ（TODO(verify) — 検証レポート用）。"""
    return [p for p in load(year).values() if not p.verified]
