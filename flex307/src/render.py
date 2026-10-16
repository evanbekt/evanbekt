"""307: OCCUPIED — the picture. Every frame is a function of t. 1080x1920, 30 fps.

    python3 src/render.py seg START END      frames [START, END) -> out/seg_START.mp4
    python3 src/render.py still T [T ...]    out/still_T.png, for review

Somewhat realistic: the tenant is his own photo, cut out and relit; the rooms are built from
light maps (moonlight, the hallway gap, the lamp) over painted albedo, with bloom, grain and shake.
"""
import os
import subprocess
import sys
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from story import CAPTIONS, CHAT, FLEX_AT, KNOCKS, SHOTS, STAMP_AT  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), '..')
W, H, FPS = 1080, 1920, 30
INTER = '/usr/share/fonts/opentype/inter/Inter-{}.otf'
COURIER = os.path.join(ROOT, '..', 'countersigned', 'fonts', 'CourierPrime-Bold.ttf')
f32 = np.float32


def font(name, size):
    return ImageFont.truetype(COURIER if name == 'courier' else INTER.format(name), size)


def ss(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def expo_out(x):
    x = float(np.clip(x, 0, 1))
    return 1 - 2 ** (-10 * x) if x < 1 else 1.0


def fbm(h, w, seed, octaves=6, base=3):
    r = np.random.default_rng(seed)
    out, amp, tot = np.zeros((h, w), f32), 1.0, 0.0
    for k in range(octaves):
        cells = base * 2 ** k
        g = r.random((max(2, int(cells * h / w) + 2), cells + 2)).astype(f32)
        out += amp * cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC)
        tot += amp
        amp *= 0.5
    out /= tot
    return (out - out.min()) / (out.max() - out.min())


def blur(x, s):
    return cv2.GaussianBlur(x, (0, 0), s)


def rgba_layer(img):
    a = np.asarray(img, f32) / 255
    return a[..., :3], a[..., 3:4]


def over(dst, rgb, a, x=0, y=0):
    """Alpha-composite a layer onto dst at (x, y), clipped to the frame."""
    h, w = a.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(dst.shape[1], x + w), min(dst.shape[0], y + h)
    if x1 <= x0 or y1 <= y0:
        return dst
    rs, as_ = rgb[y0 - y:y1 - y, x0 - x:x1 - x], a[y0 - y:y1 - y, x0 - x:x1 - x]
    dst[y0:y1, x0:x1] = dst[y0:y1, x0:x1] * (1 - as_) + rs * as_
    return dst


# ====================================================================== the door, seen from the bed
SW, SH = 1296, 2304                        # scene canvas, 1.2x the frame, so the camera can push in
DX0, DX1, DY0, DY1 = 348, 948, 420, 1720   # the door slab
GAP = 1732                                 # bottom of the light gap; the floor starts here
HOR = 980                                  # the floor's vanishing line


