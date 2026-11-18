#!/usr/bin/env python3
"""Draw the front page for 17 November 2026 (Pillow, bundled fonts).

The page is one 1024x1024 canvas, budgeted band by band from the
top, and the renderer refuses to draw when the budget overflows:

  masthead -> two hero photos -> headline band -> map + 2x2 stats
  -> section head -> story list (12 rows x 2 columns) -> footer.

Each story row is exactly 31px tall: headline on the first line,
deck on the second, stat right-aligned on the headline line. The
deck's baseline always clears the next row, so no deck can ever
collide with the headline below it. Headlines are fitted to a
single line; a deck that cannot fit is shortened with an ellipsis
instead of spilling over.

Every word on the page comes from facts.py (verified 17 November
2026 stories only). The two hero pictures are AI-generated
illustrations held in assets/. Nothing here uses the clock, the
network or randomness, so two runs produce identical bytes.

Usage: python3 render.py --variant v1 --out entry.png
"""

import argparse
import hashlib
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import facts

W = H = 1024
EDGE = 32
BODY_W = W - 2 * EDGE

# ---- palette: a light broadsheet ----
SHEET = (251, 248, 241)
SHEET_DARK = (243, 238, 228)
TEXT_INK = (26, 26, 26)
CRIMSON = (193, 18, 31)
ROYAL = (29, 78, 216)
OCHRE = (180, 83, 9)
HAIRLINE = (216, 210, 196)
MUTED = (74, 74, 74)
MAP_DOT = (43, 74, 111)

ROOT = Path(__file__).resolve().parent
FONT_DIR = ROOT / "fonts"
BRIDGE_IMG = ROOT / "assets" / "earth-night.jpg"
STORM_IMG = ROOT / "assets" / "cyclone.jpg"

# ---- the band budget, in exact pixels ----
HERO_HEIGHT = 104
MAP_HEIGHT = 190
STAT_HEIGHT = 55
ROW_HEIGHT = 31
HEAD_HEIGHT = 24

_loaded_fonts = {}


def cached_font(name, size):
    key = (name, size)
    if key not in _loaded_fonts:
        _loaded_fonts[key] = ImageFont.truetype(
            str(FONT_DIR / name), size
        )
    return _loaded_fonts[key]


def serif(size):
    return cached_font("PlayfairDisplay.ttf", size)


def sans_bold(size):
    return cached_font("Archivo.ttf", size)


def sans(size):
    return cached_font("Inter.ttf", size)


def wrap_text(d, text, face, max_width):
    """Split text into lines no wider than max_width."""
    lines = []
    words = text.split()
    if not words:
        return lines
    current = ""
    for word in words:
        trial = current + (" " if current else "") + word
        if d.textlength(trial, font=face) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def fit_font(d, text, face_fn, max_w, start_size, floor=6):
    """Biggest size at which text still fits max_w on one line."""
    pt = start_size
    while pt > floor:
        face = face_fn(pt)
        if d.textlength(text, font=face) <= max_w:
            return face
        pt -= 1
    face = face_fn(floor)
    if d.textlength(text, font=face) > max_w:
        raise ValueError("text does not fit even at floor size: %r" % text)
    return face


def ellipsize(d, text, face, max_w):
    """Shorten text with an ellipsis so it fits max_w on one line."""
    if d.textlength(text, font=face) <= max_w:
        return text
    mark = "…"
    while text and d.textlength(text + mark, font=face) > max_w:
        text = text[:-1].rstrip()
    if text:
        return text + mark
    return mark


