#!/usr/bin/env python3
"""Write the news-image-20261117 entry image to the output directory.

The entry image lives in this repository as entry.png: a one-page
newspaper front page ("WORLD NEWS", Tuesday 17 November 2026) that sums
up the day's world news in 20+ verified stories, a world map, and big
stat callouts. It was rendered at build time by render.py (Pillow +
bundled fonts) from verified facts only -- no model call, no network.

The program copies entry.png to $MAKEFUN_OUTPUT_DIR/entry.png
(falling back to /output/entry.png), byte for byte, so two runs on
the same repository write identical bytes. Standard library only; no
network, no randomness, no timestamps in the output.
"""

import os
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "entry.png"

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _check_png(path):
    """Refuse a truncated file: a whole PNG starts with its signature
    and ends with the 12-byte IEND chunk."""
    data = path.read_bytes()
    if data[:8] != PNG_SIGNATURE or data[-8:-4] != b"IEND":
        raise SystemExit("not a whole PNG: bad signature or missing IEND")


def main():
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / "entry.png"
    shutil.copyfile(SRC, dst)
    # Fail loudly instead of silently shipping a truncated copy.
    if dst.stat().st_size != SRC.stat().st_size:
        raise SystemExit("copy incomplete: output size differs from entry.png")
    _check_png(dst)


if __name__ == "__main__":
    main()
