"""Shared picture engine for the profile reels: photos, grades, type, post, and the render CLI.

Each reel (wild/, him30/, transfer/) has story.py (beats and voices), render.py (its frame(t),
built from these pieces) and score.py. The timeline comes from voice.py: out/timeline.json.
"""
import json
import os
import subprocess
import sys
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
f32 = np.float32
INTER = '/usr/share/fonts/opentype/inter/Inter-{}.otf'
SERIF = os.path.join(HERE, '..', 'stillness-saga', 'fonts', 'InstrumentSerif-{}.ttf')


def font(name, size):
    if name in ('serif', 'serif-italic'):
        return ImageFont.truetype(SERIF.format('Italic' if name.endswith('italic') else 'Regular'), size)
    return ImageFont.truetype(INTER.format(name), size)


def ss(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def expo_out(x):
    x = float(np.clip(x, 0, 1))
    return 1 - 2 ** (-10 * x) if x < 1 else 1.0


def back_out(x):
    x = float(np.clip(x, 0, 1)) - 1
    return 1 + 2.2 * x ** 3 + 1.2 * x ** 2


def blur(x, s):
    return cv2.GaussianBlur(x, (0, 0), s)


def rgba(im):
    a = np.asarray(im, f32) / 255
    return a[..., :3], a[..., 3:4]


def over(dst, rgb, a, x=0, y=0):
    h, w = a.shape[:2]
    x, y = int(x), int(y)
    x0, y0, x1, y1 = max(0, x), max(0, y), min(dst.shape[1], x + w), min(dst.shape[0], y + h)
    if x1 > x0 and y1 > y0:
        rs, as_ = rgb[y0 - y:y1 - y, x0 - x:x1 - x], a[y0 - y:y1 - y, x0 - x:x1 - x]
        dst[y0:y1, x0:x1] = dst[y0:y1, x0:x1] * (1 - as_) + rs * as_
    return dst


def text_layer(lines, w=W, h=None, align='center', pad=0):
    """lines: [(text, font, fill, y, x?, stroke?)] onto a transparent layer; cached by the caller."""
    h = h or H
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for spec in lines:
        text, f, fill, y = spec[:4]
        x = spec[4] if len(spec) > 4 and spec[4] is not None else None
        stroke = spec[5] if len(spec) > 5 else 0
        tw = d.textlength(text, font=f)
        if x is None:
            x = (w - tw) / 2 if align == 'center' else pad
        d.text((x, y), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
    return rgba(im)


def wrap(text, f, width):
    d = ImageDraw.Draw(Image.new('L', (8, 8)))
    rows, cur = [], ''
    for w_ in text.split():
        trial = (cur + ' ' + w_).strip()
        if d.textlength(trial, font=f) > width and cur:
            rows.append(cur)
            cur = w_
        else:
            cur = trial
    return rows + [cur]


# ---------------------------------------------------------------- photos and grades
def _grade(img, kind):
    lum = (img @ np.array([0.299, 0.587, 0.114], f32))[..., None]
    if kind == 'doc':        # warm, soft, a little faded like broadcast nature footage
        img = img * np.array([1.04, 1.0, 0.92], f32) + 0.025
        img = 0.1 * lum + 0.9 * img
        img = (img - 0.5) * 0.98 + 0.5
    elif kind == 'clean':    # bright and neutral, product-shot clean
        img = (img - 0.5) * 1.06 + 0.52
        img = 0.04 * lum + 0.96 * img
    elif kind == 'broadcast':  # punchy, cool, saturated like sports TV
        img = img + (img - lum) * 0.22
        img = (img - 0.5) * 1.14 + 0.5
        img = img * np.array([0.97, 1.0, 1.05], f32)
    return np.clip(img, 0, 1)


@lru_cache(None)
def photo(name, grade='none'):
    im = np.asarray(Image.open(os.path.join(HERE, 'assets', f'{name}.jpg')).convert('RGB'), f32) / 255
    return _grade(im, grade) if grade != 'none' else im


def view_matrix(name, cx, cy, z, w_=W, h_=H):
    p = photo(name)
    h, w = p.shape[:2]
    s = max(w_ / w, h_ / h) * z
    hw, hh = w_ / (2 * s), h_ / (2 * s)
    px = float(np.clip(cx * w, hw, w - hw))
    py = float(np.clip(cy * h, hh, h - hh))
    return np.array([[s, 0, w_ / 2 - s * px], [0, s, h_ / 2 - s * py]], f32)


def photo_view(name, view, u, grade, w_=W, h_=H):
    a, b = view
    k = ss(0, 1, u)
    cx, cy, z = [a[i] + (b[i] - a[i]) * k for i in range(3)]
    M = view_matrix(name, cx, cy, z, w_, h_)
    return cv2.warpAffine(photo(name, grade), M, (w_, h_), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT), M


@lru_cache(None)
def cutout():
    im = np.asarray(Image.open(os.path.join(HERE, 'assets', 'flex.png')).convert('RGBA'), f32) / 255
    return im[..., :3], im[..., 3]


# ---------------------------------------------------------------- subtitles
@lru_cache(None)
def subtitle(text, fill, size=48, face='Bold', stroke=6, width=920):
    f = font(face, size)
    rows = wrap(text, f, width)
    lh = int(size * 1.28)
    specs = [(r, f, fill, 10 + i * lh, None, stroke) for i, r in enumerate(rows)]
    return text_layer(specs, h=20 + lh * len(rows))


def subtitles(img, t, lines, y, colors, size=48, face='Bold', stroke=6):
    for i, ln in enumerate(lines):
        end = ln['t1'] + 0.3 if i == len(lines) - 1 else min(ln['t1'] + 0.3, lines[i + 1]['t0'] - 0.06)
        if ln['t0'] - 0.05 <= t < end:
            rgb, a = subtitle(ln['text'], colors.get(ln['who'], (255, 255, 255, 255)), size, face, stroke)
            img = over(img, rgb, a * ss(ln['t0'] - 0.05, ln['t0'] + 0.08, t), 0, y)
    return img


# ---------------------------------------------------------------- post
@lru_cache(None)
def grain_tiles():
    r = np.random.default_rng(5)
    return [cv2.resize(r.standard_normal((H // 2, W // 2)).astype(f32), (W, H)) for _ in range(6)]


@lru_cache(None)
def vignette(strength):
    Y, X = np.mgrid[0:H, 0:W].astype(f32)
    d = ((X - W / 2) / (W * 0.7)) ** 2 + ((Y - H / 2) / (H * 0.65)) ** 2
    return (1 - strength * np.clip(d, 0, 1.5) ** 1.5)[..., None]


@lru_cache(None)
def dither():
    return [np.random.default_rng(i).random((H, W, 1)).astype(f32) for i in range(4)]


def post(img, t, grain=0.018, vig=0.4, bloom=0.6):
    if bloom:
        hi = np.clip(img - 0.8, 0, None)
        small = cv2.resize(hi, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        img = img + cv2.resize(blur(small, 8), (W, H)) * bloom
    if vig:
        img = img * vignette(vig)
    if grain:
        img = img + grain_tiles()[int(t * FPS) % 6][..., None] * grain
    return np.clip(np.clip(img, 0, 1) * 255 + dither()[int(t * FPS) % 4], 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- timeline and CLI
def timeline(reel_dir):
    return json.load(open(os.path.join(reel_dir, 'out', 'timeline.json')))


def beat_at(beats, t):
    for i, b in enumerate(beats):
        if t < b['t1']:
            return i, b
    return len(beats) - 1, beats[-1]


def main(frame, reel_dir):
    out_dir = os.path.join(reel_dir, 'out')
    if sys.argv[1] == 'still':
        for a in sys.argv[2:]:
            Image.fromarray(frame(float(a))).save(os.path.join(out_dir, f'still_{a}.png'))
        return
    a, b = int(sys.argv[2]), int(sys.argv[3])
    out = os.path.join(out_dir, f'seg_{a:05d}.mp4')
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                           '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '12',
                           '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
    for i in range(a, b):
        ff.stdin.write(frame(i / FPS).tobytes())
        if (i - a) % 90 == 0:
            print(f'{a}: frame {i}', flush=True)
    ff.stdin.close()
    ff.wait()
