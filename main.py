#!/usr/bin/env python3
"""
Make the best-looking food picture -- make.fun bounty entry.

Renders a state-of-the-art fine-dining pasta plate, top-down: a tall
twirled nest of fresh golden tagliatelle with deep tomato sauce on an
ivory stoneware plate, over a dark wooden table. Pure Python standard
library: an in-memory RGB framebuffer, hand-drawn shapes, seeded value
noise, and a zlib-compressed PNG written to /output/entry.png.

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


GRID_BIG = make_grid(8, 101)
GRID_GRAIN = make_grid(48, 202)
GRID_FINE = make_grid(160, 303)

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


def radial_disc(cx, cy, r, c_in, c_out, light=(-0.55, -0.83), light_amt=0.16,
                power=1.0, squash=1.0):
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
            li = 1.0 + light_amt * ((dx * light[0] + dy * light[1]) / r)
            put(x, y, clamp255(cr * li), clamp255(cg * li), clamp255(cb * li))


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
    ry = r * squash
    for y in range(int(cy - ry - 1), int(cy + ry + 2)):
        dy = (y - cy) / ry
        for x in range(int(cx - r - 1), int(cx + r + 2)):
            dx = (x - cx) / r
            d2 = dx * dx + dy * dy
            if d2 < 1.0:
                blend(x, y, 255, 250, 238, strength * (1.0 - d2) ** 1.7)


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


def arc_pts(cx, cy, r, a0, a1, n=48, squash=1.0):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n),
             cy + r * squash * math.sin(a0 + (a1 - a0) * i / n))
            for i in range(n + 1)]


# ---------------------------------------------------------------- layout
PCX, PCY = 512, 516          # plate centre
R_PLATE = 404                # plate outer radius
R_WELL = 296                 # plate well radius
NCX, NCY = 506, 502          # pasta nest centre
SAUCE = (164, 40, 16)
SAUCE_D = (128, 28, 10)
SAUCE_L = (198, 74, 30)


# ---------------------------------------------------------------- table
def draw_table():
    plank_h = 170
    plank_tones = [1.00, 0.92, 1.05, 0.95, 1.01, 0.94]
    base = (43, 28, 17)
    for y in range(H):
        tone = plank_tones[(y // plank_h) % len(plank_tones)]
        row = FB[y]
        for x in range(W):
            blotch = noise2(GRID_BIG, 8, x / 260.0, y / 260.0)
            streak = noise2(GRID_GRAIN, 48, x / 180.0, y / 14.0)
            fine = noise2(GRID_FINE, 160, x / 26.0, y / 26.0)
            b = tone * (0.78 + blotch * 0.27 + (streak - 0.5) * 0.16
                        + (fine - 0.5) * 0.07)
            i = x * 3
            row[i] = clamp255(base[0] * b)
            row[i + 1] = clamp255(base[1] * b)
            row[i + 2] = clamp255(base[2] * b)
    for k in range(1, H // plank_h + 1):
        y = k * plank_h
        for x in range(W):
            wob = int(2.0 * math.sin(x * 0.011 + k * 2.3))
            yy = y + wob
            blend(x, yy, 6, 4, 2, 0.55)
            blend(x, yy + 1, 6, 4, 2, 0.35)
            blend(x, yy + 2, 110, 78, 48, 0.09)


# ---------------------------------------------------------------- plate
def draw_plate():
    soft_shadow(PCX + 16, PCY + 30, R_PLATE + 46, strength=0.62, squash=0.94)
    soft_shadow(PCX + 7, PCY + 13, R_PLATE + 12, strength=0.34, squash=0.96)
    # body: ivory stoneware, radial shading, lit from upper-left
    for y in range(PCY - R_PLATE - 2, PCY + R_PLATE + 3):
        dy = y - PCY
        for x in range(PCX - R_PLATE - 2, PCX + R_PLATE + 3):
            dx = x - PCX
            d = math.sqrt(dx * dx + dy * dy)
            if d > R_PLATE:
                continue
            t = d / R_PLATE
            li = 1.0 + 0.13 * ((dx * -0.55 + dy * -0.83) / R_PLATE)
            if t < 0.72:  # the well: gently shaded, warm pool of light
                c = mix((243, 236, 220), (236, 226, 204), t / 0.72)
                li *= 0.985
            else:         # the rim: rises, catches more light at its crest
                s = (t - 0.72) / 0.28
                c = mix((236, 226, 204), (247, 241, 228), math.sin(s * math.pi * 0.62))
                if s > 0.86:
                    c = mix(c, (214, 203, 182), (s - 0.86) / 0.14)
            sp = noise2(GRID_FINE, 160, x / 34.0, y / 34.0)
            li *= 0.985 + sp * 0.03
            put(x, y, clamp255(c[0] * li), clamp255(c[1] * li),
                clamp255(c[2] * li))
    # rim grooves
    stamp_path(arc_pts(PCX, PCY, R_PLATE - 14, 0, math.tau, 180), 2.4,
               (178, 166, 144), 0.5)
    stamp_path(arc_pts(PCX, PCY, R_WELL + 12, 0, math.tau, 180), 3.0,
               (186, 174, 150), 0.45)
    stamp_path(arc_pts(PCX, PCY, R_WELL + 18, math.radians(150),
                       math.radians(255), 40), 3.4, (255, 252, 242), 0.35)
    # foot shadow ring just inside the well edge (depth cue)
    stamp_path(arc_pts(PCX, PCY, R_WELL - 4, math.radians(20),
                       math.radians(160), 60), 10.0, (206, 192, 166), 0.18)


# ---------------------------------------------------------------- sauce
def draw_sauce_swoosh():
    # a spoon-drag tail pulled from the pool's lower-left edge,
    # tapering away under the left side twirl
    p0 = (452, 622)
    p1 = (372, 660)
    p2 = (292, 676)
    n = 44
    pts = []
    for i in range(n + 1):
        t = i / n
        x = ((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0])
        y = ((1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1])
        pts.append((x, y))
    for i, (x, y) in enumerate(pts):
        t = i / n
        w = 34 * (1 - t) ** 0.8 + 3
        disc(x, y, w * 0.72, SAUCE, 0.15)
    for i, (x, y) in enumerate(pts):
        t = i / n
        w = 30 * (1 - t) ** 0.8 + 2
        disc(x, y, w * 0.5, SAUCE, 0.85)
    stamp_path(pts[4:30], 2.6, (226, 110, 62), 0.4)
    # a few oil glints along the tail
    rng = random.Random(111)
    for _ in range(7):
        i = 4 + int(rng.random() * 26)
        disc(pts[i][0], pts[i][1], 1.8, (255, 214, 130), 0.55)


def draw_sauce_pool():
    # sauce pooled beneath the nest: ragged, hand-spooned edge
    cx, cy, R = NCX, NCY + 8, 148
    for y in range(cy - R - 14, cy + R + 15):
        dy = y - cy
        for x in range(cx - R - 14, cx + R + 15):
            dx = x - cx
            d = math.sqrt(dx * dx + dy * dy)
            ang = math.atan2(dy, dx)
            reff = R * (1.0 + 0.055 * math.sin(ang * 3.0 + 1.2)
                        + 0.045 * math.sin(ang * 7.0 + 4.0)
                        + 0.05 * (noise2(GRID_GRAIN, 48, x / 90.0, y / 90.0)
                                  - 0.5))
            if d <= reff:
                t = d / R
                c = mix((178, 50, 21), (140, 33, 12), min(1.0, t * 1.15))
                li = 1.0 + 0.08 * ((dx * -0.55 + dy * -0.83) / R)
                put(x, y, clamp255(c[0] * li), clamp255(c[1] * li),
                    clamp255(c[2] * li))
            elif d <= reff + 9:  # thin stained halo where sauce was wiped
                blend(x, y, 172, 52, 24, 0.14 * (1.0 - (d - reff) / 9.0))
    soft_light(NCX - 36, NCY - 18, 74, 0.10, 0.9)


# ---------------------------------------------------------------- pasta
PASTA_COLS = [(233, 187, 94), (238, 196, 106), (228, 178, 84), (242, 205, 120)]
PASTA_SH = (186, 134, 56)
PASTA_HL = (252, 226, 156)


def ribbon(pts, width, col, shadow=True):
    if len(pts) < 3:
        return
    if shadow:
        stamp_path([(p[0] + 2.5, p[1] + 3.5) for p in pts], width,
                   (150, 96, 34), 0.30)
    stamp_path(pts, width, col, 1.0)
    stamp_path([(p[0] - 1.8, p[1] - 2.0) for p in pts], width * 0.30,
               PASTA_HL, 0.5)


def spiral_pts(cx, cy, r0, r1, turns, phase, squash=0.92, n=90):
    pts = []
    for i in range(n + 1):
        t = i / n
        a = phase + t * turns * math.tau
        r = r0 + (r1 - r0) * t
        pts.append((cx + r * math.cos(a), cy + r * squash * math.sin(a)))
    return pts


def draw_nest(cx, cy, scale, rng, strands):
    """A tong-twirled nest: jittered spiral ribbons, crossing chords,
    strands draping over the edge, and upright loops for height."""
    # grounding shadow, then a shaded pasta mass so gaps between
    # ribbons read as pasta in shadow, not holes
    soft_shadow(cx + 5, cy + 10, 148 * scale, strength=0.34, squash=0.9)
    radial_disc(cx, cy, 148 * scale, (219, 172, 88), (192, 142, 60),
                light_amt=0.08, power=0.9, squash=0.92)
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
    # crossing chords: ribbons swept straight across the twirl
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
        col = PASTA_COLS[rng.randrange(len(PASTA_COLS))]
        ribbon(pts, 14.0 * max(0.62, scale), col)
    # centre dimple: small dark spiral at the very top
    pts = spiral_pts(cx, cy - 2, 4, 28 * scale, 1.6, 0.8)
    stamp_path(pts, 10.5 * max(0.62, scale), (214, 162, 74), 1.0)
    stamp_path([(p[0] - 1.5, p[1] - 1.6) for p in pts], 3.2, PASTA_HL, 0.5)


def draw_side_twirl(cx, cy, rng):
    soft_shadow(cx + 4, cy + 7, 56, strength=0.32, squash=0.9)
    radial_disc(cx, cy, 50, (219, 172, 88), (192, 142, 60),
                light_amt=0.08, power=0.9, squash=0.92)
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
    disc(cx + 12, cy - 8, 7, SAUCE, 0.75)


def sauce_through_pasta(rng):
    """Gentle sauce-coated arcs and dabs worked through the nest."""
    for k in range(5):
        cx = NCX + (rng.random() - 0.5) * 120
        cy = NCY + (rng.random() - 0.5) * 100
        a0 = rng.random() * math.tau
        pts = arc_pts(cx, cy, 58 + rng.random() * 34, a0, a0 + 0.55, 14)
        stamp_path(pts, 11.5, SAUCE, 0.55)
        stamp_path([(p[0] - 1.2, p[1] - 1.4) for p in pts], 3.0,
                   (224, 104, 58), 0.35)
    for k in range(16):
        a = rng.random() * math.tau
        rr = math.sqrt(rng.random()) * 112
        disc(NCX + rr * math.cos(a), NCY + rr * math.sin(a) * 0.92,
             3.0 + rng.random() * 4.5, SAUCE, 0.62)


# ---------------------------------------------------------------- tomatoes
def draw_cherry_tomato(cx, cy, r, rng):
    soft_shadow(cx + 3, cy + 5, r + 3, strength=0.30, squash=0.94)
    radial_disc(cx, cy, r, (214, 62, 32), (144, 22, 10),
                light_amt=0.14, power=0.9)
    # cut face: juicy, lighter toward the middle
    radial_disc(cx, cy, r * 0.82, (240, 128, 84), (216, 76, 38),
                light_amt=0.10, power=0.9)
    # pale membranes dividing the face
    for k in range(3):
        a = k / 3.0 * math.tau + rng.random() * 0.6
        pts = [(cx, cy), (cx + r * 0.78 * math.cos(a),
                          cy + r * 0.78 * math.sin(a))]
        stamp_path(pts, 2.2, (246, 186, 148), 0.35)
    # seed pockets, kept low-contrast
    for k in range(5):
        a = k / 5.0 * math.tau + rng.random() * 0.5
        sx = cx + r * 0.46 * math.cos(a)
        sy = cy + r * 0.46 * math.sin(a)
        disc(sx, sy, r * 0.13, (246, 190, 148), 0.65)
    disc(cx, cy, r * 0.12, (244, 176, 134), 0.7)
    # gloss
    disc(cx - r * 0.36, cy - r * 0.40, r * 0.17, (255, 226, 205), 0.8)
    disc(cx - r * 0.30, cy - r * 0.34, r * 0.07, (255, 250, 240), 0.95)


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
                if abs(v) <= edge:
                    vein = abs(v) / max(1.0, edge)
                    c = mix((26, 92, 40), (52, 138, 62), s)
                    if vein < 0.10:
                        c = mix(c, (96, 178, 96), 0.34)
                    li = 1.0 - 0.16 * vein + 0.05 * math.sin(s * 20.0 + seed)
                    put(x, y, clamp255(c[0] * li), clamp255(c[1] * li),
                        clamp255(c[2] * li))
    # gloss sweep
    pts = [(cx + (t - 0.32) * length * ca - 3 * sa,
            cy + (t - 0.32) * length * sa + 3 * ca) for t in (0, 0.25, 0.5)]
    stamp_path(pts, 5.0, (190, 235, 180), 0.16)


# ---------------------------------------------------------------- parmesan
def draw_parmesan(rng, cx, cy, on_pasta):
    n = 7 if on_pasta else 2
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
        stamp_path([(p[0] + 1.2, p[1] + 1.6) for p in pts], 6.2,
                   (206, 192, 158), 0.45)
        stamp_path(pts, 5.2, (241, 231, 203), 0.95)
        stamp_path([(p[0] - 0.7, p[1] - 0.8) for p in pts], 1.6,
                   (255, 252, 240), 0.55)


def draw_pepper(rng):
    for _ in range(110):
        a = rng.random() * math.tau
        rr = math.sqrt(rng.random()) * 150
        x = NCX + rr * math.cos(a)
        y = NCY + rr * math.sin(a) * 0.94
        disc(x, y, 0.9 + rng.random() * 1.1, (34, 26, 20), 0.85)
    for _ in range(26):  # a few specks loose on the plate
        a = rng.random() * math.tau
        rr = 170 + rng.random() * 105
        disc(PCX + rr * math.cos(a), PCY + rr * math.sin(a),
             0.9 + rng.random() * 1.0, (40, 32, 24), 0.6)


def draw_oil_drizzle(rng):
    pts = spiral_pts(NCX, NCY, 16, 108, 2.2, 1.1)
    stamp_path(pts, 3.4, (246, 208, 110), 0.30)
    for i in range(0, len(pts) - 6, 9):
        stamp_path(pts[i:i + 5], 1.4, (255, 240, 190), 0.55)


# ---------------------------------------------------------------- fork
def draw_fork():
    # resting at the right edge: head on the rim, handle onto the table
    hx, hy = 838, 428            # head centre
    ang = math.radians(52)       # handle direction (down-right)
    ca, sa = math.cos(ang), math.sin(ang)
    tip = (hx - 52 * math.cos(ang - 0.0), hy - 52 * math.sin(ang))
    # shadow
    stamp_path([(hx + 8, hy + 12), (hx + 210 * ca + 8, hy + 210 * sa + 12)],
               17, (0, 0, 0), 0.30)
    # handle: dark edge, bright core, highlight
    end = (hx + 208 * ca, hy + 208 * sa)
    stamp_path([ (hx, hy), end ], 17, (104, 108, 114), 1.0)
    stamp_path([ (hx, hy), end ], 12.5, (178, 183, 190), 1.0)
    stamp_path([ (hx - 3, hy - 3), (end[0] - 3, end[1] - 3) ], 4.0,
               (228, 231, 236), 0.7)
    # neck + head base
    disc(hx, hy, 18, (172, 177, 184), 1.0)
    disc(hx - 2, hy - 2, 13, (196, 200, 206), 1.0)
    # four short parallel tines pointing up-left
    ta = ang + math.pi
    for k in range(4):
        off = (k - 1.5) * 9.6
        ox, oy = -sa * off, ca * off
        p0 = (hx + ox, hy + oy)
        p1 = (hx + ox + 36 * math.cos(ta), hy + oy + 36 * math.sin(ta))
        stamp_path([p0, p1], 6.6, (104, 108, 114), 1.0)
        stamp_path([(p0[0] - 0.8, p0[1] - 0.8), (p1[0] - 0.8, p1[1] - 0.8)],
                   4.2, (206, 210, 216), 1.0)


# ---------------------------------------------------------------- steam
def draw_steam():
    # extremely faint wisps drifting over the crown of the nest
    for (x, y, r, s) in ((468, 408, 66, 0.055), (536, 380, 84, 0.045),
                         (500, 330, 100, 0.035)):
        soft_light(x, y, r, s, 0.62)


# ---------------------------------------------------------------- final light
def draw_final_light():
    lx, ly = 320, 290
    for y in range(H):
        dy = y - PCY
        row = FB[y]
        for x in range(W):
            dx = x - PCX
            dc2 = dx * dx + dy * dy
            vig = 1.0 - 0.22 * min(1.0, dc2 / (770.0 * 770.0))
            dg2 = (x - lx) * (x - lx) + (y - ly) * (y - ly)
            glow = 1.0 / (1.0 + dg2 / 200000.0)
            f = vig * (0.95 + 0.13 * glow)
            i = x * 3
            row[i] = clamp255(row[i] * f + 13 * glow)
            row[i + 1] = clamp255(row[i + 1] * f + 9 * glow)
            row[i + 2] = clamp255(row[i + 2] * f + 3 * glow)


# ---------------------------------------------------------------- PNG encode
def encode_png():
    stride = W * 3
    out = bytearray()
    prev = bytes(stride)
    for y in range(H):
        row = bytes(FB[y])
        sub = bytearray(stride)
        up = bytearray(stride)
        for i in range(stride):
            left = row[i - 3] if i >= 3 else 0
            sub[i] = (row[i] - left) & 0xFF
            up[i] = (row[i] - prev[i]) & 0xFF

        def cost(buf):
            s = 0
            for b in buf:
                s += b if b < 128 else 256 - b
            return s

        cands = ((cost(row), 0, row), (cost(sub), 1, bytes(sub)),
                 (cost(up), 2, bytes(up)))
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
    draw_final_light()
    return encode_png()


def main():
    png = render()
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "wb") as f:
        f.write(png)


if __name__ == "__main__":
    main()
