#!/usr/bin/env python3
"""
Make the best-looking food picture -- make.fun bounty entry.

Renders a state-of-the-art fine-dining pasta plate, top-down, with a
photographic finish: a tall twirled nest of fresh golden tagliatelle
with deep tomato sauce on an ivory stoneware plate, over a dark wooden
table. Pure Python standard library: an in-memory RGB framebuffer,
seeded multi-scale value noise, per-strand cylindrical shading, soft
contact shadows and ambient occlusion, and a zlib-compressed PNG
written to /output/entry.png.

Deterministic: every random source uses a fixed seed. No time, no
network, no environment-dependent values reach the image.
"""

import math
import os
import random
import struct
import zlib

W = H = 1024
OUT_PATH = "/output/entry.png"

# light direction (toward the light), 3D: from upper-left, fairly high
_LN = math.sqrt(0.50 * 0.50 + 0.62 * 0.62 + 0.60 * 0.60)
L3X, L3Y, L3Z = -0.50 / _LN, -0.62 / _LN, 0.60 / _LN

# ---------------------------------------------------------------- framebuffer
FB = [bytearray(W * 3) for _ in range(H)]


def clamp255(v):
    v = int(v)
    return 0 if v < 0 else (255 if v > 255 else v)


def put(x, y, r, g, b):
    if 0 <= x < W and 0 <= y < H:
        row = FB[y]
        i = x * 3
        row[i] = r
        row[i + 1] = g
        row[i + 2] = b


def blend(x, y, r, g, b, a):
    if a <= 0.0:
        return
    if 0 <= x < W and 0 <= y < H:
        row = FB[y]
        i = x * 3
        if a >= 1.0:
            row[i] = r
            row[i + 1] = g
            row[i + 2] = b
        else:
            ia = 1.0 - a
            row[i] = int(row[i] * ia + r * a)
            row[i + 1] = int(row[i + 1] * ia + g * a)
            row[i + 2] = int(row[i + 2] * ia + b * a)


def getpx(x, y):
    row = FB[y]
    i = x * 3
    return row[i], row[i + 1], row[i + 2]


def mix(c1, c2, t):
    return (c1[0] + (c2[0] - c1[0]) * t,
            c1[1] + (c2[1] - c1[1]) * t,
            c1[2] + (c2[2] - c1[2]) * t)


# ---------------------------------------------------------------- seeded noise
def make_grid(n, seed):
    rng = random.Random(seed)
    return [[rng.random() for _ in range(n)] for _ in range(n)]


def noise2(grid, n, x, y):
    xi = int(math.floor(x))
    yi = int(math.floor(y))
    xf = x - xi
    yf = y - yi
    u = xf * xf * (3.0 - 2.0 * xf)
    v = yf * yf * (3.0 - 2.0 * yf)
    x0 = xi % n
    y0 = yi % n
    x1 = (xi + 1) % n
    y1 = (yi + 1) % n
    top = grid[y0][x0] + (grid[y0][x1] - grid[y0][x0]) * u
    bot = grid[y1][x0] + (grid[y1][x1] - grid[y1][x0]) * u
    return top + (bot - top) * v


G16 = make_grid(16, 101)
G32 = make_grid(32, 202)
G64 = make_grid(64, 303)
G128 = make_grid(128, 404)
G256 = make_grid(256, 505)


def fbm(x, y):
    """Multi-scale value noise in ~0..1, features from ~128px to ~10px."""
    return (0.44 * noise2(G16, 16, x / 128.0, y / 128.0)
            + 0.29 * noise2(G32, 32, x / 48.0, y / 48.0)
            + 0.19 * noise2(G64, 64, x / 20.0, y / 20.0)
            + 0.08 * noise2(G128, 128, x / 9.5, y / 9.5))


# ---------------------------------------------------------------- primitives
def disc(cx, cy, r, color, alpha=1.0):
    r2 = r * r
    for y in range(int(cy - r - 1), int(cy + r + 2)):
        dy = y - cy
        rem = r2 - dy * dy
        if rem < 0:
            continue
        for x in range(int(cx - r - 1), int(cx + r + 2)):
            dx = x - cx
            if dx * dx <= rem:
                if alpha >= 1.0:
                    put(x, y, color[0], color[1], color[2])
                else:
                    blend(x, y, color[0], color[1], color[2], alpha)


def radial_disc(cx, cy, r, c_in, c_out, light_amt=0.16, power=1.0, squash=1.0):
    ry = r * squash
    for y in range(int(cy - ry - 1), int(cy + ry + 2)):
        dy = y - cy
        for x in range(int(cx - r - 1), int(cx + r + 2)):
            dx = x - cx
            q = (dx / r) ** 2 + (dy / ry) ** 2
            if q > 1.0:
                continue
            t = math.sqrt(q) ** power
            cr, cg, cb = mix(c_in, c_out, t)
            li = 1.0 + light_amt * ((dx * L3X + dy * L3Y) / r)
            put(x, y, clamp255(cr * li), clamp255(cg * li), clamp255(cb * li))


def soft_disc(cx, cy, r, color, alpha):
    """Disc with a smooth alpha falloff -- for shadows, glows, AO."""
    for y in range(int(cy - r - 1), int(cy + r + 2)):
        dy = (y - cy) / r
        for x in range(int(cx - r - 1), int(cx + r + 2)):
            dx = (x - cx) / r
            d2 = dx * dx + dy * dy
            if d2 < 1.0:
                a = alpha * (1.0 - d2) ** 1.5
                if a > 0.004:
                    blend(x, y, color[0], color[1], color[2], a)


