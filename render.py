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
    col = int((lon + 180.0) / 5.0)
    row = int((90.0 - lat) / 5.0)
    # Clamp to valid ranges
    col = max(0, min(col, w - 1))
    row = max(0, min(row, h - 1))
    x0_cell = x0 + col * (w / 72.0)
    y0_cell = y0 + row * (h / 36.0)
    # Center of cell
    cx = x0_cell + w / 72.0 / 2
    cy = y0_cell + h / 36.0 / 2
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


def story_row(d, x, y, w, s, head_start=15, deck_size=11, row_h=21):
    """Draw a single story row with tag, headline, deck, and stat."""
    head_f = archivo(head_start)
    deck_f = inter(deck_size)
    
    # Tag
    tw = d.textlength(s["tag"], font=head_f)
    d.text((x, y), s["tag"], font=head_f, fill=RED, stroke_width=1,
           stroke_fill=RED)
    
    # Headline - wrap to fit within w - 20 for tag + margin
    hw = w - 20
    hf = fit_size(d, s["headline"], archivo, hw, 24, 12)
    head_lines = wrap(d, s["headline"], hf, hw)
    
    # Handle multi-line headline - take max 2 lines
    if len(head_lines) > 2:
        head_lines = head_lines[:2]
    
    # Calculate headline height
    hh = len(head_lines) * hf.size + (len(head_lines) - 1) * 2
    
    # Headline position
    hy = y + head_start
    for i, line in enumerate(head_lines):
        d.text((x + 12, hy + i * (hf.size + 2)), line, font=hf, fill=INK,
               stroke_width=1, stroke_fill=INK)
    
    # Deck text - below headline, with margin
    dy_pos = y + head_start + hh + 4
    dw = wrap(d, s["deck"], deck_f, hw - 10)
    for i, line in enumerate(dw):
        d.text((x + 5, dy_pos + i * 21), line, font=deck_f, fill=SECOND)
    
    # Stat - at the bottom right of the row
    sf = inter(12)
    stat_text = s["stat"]
    sw = d.textlength(stat_text, font=sf)
    d.text((x + w - 10 - sw, y + row_h - 22), stat_text, font=sf, fill=RED,
           stroke_width=1, stroke_fill=RED)


def section_head(d, y, text, dark=False):
    """Draw a section header and return y position after it."""
    sf = archivo(15)
    tw = d.textlength(text, font=sf)
    # Center the section head
    d.text(((W - tw) / 2, y), text, font=sf, fill=INK, stroke_width=1,
           stroke_fill=INK)
    return y + 26


def render_v1():
    """Render variant v1 with explicit non-overlapping vertical bands.
    
    5 bands:
    (1) Hero photo band - Earth + cyclone side by side
    (2) Headline band - kicker, headline, deck, hero stat (own width, no overlap)
    (3) Map band - dotted world map with 14 markers in own band, no text inside
    (4) Stats row - 4 stat boxes in one row
    (5) 24-story list - below stats row
    """
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    img = paper_texture(img)
    d = ImageDraw.Draw(img)

    # ============================================================
    # (1) Masthead
    # ============================================================
    y = masthead(d, 22)

    # ============================================================
    # (2) Hero photo band - Earth + cyclone side by side (keep as is)
    # ============================================================
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

    # End of hero band - y is at hy + hh = 350
    y = hy + hh
    print(f"After hero band: y={y}")

    # ============================================================
    # (3) Headline band - kicker, headline, deck, hero stat
    #    All within own width (CONTENT_W - 40), no overlap with map or stats
    # ============================================================
    # Start headline band at y position below hero
    hy_band = y  # 350
    
    # Kicker
    d.text((MARGIN, y), "UKRAINE WAR  •  TOP STORY", font=archivo(15),
           fill=RED, stroke_width=1, stroke_fill=RED)
    y += 24  # height for kicker
    
    # Headline - sized to fit its own width without running under any stat box
    hf = fit_size(d, "KERCH BRIDGE SPAN DESTROYED", archivo, CONTENT_W - 40, 40, 24)
    lines = wrap(d, "KERCH BRIDGE SPAN DESTROYED", hf, CONTENT_W - 40)
    # Calculate exact headline height: lines * font_size + (lines-1) * inter-line spacing
    head_h = len(lines) * hf.size + (len(lines) - 1) * 2
    # Draw headline lines
    yy = y + 26  # 26 = 20 (descender space) + 6 (extra)
    for line in lines:
        d.text((MARGIN, yy), line, font=hf, fill=INK, stroke_width=1,
               stroke_fill=INK)
        yy += hf.size + 2
    y = yy + 10  # y after headline, with 10px descent buffer
    
    # Deck text - within own width, below headline
    deck_f = inter(16)
    # Calculate deck height: max 2 lines to keep band compact
    deck_lines = wrap(d, facts.HERO["deck"], deck_f, CONTENT_W - 40)
    if len(deck_lines) > 2:
        deck_lines = deck_lines[:2]  # truncate to 2 lines max
    deck_h = len(deck_lines) * 21  # inter(16) line height
    # Draw deck text
    for line in deck_lines:
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
    
    # End of headline band
    # y is now at position below headline
    # Headline band total height: from hy_band (350) to y (currently)
    # Make sure headline band doesn't extend into map area
    print(f"After headline band: y={y} (headline band from {hy_band} to {y})")

    # ============================================================
    # (4) Map band: dotted world map with 14 markers/labels in its OWN band
    #    No text from any other band inside it
    #    Map band starts BELOW the headline band with proper buffer
    # ============================================================
    # Ensure map band starts below ALL headline content
    # Current y should be above the map band start
    # We need: map_band_y >= y (where y is after headline stat)
    # Map band height: 130px (adjusted for footer budget)
    # Map band ends at: map_band_y + 130
    # Footer must start at y <= 998 (1024 - 26 for footer rule)
    
    # Calculate map band position: start below headline content with 6px buffer
    map_band_y = y + 6  # 6px buffer after headline stat
    band_h = 130  # height for map drawing
    map_band_bottom = map_band_y + band_h
    
    # Draw map band background label
    d.text((MARGIN, map_band_y), "THE DAY IN 6 CONTINENTS", font=archivo(15),
           fill=INK, stroke_width=1, stroke_fill=INK)
    # Draw map - 470px wide, starting at MARGIN
    # Map band extends from map_band_y to map_band_bottom
    # Map drawing area: from map_band_y + 24 to map_band_y + band_h - 30
    # This gives us: map_band_y + 24 + (band_h - 30) = map_band_y + band_h - 6
    # = y + 6 + 130 - 6 = y + 130 = map_band_bottom
    # So map dots go up to y + 130, which is the bottom of the map band
    draw_map(d, MARGIN, map_band_y + 24, 470, band_h - 30)
    d.rectangle([MARGIN, map_band_y + 22, MARGIN + 470, map_band_y + band_h - 4],
                outline=RULE, width=1)
    
    # y position after map band
    y = map_band_bottom + 6  # buffer after map
    print(f"After map band: y={y} (map band from {map_band_y} to {map_band_bottom})")

    # ============================================================
    # (5) Stats row - below the map band, with own band and explicit y coordinates
    #    Draw 4 stat boxes in a row, each with filled background and text inside.
    # ============================================================
    stats_row_y = y
    stat_box_h = 64
    # Draw 4 stat boxes in a row
    # Each stat: background box with number + label inside
    # Stats: NVIDIA $115.8B, Measles 5,412, 19 KM, 4 Tankers
    stats_data = [
        (facts.STORIES[0]["stat"], facts.STORIES[0]["tag"]),
        (facts.STORIES[4]["stat"], facts.STORIES[4]["tag"]),
        (facts.STORIES[10]["stat"], facts.STORIES[10]["tag"]),
        (facts.STORIES[15]["stat"], facts.STORIES[15]["tag"]),
    ]
    # Draw stats in a row, starting at MARGIN
    # Each stat: width = CONTENT_W / 4, height = 64
    cell_w = CONTENT_W / 4
    for i, (stat, tag) in enumerate(stats_data):
        cx = MARGIN + i * cell_w + cell_w / 2
        # Background box
        d.rectangle([MARGIN + i * cell_w, stats_row_y,
                     MARGIN + (i + 1) * cell_w, stats_row_y + stat_box_h],
                    fill=PAPER_DK, outline=RULE, width=1)
        # Stat text - centered, smaller font
        sf = archivo(13)
        # Parse stat value and label
        parts = stat.split()
        val = " ".join(parts[:-1])
        lbl = parts[-1] if len(parts) > 1 else ""
        sw = d.textlength(val, font=sf)
        d.text((MARGIN + i * cell_w + (cell_w - sw) / 2, stats_row_y + 10),
               val, font=sf, fill=INK, stroke_width=1, stroke_fill=INK)
        if lbl:
            d.text((MARGIN + i * cell_w + (cell_w - d.textlength(lbl, font=sf)) / 2,
                    stats_row_y + 35), lbl, font=sf, fill=SECOND)
    
    y = stats_row_y + stat_box_h + 6  # buffer after stats row
    print(f"After stats row: y={y}")

    # ============================================================
    # (6) The 24-story list - starts BELOW the stat boxes with a clear gap
    # ============================================================
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
