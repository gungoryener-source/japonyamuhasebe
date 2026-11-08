"""T-046c: scripts/backup.sh (pg_dump | gzip) davranışı.

Gerçek veritabanı gerekmez: PATH'e sahte `pg_dump` konur. DATABASE_URL bir PostgreSQL ise
(CI bot-postgres işi) gerçek pg_dump ile de bir yedek alınır (salt okuma).
"""
from __future__ import annotations

import gzip
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "backup.sh"
SECRET_URL = "postgresql://tegaru:S3cr3t-pw@db.example.invalid:5432/tegaru"
NAME_RE = re.compile(r"^tegaru-\d{8}-\d{6}-JST\.sql\.gz$")

FAKE_OK = """#!/usr/bin/env bash
# argümanları kaydet (URL'nin --dbname ile geçtiğini doğrulamak için)
printf '%s\\n' "$@" > "$FAKE_ARGS"
cat <<'SQL'
--
-- PostgreSQL database dump
--
CREATE TABLE public.entries (id integer, memo text);
COPY public.entries (id, memo) FROM stdin;
1	交通費
\\.
--
-- PostgreSQL database dump complete
--
SQL
"""

FAKE_FAIL = """#!/usr/bin/env bash
echo 'CREATE TABLE half' ; echo 'pg_dump: error: connection lost' >&2 ; exit 1
"""

FAKE_TRUNCATED = """#!/usr/bin/env bash
echo '-- PostgreSQL database dump'; echo 'CREATE TABLE public.entries (id integer);'
"""


def _fake_bin(tmp_path: Path, body: str) -> Path:
    b = tmp_path / "bin"
    b.mkdir(exist_ok=True)
    p = b / "pg_dump"
    p.write_text(body)
    p.chmod(0o755)
    return b


def _run(tmp_path: Path, fake: str | None, url: str | None = SECRET_URL, **extra):
    env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
    if fake is not None:
        env["PATH"] = f"{_fake_bin(tmp_path, fake)}:{env['PATH']}"
    if url is not None:
        env["DATABASE_URL"] = url
    env["BACKUP_DIR"] = str(tmp_path / "out")
    env["FAKE_ARGS"] = str(tmp_path / "args.txt")
    env.update(extra)
    return subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True, timeout=120)


def _out_files(tmp_path: Path) -> list[Path]:
    d = tmp_path / "out"
    return sorted(d.iterdir()) if d.exists() else []


def test_syntax_ok():
    assert subprocess.run(["bash", "-n", str(SCRIPT)]).returncode == 0
    assert os.access(SCRIPT, os.X_OK), "backup.sh çalıştırılabilir olmalı"


@pytest.mark.skipif(shutil.which("shellcheck") is None, reason="shellcheck yok")
def test_shellcheck_clean():
    r = subprocess.run(["shellcheck", str(SCRIPT)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


def test_success_writes_dated_gzip_600(tmp_path):
    r = _run(tmp_path, FAKE_OK)
    assert r.returncode == 0, r.stderr
    files = _out_files(tmp_path)
    assert len(files) == 1
    f = files[0]
    assert NAME_RE.match(f.name), f.name
    assert r.stdout.strip() == str(f)
    assert stat.S_IMODE(f.stat().st_mode) == 0o600
    sql = gzip.decompress(f.read_bytes()).decode()
    assert "CREATE TABLE public.entries" in sql and "交通費" in sql
    args = (tmp_path / "args.txt").read_text().splitlines()
    assert f"--dbname={SECRET_URL}" in args
    assert "--no-owner" in args and "--no-privileges" in args


def test_never_prints_secret(tmp_path):
    for fake in (FAKE_OK, FAKE_FAIL, FAKE_TRUNCATED):
        r = _run(tmp_path, fake)
        out = r.stdout + r.stderr
        assert "S3cr3t-pw" not in out and "db.example.invalid" not in out
    for f in _out_files(tmp_path):
        assert "S3cr3t" not in f.name


def test_missing_database_url(tmp_path):
    r = _run(tmp_path, FAKE_OK, url=None)
    assert r.returncode == 2
    assert "DATABASE_URL" in r.stderr
    assert _out_files(tmp_path) == []


def test_empty_database_url(tmp_path):
    r = _run(tmp_path, FAKE_OK, url="")
    assert r.returncode == 2
    assert not (tmp_path / "args.txt").exists()  # pg_dump hiç çağrılmadı


def test_pg_dump_failure_leaves_no_file(tmp_path):
    r = _run(tmp_path, FAKE_FAIL)
    assert r.returncode == 5
    assert _out_files(tmp_path) == []  # .partial da kalmaz


def test_truncated_dump_rejected(tmp_path):
    r = _run(tmp_path, FAKE_TRUNCATED)
    assert r.returncode == 7
    assert _out_files(tmp_path) == []


def test_pg_dump_missing(tmp_path):
    # PATH'te yalnızca bash/gzip/date vb. olsun, pg_dump olmasın
    b = tmp_path / "onlybin"
    b.mkdir()
    for tool in ("bash", "gzip", "date", "mkdir", "rm", "mv", "wc", "tr", "tail", "env"):
        src = shutil.which(tool)
        if src:
            (b / tool).symlink_to(src)
    r = _run(tmp_path, None, PATH=str(b))
    assert r.returncode == 3
    assert "pg_dump" in r.stderr
    assert _out_files(tmp_path) == []


def test_existing_backups_untouched(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    old = out / "tegaru-20000101-000000-JST.sql.gz"
    old.write_bytes(b"old")
    r = _run(tmp_path, FAKE_OK)
    assert r.returncode == 0, r.stderr
    assert old.read_bytes() == b"old"  # eski yedek silinmez / değişmez
    assert len(_out_files(tmp_path)) == 2


def test_real_postgres_dump(tmp_path):
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith(("postgres://", "postgresql://")) or shutil.which("pg_dump") is None:
        pytest.skip("PostgreSQL / pg_dump yok")
    import store  # şemanın var olduğundan emin ol (salt ekleyici init)

    store.init_db()
    env = dict(os.environ, BACKUP_DIR=str(tmp_path / "out"))
    r = subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True, timeout=300)
    if r.returncode != 0 and "version mismatch" in r.stderr:
        pytest.skip("pg_dump istemci sürümü sunucudan eski")
    assert r.returncode == 0, r.stderr
    sql = gzip.decompress(Path(r.stdout.strip()).read_bytes()).decode()
    assert "CREATE TABLE public.entries" in sql
    assert "PostgreSQL database dump complete" in sql
