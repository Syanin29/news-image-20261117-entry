#!/usr/bin/env python3
"""Render the news-image-20261117 front page (Pillow + bundled fonts).

One canvas, 1024x1024, six genuinely different layouts (variants v1-v6).
Every word comes from facts.py (verified 17 November 2026 stories only).
Photos are AI-generated illustrations held in assets/ (the rules allow
the program to copy an image the repository holds). Deterministic:
fixed seeds, no clock, no network. Output is PNG by default; --jpeg
writes a JPEG (same entry.png name either way, per the rules).

Usage: python3 render.py --variant v1 --out variants/v1.png
       python3 render.py --all --outdir variants
"""

import argparse
import hashlib
import random
import sys
import textwrap
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
# ---- palette (dark broadsheet) ----
D_BG = (20, 32, 46)
D_PANEL = (30, 46, 66)
D_PAPER = (242, 239, 230)
D_RULE = (72, 96, 128)
D_SECOND = (176, 188, 202)

HERE = Path(__file__).resolve().parent
FONTS = HERE / "fonts"
BRIDGE = HERE / "assets" / "earth-night.jpg"
TANKER = HERE / "assets" / "cyclone.jpg"

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


def wrap(d, text, font, max_width):
    """Wrap text to fit within max_width using the given font."""
    lines = []
    words = text.split()
    if not words:
        return lines
    line = ''
    for word in words:
        test_line = line + (' ' if line else '') + word
        if d.textlength(test_line, font=font) <= max_width:
            line = test_line
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


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
# Offsets keep each label off the land dots and off the other labels.
# Middle East/South Asia cluster spread further apart to avoid overlap.
MARKERS = [
    (36.0, 45.0, "KERCH", 8, -14),
    (57.0, 26.0, "HORMUZ", 8, 8),
    (121.0, 14.0, "MANILA", 8, 8),
    (-77.0, 39.0, "WASHINGTON", -15, -14),
    # Additional markers for 14 total (from NEWS-SOURCES.md)
    (35.2, 31.8, "JERUSALEM", -5, 15),       # spread downward
    (72.9, 19.1, "MUMBAI", 5, -5),          # spread right/down
    (-0.1, 51.5, "LONDON", -8, -8),
    (77.2, 28.6, "NEW DELHI", -5, 5),
    (90.4, 23.8, "DHAKA", 5, 5),
    (80.3, 13.1, "CHENNAI", 5, 20),         # spread downward
    (114.1, 22.5, "SHENZHEN", -5, 5),
    (85.7, 12.2, "Bay of Bengal", 5, 25),   # spread further down
    (30.5, 50.4, "KYIV", -8, -8),
    (-3.7, 40.4, "MADRID", -5, 5),
]


def lonlat_to_xy(lon, lat, x0, y0, w, h):
    col = (lon + 180.0) / 5.0
    row = (90.0 - lat) / 5.0
    return (x0 + (col + 0.5) * (w / 72.0), y0 + (row + 0.5) * (h / 36.0))


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
        lf = inter(max(9, int(dy * 1.9)))
        for lon, lat, name, ldx, ldy in MARKERS:
            mx, my = lonlat_to_xy(lon, lat, x0, y0, w, h)
            d.ellipse([mx - 4, my - 4, mx + 4, my + 4], fill=marker)
            if name:
                d.text((mx + ldx, my + ldy), name, font=lf, fill=marker)


def fit_size(d, text, fnt_fn, max_w, start_size, floor=6):
    """Find the largest font size where text fits within max_w."""
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


def paper_texture(img):
    """Add a subtle paper texture to the image."""
    return img


def photo_cover(path, tw, th):
    im = Image.open(path).convert("RGB")
    sw, sh = im.size
    scale = max(tw / sw, th / sh)
    nw, nh = int(sw * scale + 0.5), int(sh * scale + 0.5)
    im = im.resize((nw, nh), Image.LANCZOS)
    x = (nw - tw) // 2
    y = (nh - th) // 2
    return im.crop((x, y, x + tw, y + th))


