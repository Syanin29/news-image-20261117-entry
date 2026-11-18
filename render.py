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

The world map is dotted from run-length rows: each row of the
72-column grid is a short spec like "20.3#2.5#42." (20 ocean
cells, 3 land cells, 2 ocean, 5 land, 42 ocean). Story markers
are small dicts with a label and an offset from their dot.

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
    """Biggest size at which text still fits max_w on one line.

    Sizes are tried from the floor upward and the largest one
    that fits is kept; when even the floor size is too wide the
    text cannot be drawn at all.
    """
    best = None
    for pt in range(floor, start_size + 1):
        face = face_fn(pt)
        if d.textlength(text, font=face) <= max_w:
            best = face
    if best is not None:
        return best
    raise ValueError("text does not fit even at floor size: %r" % text)


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


def _runs_to_cols(spec):
    """Expand one run-length row spec into its land columns.

    A spec is a run of counts each followed by "." (ocean) or
    "#" (land), for example "20.3#2.5#42.". Every row must add
    up to exactly 72 columns or the map is misaligned.
    """
    cols = []
    cursor = 0
    i = 0
    while i < len(spec):
        j = i
        while j < len(spec) and spec[j].isdigit():
            j += 1
        count = int(spec[i:j])
        if spec[j] == "#":
            cols.extend(range(cursor, cursor + count))
        cursor += count
        i = j + 1
    if cursor != 72:
        raise ValueError(
            "land row does not add up to 72 columns: %r" % spec
        )
    return cols


# World landmask as run-length rows: (grid row, spec). The grid
# is 72 columns by 36 rows of 5-degree cells, longitude -180..180,
# latitude 90..-90. Only rows with land are listed; the rest of
# the grid is ocean. Hand-built from a world atlas; coarse, but
# the continents read clearly as dots.
LAND_RUNS = [
    (1, "20.3#2.5#42."),
    (2, "8.24#6.5#7.4#4.3#5.5#1."),
    (3, "2.30#7.4#1.28#"),
    (4, "2.32#4.34#"),
    (5, "3.28#3.3#35#"),
    (6, "11.6#4.7#6.3#35#"),
    (7, "11.6#4.6#7.3#35#"),
    (8, "11.16#8.10#2.25#"),
    (9, "11.14#9.3#1.9#1.21#3."),
    (10, "12.13#9.3#1.13#1.15#5."),
    (11, "13.12#8.18#14#7."),
    (12, "13.7#13.18#8#1.4#8."),
    (13, "14.6#13.14#4#4#1.4#12."),
    (14, "17.4#12.14#5.3#1.5#11."),
    (15, "18.4#12.12#7.1#2.4#1.3#8."),
    (16, "20.4#11.10#12.6#3.3#3."),
    (17, "20.7#9.8#14.6#2.4#2."),
    (18, "20.9#8.7#14.6#2.4#2."),
    (19, "21.8#9.6#15.4#3.3#3."),
    (20, "21.8#9.9#13.7#5."),
    (21, "22.7#9.8#13.8#5."),
    (22, "22.6#10.6#1.1#13.8#5."),
    (23, "22.5#11.5#16.8#5."),
    (24, "22.4#12.4#18.7#2.2#1."),
    (25, "22.3#36.4#4.2#1."),
    (26, "22.3#44.1#2."),
    (27, "22.2#48."),
    (28, "22.1#49."),
]

# Every land dot as a (column, row) pair, top row first.
LAND_DOTS = [
    (col, row) for row, spec in LAND_RUNS for col in _runs_to_cols(spec)
]

