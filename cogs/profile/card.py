"""Pure image-generation logic for /profile - kept separate from the Cog so
it can be exercised in tests without a live Discord connection."""
import io
import os
import random
import zlib
from PIL import Image, ImageDraw, ImageFont, ImageFilter

_ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "fonts")
FONT_BOLD = os.path.join(_ASSETS_DIR, "DejaVuSans-Bold.ttf")
FONT_REGULAR = os.path.join(_ASSETS_DIR, "DejaVuSans.ttf")

# DejaVu has no color-emoji glyphs (see the shop/prefix note elsewhere in
# this file) - full-color emoji, like every /slots symbol, need an actual
# color-glyph font. This is a host package (fonts-noto-color-emoji, ~11MB),
# not bundled in the repo like the DejaVu fonts are - dev and prod share
# this one server/filesystem, so installing it once covers both, and 11MB
# is too much to want in git for a font only one feature needs.
NOTO_EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
# This is a bitmap ("strike") font with exactly one baked-in size - any
# other size raises "OSError: invalid pixel size" (found by testing 100,
# 128, and 136 - all failed; only 109 works). Not a font size in the usual
# scalable-outline sense, just the fixed dimensions of the baked bitmap.
NOTO_EMOJI_SIZE = 109
_emoji_font_cache = None
_emoji_font_load_attempted = False


def _emoji_font():
    """Returns None if the font isn't installed, so callers can fall back
    gracefully instead of crashing on a host that's missing it."""
    global _emoji_font_cache, _emoji_font_load_attempted
    if not _emoji_font_load_attempted:
        _emoji_font_load_attempted = True
        try:
            _emoji_font_cache = ImageFont.truetype(NOTO_EMOJI_FONT, NOTO_EMOJI_SIZE)
        except OSError:
            _emoji_font_cache = None
    return _emoji_font_cache

CARD_SIZE = (900, 320)
BG_COLOR = (24, 24, 28)
TEXT_COLOR = (255, 255, 255)
MUTED_COLOR = (175, 175, 185)
BAR_BG_COLOR = (55, 55, 63)
DEFAULT_ACCENT = "#8a5cff"

RANK_BADGE_COLORS = {1: (255, 215, 0), 2: (200, 200, 208), 3: (205, 127, 50)}


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        raise ValueError(f"Invalid hex color: {hex_color!r}")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def _blend(color_a, color_b, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(color_a, color_b))


def _circle_mask(size):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size[0], size[1]), fill=255)
    return mask


def _truncate(text, max_chars):
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 1] + "…"


def _truncate_to_width(draw, text, font, max_width):
    """Pixel-width-aware truncation, for spots where a fixed character
    count isn't safe - e.g. a name column next to a variable-width value
    column, where a char-count limit can still overlap the value text."""
    if draw.textlength(text, font=font) <= max_width:
        return text
    while text and draw.textlength(text + "…", font=font) > max_width:
        text = text[:-1]
    return (text + "…") if text else "…"


def _gradient_image(size, sampler, low_res=(90, 32)):
    """Renders `sampler(x_frac, y_frac) -> (r,g,b)` at low resolution then
    upscales with bilinear interpolation - gives a smooth gradient (even a
    diagonal or radial one) without a per-pixel loop at full card size."""
    lw, lh = low_res
    small = Image.new("RGB", (lw, lh))
    pixels = small.load()
    for y in range(lh):
        for x in range(lw):
            pixels[x, y] = sampler(x / (lw - 1), y / (lh - 1))
    return small.resize(size, Image.BILINEAR)


def _add_stars(image, seed, count=45, color=(255, 255, 255)):
    rng = random.Random(seed)
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for _ in range(count):
        x, y = rng.randint(0, image.width), rng.randint(0, image.height)
        r = rng.choice([1, 1, 1, 2, 2, 3])
        alpha = rng.randint(110, 255)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=color + (alpha,))
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def _add_diagonal_stripes(image, color, alpha=16, spacing=46, width=16):
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = image.size
    for x in range(-h, w, spacing):
        draw.line([(x, 0), (x + h, h)], fill=color + (alpha,), width=width)
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


