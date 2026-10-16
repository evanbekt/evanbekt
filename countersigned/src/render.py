"""COUNTERSIGNED — renders one part. The counterparty is ink: a mirrored field that blooms into shapes
you almost see, and opens its eyes when the price is paid. Every frame is a pure function of time.

    python3 src/render.py PART out/videoPART.mp4 [--stills t1,t2,...]
"""
import functools
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(__file__))
from story import PARTS, SERIES  # noqa: E402

W, H, FPS, DUR = 1080, 1920, 30, 60
PART = int(sys.argv[1])
P = PARTS[PART]
LINES = json.load(open(os.path.join(ROOT, 'out', f'lines{PART}.json')))
FONT = functools.lru_cache(None)(lambda name, size: ImageFont.truetype(os.path.join(ROOT, 'fonts', name), size))
TYPE, TYPEB = 'CourierPrime-Regular.ttf', 'CourierPrime-Bold.ttf'
PAPER = np.array([236, 228, 210], np.float32)
INK = np.array([18, 16, 26], np.float32)
RED = np.array([150, 22, 26], np.float32)


def clamp(x, a=0.0, b=1.0):
    return min(b, max(a, x))


def ramp(x, a, b):
    return clamp((x - a) / (b - a))


def sine(x):
    return 0.5 - 0.5 * np.cos(np.pi * clamp(x))


