"""Shared SQLite connection and schema for the whole bot.

Every cog that used to read/write its own data/*.json file now goes
through this module instead. One connection, opened once at import time,
reused everywhere - this bot's command volume is tiny, so a single
synchronous sqlite3 connection (matching the synchronous file I/O every
cog already did) is simpler than adding an async DB layer for no real
benefit at this scale.

The database file lives at data/shouko.db - "data/" is a symlink to
/srv/shouko-chan/storage in production, so this lands in persistent
storage automatically, the same way every data/*.json file already did.
"""
import sqlite3
import os

DB_PATH = os.path.join("data", "shouko.db")

os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)

connection = sqlite3.connect(DB_PATH, check_same_thread=False)
connection.row_factory = sqlite3.Row
connection.execute("PRAGMA journal_mode=WAL")
connection.execute("PRAGMA foreign_keys=ON")

SCHEMA = """
-- Aura economy (cogs/economy/aura.py) - per-server balances.
CREATE TABLE IF NOT EXISTS aura_accounts (
    guild_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    balance INTEGER NOT NULL DEFAULT 500,
    last_daily REAL,
    daily_streak INTEGER NOT NULL DEFAULT 0,
    last_scavenge REAL,
    PRIMARY KEY (guild_id, user_id)
);

-- Leveling (cogs/settings/leveling.py) - per-server XP.
CREATE TABLE IF NOT EXISTS leveling_accounts (
    guild_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    exp INTEGER NOT NULL DEFAULT 0,
    level INTEGER NOT NULL DEFAULT 1,
    enabled INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (guild_id, user_id)
);

-- Per-server XP/Aura cooldown setting (cogs/settings/leveling.py's
-- /set_cooldown, also read by cogs/economy/aura.py).
CREATE TABLE IF NOT EXISTS server_settings (
    guild_id TEXT PRIMARY KEY,
    cooldown_time INTEGER NOT NULL DEFAULT 480
);

-- Shop (cogs/economy/shop.py) - owned items and equip state, per server.
CREATE TABLE IF NOT EXISTS shop_owned_items (
    guild_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    item_type TEXT NOT NULL CHECK (item_type IN ('title', 'prefix', 'background')),
    item_id TEXT NOT NULL,
    PRIMARY KEY (guild_id, user_id, item_type, item_id)
);
CREATE TABLE IF NOT EXISTS shop_profile (
    guild_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    nickname_unlocked INTEGER NOT NULL DEFAULT 0,
    equipped_title TEXT,
    equipped_prefix TEXT,
    equipped_background TEXT,
    nickname TEXT,
    PRIMARY KEY (guild_id, user_id)
);

-- Profile customization (cogs/profile/profile.py) - global per user, not
-- per-server, same as before (a personal preference, not part of any
-- server's economy).
CREATE TABLE IF NOT EXISTS profiles (
    user_id TEXT PRIMARY KEY,
    color TEXT NOT NULL DEFAULT '#8a5cff',
    bio TEXT NOT NULL DEFAULT ''
);

-- Warnings (cogs/moderation/warnings.py) - global per user (matches the
-- existing behavior: warnings were never keyed by guild before this
-- migration either, so this preserves that rather than silently changing
-- it - worth revisiting separately if that's not actually what's wanted).
CREATE TABLE IF NOT EXISTS warnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    reason TEXT NOT NULL
);

-- Automod (cogs/moderation/automod.py) - per-server config.
CREATE TABLE IF NOT EXISTS automod_config (
    guild_id TEXT PRIMARY KEY,
    spam_threshold INTEGER NOT NULL DEFAULT 5,
    caps_limit INTEGER NOT NULL DEFAULT 70,
    mention_limit INTEGER NOT NULL DEFAULT 5,
    link_filter INTEGER NOT NULL DEFAULT 1,
    promotion_filter INTEGER NOT NULL DEFAULT 1,
    auto_mute_threshold INTEGER NOT NULL DEFAULT 3,
    auto_kick_threshold INTEGER NOT NULL DEFAULT 5
);
CREATE TABLE IF NOT EXISTS automod_blacklisted_words (
    guild_id TEXT NOT NULL,
    word TEXT NOT NULL,
    PRIMARY KEY (guild_id, word)
);

-- Giveaways (cogs/games/giveaway.py) - keyed by the giveaway message.
-- "participants" was tracked in the old JSON but never actually read or
-- written to beyond an empty list at creation - dropped, not migrated.
CREATE TABLE IF NOT EXISTS giveaways (
    message_id TEXT PRIMARY KEY,
    guild_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    prize TEXT NOT NULL,
    host_id TEXT NOT NULL,
    end_time INTEGER NOT NULL
);

-- Stats voice channels (cogs/general/membercount.py) - was keyed by a
-- "{guild_id}_{stat_name}" string; split into real columns here.
CREATE TABLE IF NOT EXISTS stat_channels (
    guild_id TEXT NOT NULL,
    stat_name TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    PRIMARY KEY (guild_id, stat_name)
);

-- Welcome/goodbye setup (cogs/settings/inandout.py) - per-server.
CREATE TABLE IF NOT EXISTS inandout_config (
    guild_id TEXT PRIMARY KEY,
    welcome_message TEXT,
    goodbye_message TEXT,
    announcement_channel_id TEXT,
    welcome_image TEXT,
    goodbye_image TEXT
);

-- On-join announcement embed (cogs/utility/onjoin.py) - a single global
-- template sent to every new server the bot joins, same as before.
CREATE TABLE IF NOT EXISTS onjoin_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    title TEXT,
    description TEXT,
    footer TEXT,
    image_url TEXT
);

-- Reaction roles (cogs/general/reaction_roles.py) - a single global
-- message/mapping, same limitation as before (not per-server - only one
-- reaction-role message works bot-wide right now).
CREATE TABLE IF NOT EXISTS reaction_role_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    role_message_id TEXT
);
CREATE TABLE IF NOT EXISTS reaction_role_mappings (
    emoji TEXT PRIMARY KEY,
    role_id TEXT NOT NULL
);

-- Cached list of guilds the bot is in (cogs/settings/server_command.py,
-- server_notify.py) - fully regenerated (DELETE + INSERT) each time,
-- never incrementally edited.
CREATE TABLE IF NOT EXISTS known_guilds (
    guild_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    member_count INTEGER NOT NULL,
    invite TEXT
);

-- Tickets (cogs/utility/ticket.py) - keyed by the ticket's channel.
CREATE TABLE IF NOT EXISTS tickets (
    channel_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    ticket_number INTEGER NOT NULL
);

-- DM relay target channel (cogs/settings/setupdm.py) - a single global
-- value, same as before.
CREATE TABLE IF NOT EXISTS dm_relay_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    channel_id TEXT
);

-- Trivia (cogs/games/trivia.py). scope = 'global' for the cross-server
-- leaderboard, or a guild id for that server's leaderboard - unifies what
-- were two separate dicts (global_leaderboard/server_leaderboards) into
-- one table.
CREATE TABLE IF NOT EXISTS trivia_stats (
    scope TEXT NOT NULL,
    user_id TEXT NOT NULL,
    wins INTEGER NOT NULL DEFAULT 0,
    games_played INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (scope, user_id)
);
-- Active trivia sessions are genuinely transient (they hold a live
-- discord.Message reference that's lost on restart regardless of storage
-- backend) - question/players stay as JSON blobs rather than being
-- normalized, since nothing ever queries into them by field.
CREATE TABLE IF NOT EXISTS trivia_sessions (
    channel_id TEXT PRIMARY KEY,
    question_json TEXT,
    players_json TEXT,
    category INTEGER,
    message_id TEXT
);

-- Top-level bot config (main.py) - a single global row, same as before
-- (config.json was never per-server).
CREATE TABLE IF NOT EXISTS bot_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    prefix TEXT NOT NULL DEFAULT '!',
    welcome_message TEXT,
    goodbye_message TEXT,
    log_channel_id TEXT,
    welcome_channel_id TEXT,
    announcement_channel_id TEXT
);
"""