@lru_cache(None)
def door_layers():
    Y, X = np.mgrid[0:SH, 0:SW].astype(f32)
    plaster = fbm(SH, SW, 1)
    alb = np.empty((SH, SW, 3), f32)
    alb[:] = np.array([0.46, 0.46, 0.47], f32) * (0.9 + 0.2 * plaster[..., None])
    shade = np.ones((SH, SW), f32)
    # baseboard
    bb = (Y > 1650) & (Y < GAP)
    alb[bb] = [0.62, 0.61, 0.58]
    shade[(Y > 1650) & (Y < 1656)] = 0.6
    # casing round the door, then the slab and its four panels
    cas = (X > DX0 - 50) & (X < DX1 + 50) & (Y > DY0 - 50) & (Y < GAP)
    alb[cas] = [0.64, 0.63, 0.6]
    slab = (X >= DX0) & (X < DX1) & (Y >= DY0) & (Y < DY1)
    grain = fbm(SH, SW, 2, 5, 6)
    alb[slab] = (np.array([0.6, 0.58, 0.54], f32) * (0.94 + 0.08 * grain[slab][:, None]))
    shade[(np.abs(X - (DX0 - 50)) < 4) | (np.abs(X - (DX1 + 50)) < 4)] *= 0.7
    shade[(np.abs(X - DX0) < 5) & (Y > DY0) & (Y < DY1)] *= 0.35
    shade[(np.abs(X - DX1) < 5) & (Y > DY0) & (Y < DY1)] *= 0.35
    shade[(np.abs(Y - DY0) < 5) & (X > DX0) & (X < DX1)] *= 0.35
    for (px0, px1, py0, py1) in [(DX0 + 70, 640, DY0 + 80, 1020), (656, DX1 - 70, DY0 + 80, 1020),
                                 (DX0 + 70, 640, 1110, DY1 - 90), (656, DX1 - 70, 1110, DY1 - 90)]:
        inner = (X > px0) & (X < px1) & (Y > py0) & (Y < py1)
        shade[inner] *= 0.93
        e = 14
        shade[(X > px0) & (X < px1) & (Y > py0) & (Y < py0 + e)] *= 0.6        # top bevel in shadow
        shade[(X > px0) & (X < px0 + e) & (Y > py0) & (Y < py1)] *= 0.72       # left bevel
        shade[(X > px0) & (X < px1) & (Y > py1 - e) & (Y < py1)] *= 1.18       # bottom bevel catches light
        shade[(X > px1 - e) & (X < px1) & (Y > py0) & (Y < py1)] *= 1.1
    shade = blur(shade, 1.6)
    # the floor: planks running to the door, in perspective
    fl = Y >= GAP
    z = 1.0 / np.maximum(Y - HOR, 1)
    u = (X - SW / 2) * z
    pw = 0.11
    plank = np.floor(u / pw)
    fr = u / pw - plank
    tone = (np.sin(plank * 12.9898) * 43758.5453) % 1
    wood = fbm(SH, SW, 3, 6, 4)
    walb = np.stack([0.32, 0.21, 0.13]) * (0.75 + 0.35 * tone[..., None]) * (0.85 + 0.3 * wood[..., None])
    alb[fl] = walb[fl]
    seam = np.clip(1 - np.minimum(fr, 1 - fr) / (0.025 + 0.0004 / np.maximum(z * 1000, 1e-3)), 0, 1)
    shade[fl] *= 1 - 0.55 * seam[fl]
    alb *= shade[..., None]

    cool = np.array([0.72, 0.84, 1.0], f32)
    hall = np.array([0.88, 1.0, 0.86], f32)
    warm = np.array([1.0, 0.76, 0.48], f32)
    # moonlight through blinds, falling on the wall left of the door
    stripes = (np.sin((X * 0.55 + Y) * 0.055) > 0.25).astype(f32)
    win = ss(0, 120, X) * (1 - ss(260, 330, X)) * ss(300, 420, Y) * (1 - ss(1350, 1500, Y))
    moon = 0.11 + 0.05 * (1 - X / SW) + 0.32 * blur(stripes * win, 3)
    L_amb = moon[..., None] * cool
    # the hallway light spilling under the door, with and without feet blocking it
    d = np.maximum(Y - GAP, 0)
    spread = d * 0.55
    fan = ss(DX0 - 30 - spread, DX0 + 40, X) * (1 - ss(DX1 - 40, DX1 + 30 + spread, X))
    spill = np.where(fl, 1.7 * np.exp(-d / 150) * fan + 0.5 * np.exp(-d / 40) * fan, 0)
    refl = np.where(fl, 0.9 * np.exp(-d / 420) * blur(fan * (np.abs(X - SW / 2) < 300), 30), 0)
    xb = SW / 2 + (X - SW / 2) / (1 + d * 0.0045)

    def feet_mask(xs):
        m = np.zeros_like(X)
        for a, b in xs:
            m = np.maximum(m, ss(a - 8, a + 8, xb) * (1 - ss(b - 8, b + 8, xb)))
        return m

    BIG = [(548, 622), (676, 752)]
    SMALL = [(612, 634), (660, 682)]
    layers = {}
    for name, xs in [('none', []), ('big', BIG), ('small', SMALL)]:
        occ = feet_mask(xs) if xs else np.zeros_like(X)
        L_gap = (spill * (1 - 0.88 * occ) + refl * (1 - 0.6 * occ))[..., None] * hall
        em = np.zeros((SH, SW), f32)
        gx = (X > DX0 + 4) & (X < DX1 - 4) & (Y >= DY1 + 1) & (Y < GAP)
        em[gx] = 2.6
        for a, b in xs:                                        # the shoes themselves, black in the slit
            em[gx & (X > a) & (X < b)] = 0.05
        layers[name] = (alb * L_gap, blur(em, 1.2)[..., None] * hall)
    # the lamp, from the left, out of frame
    r2 = ((X + 260) ** 2 + (Y - 1250) ** 2) / 1100 ** 2
    L_lamp = (1.25 / (1 + 2.2 * r2))[..., None] * warm
    # the knob, a deadbolt, the peephole
    knob = np.zeros((SH, SW), f32)
    for cx, cy, r in [(898, 1180, 26), (898, 1064, 17)]:
        rr = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) / r
        k = rr < 1
        alb[k] = [0.42, 0.33, 0.2]
        knob = np.maximum(knob, np.where(k, np.clip(1 - np.sqrt((X - cx + r * 0.35) ** 2 + (Y - cy + r * 0.35) ** 2) / (r * 0.5), 0, 1) ** 2, 0))
    pr = np.sqrt((X - 648) ** 2 + (Y - 860) ** 2)
    alb[pr < 11] = [0.05, 0.05, 0.05]
    alb[(pr >= 11) & (pr < 15)] = [0.5, 0.45, 0.35]
    A_amb = alb * L_amb
    A_lamp = alb * L_lamp + knob[..., None] * warm * 0.9
    return dict(A_amb=A_amb, A_lamp=A_lamp, gap=layers, X=X, Y=Y)