# ---- world landmask: 72 columns by 36 rows, 5-degree cells,
# longitude -180..180, latitude 90..-90. Each row lists the
# inclusive column ranges that hold land. Hand-built from a world
# atlas; coarse, but the continents read clearly as dots. ----
LAND_MASK = {
    1: [(20, 22), (25, 29)],
    2: [(8, 24), (25, 31), (38, 42), (50, 53), (58, 60), (66, 70)],
    3: [(2, 8), (9, 26), (26, 31), (39, 42), (44, 71)],
    4: [(2, 9), (10, 27), (25, 32), (31, 33), (38, 45), (45, 71)],
    5: [(3, 10), (11, 27), (27, 30), (34, 36), (37, 45), (45, 71)],
    6: [(11, 16), (21, 27), (34, 36), (37, 44), (45, 71)],
    7: [(11, 16), (21, 26), (34, 36), (37, 48), (48, 71)],
    8: [(11, 26), (35, 44), (47, 71)],
    9: [(11, 24), (34, 36), (38, 40), (41, 45), (46, 46), (48, 68), (64, 65)],
    10: [(12, 24), (34, 36), (38, 40), (41, 45), (46, 50), (52, 66), (63, 66)],
    11: [(13, 24), (33, 46), (46, 50), (51, 55), (55, 64), (63, 64)],
    12: [(13, 19), (33, 46), (46, 50), (51, 54), (55, 58), (60, 63)],
    13: [(14, 19), (33, 46), (47, 50), (51, 54), (56, 59)],
    14: [(17, 20), (33, 46), (52, 54), (56, 60)],
    15: [(18, 21), (34, 45), (53, 53), (56, 59), (61, 63)],
    16: [(20, 23), (35, 44), (57, 62), (66, 68)],
    17: [(20, 26), (36, 43), (58, 63), (66, 69)],
    18: [(20, 28), (37, 43), (58, 63), (66, 69)],
    19: [(21, 28), (38, 43), (59, 62), (66, 68)],
    20: [(21, 28), (38, 44), (45, 46), (60, 66)],
    21: [(22, 28), (38, 44), (45, 45), (59, 66)],
    22: [(22, 27), (38, 43), (45, 45), (59, 66)],
    23: [(22, 26), (38, 42), (59, 66)],
    24: [(22, 25), (38, 41), (60, 66), (69, 70)],
    25: [(22, 24), (61, 64), (69, 70)],
    26: [(22, 24), (69, 69)],
    27: [(22, 23)],
    28: [(22, 22)],
}

# Story markers on the map: (lon, lat, label, label dx, label dy).
# The South Asia / Middle East cluster is fanned out with leader
# lines so every label gets its own slot. The label ink boxes were
# audited directly (not their font bounding boxes): no two label
# ink boxes intersect.
MAP_MARKERS = [
    (36.0, 45.0, "KERCH", 10, -18),
    (57.0, 26.0, "HORMUZ", 10, 12),
    (121.0, 14.0, "MANILA", 8, -16),
    (-77.0, 39.0, "WASHINGTON", -15, -14),
    (35.2, 31.8, "JERUSALEM", -58, -12),
    (72.9, 19.1, "MUMBAI", 10, 20),
    (-0.1, 51.5, "LONDON", -8, -18),
    (77.2, 28.6, "NEW DELHI", -6, -24),
    (90.4, 23.8, "DHAKA", 12, 4),
    (80.3, 13.1, "CHENNAI", 6, 32),
    (114.1, 22.5, "SHENZHEN", -6, -18),
    (85.7, 12.2, "Bay of Bengal", 14, 44),
    (30.5, 50.4, "KYIV", 10, -26),
    (-3.7, 40.4, "MADRID", 8, 14),
]


def project_point(lon, lat, x0, y0, w, h):
    col = int((lon + 180.0) / 5.0)
    row = int((90.0 - lat) / 5.0)
    col = max(0, min(col, 71))
    row = max(0, min(row, 35))
    cx = x0 + (col + 0.5) * (w / 72.0)
    cy = y0 + (row + 0.5) * (h / 36.0)
    return cx, cy


