"""Pure image-generation logic for /profile - kept separate from the Cog so
it can be exercised in tests without a live Discord connection."""
import io
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

_ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "fonts")
FONT_BOLD = os.path.join(_ASSETS_DIR, "DejaVuSans-Bold.ttf")
FONT_REGULAR = os.path.join(_ASSETS_DIR, "DejaVuSans.ttf")

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


def _draw_gradient_background(draw, size, color1, color2):
    width, height = size
    for x in range(width):
        t = x / (width - 1)
        draw.line([(x, 0), (x, height)], fill=_blend(color1, color2, t))


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
):
    try:
        accent = hex_to_rgb(accent_hex)
    except ValueError:
        accent = hex_to_rgb(DEFAULT_ACCENT)

    card = Image.new("RGB", CARD_SIZE, BG_COLOR)
    draw = ImageDraw.Draw(card)

    # Subtle horizontal gradient toward a faint accent tint, rather than a
    # flat fill - keeps the accent color present throughout the card
    # without competing with the text drawn on top of it.
    gradient_end = _blend(BG_COLOR, accent, 0.16)
    _draw_gradient_background(draw, CARD_SIZE, BG_COLOR, gradient_end)

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
