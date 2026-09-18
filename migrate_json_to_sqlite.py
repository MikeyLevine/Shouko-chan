#!/usr/bin/env python3
"""One-time migration: reads every data/*.json file and populates
data/shouko.db (see db.py for the schema). Run once from the repo root of
each checkout that has real data to migrate (dev and prod each have their
own data/ directory, so this needs running in both places separately).

Old JSON files are left untouched on disk - nothing here deletes them.
Safe to re-run against an empty database; refuses to run against one that
already has data unless --force is passed, since most of this isn't
naturally idempotent (warnings/tickets/etc. would just duplicate).
"""
import json
import os
import sys

import db

DATA_DIR = "data"


def load_json(filename, default):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def already_migrated():
    row = db.connection.execute("SELECT COUNT(*) FROM leveling_accounts").fetchone()
    return row[0] > 0


def migrate_aura():
    data = load_json("aura.json", {})
    count = 0
    for guild_id, guild_data in data.items():
        for user_id, value in guild_data.items():
            if isinstance(value, int):
                # Pre-daily/scavenge legacy shape - just a balance int.
                value = {"balance": value, "last_daily": None, "daily_streak": 0, "last_scavenge": None}
            db.connection.execute(
                "INSERT OR REPLACE INTO aura_accounts (guild_id, user_id, balance, last_daily, daily_streak, last_scavenge) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (guild_id, user_id, value.get("balance", 500), value.get("last_daily"),
                 value.get("daily_streak", 0), value.get("last_scavenge"))
            )
            count += 1
    print(f"  aura_accounts: {count} rows")


def migrate_leveling():
    data = load_json("user_data.json", {})
    count = 0
    for guild_id, guild_data in data.items():
        if not isinstance(guild_data, dict):
            continue
        for user_id, entry in guild_data.items():
            if not isinstance(entry, dict) or "exp" not in entry:
                print(f"  [WARN] Skipping unexpected leveling entry shape for {guild_id}/{user_id}")
                continue
            db.connection.execute(
                "INSERT OR REPLACE INTO leveling_accounts (guild_id, user_id, exp, level, enabled) VALUES (?, ?, ?, ?, ?)",
                (guild_id, user_id, entry.get("exp", 0), entry.get("level", 1), int(entry.get("enabled", True)))
            )
            count += 1
    print(f"  leveling_accounts: {count} rows")


def migrate_server_settings():
    data = load_json("server_settings.json", {})
    count = 0
    for guild_id, entry in data.items():
        db.connection.execute(
            "INSERT OR REPLACE INTO server_settings (guild_id, cooldown_time) VALUES (?, ?)",
            (guild_id, entry.get("cooldown_time", 480))
        )
        count += 1
    print(f"  server_settings: {count} rows")


def migrate_shop():
    data = load_json("shop_inventory.json", {})
    item_count = 0
    profile_count = 0
    for guild_id, guild_data in data.items():
        for user_id, entry in guild_data.items():
            for item_id in entry.get("owned_titles", []):
                db.connection.execute(
                    "INSERT OR REPLACE INTO shop_owned_items (guild_id, user_id, item_type, item_id) VALUES (?, ?, 'title', ?)",
                    (guild_id, user_id, item_id)
                )
                item_count += 1
            for item_id in entry.get("owned_prefixes", []):
                db.connection.execute(
                    "INSERT OR REPLACE INTO shop_owned_items (guild_id, user_id, item_type, item_id) VALUES (?, ?, 'prefix', ?)",
                    (guild_id, user_id, item_id)
                )
                item_count += 1
            db.connection.execute(
                "INSERT OR REPLACE INTO shop_profile (guild_id, user_id, nickname_unlocked, equipped_title, equipped_prefix, nickname) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (guild_id, user_id, int(entry.get("nickname_unlocked", False)),
                 entry.get("equipped_title"), entry.get("equipped_prefix"), entry.get("nickname"))
            )
            profile_count += 1
    print(f"  shop_owned_items: {item_count} rows, shop_profile: {profile_count} rows")


