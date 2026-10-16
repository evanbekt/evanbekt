"""TRANSFER NEWS — the picture: sports-TV grade, LIVE bug, ticker, stat bars, a gold player card."""
import os
import sys
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from engine import (H, W, back_out, blur, cutout, expo_out, f32, font, main, over, photo_view, post, rgba,  # noqa: E402
                    ss, subtitles, text_layer, timeline)

REEL = os.path.dirname(os.path.abspath(__file__))
TL = timeline(REEL)
BEATS = TL['beats']
NAVY = (12, 22, 54, 255)
GREEN = (0, 230, 118, 255)
GOLD = (236, 196, 92, 255)
RED = (225, 30, 40, 255)
WHITE = (255, 255, 255, 255)
TICKER = ('TRANSFER WINDOW OPEN  •  FREE AGENT, 30  •  HEIGHT 1.90 M  •  STAMINA 99  •  CLIMBS MOUNTAINS ON A BIKE  '
          '•  GYM EVERY WEEK  •  FEE: ONE SWIPE  •  ')


@lru_cache(None)
def bug():
    im = Image.new('RGBA', (W, 120), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((50, 30, 170, 90), radius=10, fill=RED)
    d.text((66, 38), 'LIVE', font=font('Black', 38), fill=WHITE)
    d.rounded_rectangle((180, 30, 590, 90), radius=10, fill=NAVY)
    d.text((200, 40), 'TRANSFER NEWS', font=font('Black', 36), fill=WHITE)
    return rgba(im)


@lru_cache(None)
def ticker_strip():
    f = font('Bold', 36)
    d = ImageDraw.Draw(Image.new('L', (8, 8)))
    tw = int(d.textlength(TICKER, font=f))
    im = Image.new('RGBA', (tw * 2, 70), NAVY)
    dd = ImageDraw.Draw(im)
    dd.text((0, 14), TICKER, font=f, fill=WHITE)
    dd.text((tw, 14), TICKER, font=f, fill=WHITE)
    return rgba(im), tw


@lru_cache(None)
def ticker_label():
    im = Image.new('RGBA', (250, 70), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 249, 69), fill=GREEN)
    d.text((22, 14), 'BREAKING', font=font('Black', 36), fill=NAVY)
    return rgba(im)


def hud(img, t):
    rgb, a = bug()
    img = over(img, rgb, a, 0, 60)
    (srgb, sa), tw = ticker_strip()
    off = int(t * 160) % tw
    img = over(img, srgb[:, off:off + W], sa[:, off:off + W], 0, 1690)
    rgb, a = ticker_label()
    return over(img, rgb, a, 0, 1690)


