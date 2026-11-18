"""Ship the pre-rendered front page for news-image-20261117.

Rebuilt 2026-11-18 in the fresh rebuild session. The artwork lives in
this repository as ``entry.png`` (drawn at build time by ``render.py``
from verified 17 November 2026 facts); this entrypoint only copies it,
byte for byte, to the directory make.fun expects. Standard library
only: no network, no clock, no randomness, so two runs always write
identical bytes.

Run: mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
"""

import os
import sys

SOURCE = "entry.png"
TARGET = "entry.png"
FALLBACK_DIR = "/output"

PNG_HEAD = bytes((0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A))
PNG_TAIL = bytes((0, 0, 0, 0)) + b"IEND" + bytes((0xAE, 0x42, 0x60, 0x82))


def fail(msg):
    print("main.py: error: " + msg, file=sys.stderr)
    raise SystemExit(1)


def repo_path(name):
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, name)


def load_artwork():
    path = repo_path(SOURCE)
    if not os.path.isfile(path):
        fail("source artwork %r not found" % path)
    with open(path, "rb") as fh:
        blob = fh.read()
    if not blob:
        fail("source artwork %r is empty" % path)
    return path, blob


def check_png(blob, label):
    """A whole PNG opens with the 8-byte signature and closes with
    the empty IEND chunk; anything else is truncated or corrupt."""
    shortest = len(PNG_HEAD) + len(PNG_TAIL)
    if len(blob) < shortest:
        fail("%s is only %d bytes, too short to be a PNG"
             % (label, len(blob)))
    if blob[:len(PNG_HEAD)] != PNG_HEAD:
        fail("%s does not start with the PNG signature" % label)
    if blob[-len(PNG_TAIL):] != PNG_TAIL:
        fail("%s does not end with the PNG IEND chunk" % label)


def out_dir():
    raw = os.environ.get("MAKEFUN_OUTPUT_DIR", "")
    return raw if raw.strip() else FALLBACK_DIR


def ship(blob):
    dest_dir = out_dir()
    try:
        os.makedirs(dest_dir, exist_ok=True)
    except OSError as exc:
        fail("cannot create output directory %r: %s" % (dest_dir, exc))
    dest = os.path.join(dest_dir, TARGET)
    try:
        with open(dest, "wb") as fh:
            fh.write(blob)
            fh.flush()
            os.fsync(fh.fileno())
    except OSError as exc:
        fail("cannot write %r: %s" % (dest, exc))
    with open(dest, "rb") as fh:
        written = fh.read()
    if written != blob:
        fail("copy incomplete: wrote %d bytes but source has %d"
             % (len(written), len(blob)))
    return dest


def main():
    src, blob = load_artwork()
    check_png(blob, "source %r" % src)
    dest = ship(blob)
    check_png(open(dest, "rb").read(), "output %r" % dest)
    print("wrote %s (%d bytes)" % (dest, len(blob)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
