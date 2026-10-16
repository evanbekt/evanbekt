"""THE TALL ONE — the picture. Every frame is a function of t and out/timeline.json.

    python3 src/render.py seg START END     frames [START, END) -> out/seg_START.mp4
    python3 src/render.py still T [T ...]   out/still_T.png

His photos, graded like a trailer (teal shadows, warm skin), slow pushes, a flash on every cut,
character tags, a height ruler, subtitles for both voices, black trailer cards and a rating card.
"""
import json
import os
import subprocess
import sys
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.join(os.path.dirname(__file__), '..')
W, H, FPS = 1080, 1920, 30
f32 = np.float32
INTER = '/usr/share/fonts/opentype/inter/Inter-{}.otf'
SERIF = os.path.join(ROOT, '..', 'stillness-saga', 'fonts', 'InstrumentSerif-Regular.ttf')
TL = json.load(open(os.path.join(ROOT, 'out', 'timeline.json')))
BEATS = TL['beats']
YELLOW = (255, 214, 64)


def font(name, size):
    return ImageFont.truetype(SERIF if name == 'serif' else INTER.format(name), size)


def ss(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def expo_out(x):
    x = float(np.clip(x, 0, 1))
    return 1 - 2 ** (-10 * x) if x < 1 else 1.0


def blur(x, s):
    return cv2.GaussianBlur(x, (0, 0), s)


def rgba(im):
    a = np.asarray(im, f32) / 255
    return a[..., :3], a[..., 3:4]


def over(dst, rgb, a, x=0, y=0):
    h, w = a.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 > x0 and y1 > y0:
        rs, as_ = rgb[y0 - y:y1 - y, x0 - x:x1 - x], a[y0 - y:y1 - y, x0 - x:x1 - x]
        dst[y0:y1, x0:x1] = dst[y0:y1, x0:x1] * (1 - as_) + rs * as_
    return dst


# ---------------------------------------------------------------- photos
@lru_cache(None)
def photo(name):
    im = Image.open(os.path.join(ROOT, 'assets', f'{name}.jpg')).convert('RGB')
    return np.asarray(im, f32) / 255


def grade(img):
    """Trailer grade: a bit of contrast, teal in the shadows, warmth in the mids and highlights."""
    lum = img @ np.array([0.299, 0.587, 0.114], f32)
    l3 = lum[..., None]
    img = img + (np.array([-0.03, 0.01, 0.045], f32) * (1 - l3) ** 2 + np.array([0.04, 0.012, -0.03], f32) * l3)
    img = 0.12 * l3 + 0.88 * img
    img = (img - 0.5) * 1.12 + 0.5
    return np.clip(img, 0, 1)


def view_matrix(name, cx, cy, z):
    p = photo(name)
    h, w = p.shape[:2]
    s = max(W / w, H / h) * z
    hw, hh = W / (2 * s), H / (2 * s)
    px = float(np.clip(cx * w, hw, w - hw))
    py = float(np.clip(cy * h, hh, h - hh))
    return np.array([[s, 0, W / 2 - s * px], [0, s, H / 2 - s * py]], f32)


def photo_view(name, view, u):
    (a, b) = view
    k = ss(0, 1, u)
    cx, cy, z = [a[i] + (b[i] - a[i]) * k for i in range(3)]
    M = view_matrix(name, cx, cy, z)
    img = cv2.warpAffine(photo(name), M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    return grade(img), M


# ---------------------------------------------------------------- type
@lru_cache(None)
def card_layer(lines):
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    big = len(lines) == 1
    f = font('serif', 150 if big else 96)
    total = len(lines) * (170 if big else 118)
    y = H / 2 - total / 2
    for line in lines:
        spaced = ' '.join(line) if big else line
        tw = d.textlength(spaced, font=f)
        d.text(((W - tw) / 2, y), spaced, font=f, fill=(244, 238, 226, 255))
        y += 170 if big else 118
    return rgba(im)


@lru_cache(None)
def subtitle_layer(text, who):
    f = font('Bold', 50)
    im = Image.new('RGBA', (W, 260), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    words, rows, cur = text.split(), [], ''
    for w_ in words:
        trial = (cur + ' ' + w_).strip()
        if d.textlength(trial, font=f) > 900 and cur:
            rows.append(cur)
            cur = w_
        else:
            cur = trial
    rows.append(cur)
    fill = (255, 255, 255, 255) if who == 'N' else YELLOW + (255,)
    y = 20
    for r in rows:
        tw = d.textlength(r, font=f)
        d.text(((W - tw) / 2, y), r, font=f, fill=fill, stroke_width=6, stroke_fill=(0, 0, 0, 255))
        y += 64
    return rgba(im)


@lru_cache(None)
def tag_layer(title, sub):
    f1, f2 = font('Black', 74), font('SemiBold', 36)
    im = Image.new('RGBA', (W, 220), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    tw = d.textlength(title, font=f1)
    d.rectangle((60, 30, 60 + tw + 56, 140), fill=YELLOW + (255,))
    d.text((88, 38), title, font=f1, fill=(16, 16, 18, 255))
    d.text((64, 156), sub.upper(), font=f2, fill=(255, 255, 255, 255), stroke_width=4, stroke_fill=(0, 0, 0, 200))
    return rgba(im)


@lru_cache(None)
def title_layer():
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for text, f, y, fill in [('THE', font('serif', 120), 640, (244, 238, 226, 255)),
                             ('TALL ONE', font('serif', 210), 760, (244, 238, 226, 255)),
                             ('1.90 M  ·  30  ·  RUNS  ·  RIDES  ·  LIFTS', font('SemiBold', 34), 1030, (220, 205, 170, 255))]:
        tw = d.textlength(text, font=f)
        d.text(((W - tw) / 2, y), text, font=f, fill=fill)
    return rgba(im)


@lru_cache(None)
def rating_layer():
    im = Image.new('RGBA', (W, H), (24, 82, 44, 255))
    d = ImageDraw.Draw(im)
    white = (240, 245, 240, 255)
    for text, f, y in [('THE FOLLOWING PREVIEW', font('Bold', 52), 380),
                       ('HAS BEEN APPROVED FOR', font('Bold', 52), 448),
                       ('ALL APPROPRIATE SWIPERS', font('Bold', 52), 516)]:
        tw = d.textlength(text, font=f)
        d.text(((W - tw) / 2, y), text, font=f, fill=white)
    d.rectangle((90, 680, W - 90, 1120), outline=white, width=6)
    d.rectangle((90, 680, 330, 1120), fill=white)
    d.text((140, 760), 'R', font=font('Black', 250), fill=(24, 82, 44, 255))
    d.text((370, 712), 'RESTRICTED', font=font('Black', 62), fill=white)
    y = 812
    for line in ['for running, riding,', 'repeated gym visits', 'and being 1.90 m tall']:
        d.text((370, y), line, font=font('SemiBold', 44), fill=white)
        y += 60
    for text, f, y in [('COMING SOON', font('Black', 80), 1320), ('TO YOUR PHONE', font('Bold', 52), 1420)]:
        tw = d.textlength(text, font=f)
        d.text(((W - tw) / 2, y), text, font=f, fill=white)
    return rgba(im)


# ---------------------------------------------------------------- the ruler, on the mirror shot
def ruler(img, M, k, t_count):
    """A tape from his shoes to the top of his head, counting up to 1.90."""
    _, ph_h = photo('mirror').shape[1], photo('mirror').shape[0]
    head, feet = 0.274 * ph_h, 0.846 * ph_h
    y_head = M[1, 1] * head + M[1, 2]
    y_feet = M[1, 1] * feet + M[1, 2]
    x = 905
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    top = y_feet - (y_feet - y_head) * k
    d.line((x, y_feet, x, top), fill=YELLOW + (255,), width=8)
    for i in range(20):
        yy = y_feet - (y_feet - y_head) * i / 19
        if yy >= top - 1:
            ln = 46 if i % 5 == 0 else 24
            d.line((x - ln, yy, x, yy), fill=YELLOW + (255,), width=5 if i % 5 == 0 else 3)
    d.line((x - 70, top, x + 10, top), fill=YELLOW + (255,), width=6)
    val = 1.90 * t_count
    label = f'{val:.2f} m'
    f = font('Black', 72)
    tw = d.textlength(label, font=f)
    d.text((x - tw - 70, top - 50), label, font=f, fill=(255, 255, 255, 255), stroke_width=6, stroke_fill=(0, 0, 0, 255))
    if t_count >= 1:
        d.text((x - 300, top + 34), 'WITH SHOES ON. STILL.', font=font('Bold', 30), fill=YELLOW + (255,), stroke_width=4, stroke_fill=(0, 0, 0, 255))
    rgb, a = rgba(im)
    return over(img, rgb, a)


# ---------------------------------------------------------------- the flex poster
@lru_cache(None)
def flex_assets():
    im = np.asarray(Image.open(os.path.join(ROOT, 'assets', 'flex.png')).convert('RGBA'), f32) / 255
    rgb, a = im[..., :3], im[..., 3]
    Y, X = np.mgrid[0:H, 0:W].astype(f32)
    bg = np.zeros((H, W, 3), f32)
    g = Y / H
    bg[:] = (np.array([0.05, 0.12, 0.16], f32) * (1 - g[..., None]) + np.array([0.35, 0.16, 0.06], f32) * g[..., None])
    # light from behind him, top left: rays
    ang = np.arctan2(Y - 380, X - 260)
    rays = (0.5 + 0.5 * np.cos(ang * 22)) ** 6 * np.exp(-np.hypot(X - 260, Y - 380) / 900)
    bg += rays[..., None] * np.array([1.0, 0.75, 0.45], f32) * 0.5
    bg += np.exp(-np.hypot(X - 260, Y - 380) / 260)[..., None] * np.array([1.2, 0.9, 0.6], f32) * 0.8
    return rgb, a, bg


def flex_view(u):
    rgb, a, bg = flex_assets()
    s = 0.98 + 0.06 * ss(0, 1, u)
    h = rgb.shape[0]
    cy = h - (H / 2) / s
    M = np.array([[s, 0, W / 2 - s * 570], [0, s, H / 2 - s * cy]], f32)
    fr = cv2.warpAffine(rgb, M, (W, H), flags=cv2.INTER_CUBIC)
    fa = cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_LINEAR)[..., None]
    lit = np.clip(fr * 1.05 + 0.02, 0, 1)
    # rim light on his left edge, from the glow behind
    rim = np.clip(fa[..., 0] - np.roll(fa[..., 0], 14, axis=1), 0, 1)
    img = bg * (1 - fa) + lit * fa
    img += blur(rim, 3)[..., None] * np.array([1.0, 0.8, 0.55], f32) * 0.7
    floor = ss(1380, 1720, np.arange(H, dtype=f32))[:, None, None]
    return grade(img * (1 - 0.9 * floor) + floor * 0.0)


# ---------------------------------------------------------------- frames
MONTAGE = ['cistern', 'mtb', 'river', 'table', 'rooftop', 'bridge', 'mirror']


def beat_at(t):
    for i, b in enumerate(BEATS):
        if t < b['t1']:
            return i, b
    return len(BEATS) - 1, BEATS[-1]


def frame(t):
    bi, b = beat_at(max(t, BEATS[0]['t0']))
    u = (t - b['t0']) / (b['t1'] - b['t0'])
    kind = b['kind']
    img = np.zeros((H, W, 3), f32)
    if kind == 'card':
        rgb, a = card_layer(tuple(b['text']))
        sc = 1.0 + 0.06 * u
        M = np.array([[sc, 0, W / 2 * (1 - sc)], [0, sc, H / 2 * (1 - sc)]], f32)
        layer = cv2.warpAffine(np.dstack([rgb, a]), M, (W, H), flags=cv2.INTER_LINEAR)
        k = ss(b['t0'], b['t0'] + 0.5, t) * (1 - ss(b['t1'] - 0.35, b['t1'], t))
        img = layer[..., :3] * layer[..., 3:4] * k
        # a light sweep across the type
        sweep = np.exp(-((np.arange(W, dtype=f32)[None, :] - (-200 + 1500 * u)) / 120) ** 2)
        img = img * (1 + 1.2 * sweep[..., None])
    elif kind == 'photo':
        img, M = photo_view(b['img'], b['view'], u)
        if b.get('ruler'):
            n0 = b['lines'][0]
            k = expo_out((t - n0['t0']) / 1.6)
            img = ruler(img, M, k, k)
    elif kind == 'flex':
        img = flex_view(u)
    elif kind == 'title':
        mont = 1.4
        if t < b['t0'] + mont:
            i = int((t - b['t0']) * FPS / 5) % len(MONTAGE)
            name = MONTAGE[i]
            src = next(x for x in BEATS if x.get('img') == name)
            img, _ = photo_view(name, src['view'], 1.0)
            img = img * 0.85
        else:
            rgb, a = title_layer()
            k = ss(b['t0'] + mont, b['t0'] + mont + 0.4, t)
            sc = 1.06 - 0.06 * expo_out((t - b['t0'] - mont) / 0.6)
            M = np.array([[sc, 0, W / 2 * (1 - sc)], [0, sc, H / 2 * (1 - sc)]], f32)
            layer = cv2.warpAffine(np.dstack([rgb, a]), M, (W, H), flags=cv2.INTER_LINEAR)
            img = layer[..., :3] * layer[..., 3:4] * k
            flare = np.exp(-((np.arange(H, dtype=f32)[:, None] - 905) / 7) ** 2) * np.exp(-((np.arange(W, dtype=f32)[None, :] - W / 2) / 420) ** 2)
            img += (flare * k * (1.2 - 0.6 * u))[..., None] * np.array([1.0, 0.8, 0.5], f32)
    else:  # rating
        rgb, a = rating_layer()
        img = rgb * ss(b['t0'], b['t0'] + 0.25, t)
        img = img * (1 - ss(TL['total'] - 1.0, TL['total'] - 0.2, t))
    # cut flash on every photo / flex shot
    if kind in ('photo', 'flex') and t - b['t0'] < 0.12:
        img = img + 1.0 * (1 - (t - b['t0']) / 0.12)
    if kind == 'title' and t < b['t0'] + 1.4 and ((t - b['t0']) * FPS) % 5 < 1:
        img = img + 0.6
    # the character tag
    if b.get('tag'):
        rgb, a = tag_layer(*b['tag'])
        at = b['t0'] + 0.45
        k = expo_out((t - at) / 0.4)
        img = over(img, rgb, a * k * (1 - ss(b['t1'] - 0.2, b['t1'], t)), int(-500 * (1 - k)), 230)
    # subtitles
    for i, ln in enumerate(b['lines']):
        end = ln['t1'] + 0.3 if i == len(b['lines']) - 1 else min(ln['t1'] + 0.3, b['lines'][i + 1]['t0'] - 0.06)
        if ln['t0'] - 0.05 <= t < end:
            rgb, a = subtitle_layer(ln['text'], ln['who'])
            k = ss(ln['t0'] - 0.05, ln['t0'] + 0.08, t)
            img = over(img, rgb, a * k, 0, 1560 if kind == 'rating' else 1380)
    return post(img, t)


@lru_cache(None)
def grain_tiles():
    r = np.random.default_rng(5)
    return [cv2.resize(r.standard_normal((H // 2, W // 2)).astype(f32), (W, H)) for _ in range(6)]


@lru_cache(None)
def vignette():
    Y, X = np.mgrid[0:H, 0:W].astype(f32)
    d = ((X - W / 2) / (W * 0.7)) ** 2 + ((Y - H / 2) / (H * 0.65)) ** 2
    return (1 - 0.4 * np.clip(d, 0, 1.5) ** 1.5)[..., None]


def post(img, t):
    hi = np.clip(img - 0.8, 0, None)
    small = cv2.resize(hi, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    img = img + cv2.resize(blur(small, 8), (W, H)) * 0.6
    img = img * vignette()
    img = img + grain_tiles()[int(t * FPS) % 6][..., None] * 0.018
    img = np.clip(img, 0, 1)
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
            if (i - a) % 90 == 0:
                print(f'{a}: frame {i}', flush=True)
        ff.stdin.close()
        ff.wait()
