#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR=${BACKUP_DIR:-/backup}
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}
MYSQL_HOST=${MYSQL_HOST:-mysql}
MYSQL_PORT=${MYSQL_PORT:-3306}
MYSQL_DATABASE=${MYSQL_DATABASE:-burglar}
MYSQL_USER=${MYSQL_USER:-burglar}
MYSQL_PASSWORD=${MYSQL_PASSWORD:-burglar}

mkdir -p "$BACKUP_DIR"

run_one() {
  local stamp
  stamp=$(date -u +%Y%m%dT%H%M%SZ)
  local out="$BACKUP_DIR/${MYSQL_DATABASE}_${stamp}.sql.gz"
  echo "[$(date -u +%FT%TZ)] dumping to $out"
  mysqldump \
    --host="$MYSQL_HOST" --port="$MYSQL_PORT" \
    --user="$MYSQL_USER" --password="$MYSQL_PASSWORD" \
    --single-transaction --quick --routines --triggers --events --no-tablespaces \
    "$MYSQL_DATABASE" | gzip -c > "$out"
  find "$BACKUP_DIR" -name "${MYSQL_DATABASE}_*.sql.gz" -mtime +"$RETENTION_DAYS" -delete
}

# Wait for next 02:00 UTC every day; do an immediate run on first start.
run_one
while true; do
  now=$(date -u +%s)
  next=$(date -u -d 'tomorrow 02:00' +%s 2>/dev/null || date -u -v+1d -v2H -v0M -v0S +%s)
  sleep $((next - now))
  run_one || echo "backup failed at $(date -u +%FT%TZ)"
done
