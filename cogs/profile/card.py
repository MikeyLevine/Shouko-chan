"""Pure image-generation logic for /profile - kept separate from the Cog so
it can be exercised in tests without a live Discord connection."""
import io
import os
from PIL import Image, ImageDraw, ImageFont

_ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "fonts")
FONT_BOLD = os.path.join(_ASSETS_DIR, "DejaVuSans-Bold.ttf")
FONT_REGULAR = os.path.join(_ASSETS_DIR, "DejaVuSans.ttf")

CARD_SIZE = (900, 300)
BG_COLOR = (30, 30, 35)
TEXT_COLOR = (255, 255, 255)
MUTED_COLOR = (170, 170, 180)
BAR_BG_COLOR = (60, 60, 68)
DEFAULT_ACCENT = "#8a5cff"


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        raise ValueError(f"Invalid hex color: {hex_color!r}")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def _circle_mask(size):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size[0], size[1]), fill=255)
    return mask


def _truncate(text, max_chars):
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 1] + "…"


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
):
    try:
        accent = hex_to_rgb(accent_hex)
    except ValueError:
        accent = hex_to_rgb(DEFAULT_ACCENT)

    card = Image.new("RGB", CARD_SIZE, BG_COLOR)
    draw = ImageDraw.Draw(card)

    draw.rectangle((0, 0, 10, CARD_SIZE[1]), fill=accent)

    avatar_size = 180
    avatar_pos = (40, 60)
    if avatar_bytes:
        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGB").resize((avatar_size, avatar_size))
    else:
        avatar = Image.new("RGB", (avatar_size, avatar_size), accent)
    card.paste(avatar, avatar_pos, _circle_mask((avatar_size, avatar_size)))
    draw.ellipse(
        (avatar_pos[0] - 4, avatar_pos[1] - 4, avatar_pos[0] + avatar_size + 4, avatar_pos[1] + avatar_size + 4),
        outline=accent, width=4
    )

    text_x = avatar_pos[0] + avatar_size + 40

    font_name = ImageFont.truetype(FONT_BOLD, 42)
    font_label = ImageFont.truetype(FONT_REGULAR, 22)
    font_bio = ImageFont.truetype(FONT_REGULAR, 20)
    font_bar = ImageFont.truetype(FONT_REGULAR, 20)

    draw.text((text_x, 40), _truncate(username, 22), font=font_name, fill=TEXT_COLOR)

    rank_text = f"Rank #{rank}/{total_ranked}" if rank else "Unranked"
    draw.text((text_x, 100), f"{rank_text}   •   Level {level}   •   {aura_balance} Aura", font=font_label, fill=MUTED_COLOR)

    if bio:
        draw.text((text_x, 140), _truncate(bio, 60), font=font_bio, fill=MUTED_COLOR)

    bar_x, bar_y = text_x, 200
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
