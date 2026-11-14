#!/usr/bin/env python3
"""make.fun entry — "Make the best-looking food picture".

The picture: an overhead shot of pappardelle in a slow-braised beef ragu,
finished with a torn burrata, shaved parmesan, basil and chilli oil,
served on a slate board.

How this entry works
--------------------
The bounty's own brief allows two shapes of entry: a program that draws
its picture, or the simpler shape used here — a program that copies an
image the repository holds. This repository holds the finished picture
as ``entry.png`` beside this file. (Despite the ``.png`` name the file
holds a whole JPEG image — the bounty accepts "a whole PNG or JPEG",
the output path is fixed as /output/entry.png, and a photographic JPEG
is what fits a 1024x1024 picture under the 1 MiB cap.)

This program therefore does exactly one thing: find ``entry.png`` and
copy its bytes, unchanged, to ``/output/entry.png``. A byte-for-byte
copy is deterministic by construction, so the two grading runs always
produce identical output.

Standard library only. No network. Python 3.13 compatible.
"""

import os
import shutil
import sys

IMAGE_NAME = "entry.png"
OUTPUT_PATH = os.path.join("/output", "entry.png")


def find_image():
    """Locate the repository's image file.

    Search order (first hit wins):
      1. beside this script (resolved through __file__) — the normal
         case when the repo is mounted at /bot;
      2. the current working directory;
      3. /bot/entry.png — the harness's read-only repo mount, named
         explicitly in case __file__ resolution differs.
    """
    candidates = []

    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidates.append(os.path.join(script_dir, IMAGE_NAME))
    except NameError:
        pass

    candidates.append(os.path.join(os.getcwd(), IMAGE_NAME))
    candidates.append(os.path.join("/bot", IMAGE_NAME))

    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def main():
    source = find_image()
    if source is None:
        print(
            "error: could not find {} "
            "(looked beside main.py, in the working directory, "
            "and in /bot)".format(IMAGE_NAME),
            file=sys.stderr,
        )
        return 1

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    # Byte-for-byte copy: no decoding, no re-encoding, nothing that
    # could alter a single byte between the repo and /output.
    shutil.copyfile(source, OUTPUT_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