def soft_shadow(cx, cy, r, strength=0.55, squash=0.92):
    ry = r * squash
    for y in range(int(cy - ry - 1), int(cy + ry + 2)):
        dy = (y - cy) / ry
        for x in range(int(cx - r - 1), int(cx + r + 2)):
            dx = (x - cx) / r
            d2 = dx * dx + dy * dy
            if d2 < 1.0:
                blend(x, y, 0, 0, 0, strength * (1.0 - d2) ** 1.6)


def soft_light(cx, cy, r, strength, squash=1.0):
    soft_disc(cx, cy, r, (255, 250, 238), strength)


def stamp_path(pts, width, color, alpha=1.0):
    r = width * 0.5
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        seg = math.hypot(x1 - x0, y1 - y0)
        steps = max(1, int(seg / max(1.2, r * 0.45)))
        for s in range(steps + 1):
            t = s / steps
            disc(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, r, color, alpha)


def stamp_soft_path(pts, width, color, alpha):
    r = width * 0.5
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        seg = math.hypot(x1 - x0, y1 - y0)
        steps = max(1, int(seg / max(1.2, r * 0.5)))
        for s in range(steps + 1):
            t = s / steps
            soft_disc(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, r, color, alpha)


def arc_pts(cx, cy, r, a0, a1, n=48, squash=1.0):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n),
             cy + r * squash * math.sin(a0 + (a1 - a0) * i / n))
            for i in range(n + 1)]


def resample(pts, step):
    """Walk a polyline, returning points ~step apart (plus the ends)."""
    out = [pts[0]]
    acc = 0.0
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        seg = math.hypot(x1 - x0, y1 - y0)
        if seg == 0:
            continue
        s = step - acc
        while s < seg:
            t = s / seg
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
            s += step
        acc = (acc + seg) % step
    out.append(pts[-1])
    return out


# ------------------------------------------------- lit sphere stamp (for strands)
def shade_stamp(cx, cy, r, col, tone=1.0, alpha=0.94, spec_amt=0.55):
    """A stamp lit like a small sphere/cylinder cap: diffuse wrap toward
    the light, a tight specular near the lit ridge, soft rim falloff."""
    inv = 1.0 / r
    for y in range(int(cy - r - 1), int(cy + r + 2)):
        dy = (y - cy) * inv
        for x in range(int(cx - r - 1), int(cx + r + 2)):
            dx = (x - cx) * inv
            q = dx * dx + dy * dy
            if q >= 1.0:
                continue
            nz = math.sqrt(1.0 - q)
            dif = dx * L3X + dy * L3Y + nz * L3Z
            if dif < 0.0:
                dif = 0.0
            li = (0.30 + 0.88 * dif) * tone
            d2 = dif * dif
            sp = spec_amt * d2 * d2 * d2 * d2 * dif  # dif^9
            ef = (1.0 - q) * 3.0
            a = alpha if ef >= 1.0 else alpha * ef
            blend(x, y,
                  clamp255(col[0] * li + 238.0 * sp),
                  clamp255(col[1] * li + 232.0 * sp),
                  clamp255(col[2] * li + 205.0 * sp), a)


# ---------------------------------------------------------------- layout
PCX, PCY = 512, 516          # plate centre
R_PLATE = 404                # plate outer radius
R_WELL = 296                 # plate well radius
NCX, NCY = 506, 502          # pasta nest centre
SAUCE = (164, 40, 16)
SAUCE_D = (122, 26, 9)
SAUCE_L = (203, 80, 32)