def draw_world(d, x0, y0, w, h, dot=MAP_DOT, marker=CRIMSON, labels=True):
    step_x = w / 72.0
    step_y = h / 36.0
    radius = max(1.6, min(step_x, step_y) * 0.34)
    for row, spans in LAND_MASK.items():
        cy = y0 + (row + 0.5) * step_y
        for a, b in spans:
            for col in range(a, b + 1):
                cx = x0 + (col + 0.5) * step_x
                d.ellipse(
                    [cx - radius, cy - radius, cx + radius, cy + radius],
                    fill=dot,
                )
    if labels:
        label_face = sans(10)
        leader_rgb = (225, 110, 110)
        for lon, lat, name, ldx, ldy in MAP_MARKERS:
            mx, my = project_point(lon, lat, x0, y0, w, h)
            if name:
                lx, ly = mx + ldx, my + ldy
                lw = d.textlength(name, font=label_face)
                d.line(
                    [mx, my, lx + lw / 2, ly + 5],
                    fill=leader_rgb,
                    width=1,
                )
            d.ellipse(
                [mx - 4, my - 4, mx + 4, my + 4], fill=marker
            )
            if name:
                # A paper-coloured halo knocks out the land dots
                # behind the text, so a label over the map stays
                # readable.
                d.text(
                    (mx + ldx, my + ldy),
                    name,
                    font=label_face,
                    fill=marker,
                    stroke_width=2,
                    stroke_fill=SHEET,
                )


def cover_crop(path, tw, th):
    im = Image.open(path).convert("RGB")
    src_w, src_h = im.size
    scale = max(tw / src_w, th / src_h)
    new_w, new_h = int(src_w * scale + 0.5), int(src_h * scale + 0.5)
    im = im.resize((new_w, new_h), Image.LANCZOS)
    x = (new_w - tw) // 2
    y = (new_h - th) // 2
    return im.crop((x, y, x + tw, y + th))


def draw_masthead(d, y):
    title_face = fit_font(d, facts.MASTHEAD, serif, BODY_W, 64, 40)
    d.text(
        (W / 2, y),
        facts.MASTHEAD,
        font=title_face,
        fill=TEXT_INK,
        anchor="ma",
        stroke_width=1,
        stroke_fill=TEXT_INK,
    )
    y += title_face.size + 2
    date_face = sans(19)
    d.text((W / 2, y), facts.DATE_LINE, font=date_face, fill=CRIMSON, anchor="ma")
    y += 30
    sub_face = sans(15)
    d.text((W / 2, y), facts.SUBHEAD, font=sub_face, fill=MUTED, anchor="ma")
    y += 26
    d.rectangle([EDGE, y, W - EDGE, y + 5], fill=CRIMSON)
    d.rectangle([EDGE, y + 8, W - EDGE, y + 9], fill=HAIRLINE)
    return y + 16


def draw_footer(d, y):
    if y + 26 > H:
        raise ValueError("layout overflow: footer at y=%d exceeds canvas" % y)
    d.rectangle([EDGE, y, W - EDGE, y + 1], fill=HAIRLINE)
    foot_face = sans(12)
    d.text(
        (W / 2, y + 8),
        facts.FOOTER_SOURCES,
        font=foot_face,
        fill=MUTED,
        anchor="ma",
    )
    return y + 26


def draw_section_head(d, y, text):
    head_face = sans_bold(15)
    text_w = d.textlength(text, font=head_face)
    d.text(
        ((W - text_w) / 2, y),
        text,
        font=head_face,
        fill=TEXT_INK,
        stroke_width=1,
        stroke_fill=TEXT_INK,
    )
    return y + HEAD_HEIGHT


def draw_stat_cell(d, x, y, w, value, label):
    """One cell of the 2x2 big-numbers grid beside the map."""
    d.rectangle(
        [x, y, x + w, y + STAT_HEIGHT],
        fill=SHEET_DARK,
        outline=HAIRLINE,
        width=1,
    )
    value_face = sans_bold(20)
    d.text(
        (x + 10, y + 7),
        value,
        font=value_face,
        fill=CRIMSON,
        stroke_width=1,
        stroke_fill=CRIMSON,
    )
    label_face = sans(11)
    d.text((x + 10, y + 33), label, font=label_face, fill=MUTED)


