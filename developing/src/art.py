"""DEVELOPING — the art kit: cut-paper scenes, instant-film grade, Polaroids, handwriting.

Everything is drawn once per process (scenes, photos, Polaroid cards) and composited per frame.
Characters are flat cut paper with no faces. The girl always wears yellow.
"""
import functools
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1080, 1920
SW, SH = 1350, 2400                       # scenes are drawn 1.25x so the camera can push in
FONT = lambda name, size: ImageFont.truetype(os.path.join(ROOT, 'fonts', name), size)  # noqa: E731
MARA_FONT, ELISE_FONT, TITLE_FONT = 'RockSalt-Regular.ttf', 'Caveat.ttf', 'PermanentMarker-Regular.ttf'
TYPE_FONT, TYPE_BOLD = 'CourierPrime-Regular.ttf', 'CourierPrime-Bold.ttf'

YELLOW = (226, 178, 52)      # the girl / Elise, at every age
LAVENDER = (150, 132, 168)   # Mara
TEAL = (70, 130, 128)        # the nurse
SKIN = (214, 170, 140)
INK = (28, 30, 44)
PAPER = (240, 234, 220)
RED_MARKER = (178, 40, 36)


# ---------------------------------------------------------------- film
def grade(img, seed=0, leak=0.5, fade=0.0):
    """Instant film: lifted blacks, warm highlights, teal shadows, soft, a light leak, vignette."""
    a = np.asarray(img.convert('RGB')).astype(np.float32) / 255
    h, w = a.shape[:2]
    lum = a @ np.array([0.299, 0.587, 0.114], np.float32)
    a = a * (1 - 0.18 - 0.2 * fade) + lum[..., None] * (0.18 + 0.2 * fade)      # a little desaturated
    sh = (1 - lum)[..., None] ** 2
    hi = lum[..., None] ** 2
    a = a + sh * np.array([-0.02, 0.03, 0.05]) + hi * np.array([0.05, 0.02, -0.06])
    a = 0.07 + a * 0.86                                                        # lifted blacks, soft whites
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.random.default_rng(seed)
    lx, ly = r.choice([0.0, 1.0]) * w, r.uniform(0.0, 0.5) * h
    d = np.sqrt((xx - lx) ** 2 + (yy - ly) ** 2) / max(w, h)
    a = a + leak * 0.22 * np.exp(-d * d * 9)[..., None] * np.array([1.0, 0.45, 0.15])
    v = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    a = a * (1 - 0.28 * np.clip(v - 0.55, 0, 1)[..., None] ** 1.5)
    out = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    return out.filter(ImageFilter.GaussianBlur(0.7))


