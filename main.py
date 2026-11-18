"""Entry runner for the news-image-20261117 bounty.

The artwork is pre-rendered at build time and stored in this repo as
``entry.png``.  This script only ships that file, byte for byte, to the
directory make.fun expects.  Nothing here draws, downloads, or invents
anything: standard library only, no network, no clock, no randomness,
so running it twice always produces the identical output file.
"""

import os
import sys

# Where the finished artwork lives in this repo.
SOURCE_NAME = "entry.png"

# Where the copy has to land.
DEST_NAME = "entry.png"

# Fallback output folder when MAKEFUN_OUTPUT_DIR is not set.
DEFAULT_OUT_DIR = "/output"

# First eight bytes of every valid PNG file.
PNG_MAGIC = bytes((0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A))

# The final twelve bytes of a complete PNG: an empty IEND chunk
# (4-byte length 0, the letters "IEND", and its CRC 0xAE426082).
PNG_TAIL = bytes((0, 0, 0, 0)) + b"IEND" + bytes((0xAE, 0x42, 0x60, 0x82))


def _die(message):
    """Print an error to stderr and exit non-zero."""
    print("main.py: error: " + message, file=sys.stderr)
    raise SystemExit(1)


def _read_source():
    """Load the artwork next to this script; refuse a missing file."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, SOURCE_NAME)
    if not os.path.isfile(path):
        _die("source artwork %r not found" % path)
    with open(path, "rb") as handle:
        blob = handle.read()
    if not blob:
        _die("source artwork %r is empty" % path)
    return path, blob


def _check_png(blob, label):
    """Reject data that is not a complete PNG file.

    A PNG must open with the 8-byte signature and close with the IEND
    chunk; anything shorter than the two markers combined, or missing
    either one, is a truncated or corrupted file.
    """
    if len(blob) < len(PNG_MAGIC) + len(PNG_TAIL):
        _die("%s is only %d bytes, too short to be a PNG" % (label, len(blob)))
    if blob[: len(PNG_MAGIC)] != PNG_MAGIC:
        _die("%s does not start with the PNG signature" % label)
    if blob[-len(PNG_TAIL):] != PNG_TAIL:
        _die("%s does not end with the PNG IEND chunk" % label)


def _target_dir():
    """Resolve the output directory, defaulting to /output."""
    raw = os.environ.get("MAKEFUN_OUTPUT_DIR", "")
    if raw.strip():
        return raw
    return DEFAULT_OUT_DIR


def main():
    src_path, blob = _read_source()
    _check_png(blob, "source %r" % src_path)

    out_dir = _target_dir()
    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError as exc:
        _die("cannot create output directory %r: %s" % (out_dir, exc))

    dest_path = os.path.join(out_dir, DEST_NAME)
    try:
        with open(dest_path, "wb") as handle:
            handle.write(blob)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        _die("cannot write %r: %s" % (dest_path, exc))

    with open(dest_path, "rb") as handle:
        written = handle.read()
    if written != blob:
        _die(
            "copy incomplete: wrote %d bytes but source has %d"
            % (len(written), len(blob))
        )
    _check_png(written, "output %r" % dest_path)

    print("wrote %s (%d bytes)" % (dest_path, len(blob)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
