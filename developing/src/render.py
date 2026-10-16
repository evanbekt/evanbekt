"""DEVELOPING — renders one part to H.264. Every frame is a pure function of time.

    python3 src/render.py PART out/videoPART.mp4 [--stills t1,t2,...]
"""
import functools
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
import art  # noqa: E402
from art import CH, CW, H, SH, SW, W, FONT  # noqa: E402
from story import PARTS, SERIES  # noqa: E402

FPS, DUR = 30, 60
PART = int(sys.argv[1])
P = PARTS[PART]
LINES = json.load(open(os.path.join(art.ROOT, 'out', f'lines{PART}.json')))


def clamp(x, a=0.0, b=1.0):
    return min(b, max(a, x))


def ramp(x, a, b):
    return clamp((x - a) / (b - a))


def sine(x):
    return 0.5 - 0.5 * np.cos(np.pi * clamp(x))


def ease(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


# ---------------------------------------------------------------- views
def view(img, z, cx=0.0, cy=0.0, shake=(0, 0)):
    """Crop a scene-space image (SW x SH) at zoom z around (cx, cy) and scale to the frame."""
    cw, ch = SW / z, SH / z
    x0 = min(max(0.0, SW / 2 + cx - cw / 2 + shake[0]), SW - cw)    # never look past the edge of the set
    y0 = min(max(0.0, SH / 2 + cy - ch / 2 + shake[1]), SH - ch)
    return img.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch)), (x0, y0, W / cw)


def to_frame(m, x, y):
    x0, y0, s = m
    return (x - x0) * s, (y - y0) * s


def knock_shake(t, knocks, amp=9):
    x = y = 0.0
    for k in knocks:
        u = t - k
        if 0 < u < 0.45:
            e = np.exp(-u * 11)
            x += np.sin(u * 95 + k) * amp * e
            y += np.cos(u * 70 + k) * amp * 0.5 * e
    return x, y


@functools.lru_cache(None)
def graded_desk():
    return art.grade(art.desk(), seed=5, leak=0.4)


@functools.lru_cache(None)
def desk_layout(key):
    """The desk with this shot's Polaroids laid out on it (static)."""
    shot = next(s for s in P['shots'] if s['kind'] == 'desk') if key == 'part' else None
    photos = shot['photos'] if shot else PARTS[1]['shots'][1]['photos']
    img = graded_desk().convert('RGBA')
    for item in photos:
        pid, note, hand, x, y, rot = item[:6]
        scrawl = item[6] if len(item) > 6 else None
        c = art.card(pid, 1, note, hand, 1, scrawl, 1, old=(pid == 'child_swing'))
        c = art.shadowed(c.resize((int(CW * 0.56), int(CH * 0.56)), Image.LANCZOS))
        c = c.rotate(rot, expand=True, resample=Image.BICUBIC)
        img.alpha_composite(c, (int(SW / 2 + x - c.width / 2), int(SH / 2 + y - c.height / 2)))
    return img.convert('RGB')


# ---------------------------------------------------------------- shots
def shot_black(t, s):
    img = Image.new('RGB', (W, H), (6, 5, 5))
    # the only light: under the door
    k = 0.75 + 0.25 * np.sin(t * 3.1)
    for kk in s.get('knocks', []):
        if 0 < t - kk < 0.3:
            k *= 0.6
    d = ImageDraw.Draw(img)
    d.rectangle([260, 1500, 820, 1506], fill=(int(220 * k), int(200 * k), int(160 * k)))
    g = img.filter(ImageFilter.GaussianBlur(14))
    return Image.blend(img, g, 0.5)


def shot_desk(t, s):
    (x0, y0, z0), (x1, y1, z1) = s['pan']
    u = sine(ramp(t, s['t0'], s['t1']))
    img, _ = view(desk_layout('part'), z0 + (z1 - z0) * u, x0 + (x1 - x0) * u, y0 + (y1 - y0) * u)
    return img