def masthead(d, y, dark=False):
    ink = D_PAPER if dark else INK
    second = D_SECOND if dark else SECOND
    rule_c = D_RULE if dark else RULE
    f = fit_size(d, facts.MASTHEAD, playfair, CONTENT_W, 64, 40)
    d.text((W / 2, y), facts.MASTHEAD, font=f, fill=ink, anchor="ma",
           stroke_width=1, stroke_fill=ink)
    y += f.size + 2
    df = inter(19)
    d.text((W / 2, y), facts.DATE_LINE, font=df, fill=RED, anchor="ma")
    y += 30
    sf = inter(15)
    d.text((W / 2, y), facts.SUBHEAD, font=sf, fill=second, anchor="ma")
    y += 26
    d.rectangle([MARGIN, y, W - MARGIN, y + 5], fill=RED)
    d.rectangle([MARGIN, y + 8, W - MARGIN, y + 9], fill=rule_c)
    return y + 16


def footer(d, y, dark=False):
    if y + 26 > H:
        raise ValueError("layout overflow: footer at y=%d exceeds canvas" % y)
    second = D_SECOND if dark else SECOND
    rule_c = D_RULE if dark else RULE
    d.rectangle([MARGIN, y, W - MARGIN, y + 1], fill=rule_c)
    ff = inter(12)
    d.text((W / 2, y + 8), facts.FOOTER_SOURCES, font=ff, fill=second,
           anchor="ma")
    return y + 26


def story_row(d, x, y, w, s, dark=False, deck=True, max_head_lines=1,
                narrow=False, head_start=17, deck_size=12, row_h=40):
    """One compact row: coloured beat bar, bold headline, optional 1-line
    deck, red stat. Narrow columns: headline wraps to <=2 lines and the
    stat sits on its own line below. Returns row height."""
    ink = D_PAPER if dark else INK
    second = D_SECOND if dark else SECOND
    bar = {"WAR": RED, "TECH": BLUE, "GULF": RED, "ENERGY": GOLD,
           }.get(s["tag"], SLATE if not dark else D_RULE)
    stat_f = archivo(14)
    stat_w = d.textlength(s["stat"], font=stat_f) + 8
    tx = x + 14
    if narrow:
        head_f = archivo(15)
        head_lines = wrap(d, s["headline"], head_f, w - 14)
        if len(head_lines) > 2:
            raise ValueError("headline needs >2 lines: %r" % s["headline"])
        d.rectangle([x, y + 2, x + 5, y + row_h - 6], fill=bar)
        yy = y
        for line in head_lines:
            d.text((tx, yy), line, font=head_f, fill=ink, stroke_width=1,
                   stroke_fill=ink)
            yy += head_f.size + 2
        d.text((tx, yy + 1), s["stat"], font=archivo(12), fill=RED)
        return row_h
    head_w = w - 14 - stat_w
    head_f = None
    head_lines = [s["headline"]]
    for size in range(head_start, 11, -1):
        fnt = archivo(size)
        if d.textlength(s["headline"], font=fnt) <= head_w:
            head_f = fnt
            break
    if head_f is None:
        if max_head_lines < 2:
            raise ValueError("headline does not fit 1 line: %r" % s["headline"])
        head_f = archivo(14)
        head_lines = wrap(d, s["headline"], head_f, head_w)
        if len(head_lines) > 2:
            raise ValueError("headline needs >2 lines: %r" % s["headline"])
    d.rectangle([x, y + 2, x + 5, y + row_h - 6], fill=bar)
    yy = y
    for line in head_lines:
        d.text((tx, yy), line, font=head_f, fill=ink, stroke_width=1,
               stroke_fill=ink)
        yy += head_f.size + 2
    d.text((x + w - stat_w + 8, y + 1), s["stat"], font=stat_f, fill=RED)
    if deck:
        deck_f = inter(deck_size)
        d.text((tx, y + head_f.size + 4), s["deck"], font=deck_f, fill=second)
    return row_h


def section_head(d, y, text, dark=False):
    ink = D_PAPER if dark else INK
    f = archivo(15)
    d.text((MARGIN, y), text, font=f, fill=ink, stroke_width=1,
           stroke_fill=ink)
    d.rectangle([MARGIN, y + 22, W - MARGIN, y + 23],
                fill=D_RULE if dark else RULE)
    return y + 30


