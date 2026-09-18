# Production deployment record

Shouko-chan is live 24/7 as of 2026-09-18. This documents what's actually
running and how to operate it.

## Architecture

- **Separate checkout**: `/srv/shouko-chan/app`, its own git clone — never
  the dev directory (`/home/jovan/Shouko-chan`), so an active dev session
  editing there can never touch the live bot.
- **Same bot token as dev** — there's only one Discord application. This is
  the one thing that makes a Discord bot's dev/prod split different from a
  web app on its own port: **never run `main.py` manually from the dev
  checkout while this service is up.** Discord happily lets two gateway
  sessions connect with the same token, and both will race to answer the
  same slash command interaction, causing duplicate/conflicting responses.
  Stop the service first (`sudo systemctl stop shouko-chan`) if you need to
  run the dev copy for something.
- **Persistent data**: `/srv/shouko-chan/storage`, outside the app
  checkout. `/srv/shouko-chan/app/data` is a symlink to it, so the
  `data/shouko.db` SQLite database (everything's stored here now, not
  JSON files - see db.py) lands in persistent storage automatically, and
  a redeploy (which replaces the checkout) never touches it.
- **Own venv**: `/srv/shouko-chan/app/.venv`, separate from dev's.
- **Host-level system packages this bot needs** (installed once, shared
  by dev and prod since they're the same machine - would need reinstalling
  on a fresh host): `sqlite3` (CLI, used by backup.sh's `.backup` snapshot),
  `build-essential` (compiling C-extension Python deps), and
  `fonts-noto-color-emoji` (~11MB - not bundled in the repo like the
  DejaVu fonts are; needed for /slots' reel images, since DejaVu has no
  color-emoji glyphs).
- **Backups**: a systemd timer runs `deploy/backup.sh` daily (a proper
  `sqlite3 .backup` snapshot of the database, plus a tarball of the rest
  of `storage/` - old pre-migration JSON safety-net files, ticket
  transcripts - 14-day local retention). `BACKUP_REMOTE_DEST` is unset, so
  this is **local-only** right now — not durable against this disk
  failing. Set it to an rclone/rsync destination when that matters.
- **No web server involved** — this is a gateway bot, nothing to put behind
  Caddy or expose a port for.

## Operating this

**Ship an update:**
```bash
cd /srv/shouko-chan/app && ./deploy/deploy.sh
```
Pulls `main`, reinstalls dependencies, restarts the service.

**Logs:**
```bash
journalctl -u shouko-chan -f
```

**Manual backup:**
```bash
sudo systemctl start shouko-chan-backup.service   # runs backup.sh once, outside the daily timer
```

**Restart without deploying:**
```bash
sudo systemctl restart shouko-chan
```

## Still open

- **Off-site backups**: local-only right now (see above) — same caveat as
  moonlightcherry's.
- Dev and prod data diverged the moment this was set up (prod's storage was
  seeded from dev's data at the time, then they became independent) — any
  further dev-side testing (economy balances, levels, etc.) no longer
  reflects what's live, and vice versa.