def migrate_profiles():
    data = load_json("profiles.json", {})
    count = 0
    for user_id, entry in data.items():
        db.connection.execute(
            "INSERT OR REPLACE INTO profiles (user_id, color, bio) VALUES (?, ?, ?)",
            (user_id, entry.get("color", "#8a5cff"), entry.get("bio", ""))
        )
        count += 1
    print(f"  profiles: {count} rows")


def migrate_warnings():
    data = load_json("warnings.json", {})
    count = 0
    for user_id, reasons in data.items():
        for reason in reasons:
            db.connection.execute("INSERT INTO warnings (user_id, reason) VALUES (?, ?)", (user_id, reason))
            count += 1
    print(f"  warnings: {count} rows")


def migrate_automod():
    data = load_json("automod_config.json", {})
    config_count = 0
    word_count = 0
    for guild_id, cfg in data.items():
        db.connection.execute(
            "INSERT OR REPLACE INTO automod_config "
            "(guild_id, spam_threshold, caps_limit, mention_limit, link_filter, promotion_filter, auto_mute_threshold, auto_kick_threshold) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (guild_id, cfg.get("spam_threshold", 5), cfg.get("caps_limit", 70), cfg.get("mention_limit", 5),
             int(cfg.get("link_filter", True)), int(cfg.get("promotion_filter", True)),
             cfg.get("auto_mute_threshold", 3), cfg.get("auto_kick_threshold", 5))
        )
        config_count += 1
        for word in cfg.get("blacklisted_words", []):
            db.connection.execute(
                "INSERT OR REPLACE INTO automod_blacklisted_words (guild_id, word) VALUES (?, ?)",
                (guild_id, word)
            )
            word_count += 1
    print(f"  automod_config: {config_count} rows, automod_blacklisted_words: {word_count} rows")


def migrate_giveaways():
    data = load_json("giveaways.json", {})
    count = 0
    for message_id, entry in data.items():
        db.connection.execute(
            "INSERT OR REPLACE INTO giveaways (message_id, guild_id, channel_id, prize, host_id, end_time) VALUES (?, ?, ?, ?, ?, ?)",
            (message_id, entry["guild_id"], entry["channel_id"], entry["prize"], entry["host"], entry["end_time"])
        )
        count += 1
    print(f"  giveaways: {count} rows")


def migrate_stat_channels():
    data = load_json("channel_ids.json", {})
    count = 0
    for key, channel_id in data.items():
        guild_id, stat_name = key.split("_", 1)
        db.connection.execute(
            "INSERT OR REPLACE INTO stat_channels (guild_id, stat_name, channel_id) VALUES (?, ?, ?)",
            (guild_id, stat_name, channel_id)
        )
        count += 1
    print(f"  stat_channels: {count} rows")


def migrate_inandout():
    data = load_json("inandout_config.json", {})
    count = 0
    for guild_id, cfg in data.items():
        db.connection.execute(
            "INSERT OR REPLACE INTO inandout_config (guild_id, welcome_message, goodbye_message, announcement_channel_id, welcome_image, goodbye_image) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (guild_id, cfg.get("welcome_message"), cfg.get("goodbye_message"), cfg.get("announcement_channel_id"),
             cfg.get("welcome_image"), cfg.get("goodbye_image"))
        )
        count += 1
    print(f"  inandout_config: {count} rows")


def migrate_onjoin():
    data = load_json("onjoin.json", None)
    if data is None:
        print("  onjoin_config: 0 rows (no file)")
        return
    db.connection.execute(
        "INSERT OR REPLACE INTO onjoin_config (id, title, description, footer, image_url) VALUES (1, ?, ?, ?, ?)",
        (data.get("title"), data.get("description"), data.get("footer"), data.get("image_url"))
    )
    print("  onjoin_config: 1 row")


def migrate_reaction_roles():
    data = load_json("reaction_roles.json", {})
    role_message_id = data.get("role_message_id")
    db.connection.execute(
        "INSERT OR REPLACE INTO reaction_role_config (id, role_message_id) VALUES (1, ?)",
        (role_message_id,)
    )
    count = 0
    for emoji, role_id in data.get("reaction_roles", {}).items():
        db.connection.execute(
            "INSERT OR REPLACE INTO reaction_role_mappings (emoji, role_id) VALUES (?, ?)",
            (emoji, role_id)
        )
        count += 1
    print(f"  reaction_role_config: 1 row, reaction_role_mappings: {count} rows")