def _ensure_column(table, column, coltype):
    """CREATE TABLE IF NOT EXISTS doesn't retroactively add columns to a
    table that already exists - needed when a schema change adds a field
    to something already live in dev/prod."""
    cols = [row[1] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")


def _widen_shop_owned_items_check():
    """Adding the 'background' item type widened this table's CHECK
    constraint, but SQLite can't ALTER a CHECK constraint directly - the
    standard workaround is rebuild-and-swap. Only runs against a database
    that still has the old, narrower constraint; fresh databases already
    get the new one from CREATE TABLE above."""
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='shop_owned_items'"
    ).fetchone()
    if row and "'background'" not in row[0]:
        connection.executescript("""
            ALTER TABLE shop_owned_items RENAME TO shop_owned_items_old;
            CREATE TABLE shop_owned_items (
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                item_type TEXT NOT NULL CHECK (item_type IN ('title', 'prefix', 'background')),
                item_id TEXT NOT NULL,
                PRIMARY KEY (guild_id, user_id, item_type, item_id)
            );
            INSERT INTO shop_owned_items SELECT * FROM shop_owned_items_old;
            DROP TABLE shop_owned_items_old;
        """)


def init_db():
    connection.executescript(SCHEMA)
    _ensure_column("shop_profile", "equipped_background", "TEXT")
    _widen_shop_owned_items_check()
    connection.commit()


init_db()
