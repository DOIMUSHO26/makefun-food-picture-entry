# Make the Best-Looking Food Picture — Entry

A single-file Python program that draws a state-of-the-art fine-dining
pasta plate, seen from directly overhead: a tall tong-twirled nest of
fresh golden tagliatelle with deep tomato sauce (pooled under the nest,
worked through the strands, and finished with a spoon-drag smear), two
small side twirls, halved roasted cherry tomatoes, basil leaves, shaved
parmesan, cracked pepper and an olive-oil sheen, served on an ivory
stoneware plate over a dark wooden table, with a fork resting at the rim.

Everything is drawn procedurally with the **Python standard library
only** — an in-memory framebuffer, seeded value noise, hand-built shape
and shading routines, and a zlib-compressed PNG encoder. No PIL, no
numpy, no network, no image assets.

## Run

```sh
python3 main.py
```

Writes the picture to `/output/entry.png` (the directory is created if
needed).

## Properties

- Output: 1024 × 1024 PNG, well under the 1 MiB limit (~366 KB).
- Fully deterministic: every random source uses a fixed seed, so two
  runs produce byte-identical files (verified by SHA-256).
- Runtime: roughly 15 seconds on a modest machine; no network access
  required or used.

`preview.png` in this folder is a copy of the final rendered entry.

## License

MIT — see `LICENSE`.
