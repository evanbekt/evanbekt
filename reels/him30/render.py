"""HIM 30 — the picture: a white keynote stage, photos as floating product cards, specs, fine print."""
import os
import sys
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from engine import (H, W, back_out, blur, expo_out, f32, font, main, over, photo, photo_view, post, rgba,  # noqa: E402
                    ss, subtitles, text_layer, timeline, wrap)

REEL = os.path.dirname(os.path.abspath(__file__))
TL = timeline(REEL)
BEATS = TL['beats']
BG = np.array([0.961, 0.961, 0.969], f32)
INK = (29, 29, 31, 255)
GREY = (110, 110, 115, 255)
BLUE = (0, 113, 227, 255)


def stage():
    img = np.empty((H, W, 3), f32)
    img[:] = BG
    return img


@lru_cache(None)
def gradient_word(text, size):
    """Big product name, filled with a deep blue-to-violet gradient."""
    f = font('Black', size)
    d = ImageDraw.Draw(Image.new('L', (8, 8)))
    tw = int(d.textlength(text, font=f)) + 20
    mask = Image.new('L', (tw, int(size * 1.3)), 0)
    ImageDraw.Draw(mask).text((10, 0), text, font=f, fill=255)
    m = np.asarray(mask, f32)[..., None] / 255
    x = np.linspace(0, 1, tw, dtype=f32)[None, :, None]
    col = np.array([0.05, 0.2, 0.75], f32) * (1 - x) + np.array([0.55, 0.15, 0.75], f32) * x
    return np.broadcast_to(col, m.shape[:2] + (3,)).copy(), m


@lru_cache(None)
def mask_round(w, h, r):
    im = Image.new('L', (w, h), 0)
    ImageDraw.Draw(im).rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=255)
    return np.asarray(im, f32)[..., None] / 255


def card(img, name, view, u, cx, cy, w, h, k, rot=0.0):
    """A photo card with rounded corners and a soft shadow, entering with k in [0,1]."""
    ph, M = photo_view(name, view, u, 'clean', w, h)
    m = mask_round(w, h, 44)
    sc = 0.92 + 0.08 * back_out(k)
    y_off = 160 * (1 - expo_out(k))
    R = cv2.getRotationMatrix2D((w / 2, h / 2), rot, sc)
    R[0, 2] += cx - w / 2
    R[1, 2] += cy - h / 2 + y_off
    rgb = cv2.warpAffine(ph, R, (W, H), flags=cv2.INTER_LINEAR)
    a = cv2.warpAffine(m, R, (W, H), flags=cv2.INTER_LINEAR)[..., None] * min(1.0, k * 3)
    sh = blur(np.roll(a[..., 0], 30, axis=0), 34)[..., None]
    img = img * (1 - 0.22 * sh)
    return img * (1 - a) + rgb * a, M, R


@lru_cache(None)
def head_layer(text):
    f = font('Black', 84)
    rows = wrap(text, f, 1010)
    return text_layer([(r, f, INK, 10 + 96 * i) for i, r in enumerate(rows)], h=20 + 96 * len(rows))


@lru_cache(None)
def spec_layer(value, line):
    return text_layer([(value, font('Black', 78), BLUE, 0), (line, font('Medium', 38), GREY, 96)], h=160)


@lru_cache(None)
def intro_layer():
    return text_layer([('Introducing', font('SemiBold', 66), GREY, 700)])


SPECS = [('Model', 'Him 30'), ('Height', '1.90 m'), ('Age', '30'), ('Cardio', 'Running. A lot.'), ('Terrain', 'Mountain bike'),
         ('Strength', 'Gym, every week'), ('Smile', 'Built in'), ('Jars', 'Opened')]