def shot_polaroid(t, s):
    u = ramp(t, s['t0'], s['t1'])
    bg, _ = view(graded_desk(), 1.1 + 0.08 * u)
    dv = s.get('develop')
    develop = 1.0 if dv is None else sine(ramp(t, dv[0], dv[1]))     # slow to start, like real film
    note = s.get('note')
    if s.get('write') is not None:
        dur = max(1.2, 0.075 * len(note))
        reveal = ramp(t, s['write'], s['write'] + dur)
    else:
        reveal = 1.0 if dv is None else 0.0
    sc = s.get('scrawl')
    scr = ramp(t, s.get('scrawl_t', 0), s.get('scrawl_t', 0) + 1.6) if sc else 0
    c = art.card(s['photo'], develop, note, s['hand'], reveal, sc, scr, old=s.get('old', False))
    scale = 1.12
    c = art.shadowed(c.resize((int(CW * scale), int(CH * scale)), Image.BILINEAR), blur=22, off=(14, 24))
    rot = s.get('rot', 0) + 1.2 * (u - 0.5)
    c = c.rotate(rot, expand=True, resample=Image.BILINEAR)
    y = 860
    if s.get('eject') is not None:   # slides up out of the camera
        y += 1500 * (1 - ease(ramp(t, s['eject'], s['eject'] + 0.9)))
    bg = bg.convert('RGBA')
    bg.alpha_composite(c, (int(W / 2 - c.width / 2), int(y - c.height / 2)))
    return bg.convert('RGB')


def shot_scene(t, s):
    name = s['scene']
    u = sine(ramp(t, s['t0'], s['t1']))
    z = s['zoom'][0] + (s['zoom'][1] - s['zoom'][0]) * u
    shake = knock_shake(t, s.get('knocks', []))
    if name == 'radiator':
        base = art.graded_scene('radiator_back').convert('RGBA')
        sprite = None
        if s.get('pull'):                     # P2: a Polaroid comes up out of the gap
            a, b = s['pull']
            k = ease(ramp(t, a, b))
            sprite = (640, 1290 - 420 * k, -8 + 10 * k)
        if s.get('slip'):                     # P6: it slips down behind the radiator
            a, b = s['slip']
            k = ramp(t, a, b) ** 1.6
            sprite = (680, 1080 + 330 * k, -4 + 8 * k)
        if sprite:
            c = art.card('elise_smile', 1, 'THIS IS ELISE. SHE IS YOUR DAUGHTER.', 'elise', 1)
            c = art.shadowed(c.resize((int(CW * 0.42), int(CH * 0.42)), Image.BILINEAR), blur=10, off=(6, 10))
            c = c.rotate(sprite[2], expand=True, resample=Image.BILINEAR)
            base.alpha_composite(c, (int(sprite[0] - c.width / 2), int(sprite[1] - c.height / 2)))
        base.alpha_composite(art.graded_scene('radiator_front'))
        img, m = view(base.convert('RGB'), z, 0, 150, shake)
        return img
    src = art.graded_scene(name)
    if name == 'corridor_glass' and s.get('wave') is not None:
        k = ramp(t, s['wave'], s['wave'] + 0.4)
        if k > 0:
            src = Image.blend(src, art.graded_scene('corridor_glass_wave'), k)
    if name == 'door_in' and s.get('ajar'):
        a, amt = s['ajar']
        k = ramp(t, a, a + 1.6) * amt
        if k > 0:
            src = Image.blend(src, art.graded_scene('door_in_ajar'), k)
    img, m = view(src, z, 0, 0, shake)
    if name == 'door_in' and s.get('feet') is not None and t >= s['feet']:
        d = ImageDraw.Draw(img)
        gx0, gy0, gx1, gy1 = art.GAP
        for k, (fa, fb) in enumerate([(-170, -60), (40, 150)]):
            if t >= s['feet'] + 0.6 * k:
                p0 = to_frame(m, (gx0 + gx1) / 2 + fa, gy0)
                p1 = to_frame(m, (gx0 + gx1) / 2 + fb, gy1)
                d.rectangle([p0[0], p0[1], p1[0], p1[1]], fill=(20, 16, 14))
    if s.get('viewfinder'):
        img = viewfinder(img, t)
    return img