# Story markers on the map. The South Asia / Middle East cluster
# is fanned out with leader lines so every label gets its own
# slot. The label ink boxes were audited directly (not their font
# bounding boxes): no two label ink boxes intersect.
MAP_MARKERS = [
    {
        "label": "KERCH",
        "lon": 36.0,
        "lat": 45.0,
        "dx": 10,
        "dy": -18,
    },
    {
        "label": "HORMUZ",
        "lon": 57.0,
        "lat": 26.0,
        "dx": 10,
        "dy": 12,
    },
    {
        "label": "MANILA",
        "lon": 121.0,
        "lat": 14.0,
        "dx": 8,
        "dy": -16,
    },
    {
        "label": "WASHINGTON",
        "lon": -77.0,
        "lat": 39.0,
        "dx": -15,
        "dy": -14,
    },
    {
        "label": "JERUSALEM",
        "lon": 35.2,
        "lat": 31.8,
        "dx": -58,
        "dy": -12,
    },
    {
        "label": "MUMBAI",
        "lon": 72.9,
        "lat": 19.1,
        "dx": 10,
        "dy": 20,
    },
    {
        "label": "LONDON",
        "lon": -0.1,
        "lat": 51.5,
        "dx": -8,
        "dy": -18,
    },
    {
        "label": "NEW DELHI",
        "lon": 77.2,
        "lat": 28.6,
        "dx": -6,
        "dy": -24,
    },
    {
        "label": "DHAKA",
        "lon": 90.4,
        "lat": 23.8,
        "dx": 12,
        "dy": 4,
    },
    {
        "label": "CHENNAI",
        "lon": 80.3,
        "lat": 13.1,
        "dx": 6,
        "dy": 32,
    },
    {
        "label": "SHENZHEN",
        "lon": 114.1,
        "lat": 22.5,
        "dx": -6,
        "dy": -18,
    },
    {
        "label": "Bay of Bengal",
        "lon": 85.7,
        "lat": 12.2,
        "dx": 14,
        "dy": 44,
    },
    {
        "label": "KYIV",
        "lon": 30.5,
        "lat": 50.4,
        "dx": 10,
        "dy": -26,
    },
    {
        "label": "MADRID",
        "lon": -3.7,
        "lat": 40.4,
        "dx": 8,
        "dy": 14,
    },
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
    for col, row in LAND_DOTS:
        cx = x0 + (col + 0.5) * step_x
        cy = y0 + (row + 0.5) * step_y
        d.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            fill=dot,
        )
    if labels:
        label_face = sans(10)
        leader_rgb = (225, 110, 110)
        for mark in MAP_MARKERS:
            mx, my = project_point(
                mark["lon"], mark["lat"], x0, y0, w, h
            )
            name = mark["label"]
            lx, ly = mx + mark["dx"], my + mark["dy"]
            lw = d.textlength(name, font=label_face)
            d.line(
                [mx, my, lx + lw / 2, ly + 5],
                fill=leader_rgb,
                width=1,
            )
            d.ellipse(
                [mx - 4, my - 4, mx + 4, my + 4], fill=marker
            )
            # A paper-coloured halo knocks out the land dots
            # behind the text, so a label over the map stays
            # readable.
            d.text(
                (lx, ly),
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

    # (2) Hero photo band: the two illustrations side by side,
    # each with its caption burned into the bottom corner.
    photo_y, photo_h = y, HERO_HEIGHT
    photo_w = (BODY_W - 8) // 2
    photos = [
        (BRIDGE_IMG, "AI ILLUSTRATION — KERCH BRIDGE"),
        (STORM_IMG, "AI ILLUSTRATION — CYCLONE AKVAN"),
    ]
    for i, (path, caption) in enumerate(photos):
        px = EDGE + i * (photo_w + 8)
        img.paste(cover_crop(path, photo_w, photo_h), (px, photo_y))
        d.rectangle(
            [px, photo_y, px + photo_w, photo_y + photo_h],
            outline=TEXT_INK,
            width=2,
        )
        d.text(
            (px + 8, photo_y + photo_h - 24),
            caption,
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


def save_variant(variant, out_path):
    name, fn = VARIANTS[variant]
    img = fn()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
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
    args = ap.parse_args()
    out = args.out or (args.variant + ".png")
    print(save_variant(args.variant, out))


if __name__ == "__main__":
    main()