@lru_cache(None)
def spec_rows():
    out = []
    for i, (k, v) in enumerate(SPECS):
        im = Image.new('RGBA', (W, 120), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.line((90, 118, W - 90, 118), fill=(210, 210, 215, 255), width=2)
        d.text((90, 34), k, font=font('Medium', 44), fill=GREY)
        v_f = font('Bold', 50)
        d.text((W - 90 - d.textlength(v, font=v_f), 28), v, font=v_f, fill=INK)
        out.append(rgba(im))
    return out


@lru_cache(None)
def fine_print(text):
    f = font('Medium', 26)
    rows = wrap(text, f, 900)
    return text_layer([(r, f, GREY, 4 + 34 * i) for i, r in enumerate(rows)], h=10 + 34 * len(rows))


def frame(t):
    bi = next((i for i, b in enumerate(BEATS) if t < b['t1']), len(BEATS) - 1)
    b = BEATS[bi]
    u = (t - b['t0']) / (b['t1'] - b['t0'])
    kind = b['kind']
    img = stage()
    if kind == 'intro':
        l1, l2 = b['lines']
        rgb, a = intro_layer()
        k1 = ss(l1['t0'] - 0.1, l1['t0'] + 0.5, t) * (1 - ss(l2['t0'] - 0.4, l2['t0'] - 0.1, t))
        img = img * (1 - a * k1) + rgb * a * k1
        rgb, a = gradient_word('Him 30', 250)
        k2 = ss(l2['t0'] - 0.1, l2['t0'] + 0.6, t)
        sc = 0.9 + 0.1 * expo_out((t - l2['t0'] + 0.1) / 0.9)
        rs = cv2.resize(np.dstack([rgb, a]), (int(a.shape[1] * sc), int(a.shape[0] * sc)))
        img = over(img, rs[..., :3], rs[..., 3:4] * k2, (W - rs.shape[1]) // 2, 820 - rs.shape[0] // 2)
    elif kind in ('card', 'pair'):
        k = (t - b['t0']) / 0.7
        rgb, a = head_layer(b['head'])
        hk = ss(b['t0'] + 0.1, b['t0'] + 0.6, t)
        img = over(img, rgb, a * hk, 0, 170 + int(30 * (1 - hk)))
        if kind == 'card':
            img, M, R = card(img, b['img'], b['view'], u, W // 2, 930, 820, 1120, k)
            if b.get('ruler'):
                p = photo('mirror')
                ph_h = p.shape[0]
                y_head, y_feet = M[1, 1] * 0.274 * ph_h + M[1, 2], M[1, 1] * 0.846 * ph_h + M[1, 2]
                y_head, y_feet = R[1, 1] * y_head + R[1, 2], R[1, 1] * y_feet + R[1, 2]
                kk = expo_out((t - b['t0'] - 0.6) / 1.2)
                top = y_feet - (y_feet - y_head) * kk
                x = 980
                img[int(top):int(y_feet), x - 3:x + 3] = np.array(BLUE[:3], f32) / 255
                for yy in (int(top), int(y_feet)):
                    img[yy - 3:yy + 3, x - 26:x + 26] = np.array(BLUE[:3], f32) / 255
        else:
            for j, (name, cx, rot) in enumerate(zip(b['imgs'], (300, 780), (3.5, -3.0))):
                src = (0.33, 0.5, 1.0) if name == 'rooftop' else (0.36, 0.55, 1.0)
                img, _, _ = card(img, name, (src, src[:2] + (1.08,)), u, cx, 900 + 60 * j, 470, 840, k - 0.25 * j, rot)
        if b.get('spec'):
            rgb, a = spec_layer(*b['spec'])
            sk = ss(b['t0'] + 0.8, b['t0'] + 1.2, t)
            img = over(img, rgb, a * sk, 0, 1530 + int(20 * (1 - sk)))
    elif kind == 'specs':
        rgb, a = head_layer('Tech specs')
        img = over(img, rgb, a * ss(b['t0'], b['t0'] + 0.4, t), 0, 210)
        for i, (rgb, a) in enumerate(spec_rows()):
            k = expo_out((t - b['t0'] - 0.3 - i * 0.28) / 0.5)
            img = over(img, rgb, a * k, int(60 * (1 - k)), 400 + i * 128)
    else:  # end
        n1, kfine, n2 = b['lines']
        rgb, a = head_layer('Swipe right to pre-order.')
        img = over(img, rgb, a * ss(b['t0'], b['t0'] + 0.5, t), 0, 640)
        rgb, a = gradient_word('Him 30', 120)
        img = over(img, rgb, a * ss(b['t0'], b['t0'] + 0.5, t), (W - a.shape[1]) // 2, 400)
        rgb, a = fine_print(kfine['text'])
        img = over(img, rgb, a * ss(kfine['t0'] - 0.2, kfine['t0'] + 0.2, t), 0, 1000)
        img = img * (1 - ss(TL['total'] - 0.7, TL['total'] - 0.1, t)) + BG * 0
    colors = {'N': INK, 'K': GREY}
    if kind != 'end':
        img = subtitles(img, t, b['lines'], 1700, colors, size=40, face='SemiBold', stroke=0)
    else:
        img = subtitles(img, t, [l for l in b['lines'] if l['who'] == 'N'], 1700, colors, size=40, face='SemiBold', stroke=0)
    return post(img, t, grain=0.006, vig=0.0, bloom=0.0)


if __name__ == '__main__':
    main(frame, REEL)