# Purchasable background styles (cogs/economy/shop.py BACKGROUNDS catalog
# mirrors these ids). "midnight" is the free default - it tints toward the
# user's own accent color, same as before this feature existed. Every other
# style has its own fixed palette, independent of /setcolor - accent still
# controls the avatar ring/border/progress bar/title regardless of which
# background is equipped, so the two customizations layer rather than
# compete. Stars/stripes use a fixed seed (not random per render) so a
# style looks the same every time, not different on every /profile call.
BACKGROUND_STYLES = {
    "midnight": {"name": "Midnight", "accent_tinted": True, "direction": "horizontal"},
    "sunset": {"name": "Sunset", "colors": ((255, 94, 77), (60, 20, 90)), "direction": "horizontal"},
    "ocean": {"name": "Ocean", "colors": ((10, 25, 47), (0, 120, 140)), "direction": "vertical"},
    "forest": {"name": "Forest", "colors": ((8, 26, 18), (24, 90, 48)), "direction": "diagonal"},
    "neon": {"name": "Neon", "colors": ((255, 0, 150), (0, 220, 255)), "direction": "diagonal"},
    "carbon": {"name": "Carbon", "colors": ((18, 18, 20), (30, 30, 34)), "direction": "diagonal", "stripes": True},
    "galaxy": {"name": "Galaxy", "colors": ((10, 5, 25), (45, 15, 70)), "direction": "radial", "stars": True},
}
DEFAULT_BACKGROUND = "midnight"


def _render_background(size, background_id, accent):
    style = BACKGROUND_STYLES.get(background_id, BACKGROUND_STYLES[DEFAULT_BACKGROUND])

    if style.get("accent_tinted"):
        color1, color2 = BG_COLOR, _blend(BG_COLOR, accent, 0.16)
    else:
        color1, color2 = style["colors"]

    direction = style["direction"]
    if direction == "horizontal":
        sampler = lambda xf, yf: _blend(color1, color2, xf)
    elif direction == "vertical":
        sampler = lambda xf, yf: _blend(color1, color2, yf)
    elif direction == "diagonal":
        sampler = lambda xf, yf: _blend(color1, color2, (xf + yf) / 2)
    else:  # radial, glow centered near the avatar
        def sampler(xf, yf, cx=0.15, cy=0.3):
            d = min((((xf - cx) ** 2 + (yf - cy) ** 2) ** 0.5) / 0.9, 1.0)
            return _blend(color1, color2, d)

    image = _gradient_image(size, sampler)

    if style.get("stars"):
        # zlib.crc32, not the builtin hash() - that's randomized per
        # process (PYTHONHASHSEED), which would make the star pattern
        # shuffle on every bot restart instead of staying put.
        image = _add_stars(image, seed=zlib.crc32((background_id + "-stars").encode()))
    if style.get("stripes"):
        image = _add_diagonal_stripes(image, color=(255, 255, 255))

    return image