def texture(size, seed, base, var=10, streak=False):
    """Paper/wall/wood: flat colour with soft noise (and long grain for wood)."""
    w, h = size
    r = np.random.default_rng(seed)
    n = r.standard_normal((h // 8 + 1, w // 8 + 1)).astype(np.float32)
    n = np.asarray(Image.fromarray(n).resize((w, h), Image.BICUBIC))
    if streak:
        s = r.standard_normal((h // 2 + 1, 4)).astype(np.float32)
        s = np.asarray(Image.fromarray(s).resize((w, h), Image.BICUBIC))
        n = n * 0.4 + s * 1.2
    a = np.array(base, np.float32)[None, None] + n[..., None] * var
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


# ---------------------------------------------------------------- cut-paper people
def person(d, cx, base, h, kind, back=False, arm_up=False, sitting=False):
    """kind: girl (16, yellow coat), child (7, yellow dress), mara (grey hair, lavender), nurse (teal)."""
    u = h / 100
    coat = {'girl': YELLOW, 'child': YELLOW, 'mara': LAVENDER, 'nurse': TEAL}[kind]
    hair = {'girl': (62, 42, 34), 'child': (70, 48, 36), 'mara': (196, 196, 200), 'nurse': (40, 34, 30)}[kind]
    legs = {'girl': (52, 60, 84), 'child': SKIN, 'mara': (90, 84, 96), 'nurse': TEAL}[kind]
    top = base - h
    hx, hy, hr = cx, top + 7 * u, 6.2 * u
    # hair behind the head
    if kind == 'girl':
        d.polygon([(cx - 8 * u, top + 6 * u), (cx + 8 * u, top + 6 * u), (cx + 9 * u, top + 26 * u), (cx - 9 * u, top + 26 * u)], fill=hair)
    if kind == 'child':
        d.ellipse([cx - 11 * u, top + 6 * u, cx - 5 * u, top + 12 * u], fill=hair)
        d.ellipse([cx + 5 * u, top + 6 * u, cx + 11 * u, top + 12 * u], fill=hair)
    if kind == 'mara':
        d.ellipse([cx - 4 * u, top - 3 * u, cx + 4 * u, top + 4 * u], fill=hair)
    # legs
    if sitting:
        d.rectangle([cx - 7 * u, base - 30 * u, cx + 14 * u, base - 24 * u], fill=legs)
        d.rectangle([cx + 9 * u, base - 30 * u, cx + 15 * u, base], fill=legs)
    else:
        d.rectangle([cx - 6.5 * u, base - 44 * u, cx - 1 * u, base], fill=legs)
        d.rectangle([cx + 1 * u, base - 44 * u, cx + 6.5 * u, base], fill=legs)
    # body: coat / cardigan / scrubs / dress, a little too narrow at the waist
    hem = base - (40 if kind in ('girl', 'nurse') else 36 if kind == 'mara' else 42) * u
    if sitting:
        hem = base - 28 * u
    d.polygon([(cx - 12 * u, top + 17 * u), (cx + 12 * u, top + 17 * u), (cx + 9 * u, top + 38 * u), (cx + 13 * u, hem),
               (cx - 13 * u, hem), (cx - 9 * u, top + 38 * u)], fill=coat)
    # arms
    if arm_up:
        d.polygon([(cx + 10 * u, top + 19 * u), (cx + 14 * u, top + 18 * u), (cx + 22 * u, top + 2 * u), (cx + 18 * u, top)], fill=coat)
        d.ellipse([cx + 17 * u, top - 4 * u, cx + 23 * u, top + 2 * u], fill=SKIN)
    else:
        d.polygon([(cx + 10 * u, top + 18 * u), (cx + 14 * u, top + 19 * u), (cx + 15 * u, top + 46 * u), (cx + 11 * u, top + 46 * u)], fill=coat)
    d.polygon([(cx - 10 * u, top + 18 * u), (cx - 14 * u, top + 19 * u), (cx - 15 * u, top + 46 * u), (cx - 11 * u, top + 46 * u)], fill=coat)
    # neck, head. No faces.
    d.rectangle([cx - 2.5 * u, top + 11 * u, cx + 2.5 * u, top + 18 * u], fill=SKIN)
    d.ellipse([hx - hr * 0.86, hy - hr, hx + hr * 0.86, hy + hr], fill=hair if back else SKIN)
    if not back:   # hair line over the forehead
        d.chord([hx - hr * 0.9, hy - hr * 1.05, hx + hr * 0.9, hy + hr * 0.5], 180, 360, fill=hair)
    if kind == 'nurse':
        d.rectangle([cx - 5 * u, top - 1 * u, cx + 5 * u, top + 2 * u], fill=(236, 236, 230))


# ---------------------------------------------------------------- scenes (drawn at SW x SH)
def _room(seed, wall=(128, 112, 96)):
    img = texture((SW, SH), seed, wall, 8)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 1900, SW, SH], fill=(96, 78, 62))                              # floor
    d.rectangle([0, 1880, SW, 1900], fill=(70, 58, 48))                            # skirting
    return img, d


def _door(d, x0, y0, x1, y1, col=(88, 70, 56), glass=None):
    d.rectangle([x0 - 26, y0 - 26, x1 + 26, y1], fill=(196, 186, 168))              # frame
    d.rectangle([x0, y0, x1, y1], fill=col)
    d.rectangle([x0 + 40, y0 + 60, x1 - 40, y0 + 520], outline=(74, 58, 46), width=6)
    d.rectangle([x0 + 40, y0 + 600, x1 - 40, y1 - 80], outline=(74, 58, 46), width=6)
    d.ellipse([x1 - 70, (y0 + y1) // 2 - 16, x1 - 38, (y0 + y1) // 2 + 16], fill=(200, 170, 90))
    if glass:
        d.rectangle(glass, fill=(150, 190, 196))


def _lamp_glow(img, x, y, r, col=(255, 190, 110), k=0.55):
    g = Image.new('RGB', img.size, (0, 0, 0))
    ImageDraw.Draw(g).ellipse([x - r, y - r, x + r, y + r], fill=col)
    g = g.filter(ImageFilter.GaussianBlur(r * 0.45))
    return Image.fromarray(np.clip(np.asarray(img, np.float32) + np.asarray(g, np.float32) * k, 0, 255).astype(np.uint8))


DOOR_BOX = (420, 520, 930, 1890)   # x0, y0, x1, y1 of the room door in scene space
GAP = (420, 1876, 930, 1890)       # the light under it


def scene_door_in(ajar=False):
    img, d = _room(11, (112, 96, 84))
    x0, y0, x1, y1 = DOOR_BOX
    if ajar:
        d.rectangle([x0 - 26, y0 - 26, x1 + 26, y1], fill=(196, 186, 168))
        d.rectangle([x0, y0, x1, y1], fill=(206, 222, 220))                         # the corridor, bright
        person(d, 640, y1 - 10, 1150, 'girl')
        d.polygon([(x1 - 130, y0), (x1, y0 - 30), (x1, y1 + 10), (x1 - 130, y1)], fill=(88, 70, 56))  # door swung in
    else:
        _door(d, x0, y0, x1, y1, glass=(560, 640, 790, 900))
        d.rectangle(GAP, fill=(232, 240, 230))
    # Mara's photos pinned up beside the door
    for k, (px, py, rot) in enumerate([(120, 700, -6), (230, 980, 4), (110, 1240, 3), (1080, 760, 5), (1180, 1080, -4)]):
        c = Image.new('RGBA', (150, 180), PAPER + (255,))
        ImageDraw.Draw(c).rectangle([12, 12, 138, 138], fill=(60 + k * 20, 70, 80))
        c = c.rotate(rot, expand=True, resample=Image.BICUBIC)
        img.paste(c, (px - 75, py - 90), c)
    img = _lamp_glow(img, 120, 600, 520)
    return img


def scene_nurse_door():
    img, d = _room(12, (124, 108, 92))
    x0, y0, x1, y1 = DOOR_BOX
    d.rectangle([x0 - 26, y0 - 26, x1 + 26, y1], fill=(196, 186, 168))
    d.rectangle([x0, y0, x1, y1], fill=(196, 214, 210))
    d.rectangle([x0, y0 + 980, x1, y1], fill=(150, 160, 156))
    person(d, 675, y1 - 10, 1180, 'nurse')
    d.polygon([(x0, y0), (x0 + 120, y0 + 40), (x0 + 120, y1 - 20), (x0, y1)], fill=(88, 70, 56))
    return _lamp_glow(img, 1200, 700, 500)


def scene_corridor_glass(wave=False):
    img = texture((SW, SH), 13, (100, 82, 66), 6)                                   # the inside of the door
    d = ImageDraw.Draw(img)
    gx0, gy0, gx1, gy1 = 210, 520, 1140, 1640
    d.rectangle([gx0 - 30, gy0 - 30, gx1 + 30, gy1 + 30], fill=(70, 56, 44))
    # through the glass: a long corridor, cold light
    corr = texture((gx1 - gx0, gy1 - gy0), 14, (180, 196, 192), 6)
    cd = ImageDraw.Draw(corr)
    cw, ch = corr.size
    vx, vy = cw // 2, int(ch * 0.42)
    cd.polygon([(0, ch), (cw, ch), (vx + 90, vy + 120), (vx - 90, vy + 120)], fill=(140, 150, 140))
    cd.polygon([(0, 0), (cw, 0), (vx + 90, vy - 120), (vx - 90, vy - 120)], fill=(206, 216, 212))
    for k in range(4):
        y = 30 + k * 60
        cd.rectangle([vx - 60 + k * 12, y, vx + 60 - k * 12, y + 14], fill=(240, 246, 236))
    person(cd, vx + 40, vy + 330, 560, 'girl', arm_up=wave)
    img.paste(corr, (gx0, gy0))
    d.line([(gx0, gy0), (gx1, gy0)], fill=(230, 236, 230), width=3)
    d.text((gx0 + 30, gy1 + 60), '307', font=FONT(TYPE_BOLD, 72), fill=(200, 170, 90))   # anchor: The Stillness, apt 307
    return img


def scene_radiator():
    back = texture((SW, SH), 15, (150, 138, 120), 7)
    d = ImageDraw.Draw(back)
    d.rectangle([180, 300, 1170, 1050], fill=(206, 214, 210))                     # window: pale sky
    for k in range(12):
        d.rectangle([180, 300 + k * 62, 1170, 300 + k * 62 + 30], fill=(226, 220, 204))   # blinds
    d.rectangle([150, 1050, 1200, 1100], fill=(214, 206, 190))                     # sill
    d.rectangle([220, 1240, 1130, 1260], fill=(40, 34, 30))                        # the dark gap behind
    d.rectangle([0, 1900, SW, SH], fill=(96, 78, 62))
    front = Image.new('RGBA', (SW, SH), (0, 0, 0, 0))
    fd = ImageDraw.Draw(front)
    fd.rectangle([200, 1250, 1150, 1760], fill=(214, 210, 200, 255))
    for k in range(17):
        x = 230 + k * 54
        fd.rectangle([x, 1270, x + 30, 1740], fill=(196, 192, 182, 255))
    fd.rectangle([260, 1760, 300, 1900], fill=(180, 176, 166, 255))
    fd.rectangle([1050, 1760, 1090, 1900], fill=(180, 176, 166, 255))
    return back, front


def scene_wallet():
    img = texture((SW, SH), 16, (156, 64, 58), 10)                                 # red knit blanket
    d = ImageDraw.Draw(img)
    for y in range(0, SH, 46):
        d.line([(0, y), (SW, y + 20)], fill=(140, 56, 50), width=6)
    d.rounded_rectangle([170, 700, 1180, 1500], 30, fill=(92, 60, 40))
    d.line([(675, 700), (675, 1500)], fill=(70, 46, 30), width=8)
    d.rounded_rectangle([730, 780, 1110, 1420], 16, fill=(120, 84, 58))
    d.rectangle([760, 820, 1080, 1260], fill=(210, 220, 214))                     # clear window
    ph = photo('child_swing').resize((300, 300))
    img.paste(ph, (770, 860))
    d.rectangle([760, 820, 1080, 1260], outline=(230, 236, 230), width=4)
    for k in range(3):
        d.rounded_rectangle([240, 800 + k * 160, 620, 900 + k * 160], 10, fill=(80 + k * 40, 120, 150 - k * 30))
    # her residence card. Anchor to The Stillness: Building 3, room 307.
    d.rounded_rectangle([230, 1280, 640, 1440], 12, fill=(236, 232, 220))
    d.text((255, 1300), 'RESIDENT', font=FONT(TYPE_BOLD, 30), fill=(120, 60, 50))
    d.text((255, 1340), 'MARA H.', font=FONT(TYPE_BOLD, 40), fill=INK)
    d.text((255, 1392), 'BUILDING 3 \u00b7 RM 307', font=FONT(TYPE_BOLD, 30), fill=INK)
    return img


def scene_camera_bed(tag=True):
    img = texture((SW, SH), 17, (200, 196, 184), 6)                                # pale blanket
    d = ImageDraw.Draw(img)
    for x in range(0, SW, 90):
        d.line([(x, 0), (x + 200, SH)], fill=(188, 184, 172), width=10)
    cx, cy = 640, 1000
    d.rounded_rectangle([cx - 330, cy - 260, cx + 330, cy + 260], 60, fill=(236, 232, 224))    # the camera
    d.rounded_rectangle([cx - 330, cy + 120, cx + 330, cy + 260], 40, fill=(214, 120, 90))
    d.ellipse([cx - 150, cy - 170, cx + 150, cy + 130], fill=(40, 40, 46))
    d.ellipse([cx - 95, cy - 115, cx + 95, cy + 75], fill=(70, 86, 104))
    d.ellipse([cx - 40, cy - 70, cx + 10, cy - 20], fill=(170, 190, 210))
    d.rectangle([cx + 190, cy - 230, cx + 300, cy - 160], fill=(60, 60, 66))
    d.rectangle([cx - 300, cy - 230, cx - 220, cy - 180], fill=(250, 240, 200))
    if tag:
        d.line([(cx + 260, cy + 200), (cx + 330, cy + 520)], fill=(120, 100, 80), width=5)
        t = Image.new('RGBA', (520, 300), PAPER + (255,))
        td = ImageDraw.Draw(t)
        td.ellipse([30, 130, 60, 160], outline=(120, 100, 80), width=4)
        f = FONT(ELISE_FONT, 64)
        td.text((90, 40), 'For Mom —', font=f, fill=INK)
        td.text((90, 120), 'take pictures,', font=f, fill=INK)
        td.text((90, 196), 'write names.  E x', font=f, fill=INK)
        t = t.rotate(-8, expand=True, resample=Image.BICUBIC)
        img.paste(t, (cx + 200, cy + 480), t)
    return img


def scene_room_day():
    img, d = _room(18, (170, 150, 124))
    d.rectangle([700, 380, 1240, 1180], fill=(232, 226, 200))                     # window, morning
    for k in range(10):
        d.rectangle([700, 380 + k * 80, 1240, 380 + k * 80 + 44], fill=(206, 190, 160))
    d.rounded_rectangle([60, 1350, 1100, 1900], 30, fill=(230, 226, 214))          # bed
    d.rounded_rectangle([60, 1450, 1100, 1900], 30, fill=(150, 160, 190))          # blanket
    d.rounded_rectangle([90, 1290, 420, 1460], 40, fill=(246, 242, 234))           # pillow
    d.rectangle([40, 1180, 90, 1900], fill=(110, 90, 72))                          # headboard
    # sunlight through the blinds, across the wall and the bed
    beam = Image.new('L', (SW, SH), 0)
    bd = ImageDraw.Draw(beam)
    for k in range(10):
        y = 380 + k * 80 + 44
        bd.polygon([(700, y), (700, y + 36), (100, y + 700), (100, y + 664)], fill=90)
    beam = beam.filter(ImageFilter.GaussianBlur(10))
    a = np.asarray(img, np.float32) + np.asarray(beam, np.float32)[..., None] * np.array([1.0, 0.8, 0.5]) * 0.6
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def scene_mirror():
    img = texture((SW, SH), 19, (180, 196, 190), 6)                                # bathroom tiles
    d = ImageDraw.Draw(img)
    for y in range(0, SH, 120):
        d.line([(0, y), (SW, y)], fill=(160, 176, 170), width=4)
    for x in range(0, SW, 120):
        d.line([(x, 0), (x, SH)], fill=(160, 176, 170), width=4)
    d.ellipse([235, 330, 1115, 1530], fill=(150, 158, 150))
    m = Image.new('RGB', (840, 1160), (196, 204, 196))
    md = ImageDraw.Draw(m)
    person(md, 420, 1500, 1320, 'mara')
    mask = Image.new('L', (840, 1160), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, 840, 1160], fill=255)
    img.paste(m, (255, 350), mask)
    d.rounded_rectangle([200, 1700, 1150, 1860], 30, fill=(238, 238, 232))         # sink
    return img


def scene_door_out():
    img, d = _room(20, (130, 114, 98))
    x0, y0, x1, y1 = DOOR_BOX
    d.rectangle([x0 - 26, y0 - 26, x1 + 26, y1], fill=(196, 186, 168))
    d.rectangle([x0, y0, x1, y1], fill=(200, 214, 208))
    d.polygon([(x0 + 40, y1), (x1 - 40, y1), (x0 + 330, y0 + 700), (x0 + 180, y0 + 700)], fill=(160, 166, 156))
    person(d, 690, y0 + 1060, 420, 'girl', back=True)                               # walking away
    d.polygon([(x1, y0), (x1 + 160, y0 - 40), (x1 + 160, y1 + 30), (x1, y1)], fill=(88, 70, 56))
    return _lamp_glow(img, 160, 500, 420, k=0.35)


def scene_elise_visit():
    img = scene_room_day()
    d = ImageDraw.Draw(img)
    d.rectangle([880, 1500, 1200, 1560], fill=(110, 86, 64))                       # chair
    d.rectangle([1160, 1180, 1200, 1900], fill=(110, 86, 64))
    d.rectangle([890, 1560, 920, 1900], fill=(110, 86, 64))
    person(d, 1020, 1900, 860, 'girl', sitting=True)
    d.rounded_rectangle([860, 1320, 980, 1400], 12, fill=(236, 232, 224))         # the camera, in her hands
    d.ellipse([890, 1330, 950, 1390], fill=(40, 40, 46))
    return img


# ---------------------------------------------------------------- photos (square)
PS = 760


def _sq(img, box):
    return img.crop(box).resize((PS, PS), Image.LANCZOS)


@functools.lru_cache(None)
def photo(pid):
    if pid == 'girl_door':
        return _sq(scene_door_in(ajar=True), (215, 400, 1065, 1250))
    if pid == 'girl_glass':
        return _sq(scene_corridor_glass(wave=True), (300, 600, 1060, 1360))
    if pid == 'nurse':
        return _sq(scene_nurse_door(), (250, 420, 1100, 1270))
    if pid == 'girl_leaving':
        return _sq(scene_door_out(), (300, 760, 1080, 1540))
    if pid == 'old_woman':
        return _sq(scene_mirror(), (275, 380, 1075, 1180))
    if pid == 'child_swing':
        img = texture((PS, PS), 21, (150, 196, 220), 6)                            # summer sky
        d = ImageDraw.Draw(img)
        d.rectangle([0, 560, PS, PS], fill=(110, 160, 80))
        d.line([(120, 0), (330, 520)], fill=(90, 70, 50), width=8)
        d.line([(560, 0), (380, 520)], fill=(90, 70, 50), width=8)
        d.rectangle([300, 500, 420, 520], fill=(90, 70, 50))
        person(d, 360, 690, 330, 'child')
        return img
    if pid == 'elise_smile':
        img = scene_elise_visit()
        d = ImageDraw.Draw(img)
        return _sq(img, (720, 1060, 1320, 1660))
    if pid == 'girl_face':
        # the only face in the story with eyes
        img = Image.new('RGB', (PS, PS), (250, 246, 236))                           # flash-white corridor
        d = ImageDraw.Draw(img)
        d.ellipse([110, 60, 650, 760], fill=(62, 42, 34))                           # hair
        d.ellipse([190, 120, 570, 640], fill=(236, 200, 172))                       # face, blown out by the flash
        d.rectangle([150, 560, 610, PS], fill=YELLOW)
        d.chord([180, 100, 580, 420], 180, 360, fill=(62, 42, 34))
        for ex in (300, 460):
            d.ellipse([ex - 34, 360, ex + 34, 404], fill=(250, 248, 244))
            d.ellipse([ex - 18, 364, ex + 18, 400], fill=(70, 96, 120))
            d.ellipse([ex - 7, 375, ex + 7, 389], fill=(10, 10, 14))
        return img
    raise KeyError(pid)


@functools.lru_cache(None)
def graded_photo(pid, old=False):
    return grade(photo(pid), seed=sum(map(ord, pid)), leak=0.9 if old else 0.6, fade=0.5 if old else 0.0)


# ---------------------------------------------------------------- Polaroid cards
CW, CH = 844, 1026        # card; the image sits 42 px in from the top and sides


def fit_font(name, text, max_w, start):
    s = start
    while s > 20:
        f = FONT(name, s)
        if f.getlength(text) <= max_w:
            return f
        s -= 4
    return FONT(name, 20)


def handwriting(text, hand, max_w=760, start=None):
    """The note under the photo, as an RGBA layer, plus its width (for the write-on reveal)."""
    name = MARA_FONT if hand == 'mara' else ELISE_FONT
    f = fit_font(name, text, max_w, start or (54 if hand == 'mara' else 92))
    col = INK if hand == 'mara' else (40, 70, 130)
    w = int(f.getlength(text)) + 20
    layer = Image.new('RGBA', (w, 170), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((10, 20 if hand == 'mara' else 0), text, font=f, fill=col + (255,))
    return layer


@functools.lru_cache(None)
def card_base():
    c = texture((CW, CH), 31, PAPER, 4).convert('RGBA')
    return c


def card(pid, develop, note, hand, reveal, scrawl=None, scrawl_reveal=0, old=False):
    """A Polaroid: develop 0..1 (blue-grey to picture), reveal 0..1 of the note written on."""
    c = card_base().copy()
    ph = graded_photo(pid, old)
    if develop < 1:
        a = np.asarray(ph, np.float32)
        lum = a.mean(axis=2, keepdims=True)
        und = np.array([86, 98, 108], np.float32)
        k = develop
        early = und + (lum * np.array([0.9, 0.75, 0.6]) - und) * min(1, k * 1.6)       # a brown ghost comes first
        a = early * (1 - k) + a * k
        ph = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    c.paste(ph, (42, 42))
    if note and reveal > 0:
        layer = handwriting(note, hand)
        w = int(layer.width * min(1, reveal))
        if w > 0:
            lw = layer.crop((0, 0, w, layer.height))
            c.alpha_composite(lw, (max(30, (CW - layer.width) // 2), 832))
    if scrawl and scrawl_reveal > 0:
        f = FONT(MARA_FONT, 92)
        s = Image.new('RGBA', (int(f.getlength(scrawl)) + 40, 200), (0, 0, 0, 0))
        ImageDraw.Draw(s).text((20, 20), scrawl, font=f, fill=RED_MARKER + (235,))
        s = s.crop((0, 0, int(s.width * min(1, scrawl_reveal)), s.height)).rotate(14, expand=True, resample=Image.BICUBIC)
        c.alpha_composite(s, (max(0, (CW - s.width) // 2), 260))
    return c


def shadowed(img_rgba, blur=18, off=(10, 18), alpha=110):
    """RGBA with a soft drop shadow underneath (returned image is larger by a margin)."""
    m = 60
    out = Image.new('RGBA', (img_rgba.width + 2 * m, img_rgba.height + 2 * m), (0, 0, 0, 0))
    sh = Image.new('RGBA', out.size, (0, 0, 0, 0))
    a = img_rgba.split()[3].point(lambda v: v * alpha // 255)
    sh.paste((20, 14, 10, 255), (m + off[0], m + off[1]), a)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(sh)
    out.alpha_composite(img_rgba, (m, m))
    return out


@functools.lru_cache(None)
def desk(seed=41):
    return texture((SW, SH), seed, (122, 86, 58), 14, streak=True)


SCENES = {
    'door_in': lambda: scene_door_in(False), 'door_in_ajar': lambda: scene_door_in(True),
    'nurse_door': scene_nurse_door, 'corridor_glass': lambda: scene_corridor_glass(False),
    'corridor_glass_wave': lambda: scene_corridor_glass(True), 'wallet': scene_wallet,
    'camera_bed': scene_camera_bed, 'room_day': scene_room_day, 'mirror': scene_mirror,
    'door_out': scene_door_out, 'elise_visit': scene_elise_visit,
}


@functools.lru_cache(None)
def graded_scene(name):
    if name in ('radiator_back', 'radiator_front'):
        back, front = scene_radiator()
        if name == 'radiator_back':
            return grade(back, seed=7, leak=0.5)
        g = grade(front.convert('RGB'), seed=7, leak=0.5).convert('RGBA')
        g.putalpha(front.split()[3])
        return g
    return grade(SCENES[name](), seed=sum(map(ord, name)), leak=0.55)
