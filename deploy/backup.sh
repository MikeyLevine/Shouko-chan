#!/usr/bin/env bash
# Daily backup: a consistent SQLite snapshot (via `.backup`, not a raw file
# copy - the live db can be mid-write when this runs, and copying its bytes
# directly risks capturing it torn between the main file and its WAL) plus
# a tarball of everything else under the persistent data storage directory
# (old pre-migration JSON files kept as a safety net, ticket transcripts,
# etc.), both timestamped and kept for 14 days locally. This only protects
# against local disk failure if BACKUP_REMOTE_DEST also copies these off
# this machine - set it to an rclone/rsync destination or backups are only
# as safe as this one disk.
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/srv/shouko-chan/backups}"
STORAGE_DIR="${STORAGE_DIR:-/srv/shouko-chan/storage}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
STAMP=$(date +%Y%m%d-%H%M%S)

mkdir -p "$BACKUP_DIR"

echo "==> Snapshotting SQLite database"
sqlite3 "$STORAGE_DIR/shouko.db" ".backup '$BACKUP_DIR/shouko-$STAMP.db'"
gzip "$BACKUP_DIR/shouko-$STAMP.db"

echo "==> Archiving remaining data storage"
tar -czf "$BACKUP_DIR/data-$STAMP.tar.gz" \
  --exclude="shouko.db" --exclude="shouko.db-wal" --exclude="shouko.db-shm" \
  -C "$(dirname "$STORAGE_DIR")" "$(basename "$STORAGE_DIR")"

if [ -n "${BACKUP_REMOTE_DEST:-}" ]; then
  echo "==> Syncing to $BACKUP_REMOTE_DEST"
  rclone copy "$BACKUP_DIR/shouko-$STAMP.db.gz" "$BACKUP_REMOTE_DEST"
  rclone copy "$BACKUP_DIR/data-$STAMP.tar.gz" "$BACKUP_REMOTE_DEST"
else
  echo "==> BACKUP_REMOTE_DEST not set — backup is LOCAL ONLY, not off-site."
fi

echo "==> Pruning backups older than $RETENTION_DAYS days"
find "$BACKUP_DIR" -name "shouko-*.db.gz" -mtime "+$RETENTION_DAYS" -delete
find "$BACKUP_DIR" -name "data-*.tar.gz" -mtime "+$RETENTION_DAYS" -delete

echo "==> Done: $BACKUP_DIR/shouko-$STAMP.db.gz, $BACKUP_DIR/data-$STAMP.tar.gz"