def migrate_known_guilds():
    data = load_json("server_list.json", [])
    count = 0
    for entry in data:
        db.connection.execute(
            "INSERT OR REPLACE INTO known_guilds (guild_id, name, member_count, invite) VALUES (?, ?, ?, ?)",
            (entry["id"], entry["name"], entry["member_count"], entry.get("invite"))
        )
        count += 1
    print(f"  known_guilds: {count} rows")


def migrate_tickets():
    data = load_json("tickets.json", {})
    count = 0
    for channel_id, entry in data.items():
        db.connection.execute(
            "INSERT OR REPLACE INTO tickets (channel_id, user_id, guild_id, ticket_number) VALUES (?, ?, ?, ?)",
            (channel_id, entry["user_id"], entry["guild_id"], entry["ticket_number"])
        )
        count += 1
    print(f"  tickets: {count} rows")


def migrate_dm_relay():
    data = load_json("dm_channel.json", {})
    db.connection.execute(
        "INSERT OR REPLACE INTO dm_relay_config (id, channel_id) VALUES (1, ?)",
        (data.get("dm_channel_id"),)
    )
    print("  dm_relay_config: 1 row")


def migrate_trivia():
    data = load_json("trivia.json", {"global_leaderboard": {}, "server_leaderboards": {}})
    count = 0
    for user_id, stats in data.get("global_leaderboard", {}).items():
        db.connection.execute(
            "INSERT OR REPLACE INTO trivia_stats (scope, user_id, wins, games_played) VALUES ('global', ?, ?, ?)",
            (user_id, stats.get("wins", 0), stats.get("games_played", 0))
        )
        count += 1
    for guild_id, guild_data in data.get("server_leaderboards", {}).items():
        for user_id, stats in guild_data.items():
            db.connection.execute(
                "INSERT OR REPLACE INTO trivia_stats (scope, user_id, wins, games_played) VALUES (?, ?, ?, ?)",
                (guild_id, user_id, stats.get("wins", 0), stats.get("games_played", 0))
            )
            count += 1
    print(f"  trivia_stats: {count} rows")

    sessions = load_json("trivia_sessions.json", {})
    session_count = 0
    for channel_id, session in sessions.items():
        db.connection.execute(
            "INSERT OR REPLACE INTO trivia_sessions (channel_id, question_json, players_json, category, message_id) VALUES (?, ?, ?, ?, ?)",
            (channel_id, json.dumps(session.get("question")), json.dumps(session.get("players", {})),
             session.get("category"), session.get("message_id"))
        )
        session_count += 1
    print(f"  trivia_sessions: {session_count} rows")


def migrate_bot_config():
    data = load_json("config.json", {})
    db.connection.execute(
        "INSERT OR REPLACE INTO bot_config (id, prefix, welcome_message, goodbye_message, log_channel_id, welcome_channel_id, announcement_channel_id) "
        "VALUES (1, ?, ?, ?, ?, ?, ?)",
        (data.get("prefix", "!"), data.get("welcome_message"), data.get("goodbye_message"),
         data.get("log_channel_id"), data.get("welcome_channel_id"), data.get("announcement_channel_id"))
    )
    print("  bot_config: 1 row")


def main():
    force = "--force" in sys.argv
    if already_migrated() and not force:
        print("Database already has leveling_accounts data - refusing to re-run without --force "
              "(most of this migration isn't idempotent and would duplicate rows).")
        sys.exit(1)

    print(f"Migrating JSON data from ./{DATA_DIR}/ into {db.DB_PATH} ...")
    migrate_aura()
    migrate_leveling()
    migrate_server_settings()
    migrate_shop()
    migrate_profiles()
    migrate_warnings()
    migrate_automod()
    migrate_giveaways()
    migrate_stat_channels()
    migrate_inandout()
    migrate_onjoin()
    migrate_reaction_roles()
    migrate_known_guilds()
    migrate_tickets()
    migrate_dm_relay()
    migrate_trivia()
    migrate_bot_config()
    db.connection.commit()
    print("Done. Old JSON files were left untouched on disk.")


if __name__ == "__main__":
    main()