# ---------------------------------------------------------------- paper
@functools.lru_cache(None)
def paper():
    r = np.random.default_rng(7)
    n = np.asarray(Image.fromarray(r.standard_normal((H // 6, W // 6)).astype(np.float32)).resize((W, H), Image.BICUBIC))
    fib = np.asarray(Image.fromarray(r.standard_normal((H // 2, W // 24)).astype(np.float32)).resize((W, H), Image.BICUBIC))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 1.6)) ** 2)
    a = PAPER[None, None] + (n * 5 + fib * 3)[..., None] - (np.clip(v - 0.7, 0, 1) * 40)[..., None]
    return a.astype(np.float32), (0.86 + 0.14 * np.clip(n * 0.5 + 0.5, 0, 1)).astype(np.float32)


GRAIN = [np.random.default_rng(k).normal(0, 5, (H, W, 1)).astype(np.float32) for k in range(6)]

# ---------------------------------------------------------------- the ink field
LW, LH = 96, 320                       # half width (mirrored), height
AX = np.linspace(0, 1, LW)[None, :].repeat(LH, 0)
V = np.linspace(-1.78, 1.78, LH)[:, None].repeat(LW, 1)


def g(cx, cy, sx, sy, w):
    return w * np.exp(-(((AX - cx) / sx) ** 2 + ((V - cy) / sy) ** 2))


TEMPLATES = {
    'moth': lambda: g(.45, -.3, .35, .28, 1) + g(.35, .38, .25, .3, .8) + g(0, 0, .08, .6, 1) + g(.12, -.85, .04, .25, .6),
    'hourglass': lambda: g(0, -.6, .45, .25, 1) + g(0, .6, .45, .25, 1) + g(0, 0, .06, .2, .9),
    'door': lambda: g(.32, 0, .16, .95, 1) + g(0, -1.0, .45, .08, .8),
    'mouth': lambda: g(0, .1, .78, .2, 1.1) + g(0, -.08, .6, .06, .5) - sum(g(x, .1, .035, .07, .9) for x in (.08, .22, .36, .5)),
    'book': lambda: g(.42, 0, .38, .55, 1.0) - g(0, 0, .03, .6, .6),
    'eye': lambda: g(0, 0, .9, .34, 1.15),
    'bed': lambda: g(0, .55, .85, .17, 1.0) + g(.6, .3, .15, .13, .9),
    'mother': lambda: g(0, -1.1, .14, .16, 1) + g(0, -.2, .22, .75, 1) + g(.45, .25, .07, .9, .8),
    'heart': lambda: g(.26, -.2, .28, .3, 1) + g(0, .28, .3, .42, .9),
    'face': lambda: g(0, -.1, .62, .88, 1.05),
    'hand': lambda: g(0, .35, .36, .36, 1) + g(.12, -.35, .06, .36, .9) + g(.32, -.22, .06, .32, .85) + g(.52, .3, .08, .22, .8),
    'eyes': lambda: g(0, 0, .95, 1.2, 1.0),
}
EYES = {   # (ax, v, size) where the ink opens its eyes at the price
    'hourglass': [(0.0, -0.62, 0.11)], 'mouth': [(0.34, -0.36, 0.09)], 'eye': [(0.0, 0.0, 0.3)],
    'mother': [(0.06, -1.12, 0.045)], 'face': [(0.26, -0.32, 0.12)],
    'eyes': [(0.2, -0.65, 0.08), (0.52, -0.12, 0.07), (0.14, 0.42, 0.09), (0.62, 0.66, 0.06), (0.36, -1.05, 0.07), (0.0, 0.05, 0.1)],
}
FOLD_T, PRICE_T, EYES_T = 42.0, 44.0, 47.0


@functools.lru_cache(None)
def noise_keys(seed):
    from scipy.ndimage import gaussian_filter
    r = np.random.default_rng(seed)
    return [gaussian_filter(r.standard_normal((LH, LW)), 6) * 9 for _ in range(10)]


def noise(t, seed, period=2.6):
    ks = noise_keys(seed)
    x = t / period
    i = int(np.floor(x))
    f = sine(x - i)
    return ks[i % len(ks)] * (1 - f) + ks[(i + 1) % len(ks)] * f


@functools.lru_cache(None)
def template(name):
    return TEMPLATES[name]()


def field(t, name, amp, thr, seed, reveal=None):
    f = template(name) * amp + 0.42 * noise(t, seed) + 0.18 * noise(t * 1.7, seed + 1, 1.3) - thr
    if reveal is not None:                       # the fold: ink spreads out from the crease
        f = f - np.clip(AX - reveal, 0, None) * 6
    full = np.concatenate([f[:, ::-1], f], axis=1)
    return np.asarray(Image.fromarray(full.astype(np.float32)).resize((W, H), Image.BICUBIC))


def ink_onto(a, F, col=INK, opacity=1.0):
    pap, tooth = paper()
    alpha = np.clip(F / 0.035 + 0.5, 0, 1) * tooth
    halo = np.clip((F + 0.09) / 0.09, 0, 1) * 0.22 * (1 - alpha)
    pool = np.clip(F * 1.5, 0, 0.45)
    c = col[None, None] * (1 - pool[..., None]) + 4 * pool[..., None]
    k = (alpha + halo)[..., None] * opacity
    return a * (1 - k) + c * k


def eyes_onto(img, name, openness, t):
    d = ImageDraw.Draw(img)
    for ax, v, s in EYES.get(name, []):
        for sgn in ((1,) if ax == 0 else (-1, 1)):
            cx = W / 2 + sgn * ax * W / 2
            cy = H / 2 + v * W / 2
            rx, ry = s * W / 2, s * W / 2 * 0.6 * openness
            if ry < 1:
                continue
            d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(238, 232, 214))
            pr = min(rx, ry) * 0.55
            jx = np.sin(t * 0.7 + ax * 9) * rx * 0.08
            d.ellipse([cx - pr + jx, cy - pr, cx + pr + jx, cy + pr], fill=(14, 12, 18))
    return img


# ---------------------------------------------------------------- text
def card_text(img, t):
    d = ImageDraw.Draw(img)
    a = ramp(t, 0.3, 1.2)
    col = lambda c: tuple(int(236 + (cc - 236) * a) for cc in c)  # noqa: E731
    d.text((W / 2, 640), SERIES, font=FONT(TYPEB, 54), fill=col((24, 22, 30)), anchor='mm')
    d.text((W / 2, 900), f'CLAUSE {PART}', font=FONT('PermanentMarker-Regular.ttf', 150), fill=col((24, 22, 30)), anchor='mm')
    who = P['name'] if P['apt'] == '—' else f"{P['name']}  ·  APT {P['apt']}"
    d.text((W / 2, 1060), who, font=FONT(TYPEB, 44), fill=col((150, 22, 26)), anchor='mm')
    d.text((W / 2, 1140), 'BUILDING 3', font=FONT(TYPE, 34), fill=col((80, 76, 84)), anchor='mm')
    return img


def contract(img, t):
    d = ImageDraw.Draw(img)
    x0, y0 = 100, 420
    d.text((x0, y0 - 120), f'{SERIES}  ·  BUILDING 3', font=FONT(TYPEB, 30), fill=(70, 66, 74))
    d.line([(x0, y0 - 70), (W - x0, y0 - 70)], fill=(70, 66, 74), width=2)
    lines = P['clause']
    t0, t1 = 21.0, 36.5
    per = (t1 - t0) / len(lines)
    y = y0
    for i, ln in enumerate(lines):
        st = t0 + i * per
        if t < st:
            break
        n = int(len(ln) * ramp(t, st, st + per * 0.8))
        f = FONT(TYPEB if i == 0 else TYPE, 46 if i == 0 else 38)
        # typed left to right; the words that matter come out red
        reds = [r for r in P['red'] if r in ln]
        a_, b_ = (ln.index(reds[0]), ln.index(reds[0]) + len(reds[0])) if reds else (len(ln), len(ln))
        x = x0
        for seg, c, s0 in ((ln[:a_], (28, 26, 34), 0), (ln[a_:b_], (150, 22, 26), a_), (ln[b_:], (28, 26, 34), b_)):
            vis = seg[:max(0, n - s0)]
            if vis:
                d.text((x, y), vis, font=f, fill=c)
            x += f.getlength(seg)
        y += 92 if i == 0 else 76
    # the signature line
    sy = 1210
    d.line([(x0, sy), (W - x0, sy)], fill=(40, 38, 46), width=3)
    d.text((x0, sy + 16), 'SIGNATURE OF SIGNER' if P['signer'] else 'SIGNATURE OF VIEWER', font=FONT(TYPE, 28), fill=(80, 76, 84))
    d.text((W - x0, sy + 16), 'COUNTERSIGNED 3:07 AM', font=FONT(TYPE, 28), fill=(80, 76, 84), anchor='ra')
    return img, sy


def signature(img, t, sy):
    if not P['sig'] or t < 38.5:
        return img
    f = FONT(P['sig_font'], 120 if 'Rock' not in P['sig_font'] else 84)
    layer = Image.new('RGBA', (W, 260), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((160, 30), P['sig'], font=f, fill=(150, 22, 26, 255))
    w = int(W * ramp(t, 38.5, 41.0))
    layer = layer.crop((0, 0, max(1, w), 260))
    img.paste(layer, (0, sy - 210), layer)
    return img


STRIP = (244, 238, 222)


def subtitles(img, t):
    d = ImageDraw.Draw(img)
    for i, l in enumerate(LINES):
        nxt = LINES[i + 1]['t0'] if i + 1 < len(LINES) else 99
        end = min(nxt - 0.05, l['t1'] + 1.2)
        if not (l['t0'] - 0.05 <= t < end):
            continue
        ent = l['kind'] in ('c', 'cw')
        f = FONT(TYPEB, 46)
        words, rows, cur = l['text'].split(' '), [], ''
        for w_ in words:
            trial = (cur + ' ' + w_).strip()
            if f.getlength(trial) > 860 and cur:
                rows.append(cur); cur = w_
            else:
                cur = trial
        rows.append(cur)
        shown = int(len(l['text']) * clamp((t - l['t0']) / max(0.3, (l['t1'] - l['t0']) * 0.85)))
        y = 1440 - (len(rows) - 1) * 64
        left = shown
        for r in rows:
            tw = f.getlength(r)
            x0 = W / 2 - tw / 2
            d.rectangle([x0 - 22, y - 36, x0 + tw + 22, y + 32], fill=STRIP, outline=(150, 22, 26) if ent else (40, 38, 46), width=3 if ent else 2)
            if not ent:
                d.text((x0, y), r[:max(0, left)], font=f, fill=(24, 22, 28), anchor='lm')
            else:
                # the counterparty's words don't sit still
                xs = x0
                for k, ch in enumerate(r[:max(0, left)]):
                    jx = np.sin(t * 23 + k * 1.7) * 2.5
                    jy = np.cos(t * 19 + k * 2.3) * 2.5
                    d.text((xs + jx, y + jy), ch, font=f, fill=(150, 22, 26), anchor='lm')
                    xs += f.getlength(ch)
            left -= len(r) + 1
            y += 64
    return img


def end_card(img, t):
    d = ImageDraw.Draw(img)
    a = ramp(t, 56.0, 56.6)
    if a <= 0:
        return img
    stamp = Image.new('RGBA', (760, 300), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stamp)
    sd.rounded_rectangle([10, 10, 750, 290], 26, outline=(150, 22, 26, int(230 * a)), width=10)
    sd.text((380, 100), 'COUNTERSIGNED', font=FONT(TYPEB, 74), fill=(150, 22, 26, int(230 * a)), anchor='mm')
    sd.text((380, 205), '3:07 AM', font=FONT(TYPEB, 74), fill=(150, 22, 26, int(230 * a)), anchor='mm')
    stamp = stamp.rotate(-9, expand=True, resample=Image.BICUBIC)
    img.paste(stamp, (int(W / 2 - stamp.width / 2), 760), stamp)
    d.text((W / 2, 1180), f'CLAUSE {PART} OF 6', font=FONT(TYPEB, 40), fill=(40, 38, 46), anchor='mm')
    if PART == 6:
        d.text((W / 2, 1250), 'it has your name on it now.', font=FONT('Caveat.ttf', 72), fill=(150, 22, 26), anchor='mm')
    return img


# ---------------------------------------------------------------- frame
def frame(fi):
    t = fi / FPS
    pap, _ = paper()
    a = pap.copy()
    seed = 100 * PART
    phase = 'card' if t < 4 else 'want' if t < 20 else 'clause' if t < PRICE_T else 'price' if t < 56 else 'end'
    if phase == 'card':
        # one drop falls on the paper and spreads, mirrored
        k = ramp(t, 1.6, 3.8)
        if k > 0:
            F = field(t, 'heart', 0.25 + 0.5 * sine(k), 0.95 - 0.25 * sine(k), seed + 5)
            a = ink_onto(a, F, opacity=0.3)
    elif phase == 'want':
        u = sine(ramp(t, 4, 18))
        F = field(t, P['want'], 0.35 + 0.75 * u, 0.62 - 0.2 * u, seed)
        a = ink_onto(a, F)
    elif phase == 'clause':
        F = field(t, P['want'], 1.0, 0.45, seed)
        a = ink_onto(a, F, opacity=0.08)                         # it shows through the paper
        if t >= 41.4:                                            # the signature bleeds
            k = sine(ramp(t, 41.4, FOLD_T + 1.6))
            Fr = field(t, 'heart', 0.6 * k, 0.75 - 0.5 * k, seed + 9)
            a = ink_onto(a, Fr, col=RED, opacity=0.85)
    elif phase in ('price', 'end'):
        k = sine(ramp(t, PRICE_T, PRICE_T + 2.2))
        F = field(t, P['price'], 0.6 + 0.6 * k, 0.5 - 0.12 * k, seed + 50, reveal=1.2 * k)
        a = ink_onto(a, F, opacity=1.0 if phase == 'price' else 1 - 0.85 * ramp(t, 56, 56.8))
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    if phase == 'card':
        img = card_text(img, t)
    if phase == 'clause':
        img, sy = contract(img, t)
        img = signature(img, t, sy)
        if t >= FOLD_T:                                          # the page folds over on itself
            k = ramp(t, FOLD_T, PRICE_T)
            d = ImageDraw.Draw(img, 'RGBA')
            fw = int(W / 2 * sine(k))
            d.rectangle([0, 0, fw, H], fill=(28, 24, 30, int(200 * k)))
            d.rectangle([W - fw, 0, W, H], fill=(28, 24, 30, int(200 * k)))
    if phase in ('price', 'end'):
        d = ImageDraw.Draw(img, 'RGBA')
        d.line([(W / 2, 0), (W / 2, H)], fill=(120, 110, 100, 60), width=2)   # the crease
        op = sine(ramp(t, EYES_T, EYES_T + 1.4)) * (1 - ramp(t, 56, 56.6))
        blink = 1.0 if (t % 5.3) > 0.18 else 0.1
        if op > 0.02:
            img = eyes_onto(img, P['price'], op * blink, t)
    if phase == 'end':
        img = end_card(img, t)
    img = subtitles(img, t)
    out = np.asarray(img, np.float32) + GRAIN[fi % 6]
    return np.clip(out, 0, 255).astype(np.uint8)


if __name__ == '__main__':
    out = sys.argv[2]
    if '--stills' in sys.argv:
        for ts in sys.argv[sys.argv.index('--stills') + 1].split(','):
            Image.fromarray(frame(int(float(ts) * FPS))).save(f'{out}_{float(ts):05.1f}.png')
        sys.exit(0)
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                           '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-maxrate', '3.4M', '-bufsize', '6.8M', '-threads', '2',
                           '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-g', '60', out], stdin=subprocess.PIPE)
    for fi in range(FPS * DUR):
        ff.stdin.write(frame(fi).tobytes())
        if fi % 300 == 0:
            print(f'part {PART}: {fi}/{FPS * DUR}', flush=True)
    ff.stdin.close()
    ff.wait()
    print(f'part {PART}: done')
