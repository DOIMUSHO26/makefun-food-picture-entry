# Make the Best-Looking Food Picture — Entry

**The picture:** a deep, dark rustic ceramic bowl of wide pappardelle
ribbons in a slow-braised beef ragù, photographed at a three-quarter
angle on a dark wooden table. Resting on the pasta at the top right
is ONE whole burrata ball — intact, smooth, closed and glossy, its
surface clean — dressed with a small basil sprig on top and a small
cluster of thin curled butter shavings at its base. Shaved parmesan,
fresh basil leaves and droplets of chilli oil finish the dish, steam
rises through the frame, and a polished gold fork rests in the bowl
at the right, its handle on the rim. The light is low and warm, the
focus shallow, the sauce rich and glossy.

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
- Size: **950,042 bytes** (cap: 1,048,576)
- SHA-256 of `entry.png`, and of both test runs' `/output/entry.png`:
  `d909016fd49505657e42f706866aae2b2a0f11737bb6beefaf6dbb52fb03a5eb`
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
beef ragu and burrata platter on a slate board. It was replaced by a
second photograph (entry 2, "the lift" — a fork twirling ribbon pasta
in tomato sauce above a dark bowl), then by a third (entry 3 — the
same bowl as above, with a plain whole burrata), then by a fourth
(entry 4 — the dressed burrata with oil drops and a rolled butter
curl), which has in turn been replaced by the photograph above. The
copy program is unchanged throughout — it serves whichever finished
picture `entry.png` holds.

`preview.png` in this folder is a copy of the final entry image.

## License

MIT — see `LICENSE`.
