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
BRIDGE = HERE / "assets" / "media-generation-hero-bridge-0-91b22b9f-23e9-474d-9300-cd0bf7276343.jpg"
TANKER = HERE / "assets" / "media-generation-hero-tanker-0-d42e7341-4bc3-447d-af70-fa67106b0509.jpg"

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
MARKERS = [
    (36.0, 45.0, "KERCH", 8, -14),
    (57.0, 26.0, "HORMUZ", 8, 8),
    (121.0, 14.0, "MANILA", 8, 8),
    (-77.0, 39.0, "WASHINGTON", -78, -14),
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
            d.ellipse([mx - 4, my - 4, mx + 4, my + 4], fill=marker,
                      outline=(255, 255, 255), width=1)
            tx = min(max(mx + ldx, x0), x0 + w - d.textlength(name, font=lf))
            d.text((tx, my + ldy), name, font=lf, fill=marker)


def paper_texture(img, seed=1234, speckles=2600):
    """Deterministic paper grain: faint speckles + a soft top light."""
    rng = random.Random(seed)
    img = img.convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")
    w, h = img.size
    for _ in range(speckles):
        x = rng.randrange(w)
        y = rng.randrange(h)
        a = rng.randrange(3, 7)
        if rng.random() < 0.5:
            d.point((x, y), fill=(120, 105, 80, a))
        else:
            d.point((x, y), fill=(255, 255, 255, a))
    # soft vignette: darker corners, lighter centre-top
    vig = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vig)
    vd.rectangle([0, 0, w, 26], fill=(255, 255, 255, 26))
    vd.rectangle([0, h - 26, w, h], fill=(90, 70, 40, 16))
    img.alpha_composite(vig)
    img = img.convert("RGB")
    return img