def _draw_avatar_glow(card, center, radius, color):
    glow = Image.new("RGBA", card.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse(
        (center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius),
        fill=color + (110,)
    )
    glow = glow.filter(ImageFilter.GaussianBlur(22))
    return Image.alpha_composite(card.convert("RGBA"), glow).convert("RGB")


def _text_size(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1], bbox[1]


def generate_profile_card(
    username,
    avatar_bytes,
    level,
    exp_into_level,
    exp_needed_for_level,
    rank,
    total_ranked,
    aura_balance,
    bio,
    accent_hex,
    prefix_text="",
    title_text=None,
    background_id=DEFAULT_BACKGROUND,
):
    try:
        accent = hex_to_rgb(accent_hex)
    except ValueError:
        accent = hex_to_rgb(DEFAULT_ACCENT)

    card = _render_background(CARD_SIZE, background_id or DEFAULT_BACKGROUND, accent)
    draw = ImageDraw.Draw(card)

    avatar_size = 180
    avatar_pos = (40, 70)
    avatar_center = (avatar_pos[0] + avatar_size // 2, avatar_pos[1] + avatar_size // 2)

    card = _draw_avatar_glow(card, avatar_center, avatar_size // 2 + 26, accent)
    draw = ImageDraw.Draw(card)

    if avatar_bytes:
        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGB").resize((avatar_size, avatar_size))
    else:
        avatar = Image.new("RGB", (avatar_size, avatar_size), accent)
    card.paste(avatar, avatar_pos, _circle_mask((avatar_size, avatar_size)))
    draw.ellipse(
        (avatar_pos[0] - 4, avatar_pos[1] - 4, avatar_pos[0] + avatar_size + 4, avatar_pos[1] + avatar_size + 4),
        outline=accent, width=4
    )

    if rank:
        badge_r = 24
        badge_cx = avatar_pos[0] + avatar_size - 6
        badge_cy = avatar_pos[1] + avatar_size - 6
        badge_color = RANK_BADGE_COLORS.get(rank, accent)
        draw.ellipse(
            (badge_cx - badge_r, badge_cy - badge_r, badge_cx + badge_r, badge_cy + badge_r),
            fill=badge_color, outline=BG_COLOR, width=3
        )
        font_badge = ImageFont.truetype(FONT_BOLD, 20)
        text = f"#{rank}"
        tw, th, ty_off = _text_size(draw, text, font_badge)
        draw.text((badge_cx - tw / 2, badge_cy - th / 2 - ty_off), text, font=font_badge, fill=(20, 20, 20))

    # Thin inset border to frame the card without needing outer transparency.
    draw.rounded_rectangle((4, 4, CARD_SIZE[0] - 4, CARD_SIZE[1] - 4), radius=22, outline=accent, width=3)

    text_x = avatar_pos[0] + avatar_size + 40

    # Translucent panel behind the text column - keeps text readable
    # regardless of background style (a bright style like Neon would
    # otherwise wash out the accent-colored title/progress-bar text).
    panel = Image.new("RGBA", card.size, (0, 0, 0, 0))
    ImageDraw.Draw(panel).rounded_rectangle(
        (text_x - 16, 16, CARD_SIZE[0] - 16, CARD_SIZE[1] - 16), radius=18, fill=(0, 0, 0, 90)
    )
    card = Image.alpha_composite(card.convert("RGBA"), panel).convert("RGB")
    draw = ImageDraw.Draw(card)

    font_name = ImageFont.truetype(FONT_BOLD, 42)
    font_label = ImageFont.truetype(FONT_REGULAR, 22)
    font_title = ImageFont.truetype(FONT_BOLD, 20)
    font_bio = ImageFont.truetype(FONT_REGULAR, 20)
    font_bar = ImageFont.truetype(FONT_REGULAR, 20)

    display_name = f"{prefix_text} {username}".strip() if prefix_text else username
    draw.text((text_x, 30), _truncate(display_name, 24), font=font_name, fill=TEXT_COLOR)

    rank_text = f"Rank #{rank}/{total_ranked}" if rank else "Unranked"
    draw.text((text_x, 85), f"{rank_text}   •   Level {level}   •   {aura_balance} Aura", font=font_label, fill=MUTED_COLOR)

    if title_text:
        draw.text((text_x, 118), f"✦ {title_text}", font=font_title, fill=accent)

    if bio:
        draw.text((text_x, 152), _truncate(bio, 60), font=font_bio, fill=MUTED_COLOR)

    bar_x, bar_y = text_x, 220
    bar_w, bar_h = CARD_SIZE[0] - text_x - 40, 28
    draw.rounded_rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), radius=14, fill=BAR_BG_COLOR)

    progress = 0.0
    if exp_needed_for_level > 0:
        progress = max(0.0, min(1.0, exp_into_level / exp_needed_for_level))
    fill_w = int(bar_w * progress)
    if fill_w > 0:
        draw.rounded_rectangle((bar_x, bar_y, bar_x + max(fill_w, bar_h), bar_y + bar_h), radius=14, fill=accent)

    draw.text(
        (bar_x, bar_y + bar_h + 6),
        f"{exp_into_level} / {exp_needed_for_level} XP to next level",
        font=font_bar, fill=MUTED_COLOR
    )

    buffer = io.BytesIO()
    card.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def generate_leaderboard_card(title, entries, accent_hex=DEFAULT_ACCENT):
    """entries: list of {rank, name, avatar_bytes, value_text}, already
    fetched by the caller (avatar_bytes may be None) - kept pure like
    generate_profile_card so it doesn't need a live Discord connection to
    test. Used by /leaderboard (leveling.py) and /richest (aura.py)."""
    try:
        accent = hex_to_rgb(accent_hex)
    except ValueError:
        accent = hex_to_rgb(DEFAULT_ACCENT)

    row_h = 64
    header_h = 76
    pad = 16
    width = 640
    height = header_h + row_h * max(len(entries), 1) + pad

    card = _render_background((width, height), DEFAULT_BACKGROUND, accent)
    draw = ImageDraw.Draw(card)

    font_title = ImageFont.truetype(FONT_BOLD, 30)
    font_name = ImageFont.truetype(FONT_BOLD, 22)
    font_value = ImageFont.truetype(FONT_REGULAR, 20)
    font_rank = ImageFont.truetype(FONT_BOLD, 18)
    font_empty = ImageFont.truetype(FONT_REGULAR, 20)

    draw.text((pad + 8, 20), title, font=font_title, fill=TEXT_COLOR)

    if not entries:
        draw.text((pad + 8, header_h + 16), "No data yet.", font=font_empty, fill=MUTED_COLOR)

    avatar_size = 44
    for i, entry in enumerate(entries):
        y = header_h + i * row_h
        row_center_y = y + row_h // 2

        if i % 2 == 0:
            panel = Image.new("RGBA", card.size, (0, 0, 0, 0))
            ImageDraw.Draw(panel).rectangle((pad, y + 2, width - pad, y + row_h - 2), fill=(0, 0, 0, 40))
            card = Image.alpha_composite(card.convert("RGBA"), panel).convert("RGB")
            draw = ImageDraw.Draw(card)

        badge_color = RANK_BADGE_COLORS.get(entry["rank"], accent)
        badge_r = 16
        bx, by = pad + 20, row_center_y
        draw.ellipse((bx - badge_r, by - badge_r, bx + badge_r, by + badge_r), fill=badge_color)
        rank_text = str(entry["rank"])
        tw, th, ty_off = _text_size(draw, rank_text, font_rank)
        draw.text((bx - tw / 2, by - th / 2 - ty_off), rank_text, font=font_rank, fill=(20, 20, 20))

        avatar_x = pad + 52
        avatar_y = row_center_y - avatar_size // 2
        if entry.get("avatar_bytes"):
            avatar = Image.open(io.BytesIO(entry["avatar_bytes"])).convert("RGB").resize((avatar_size, avatar_size))
        else:
            avatar = Image.new("RGB", (avatar_size, avatar_size), accent)
        card.paste(avatar, (avatar_x, avatar_y), _circle_mask((avatar_size, avatar_size)))
        draw = ImageDraw.Draw(card)

        value_text = entry["value_text"]
        value_w, value_h, value_ty_off = _text_size(draw, value_text, font_value)
        draw.text(
            (width - pad - 12 - value_w, row_center_y - value_h / 2 - value_ty_off),
            value_text, font=font_value, fill=MUTED_COLOR
        )

        name_x = avatar_x + avatar_size + 16
        # Width-aware, not a fixed char count - the value column's width
        # varies (a big Aura number vs. "Level 3"), so a fixed character
        # limit on the name can still run into it.
        available_name_width = (width - pad - 12 - value_w - 16) - name_x
        name_text = _truncate_to_width(draw, entry["name"], font_name, available_name_width)
        tw, th, ty_off = _text_size(draw, name_text, font_name)
        draw.text((name_x, row_center_y - th / 2 - ty_off), name_text, font=font_name, fill=TEXT_COLOR)

    draw.rounded_rectangle((4, 4, width - 4, height - 4), radius=20, outline=accent, width=3)

    buffer = io.BytesIO()
    card.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


SLOTS_ACCENT = "#e8b923"  # warm gold, casino feel - fixed, not user customization
TABLE_ACCENT = "#1f7a4d"  # felt green, for blackjack/poker - distinct from slots' gold

PLAYING_CARD_SIZE = (100, 140)
CARD_FACE_COLOR = (250, 250, 245)
CARD_BACK_COLOR = (35, 40, 90)
CARD_BORDER_COLOR = (180, 180, 180)
RED_SUIT_COLOR = (200, 30, 30)
BLACK_SUIT_COLOR = (25, 25, 30)


def _draw_card_face(rank, suit):
    w, h = PLAYING_CARD_SIZE
    img = Image.new("RGB", (w, h), CARD_FACE_COLOR)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((1, 1, w - 2, h - 2), radius=10, outline=CARD_BORDER_COLOR, width=2)

    color = RED_SUIT_COLOR if suit in ("♥", "♦") else BLACK_SUIT_COLOR
    font_rank = ImageFont.truetype(FONT_BOLD, 28)
    font_suit = ImageFont.truetype(FONT_BOLD, 24)

    draw.text((10, 6), rank, font=font_rank, fill=color)
    draw.text((10, 38), suit, font=font_suit, fill=color)

    rank_w, rank_h, _ = _text_size(draw, rank, font_rank)
    suit_w, suit_h, _ = _text_size(draw, suit, font_suit)
    draw.text((w - 10 - rank_w, h - 10 - rank_h), rank, font=font_rank, fill=color)
    draw.text((w - 10 - suit_w, h - 42 - suit_h), suit, font=font_suit, fill=color)
    return img


def _draw_card_back():
    w, h = PLAYING_CARD_SIZE
    img = Image.new("RGB", (w, h), CARD_BACK_COLOR)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((1, 1, w - 2, h - 2), radius=10, outline=(15, 15, 40), width=2)
    draw.rounded_rectangle((10, 10, w - 11, h - 11), radius=6, outline=(95, 100, 170), width=3)
    return img


def _compose_card_row(cards, hide_first=False, held=None):
    """cards: list of 'RANKSUIT' strings like '10♠'. Returns an RGBA strip
    image - held (optional list of bool, same length as cards) draws a
    small tag under held cards, for /poker."""
    w, h = PLAYING_CARD_SIZE
    gap = 10
    tag_h = 20 if held else 0
    n = len(cards)
    row = Image.new("RGBA", (n * w + (n - 1) * gap, h + tag_h), (0, 0, 0, 0))
    font_tag = ImageFont.truetype(FONT_BOLD, 13)

    for i, card_str in enumerate(cards):
        x = i * (w + gap)
        if hide_first and i == 0:
            face = _draw_card_back()
        else:
            face = _draw_card_face(card_str[:-1], card_str[-1])
        row.paste(face, (x, 0))
        if held and held[i]:
            tag_draw = ImageDraw.Draw(row)
            tag_draw.rectangle((x, h + 2, x + w, h + tag_h), fill=(80, 200, 120, 255))
            tw, th, ty_off = _text_size(tag_draw, "HELD", font_tag)
            tag_draw.text((x + w / 2 - tw / 2, h + 2 - ty_off + (tag_h - 2 - th) / 2), "HELD", font=font_tag, fill=(15, 15, 15))
    return row


def generate_blackjack_image(player_hand, player_total, dealer_hand, dealer_total, reveal_dealer, bet, result_text=None):
    accent = hex_to_rgb(TABLE_ACCENT)
    card_w, card_h = PLAYING_CARD_SIZE
    max_cards = max(len(player_hand), len(dealer_hand))
    content_w = max_cards * card_w + (max_cards - 1) * 10
    width = max(content_w + 80, 500)

    top_margin, label_gap, hand_gap, after_dealer_gap = 24, 34, 24, 20
    bet_line_h, bottom_margin = 30, 20
    result_line_h = 34 if result_text else 0
    height = (top_margin + label_gap + card_h + hand_gap + label_gap + card_h
              + after_dealer_gap + result_line_h + bet_line_h + bottom_margin)

    card = _render_background((width, height), DEFAULT_BACKGROUND, accent)
    draw = ImageDraw.Draw(card)

    font_label = ImageFont.truetype(FONT_BOLD, 22)
    font_result = ImageFont.truetype(FONT_BOLD, 22)
    font_stats = ImageFont.truetype(FONT_REGULAR, 20)

    y = top_margin
    draw.text((30, y), f"Your hand ({player_total})", font=font_label, fill=TEXT_COLOR)
    y += label_gap
    player_row = _compose_card_row(player_hand)
    card.paste(player_row, (30, y), player_row)
    y += card_h + hand_gap

    draw = ImageDraw.Draw(card)
    dealer_label = f"Dealer's hand ({dealer_total})" if reveal_dealer else "Dealer's hand"
    draw.text((30, y), dealer_label, font=font_label, fill=TEXT_COLOR)
    y += label_gap
    dealer_row = _compose_card_row(dealer_hand, hide_first=not reveal_dealer)
    card.paste(dealer_row, (30, y), dealer_row)
    y += card_h + after_dealer_gap

    draw = ImageDraw.Draw(card)
    if result_text:
        draw.text((30, y), result_text, font=font_result, fill=accent)
        y += result_line_h

    draw.text((30, y), f"Bet: {bet} Aura", font=font_stats, fill=MUTED_COLOR)
    draw.rounded_rectangle((4, 4, width - 4, height - 4), radius=20, outline=accent, width=3)

    buffer = io.BytesIO()
    card.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def generate_poker_image(hand, held, bet, result_text=None):
    accent = hex_to_rgb(TABLE_ACCENT)
    card_w, card_h = PLAYING_CARD_SIZE
    n = len(hand)
    content_w = n * card_w + (n - 1) * 10
    width = max(content_w + 80, 500)

    top_margin, label_gap, tag_h, after_cards_gap = 24, 34, 20, 20
    bet_line_h, bottom_margin = 30, 20
    result_line_h = 34 if result_text else 0
    height = top_margin + label_gap + card_h + tag_h + after_cards_gap + result_line_h + bet_line_h + bottom_margin

    card = _render_background((width, height), DEFAULT_BACKGROUND, accent)
    draw = ImageDraw.Draw(card)

    font_label = ImageFont.truetype(FONT_BOLD, 22)
    font_result = ImageFont.truetype(FONT_BOLD, 22)
    font_stats = ImageFont.truetype(FONT_REGULAR, 20)

    y = top_margin
    draw.text((30, y), "Your hand", font=font_label, fill=TEXT_COLOR)
    y += label_gap
    row = _compose_card_row(hand, held=held)
    card.paste(row, (30, y), row)
    y += card_h + tag_h + after_cards_gap

    draw = ImageDraw.Draw(card)
    if result_text:
        draw.text((30, y), result_text, font=font_result, fill=accent)
        y += result_line_h

    draw.text((30, y), f"Bet: {bet} Aura", font=font_stats, fill=MUTED_COLOR)
    draw.rounded_rectangle((4, 4, width - 4, height - 4), radius=20, outline=accent, width=3)

    buffer = io.BytesIO()
    card.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def generate_slots_card(reels, bet, net, new_balance, result_text, won):
    """reels: the 3 spun emoji. result_text must be plain (no emoji) -
    drawn with the regular text font, which can't render color emoji;
    the reels themselves use the color emoji font instead."""
    accent = hex_to_rgb(SLOTS_ACCENT)
    width, height = 640, 330
    card = _render_background((width, height), DEFAULT_BACKGROUND, accent)
    draw = ImageDraw.Draw(card)

    font_title = ImageFont.truetype(FONT_BOLD, 32)
    font_result = ImageFont.truetype(FONT_BOLD, 24)
    font_stats = ImageFont.truetype(FONT_REGULAR, 20)
    emoji_font = _emoji_font()

    draw.text((24, 20), "SLOTS", font=font_title, fill=TEXT_COLOR)

    box_size = 170  # comfortably fits NotoColorEmoji's fixed ~136x128px glyph
    gap = 20
    total_w = box_size * 3 + gap * 2
    start_x = (width - total_w) // 2
    reel_y = 68

    for i, symbol in enumerate(reels):
        bx = start_x + i * (box_size + gap)
        draw.rounded_rectangle(
            (bx, reel_y, bx + box_size, reel_y + box_size), radius=16, fill=BAR_BG_COLOR, outline=accent, width=3
        )
        if emoji_font:
            tw, th, ty_off = _text_size(draw, symbol, emoji_font)
            draw.text(
                (bx + box_size / 2 - tw / 2, reel_y + box_size / 2 - th / 2 - ty_off),
                symbol, font=emoji_font, embedded_color=True
            )
        else:
            # Font not installed on this host - better a visible fallback
            # than a crash. Will render as a tofu box, same DejaVu
            # limitation documented throughout this file.
            tw, th, ty_off = _text_size(draw, symbol, font_title)
            draw.text(
                (bx + box_size / 2 - tw / 2, reel_y + box_size / 2 - th / 2 - ty_off),
                symbol, font=font_title, fill=TEXT_COLOR
            )

    result_y = reel_y + box_size + 24
    tw, th, ty_off = _text_size(draw, result_text, font_result)
    draw.text((width / 2 - tw / 2, result_y - ty_off), result_text, font=font_result, fill=accent if won else MUTED_COLOR)

    stats_text = f"Bet: {bet} Aura   •   Net: {'+' if net >= 0 else ''}{net} Aura   •   Balance: {new_balance} Aura"
    tw, th, ty_off = _text_size(draw, stats_text, font_stats)
    draw.text((width / 2 - tw / 2, result_y + 38 - ty_off), stats_text, font=font_stats, fill=MUTED_COLOR)

    draw.rounded_rectangle((4, 4, width - 4, height - 4), radius=20, outline=accent, width=3)

    buffer = io.BytesIO()
    card.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer
