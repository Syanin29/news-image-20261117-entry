"""Ship the finished front page for news-image-20261117.

The artwork is ``entry.png`` in this repository, drawn at build
time by ``render.py`` from the verified 17 November 2026 facts.
This entrypoint does one job only: copy that file, byte for byte,
into the directory make.fun expects. Standard library only, no
network, no clock, no randomness, so two runs always write
identical bytes.

Run: mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
"""

import os
import sys

ARTWORK = "entry.png"
ARTWORK_NAME = "entry.png"
DEFAULT_OUT = "/output"

PNG_SIGNATURE = bytes(
    (0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A)
)
PNG_ENDING = (
    bytes((0, 0, 0, 0)) + b"IEND" + bytes((0xAE, 0x42, 0x60, 0x82))
)


def die(message):
    print("main.py: error: " + message, file=sys.stderr)
    raise SystemExit(1)


def in_repo(name):
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, name)


def read_artwork():
    path = in_repo(ARTWORK)
    if not os.path.isfile(path):
        die("source artwork %r not found" % path)
    with open(path, "rb") as handle:
        blob = handle.read()
    if not blob:
        die("source artwork %r is empty" % path)
    return path, blob


def verify_png(blob, label):
    """A whole PNG opens with its 8-byte signature and closes with
    the empty IEND chunk; anything else is truncated or corrupt."""
    minimum_len = len(PNG_SIGNATURE) + len(PNG_ENDING)
    if len(blob) < minimum_len:
        die(
            "%s is only %d bytes, too short to be a PNG"
            % (label, len(blob))
        )
    if blob[: len(PNG_SIGNATURE)] != PNG_SIGNATURE:
        die("%s does not start with the PNG signature" % label)
    if blob[-len(PNG_ENDING):] != PNG_ENDING:
        die("%s does not end with the PNG IEND chunk" % label)


def output_dir():
    raw = os.environ.get("MAKEFUN_OUTPUT_DIR", "")
    if raw.strip():
        return raw
    return DEFAULT_OUT


def copy_out(blob):
    dest_dir = output_dir()
    try:
        os.makedirs(dest_dir, exist_ok=True)
    except OSError as exc:
        die("cannot create output directory %r: %s" % (dest_dir, exc))
    dest = os.path.join(dest_dir, ARTWORK_NAME)
    try:
        with open(dest, "wb") as handle:
            handle.write(blob)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        die("cannot write %r: %s" % (dest, exc))
    with open(dest, "rb") as handle:
        written = handle.read()
    if written != blob:
        die(
            "copy incomplete: wrote %d bytes but source has %d"
            % (len(written), len(blob))
        )
    return dest


def main():
    src, blob = read_artwork()
    verify_png(blob, "source %r" % src)
    dest = copy_out(blob)
    with open(dest, "rb") as handle:
        verify_png(handle.read(), "output %r" % dest)
    print("wrote %s (%d bytes)" % (dest, len(blob)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