def wrap(d, text, fnt, max_w):
    words = text.split()
    lines, cur = [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if d.textlength(trial, font=fnt) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit_size(d, text, fnt_fn, max_w, start, floor):
    """Largest size in [floor, start] whose text fits max_w, else raise."""
    size = start
    while size > floor:
        fnt = fnt_fn(size)
        if d.textlength(text, font=fnt) <= max_w:
            return fnt
        size -= 1
    fnt = fnt_fn(floor)
    if d.textlength(text, font=fnt) > max_w:
        raise ValueError("text does not fit even at floor size: %r" % text)
    return fnt


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
    """2x2 grid of big numbers."""
    ink = D_PAPER if dark else INK
    second = D_SECOND if dark else SECOND
    cw, ch = w // 2, h // 2
    for i, (num, label) in enumerate(facts.BIG_STATS):
        cx = x + (i % 2) * cw
        cy = y + (i // 2) * ch
        d.rectangle([cx, cy, cx + cw - 8, cy + ch - 8],
                    outline=D_RULE if dark else RULE, width=1)
        nf = fit_size(d, num, archivo, cw - 24, 40, 20)
        d.text((cx + 12, cy + 8), num, font=nf, fill=RED, stroke_width=1,
               stroke_fill=RED)
        lf = inter(12)
        for j, line in enumerate(wrap(d, label, lf, cw - 24)):
            d.text((cx + 12, cy + 8 + nf.size + 2 + j * 15), line,
                   font=lf, fill=second)


def stat_row(d, x, y, w, h, dark=False):
    """Four big stats in one row."""
    ink = D_PAPER if dark else INK
    second = D_SECOND if dark else SECOND
    cw = w // 4
    for i, (num, label) in enumerate(facts.BIG_STATS):
        cx = x + i * cw
        d.rectangle([cx, y, cx + cw - 8, y + h], outline=D_RULE if dark else RULE,
                    width=1)
        nf = fit_size(d, num, archivo, cw - 24, 30, 18)
        d.text((cx + 10, y + 6), num, font=nf, fill=RED, stroke_width=1,
               stroke_fill=RED)
        lf = inter(11)
        for j, line in enumerate(wrap(d, label, lf, cw - 24)):
            d.text((cx + 10, y + 6 + nf.size + 2 + j * 14), line,
                   font=lf, fill=second)


# ---------------------------------------------------------------- variants

def v1_frontpage():
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    img = paper_texture(img)
    d = ImageDraw.Draw(img)
    y = masthead(d, 22)
    # hero: photo left, text right
    hy = y
    hh = 190
    ph = photo_cover(BRIDGE, 500, hh)
    img.paste(ph, (MARGIN, hy))
    d.rectangle([MARGIN, hy, MARGIN + 500, hy + hh], outline=INK, width=2)
    d.text((MARGIN + 8, hy + hh - 24), "AI ILLUSTRATION — KERCH BRIDGE",
           font=inter(11), fill=(255, 255, 255),
           stroke_width=2, stroke_fill=(0, 0, 0))
    hx = MARGIN + 516
    hw = W - MARGIN - hx
    d.text((hx, hy), "UKRAINE WAR  •  TOP STORY", font=archivo(15),
           fill=RED, stroke_width=1, stroke_fill=RED)
    hf = fit_size(d, "KERCH BRIDGE", archivo, hw, 40, 24)
    lines = wrap(d, facts.HERO["headline"], hf, hw)
    yy = hy + 26
    for line in lines:
        d.text((hx, yy), line, font=hf, fill=INK, stroke_width=1,
               stroke_fill=INK)
        yy += hf.size + 2
    deck_f = inter(16)
    for line in wrap(d, facts.HERO["deck"], deck_f, hw):
        d.text((hx, yy), line, font=deck_f, fill=SECOND)
        yy += 21
    yy += 4
    sf = archivo(15)
    d.text((hx, yy), facts.HERO["stat"], font=sf, fill=RED, stroke_width=1,
           stroke_fill=RED)
    y = hy + hh + 10
    # middle band: map left, big stats right
    band_h = 150
    d.text((MARGIN, y), "THE DAY IN 6 CONTINENTS", font=archivo(15),
           fill=INK, stroke_width=1, stroke_fill=INK)
    draw_map(d, MARGIN, y + 24, 470, band_h - 30)
    d.rectangle([MARGIN, y + 22, MARGIN + 470, y + band_h - 4],
                outline=RULE, width=1)
    big_stats(d, MARGIN + 486, y, CONTENT_W - 486, band_h)
    y += band_h + 10
    y = section_head(d, y, "THE REST OF THE DAY  —  23 MORE STORIES")
    gy = y
    half = (len(facts.STORIES) + 1) // 2
    col_w = (CONTENT_W - 24) // 2
    for i, s in enumerate(facts.STORIES[:half]):
        story_row(d, MARGIN, gy + i * 36, col_w, s, head_start=15,
                  deck_size=11, row_h=36)
    for i, s in enumerate(facts.STORIES[half:]):
        story_row(d, MARGIN + col_w + 24, gy + i * 36, col_w, s,
                  head_start=15, deck_size=11, row_h=36)
    y = gy + half * 36 + 6
    footer(d, y)
    return img


def v2_magazine():
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    img = paper_texture(img)
    d = ImageDraw.Draw(img)
    # full-bleed hero photo with masthead band overlaid at its foot
    ph = photo_cover(BRIDGE, W, 360)
    img.paste(ph, (0, 0))
    d = ImageDraw.Draw(img)
    band_y = 260
    d.rectangle([0, band_y, W, 360], fill=(20, 20, 20, 255))
    d.rectangle([0, band_y, W, band_y + 3], fill=RED)
    mf = fit_size(d, facts.MASTHEAD, playfair, CONTENT_W, 66, 40)
    d.text((W / 2, band_y + 6), facts.MASTHEAD, font=mf, fill=(251, 248, 241),
           anchor="ma", stroke_width=1, stroke_fill=(251, 248, 241))
    d.text((W / 2, band_y + 6 + mf.size + 12), facts.DATE_LINE,
           font=inter(17), fill=(255, 255, 255), anchor="ma")
    d.text((MARGIN + 6, 360 - 22), "AI ILLUSTRATION — KERCH BRIDGE",
           font=inter(11), fill=(255, 255, 255), stroke_width=2,
           stroke_fill=(0, 0, 0))
    y = 374
    d.text((MARGIN, y), facts.HERO["tag"] + "  •  TOP STORY",
           font=archivo(15), fill=RED, stroke_width=1, stroke_fill=RED)
    y += 24
    hf = fit_size(d, facts.HERO["headline"], archivo, CONTENT_W, 38, 24)
    for line in wrap(d, facts.HERO["headline"], hf, CONTENT_W):
        d.text((MARGIN, y), line, font=hf, fill=INK, stroke_width=1,
               stroke_fill=INK)
        y += hf.size + 2
    df = inter(16)
    for line in wrap(d, facts.HERO["deck"] + "  " + facts.HERO["stat"],
                     df, CONTENT_W):
        d.text((MARGIN, y), line, font=df, fill=SECOND)
        y += 21
    y += 8
    y = section_head(d, y, "23 MORE STORIES FROM THE DAY")
    gy = y
    third = (len(facts.STORIES) + 2) // 3
    col_w = (CONTENT_W - 2 * 20) // 3
    for c in range(3):
        chunk = facts.STORIES[c * third:(c + 1) * third]
        for i, s in enumerate(chunk):
            story_row(d, MARGIN + c * (col_w + 20), gy + i * 50, col_w, s,
                      narrow=True, row_h=50)
    y = gy + third * 50 + 12
    stat_row(d, MARGIN, y, CONTENT_W, 64)
    y += 64 + 10
    footer(d, y)
    return img


def v3_map():
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    img = paper_texture(img)
    d = ImageDraw.Draw(img)
    y = masthead(d, 22)
    # big map panel with numbered pins keyed to the story list
    map_h = 240
    d.text((MARGIN, y), "WHERE THE DAY HAPPENED  —  24 STORIES, 6 CONTINENTS",
           font=archivo(15), fill=INK, stroke_width=1, stroke_fill=INK)
    draw_map(d, MARGIN, y + 26, CONTENT_W, map_h - 26)
    d.rectangle([MARGIN, y + 24, W - MARGIN, y + map_h],
                outline=RULE, width=1)
    # numbered pins: first 8 stories get a number on the map by region
    pin_xy = {
        0: (36.0, 45.0), 1: (-77.0, 39.0), 2: (121.0, 14.0),
        3: (47.0, 26.0), 4: (57.0, 26.0), 5: (100.0, 60.0),
        6: (139.0, 37.0), 7: (35.0, 31.0),
    }
    nf = archivo(11)
    for idx, (lon, lat) in pin_xy.items():
        mx, my = lonlat_to_xy(lon, lat, MARGIN, y + 26, CONTENT_W,
                              map_h - 26)
        d.ellipse([mx - 8, my - 8, mx + 8, my + 8], fill=RED,
                  outline=(255, 255, 255), width=2)
        d.text((mx, my - 1), str(idx + 1), font=nf, fill=(255, 255, 255),
               anchor="mm", stroke_width=1, stroke_fill=(255, 255, 255))
    y += map_h + 10
    # hero banner
    d.rectangle([MARGIN, y, W - MARGIN, y + 60], fill=INK)
    d.text((MARGIN + 14, y + 7), "1  " + facts.HERO["headline"],
           font=archivo(23), fill=(251, 248, 241), stroke_width=1,
           stroke_fill=(251, 248, 241))
    d.text((MARGIN + 14, y + 36), facts.HERO["deck"], font=inter(13),
           fill=(200, 196, 186))
    y += 68
    y = section_head(d, y, "THE DAY, NUMBERED  —  STORIES 2–24")
    gy = y
    rest = facts.STORIES
    third = (len(rest) + 2) // 3
    col_w = (CONTENT_W - 2 * 20) // 3
    for c in range(3):
        chunk = rest[c * third:(c + 1) * third]
        for i, s in enumerate(chunk):
            story_row(d, MARGIN + c * (col_w + 20), gy + i * 50, col_w, s,
                      narrow=True, row_h=50)
    y = gy + third * 50 + 12
    stat_row(d, MARGIN, y, CONTENT_W, 64)
    y += 64 + 10
    footer(d, y)
    return img


def v4_dark():
    img = Image.new("RGB", (W, H), D_BG)
    d = ImageDraw.Draw(img)
    y = masthead(d, 22, dark=True)
    hy = y
    hh = 190
    # hero: text left, photo right (mirrored v1)
    hx = MARGIN
    hw = W - MARGIN - 516 - MARGIN
    d.text((hx, hy), "UKRAINE WAR  •  TOP STORY", font=archivo(15),
           fill=(255, 120, 120), stroke_width=1, stroke_fill=(255, 120, 120))
    hf = fit_size(d, "KERCH BRIDGE", archivo, hw, 40, 24)
    yy = hy + 26
    for line in wrap(d, facts.HERO["headline"], hf, hw):
        d.text((hx, yy), line, font=hf, fill=D_PAPER, stroke_width=1,
               stroke_fill=D_PAPER)
        yy += hf.size + 2
    deck_f = inter(16)
    for line in wrap(d, facts.HERO["deck"], deck_f, hw):
        d.text((hx, yy), line, font=deck_f, fill=D_SECOND)
        yy += 21
    yy += 4
    d.text((hx, yy), facts.HERO["stat"], font=archivo(15),
           fill=(255, 120, 120), stroke_width=1, stroke_fill=(255, 120, 120))
    px = W - MARGIN - 500
    ph = photo_cover(BRIDGE, 500, hh)
    img.paste(ph, (px, hy))
    d.rectangle([px, hy, px + 500, hy + hh], outline=D_RULE, width=2)
    d.text((px + 8, hy + hh - 24), "AI ILLUSTRATION — KERCH BRIDGE",
           font=inter(11), fill=(255, 255, 255), stroke_width=2,
           stroke_fill=(0, 0, 0))
    y = hy + hh + 10
    band_h = 150
    d.text((MARGIN, y), "THE DAY IN 6 CONTINENTS", font=archivo(15),
           fill=D_PAPER, stroke_width=1, stroke_fill=D_PAPER)
    draw_map(d, MARGIN, y + 24, 470, band_h - 30, dot=(120, 160, 200),
             marker=(255, 120, 120))
    d.rectangle([MARGIN, y + 22, MARGIN + 470, y + band_h - 4],
                outline=D_RULE, width=1)
    big_stats(d, MARGIN + 486, y, CONTENT_W - 486, band_h, dark=True)
    y += band_h + 10
    y = section_head(d, y, "THE REST OF THE DAY  —  23 MORE STORIES",
                     dark=True)
    gy = y
    half = (len(facts.STORIES) + 1) // 2
    col_w = (CONTENT_W - 24) // 2
    for i, s in enumerate(facts.STORIES[:half]):
        story_row(d, MARGIN, gy + i * 36, col_w, s, dark=True,
                  head_start=15, deck_size=11, row_h=36)
    for i, s in enumerate(facts.STORIES[half:]):
        story_row(d, MARGIN + col_w + 24, gy + i * 36, col_w, s, dark=True,
                  head_start=15, deck_size=11, row_h=36)
    y = gy + half * 36 + 6
    footer(d, y, dark=True)
    return img


def v5_timeline():
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    img = paper_texture(img)
    d = ImageDraw.Draw(img)
    y = masthead(d, 22)
    # left: numbered timeline of all 24 stories; right: photo + stats
    right_x = MARGIN + 560
    right_w = W - MARGIN - right_x
    ph = photo_cover(BRIDGE, right_w, 300)
    img.paste(ph, (right_x, y))
    d.rectangle([right_x, y, right_x + right_w, y + 300], outline=INK,
                width=2)
    d.text((right_x + 8, y + 300 - 24), "AI ILLUSTRATION — KERCH BRIDGE",
           font=inter(11), fill=(255, 255, 255), stroke_width=2,
           stroke_fill=(0, 0, 0))
    sy = y + 312
    big_stats(d, right_x, sy, right_w, 300)
    # timeline rows
    ty = y
    d.text((MARGIN, ty), "THE DAY, HOUR BY HOUR — IN ORDER OF IMPACT",
           font=archivo(15), fill=INK, stroke_width=1, stroke_fill=INK)
    ty += 28
    all_stories = [{"tag": "UKRAINE WAR", "headline": facts.HERO["headline"],
                    "deck": facts.HERO["deck"], "stat": "19 KM"}] + \
        facts.STORIES
    d.line([(MARGIN + 12, ty + 6), (MARGIN + 12, ty + 24 * 31)],
           fill=RULE, width=2)
    for i, s in enumerate(all_stories):
        ry = ty + i * 31
        d.ellipse([MARGIN + 4, ry, MARGIN + 20, ry + 16], fill=RED)
        d.text((MARGIN + 12, ry + 1), str(i + 1), font=archivo(10),
               fill=(255, 255, 255), anchor="mm")
        hf = fit_size(d, s["headline"], archivo, 500 - 40, 14, 11)
        d.text((MARGIN + 30, ry), s["headline"], font=hf, fill=INK,
               stroke_width=1, stroke_fill=INK)
        sw = d.textlength(s["stat"], font=archivo(12))
        d.text((MARGIN + 500 - sw, ry + 1), s["stat"], font=archivo(12),
               fill=RED)
    y = ty + 24 * 31 + 10
    footer(d, y)
    return img


def v6_cards():
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    img = paper_texture(img)
    d = ImageDraw.Draw(img)
    y = masthead(d, 22)
    # 6 big cards (2 rows x 3 cols); card 1 = hero photo, card 5 = tanker
    cards = [
        {"photo": BRIDGE, "tag": "UKRAINE WAR",
         "headline": facts.HERO["headline"], "deck": facts.HERO["deck"],
         "stat": facts.HERO["stat"]},
        {"photo": None, "tag": facts.STORIES[0]["tag"],
         "headline": facts.STORIES[0]["headline"],
         "deck": facts.STORIES[0]["deck"], "stat": facts.STORIES[0]["stat"]},
        {"photo": None, "tag": facts.STORIES[1]["tag"],
         "headline": facts.STORIES[1]["headline"],
         "deck": facts.STORIES[1]["deck"], "stat": facts.STORIES[1]["stat"]},
        {"photo": None, "tag": facts.STORIES[2]["tag"],
         "headline": facts.STORIES[2]["headline"],
         "deck": facts.STORIES[2]["deck"], "stat": facts.STORIES[2]["stat"]},
        {"photo": TANKER, "tag": facts.STORIES[4]["tag"],
         "headline": facts.STORIES[4]["headline"],
         "deck": facts.STORIES[4]["deck"], "stat": facts.STORIES[4]["stat"]},
        {"photo": None, "tag": facts.STORIES[3]["tag"],
         "headline": facts.STORIES[3]["headline"],
         "deck": facts.STORIES[3]["deck"], "stat": facts.STORIES[3]["stat"]},
    ]
    cw = (CONTENT_W - 2 * 16) // 3
    ch = 226
    for i, c in enumerate(cards):
        cx = MARGIN + (i % 3) * (cw + 16)
        cy = y + (i // 3) * (ch + 16)
        d.rectangle([cx, cy, cx + cw, cy + ch], outline=RULE, width=1)
        if c["photo"]:
            ph = photo_cover(c["photo"], cw, 100)
            img.paste(ph, (cx, cy))
            d.rectangle([cx, cy, cx + cw, cy + 100], outline=INK, width=1)
            ty = cy + 108
        else:
            d.rectangle([cx, cy, cx + cw, cy + 6], fill=RED)
            ty = cy + 14
        d.text((cx + 10, ty), c["tag"], font=archivo(12), fill=RED,
               stroke_width=1, stroke_fill=RED)
        hf = fit_size(d, c["headline"], archivo, cw - 20, 19, 13)
        yy = ty + 18
        for line in wrap(d, c["headline"], hf, cw - 20):
            d.text((cx + 10, yy), line, font=hf, fill=INK, stroke_width=1,
                   stroke_fill=INK)
            yy += hf.size + 1
        df = inter(12)
        for line in wrap(d, c["deck"], df, cw - 20):
            d.text((cx + 10, yy), line, font=df, fill=SECOND)
            yy += 15
        d.text((cx + 10, cy + ch - 22), c["stat"], font=archivo(14),
               fill=RED, stroke_width=1, stroke_fill=RED)
    y += 2 * ch + 16 + 8
    y = section_head(d, y, "18 MORE STORIES  —  THE REST OF THE DAY")
    gy = y
    rest = facts.STORIES[5:]
    half = (len(rest) + 1) // 2
    col_w = (CONTENT_W - 24) // 2
    for i, s in enumerate(rest[:half]):
        story_row(d, MARGIN, gy + i * 36, col_w, s, head_start=15,
                  deck_size=11, row_h=36)
    for i, s in enumerate(rest[half:]):
        story_row(d, MARGIN + col_w + 24, gy + i * 36, col_w, s,
                  head_start=15, deck_size=11, row_h=36)
    y = gy + half * 36 + 2
    footer(d, y)
    return img


VARIANTS = {
    "v1": ("frontpage", v1_frontpage),
    "v2": ("magazine", v2_magazine),
    "v3": ("map", v3_map),
    "v4": ("dark", v4_dark),
    "v5": ("timeline", v5_timeline),
    "v6": ("cards", v6_cards),
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