# ---------------------------------------------------------------- table
def draw_table():
    plank_h = 170
    plank_tones = [1.00, 0.92, 1.05, 0.95, 1.01, 0.94]
    base = (46, 30, 18)
    for y in range(H):
        tone = plank_tones[(y // plank_h) % len(plank_tones)]
        row = FB[y]
        for x in range(W):
            blotch = noise2(G16, 16, x / 300.0, y / 300.0)
            # long horizontal grain: heavily stretched noise, ridged
            g = noise2(G64, 64, x / 150.0, y / 9.0)
            ridge = 1.0 - abs(2.0 * g - 1.0)
            grain = ridge * ridge * 0.16
            fine = noise2(G256, 256, x / 30.0, y / 5.0)
            b = tone * (0.74 + blotch * 0.30 + grain
                        + (fine - 0.5) * 0.055)
            i = x * 3
            row[i] = clamp255(base[0] * b)
            row[i + 1] = clamp255(base[1] * b)
            row[i + 2] = clamp255(base[2] * b)
    # a few darker grain streaks wandering along the planks
    rng = random.Random(31)
    for _ in range(26):
        y0 = rng.random() * H
        pts = []
        for i in range(25):
            t = i / 24.0
            pts.append((t * W, y0 + 6.0 * math.sin(t * 9.0 + y0)
                        + (rng.random() - 0.5) * 2.0))
        stamp_soft_path(pts, 2.2 + rng.random() * 2.0, (16, 9, 4),
                        0.10 + rng.random() * 0.10)
    # plank seams: soft dark gap with a faint catch-light below
    for k in range(1, H // plank_h + 1):
        y = k * plank_h
        for x in range(W):
            wob = int(2.0 * math.sin(x * 0.011 + k * 2.3))
            yy = y + wob
            blend(x, yy - 1, 8, 5, 3, 0.30)
            blend(x, yy, 5, 3, 2, 0.60)
            blend(x, yy + 1, 5, 3, 2, 0.42)
            blend(x, yy + 2, 120, 86, 54, 0.08)


# ---------------------------------------------------------------- plate
def draw_plate():
    # blurred, multi-layer contact shadow on the table
    soft_shadow(PCX + 20, PCY + 38, R_PLATE + 58, strength=0.60, squash=0.93)
    soft_shadow(PCX + 12, PCY + 22, R_PLATE + 30, strength=0.42, squash=0.95)
    soft_shadow(PCX + 6, PCY + 12, R_PLATE + 10, strength=0.30, squash=0.96)
    for y in range(PCY - R_PLATE - 2, PCY + R_PLATE + 3):
        dy = y - PCY
        for x in range(PCX - R_PLATE - 2, PCX + R_PLATE + 3):
            dx = x - PCX
            d = math.sqrt(dx * dx + dy * dy)
            if d > R_PLATE:
                continue
            t = d / R_PLATE
            li = 1.0 + 0.14 * ((dx * L3X + dy * L3Y) / R_PLATE)
            if t < 0.72:  # the well
                c = mix((240, 232, 214), (228, 216, 192), t / 0.72)
                li *= 0.985
            else:         # the rim, cresting toward the light
                s = (t - 0.72) / 0.28
                c = mix((228, 216, 192), (246, 239, 224),
                        math.sin(s * math.pi * 0.62))
                if s > 0.86:
                    c = mix(c, (208, 196, 174), (s - 0.86) / 0.14)
            # stoneware mottle (coarse octaves only, so the big pale
            # surface stays smooth and compressible) + faint rings
            mo = (0.62 * noise2(G16, 16, (x + 40.0) / 128.0, (y + 9.0) / 128.0)
                  + 0.38 * noise2(G32, 32, (x + 40.0) / 48.0, (y + 9.0) / 48.0))
            li *= 0.974 + mo * 0.052
            ring = math.sin(d * 1.35 + (mo - 0.5) * 5.0) * 0.0045
            li *= 1.0 + ring
            put(x, y, clamp255(c[0] * li), clamp255(c[1] * li),
                clamp255(c[2] * li))
    # broad soft sheen sweeping the upper-left rim
    stamp_soft_path(arc_pts(PCX, PCY, R_PLATE - 52, math.radians(168),
                            math.radians(262), 60), 44.0,
                    (255, 253, 244), 0.10)
    # grooves: soft twin lines at the rim edge and the well edge
    stamp_soft_path(arc_pts(PCX, PCY, R_PLATE - 14, 0, math.tau, 180), 3.2,
                    (172, 159, 136), 0.35)
    stamp_soft_path(arc_pts(PCX, PCY, R_WELL + 12, 0, math.tau, 180), 4.2,
                    (178, 165, 140), 0.30)
    stamp_soft_path(arc_pts(PCX, PCY, R_WELL + 18, math.radians(150),
                            math.radians(255), 40), 4.5,
                    (255, 252, 242), 0.30)
    # the well's inner wall falls into soft shade at lower right
    stamp_soft_path(arc_pts(PCX, PCY, R_WELL - 6, math.radians(18),
                            math.radians(150), 60), 13.0,
                    (198, 184, 156), 0.16)


# ---------------------------------------------------------------- sauce
def _sauce_color(x, y, t):
    n1 = fbm(x * 0.9, y * 0.9)
    n2 = noise2(G128, 128, x / 11.0, y / 11.0)
    c = mix(SAUCE_D, SAUCE, min(1.0, max(0.0, (n1 - 0.18) * 1.7)))
    if n1 > 0.62:
        c = mix(c, SAUCE_L, (n1 - 0.62) * 1.6)
    if n2 > 0.78:  # flecks of brighter pulp
        c = mix(c, (216, 102, 44), (n2 - 0.78) * 2.2)
    li = (1.0 - 0.14 * t) * (0.94 + n2 * 0.12)
    return (clamp255(c[0] * li), clamp255(c[1] * li), clamp255(c[2] * li))


def draw_sauce_swoosh():
    # a spoon-drag tail pulled from the pool's lower-left edge
    p0 = (452, 622)
    p1 = (386, 652)
    p2 = (322, 664)
    n = 44
    pts = []
    for i in range(n + 1):
        t = i / n
        x = ((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0])
        y = ((1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1])
        pts.append((x, y))
    for i, (x, y) in enumerate(pts):
        t = i / n
        w = (24 * (1 - t) ** 0.8 + 3) * 0.5
        if w > 1.2:
            _saucestamp(x, y, w, 0.16)
    for i, (x, y) in enumerate(pts):
        t = i / n
        w = (20 * (1 - t) ** 0.8 + 2) * 0.5
        if w > 1.2:
            _saucestamp(x, y, w, 0.68)
    # glossy streak + oil glints along the tail
    stamp_soft_path(pts[4:30], 3.0, (232, 122, 70), 0.35)
    rng = random.Random(111)
    for _ in range(8):
        i = 4 + int(rng.random() * 26)
        soft_disc(pts[i][0], pts[i][1], 2.4, (255, 216, 132), 0.5)


def _saucestamp(cx, cy, r, alpha):
    for y in range(int(cy - r - 1), int(cy + r + 2)):
        dy = y - cy
        for x in range(int(cx - r - 1), int(cx + r + 2)):
            dx = x - cx
            q = dx * dx + dy * dy
            if q <= r * r:
                cr, cg, cb = _sauce_color(x, y, math.sqrt(q) / r * 0.4)
                blend(x, y, cr, cg, cb, alpha)


def draw_sauce_pool():
    # sauce pooled beneath the nest: ragged, hand-spooned, mottled edge
    cx, cy, R = NCX, NCY + 8, 148
    for y in range(cy - R - 16, cy + R + 17):
        dy = y - cy
        for x in range(cx - R - 16, cx + R + 17):
            dx = x - cx
            d = math.sqrt(dx * dx + dy * dy)
            ang = math.atan2(dy, dx)
            edge_n = (noise2(G32, 32, x / 70.0, y / 70.0) - 0.5)
            reff = R * (1.0 + 0.055 * math.sin(ang * 3.0 + 1.2)
                        + 0.045 * math.sin(ang * 7.0 + 4.0)
                        + 0.11 * edge_n)
            if d <= reff:
                t = d / R
                cr, cg, cb = _sauce_color(x, y, t)
                li = 1.0 + 0.07 * ((dx * L3X + dy * L3Y) / R)
                put(x, y, clamp255(cr * li), clamp255(cg * li),
                    clamp255(cb * li))
            elif d <= reff + 10:  # thin stained halo where sauce was wiped
                blend(x, y, 172, 52, 24, 0.13 * (1.0 - (d - reff) / 10.0))
    # wet gloss: soft sheen patches and pinpoint sparkles
    soft_light(NCX - 44, NCY - 30, 66, 0.13, 0.9)
    soft_light(NCX + 58, NCY + 38, 44, 0.08, 0.9)
    rng = random.Random(115)
    for _ in range(26):
        a = rng.random() * math.tau
        rr = math.sqrt(rng.random()) * 128
        soft_disc(NCX + rr * math.cos(a), NCY + 8 + rr * math.sin(a) * 0.95,
                  1.6 + rng.random() * 1.6, (255, 206, 140), 0.40)


# ---------------------------------------------------------------- pasta
PASTA_COLS = [(233, 187, 94), (238, 196, 106), (228, 178, 84), (242, 205, 120),
              (236, 190, 98), (224, 172, 78)]
PASTA_HL = (252, 226, 156)


def ribbon(pts, width, col, shadow_alpha=0.22):
    """A pasta ribbon with true cross-section shading: brightness is a
    function of the pixel's position across the strand (dark edges, a
    broad lit top whose ridge shifts toward the light depending on the
    strand's orientation), so the shading stays continuous along the
    strand instead of beading stamp by stamp. A soft contact shadow is
    laid first, offset away from the light."""
    r = width * 0.5
    stamp_soft_path([(p[0] + 3.0, p[1] + 4.2) for p in pts], width * 1.04,
                    (110, 70, 22), shadow_alpha)
    step = max(2.0, r * 0.40)
    sp = resample(pts, step)
    half = step * 0.78
    reach = r + half + 1.5
    last = len(sp) - 1
    for i, (cx, cy) in enumerate(sp):
        x0, y0 = sp[i - 1] if i > 0 else sp[0]
        x1, y1 = sp[i + 1] if i < last else sp[last]
        tx, ty = x1 - x0, y1 - y0
        tl = math.hypot(tx, ty)
        if tl == 0:
            continue
        tx, ty = tx / tl, ty / tl
        px, py = -ty, tx
        # the bright ridge shifts toward whichever side faces the light
        shift = (px * L3X + py * L3Y) * 0.38
        tone = (0.94 + noise2(G64, 64, cx / 46.0, cy / 46.0) * 0.12)
        for y in range(int(cy - reach), int(cy + reach + 1)):
            rely = y - cy
            for x in range(int(cx - reach), int(cx + reach + 1)):
                relx = x - cx
                along = relx * tx + rely * ty
                if along > half or along < -half:
                    continue
                perp = relx * px + rely * py
                if perp > r or perp < -r:
                    continue
                w = perp / r - shift
                if w > 1.0 or w < -1.0:
                    prof = 0.0
                else:
                    prof = math.sqrt(1.0 - w * w)
                prof = prof ** 0.62  # flattened top: a ribbon, not a tube
                edge = math.sqrt(max(0.0, 1.0 - (perp / r) ** 2))
                li = (0.40 + 0.72 * prof) * (0.72 + 0.28 * edge) * tone
                p2 = prof * prof
                spk = 0.24 * p2 * p2 * p2 * prof  # gentle wet sheen
                ef = (r - abs(perp)) / 1.6
                a = 0.92 if ef >= 1.0 else 0.92 * max(0.0, ef)
                a *= 0.80 + 0.20 * math.cos(math.pi * along / half)
                blend(x, y,
                      clamp255(col[0] * li + 240.0 * spk),
                      clamp255(col[1] * li + 233.0 * spk),
                      clamp255(col[2] * li + 208.0 * spk), a)


def spiral_pts(cx, cy, r0, r1, turns, phase, squash=0.92, n=90):
    pts = []
    for i in range(n + 1):
        t = i / n
        a = phase + t * turns * math.tau
        r = r0 + (r1 - r0) * t
        pts.append((cx + r * math.cos(a), cy + r * squash * math.sin(a)))
    return pts


def nest_base(cx, cy, R, scale):
    """The shaded pasta mass under the ribbons: mottled gold, dark in the
    crevices, so gaps between strands read as pasta in shadow."""
    squash = 0.92
    for y in range(int(cy - R * squash - 2), int(cy + R * squash + 3)):
        dy = (y - cy) / squash
        for x in range(int(cx - R - 2), int(cx + R + 3)):
            dx = x - cx
            d = math.sqrt(dx * dx + dy * dy)
            if d > R:
                continue
            t = d / R
            n = fbm(x * 1.4, y * 1.4)
            c = mix((206, 158, 76), (172, 124, 50), min(1.0, t * 1.25))
            c = mix(c, (226, 182, 96), max(0.0, (n - 0.42)) * 1.5)
            if n < 0.34:  # crevice darkening
                c = mix(c, (138, 96, 36), (0.34 - n) * 2.4)
            li = 1.0 + 0.10 * ((dx * L3X + dy * L3Y) / R) - 0.10 * t
            put(x, y, clamp255(c[0] * li), clamp255(c[1] * li),
                clamp255(c[2] * li))
    # ambient-occlusion blobs tucked between future strands
    rng = random.Random(777)
    for _ in range(46):
        a = rng.random() * math.tau
        rr = math.sqrt(rng.random()) * R * 0.88
        soft_disc(cx + rr * math.cos(a), cy + rr * math.sin(a) * squash,
                  (7 + rng.random() * 15) * scale, (112, 76, 26),
                  0.10 + rng.random() * 0.08)


def draw_nest(cx, cy, scale, rng, strands):
    soft_shadow(cx + 6, cy + 12, 152 * scale, strength=0.36, squash=0.9)
    nest_base(cx, cy, 148 * scale, scale)
    for s in range(strands):
        t = s / max(1, strands - 1)
        r_out = (148 - 66 * t) * scale
        r_in = r_out * (0.28 + 0.22 * rng.random())
        turns = 1.3 + rng.random() * 1.0
        phase = rng.random() * math.tau
        jx = cx + (rng.random() - 0.5) * 30 * scale
        jy = cy + (rng.random() - 0.5) * 24 * scale
        col = PASTA_COLS[rng.randrange(len(PASTA_COLS))]
        pts = spiral_pts(jx, jy, r_in, r_out, turns, phase)
        ribbon(pts, (18.5 - 3.5 * t) * (0.9 + rng.random() * 0.25)
               * max(0.62, scale), col)
    # crossing chords swept straight across the twirl
    for k in range(6):
        ang = rng.random() * math.tau
        off = (rng.random() - 0.5) * 120 * scale
        bulge = (rng.random() - 0.5) * 46 * scale
        ca, sa = math.cos(ang), math.sin(ang)
        pts = []
        for i in range(31):
            tt = i / 30.0
            along = (tt - 0.5) * 250 * scale
            o = off + bulge * math.sin(tt * math.pi)
            pts.append((cx + along * ca - o * sa, cy + along * sa + o * ca))
        ribbon(pts, 14.5 * max(0.62, scale),
               PASTA_COLS[rng.randrange(len(PASTA_COLS))])
    # drape strands spilling over the nest edge onto the sauce
    for k in range(4):
        a = rng.random() * math.tau
        ex = cx + 120 * scale * math.cos(a)
        ey = cy + 112 * scale * math.sin(a)
        pts = spiral_pts(ex, ey, 8, 52 * scale, 0.85, rng.random() * math.tau)
        ribbon(pts, 13.5 * max(0.62, scale),
               PASTA_COLS[rng.randrange(len(PASTA_COLS))])
    # upright loops over the crown for height
    for k in range(7):
        rr = (104 - k * 12) * scale
        a0 = math.radians(175 + k * 15)
        a1 = math.radians(368 + 30 - k * 9)
        pts = arc_pts(cx + (rng.random() - 0.5) * 14, cy - 4 * scale, rr,
                      a0, a1, 60, squash=0.82)
        ribbon(pts, 14.0 * max(0.62, scale),
               PASTA_COLS[rng.randrange(len(PASTA_COLS))])
    # a last whisper of AO where loops cross the body
    for _ in range(20):
        a = rng.random() * math.tau
        rr = math.sqrt(rng.random()) * 108 * scale
        soft_disc(cx + rr * math.cos(a), cy + rr * math.sin(a) * 0.9,
                  6 + rng.random() * 10, (116, 80, 28), 0.07)
    # centre dimple: tight bright spiral at the very top
    pts = spiral_pts(cx, cy - 2, 4, 28 * scale, 1.6, 0.8)
    ribbon(pts, 10.5 * max(0.62, scale), (232, 182, 88), shadow_alpha=0.15)
    # crown kiss of light, upper-left of the nest
    soft_light(cx - 52 * scale, cy - 44 * scale, 62 * scale, 0.10, 0.9)


def draw_side_twirl(cx, cy, rng):
    soft_shadow(cx + 4, cy + 7, 56, strength=0.32, squash=0.9)
    nest_base(cx, cy, 50, 0.34)
    for s in range(5):
        r_out = 48 - s * 7
        pts = spiral_pts(cx + (rng.random() - 0.5) * 10,
                         cy + (rng.random() - 0.5) * 8,
                         r_out * 0.35, r_out, 0.85 + rng.random() * 0.35,
                         rng.random() * math.tau)
        ribbon(pts, 12.5, PASTA_COLS[rng.randrange(len(PASTA_COLS))])
    for k in range(3):  # loose strands across, so it is pasta, not a shell
        ang = rng.random() * math.tau
        ca, sa = math.cos(ang), math.sin(ang)
        off = (rng.random() - 0.5) * 36
        pts = [(cx + ((i / 16.0) - 0.5) * 96 * ca - off * sa,
                cy + ((i / 16.0) - 0.5) * 96 * sa + off * ca)
               for i in range(17)]
        ribbon(pts, 11.5, PASTA_COLS[rng.randrange(len(PASTA_COLS))])
    _saucestamp(cx + 12, cy - 8, 7.5, 0.8)


def sauce_through_pasta(rng):
    """Sauce worked through the nest: textured dabs and coated arcs."""
    for k in range(5):
        cx = NCX + (rng.random() - 0.5) * 120
        cy = NCY + (rng.random() - 0.5) * 100
        a0 = rng.random() * math.tau
        pts = arc_pts(cx, cy, 58 + rng.random() * 34, a0, a0 + 0.55, 14)
        for (x, y) in resample(pts, 5.0):
            _saucestamp(x, y, 6.2, 0.55)
        stamp_soft_path([(p[0] - 1.2, p[1] - 1.4) for p in pts], 3.0,
                        (228, 110, 62), 0.30)
    for k in range(16):
        a = rng.random() * math.tau
        rr = math.sqrt(rng.random()) * 112
        _saucestamp(NCX + rr * math.cos(a), NCY + rr * math.sin(a) * 0.92,
                    3.2 + rng.random() * 4.2, 0.65)


# ---------------------------------------------------------------- tomatoes
def draw_cherry_tomato(cx, cy, r, rng):
    soft_shadow(cx + 3, cy + 5, r + 4, strength=0.30, squash=0.94)
    # skin: deep red rim with a glossy lit shoulder
    for y in range(int(cy - r - 1), int(cy + r + 2)):
        dy = y - cy
        for x in range(int(cx - r - 1), int(cx + r + 2)):
            dx = x - cx
            q = (dx * dx + dy * dy) / (r * r)
            if q > 1.0:
                continue
            nz = math.sqrt(1.0 - q)
            dif = max(0.0, dx / r * L3X + dy / r * L3Y + nz * L3Z)
            c = mix((198, 52, 26), (138, 20, 9),
                    min(1.0, math.sqrt(q) * 1.1))
            li = 0.42 + 0.85 * dif
            put(x, y, clamp255(c[0] * li), clamp255(c[1] * li),
                clamp255(c[2] * li))
    # cut face: juicy flesh, mottled, lighter pulp toward the middle
    rf = r * 0.82
    for y in range(int(cy - rf - 1), int(cy + rf + 2)):
        dy = y - cy
        for x in range(int(cx - rf - 1), int(cx + rf + 2)):
            dx = x - cx
            q = (dx * dx + dy * dy) / (rf * rf)
            if q > 1.0:
                continue
            n = fbm(x * 1.3 + 7.0, y * 1.3)
            c = mix((243, 138, 92), (219, 82, 42), min(1.0, math.sqrt(q)))
            c = mix(c, (248, 168, 118), max(0.0, (n - 0.5)) * 1.1)
            li = 1.0 + 0.09 * ((dx * L3X + dy * L3Y) / rf)
            put(x, y, clamp255(c[0] * li), clamp255(c[1] * li),
                clamp255(c[2] * li))
    # pale membranes dividing the face (soft, low contrast)
    for k in range(3):
        a = k / 3.0 * math.tau + rng.random() * 0.6
        pts = [(cx, cy), (cx + rf * 0.92 * math.cos(a),
                          cy + rf * 0.92 * math.sin(a))]
        stamp_soft_path(pts, 3.4, (247, 192, 156), 0.30)
    # seed pockets: small pale ellipses in a ring
    for k in range(6):
        a = k / 6.0 * math.tau + rng.random() * 0.5
        sx = cx + rf * 0.5 * math.cos(a)
        sy = cy + rf * 0.5 * math.sin(a)
        radial_disc(sx, sy, r * 0.13, (248, 199, 158), (238, 160, 112),
                    light_amt=0.06, power=0.8)
    radial_disc(cx, cy, r * 0.13, (245, 180, 138), (236, 150, 104),
                light_amt=0.06, power=0.8)
    # gloss: elongated wet highlight, upper-left
    soft_disc(cx - r * 0.36, cy - r * 0.40, r * 0.20, (255, 228, 208), 0.55)
    soft_disc(cx - r * 0.30, cy - r * 0.34, r * 0.08, (255, 250, 240), 0.85)


# ---------------------------------------------------------------- basil
def draw_basil(cx, cy, length, width, ang, seed):
    rng = random.Random(seed)
    ca, sa = math.cos(ang), math.sin(ang)
    soft_shadow(cx + 3, cy + 5, length * 0.52, strength=0.26, squash=0.8)
    hl = length * 0.5
    hw = width * 0.5
    for y in range(int(cy - hl - 3), int(cy + hl + 4)):
        for x in range(int(cx - hl - 3), int(cx + hl + 4)):
            dx, dy = x - cx, y - cy
            u = dx * ca + dy * sa          # along leaf, -hl..hl
            v = -dx * sa + dy * ca         # across
            if -hl <= u <= hl:
                s = (u + hl) / length      # 0 at stem, 1 at tip
                edge = hw * (math.sin(math.pi * (0.12 + 0.82 * s)) ** 0.75)
                edge *= 1.0 - 0.25 * s
                edge *= 1.0 + 0.10 * (noise2(G64, 64, x / 13.0, y / 13.0)
                                      - 0.5)
                if abs(v) <= edge:
                    vein = abs(v) / max(1.0, edge)
                    n = fbm(x * 1.2 + seed, y * 1.2)
                    c = mix((24, 88, 38), (54, 140, 64), s)
                    c = mix(c, (34, 112, 48), max(0.0, (n - 0.45)) * 1.2)
                    # cupping: darker at the edges, lit ridge at the vein
                    li = 0.70 + 0.46 * (1.0 - vein * vein)
                    if vein > 0.90:
                        li *= 0.82
                    # side veins: faint diagonal lighter lines
                    vv = abs(math.sin(s * 22.0 + vein * 2.6 + seed))
                    if vv > 0.93 and vein > 0.12:
                        li *= 1.10
                    if vein < 0.07:  # central vein, slightly paler
                        c = mix(c, (104, 186, 104), 0.30)
                    put(x, y, clamp255(c[0] * li), clamp255(c[1] * li),
                        clamp255(c[2] * li))
    # waxy sheen sweeping the lit half of the leaf
    pts = [(cx + (t - 0.30) * length * ca - width * 0.14 * sa,
            cy + (t - 0.30) * length * sa + width * 0.14 * ca)
           for t in (0, 0.25, 0.5)]
    stamp_soft_path(pts, width * 0.30, (196, 240, 186), 0.18)


# ---------------------------------------------------------------- parmesan
def draw_parmesan(rng, cx, cy, on_pasta):
    n = 8 if on_pasta else 2
    for _ in range(n):
        if on_pasta:
            a = rng.random() * math.tau
            rr = math.sqrt(rng.random()) * 72
            x = cx + rr * math.cos(a)
            y = cy + rr * math.sin(a) * 0.92 - 10
        else:
            x = cx + (rng.random() - 0.5) * 60
            y = cy + (rng.random() - 0.5) * 50
        ang = rng.random() * math.tau
        r = 9 + rng.random() * 6
        pts = arc_pts(x, y, r, ang, ang + 1.6 + rng.random() * 0.6, 12)
        # curled shaving: a thin flat flake -- soft shadow, cream body,
        # bright top edge where the curl catches the light
        stamp_soft_path([(p[0] + 1.1, p[1] + 1.5) for p in pts], 4.8,
                        (198, 182, 146), 0.35)
        stamp_path(pts, 4.4, (240, 230, 202), 0.95)
        stamp_path([(p[0] - 0.6, p[1] - 0.7) for p in pts], 1.8,
                   (255, 252, 240), 0.55)
    if on_pasta:  # a dusting of fine gratings
        for _ in range(26):
            a = rng.random() * math.tau
            rr = math.sqrt(rng.random()) * 92
            disc(cx + rr * math.cos(a), cy + rr * math.sin(a) * 0.92 - 6,
                 0.8 + rng.random() * 0.9, (246, 238, 214), 0.75)


def draw_pepper(rng):
    for _ in range(100):
        a = rng.random() * math.tau
        rr = math.sqrt(rng.random()) * 148
        x = NCX + rr * math.cos(a)
        y = NCY + rr * math.sin(a) * 0.94
        disc(x, y, 0.7 + rng.random() * 0.9, (40, 31, 24), 0.75)
    for _ in range(20):  # a few specks loose on the plate
        a = rng.random() * math.tau
        rr = 170 + rng.random() * 105
        disc(PCX + rr * math.cos(a), PCY + rr * math.sin(a),
             0.7 + rng.random() * 0.8, (46, 37, 28), 0.5)


def draw_oil_drizzle(rng):
    pts = spiral_pts(NCX, NCY, 16, 108, 2.2, 1.1)
    stamp_soft_path(pts, 3.6, (246, 208, 110), 0.26)
    for i in range(0, len(pts) - 6, 9):
        stamp_soft_path(pts[i:i + 5], 1.5, (255, 242, 196), 0.5)


# ---------------------------------------------------------------- fork
def _metal_path(pts, width, shadow=True):
    if shadow:
        stamp_soft_path([(p[0] + 7, p[1] + 10) for p in pts], width * 1.1,
                        (0, 0, 0), 0.22)
    stamp_path(pts, width, (96, 100, 107), 1.0)
    stamp_path(pts, width * 0.68, (158, 163, 171), 1.0)
    off = [(p[0] - width * 0.10, p[1] - width * 0.12) for p in pts]
    stamp_path(off, width * 0.34, (214, 218, 224), 0.85)
    off2 = [(p[0] - width * 0.14, p[1] - width * 0.16) for p in pts]
    stamp_path(off2, width * 0.12, (242, 244, 247), 0.8)


def draw_fork():
    # resting at the right edge: head on the rim, handle onto the table
    hx, hy = 838, 428
    ang = math.radians(52)
    ca, sa = math.cos(ang), math.sin(ang)
    end = (hx + 208 * ca, hy + 208 * sa)
    _metal_path([(hx, hy), end], 16.5)
    # neck + head base, lit like the handle
    shade_stamp(hx, hy, 17, (168, 173, 180), tone=1.0, alpha=1.0,
                spec_amt=0.35)
    shade_stamp(hx - 2, hy - 2, 12, (188, 193, 199), tone=1.0, alpha=0.9,
                spec_amt=0.35)
    ta = ang + math.pi
    for k in range(4):
        off = (k - 1.5) * 9.6
        ox, oy = -sa * off, ca * off
        p0 = (hx + ox, hy + oy)
        p1 = (hx + ox + 36 * math.cos(ta), hy + oy + 36 * math.sin(ta))
        _metal_path([p0, p1], 6.4, shadow=False)


# ---------------------------------------------------------------- steam
def draw_steam():
    for (x, y, r, s) in ((468, 408, 66, 0.05), (536, 380, 84, 0.04),
                         (500, 330, 100, 0.03)):
        soft_light(x, y, r, s, 0.62)


# ---------------------------------------------------------------- finish
def draw_finish():
    """Photographic finish: warm top-light, gentle vignette, fine grain.
    The grain is drawn from fine seeded noise fields (1-3 px correlation)
    rather than white noise: it still breaks up flat areas and banding,
    but stays compressible."""
    lx, ly = 330, 300
    for y in range(H):
        dy = y - PCY
        row = FB[y]
        for x in range(W):
            dx = x - PCX
            dc2 = dx * dx + dy * dy
            v = min(1.0, dc2 / (760.0 * 760.0))
            vig = 1.0 - 0.27 * v * v
            dg2 = (x - lx) * (x - lx) + (y - ly) * (y - ly)
            glow = 1.0 / (1.0 + dg2 / 220000.0)
            f = vig * (0.94 + 0.14 * glow)
            i = x * 3
            grain = ((noise2(G256, 256, x / 1.5, y / 1.5) - 0.5) * 2.7
                     + (noise2(G128, 128, x / 2.6, y / 2.6) - 0.5) * 2.7)
            row[i] = clamp255(row[i] * f + 12.0 * glow + grain)
            row[i + 1] = clamp255(row[i + 1] * f + 8.0 * glow + grain)
            row[i + 2] = clamp255(row[i + 2] * f + 2.0 * glow + grain * 0.9)


# ---------------------------------------------------------------- PNG encode
def encode_png():
    stride = W * 3
    out = bytearray()
    prev = bytes(stride)
    for y in range(H):
        row = bytes(FB[y])
        sub = bytearray(stride)
        up = bytearray(stride)
        pae = bytearray(stride)
        for i in range(stride):
            left = row[i - 3] if i >= 3 else 0
            u = prev[i]
            ul = prev[i - 3] if i >= 3 else 0
            sub[i] = (row[i] - left) & 0xFF
            up[i] = (row[i] - u) & 0xFF
            p = left + u - ul
            pa = abs(p - left)
            pb = abs(p - u)
            pc = abs(p - ul)
            pred = left if (pa <= pb and pa <= pc) else (u if pb <= pc
                                                          else ul)
            pae[i] = (row[i] - pred) & 0xFF

        def cost(buf):
            s = 0
            for b in buf:
                s += b if b < 128 else 256 - b
            return s

        cands = ((cost(row), 0, row), (cost(sub), 1, bytes(sub)),
                 (cost(up), 2, bytes(up)), (cost(pae), 4, bytes(pae)))
        _, ftype, data = min(cands, key=lambda c: c[0])
        out.append(ftype)
        out += data
        prev = row
    comp = zlib.compress(bytes(out), 9)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        c += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return c

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


# ---------------------------------------------------------------- main
def render():
    draw_table()
    draw_plate()
    draw_sauce_swoosh()
    draw_sauce_pool()
    rng = random.Random(1212)
    draw_cherry_tomato(348, 366, 31, rng)
    draw_cherry_tomato(680, 374, 29, rng)
    draw_side_twirl(322, 648, rng)
    draw_side_twirl(694, 656, rng)
    draw_nest(NCX, NCY, 1.0, rng, 16)
    sauce_through_pasta(rng)
    draw_cherry_tomato(578, 424, 24, rng)
    draw_basil(452, 428, 74, 40, -0.7, 21)
    draw_basil(566, 500, 66, 36, 2.5, 22)
    draw_basil(398, 600, 60, 33, 0.9, 23)
    draw_basil(646, 556, 58, 32, -2.2, 24)
    draw_parmesan(rng, NCX, NCY, True)
    draw_parmesan(rng, 372, 452, False)
    draw_pepper(rng)
    draw_oil_drizzle(rng)
    draw_steam()
    draw_fork()
    draw_finish()
    return encode_png()


def main():
    png = render()
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "wb") as f:
        f.write(png)


if __name__ == "__main__":
    main()