@lru_cache(None)
def ink_noise():
    return fbm(SH // 2 + 64, SW // 2 + 64, 11, 6, 5), fbm(SH // 2 + 64, SW // 2 + 64, 12, 4, 12)


def puddle_and_figure(t, R, fig_h, fig_melt=0.0):
    """Half-res masks for the ink pool and the thing standing in it, plus its gloss."""
    n1, n2 = ink_noise()
    h, w = SH // 2, SW // 2
    ox = int(t * 6) % 60
    N1 = n1[:h, ox:ox + w]
    N2 = n2[ox // 2:ox // 2 + h, :w]
    Y, X = np.mgrid[0:h, 0:w].astype(f32)
    Y, X = Y * 2, X * 2
    cy = GAP + R * 0.3
    pool = np.zeros((h, w), f32)
    if R > 1:
        q = ((X - SW / 2) / R) ** 2 + ((Y - cy) / (R * 0.32)) ** 2
        pool = ss(0.0, 0.08, 1 - q + 0.45 * (N1 - 0.5)) * (Y >= GAP - 6)
    fig = np.zeros((h, w), f32)
    if fig_h > 4:
        by = cy + R * 0.05
        v = (by - Y) / fig_h
        xx = X - SW / 2 + (N2 - 0.5) * 34 + 10 * np.sin(Y * 0.01 + t * 1.3)
        knots = np.array([0.0, 0.08, 0.35, 0.62, 0.74, 0.8, 0.84], f32)
        hw = np.array([0.2, 0.12, 0.085, 0.11, 0.13, 0.05, 0.035], f32)
        halfw = np.interp(v, knots, hw) * fig_h * (1 - 0.4 * fig_melt)
        body = ss(-6, 6, halfw - np.abs(xx)) * (v >= 0) * (v <= 0.84)
        head = ss(-6, 6, 0.075 * fig_h - np.sqrt(xx ** 2 + ((v - 0.9) * fig_h) ** 2))
        arms = ss(-4, 4, 0.022 * fig_h - np.abs(np.abs(xx) - 0.155 * fig_h)) * (v > 0.16) * (v < 0.74)
        fig = np.maximum(np.maximum(body, head), arms) * (Y < by + 6)
    ink = np.maximum(pool, fig)
    hb = blur(pool, 5)
    gy, gx = np.gradient(hb)
    spec = 0.3 * np.clip(-gy * 9, 0, 1) ** 1.5 * np.exp(-(Y - GAP) / 200) + np.clip(N2 - 0.78, 0, 1) * 2.5 * pool * np.exp(-(Y - GAP) / 400)
    up = lambda a: cv2.resize(a, (SW, SH), interpolation=cv2.INTER_LINEAR)  # noqa: E731
    return up(ink), up(spec * pool), up(fig)


def door_view(t, zoom=1.0, pan=(0.0, 0.0), feet=('none', 0.0), gap=1.0, amb=1.0, lamp=0.0,
              R=0.0, fig_h=0.0, melt=0.0, eyes=0.0, eye_size=1.0, eye_y=None):
    L = door_layers()
    img = amb * L['A_amb'] + lamp * L['A_lamp']
    kind, k = feet
    g0, e0 = L['gap']['none']
    if kind != 'none' and k > 0:
        g1, e1 = L['gap'][kind]
        img += gap * ((1 - k) * g0 + k * g1) + gap * ((1 - k) * e0 + k * e1)
    else:
        img += gap * (g0 + e0)
    if R > 0 or fig_h > 0:
        ink, spec, fig = puddle_and_figure(t, R, fig_h, melt)
        hall = np.array([0.88, 1.0, 0.86], f32)
        img = img * (1 - ink[..., None]) + ink[..., None] * (0.012 + 0.02 * lamp)
        img += spec[..., None] * hall * gap * 1.6 + (spec * lamp * 0.5)[..., None] * np.array([1, 0.8, 0.55], f32)
        # a thin sheen down its left side once the lamp is on
        if lamp > 0:
            sheen = np.clip(fig - np.roll(fig, -10, axis=1), 0, 1)
            img += (sheen * lamp * 0.25)[..., None] * np.array([1, 0.8, 0.55], f32)
    if eyes > 0:
        cy = eye_y if eye_y is not None else GAP + R * 0.35 - fig_h * 0.905
        r = 10 * eye_size * max(fig_h, 200) / 1100
        Yy, Xx = L['Y'], L['X']
        y0, y1 = int(max(0, cy - 80)), int(min(SH, cy + 80))
        sub = np.zeros((y1 - y0, SW), f32)
        for sx in (-1, 1):
            ex = SW / 2 + sx * max(fig_h, 200) * 0.032 * max(eye_size, 0.6)
            dd = ((Xx[y0:y1] - ex) / (r * 1.25)) ** 2 + ((Yy[y0:y1] - cy) / r) ** 2
            sub = np.maximum(sub, ss(1.15, 0.85, dd))
        glow = blur(sub, 10) * 1.6
        img[y0:y1] += ((sub + glow) * eyes)[..., None] * np.array([0.95, 0.96, 0.9], f32)
    # camera: crop and scale to the frame
    cw, ch = SW / 1.2 / zoom, SH / 1.2 / zoom
    cx, cy = SW / 2 + pan[0], SH / 2 + pan[1]
    M = np.array([[W / cw, 0, -(cx - cw / 2) * W / cw], [0, H / ch, -(cy - ch / 2) * H / ch]], f32)
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


# ====================================================================== the tenant
@lru_cache(None)
def tenant():
    im = np.asarray(Image.open(os.path.join(ROOT, 'assets', 'tenant.png')).convert('RGBA'), f32) / 255
    rgb, a = im[..., :3], im[..., 3]
    h, w = a.shape
    Y, X = np.mgrid[0:h, 0:w].astype(f32)
    lum = rgb @ np.array([0.299, 0.587, 0.114], f32)
    # night: desaturated, a cold key from the door on his right, the clock's red from below
    nrgb = 0.5 * lum[..., None] + 0.5 * rgb
    key = 0.16 + 0.95 * ss(0.15, 0.95, X / w) ** 1.3
    red = 0.22 * np.exp(-(((X - 0.1 * w) / (0.5 * w)) ** 2 + ((Y - h) / (0.7 * h)) ** 2))
    night = nrgb * (key[..., None] * np.array([0.68, 0.82, 1.0], f32) + red[..., None] * np.array([1, 0.18, 0.12], f32))
    night = np.clip(night, 0, 1) ** 1.12
    # lamp: warm, from his left (our left), a little contrast
    lampk = 0.55 + 0.75 * (1 - X / w) ** 1.2
    warm = np.clip(rgb * lampk[..., None] * np.array([1.06, 0.93, 0.76], f32), 0, 1.4)
    warm = np.clip((warm - 0.5) * 1.08 + 0.5, 0, 1.4)
    return night, warm, a


@lru_cache(None)
def wall(kind):
    Y, X = np.mgrid[0:H, 0:W].astype(f32)
    plaster = fbm(H, W, 21)
    alb = np.array([0.46, 0.45, 0.45], f32) * (0.9 + 0.2 * plaster[..., None])
    if kind == 'night':
        stripes = (np.sin((X * 0.5 - Y) * 0.05) > 0.3).astype(f32)
        win = ss(450, 600, X) * ss(150, 300, Y) * (1 - ss(1100, 1300, Y))
        L = (0.07 + 0.25 * blur(stripes * win, 4) + 0.05 * (X / W))[..., None] * np.array([0.7, 0.82, 1.0], f32)
        return alb * L
    r2 = ((X + 180) ** 2 + (Y - 1150) ** 2) / 900 ** 2
    L = (0.25 + 1.3 / (1 + 2.5 * r2))[..., None] * np.array([1.0, 0.78, 0.52], f32)
    return alb * L


def tenant_view(t, cx, cy, s, kind):
    """Place the cutout: crop-space point (cx, cy) at the frame centre, s frame px per photo px."""
    night, warm, a = tenant()
    rgb = night if kind == 'night' else warm
    M = np.array([[s, 0, W / 2 - s * cx], [0, s, H / 2 - s * cy]], f32)
    fr = cv2.warpAffine(rgb, M, (W, H), flags=cv2.INTER_CUBIC, borderValue=(0, 0, 0))
    fa = cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)[..., None]
    # the background moves less than he does
    bs = 1 + (s - 1) * 0.12
    Mb = np.array([[bs, 0, W / 2 * (1 - bs)], [0, bs, H / 2 * (1 - bs)]], f32)
    bg = cv2.warpAffine(wall(kind), Mb, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    sh = blur(np.roll(fa[..., 0], int(55 * s) if kind == 'warm' else -int(20 * s), axis=1), 30 * s)
    bg = bg * (1 - (0.55 if kind == 'warm' else 0.3) * sh[..., None])
    return bg * (1 - fa) + fr * fa


# ====================================================================== the clock
@lru_cache(None)
def clock_layer():
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    segs = {'0': 'abcdef', '3': 'abcdg', '7': 'abc'}
    x0, y0, dw, dh, th = 250, 820, 150, 270, 26

    def seg(x, y, c):
        L = {'a': (x + th, y, x + dw - th, y + th), 'g': (x + th, y + dh / 2 - th / 2, x + dw - th, y + dh / 2 + th / 2),
             'd': (x + th, y + dh - th, x + dw - th, y + dh), 'f': (x, y + th, x + th, y + dh / 2 - th / 2),
             'b': (x + dw - th, y + th, x + dw, y + dh / 2 - th / 2), 'e': (x, y + dh / 2 + th / 2, x + th, y + dh - th),
             'c': (x + dw - th, y + dh / 2 + th / 2, x + dw, y + dh - th)}[c]
        d.rounded_rectangle(L, radius=6, fill=(255, 40, 30, 255))
    for i, ch in enumerate('307'):
        x = x0 + i * (dw + 50) + (60 if i else 0)
        for c in segs[ch]:
            seg(x, y0, c)
    for yy in (y0 + 80, y0 + 190):
        d.ellipse((x0 + dw + 40, yy, x0 + dw + 70, yy + 30), fill=(255, 40, 30, 255))
    return rgba_layer(im)


def clock_view(t):
    base, lit = clock_static()
    return base + lit * ss(0.2, 0.6, t)


@lru_cache(None)
def clock_static():
    """The clock is still; only its digits come on. Built once: dark body, digits with glow, reflection."""
    t = 10.0
    Y, X = np.mgrid[0:H, 0:W].astype(f32)
    img = np.zeros((H, W, 3), f32)
    body = (np.abs(X - 540) < 380) & (np.abs(Y - 955) < 230)
    img[body] = [0.025, 0.022, 0.024]
    rgb, a = clock_layer()
    on = ss(0.2, 0.6, t)
    seg_ = rgb * a * on * 1.6
    img += seg_ + blur(seg_, 18) * 0.9 + blur(seg_, 70) * 0.6
    # the nightstand top, reflecting the digits
    top = Y > 1190
    refl = np.flipud(np.roll(seg_, -(2 * 1190 - H), axis=0))
    img[top] = img[top] * 0 + np.array([0.03, 0.022, 0.018], f32) + blur(refl, 22)[top] * 0.12
    base = np.zeros((H, W, 3), f32)
    base[body] = [0.025, 0.022, 0.024]
    base[top] = [0.03, 0.022, 0.018]
    return base, img - base


# ====================================================================== under the door
@lru_cache(None)
def under_layers():
    Y, X = np.mgrid[0:H, 0:W].astype(f32)
    YH, SL0, SL1 = 700, 778, 796                     # horizon, slit top, slit bottom (= floor line)
    img = np.zeros((H, W, 3), f32)
    door = Y < SL0
    img[door] = (np.array([0.05, 0.048, 0.045], f32) * (0.8 + 0.4 * fbm(H, W, 31, 5, 6)[..., None]))[door]
    slit = (Y >= SL0) & (Y < SL1)
    carpet = fbm(H, W, 32, 4, 40)
    img[slit] = (np.array([2.2, 2.5, 2.1], f32) * (0.7 + 0.5 * carpet[..., None]))[slit]
    fl = Y >= SL1
    z = 135.0 / np.maximum(Y - YH, 1)
    u = (X - W / 2) * z / 1500
    pw = 0.11
    plank = np.floor(u / pw)
    fr = u / pw - plank
    tone = (np.sin(plank * 12.9898) * 43758.5453) % 1
    wood = fbm(H, W, 33, 6, 5)
    alb = np.stack([0.32, 0.21, 0.13]) * (0.75 + 0.35 * tone[..., None]) * (0.85 + 0.3 * wood[..., None])
    seam = np.clip(1 - np.minimum(fr, 1 - fr) / 0.03, 0, 1)
    dist = np.maximum(1.5 - z, 0)
    light = 0.03 + 1.6 * np.exp(-dist / 0.35)
    refl = 1.4 * np.exp(-(Y - SL1) / 70) * (1 - 0.7 * seam)
    hall = np.array([0.88, 1.0, 0.86], f32)
    floor = alb * (1 - 0.6 * seam[..., None]) * light[..., None] * hall + refl[..., None] * hall * 0.5
    img[fl] = floor[fl]
    return img, z, u, fl, (SL0, SL1)


@lru_cache(None)
def card():
    w, h = 760, 980
    im = Image.new('RGBA', (w, h), (236, 228, 210, 255))
    px = np.asarray(im, f32)
    fib = fbm(h, w, 41, 6, 8)
    px[..., :3] *= (0.92 + 0.1 * fib[..., None])
    im = Image.fromarray(np.clip(px, 0, 255).astype(np.uint8), 'RGBA')
    d = ImageDraw.Draw(im)
    ink, red = (30, 28, 34, 255), (170, 24, 22, 255)
    d.text((60, 70), 'THE STILLNESS', font=font('courier', 72), fill=ink)
    d.text((62, 160), 'BUILDING 3 · APT 307 · 3:07 AM', font=font('courier', 28), fill=ink)
    d.line((60, 215, w - 60, 215), fill=ink, width=3)
    y = 260
    for line, c in [('You have been offered', ink), ('the Stillness.', ink), ('', ink), ('Accept or decline', ink),
                    ('by sunrise.', ink), ('', ink), ('§3.2 Silence is', red), ('taken as acceptance.', red)]:
        d.text((60, y), line, font=font('courier', 46), fill=c)
        y += 62
    d.text((60, h - 150), 'Signed: ____________', font=font('courier', 40), fill=ink)
    return np.asarray(im, f32) / 255


def under_view(t):
    """17.0-19.6: floor level. The shoes in the slit, the ink and the envelope coming under."""
    base, z, u, fl, (SL0, SL1) = under_layers()
    img = base.copy()
    # the shoes, black against the slit
    X = np.arange(W, dtype=f32)
    for a, b in [(330, 470), (610, 750)]:
        img[SL0:SL1, a:b] *= 0.04
    # the envelope: a card slid along the floor, projected
    k = expo_out((t - 17.2) / 1.6)
    zf = 1.5 - 0.85 * k
    zn = zf - 0.3
    pts = []
    for uu, zz in [(-0.12, zf), (0.12, zf), (0.12, zn), (-0.12, zn)]:
        pts.append((W / 2 + 1500 * uu / zz, 700 + 135 / zz))
    c = card()
    M = cv2.getPerspectiveTransform(np.float32([[0, 0], [c.shape[1], 0], [c.shape[1], c.shape[0]], [0, c.shape[0]]]), np.float32(pts))
    warped = cv2.warpPerspective(c, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
    ca = warped[..., 3:4] * (np.arange(H)[:, None, None] >= SL1)
    lit = 0.08 + 1.4 * np.exp(-np.maximum(1.5 - (zf + zn) / 2, 0) / 0.35)
    img = img * (1 - ca) + warped[..., :3] * ca * lit * np.array([0.9, 1.0, 0.88], f32)
    # the ink, out from under the door
    if t > 17.5:
        n = ink_noise()[0][: H // 2, : W // 2]
        nn = cv2.resize(n, (W, H))
        zfront = 1.5 - 1.25 * ss(17.5, 20.5, t) ** 0.8
        ink = ss(-0.02, 0.02, z - zfront + 0.18 * (nn - 0.5) * (1.6 - z)) * fl
        refl = np.clip(1.6 * np.exp(-(np.arange(H, dtype=f32)[:, None] - SL1) / 45), 0, 2)
        img = img * (1 - ink[..., None]) + ink[..., None] * (0.01 + refl[..., None] * np.array([0.88, 1.0, 0.86], f32) * 0.6)
    return img


def overhead_view(t):
    """19.6-25: straight down at the envelope on the floorboards; the ink gets there first."""
    Y, X = np.mgrid[0:H, 0:W].astype(f32)
    light = (0.1 + 1.25 * np.exp(-Y / 520))[..., None] * np.array([0.88, 1.0, 0.86], f32)
    floor = overhead_floor()
    img = floor * light
    img[:96] = [0.03, 0.028, 0.026]
    img[96:110] = [2.0, 2.3, 1.9]
    # the card, settling
    c = card()
    k = expo_out((t - 19.6) / 0.9)
    cx, cy, ang = 540, 900 + 80 * k, -9 + 4 * k
    M = cv2.getRotationMatrix2D((c.shape[1] / 2, c.shape[0] / 2), ang, 1.0)
    M[0, 2] += cx - c.shape[1] / 2
    M[1, 2] += cy - c.shape[0] / 2
    wc = cv2.warpAffine(c, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
    ca = wc[..., 3:4]
    shadow = blur(np.roll(np.roll(ca[..., 0], 14, 0), 6, 1), 10)[..., None]
    img = img * (1 - 0.6 * shadow)
    plit = 0.3 + 0.9 * np.exp(-Y / 900)
    img = img * (1 - ca) + wc[..., :3] * ca * plit[..., None] * np.array([0.92, 1.0, 0.9], f32)
    # ink: a ragged front from the gap, faster in the cracks between planks
    n = cv2.resize(ink_noise()[0][: H // 2, : W // 2], (W, H))
    pl = (X % 150) / 150
    crack = np.exp(-((pl - 0.5) / 0.04) ** 2) * 0.0  # planks run across here; keep the front organic
    front = 110 + (t - 19.6) * 165 + 120 * (n - 0.5) + crack
    m = ss(-10, 10, front - Y)
    paper = ca[..., 0]
    soak = ss(-40, 40, (front - 260) - Y + 60 * (n - 0.5)) * paper           # paper drinks it slower, softer
    floor_ink = m * (1 - paper)
    hb = blur(floor_ink, 6)
    gy, gx = np.gradient(hb)
    spec = np.clip(np.sqrt(gx ** 2 + gy ** 2) * 8, 0, 1) ** 2 * np.exp(-Y / 700) * 1.6
    img = img * (1 - floor_ink[..., None]) + floor_ink[..., None] * 0.012 + spec[..., None] * np.array([0.88, 1.0, 0.86], f32)
    img = img * (1 - 0.9 * blur(soak, 3)[..., None])
    return img


@lru_cache(None)
def overhead_floor():
    Y, X = np.mgrid[0:H, 0:W].astype(f32)
    pw = 150
    plank = np.floor(X / pw)
    fr = (X % pw) / pw
    tone = (np.sin(plank * 7.13 + 1) * 43758.5453) % 1
    grain = cv2.resize(fbm(H // 8, W, 51, 6, 6), (W, H))
    alb = np.stack([0.34, 0.22, 0.13]) * (0.75 + 0.35 * tone[..., None]) * (0.8 + 0.4 * grain[..., None])
    seam = np.clip(1 - np.minimum(fr, 1 - fr) / 0.02, 0, 1)
    return alb * (1 - 0.65 * seam[..., None])


# ====================================================================== type
@lru_cache(None)
def caption_layer(text):
    f = font('ExtraBold', 64)
    im = Image.new('RGBA', (W, 220), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    bw = d.textlength(text, font=f)
    d.text(((W - bw) / 2, 60), text, font=f, fill=(255, 255, 255, 255), stroke_width=8, stroke_fill=(0, 0, 0, 255))
    return rgba_layer(im)


@lru_cache(None)
def chat_layer(who, text):
    w, h = 960, 150
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=34, fill=(32, 32, 36, 228))
    d.rounded_rectangle((26, 30, 106, 110), radius=20, fill=(52, 199, 89, 255))
    d.text((44, 46), 'B3', font=font('Black', 36), fill=(255, 255, 255, 255))
    d.text((130, 28), f'Building 3 · {who}', font=font('SemiBold', 30), fill=(235, 235, 240, 255))
    d.text((w - 90, 30), 'now', font=font('Medium', 26), fill=(150, 150, 160, 255))
    d.text((130, 76), text, font=font('Medium', 36), fill=(255, 255, 255, 255))
    return rgba_layer(im)


@lru_cache(None)
def stamp_layer():
    w, h = 640, 330
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (200, 26, 22, 255)
    d.rounded_rectangle((10, 10, w - 10, h - 10), radius=26, outline=col, width=16)
    d.text((48, 36), 'CLAUSE 7:', font=font('Black', 94), fill=col)
    d.text((48, 140), 'NO.', font=font('Black', 150), fill=col)
    rgb, a = rgba_layer(im.rotate(8, resample=Image.BICUBIC, expand=True))
    wear = fbm(a.shape[0], a.shape[1], 61, 6, 10)
    return rgb, a * (0.55 + 0.45 * ss(0.25, 0.5, wear))[..., None]


@lru_cache(None)
def title_layer():
    im = Image.new('RGBA', (W, 900), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for text, f, y, fill in [('307', font('Black', 330), 60, (255, 255, 255, 255)),
                             ('O C C U P I E D', font('ExtraBold', 76), 450, (255, 255, 255, 255)),
                             ('BUILDING 3  ·  NEW TENANT', font('Medium', 34), 580, (210, 200, 185, 255))]:
        bw = d.textlength(text, font=f)
        d.text(((W - bw) / 2, y), text, font=f, fill=fill)
    return rgba_layer(im)


def captions(img, t):
    for t0, t1, text in CAPTIONS:
        if t0 <= t < t1:
            rgb, a = caption_layer(text)
            k = ss(t0, t0 + 0.12, t) * (1 - ss(t1 - 0.15, t1, t))
            img = over(img, rgb, a * k, 0, 1240 - int(16 * (1 - ss(t0, t0 + 0.15, t))))
    return img


# ====================================================================== shots
def shot_at(t):
    for t0, t1, kind in SHOTS:
        if t0 <= t < t1:
            return kind, t - t0
    return SHOTS[-1][2], t - SHOTS[-1][0]


def gap_flicker(t, strength):
    return 1 - strength * (0.5 + 0.5 * np.sign(np.sin(t * 37.0) * np.sin(t * 11.3 + 1) - 0.55))


def frame(t):
    kind, lt = shot_at(t)
    if kind == 'clock':
        img = clock_view(t)
    elif kind == 'door':
        img = door_view(t, zoom=1.0 + 0.1 * ss(4, 11, t), feet=('big', ss(5.0, 5.6, t)), gap=gap_flicker(t, 0.06), pan=(0, 60 * ss(4, 11, t)))
    elif kind == 'face':
        s = 2.1 + 0.16 * ss(11, 17, t)
        img = tenant_view(t, 400, 400, s, 'night')
    elif kind == 'under':
        img = under_view(t) if t < 19.6 else overhead_view(t)
    elif kind == 'rise':
        if 29.2 <= t < 30.3 or 32.1 <= t < 32.9:          # cut to his face, still smiling, in the strobe
            img = tenant_view(t, 410, 380, 2.4, 'night') * (0.55 + 0.45 * gap_flicker(t, 0.6))
        elif t >= 33.6:
            img = np.zeros((H, W, 3), f32)
        else:
            R = 260 + 160 * ss(25, 28, t)
            fh = 1150 * ss(25.6, 28.6, t) ** 1.3
            eyes = ss(27.6, 27.9, t) * (0.0 if 31.0 < t < 31.15 else 1.0)
            img = door_view(t, zoom=1.04 + 0.12 * ss(25, 33.6, t), feet=('big', 1 - ss(25, 26, t)), gap=gap_flicker(t, 0.55),
                            R=R, fig_h=fh, eyes=eyes, amb=0.8, pan=(0, 80))
    elif kind == 'flex':
        k = expo_out((t - FLEX_AT) / 1.0)
        s = 2.4 + (1.12 - 2.4) * k + 0.05 * ss(35, 42, t)
        cx = 400 + (600 - 400) * k
        cy = 400 + ((960 - 470) / s - 400) * k
        img = tenant_view(t, cx, cy, s, 'warm')
        # the end of the bed in the foreground, out of focus: hides where the photo runs out
        fg = ss(1380, 1700, np.arange(H, dtype=f32))[:, None, None]
        img = img * (1 - 0.94 * fg)
    elif kind == 'retreat':
        k = ss(42.6, 47.2, t)
        R = 420 * (1 - ss(45.5, 48.6, t)) + 20
        fh = 1150 * (1 - k) ** 1.6
        eye_y = GAP + 30 if fh < 220 else None
        eyes = 1.0 * (1 - ss(48.4, 48.9, t))
        img = door_view(t, zoom=1.08, lamp=1.0, amb=0.7, R=R if t < 48.8 else 0, fig_h=fh, melt=k,
                        eyes=eyes, eye_size=1.5 - 0.7 * k, eye_y=eye_y, pan=(0, 60))
    else:  # title
        if 57.0 <= t < 58.6:
            img = tenant_view(t, 470, 330, 1.35, 'warm')
        else:
            img = door_view(t, zoom=1.0 + 0.05 * ss(50, 57, t), lamp=0.85, amb=0.6,
                            feet=('small', ss(53.0, 53.3, t) * (1 - ss(56.4, 56.8, t))), pan=(0, 40))
            img = img * (1 - 0.45 * ss(50.3, 51.2, t))
            rgb, a = title_layer()
            img = over(img, rgb, a * ss(50.6, 51.6, t) * (1 - ss(56.6, 57.0, t)), 0, 300)
        img = img * (1 - ss(58.6, 59.4, t))
    # the flash and the stamp
    if FLEX_AT <= t < FLEX_AT + 0.6:
        img = img + 1.3 * (1 - (t - FLEX_AT) / 0.6) ** 2
    if kind == 'flex' and t >= STAMP_AT:
        rgb, a = stamp_layer()
        k = ss(STAMP_AT, STAMP_AT + 0.1, t)
        sc = 1.7 - 0.7 * k
        hh, ww = a.shape[:2]
        rs = cv2.resize(np.dstack([rgb, a]), (int(ww * sc), int(hh * sc)))
        img = over(img, rs[..., :3], rs[..., 3:4] * k * 0.95, (W - rs.shape[1]) // 2, 60 - (rs.shape[0] - hh) // 2)
    if kind == 'retreat':
        for i, (at, who, text) in enumerate(CHAT):
            if t >= at:
                rgb, a = chat_layer(who, text)
                k = expo_out((t - at) / 0.45)
                slot = sum(1 for (a2, _, _) in CHAT if a2 > at and t >= a2)
                img = over(img, rgb, a * k * (1 - ss(49.4, 49.9, t)), 60, int(-160 + (170 + 170 * slot + 140) * k))
    img = captions(img, t)
    return post(img, t)


@lru_cache(None)
def grain_tiles():
    r = np.random.default_rng(99)
    return [cv2.resize(r.standard_normal((H // 2, W // 2)).astype(f32), (W, H)) for _ in range(6)]


@lru_cache(None)
def vignette():
    Y, X = np.mgrid[0:H, 0:W].astype(f32)
    d = ((X - W / 2) / (W * 0.62)) ** 2 + ((Y - H / 2) / (H * 0.6)) ** 2
    return (1 - 0.55 * np.clip(d, 0, 1.4) ** 1.4)[..., None]


def post(img, t):
    # bloom
    hi = np.clip(img - 0.75, 0, None)
    small = cv2.resize(hi, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    img = img + cv2.resize(blur(small, 6) * 0.7 + blur(small, 22) * 0.6, (W, H))
    img = img * vignette()
    # filmic shoulder, a cold lift in the blacks
    img = 1 - np.exp(-img * 1.25)
    img = img * 0.97 + np.array([0.004, 0.008, 0.014], f32)
    # grain
    g = grain_tiles()[int(t * FPS) % 6]
    img = img + g[..., None] * (0.022 + 0.02 * (1 - img))
    # shake on every knock, and a hand that is never quite still
    sh = sum(np.exp(-(t - k) / 0.12) * 7 for k in KNOCKS if t >= k)
    if FLEX_AT <= t:
        sh += np.exp(-(t - FLEX_AT) / 0.2) * 10
    if STAMP_AT <= t:
        sh += np.exp(-(t - STAMP_AT) / 0.15) * 14
    dx = sh * np.sin(t * 91) + 2.2 * np.sin(t * 1.3) + 1.4 * np.sin(t * 2.9 + 1)
    dy = sh * np.cos(t * 77) + 1.8 * np.sin(t * 1.1 + 2)
    M = np.array([[1.02, 0, -W * 0.01 + dx], [0, 1.02, -H * 0.01 + dy]], f32)
    img = cv2.warpAffine(np.clip(img, 0, 1), M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    # a little chromatic fringing
    img[..., 0] = cv2.warpAffine(img[..., 0], np.array([[1.002, 0, -W * 0.001], [0, 1.002, -H * 0.001]], f32), (W, H), borderMode=cv2.BORDER_REFLECT)
    return np.clip(img * 255 + np.random.default_rng(int(t * 1000)).random((H, W, 1)), 0, 255).astype(np.uint8)


if __name__ == '__main__':
    if sys.argv[1] == 'still':
        for a in sys.argv[2:]:
            Image.fromarray(frame(float(a))).save(os.path.join(ROOT, 'out', f'still_{a}.png'))
    else:
        a, b = int(sys.argv[2]), int(sys.argv[3])
        out = os.path.join(ROOT, 'out', f'seg_{a:05d}.mp4')
        ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                               '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '14',
                               '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
        for i in range(a, b):
            ff.stdin.write(frame(i / FPS).tobytes())
            if (i - a) % 60 == 0:
                print(f'{a}: frame {i}', flush=True)
        ff.stdin.close()
        ff.wait()
