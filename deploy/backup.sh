#!/usr/bin/env bash
# Daily backup: a tarball of the persistent data storage directory (Aura,
# leveling, shop inventory, profiles, per-server config - everything under
# data/, which is a symlink to /srv/shouko-chan/storage outside this
# checkout), timestamped, kept for 14 days locally. This only protects
# against local disk failure if BACKUP_REMOTE_DEST also copies these off
# this machine - set it to an rclone/rsync destination or backups are only
# as safe as this one disk.
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/srv/shouko-chan/backups}"
STORAGE_DIR="${STORAGE_DIR:-/srv/shouko-chan/storage}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
STAMP=$(date +%Y%m%d-%H%M%S)

mkdir -p "$BACKUP_DIR"

echo "==> Archiving data storage"
tar -czf "$BACKUP_DIR/data-$STAMP.tar.gz" -C "$(dirname "$STORAGE_DIR")" "$(basename "$STORAGE_DIR")"

if [ -n "${BACKUP_REMOTE_DEST:-}" ]; then
  echo "==> Syncing to $BACKUP_REMOTE_DEST"
  rclone copy "$BACKUP_DIR/data-$STAMP.tar.gz" "$BACKUP_REMOTE_DEST"
else
  echo "==> BACKUP_REMOTE_DEST not set — backup is LOCAL ONLY, not off-site."
fi

echo "==> Pruning backups older than $RETENTION_DAYS days"
find "$BACKUP_DIR" -name "*.tar.gz" -mtime "+$RETENTION_DAYS" -delete

echo "==> Done: $BACKUP_DIR/data-$STAMP.tar.gz"
