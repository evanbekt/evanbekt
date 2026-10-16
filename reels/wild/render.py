"""WILD SINGLES — the picture: warm nature-doc grade, letterbox, long-lens viewfinder, Latin lower-thirds."""
import os
import sys
from functools import lru_cache

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from engine import (FPS, H, W, blur, expo_out, f32, font, main, over, photo_view, post, ss,  # noqa: E402
                    subtitles, text_layer, timeline)

REEL = os.path.dirname(os.path.abspath(__file__))
TL = timeline(REEL)
BEATS = TL['beats']
BAR = 110
CREAM = (246, 240, 226, 255)


@lru_cache(None)
def mist():
    r = np.random.default_rng(3)
    n = sum(blur(r.random((H // 8 + 40, W // 8 + 40)).astype(f32), s) * (1 / (i + 1)) for i, s in enumerate((2, 5, 10)))
    n = (n - n.min()) / (n.max() - n.min())
    return n


@lru_cache(None)
def title_layer():
    return text_layer([('WILD', font('serif', 260), CREAM, 610), ('SINGLES', font('serif', 170), CREAM, 860),
                       ('Episode one · The Tall One', font('serif-italic', 62), (220, 205, 170, 255), 1080)])


@lru_cache(None)
def end_layer():
    return text_layer([('If you meet one in the wild', font('serif-italic', 66), (220, 205, 170, 255), 560),
                       ('SWIPE RIGHT', font('serif', 170), CREAM, 680),
                       ('slowly. do not startle him.', font('serif-italic', 62), (220, 205, 170, 255), 880),
                       ('WILD SINGLES', font('SemiBold', 30), (200, 190, 170, 255), 1180)])


@lru_cache(None)
def lower_layer(latin, line):
    return text_layer([(latin, font('serif-italic', 76), CREAM, 0, 70, 0),
                       (line.upper(), font('SemiBold', 30), (235, 228, 210, 255), 100, 72, 0)], h=160)


@lru_cache(None)
def viewfinder_layer():
    from PIL import Image, ImageDraw
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = (255, 255, 255, 200)
    m, L = 90, 90
    for (x, y, sx, sy) in [(m, BAR + 60, 1, 1), (W - m, BAR + 60, -1, 1), (m, H - BAR - 60, 1, -1), (W - m, H - BAR - 60, -1, -1)]:
        d.line((x, y, x + sx * L, y), fill=c, width=5)
        d.line((x, y, x, y + sy * L), fill=c, width=5)
    cx, cy = W // 2, H // 2
    d.line((cx - 40, cy, cx + 40, cy), fill=(255, 255, 255, 140), width=3)
    d.line((cx, cy - 40, cx, cy + 40), fill=(255, 255, 255, 140), width=3)
    d.text((W - 360, BAR + 80), '600mm  f/4  ISO 800', font=font('SemiBold', 28), fill=c)
    return np.asarray(im, f32)[..., :3] / 255, np.asarray(im, f32)[..., 3:4] / 255


def rec_layer(t):
    from PIL import Image, ImageDraw
    im = Image.new('RGBA', (420, 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if int(t * 2) % 2 == 0:
        d.ellipse((0, 12, 34, 46), fill=(230, 40, 30, 255))
    fr = int(t * FPS)
    d.text((50, 8), f'REC  00:{fr // (FPS * 60):02d}:{(fr // FPS) % 60:02d}:{fr % FPS:02d}', font=font('SemiBold', 34), fill=(255, 255, 255, 220))
    a = np.asarray(im, f32) / 255
    return a[..., :3], a[..., 3:4]


@lru_cache(None)
def low_shade():
    return ss(1000, 1500, np.arange(H, dtype=f32))[:, None, None]


def frame(t):
    bi = next((i for i, b in enumerate(BEATS) if t < b['t1']), len(BEATS) - 1)
    b = BEATS[bi]
    u = (t - b['t0']) / (b['t1'] - b['t0'])
    kind = b['kind']
    if kind in ('title', 'end'):
        m = mist()
        off = int(t * 12) % 40
        fog = np.repeat(np.repeat(m[off // 2: off // 2 + H // 8, off: off + W // 8], 8, 0), 8, 1)[:H, :W]
        img = (np.array([0.03, 0.05, 0.04], f32) + fog[..., None] * np.array([0.1, 0.13, 0.1], f32))
        rgb, a = title_layer() if kind == 'title' else end_layer()
        k = ss(b['t0'] + 0.2, b['t0'] + 1.4, t) * (1 - ss(b['t1'] - 0.6, b['t1'], t)) if kind == 'title' else ss(b['t0'] + 0.1, b['t0'] + 1.2, t)
        if kind == 'end':
            k *= 1 - ss(TL['total'] - 0.8, TL['total'] - 0.1, t)
        img = img * (1 - a * k) + rgb * a * k
    else:
        img, _ = photo_view(b['img'], b['view'], u, 'doc')
        img = img.copy()
        if b.get('rare'):
            img = img + 0.25 * ss(b['lines'][1]['t0'], b['lines'][1]['t0'] + 1.0, t) * blur(np.clip(img - 0.5, 0, 1), 20)
        if b.get('viewfinder'):
            rgb, a = viewfinder_layer()
            img = over(img, rgb, a)
            rgb, a = rec_layer(t)
            img = over(img, rgb, a, 90, BAR + 70)
        img = img * (1 - 0.55 * low_shade())
        if b.get('lower'):
            at = b['t0'] + 0.7
            k = ss(at, at + 0.6, t) * (1 - ss(b['t1'] - 0.4, b['t1'] - 0.05, t))
            line = int(560 * expo_out((t - at) / 0.8))
            img[1162:1166, 70:70 + line] = img[1162:1166, 70:70 + line] * (1 - k) + k
            rgb, a = lower_layer(*b['lower'])
            img = over(img, rgb, a * k, 0, 1180)
        img = img * (1 - ss(b['t0'], b['t0'] + 0.35, t) * 0 - (1 - ss(b['t0'], b['t0'] + 0.35, t)) * 0.9)   # dip in from black
    img = subtitles(img, t, b['lines'], 1420, {'N': (255, 255, 255, 255), 'K': (255, 225, 150, 255)}, size=44, face='SemiBold', stroke=5)
    img[:BAR] = 0
    img[H - BAR:] = 0
    return post(img, t, grain=0.022, vig=0.35, bloom=0.4)


if __name__ == '__main__':
    main(frame, REEL)
