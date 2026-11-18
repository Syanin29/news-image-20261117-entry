"""Ship the finished front page for news-image-20261117.

The artwork is ``entry.png`` in this repository, drawn at build
time by ``render.py`` from the verified 17 November 2026 facts.
This entrypoint does one job only: copy that file, byte for byte,
into the directory make.fun expects. It runs on the standard
library alone — no network, no clock, no randomness — so two runs
always write identical bytes.

Run: mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
"""

import os
import sys
from pathlib import Path

ARTWORK = "entry.png"
DEFAULT_OUT = "/output"

PNG_SIGNATURE = bytes((0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A))
PNG_ENDING = bytes((0, 0, 0, 0)) + b"IEND" + bytes((0xAE, 0x42, 0x60, 0x82))


class ShipError(Exception):
    """The artwork could not be read, checked or delivered."""


def _source_bytes():
    path = Path(__file__).resolve().parent / ARTWORK
    try:
        blob = path.read_bytes()
    except OSError:
        raise ShipError("source artwork %r not found" % str(path))
    if not blob:
        raise ShipError("source artwork %r is empty" % str(path))
    return path, blob


def _check_png(blob, label):
    """A whole PNG opens with its 8-byte signature and closes
    with the empty IEND chunk; anything else is truncated or
    corrupt."""
    leading = blob[: len(PNG_SIGNATURE)]
    trailing = blob[-len(PNG_ENDING):]
    if len(blob) < len(PNG_SIGNATURE) + len(PNG_ENDING):
        raise ShipError(
            "%s is only %d bytes, too short to be a PNG"
            % (label, len(blob))
        )
    if leading != PNG_SIGNATURE:
        raise ShipError("%s does not start with the PNG signature" % label)
    if trailing != PNG_ENDING:
        raise ShipError("%s does not end with the PNG IEND chunk" % label)


def _destination():
    raw = os.environ.get("MAKEFUN_OUTPUT_DIR", "")
    if raw.strip():
        return Path(raw)
    return Path(DEFAULT_OUT)


def _deliver(blob):
    dest_dir = _destination()
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ShipError(
            "cannot create output directory %r: %s" % (str(dest_dir), exc)
        )
    dest = dest_dir / ARTWORK
    try:
        dest.write_bytes(blob)
    except OSError as exc:
        raise ShipError("cannot write %r: %s" % (str(dest), exc))
    written = dest.read_bytes()
    if written != blob:
        raise ShipError(
            "copy incomplete: wrote %d bytes but source has %d"
            % (len(written), len(blob))
        )
    return dest


def main():
    try:
        src, blob = _source_bytes()
        _check_png(blob, "source %r" % str(src))
        dest = _deliver(blob)
        _check_png(dest.read_bytes(), "output %r" % str(dest))
    except ShipError as exc:
        print("main.py: error: " + str(exc), file=sys.stderr)
        return 1
    print("wrote %s (%d bytes)" % (dest, len(blob)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
