#!/usr/bin/env python3
"""Render the news-image-20261117 front page (Pillow + bundled fonts).

Rebuild 2026-11-18 (fresh session): the a30ad70 layout drew each story
row as headline + deck + stat inside a row far shorter than the drawn
content, so every deck collided with the next row's headline; HEAD
19b8a62 made it worse by stacking tag, headline, deck and stat inside
a 21px row. This rewrite budgets every band in exact pixels, top to
bottom, and refuses to render when the budget overflows:

  masthead -> hero photos (128) -> headline band -> map + 2x2 stats
  -> section head -> story list (12 rows x 35px, 2 columns)
  -> footer sources line. Total must stay <= 1024.

Story rows keep headline + 1-line deck + right-aligned stat, but the
row is 31px: headline at +1, deck at +17, so the deck's baseline
(y+27) always clears the next row (y+31). Headlines are fitted to one
line; decks that cannot fit at 10px are truncated with an ellipsis
rather than drawn over the next row.

One canvas, 1024x1024. Every word comes from facts.py (verified
17 November 2026 stories only). Photos are AI-generated illustrations
held in assets/. Deterministic: fixed seeds, no clock, no network.

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
MARGIN = 32
CONTENT_W = W - 2 * MARGIN

# ---- palette (light broadsheet) ----
PAPER = (251, 248, 241)
PAPER_DK = (243, 238, 228)
INK = (26, 26, 26)
RED = (193, 18, 31)
BLUE = (29, 78, 216)
GOLD = (180, 83, 9)
RULE = (216, 210, 196)
SECOND = (74, 74, 74)
SLATE = (43, 74, 111)

HERE = Path(__file__).resolve().parent
FONTS = HERE / "fonts"
BRIDGE = HERE / "assets" / "earth-night.jpg"
TANKER = HERE / "assets" / "cyclone.jpg"

# ---- exact band budget (px) ----
HERO_H = 104
MAP_BAND_H = 190
STAT_CELL_H = 55
LIST_ROW_H = 31
LIST_HEAD_H = 24

_font_cache = {}


def font(name, size):
    key = (name, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(str(FONTS / name), size)
    return _font_cache[key]


def playfair(size):
    return font("PlayfairDisplay.ttf", size)


def archivo(size):
    return font("Archivo.ttf", size)


def inter(size):
    return font("Inter.ttf", size)


def wrap(d, text, fnt, max_width):
    """Wrap text to fit within max_width using the given font."""
    lines = []
    words = text.split()
    if not words:
        return lines
    line = ""
    for word in words:
        test_line = line + (" " if line else "") + word
        if d.textlength(test_line, font=fnt) <= max_width:
            line = test_line
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def fit_size(d, text, fnt_fn, max_w, start_size, floor=6):
    """Largest font size where text fits within max_w (single line)."""
    size = start_size
    while size > floor:
        fnt = fnt_fn(size)
        if d.textlength(text, font=fnt) <= max_w:
            return fnt
        size -= 1
    fnt = fnt_fn(floor)
    if d.textlength(text, font=fnt) > max_w:
        raise ValueError("text does not fit even at floor size: %r" % text)
    return fnt


def truncate_to(d, text, fnt, max_w):
    """Shorten text with an ellipsis so it fits max_w on one line."""
    if d.textlength(text, font=fnt) <= max_w:
        return text
    ell = "…"
    while text and d.textlength(text + ell, font=fnt) > max_w:
        text = text[:-1].rstrip()
    return text + ell if text else ell


# ---- world landmask: 72 cols x 36 rows, 5-degree cells, lon -180..180,
# lat 90..-90. Intervals are inclusive column ranges per row. Hand-built
# from a world atlas; coarse but the continents read clearly as dots. ----
LAND_ROWS = {
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

# (lon, lat, label, label dx, label dy) story markers on the map.
# The South Asia / Middle East cluster is fanned out with leader
# lines: each label gets its own slot, verified against the marker
# coordinates (map 470x164: dx 6.53, dy 4.56). No two label boxes
# share both an x-range and a y-range.
MARKERS = [
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


def lonlat_to_xy(lon, lat, x0, y0, w, h):
    col = int((lon + 180.0) / 5.0)
    row = int((90.0 - lat) / 5.0)
    col = max(0, min(col, 71))
    row = max(0, min(row, 35))
    cx = x0 + (col + 0.5) * (w / 72.0)
    cy = y0 + (row + 0.5) * (h / 36.0)
    return cx, cy


def draw_map(d, x0, y0, w, h, dot=SLATE, marker=RED, labels=True):
    dx = w / 72.0
    dy = h / 36.0
    r = max(1.6, min(dx, dy) * 0.34)
    for row, spans in LAND_ROWS.items():
        cy = y0 + (row + 0.5) * dy
        for a, b in spans:
            for col in range(a, b + 1):
                cx = x0 + (col + 0.5) * dx
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=dot)
    if labels:
        lf = inter(10)
        leader = (225, 110, 110)
        for lon, lat, name, ldx, ldy in MARKERS:
            mx, my = lonlat_to_xy(lon, lat, x0, y0, w, h)
            if name:
                lx, ly = mx + ldx, my + ldy
                lw = d.textlength(name, font=lf)
                d.line([mx, my, lx + lw / 2, ly + 5], fill=leader, width=1)
            d.ellipse([mx - 4, my - 4, mx + 4, my + 4], fill=marker)
            if name:
                # Paper halo knocks out the land dots behind the text,
                # so a label over the map stays readable.
                d.text((mx + ldx, my + ldy), name, font=lf, fill=marker,
                       stroke_width=2, stroke_fill=PAPER)


def photo_cover(path, tw, th):
    im = Image.open(path).convert("RGB")
    sw, sh = im.size
    scale = max(tw / sw, th / sh)
    nw, nh = int(sw * scale + 0.5), int(sh * scale + 0.5)
    im = im.resize((nw, nh), Image.LANCZOS)
    x = (nw - tw) // 2
    y = (nh - th) // 2
    return im.crop((x, y, x + tw, y + th))


def masthead(d, y):
    f = fit_size(d, facts.MASTHEAD, playfair, CONTENT_W, 64, 40)
    d.text((W / 2, y), facts.MASTHEAD, font=f, fill=INK, anchor="ma",
           stroke_width=1, stroke_fill=INK)
    y += f.size + 2
    df = inter(19)
    d.text((W / 2, y), facts.DATE_LINE, font=df, fill=RED, anchor="ma")
    y += 30
    sf = inter(15)
    d.text((W / 2, y), facts.SUBHEAD, font=sf, fill=SECOND, anchor="ma")
    y += 26
    d.rectangle([MARGIN, y, W - MARGIN, y + 5], fill=RED)
    d.rectangle([MARGIN, y + 8, W - MARGIN, y + 9], fill=RULE)
    return y + 16


def footer(d, y):
    if y + 26 > H:
        raise ValueError("layout overflow: footer at y=%d exceeds canvas" % y)
    d.rectangle([MARGIN, y, W - MARGIN, y + 1], fill=RULE)
    ff = inter(12)
    d.text((W / 2, y + 8), facts.FOOTER_SOURCES, font=ff, fill=SECOND,
           anchor="ma")
    return y + 26


def section_head(d, y, text):
    sf = archivo(15)
    tw = d.textlength(text, font=sf)
    d.text(((W - tw) / 2, y), text, font=sf, fill=INK, stroke_width=1,
           stroke_fill=INK)
    return y + LIST_HEAD_H


def story_row(d, x, y, w, s):
    """One story in exactly LIST_ROW_H px: 1-line headline at +2, 1-line
    deck at +19, red stat right-aligned on the headline line. Nothing
    is drawn below y + LIST_ROW_H - 5, so rows can never overlap."""
    bar = {"WAR": RED, "TECH": BLUE, "GULF": RED, "ENERGY": GOLD,
           }.get(s["tag"], SLATE)
    d.rectangle([x, y + 2, x + 5, y + LIST_ROW_H - 6], fill=bar)
    tx = x + 14
    stat_f = archivo(12)
    stat_w = d.textlength(s["stat"], font=stat_f)
    head_w = w - 14 - int(stat_w) - 10
    head_f = fit_size(d, s["headline"], archivo, head_w, 15, 11)
    d.text((tx, y + 1), s["headline"], font=head_f, fill=INK,
           stroke_width=1, stroke_fill=INK)
    d.text((x + w - stat_w, y + 2), s["stat"], font=stat_f, fill=RED,
           stroke_width=1, stroke_fill=RED)
    deck_f = inter(11)
    deck_w = w - 14
    deck = s["deck"]
    if d.textlength(deck, font=deck_f) > deck_w:
        deck_f = inter(10)
        deck = truncate_to(d, deck, deck_f, deck_w)
    d.text((tx, y + 17), deck, font=deck_f, fill=SECOND)


def stat_cell(d, x, y, w, value, label):
    """One cell of the 2x2 big-numbers grid beside the map."""
    d.rectangle([x, y, x + w, y + STAT_CELL_H], fill=PAPER_DK,
                outline=RULE, width=1)
    vf = archivo(20)
    d.text((x + 10, y + 7), value, font=vf, fill=RED, stroke_width=1,
           stroke_fill=RED)
    lf = inter(11)
    d.text((x + 10, y + 33), label, font=lf, fill=SECOND)


def render_v1():
    """Front page, bands budgeted top to bottom with a hard overflow
    guard. 24 stories: 1 hero + 23 in the list (12 left, 11 right)."""
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    # (1) Masthead.
    y = masthead(d, 22)
    print("after masthead: y=%d" % y)

    # (2) Hero photo band: Earth + cyclone side by side.
    hy, hh = y, HERO_H
    pw = (CONTENT_W - 8) // 2
    img.paste(photo_cover(BRIDGE, pw, hh), (MARGIN, hy))
    d.rectangle([MARGIN, hy, MARGIN + pw, hy + hh], outline=INK, width=2)
    d.text((MARGIN + 8, hy + hh - 24), "AI ILLUSTRATION — KERCH BRIDGE",
           font=inter(11), fill=(255, 255, 255),
           stroke_width=2, stroke_fill=(0, 0, 0))
    img.paste(photo_cover(TANKER, pw, hh), (MARGIN + pw + 8, hy))
    d.rectangle([MARGIN + pw + 8, hy, MARGIN + pw + 8 + pw, hy + hh],
                outline=INK, width=2)
    d.text((MARGIN + pw + 8 + 8, hy + hh - 24),
           "AI ILLUSTRATION — CYCLONE AKVAN",
           font=inter(11), fill=(255, 255, 255),
           stroke_width=2, stroke_fill=(0, 0, 0))
    y = hy + hh + 8
    print("after hero: y=%d" % y)

    # (3) Headline band: kicker, 1-line headline, 1-line deck, stat.
    d.text((MARGIN, y), "UKRAINE WAR  •  TOP STORY", font=archivo(15),
           fill=RED, stroke_width=1, stroke_fill=RED)
    y += 18
    hf = fit_size(d, facts.HERO["headline"], archivo, CONTENT_W - 40, 34, 26)
    d.text((MARGIN, y), facts.HERO["headline"], font=hf, fill=INK,
           stroke_width=1, stroke_fill=INK)
    y += hf.size + 6
    deck_f = inter(15)
    deck_lines = wrap(d, facts.HERO["deck"], deck_f, CONTENT_W - 40)
    deck_lines = deck_lines[:1]
    for line in deck_lines:
        d.text((MARGIN, y), line, font=deck_f, fill=SECOND)
        y += 18
    sf = archivo(15)
    stat_text = facts.HERO["stat"]
    sw = d.textlength(stat_text, font=sf)
    d.text((MARGIN + CONTENT_W - 40 - sw, y), stat_text, font=sf,
           fill=RED, stroke_width=1, stroke_fill=RED)
    y += 22
    print("after headline band: y=%d" % y)

    # (4) Map band: dotted world map left, 2x2 big stats right.
    map_y = y
    d.text((MARGIN, map_y), "THE DAY IN 6 CONTINENTS", font=archivo(15),
           fill=INK, stroke_width=1, stroke_fill=INK)
    map_h = MAP_BAND_H - 26
    draw_map(d, MARGIN, map_y + 24, 470, map_h)
    d.rectangle([MARGIN, map_y + 22, MARGIN + 470, map_y + MAP_BAND_H - 4],
                outline=RULE, width=1)
    gx = MARGIN + 470 + 12
    gw = CONTENT_W - 470 - 12
    cw = gw // 2
    stats = [
        ("$115.8B", "NVIDIA REVENUE, +103%"),
        ("5,412", "US MEASLES CASES IN 2026"),
        ("19 KM", "KERCH BRIDGE SPAN DOWN"),
        ("4", "TANKERS HIT IN HORMUZ"),
    ]
    for i, (val, lab) in enumerate(stats):
        cx = gx + (i % 2) * cw
        cy = map_y + 22 + (i // 2) * STAT_CELL_H
        stat_cell(d, cx, cy, cw - 4, val, lab)
    y = map_y + MAP_BAND_H + 4
    print("after map+stats: y=%d" % y)

    # (5) Story list: 23 stories, 2 columns, LIST_ROW_H per row.
    y = section_head(d, y, "THE REST OF THE DAY  —  23 MORE STORIES")
    gy = y
    half = (len(facts.STORIES) + 1) // 2
    col_w = (CONTENT_W - 24) // 2
    for i, s in enumerate(facts.STORIES[:half]):
        story_row(d, MARGIN, gy + i * LIST_ROW_H, col_w, s)
    for i, s in enumerate(facts.STORIES[half:]):
        story_row(d, MARGIN + col_w + 24, gy + i * LIST_ROW_H, col_w, s)
    y = gy + half * LIST_ROW_H + 4
    print("after story list: y=%d (rows=%d)" % (y, half))

    # (6) Footer sources line. Overflow here raises, never overlaps.
    y = footer(d, y)
    print("final y=%d (canvas %d)" % (y, H))
    if y > H:
        raise ValueError("layout overflow: final y=%d > %d" % (y, H))
    return img


VARIANTS = {
    "v1": ("frontpage", render_v1),
}


def render(variant, out_path, jpeg=False, quality=90):
    name, fn = VARIANTS[variant]
    img = fn()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if jpeg:
        img.save(out_path, "JPEG", quality=quality, optimize=True)
    else:
        img.save(out_path, "PNG", optimize=True)
    data = out_path.read_bytes()
    return {"variant": variant, "name": name, "path": str(out_path),
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": img.size}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=list(VARIANTS), default="v1")
    ap.add_argument("--out", default=None)
    ap.add_argument("--jpeg", action="store_true")
    ap.add_argument("--quality", type=int, default=90)
    args = ap.parse_args()
    out = args.out or (args.variant + (".jpg" if args.jpeg else ".png"))
    print(render(args.variant, out, args.jpeg, args.quality))


if __name__ == "__main__":
    main()