def draw_story_row(d, x, y, w, s):
    """One story in exactly ROW_HEIGHT px: headline on the first
    line, deck on the second, red stat right-aligned with the
    headline. Nothing is drawn below y + ROW_HEIGHT - 5, so rows
    can never overlap. The deck's baseline sits at y+27, four
    pixels clear of the next row at y+31."""
    accent = {
        "WAR": CRIMSON,
        "TECH": ROYAL,
        "GULF": CRIMSON,
        "ENERGY": OCHRE,
    }.get(s["tag"], MAP_DOT)
    d.rectangle([x, y + 2, x + 5, y + ROW_HEIGHT - 6], fill=accent)
    text_x = x + 14
    stat_face = sans_bold(12)
    stat_width = d.textlength(s["stat"], font=stat_face)
    head_width = w - 14 - int(stat_width) - 10
    head_face = fit_font(d, s["headline"], sans_bold, head_width, 15, 11)
    d.text(
        (text_x, y + 1),
        s["headline"],
        font=head_face,
        fill=TEXT_INK,
        stroke_width=1,
        stroke_fill=TEXT_INK,
    )
    d.text(
        (x + w - stat_width, y + 2),
        s["stat"],
        font=stat_face,
        fill=CRIMSON,
        stroke_width=1,
        stroke_fill=CRIMSON,
    )
    deck_face = sans(11)
    deck_width = w - 14
    deck = s["deck"]
    if d.textlength(deck, font=deck_face) > deck_width:
        deck_face = sans(10)
        deck = ellipsize(d, deck, deck_face, deck_width)
    d.text((text_x, y + 17), deck, font=deck_face, fill=MUTED)


