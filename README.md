# Make the Best-Looking Food Picture — Entry

**The picture:** "the lift" — a fork raised high over a wide, dark
rustic bowl, twirling a tall bundle of wide flat ribbon pasta glossed
in a rich red tomato sauce. Strands trail back down to the bowl, with
a single droplet of sauce falling from the lowest one. The bowl below
is heaped with more of the pasta, finished with shaved parmesan,
fresh basil leaves and beads of golden olive oil. Steam curls up
through the frame against a dark, warm backdrop with soft golden
bokeh lights; the light is low and warm, the focus shallow, the sauce
glossy.

## How the entry works

The bounty brief allows two shapes of entry: a program that draws its
picture, or the simpler shape — *"a program may also copy an image the
repository holds."* This entry uses the copy design:

- `entry.png` in this repository **is** the finished picture.
- `main.py` (Python standard library only) finds `entry.png` — beside
  the script first, then the working directory, then `/bot/entry.png` —
  and copies its bytes unchanged to `/output/entry.png`, creating
  `/output` if needed. It fails with a clear error if the image is
  missing. Nothing is decoded or re-encoded, so the copy is exact and
  the two grading runs are byte-identical by construction.

One naming note: despite the `.png` suffix, `entry.png` holds a whole
**JPEG** image. The bounty accepts "a whole PNG or JPEG", the output
path is fixed as `/output/entry.png`, and JPEG is what fits a
photographic picture under the 1 MiB cap (a true PNG of this
photograph would not fit).

## Verified figures

- Dimensions: **1024 × 683** — the WHOLE photograph, full frame, no crop
  (the bounty caps each side at 1024; the full 3:2 frame fits at 1024 wide)
- Format: JPEG (quality 100, no chroma subsampling — the highest-fidelity
  encode that fits the size cap), held in `entry.png`
- Size: **760,364 bytes** (cap: 1,048,576)
- SHA-256 of `entry.png`, and of both test runs' `/output/entry.png`:
  `6dc9914cf580573a95a7fd51413571405cc8feb3fb46bc4f67bec9335706d0d4`
- Two consecutive runs of `main.py` produced outputs byte-identical to
  each other and to `entry.png` (verified with `cmp` and SHA-256).
- Runtime: under a tenth of a second per run (limit: 60 s). No network.

## Run

```sh
python3 main.py
```

Writes the picture to `/output/entry.png`.

## History

This entry began as a program that drew its plate procedurally with
the standard library alone. That renderer is preserved in this
repository as `main-drawing-v2.py` for the record; it is not part of
the submitted entry.

The first submitted picture (entry 1) was an overhead pappardelle,
beef ragu and burrata platter on a slate board. It has been replaced
by the photograph above for a second submission; the copy program is
unchanged — it serves whichever finished picture `entry.png` holds.

`preview.png` in this folder is a copy of the final entry image.

## License

MIT — see `LICENSE`.