def viewfinder(img, t):
    d = ImageDraw.Draw(img, 'RGBA')
    d.rectangle([0, 0, W, 300], fill=(0, 0, 0, 150)); d.rectangle([0, 1420, W, H], fill=(0, 0, 0, 150))
    d.rectangle([0, 300, 90, 1420], fill=(0, 0, 0, 150)); d.rectangle([990, 300, W, 1420], fill=(0, 0, 0, 150))
    L = 70
    for (x, y, sx, sy) in [(110, 320, 1, 1), (970, 320, -1, 1), (110, 1400, 1, -1), (970, 1400, -1, -1)]:
        d.line([(x, y), (x + sx * L, y)], fill=(250, 246, 236, 230), width=5)
        d.line([(x, y), (x, y + sy * L)], fill=(250, 246, 236, 230), width=5)
    d.ellipse([W / 2 - 40, 860 - 40, W / 2 + 40, 860 + 40], outline=(250, 246, 236, 160), width=3)
    if int(t * 2) % 2 == 0:
        d.ellipse([130, 1340, 154, 1364], fill=(255, 80, 60, 230))
    return img


def shot_rewind(t, s):
    u = ramp(t, s['t0'], s['t1'])
    src = desk_layout('p1')
    img, _ = view(src, 1.3, 0, -270 + 540 * ((u * 3.2) % 1.0))
    img = img.filter(ImageFilter.BoxBlur(0)).resize((W // 4, H // 16)).resize((W, H), Image.BILINEAR)   # streaks
    a = np.asarray(img, np.float32)
    a = a * 0.5 + a.mean(axis=2, keepdims=True) * 0.5
    img = Image.fromarray(a.astype(np.uint8))
    d = ImageDraw.Draw(img)
    # the clock runs backwards
    def mins(c):
        hh, rest = c.split(':'); mm, ap = rest.split(' ')
        return (int(hh) % 12 + (12 if ap == 'PM' else 0)) * 60 + int(mm)
    m = mins(s['from_clock']) + (mins(s['to_clock']) - mins(s['from_clock'])) * sine(u)
    hh, mm = int(m // 60), int(m % 60)
    txt = f"{(hh - 1) % 12 + 1}:{mm:02d} {'PM' if hh >= 12 else 'AM'}"
    f = FONT(art.TYPE_BOLD, 120)
    d.text((W / 2, 900), txt, font=f, fill=(255, 140, 40), anchor='mm')
    d.text((W / 2, 1020), 'EARLIER', font=FONT(art.TYPE_BOLD, 40), fill=(250, 240, 220), anchor='mm')
    return img


@functools.lru_cache(None)
def title_card():
    c = art.texture((900, 760), 61, (238, 232, 216), 4).convert('RGBA')
    d = ImageDraw.Draw(c)
    for y in range(190, 760, 64):
        d.line([(40, y), (860, y)], fill=(170, 196, 220), width=2)
    d.line([(110, 0), (110, 760)], fill=(220, 120, 120), width=3)
    d.text((140, 70), f'{SERIES}  ·  PART {PART} OF 6', font=FONT(art.TYPE_BOLD, 34), fill=(60, 60, 70))
    lines = P['title'].split(' ') if len(P['title']) > 11 else [P['title']]
    if len(lines) > 2:
        lines = [' '.join(lines[:2]), ' '.join(lines[2:])]
    f = art.fit_font(art.TITLE_FONT, max(lines, key=len), 700, 110)
    for i, l in enumerate(lines):
        d.text((140, 220 + i * 130), l, font=f, fill=art.INK)
    d.text((140, 520), P['clock'], font=FONT(art.TYPE_BOLD, 44), fill=(214, 100, 30))
    if P['shots'][-1].get('loop'):
        d.text((140, 600), 'now watch Part 1 again.', font=FONT(art.ELISE_FONT, 64), fill=(40, 70, 130))
    elif PART == 1:
        d.text((140, 600), 'it goes backwards from here.', font=FONT(art.ELISE_FONT, 60), fill=(40, 70, 130))
    else:
        d.text((140, 600), f'before Part {PART - 1}.', font=FONT(art.ELISE_FONT, 64), fill=(40, 70, 130))
    c = art.shadowed(c, blur=20, off=(12, 20)).rotate(-2.5, expand=True, resample=Image.BICUBIC)
    return c


def shot_title(t, s):
    u = ramp(t, s['t0'], s['t1'])
    bg, _ = view(graded_desk(), 1.15 + 0.05 * u)
    bg = bg.convert('RGBA')
    c = title_card()
    k = ease(ramp(t, s['t0'], s['t0'] + 0.8))
    bg.alpha_composite(c, (int(W / 2 - c.width / 2), int(860 - c.height / 2 + 300 * (1 - k))))
    return bg.convert('RGB')


SHOT = dict(black=shot_black, desk=shot_desk, polaroid=shot_polaroid, scene=shot_scene, rewind=shot_rewind, title=shot_title)


# ---------------------------------------------------------------- overlays
STRIP = {'m': (246, 242, 232), 'mw': (246, 242, 232), 'e': (252, 236, 170), 'ed': (252, 236, 170), 'n': (200, 230, 226)}


def subtitles(img, t):
    for i, l in enumerate(LINES):
        nxt = LINES[i + 1]['t0'] if i + 1 < len(LINES) else 99
        end = min(nxt - 0.05, l['t1'] + 1.2)
        if not (l['t0'] - 0.05 <= t < end):
            continue
        text = l['text'] if l['kind'] not in ('ed',) else f"({l['text']})"
        f = FONT(art.TYPE_BOLD, 44)
        words, rows, cur = text.split(' '), [], ''
        for w_ in words:
            trial = (cur + ' ' + w_).strip()
            if f.getlength(trial) > 860 and cur:
                rows.append(cur); cur = w_
            else:
                cur = trial
        rows.append(cur)
        n = len(text)
        shown = int(n * clamp((t - l['t0']) / max(0.3, (l['t1'] - l['t0']) * 0.9)))
        d = ImageDraw.Draw(img)
        y = 1400 - (len(rows) - 1) * 62
        left = shown
        for r in rows:
            tw = f.getlength(r)
            x0 = W / 2 - tw / 2
            d.rectangle([x0 - 22, y - 34, x0 + tw + 22, y + 30], fill=STRIP[l['kind']])
            d.text((x0, y), r[:max(0, left)], font=f, fill=(24, 22, 26), anchor='lm')
            left -= len(r) + 1
            y += 62
    return img


def date_stamp(img):
    d = ImageDraw.Draw(img)
    f = FONT(art.TYPE_BOLD, 40)
    txt = f"'26 10 16  {P['clock']}"
    for dx, dy, a in [(0, 0, 255)]:
        d.text((1000, 236), txt, font=f, fill=(255, 132, 36), anchor='rm')
    return img


GRAIN = [np.random.default_rng(k).normal(0, 7, (H, W, 1)).astype(np.int16) for k in range(8)]


def finish(img, t, fi):
    a = np.asarray(img, np.int16)
    for tf in P.get('flashes', []):
        u = t - tf
        if -0.05 < u < 0.7:
            k = 1.0 if u < 0.06 else np.exp(-(u - 0.06) * 6)
            a = (a + (255 - a) * k).astype(np.int16)
    a = a + GRAIN[fi % 8]
    return np.clip(a, 0, 255).astype(np.uint8)


def frame(fi):
    t = fi / FPS
    s = next((x for x in P['shots'] if x['t0'] <= t < x['t1']), P['shots'][-1])
    img = SHOT[s['kind']](t, s)
    if s['kind'] in ('scene', 'polaroid', 'desk'):
        img = date_stamp(img)
    img = subtitles(img, t)
    return finish(img, t, fi)


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