@lru_cache(None)
def stat_layer(label, value):
    im = Image.new('RGBA', (W, 200), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((60, 20, W - 60, 180), fill=(12, 22, 54, 225))
    d.rectangle((60, 20, 74, 180), fill=GREEN)
    d.text((100, 36), label, font=font('Black', 52), fill=WHITE)
    vf = font('Black', 84)
    d.text((W - 100 - d.textlength(value, font=vf), 34), value, font=vf, fill=GREEN)
    d.rectangle((100, 136, W - 100, 156), fill=(40, 55, 95, 255))
    return rgba(im)


@lru_cache(None)
def banner_layer(text):
    im = Image.new('RGBA', (W, 140), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((60, 20, W - 60, 120), fill=NAVY)
    d.rectangle((60, 20, 74, 120), fill=GREEN)
    d.text((100, 42), text, font=font('Black', 48), fill=WHITE)
    return rgba(im)


@lru_cache(None)
def breaking_layer():
    return text_layer([('BREAKING', font('Black', 190), WHITE, 720), ('NEWS', font('Black', 190), GREEN[:3] + (255,), 910)])


@lru_cache(None)
def stadium():
    Y, X = np.mgrid[0:H, 0:W].astype(f32)
    img = np.zeros((H, W, 3), f32)
    img[:] = np.array([0.02, 0.04, 0.12], f32)
    for lx in (120, 540, 960):
        beam = np.exp(-np.abs(X - lx - (Y - 0) * (lx - 540) / 2600) / 90) * np.exp(-Y / 1600)
        img += beam[..., None] * np.array([0.25, 0.32, 0.5], f32)
        img += np.exp(-np.hypot(X - lx, Y + 40) / 60)[..., None] * np.array([1.2, 1.2, 1.3], f32)
    r = np.random.default_rng(7)
    crowd = blur(r.random((H, W)).astype(f32), 1.5) * (Y > 1250)
    img += crowd[..., None] * 0.08
    return img


@lru_cache(None)
def player_card():
    """A gold player card: the flex cutout, rating, name, six stats."""
    cw, ch = 760, 1080
    im = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
    m = Image.new('L', (cw, ch), 0)
    md = ImageDraw.Draw(m)
    md.polygon([(60, 0), (cw - 60, 0), (cw, 70), (cw, ch - 110), (cw // 2, ch), (0, ch - 110), (0, 70)], fill=255)
    g = np.zeros((ch, cw, 3), f32)
    yy = np.linspace(0, 1, ch, dtype=f32)[:, None, None]
    xx = np.linspace(0, 1, cw, dtype=f32)[None, :, None]
    g[:] = np.array([0.98, 0.86, 0.5], f32) * (1 - yy) + np.array([0.72, 0.52, 0.2], f32) * yy
    g += 0.12 * np.exp(-((xx - yy * 0.7 - 0.1) / 0.08) ** 2)
    rgb, a = cutout()
    s = 620 / rgb.shape[1]
    pr = cv2.resize(rgb, (620, int(rgb.shape[0] * s)))
    pa = cv2.resize(a, (620, int(a.shape[0] * s)))[..., None]
    py, px = 90, 100
    hh = min(pr.shape[0], 560)
    fade = (1 - ss(hh - 160, hh, np.arange(hh, dtype=f32)))[:, None, None]
    g[py:py + hh, px:px + 620] = g[py:py + hh, px:px + 620] * (1 - pa[:hh] * fade) + pr[:hh] * pa[:hh] * fade
    base = Image.fromarray((np.clip(g, 0, 1) * 255).astype(np.uint8), 'RGB').convert('RGBA')
    d = ImageDraw.Draw(base)
    dark = (52, 36, 10, 255)
    d.text((70, 60), '94', font=font('Black', 130), fill=dark)
    d.text((86, 200), 'ST', font=font('Black', 56), fill=dark)
    d.line((90, 660, cw - 90, 660), fill=dark, width=3)
    nf = font('Black', 64)
    name = 'THE TALL ONE'
    d.text(((cw - d.textlength(name, font=nf)) / 2, 672), name, font=nf, fill=dark)
    d.line((90, 760, cw - 90, 760), fill=dark, width=3)
    stats = [('92', 'PAC'), ('99', 'STA'), ('94', 'CLM'), ('93', 'PHY'), ('97', 'VIS'), ('190', 'HGT')]
    for i, (v, k) in enumerate(stats):
        col, row = i // 3, i % 3
        x = 120 + col * 300
        y = 778 + row * 66
        d.text((x, y), v, font=font('Black', 56), fill=dark)
        d.text((x + 120, y + 6), k, font=font('Bold', 48), fill=dark)
    im = base
    im.putalpha(m)
    return rgba(im)


def frame(t):
    bi = next((i for i, b in enumerate(BEATS) if t < b['t1']), len(BEATS) - 1)
    b = BEATS[bi]
    u = (t - b['t0']) / (b['t1'] - b['t0'])
    kind = b['kind']
    if kind == 'breaking':
        img = np.zeros((H, W, 3), f32)
        img[:] = np.array([0.05, 0.09, 0.22], f32)
        X = np.arange(W, dtype=f32)[None, :]
        Y = np.arange(H, dtype=f32)[:, None]
        stripes = ((X + Y * 0.6 + t * 900) % 160 < 70).astype(f32) * 0.06
        img += stripes[..., None] * np.array([1, 0.2, 0.25], f32)
        rgb, a = breaking_layer()
        k = back_out((t - b['t0'] - 0.1) / 0.5)
        sc = 1.6 - 0.6 * min(1, k)
        rs = cv2.resize(np.dstack([rgb, a]), (int(W * sc), int(H * sc)))
        y0, x0 = (rs.shape[0] - H) // 2, (rs.shape[1] - W) // 2
        crop = rs[y0:y0 + H, x0:x0 + W]
        img = img * (1 - crop[..., 3:4]) + crop[..., :3] * crop[..., 3:4]
    elif kind == 'photo':
        img, _ = photo_view(b['img'], b['view'], u, 'broadcast')
        img = img.copy()
        if b.get('stat'):
            label, value, frac = b['stat']
            rgb, a = stat_layer(label, value)
            k = expo_out((t - b['t0'] - 0.3) / 0.5)
            img = over(img, rgb, a * k, int(-W * (1 - k)), 1210)
            fill = expo_out((t - b['t0'] - 0.6) / 1.0) * frac
            x0, x1 = 100, int(100 + (W - 200) * fill)
            img[1210 + 136:1210 + 156, x0:x1] = np.array(GREEN[:3], f32) / 255
        if b.get('banner'):
            rgb, a = banner_layer(b['banner'])
            k = expo_out((t - b['t0'] - 0.3) / 0.5)
            img = over(img, rgb, a * k, int(-W * (1 - k)), 1230)
    elif kind == 'card':
        img = stadium().copy()
        here = b['lines'][0]
        rgb, a = player_card()
        k = expo_out((t - b['t0'] - 0.1) / 0.8)
        flip = abs(np.cos((1 - k) * np.pi * 1.5))
        w_ = max(2, int(a.shape[1] * flip * (0.85 + 0.15 * k)))
        h_ = int(a.shape[0] * (0.85 + 0.15 * k))
        rs = cv2.resize(np.dstack([rgb, a]), (w_, h_))
        img = over(img, rs[..., :3], rs[..., 3:4], (W - w_) // 2, 300 + (a.shape[0] - h_) // 2)
        sparkle = np.exp(-((t - b['t0'] - 0.9) / 0.2) ** 2)
        img += sparkle * 0.5
        rgb, a = text_layer([('HERE WE GO!', font('Black', 120), GOLD, 0, None, 8)], h=170)
        hk = back_out((t - here['t0']) / 0.35) if t >= here['t0'] else 0
        if hk > 0:
            rs = cv2.resize(np.dstack([rgb, a]), (int(W * min(hk, 1.3)), int(170 * min(hk, 1.3))))
            img = over(img, rs[..., :3], rs[..., 3:4], (W - rs.shape[1]) // 2, 140)
    else:  # end
        img = stadium().copy() * 0.7
        rgb, a = text_layer([('TRANSFER WINDOW', font('Black', 96), WHITE, 640), ('OPEN', font('Black', 210), GREEN, 750),
                             ('SWIPE RIGHT', font('Black', 110), GOLD, 1030), ('TO MAKE AN OFFER', font('Black', 70), WHITE, 1150)])
        k = ss(b['t0'], b['t0'] + 0.4, t)
        img = img * (1 - a * k) + rgb * a * k
        img = img * (1 - ss(TL['total'] - 0.7, TL['total'] - 0.1, t))
    if kind != 'breaking' and t - b['t0'] < 0.1:
        img = img + 0.8 * (1 - (t - b['t0']) / 0.1)
    img = hud(img, t)
    img = subtitles(img, t, b['lines'], 1440, {'N': WHITE, 'K': GREEN}, size=48, face='Bold', stroke=6)
    return post(img, t, grain=0.01, vig=0.25, bloom=0.5)


if __name__ == '__main__':
    main(frame, REEL)
