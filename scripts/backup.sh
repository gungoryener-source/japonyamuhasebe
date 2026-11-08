#!/usr/bin/env bash
# T-046c: PostgreSQL yedeği — pg_dump "$DATABASE_URL" | gzip → tarih adlı dosya.
#
# Kullanım (operatörün kendi makinesinde; adımlar docs/OPERATIONS.md):
#   DATABASE_URL='postgresql://…' scripts/backup.sh            # ./backups/ altına yazar
#   DATABASE_URL='postgresql://…' BACKUP_DIR=/path scripts/backup.sh
#
# - Sır yazmaz: DATABASE_URL hiçbir zaman ekrana / dosya adına / log'a yazılmaz.
# - Veri silmez: veritabanına yalnızca okur; eski yedekleri de silmez (temizlik elle).
# - Yarım dosya bırakmaz: önce *.partial'a yazar, pg_dump + gzip doğrulaması başarılıysa yeniden adlandırır.
# - Dosya izni 600 (yalnızca sahibi okur) — yedekte kişisel/muhasebe verisi var.
# - Başarıda son satır stdout'a yalnızca yedek dosyasının yolu yazılır (betiklerde kullanılabilir).
set -euo pipefail
umask 077

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "backup.sh: DATABASE_URL tanımlı değil (Render → jsaas-db → Connect → External Database URL)" >&2
  exit 2
fi

for cmd in pg_dump gzip; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "backup.sh: '$cmd' bulunamadı (PostgreSQL istemcisi: sunucu sürümüyle aynı veya daha yeni pg_dump gerekir)" >&2
    exit 3
  fi
done

backup_dir="${BACKUP_DIR:-./backups}"
mkdir -p -- "$backup_dir"

stamp="$(TZ=Asia/Tokyo date +%Y%m%d-%H%M%S)"
out="${backup_dir%/}/tegaru-${stamp}-JST.sql.gz"
if [[ -e "$out" ]]; then
  echo "backup.sh: $out zaten var; üzerine yazılmadı" >&2
  exit 4
fi
partial="${out}.partial"

cleanup() { rm -f -- "$partial"; }
trap cleanup EXIT

# --no-owner / --no-privileges: başka bir veritabanına (yeni Render DB, yerel PG) rol adlarından bağımsız geri yüklenir.
# Düz SQL (format plain) → `gunzip -c … | psql` ile geri yüklenir.
if ! pg_dump --dbname="$DATABASE_URL" --format=plain --no-owner --no-privileges --encoding=UTF8 \
    | gzip -9 >"$partial"; then
  echo "backup.sh: pg_dump başarısız; yedek oluşturulmadı" >&2
  exit 5
fi

if ! gzip -t -- "$partial" 2>/dev/null; then
  echo "backup.sh: gzip doğrulaması başarısız; yedek oluşturulmadı" >&2
  exit 6
fi
# Boş/kesik döküm (bağlantı yarıda koptu vb.) yedek sayılmaz: pg_dump'ın son satırını ara.
tail_lines="$(gzip -dc -- "$partial" | tail -n 5)"
if [[ "$tail_lines" != *"PostgreSQL database dump complete"* ]]; then
  echo "backup.sh: döküm tamamlanmamış görünüyor; yedek oluşturulmadı" >&2
  exit 7
fi

mv -- "$partial" "$out"
trap - EXIT
size="$(wc -c <"$out" | tr -d ' ')"
echo "backup.sh: yedek tamam (${size} bayt)" >&2
echo "$out"