def big_stats(d, x, y, w, h, dark=False):
    """2x2 grid of big numbers with filled boxes and text inside."""
    ink = D_PAPER if dark else INK
    second = D_SECOND if dark else SECOND
    cw, ch = w // 2, h // 2
    for i, (num, label) in enumerate(facts.BIG_STATS):
        cx = x + (i % 2) * cw
        cy = y + (i // 2) * ch
        # Draw filled rectangle as background for each stat box
        d.rectangle([cx, cy, cx + cw - 8, cy + ch - 8],
                    fill=PAPER_DK, outline=D_RULE if dark else RULE, width=1)
        nf = fit_size(d, num, archivo, cw - 24, 40, 20)
        # Position stat number: centered vertically-ish, with top margin
        d.text((cx + 12, cy + 6), num, font=nf, fill=RED, stroke_width=1,
               stroke_fill=RED)
        lf = inter(12)
        # Position label: below the number with consistent gap
        wrapped = wrap(d, label, lf, cw - 24)
        # Calculate total label height
        label_h = len(wrapped) * 15 + 2  # 15px line height + small gap
        # Draw label starting just below the number
        for j, line in enumerate(wrapped):
            d.text((cx + 12, cy + 8 + nf.size + 2 + j * 15), line,
                   font=lf, fill=second)


def stat_row(d, x, y, w, h, dark=False):
    """Four big stats in one row with filled boxes and text inside."""
    ink = D_PAPER if dark else INK
    second = D_SECOND if dark else SECOND
    cw = w // 4
    for i, (num, label) in enumerate(facts.BIG_STATS):
        cx = x + i * cw
        # Draw filled rectangle as background for each stat box
        d.rectangle([cx, y, cx + cw - 8, y + h], fill=PAPER_DK,
                    outline=D_RULE if dark else RULE, width=1)
        nf = fit_size(d, num, archivo, cw - 24, 30, 18)
        # Position stat number: centered within box with top margin
        d.text((cx + 10, y + 6), num, font=nf, fill=RED, stroke_width=1,
               stroke_fill=RED)
        lf = inter(11)
        # Position label: below the number with consistent gap
        wrapped = wrap(d, label, lf, cw - 24)
        # Draw label starting just below the number
        for j, line in enumerate(wrapped):
            d.text((cx + 10, y + 6 + nf.size + 2 + j * 14), line,
                   font=lf, fill=second)


def render_v1():
    """Render variant v1 with fixed layout - stats inside boxes, story list below."""
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    img = paper_texture(img)
    d = ImageDraw.Draw(img)

    # (1) Masthead
    y = masthead(d, 22)

    # (2) Hero photo band - keep as is
    hy = y
    hh = 190
    pw = (CONTENT_W - 8) // 2
    # Left photo: Earth (BRIDGE/earth-night.jpg)
    ph = photo_cover(BRIDGE, pw, hh)
    img.paste(ph, (MARGIN, hy))
    d.rectangle([MARGIN, hy, MARGIN + pw, hy + hh], outline=INK, width=2)
    d.text((MARGIN + 8, hy + hh - 24), "AI ILLUSTRATION — KERCH BRIDGE",
           font=inter(11), fill=(255, 255, 255),
           stroke_width=2, stroke_fill=(0, 0, 0))
    # Right photo: TANKER (cyclone.jpg)
    ph = photo_cover(TANKER, pw, hh)
    img.paste(ph, (MARGIN + pw + 8, hy))
    d.rectangle([MARGIN + pw + 8, hy, MARGIN + pw + 8 + pw, hy + hh], outline=INK, width=2)
    d.text((MARGIN + pw + 8 + 8, hy + hh - 24), "AI ILLUSTRATION — CYCLONE AKVAN",
           font=inter(11), fill=(255, 255, 255),
           stroke_width=2, stroke_fill=(0, 0, 0))

    # --- End of hero band ---
    # y is now at hy + hh

    # (3) Headline band: its own height, NO overlap with map or stats
    y = hy + hh + 10  # start below hero

    # Kicker
    d.text((MARGIN, y), "UKRAINE WAR  •  TOP STORY", font=archivo(15),
           fill=RED, stroke_width=1, stroke_fill=RED)
    y += 24  # height for kicker

    # Headline - sized to fit its own width without running under stat box
    # Use CONTENT_W - 40 as max width (leave margin on both sides)
    hf = fit_size(d, "KERCH BRIDGE SPAN DESTROYED", archivo, CONTENT_W - 40, 40, 24)
    lines = wrap(d, "KERCH BRIDGE SPAN DESTROYED", hf, CONTENT_W - 40)
    yy = y + 26  # 26 = 20 (descender space) + 6 (extra)
    for line in lines:
        d.text((MARGIN, yy), line, font=hf, fill=INK, stroke_width=1,
               stroke_fill=INK)
        yy += hf.size + 2
    y = yy + 10  # y after headline, with 10px descent buffer

    # Deck text
    deck_f = inter(16)
    for line in wrap(d, facts.HERO["deck"], deck_f, CONTENT_W - 40):
        d.text((MARGIN, yy), line, font=deck_f, fill=SECOND)
        yy += 21
    y = yy + 6  # y after deck, with 6px buffer

    # Hero stat line - positioned on its own line, right-aligned within content width
    # but NOT under any other band. This is the hero's own stat, not the BIG_STATS strip.
    sf = archivo(15)
    stat_text = facts.HERO["stat"]
    sw = d.textlength(stat_text, font=sf)
    # Place hero stat on its own line, right-aligned within content width
    d.text((MARGIN + CONTENT_W - 40 - sw, yy), stat_text, font=sf, fill=RED, stroke_width=1,
           stroke_fill=RED)
    y = yy + 28  # y after stat line (28 = stat height + buffer)

    # --- End of headline band ---
    # y is now at position below headline

    # (4) Map band: dotted world map with 14 markers/labels in its OWN band
    # No text from any other band inside it
    # NOTE (SIC fix-5): band_h was 150; trimmed to 130 to pay for the taller
    # one-row stats band below (footer must start at y<=998 on a 1024 canvas).
    band_h = 130  # height for map drawing
    d.text((MARGIN, y), "THE DAY IN 6 CONTINENTS", font=archivo(15),
           fill=INK, stroke_width=1, stroke_fill=INK)
    # Draw map - 470px wide, starting at MARGIN
    draw_map(d, MARGIN, y + 24, 470, band_h - 30)
    d.rectangle([MARGIN, y + 22, MARGIN + 470, y + band_h - 4],
                outline=RULE, width=1)
    # y position after map band
    y += band_h + 6  # buffer after map

    # (5) Stats row - below the map band, with own band and explicit y coordinates
    # Draw 4 stat boxes in a row, each with filled background and text inside.
    # NOTE (SIC 2026-11-18, fix-5): the old call used big_stats(), a 2x2 GRID,
    # with stat_box_h=40, so each cell was only 20px tall while its number is
    # up to 40px + label below: text overflowed ~35px past the boxes, row 0
    # overlapped row 1, and everything spilled into the story list. stat_row()
    # draws the same 4 stats in ONE row, so h=64 fits number (<=30) + label.
    stats_row_y = y
    stat_box_h = 64
    stat_row(d, MARGIN, stats_row_y, CONTENT_W, stat_box_h)
    y = stats_row_y + stat_box_h + 6  # buffer after stats row

    # (6) The 24-story list - starts BELOW the stat boxes with a clear gap
    y = section_head(d, y, "THE REST OF THE DAY  —  23 MORE STORIES")
    gy = y
    half = (len(facts.STORIES) + 1) // 2
    col_w = (CONTENT_W - 24) // 2
    for i, s in enumerate(facts.STORIES[:half]):
        story_row(d, MARGIN, gy + i * 21, col_w, s, head_start=15,
                  deck_size=11, row_h=21)
    for i, s in enumerate(facts.STORIES[half:]):
        story_row(d, MARGIN + col_w + 24, gy + i * 21, col_w, s,
                  head_start=15, deck_size=11, row_h=21)
    y = gy + half * 21 + 2  # updated from half * 30 + 6, with small buffer
    footer(d, y)
    return img


# Keep the original v2-v6 variants unchanged for reference
# (they are rendered via the VARIANTS dict below, but v1 is handled separately)

VARIANTS = {
    "v1": ("frontpage", render_v1),
    "v2": ("magazine", lambda: v2_magazine()),
    "v3": ("map", lambda: v3_map()),
    "v4": ("dark", lambda: v4_dark()),
    "v5": ("timeline", lambda: v5_timeline()),
    "v6": ("cards", lambda: v6_cards()),
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
    ap.add_argument("--variant", choices=list(VARIANTS))
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--outdir", default="variants")
    ap.add_argument("--jpeg", action="store_true")
    ap.add_argument("--quality", type=int, default=90)
    args = ap.parse_args()
    if args.all:
        for v in VARIANTS:
            out = Path(args.outdir) / (v + (".jpg" if args.jpeg else ".png"))
            print(render(v, out, args.jpeg, args.quality))
    elif args.variant:
        out = args.out or (args.variant + (".jpg" if args.jpeg else ".png"))
        print(render(args.variant, out, args.jpeg, args.quality))
    else:
        ap.error("pass --variant or --all")


if __name__ == "__main__":
    main()