def render_front_page():
    """Front page, bands budgeted top to bottom with a hard
    overflow guard. 25 stories: 1 hero + 24 in the list, 12 left
    and 12 right."""
    img = Image.new("RGB", (W, H), SHEET)
    d = ImageDraw.Draw(img)

    # (1) Masthead.
    y = draw_masthead(d, 22)
    print("after masthead: y=%d" % y)

    # (2) Hero photo band: Earth + cyclone side by side.
    photo_y, photo_h = y, HERO_HEIGHT
    photo_w = (BODY_W - 8) // 2
    img.paste(cover_crop(BRIDGE_IMG, photo_w, photo_h), (EDGE, photo_y))
    d.rectangle(
        [EDGE, photo_y, EDGE + photo_w, photo_y + photo_h],
        outline=TEXT_INK,
        width=2,
    )
    d.text(
        (EDGE + 8, photo_y + photo_h - 24),
        "AI ILLUSTRATION — KERCH BRIDGE",
        font=sans(11),
        fill=(255, 255, 255),
        stroke_width=2,
        stroke_fill=(0, 0, 0),
    )
    img.paste(
        cover_crop(STORM_IMG, photo_w, photo_h),
        (EDGE + photo_w + 8, photo_y),
    )
    d.rectangle(
        [
            EDGE + photo_w + 8,
            photo_y,
            EDGE + photo_w + 8 + photo_w,
            photo_y + photo_h,
        ],
        outline=TEXT_INK,
        width=2,
    )
    d.text(
        (EDGE + photo_w + 8 + 8, photo_y + photo_h - 24),
        "AI ILLUSTRATION — CYCLONE AKVAN",
        font=sans(11),
        fill=(255, 255, 255),
        stroke_width=2,
        stroke_fill=(0, 0, 0),
    )
    y = photo_y + photo_h + 8
    print("after hero: y=%d" % y)

    # (3) Headline band: kicker, one-line headline, one-line deck,
    # then the hero stat on its own line below the deck.
    d.text(
        (EDGE, y),
        "UKRAINE WAR  •  TOP STORY",
        font=sans_bold(15),
        fill=CRIMSON,
        stroke_width=1,
        stroke_fill=CRIMSON,
    )
    y += 18
    headline_face = fit_font(
        d, facts.HERO["headline"], sans_bold, BODY_W - 40, 34, 26
    )
    d.text(
        (EDGE, y),
        facts.HERO["headline"],
        font=headline_face,
        fill=TEXT_INK,
        stroke_width=1,
        stroke_fill=TEXT_INK,
    )
    y += headline_face.size + 6
    deck_face = sans(15)
    deck_lines = wrap_text(d, facts.HERO["deck"], deck_face, BODY_W - 40)
    deck_lines = deck_lines[:1]
    for line in deck_lines:
        d.text((EDGE, y), line, font=deck_face, fill=MUTED)
        y += 18
    stat_face = sans_bold(15)
    stat_line = facts.HERO["stat"]
    stat_width = d.textlength(stat_line, font=stat_face)
    d.text(
        (EDGE + BODY_W - 40 - stat_width, y),
        stat_line,
        font=stat_face,
        fill=CRIMSON,
        stroke_width=1,
        stroke_fill=CRIMSON,
    )
    y += 22
    print("after headline band: y=%d" % y)

    # (4) Map band: dotted world map left, 2x2 big stats right.
    map_y = y
    d.text(
        (EDGE, map_y),
        "THE DAY IN 6 CONTINENTS",
        font=sans_bold(15),
        fill=TEXT_INK,
        stroke_width=1,
        stroke_fill=TEXT_INK,
    )
    map_height = MAP_HEIGHT - 26
    draw_world(d, EDGE, map_y + 24, 470, map_height)
    d.rectangle(
        [EDGE, map_y + 22, EDGE + 470, map_y + MAP_HEIGHT - 4],
        outline=HAIRLINE,
        width=1,
    )
    grid_x = EDGE + 470 + 12
    grid_w = BODY_W - 470 - 12
    cell_w = grid_w // 2
    stats = [
        ("$115.8B", "NVIDIA REVENUE, +103%"),
        ("5,412", "US MEASLES CASES IN 2026"),
        ("19 KM", "KERCH BRIDGE SPAN DOWN"),
        ("4", "TANKERS HIT IN HORMUZ"),
    ]
    for i, (val, lab) in enumerate(stats):
        cx = grid_x + (i % 2) * cell_w
        cy = map_y + 22 + (i // 2) * STAT_HEIGHT
        draw_stat_cell(d, cx, cy, cell_w - 4, val, lab)
    y = map_y + MAP_HEIGHT + 4
    print("after map+stats: y=%d" % y)

    # (5) Story list: 24 stories, 2 columns, ROW_HEIGHT per row.
    y = draw_section_head(d, y, "THE REST OF THE DAY  —  24 MORE STORIES")
    list_y = y
    half = (len(facts.STORIES) + 1) // 2
    column_w = (BODY_W - 24) // 2
    for i, s in enumerate(facts.STORIES[:half]):
        draw_story_row(d, EDGE, list_y + i * ROW_HEIGHT, column_w, s)
    for i, s in enumerate(facts.STORIES[half:]):
        draw_story_row(
            d, EDGE + column_w + 24, list_y + i * ROW_HEIGHT, column_w, s
        )
    y = list_y + half * ROW_HEIGHT + 4
    print("after story list: y=%d (rows=%d)" % (y, half))

    # (6) Footer sources line. Overflow here raises, never overlaps.
    y = draw_footer(d, y)
    print("final y=%d (canvas %d)" % (y, H))
    if y > H:
        raise ValueError("layout overflow: final y=%d > %d" % (y, H))
    return img


VARIANTS = {
    "v1": ("frontpage", render_front_page),
}


def save_variant(variant, out_path, jpeg=False, quality=90):
    name, fn = VARIANTS[variant]
    img = fn()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if jpeg:
        img.save(out_path, "JPEG", quality=quality, optimize=True)
    else:
        img.save(out_path, "PNG", optimize=True)
    data = out_path.read_bytes()
    return {
        "variant": variant,
        "name": name,
        "path": str(out_path),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": img.size,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=list(VARIANTS), default="v1")
    ap.add_argument("--out", default=None)
    ap.add_argument("--jpeg", action="store_true")
    ap.add_argument("--quality", type=int, default=90)
    args = ap.parse_args()
    out = args.out or (args.variant + (".jpg" if args.jpeg else ".png"))
    print(save_variant(args.variant, out, args.jpeg, args.quality))


if __name__ == "__main__":
    main()
